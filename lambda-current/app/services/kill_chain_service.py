"""
Kill chain service – deterministic ATT&CK kill chain builder.

Architecture:
  1. Load threat's mapped techniques from DB (guaranteed valid ATT&CK T-IDs).
  2. Group by tactic, sort by canonical phase_order.
  3. Select best technique per tactic (highest confidence score).
  4. Use STIX x_mitre_detection text as base detection_hint — zero hallucination.
  5. Call Bedrock ONCE for narrative enrichment only (scenario_name, description,
     per-stage actor_behavior). LLM writes prose; it never selects techniques.
  6. Persist KillChain + KillChainStage records with all technique_id FKs populated.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.models import (
    ATTACK_TACTIC_ORDER,
    AttackTechnique,
    KillChain,
    KillChainStage,
    Threat,
    ThreatAttackMapping,
)
from ..services.bedrock_service import bedrock_service

logger = logging.getLogger(__name__)

# Fallback order when tactic has no phase_order stored yet
_FALLBACK_ORDER = 99


class KillChainService:
    """Builds and manages deterministic ATT&CK kill chain scenarios."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @staticmethod
    def get_kill_chains(db: Session, threat_id: UUID) -> List[KillChain]:
        """Return all kill chains for a threat, newest first."""
        return (
            db.query(KillChain)
            .filter(KillChain.threat_id == threat_id)
            .order_by(KillChain.created_at.desc())
            .all()
        )

    @staticmethod
    def get_kill_chain(db: Session, kill_chain_id: UUID) -> Optional[KillChain]:
        return db.query(KillChain).filter(KillChain.id == kill_chain_id).first()

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def generate(
        self,
        db: Session,
        threat_id: UUID,
        tenant_id: UUID,
        threat_actor: Optional[str] = None,
        include_detection_hints: bool = True,
    ) -> KillChain:
        """
        Build a deterministic ATT&CK kill chain for a threat.

        Steps:
          1. Load threat + assessment context.
          2. Load mapped ATT&CK techniques (valid IDs from DB, never hallucinated).
          3. Group by tactic, sort by canonical phase_order.
          4. Select highest-confidence technique per tactic.
          5. Use STIX x_mitre_detection as base detection_hint.
          6. Call Bedrock once for narrative enrichment only.
          7. Persist and return.
        """
        # 1. Load threat
        threat: Optional[Threat] = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            raise ValueError(f"Threat {threat_id} not found")

        # 2. Load mapped techniques with confidence scores
        mappings: List[ThreatAttackMapping] = (
            db.query(ThreatAttackMapping)
            .filter(ThreatAttackMapping.threat_id == threat_id)
            .all()
        )
        technique_ids = [m.technique_id for m in mappings]
        confidence_by_id: Dict[UUID, int] = {m.technique_id: m.confidence_score for m in mappings}

        if not technique_ids:
            raise ValueError(
                "No ATT&CK techniques mapped to this threat. "
                "Use 'Manage Mappings → AI Suggest' to map techniques first."
            )

        techniques: List[AttackTechnique] = (
            db.query(AttackTechnique)
            .filter(AttackTechnique.id.in_(technique_ids))
            .all()
        )

        # 3. Group by tactic, resolve phase_order, sort canonically
        tactic_groups: Dict[str, List[AttackTechnique]] = defaultdict(list)
        for tech in techniques:
            tactic_key = tech.tactic_shortname or "unknown"
            tactic_groups[tactic_key].append(tech)

        sorted_tactics = sorted(
            tactic_groups.keys(),
            key=lambda s: ATTACK_TACTIC_ORDER.get(s, _FALLBACK_ORDER),
        )

        # 4. Select best technique per tactic (highest confidence score)
        selected: List[Dict[str, Any]] = []
        for tactic_shortname in sorted_tactics:
            techs = tactic_groups[tactic_shortname]
            best = max(techs, key=lambda t: confidence_by_id.get(t.id, 0))
            selected.append({
                "tactic_shortname": tactic_shortname,
                "tactic_name": self._shortname_to_display(tactic_shortname),
                "technique": best,
                "confidence": confidence_by_id.get(best.id, 70),
            })

        logger.info(
            f"Kill chain for '{threat.title}': "
            f"{len(selected)} stages from {len(techniques)} mapped techniques "
            f"(0 hallucinated T-IDs)"
        )

        # 5. Build assessment context string
        assessment_context: Optional[str] = None
        if threat.assessment:
            a = threat.assessment
            parts = []
            if a.title:
                parts.append(f"System: {a.title}")
            if a.tech_stack:
                parts.append(f"Tech: {', '.join(a.tech_stack[:3])}")
            if a.scope:
                parts.append(f"Scope: {a.scope[:150]}")
            assessment_context = "; ".join(parts) if parts else None

        # 6. AI enrichment: narrative only (not technique selection)
        enrichment = self._enrich_with_ai(
            threat_title=threat.title,
            threat_description=threat.description or "",
            stages=selected,
            assessment_context=assessment_context,
            threat_actor=threat_actor,
        )

        # 7. Persist
        kill_chain = self._persist(
            db=db,
            threat=threat,
            tenant_id=tenant_id,
            stages=selected,
            enrichment=enrichment,
            threat_actor=threat_actor,
            include_detection_hints=include_detection_hints,
        )

        logger.info(f"Kill chain '{kill_chain.scenario_name}' saved ({len(kill_chain.stages)} stages)")
        return kill_chain

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    @staticmethod
    def delete_kill_chain(db: Session, kill_chain_id: UUID, tenant_id: UUID) -> bool:
        kc = (
            db.query(KillChain)
            .filter(KillChain.id == kill_chain_id, KillChain.tenant_id == tenant_id)
            .first()
        )
        if not kc:
            return False
        db.delete(kc)
        db.commit()
        return True

    # ------------------------------------------------------------------
    # Private — AI enrichment (narrative only)
    # ------------------------------------------------------------------

    def _enrich_with_ai(
        self,
        threat_title: str,
        threat_description: str,
        stages: List[Dict[str, Any]],
        assessment_context: Optional[str],
        threat_actor: Optional[str],
    ) -> Dict[str, Any]:
        """
        Call Bedrock with a narrow, grounded prompt to write:
          - scenario_name
          - description (1-2 sentence overview)
          - actor_behavior per stage (concrete, observable adversary action)

        Techniques and T-IDs are NOT determined by the model — they come from the DB.
        On any failure, deterministic fallback text is returned.
        """
        if not bedrock_service.enabled or not bedrock_service.client:
            return self._fallback_enrichment(threat_title, stages)

        stage_list = "\n".join(
            f"  Stage {i+1}: [{s['technique'].mitre_id}] {s['technique'].name} "
            f"(tactic: {s['tactic_name']})"
            for i, s in enumerate(stages)
        )
        actor_hint = f"The adversary is: {threat_actor}." if threat_actor else "Assume a motivated, skilled adversary."
        context_hint = f"\nContext: {assessment_context}" if assessment_context else ""

        system_prompt = (
            "You are a cybersecurity analyst writing briefing content for a threat risk "
            "assessment platform. Your output helps security teams understand and defend "
            "against threats. Write clear, professional, defender-focused content."
        )

        user_prompt = f"""Threat being assessed: {threat_title}
Threat description: {threat_description or "No description provided"}{context_hint}
{actor_hint}

The following ATT&CK technique stages have been identified for this threat (do NOT change them):
{stage_list}

Provide:
1. A scenario_name (5-10 words summarizing the threat progression)
2. A description (1-2 sentences explaining how this threat typically unfolds)
3. For EACH stage, a single sentence describing a specific, observable adversary
   behavior that defenders should monitor (be concrete and actionable)

Return valid JSON only:
{{
  "scenario_name": "...",
  "description": "...",
  "actor_behaviors": [
    {{"stage_number": 1, "actor_behavior": "..."}},
    {{"stage_number": 2, "actor_behavior": "..."}}
  ]
}}"""

        try:
            raw = bedrock_service.invoke_model(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.3,
            )
            if raw:
                data = bedrock_service._extract_json_object(raw)
                if data and "scenario_name" in data:
                    logger.info("AI narrative enrichment succeeded")
                    return data
        except Exception as exc:
            logger.warning(f"AI enrichment failed, using deterministic fallback: {exc}")

        return self._fallback_enrichment(threat_title, stages)

    @staticmethod
    def _fallback_enrichment(threat_title: str, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic fallback when Bedrock is unavailable or fails."""
        return {
            "scenario_name": f"Threat progression: {threat_title[:60]}",
            "description": (
                f"Multi-stage threat scenario for '{threat_title}' based on "
                f"{len(stages)} ATT&CK tactic phase(s)."
            ),
            "actor_behaviors": [
                {"stage_number": i + 1, "actor_behavior": None}
                for i in range(len(stages))
            ],
        }

    # ------------------------------------------------------------------
    # Private — persistence
    # ------------------------------------------------------------------

    def _persist(
        self,
        db: Session,
        threat: Threat,
        tenant_id: UUID,
        stages: List[Dict[str, Any]],
        enrichment: Dict[str, Any],
        threat_actor: Optional[str],
        include_detection_hints: bool,
    ) -> KillChain:
        # Build actor_behavior lookup from AI enrichment
        behavior_map: Dict[int, str] = {}
        for item in enrichment.get("actor_behaviors", []):
            sn = item.get("stage_number")
            ab = item.get("actor_behavior")
            if sn is not None and ab:
                behavior_map[sn] = ab

        kill_chain = KillChain(
            threat_id=threat.id,
            tenant_id=tenant_id,
            scenario_name=enrichment.get(
                "scenario_name", f"Threat progression: {threat.title[:60]}"
            ),
            description=enrichment.get("description"),
            threat_actor=threat_actor,
            generated_by_ai=True,
            model_id=settings.bedrock_model_id if bedrock_service.enabled else "deterministic",
            status="complete",
        )
        db.add(kill_chain)
        db.flush()

        for idx, stage_info in enumerate(stages, start=1):
            tech: AttackTechnique = stage_info["technique"]
            tactic_name: str = stage_info["tactic_name"]

            # Use STIX x_mitre_detection as the authoritative detection_hint
            detection_hint: Optional[str] = None
            if include_detection_hints:
                raw_detection = (tech.detection_text or "").strip()
                detection_hint = raw_detection or (
                    f"Monitor for activity related to {tech.name} ({tech.mitre_id})."
                )

            stage = KillChainStage(
                kill_chain_id=kill_chain.id,
                technique_id=tech.id,           # always a valid FK — never NULL
                stage_number=idx,
                tactic_name=tactic_name,
                technique_name=tech.name,
                mitre_id=tech.mitre_id,
                description=tech.description,
                actor_behavior=behavior_map.get(idx),
                detection_hint=detection_hint,
            )
            db.add(stage)

        db.commit()
        db.refresh(kill_chain)
        return kill_chain

    # ------------------------------------------------------------------
    # Private — helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shortname_to_display(shortname: str) -> str:
        """Convert 'initial-access' → 'Initial Access'."""
        return shortname.replace("-", " ").title()


# Module-level singleton
kill_chain_service = KillChainService()

