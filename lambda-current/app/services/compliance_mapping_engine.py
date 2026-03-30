"""Intelligent compliance control auto-mapping engine.

Hybrid approach:
  1. Static layer — looks up ThreatControlDefault table for known catalogue keys.
  2. AI layer   — calls Bedrock to suggest mappings for controls not covered by static.
  3. Orchestrator — runs both, deduplicates, saves ComplianceMapping records.
"""
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.models import (
    ComplianceControl,
    ComplianceFramework,
    ComplianceMapping,
    Threat,
    ThreatControlDefault,
    AuditLog,
)
from .bedrock_service import bedrock_service

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 70


# ═══ Static Mapping Engine ══════════════════════════════════════════════════

def _resolve_control_id(
    db: Session,
    tenant_id: str,
    framework_id: UUID,
    control_id_ref: str,
) -> Optional[UUID]:
    """Look up a ComplianceControl UUID by its human-readable control_id (e.g. 'AC-2')."""
    row = db.execute(
        select(ComplianceControl.id).where(
            ComplianceControl.tenant_id == tenant_id,
            ComplianceControl.framework_id == framework_id,
            ComplianceControl.control_id == control_id_ref,
        )
    ).scalar_one_or_none()
    return row


def static_map(
    db: Session,
    tenant_id: str,
    threat: Threat,
    framework: ComplianceFramework,
) -> list[dict]:
    """Return static mapping suggestions for a threat against a framework.

    Returns list of dicts: {control_uuid, control_id_ref, confidence, source}
    """
    catalogue_key = threat.catalogue_key
    if not catalogue_key:
        return []

    # Prefer tenant-specific defaults, fall back to global (tenant_id IS NULL)
    defaults = db.execute(
        select(ThreatControlDefault).where(
            ThreatControlDefault.framework_key == framework.key,
            ThreatControlDefault.catalogue_key == catalogue_key,
            (ThreatControlDefault.tenant_id == tenant_id)
            | (ThreatControlDefault.tenant_id == None),  # noqa: E711
        )
    ).scalars().all()

    results = []
    for d in defaults:
        ctrl_uuid = _resolve_control_id(db, tenant_id, framework.id, d.control_id_ref)
        if ctrl_uuid:
            results.append({
                "control_uuid": ctrl_uuid,
                "control_id_ref": d.control_id_ref,
                "confidence": d.confidence,
                "source": "auto_static",
            })
    return results


# ═══ Bedrock AI Fallback Engine ═════════════════════════════════════════════

def ai_map(
    db: Session,
    tenant_id: str,
    threat: Threat,
    framework: ComplianceFramework,
    exclude_control_ids: set[UUID] | None = None,
) -> list[dict]:
    """Call Bedrock to suggest compliance control mappings for a threat.

    Sends all controls in the framework; filters out controls already mapped by static.
    Returns list of dicts: {control_uuid, control_id_ref, confidence, source}
    """
    if not bedrock_service.enabled or not bedrock_service.client:
        logger.info("Bedrock disabled — skipping AI compliance mapping")
        return []

    exclude_control_ids = exclude_control_ids or set()

    # Fetch all controls for the framework
    controls = db.execute(
        select(ComplianceControl).where(
            ComplianceControl.tenant_id == tenant_id,
            ComplianceControl.framework_id == framework.id,
        )
    ).scalars().all()

    # Build candidate list (exclude already-mapped)
    candidates = [
        c for c in controls if c.id not in exclude_control_ids
    ]
    if not candidates:
        return []

    controls_context = "\n".join(
        f"- [{c.control_id}] {c.title} (family: {c.family or 'General'})"
        for c in candidates
    )

    system_prompt = (
        "You are a cybersecurity compliance mapping expert.\n"
        "Given a threat, identify the most relevant compliance controls from the provided list.\n\n"
        "Return valid JSON only — no markdown, no extra text:\n"
        '{\n  "mappings": [\n    {\n'
        '      "control_id": "AC-2",\n'
        '      "confidence_score": 85,\n'
        '      "rationale": "Brief reason"\n'
        "    }\n  ]\n}\n\n"
        "Rules:\n"
        "- Return 2-8 mappings maximum\n"
        "- confidence_score must be an integer 0-100\n"
        "- Only include controls from the provided list\n"
        f"- Only include mappings with confidence >= {CONFIDENCE_THRESHOLD}\n"
        "- Return ONLY valid JSON"
    )

    user_prompt = (
        f"Threat: {threat.title}\n"
        f"Category: {threat.catalogue_key or 'Unknown'}\n"
        f"Description: {threat.description or 'No description provided'}\n\n"
        f"Framework: {framework.name} ({framework.key})\n\n"
        f"Available controls:\n{controls_context}\n\n"
        "Map this threat to the most relevant controls above."
    )

    try:
        raw = bedrock_service.invoke_model(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.2,
        )
        if not raw:
            return []

        data = bedrock_service._extract_json_object(raw)
        if not data:
            return []

        # Build control_id → UUID lookup
        ctrl_lookup = {c.control_id: c.id for c in candidates}

        results = []
        for m in data.get("mappings", []):
            ctrl_ref = m.get("control_id", "")
            confidence = int(m.get("confidence_score", 0))
            ctrl_uuid = ctrl_lookup.get(ctrl_ref)
            if ctrl_uuid and confidence >= CONFIDENCE_THRESHOLD:
                results.append({
                    "control_uuid": ctrl_uuid,
                    "control_id_ref": ctrl_ref,
                    "confidence": confidence,
                    "source": "ai_suggested",
                })

        logger.info(
            f"Bedrock compliance mapping for threat '{threat.title}': "
            f"{len(results)} suggestions"
        )
        return results

    except Exception as exc:
        logger.error(f"Bedrock compliance mapping failed: {exc}")
        return []


