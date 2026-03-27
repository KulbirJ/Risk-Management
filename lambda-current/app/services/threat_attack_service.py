"""
Threat → ATT&CK Technique mapping service.

Handles:
  - Manual mapping (user picks technique)
  - AI auto-mapping via Bedrock
  - CRUD for ThreatAttackMapping records
"""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.config import settings
from ..models.models import Threat, ThreatAttackMapping, AttackTechnique
from ..services.attack_data_service import attack_data_service
from ..services.bedrock_service import bedrock_service

logger = logging.getLogger(__name__)


class ThreatAttackService:
    """Manages mappings between threats and MITRE ATT&CK techniques."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @staticmethod
    def get_mappings(db: Session, threat_id: UUID) -> List[ThreatAttackMapping]:
        """Return all technique mappings for a threat, newest first."""
        return (
            db.query(ThreatAttackMapping)
            .filter(ThreatAttackMapping.threat_id == threat_id)
            .join(AttackTechnique, ThreatAttackMapping.technique_id == AttackTechnique.id)
            .order_by(ThreatAttackMapping.confidence_score.desc())
            .all()
        )

    # ------------------------------------------------------------------
    # Manual mapping
    # ------------------------------------------------------------------

    @staticmethod
    def add_mapping(
        db: Session,
        threat_id: UUID,
        technique_id: UUID,
        confidence_score: int = 70,
        mapping_rationale: Optional[str] = None,
        auto_mapped: bool = False,
        created_by_id: Optional[UUID] = None,
    ) -> ThreatAttackMapping:
        """
        Create or update a mapping from a threat to an ATT&CK technique.
        Upserts: if the (threat_id, technique_id) pair already exists, update it.
        """
        existing = (
            db.query(ThreatAttackMapping)
            .filter(
                ThreatAttackMapping.threat_id == threat_id,
                ThreatAttackMapping.technique_id == technique_id,
            )
            .first()
        )

        if existing:
            existing.confidence_score = confidence_score
            existing.mapping_rationale = mapping_rationale or existing.mapping_rationale
            existing.auto_mapped = auto_mapped
            db.commit()
            db.refresh(existing)
            return existing

        mapping = ThreatAttackMapping(
            threat_id=threat_id,
            technique_id=technique_id,
            confidence_score=confidence_score,
            mapping_rationale=mapping_rationale,
            auto_mapped=auto_mapped,
            created_by_id=created_by_id,
        )
        db.add(mapping)
        try:
            db.commit()
            db.refresh(mapping)
        except IntegrityError:
            db.rollback()
            # Race condition – read back the existing one
            return (
                db.query(ThreatAttackMapping)
                .filter(
                    ThreatAttackMapping.threat_id == threat_id,
                    ThreatAttackMapping.technique_id == technique_id,
                )
                .first()
            )
        return mapping

    @staticmethod
    def remove_mapping(db: Session, threat_id: UUID, technique_id: UUID) -> bool:
        """Delete a specific technique mapping. Returns True if deleted."""
        deleted = (
            db.query(ThreatAttackMapping)
            .filter(
                ThreatAttackMapping.threat_id == threat_id,
                ThreatAttackMapping.technique_id == technique_id,
            )
            .delete()
        )
        db.commit()
        return deleted > 0

    # ------------------------------------------------------------------
    # AI auto-mapping
    # ------------------------------------------------------------------

    def auto_map_threat(
        self,
        db: Session,
        threat_id: UUID,
        tenant_id: UUID,
        save_suggestions: bool = True,
        confidence_threshold: int = 60,
    ) -> dict:
        """
        Use Bedrock to automatically suggest ATT&CK technique mappings for a
        threat.

        Steps:
          1. Load the threat record.
          2. Extract keywords from title + description to narrow technique candidates.
          3. Fetch a curated shortlist of candidate techniques from local cache.
          4. Call Bedrock with threat context + candidate list.
          5. Match Bedrock's mitre_id suggestions back to DB records.
          6. Optionally save suggestions above confidence_threshold.

        Returns:
          {suggestions: [...], saved_count: int, threat_id: str}
        """
        # 1. Load threat
        threat: Optional[Threat] = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            raise ValueError(f"Threat {threat_id} not found")

        if not attack_data_service.is_populated(db):
            raise RuntimeError(
                "ATT&CK data not yet synced. "
                "Call POST /api/v1/attack/sync first."
            )

        # 2. Keyword extraction
        keywords = self._extract_keywords(threat.title, threat.description)

        # 3. Candidate techniques
        candidates = attack_data_service.get_techniques_for_threat_keywords(
            db, keywords, max_results=settings.attack_max_techniques_per_prompt
        )
        candidate_dicts = [
            {
                "id": str(t.id),
                "mitre_id": t.mitre_id,
                "name": t.name,
                "tactic_shortname": t.tactic_shortname or "",
                "description": (t.description or "")[:150],
            }
            for t in candidates
        ]

        # 4. Call Bedrock
        raw_suggestions = bedrock_service.map_threat_to_attack_techniques(
            threat_title=threat.title,
            threat_description=threat.description or "",
            candidate_techniques=candidate_dicts,
            confidence_threshold=confidence_threshold,
        )

        if not raw_suggestions:
            logger.warning(f"Bedrock returned no ATT&CK suggestions for threat {threat_id}")
            return {"suggestions": [], "saved_count": 0, "threat_id": str(threat_id)}

        # 5. Match mitre_id → DB technique records
        mitre_id_map = {t.mitre_id: t for t in candidates}
        suggestions = []
        saved_count = 0

        already_mapped = set(
            str(tid)
            for tid in attack_data_service.get_mapped_technique_ids(db, threat_id)
        )

        for s in raw_suggestions:
            mitre_id = s.get("mitre_id", "")
            technique = mitre_id_map.get(mitre_id)
            if not technique:
                # mitre_id not in candidates – do a direct lookup
                technique = attack_data_service.get_technique_by_mitre_id(db, mitre_id)

            confidence = int(s.get("confidence_score", 0))
            suggestion = {
                "technique_id": str(technique.id) if technique else None,
                "mitre_id": mitre_id,
                "technique_name": s.get("technique_name", ""),
                "tactic_shortname": s.get("tactic_shortname", ""),
                "confidence_score": confidence,
                "mapping_rationale": s.get("mapping_rationale", ""),
            }
            suggestions.append(suggestion)

            # 6. Save if above threshold and not already mapped
            if (
                save_suggestions
                and technique
                and confidence >= confidence_threshold
                and str(technique.id) not in already_mapped
            ):
                self.add_mapping(
                    db=db,
                    threat_id=threat_id,
                    technique_id=technique.id,
                    confidence_score=confidence,
                    mapping_rationale=s.get("mapping_rationale", ""),
                    auto_mapped=True,
                )
                already_mapped.add(str(technique.id))
                saved_count += 1

        logger.info(
            f"Auto-map threat {threat_id}: {len(suggestions)} suggestions, "
            f"{saved_count} saved"
        )
        return {
            "suggestions": suggestions,
            "saved_count": saved_count,
            "threat_id": str(threat_id),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_keywords(title: str, description: Optional[str]) -> List[str]:
        """
        Simple keyword extractor.  Splits on spaces/punctuation, removes
        stopwords, returns lowercase tokens.
        """
        import re
        STOPWORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "has", "have", "had", "this", "that", "with", "for", "from",
            "and", "or", "but", "in", "on", "at", "to", "of", "by",
            "can", "could", "may", "might", "will", "would", "should",
        }
        text = f"{title} {description or ''}"
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        return list({t for t in tokens if t not in STOPWORDS})[:20]


# Module-level singleton
threat_attack_service = ThreatAttackService()
