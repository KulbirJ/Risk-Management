"""
Phase 3 API — Graph-Based Threat Mapping & PageRank endpoints.

Routes:
  GET /graph/assessment/{id}             — Full graph for an assessment
  GET /graph/threat/{threat_id}/neighbourhood — N-hop neighbourhood
  GET /graph/assessment/{id}/critical    — Top-N critical nodes
  GET /graph/assessment/{id}/path        — Shortest path between two nodes
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.ml.graph_service import GraphService

logger = logging.getLogger(__name__)
router = APIRouter()

TENANT_ID = "67636bd3-9846-4bde-806f-aea369fc9457"

_graph_service: Optional[GraphService] = None


def _graph() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service


# ═══════════════════════════════════════════════════════════════════
# ASSESSMENT GRAPH
# ═══════════════════════════════════════════════════════════════════

@router.get("/assessment/{assessment_id}")
def get_assessment_graph(
    assessment_id: UUID,
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Build and return the full knowledge graph for an assessment."""
    try:
        result = _graph().build_assessment_graph(db, UUID(tenant_id), assessment_id)
        return result
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="networkx is not installed. Install it to use graph features.",
        )
    except Exception as e:
        logger.exception("Graph build error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# NEIGHBOURHOOD
# ═══════════════════════════════════════════════════════════════════

@router.get("/threat/{threat_id}/neighbourhood")
def get_threat_neighbourhood(
    threat_id: UUID,
    depth: int = Query(default=2, ge=1, le=5),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Return the N-hop neighbourhood around a threat node."""
    try:
        result = _graph().threat_neighbourhood(db, UUID(tenant_id), threat_id, depth=depth)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=501, detail="networkx not installed")
    except Exception as e:
        logger.exception("Neighbourhood query error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# CRITICAL NODES
# ═══════════════════════════════════════════════════════════════════

@router.get("/assessment/{assessment_id}/critical")
def get_critical_nodes(
    assessment_id: UUID,
    top_n: int = Query(default=10, ge=1, le=50),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Identify the most critical nodes by PageRank + betweenness."""
    try:
        result = _graph().critical_nodes(db, UUID(tenant_id), assessment_id, top_n=top_n)
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="networkx not installed")
    except Exception as e:
        logger.exception("Critical nodes error")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# PATH ANALYSIS
# ═══════════════════════════════════════════════════════════════════

@router.get("/assessment/{assessment_id}/path")
def get_shortest_path(
    assessment_id: UUID,
    source: str = Query(..., description="Source node ID"),
    target: str = Query(..., description="Target node ID"),
    tenant_id: str = Query(default=TENANT_ID),
    db: Session = Depends(get_db),
):
    """Find shortest path between two nodes in the assessment graph."""
    try:
        result = _graph().shortest_path(
            db, UUID(tenant_id), assessment_id, source, target,
        )
        if "error" in result and result.get("length", 0) == -1:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=501, detail="networkx not installed")
    except Exception as e:
        logger.exception("Path analysis error")
        raise HTTPException(status_code=500, detail=str(e))