# ═══ Combined Orchestrator ══════════════════════════════════════════════════

def run_auto_mapping(
    db: Session,
    tenant_id: str,
    user_id: str,
    threat_id: UUID,
    framework_key: str,
    assessment_id: UUID | None = None,
) -> dict:
    """Run the full auto-mapping pipeline for one threat against one framework.

    1. Look up threat + framework
    2. Run static mapping
    3. Run Bedrock AI for remaining controls
    4. Deduplicate & save ComplianceMapping records
    5. Return summary

    Returns: {threat_id, framework_key, static_count, ai_count, saved_count, skipped}
    """
    # Load threat
    threat = db.execute(
        select(Threat).where(Threat.id == threat_id, Threat.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not threat:
        raise ValueError(f"Threat {threat_id} not found")

    # Load framework
    framework = db.execute(
        select(ComplianceFramework).where(
            ComplianceFramework.tenant_id == tenant_id,
            ComplianceFramework.key == framework_key,
        )
    ).scalar_one_or_none()
    if not framework:
        raise ValueError(f"Framework '{framework_key}' not found for tenant")

    # Use assessment from threat if not provided
    if not assessment_id:
        assessment_id = threat.assessment_id

    # Already-mapped control IDs for this threat
    existing_mappings = db.execute(
        select(ComplianceMapping.control_id).where(
            ComplianceMapping.tenant_id == tenant_id,
            ComplianceMapping.threat_id == threat_id,
        )
    ).scalars().all()
    already_mapped = set(existing_mappings)

    # 1. Static mapping
    static_suggestions = static_map(db, tenant_id, threat, framework)
    static_ctrl_uuids = {s["control_uuid"] for s in static_suggestions}

    # 2. AI fallback for unmapped controls
    ai_suggestions = ai_map(
        db, tenant_id, threat, framework,
        exclude_control_ids=static_ctrl_uuids | already_mapped,
    )

    # 3. Merge, deduplicate, save
    all_suggestions = static_suggestions + ai_suggestions
    saved_count = 0
    skipped = 0

    for s in all_suggestions:
        ctrl_uuid = s["control_uuid"]
        if ctrl_uuid in already_mapped:
            skipped += 1
            continue

        mapping = ComplianceMapping(
            tenant_id=tenant_id,
            control_id=ctrl_uuid,
            threat_id=threat_id,
            assessment_id=assessment_id,
            status="not_assessed",
            mapped_by=s["source"],
            confidence_score=s["confidence"],
        )
        db.add(mapping)
        already_mapped.add(ctrl_uuid)
        saved_count += 1

    db.flush()

    # Audit log
    try:
        db.add(AuditLog(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            action_type="auto_map_compliance",
            resource_type="threat",
            resource_id=str(threat_id),
            changes={
                "framework_key": framework_key,
                "static_count": len(static_suggestions),
                "ai_count": len(ai_suggestions),
                "saved_count": saved_count,
            },
        ))
    except Exception:
        logger.warning("Failed to write audit log for auto_map_compliance")

    db.commit()

    result = {
        "threat_id": str(threat_id),
        "framework_key": framework_key,
        "static_count": len(static_suggestions),
        "ai_count": len(ai_suggestions),
        "saved_count": saved_count,
        "skipped": skipped,
    }
    logger.info(f"Auto-mapping complete: {result}")
    return result
