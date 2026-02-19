"""
Attack data service – read-only queries against the cached ATT&CK data.

This layer sits on top of the local AttackTactic / AttackTechnique tables
that are populated by TaxiiSyncService.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.models import AttackTactic, AttackTechnique, AttackSyncStatus, ThreatAttackMapping

logger = logging.getLogger(__name__)


class AttackDataService:
    """Read-only queries against the local ATT&CK cache."""

    # ------------------------------------------------------------------
    # Tactics
    # ------------------------------------------------------------------

    @staticmethod
    def get_all_tactics(db: Session) -> List[AttackTactic]:
        """Return all tactics ordered by MITRE ID."""
        return (
            db.query(AttackTactic)
            .order_by(AttackTactic.mitre_id)
            .all()
        )

    @staticmethod
    def get_tactic(db: Session, tactic_id: UUID) -> Optional[AttackTactic]:
        return db.query(AttackTactic).filter(AttackTactic.id == tactic_id).first()

    @staticmethod
    def get_tactic_technique_counts(db: Session) -> dict[str, int]:
        """Return a dict mapping tactic stix_id → technique count."""
        rows = (
            db.query(AttackTechnique.tactic_id, func.count(AttackTechnique.id))
            .filter(
                AttackTechnique.is_deprecated == False,
                AttackTechnique.tactic_id.isnot(None),
            )
            .group_by(AttackTechnique.tactic_id)
            .all()
        )
        return {str(tactic_id): count for tactic_id, count in rows}

    # ------------------------------------------------------------------
    # Techniques
    # ------------------------------------------------------------------

    @staticmethod
    def get_techniques_by_tactic(
        db: Session,
        tactic_id: UUID,
        include_subtechniques: bool = False,
    ) -> List[AttackTechnique]:
        """Return techniques for a given tactic."""
        q = db.query(AttackTechnique).filter(
            AttackTechnique.tactic_id == tactic_id,
            AttackTechnique.is_deprecated == False,
        )
        if not include_subtechniques:
            q = q.filter(AttackTechnique.is_subtechnique == False)
        return q.order_by(AttackTechnique.mitre_id).all()

    @staticmethod
    def get_technique(db: Session, technique_id: UUID) -> Optional[AttackTechnique]:
        return (
            db.query(AttackTechnique)
            .filter(AttackTechnique.id == technique_id)
            .first()
        )

    @staticmethod
    def get_technique_by_mitre_id(db: Session, mitre_id: str) -> Optional[AttackTechnique]:
        return (
            db.query(AttackTechnique)
            .filter(AttackTechnique.mitre_id == mitre_id)
            .first()
        )

    @staticmethod
    def search_techniques(
        db: Session,
        query: str,
        limit: int = 30,
    ) -> List[AttackTechnique]:
        """
        Case-insensitive keyword search across technique name, description,
        mitre_id, and tactic_shortname.
        """
        pattern = f"%{query.lower()}%"
        return (
            db.query(AttackTechnique)
            .filter(
                AttackTechnique.is_deprecated == False,
                or_(
                    func.lower(AttackTechnique.name).like(pattern),
                    func.lower(AttackTechnique.description).like(pattern),
                    func.lower(AttackTechnique.mitre_id).like(pattern),
                    func.lower(AttackTechnique.tactic_shortname).like(pattern),
                ),
            )
            .order_by(AttackTechnique.mitre_id)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_techniques_for_threat_keywords(
        db: Session,
        keywords: List[str],
        max_results: int = 60,
    ) -> List[AttackTechnique]:
        """
        Returns a curated shortlist of techniques relevant to the given keyword
        list.  Called before sending technique context to Bedrock so we don't
        overload the prompt.
        """
        if not keywords:
            # No keywords → return a spread of all techniques (every 10th)
            all_t = (
                db.query(AttackTechnique)
                .filter(
                    AttackTechnique.is_deprecated == False,
                    AttackTechnique.is_subtechnique == False,
                )
                .order_by(AttackTechnique.mitre_id)
                .limit(max_results)
                .all()
            )
            return all_t

        filters = []
        for kw in keywords[:8]:  # limit keyword expansion
            pattern = f"%{kw.lower()}%"
            filters.append(func.lower(AttackTechnique.name).like(pattern))
            filters.append(func.lower(AttackTechnique.description).like(pattern))

        results = (
            db.query(AttackTechnique)
            .filter(
                AttackTechnique.is_deprecated == False,
                or_(*filters),
            )
            .order_by(AttackTechnique.mitre_id)
            .limit(max_results)
            .all()
        )

        if len(results) < 10:
            # Too few matches → supplement with un-filtered top techniques
            existing_ids = {t.id for t in results}
            extras = (
                db.query(AttackTechnique)
                .filter(
                    AttackTechnique.is_deprecated == False,
                    AttackTechnique.is_subtechnique == False,
                    AttackTechnique.id.notin_(existing_ids),
                )
                .order_by(AttackTechnique.mitre_id)
                .limit(max_results - len(results))
                .all()
            )
            results = results + extras

        return results[:max_results]

    # ------------------------------------------------------------------
    # Sync status
    # ------------------------------------------------------------------

    @staticmethod
    def get_sync_status(db: Session) -> Optional[AttackSyncStatus]:
        return db.query(AttackSyncStatus).first()

    @staticmethod
    def is_populated(db: Session) -> bool:
        """Return True if the local cache has at least some tactics."""
        return db.query(func.count(AttackTactic.id)).scalar() > 0

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_mapped_technique_ids(db: Session, threat_id: UUID) -> List[UUID]:
        rows = (
            db.query(ThreatAttackMapping.technique_id)
            .filter(ThreatAttackMapping.threat_id == threat_id)
            .all()
        )
        return [r[0] for r in rows]


attack_data_service = AttackDataService()
