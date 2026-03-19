"""
Full Assessment Run Service
===========================
Orchestrates the complete risk-assessment pipeline in a single background job:

  Step 1  AI Risk Enrichment          — extract threats via Bedrock
  Step 2  Intel Threat Enrichment     — CVE / ATT&CK group / sector-frequency
  Step 3  ML Risk Scoring             — predict likelihood with trained model
  Step 4  Threat Clustering           — DBSCAN cluster grouping
  Step 5  ATT&CK Auto-Mapping         — AI-suggest + save technique mappings
  Step 6  Attack Scenarios            — generate kill-chain narratives

Progress is persisted in IntelligenceJob.results so the frontend can poll it.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import traceback
from datetime import datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Step definitions  (name, display-label, target % when done)
# ─────────────────────────────────────────────────────────────────
FULL_RUN_STEPS = [
    ("ai_enrichment",  "AI Risk Enrichment",             17),
    ("intel_threats",  "Intel Threat Enrichment",        33),
    ("ml_scoring",     "ML Risk Scoring",                50),
    ("clustering",     "Threat Clustering",              65),
    ("attack_mapping", "ATT\u0026CK Auto-Mapping",       82),
    ("kill_chains",    "Attack Scenarios (Kill Chains)", 97),
]


def build_initial_results() -> dict:
    """Return the initial results dict that goes into IntelligenceJob.results."""
    return {
        "steps": [
            {
                "name": name,
                "label": label,
                "status": "pending",
                "message": "",
                "percent_end": pct,
            }
            for name, label, pct in FULL_RUN_STEPS
        ],
        "percent_complete": 0,
    }


# ─────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────

def _set_step(results: dict, step_name: str, status: str, message: str, percent: int | None = None) -> None:
    for s in results["steps"]:
        if s["name"] == step_name:
            s["status"] = status
            s["message"] = message
            break
    if percent is not None:
        results["percent_complete"] = percent


def _commit_results(db: Any, job: Any, results: dict) -> None:
    """
    Flush results to DB.

    Rolls back any open/failed transaction first so a preceding exception
    (e.g. an FK-violation inside a step's DB work) cannot permanently
    invalidate the session and block subsequent progress writes.
    """
    try:
        db.rollback()  # no-op if session is clean; recovers an invalid tx if not
    except Exception:
        pass
    job.results = {
        "steps": [dict(s) for s in results["steps"]],
        "percent_complete": results["percent_complete"],
    }
    db.commit()


# ─────────────────────────────────────────────────────────────────
# Pipeline runner
# ─────────────────────────────────────────────────────────────────

def run_full_assessment_pipeline(
    db: Any,
    job_id: str,
    assessment_id: str,
    tenant_id: str,
    user_id: str,
) -> dict:
    """
    Run the full pipeline synchronously.  Intended to be called from:
      - The Lambda handler  (_handle_full_assessment_run)
      - A background thread (fallback when Lambda invocation fails)

    Returns {"status": "completed"|"failed", "job_id": job_id}
    """
    from ..models.models import IntelligenceJob, Threat, ThreatAttackMapping
    from ..services.intelligence_service import intelligence_service

    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.INFO)
    _logger.info("[FULL_RUN] Starting pipeline job=%s assessment=%s", job_id, assessment_id)

    job = db.query(IntelligenceJob).filter(IntelligenceJob.id == job_id).first()
    if not job:
        _logger.error("[FULL_RUN] Job %s not found", job_id)
        return {"status": "error", "message": "Job not found"}

    try:
        return _run_pipeline_body(db, job, job_id, assessment_id, tenant_id, user_id, _logger)
    except Exception as exc:
        _logger.error("[FULL_RUN] Unhandled exception for job=%s: %s\n%s",
                      job_id, exc, traceback.format_exc())
        try:
            db.rollback()  # recover session from any invalid transaction state
            job.status = "failed"
            job.error_message = f"Unexpected pipeline error: {str(exc)[:500]}"
            job.completed_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass
        return {"status": "failed", "job_id": job_id}


def _run_pipeline_body(db, job, job_id, assessment_id, tenant_id, user_id, _logger):
    """Inner pipeline body — separated so the caller can wrap it in a clean try/except."""
    from ..models.models import IntelligenceJob, Threat, ThreatAttackMapping  # noqa: F401
    from ..services.intelligence_service import intelligence_service

    # Mark job running
    job.status = "running"
    job.started_at = datetime.utcnow()
    results = build_initial_results()
    _commit_results(db, job, results)

    tid = UUID(tenant_id)
    aid = UUID(assessment_id)

    # ── Step 1: AI Enrichment ─────────────────────────────────────
    # Each Bedrock call is capped at 60 s (bedrock_service).  Give the whole
    # step 90 s — enough for 1-2 calls — so a Bedrock outage fails within
    # 90 s rather than hanging for 5 minutes.
    _AI_ENRICHMENT_STEP_TIMEOUT = 90  # seconds
    _set_step(results, "ai_enrichment", "running", "Calling Bedrock for threat analysis…")
    _commit_results(db, job, results)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
            _fut = _pool.submit(
                intelligence_service.enrich_assessment,
                db=db,
                assessment_id=assessment_id,
                tenant_id=tenant_id,
                job_id=job_id,
            )
            try:
                ai_result = _fut.result(timeout=_AI_ENRICHMENT_STEP_TIMEOUT)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"AI enrichment timed out after {_AI_ENRICHMENT_STEP_TIMEOUT // 60} minutes"
                )
        n_threats = ai_result.get("threats_mapped", 0)
        _set_step(results, "ai_enrichment", "completed",
                  f"{n_threats} threat{'s' if n_threats != 1 else ''} identified", 17)
        _logger.info("[FULL_RUN] Step ai_enrichment done: %s threats", n_threats)
    except Exception as exc:
        _set_step(results, "ai_enrichment", "failed", str(exc)[:200], 17)
        _logger.warning("[FULL_RUN] ai_enrichment failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Step 2: Intel Threat Enrichment ───────────────────────────
    _set_step(results, "intel_threats", "running", "Fetching CVE / ATT&CK group data…")
    _commit_results(db, job, results)
    try:
        from .intel.enrichment_orchestrator import EnrichmentOrchestrator
        orchestrator = EnrichmentOrchestrator()
        intel_result = asyncio.run(
            orchestrator.enrich_threats(
                db=db,
                tenant_id=tid,
                threat_ids=None,
                assessment_id=aid,
                force_refresh=False,
            )
        )
        n_enriched = intel_result.get("enriched_count", 0)
        _set_step(results, "intel_threats", "completed",
                  f"{n_enriched} threat{'s' if n_enriched != 1 else ''} enriched with CVE / ATT&CK data", 33)
        _logger.info("[FULL_RUN] Step intel_threats done: %s enriched", n_enriched)
    except Exception as exc:
        _set_step(results, "intel_threats", "failed", str(exc)[:200], 33)
        _logger.warning("[FULL_RUN] intel_threats failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Step 3: ML Scoring ────────────────────────────────────────
    _set_step(results, "ml_scoring", "running", "Running ML likelihood model…")
    _commit_results(db, job, results)
    try:
        from .ml.scoring_service import MLScoringService
        scorer = MLScoringService()
        ml_result = scorer.score_batch(
            db, tid, assessment_id=aid, persist=True
        )
        n_scored = ml_result.get("scored", 0)
        _set_step(results, "ml_scoring", "completed",
                  f"{n_scored} threat{'s' if n_scored != 1 else ''} scored", 50)
        _logger.info("[FULL_RUN] Step ml_scoring done: %s scored", n_scored)
    except Exception as exc:
        _set_step(results, "ml_scoring", "failed", str(exc)[:200], 50)
        _logger.warning("[FULL_RUN] ml_scoring failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Step 4: Clustering ────────────────────────────────────────
    _set_step(results, "clustering", "running", "Grouping threats with DBSCAN…")
    _commit_results(db, job, results)
    try:
        from .ml.clustering_service import ClusteringService
        clusterer = ClusteringService()
        cl_result = clusterer.cluster_assessment(db, tid, aid)
        n_clusters = cl_result.get("n_clusters", 0)
        _set_step(results, "clustering", "completed",
                  f"{n_clusters} cluster{'s' if n_clusters != 1 else ''} identified", 65)
        _logger.info("[FULL_RUN] Step clustering done: %s clusters", n_clusters)
    except Exception as exc:
        _set_step(results, "clustering", "failed", str(exc)[:200], 65)
        _logger.warning("[FULL_RUN] clustering failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Step 5: ATT&CK Auto-Mapping ───────────────────────────────
    _set_step(results, "attack_mapping", "running", "Auto-mapping threats to ATT&CK techniques…")
    _commit_results(db, job, results)
    try:
        from .threat_attack_service import threat_attack_service
        threat_rows = db.query(Threat).filter(
            Threat.assessment_id == aid,
            Threat.tenant_id == tid,
        ).all()
        mapped = 0
        for t in threat_rows:
            try:
                threat_attack_service.auto_map_threat(
                    db=db,
                    threat_id=t.id,
                    tenant_id=tid,
                    save_suggestions=True,
                    confidence_threshold=0.6,
                )
                mapped += 1
            except Exception as exc_t:
                _logger.debug("[FULL_RUN] auto_map %s: %s", t.id, exc_t)
        total = len(threat_rows)
        _set_step(results, "attack_mapping", "completed",
                  f"{mapped}/{total} threat{'s' if total != 1 else ''} mapped to ATT&CK techniques", 82)
        _logger.info("[FULL_RUN] Step attack_mapping done: %s/%s", mapped, total)
    except Exception as exc:
        _set_step(results, "attack_mapping", "failed", str(exc)[:200], 82)
        _logger.warning("[FULL_RUN] attack_mapping failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Step 6: Kill Chain (Attack Scenarios) ─────────────────────
    _set_step(results, "kill_chains", "running", "Generating attack scenario narratives…")
    _commit_results(db, job, results)
    try:
        from .kill_chain_service import kill_chain_service
        threat_rows = db.query(Threat).filter(
            Threat.assessment_id == aid,
            Threat.tenant_id == tid,
        ).all()
        generated = 0
        for t in threat_rows:
            has_mappings = db.query(ThreatAttackMapping).filter(
                ThreatAttackMapping.threat_id == t.id
            ).first()
            if has_mappings:
                try:
                    kill_chain_service.generate(
                        db=db,
                        threat_id=t.id,
                        tenant_id=tid,
                    )
                    generated += 1
                except Exception as exc_t:
                    _logger.debug("[FULL_RUN] kill_chain %s: %s", t.id, exc_t)
        _set_step(results, "kill_chains", "completed",
                  f"{generated} attack scenario{'s' if generated != 1 else ''} generated", 97)
        _logger.info("[FULL_RUN] Step kill_chains done: %s generated", generated)
    except Exception as exc:
        _set_step(results, "kill_chains", "failed", str(exc)[:200], 97)
        _logger.warning("[FULL_RUN] kill_chains failed (continuing): %s", exc)
    _commit_results(db, job, results)

    # ── Finalize ──────────────────────────────────────────────────
    results["percent_complete"] = 100
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    _commit_results(db, job, results)
    _logger.info("[FULL_RUN] Pipeline completed for job=%s", job_id)
    return {"status": "completed", "job_id": job_id}
