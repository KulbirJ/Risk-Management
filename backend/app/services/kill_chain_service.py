"""
Kill chain service – generates and stores AI attack scenario kill chains.

A KillChain is a sequenced, multi-stage attack scenario for a specific threat,
based on that threat's mapped ATT&CK techniques.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.models import Threat, KillChain, KillChainStage, ThreatAttackMapping, AttackTechnique
from ..services.bedrock_service import bedrock_service
from ..services.attack_data_service import attack_data_service

logger = logging.getLogger(__name__)


class KillChainService:
    """Generates and manages attack kill chain scenarios."""

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
        Generate an AI kill chain scenario for a threat.

        Steps:
          1. Load threat + its assessment context.
          2. Load the threat's mapped ATT&CK techniques.
          3. Call Bedrock to generate the scenario.
          4. Persist KillChain + KillChainStage records.
          5. Return the persisted KillChain.
        """
        # 1. Load threat
        threat: Optional[Threat] = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            raise ValueError(f"Threat {threat_id} not found")

        # 2. Load mapped techniques
        mappings: List[ThreatAttackMapping] = (
            db.query(ThreatAttackMapping)
            .filter(ThreatAttackMapping.threat_id == threat_id)
            .all()
        )
        technique_ids = [m.technique_id for m in mappings]
        techniques: List[AttackTechnique] = []
        if technique_ids:
            techniques = (
                db.query(AttackTechnique)
                .filter(AttackTechnique.id.in_(technique_ids))
                .all()
            )

        mapped_technique_dicts = [
            {
                "mitre_id": t.mitre_id,
                "technique_name": t.name,
                "tactic_shortname": t.tactic_shortname or "",
            }
            for t in techniques
        ]

        # Build assessment context snippet
        assessment_context: Optional[str] = None
        if threat.assessment:
            a = threat.assessment
            parts = []
            if a.title:
                parts.append(f"System: {a.title}")
            if a.tech_stack:
                parts.append(f"Tech stack: {', '.join(a.tech_stack)}")
            if a.scope:
                parts.append(f"Scope: {a.scope[:200]}")
            assessment_context = "; ".join(parts) if parts else None

        # 3. Call Bedrock
        scenario_data = bedrock_service.generate_kill_chain_scenario(
            threat_title=threat.title,
            threat_description=threat.description or "",
            mapped_techniques=mapped_technique_dicts,
            assessment_context=assessment_context,
            threat_actor=threat_actor,
            include_detection_hints=include_detection_hints,
        )

        if not scenario_data:
            raise RuntimeError("AI failed to generate a kill chain scenario – check Bedrock logs")

        # 4. Persist
        kill_chain = self._persist_kill_chain(
            db=db,
            threat=threat,
            tenant_id=tenant_id,
            scenario_data=scenario_data,
            techniques=techniques,
        )

        logger.info(
            f"Kill chain '{kill_chain.scenario_name}' created for threat {threat_id} "
            f"({len(kill_chain.stages)} stages)"
        )
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
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _persist_kill_chain(
        db: Session,
        threat: Threat,
        tenant_id: UUID,
        scenario_data: dict,
        techniques: List[AttackTechnique],
    ) -> KillChain:
        """Save KillChain + KillChainStage records to the database."""
        # Build mitre_id → technique lookup for stage resolution
        technique_by_mitre: dict = {t.mitre_id: t for t in techniques}

        kill_chain = KillChain(
            threat_id=threat.id,
            tenant_id=tenant_id,
            scenario_name=scenario_data.get("scenario_name", f"Attack scenario for {threat.title}"),
            description=scenario_data.get("description"),
            threat_actor=scenario_data.get("threat_actor"),
            generated_by_ai=True,
            model_id=settings.bedrock_model_id,
        )
        db.add(kill_chain)
        db.flush()  # get kill_chain.id

        for idx, stage_data in enumerate(scenario_data.get("stages", []), start=1):
            mitre_id = stage_data.get("mitre_id") or ""
            technique = technique_by_mitre.get(mitre_id)

            # If we have a T-ID but it wasn't in mapped techniques, look it up
            if not technique and mitre_id:
                technique = (
                    db.query(AttackTechnique)
                    .filter(AttackTechnique.mitre_id == mitre_id)
                    .first()
                )

            stage = KillChainStage(
                kill_chain_id=kill_chain.id,
                technique_id=technique.id if technique else None,
                stage_number=idx,
                tactic_name=stage_data.get("tactic_name", ""),
                technique_name=stage_data.get("technique_name"),
                mitre_id=mitre_id or None,
                description=stage_data.get("description"),
                actor_behavior=stage_data.get("actor_behavior"),
                detection_hint=stage_data.get("detection_hint"),
            )
            db.add(stage)

        db.commit()
        db.refresh(kill_chain)
        return kill_chain


# Module-level singleton
kill_chain_service = KillChainService()
