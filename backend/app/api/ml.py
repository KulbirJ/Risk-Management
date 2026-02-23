"""
Phase 2 API — ML Scoring, Survival Analysis & Explainability endpoints.

Routes:
  POST /ml/train             — Train / re-train the scoring model
  POST /ml/score             — Score a batch of threats
  GET  /ml/score/{threat_id} — Score a single threat
  GET  /ml/explain/{threat_id} — Feature-level explanation
  GET  /ml/model-info        — Current model metadata
  GET  /ml/bias-report       — Sector-level bias monitoring
  POST /ml/survival          — Estimate persistence for active risks
  GET  /ml/survival/curve    — Survival curve for the tenant
"""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.ml.scoring_service import MLScoringService
from ..services.ml.survival_service import SurvivalAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Singleton-ish service instances (re-created per cold start) ──
_scoring_service: Optional[MLScoringService] = None
_survival_service: Optional[SurvivalAnalysisService] = None

TENANT_ID = "67636bd3-9846-4bde-806f-aea369fc9457"  # default tenant


def _scoring() -> MLScoringService:
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = MLScoringService()
    return _scoring_service


def _survival() -> SurvivalAnalysisService:
    global _survival_service
    if _survival_service is None:
        _survival_service = SurvivalAnalysisService()
    return _survival_service


# ═══════════════════════════════════════════════════════════════════
# Request / Response schemas
# ═══════════════════════════════════════════════════════════════════

class TrainRequest(BaseModel):
    algorithm: str = "random_forest"  # or "gradient_boosting"
    min_samples: int = 10


class ScoreBatchRequest(BaseModel):
    assessment_id: Optional[UUID] = None
    threat_ids: Optional[List[UUID]] = None
    persist: bool = True


class SurvivalEstimateRequest(BaseModel):
    active_risk_id: Optional[UUID] = None
    assessment_id: Optional[UUID] = None
    persist: bool = True


# ═══════════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════════

@router.post("/train")
def train_model(
    body: TrainRequest,
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Train or re-train the ML scoring model on enriched threats."""
    try:
        result = _scoring().train(
            db,
            UUID(tenant_id),
            algorithm=body.algorithm,
            min_samples=body.min_samples,
        )
        return result
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"ML dependencies not installed: {e}. Install scikit-learn.",
        )
    except Exception as e:
        logger.exception("ML training error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════

@router.post("/score")
def score_batch(
    body: ScoreBatchRequest,
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Score a batch of threats (by assessment or explicit IDs)."""
    try:
        result = _scoring().score_batch(
            db,
            UUID(tenant_id),
            threat_ids=body.threat_ids,
            assessment_id=body.assessment_id,
            persist=body.persist,
        )
        return result
    except Exception as e:
        logger.exception("ML batch scoring error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/score/{threat_id}")
def score_single(
    threat_id: UUID,
    persist: bool = Query(default=True),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Score a single threat."""
    result = _scoring().score_threat(
        db, UUID(tenant_id), threat_id, persist=persist,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ═══════════════════════════════════════════════════════════════════
# EXPLAINABILITY
# ═══════════════════════════════════════════════════════════════════

@router.get("/explain/{threat_id}")
def explain_score(
    threat_id: UUID,
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Return per-feature explanation for a threat's score."""
    result = _scoring().explain(db, UUID(tenant_id), threat_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ═══════════════════════════════════════════════════════════════════
# MODEL INFO & BIAS
# ═══════════════════════════════════════════════════════════════════

@router.get("/model-info")
def model_info():
    """Return current model metadata."""
    return _scoring().model_info


@router.get("/bias-report")
def bias_report(
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Generate bias monitoring report (score distribution per sector)."""
    return _scoring().bias_report(db, UUID(tenant_id))


# ═══════════════════════════════════════════════════════════════════
# SURVIVAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════

@router.post("/survival")
def estimate_survival(
    body: SurvivalEstimateRequest,
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Estimate persistence (days) for active risks."""
    result = _survival().estimate_persistence(
        db,
        UUID(tenant_id),
        active_risk_id=body.active_risk_id,
        assessment_id=body.assessment_id,
        persist=body.persist,
    )
    return result


@router.get("/survival/curve")
def survival_curve(
    sector: Optional[str] = Query(default=None),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Return survival curve (time → probability) for the tenant's risks."""
    return _survival().survival_curve(db, UUID(tenant_id), sector=sector)
