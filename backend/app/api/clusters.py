"""
Phase 4 API — DBSCAN Threat Clustering endpoints.

Routes:
  POST /clusters/assessment/{id}         — Cluster threats in an assessment
  POST /clusters/tenant                  — Cluster all tenant threats
  GET  /clusters/similar/{threat_id}     — Find similar threats
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.ml.clustering_service import ClusteringService

logger = logging.getLogger(__name__)
router = APIRouter()

TENANT_ID = "67636bd3-9846-4bde-806f-aea369fc9457"

_clustering_service: Optional[ClusteringService] = None


def _clustering() -> ClusteringService:
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service


class ClusterRequest(BaseModel):
    eps: float = 0.8
    min_samples: int = 2


# ═══════════════════════════════════════════════════════════════════
# ASSESSMENT CLUSTERING
# ═══════════════════════════════════════════════════════════════════

@router.post("/assessment/{assessment_id}")
def cluster_assessment(
    assessment_id: UUID,
    body: ClusterRequest = ClusterRequest(),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Cluster enriched threats in an assessment using DBSCAN."""
    try:
        result = _clustering().cluster_assessment(
            db, UUID(tenant_id), assessment_id,
            eps=body.eps, min_samples=body.min_samples,
        )
        return result
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"ML dependencies not installed: {e}",
        )
    except Exception as e:
        logger.exception("Clustering error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# TENANT-WIDE CLUSTERING
# ═══════════════════════════════════════════════════════════════════

@router.post("/tenant")
def cluster_tenant(
    body: ClusterRequest = ClusterRequest(),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Cluster ALL enriched threats across the entire tenant."""
    try:
        result = _clustering().cluster_tenant_threats(
            db, UUID(tenant_id),
            eps=body.eps, min_samples=body.min_samples,
        )
        return result
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"ML dependencies not installed: {e}")
    except Exception as e:
        logger.exception("Tenant clustering error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# SIMILARITY SEARCH
# ═══════════════════════════════════════════════════════════════════

@router.get("/similar/{threat_id}")
def find_similar(
    threat_id: UUID,
    top_n: int = Query(default=5, ge=1, le=50),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Find the N most similar threats to the given threat."""
    result = _clustering().find_similar_threats(
        db, UUID(tenant_id), threat_id, top_n=top_n,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
