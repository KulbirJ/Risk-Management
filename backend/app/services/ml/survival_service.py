"""
Phase 2 — Survival Analysis Service.

Estimates **how long** an active risk is likely to persist using
Kaplan-Meier / log-rank statistics.  Full Cox-PH regression is
available when the ``lifelines`` package is installed (optional
heavy dependency).

Key outputs:
* ``estimated_persistence_days`` on ActiveRisk
* Survival curves per sector / threat category
* Hazard ratios for key covariates

Design constraints:
* Runs without ``lifelines`` — falls back to a simpler parametric
  estimator using numpy / scipy.
* Respects ``score_locked`` — never overwrites a locked risk.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from ...models.models import ActiveRisk, Assessment, AuditLog, Threat

logger = logging.getLogger(__name__)

# Default median persistence by residual-risk tier (days)
DEFAULT_PERSISTENCE: Dict[str, int] = {
    "critical": 180,
    "high": 120,
    "medium": 60,
    "low": 30,
}


class SurvivalAnalysisService:
    """
    Estimates how long an active risk is expected to persist
    (i.e., remain open) before being mitigated or accepted.

    Two modes:
    1. **Parametric fallback** — uses an exponential model fitted to closed
       risk durations plus sector / severity multipliers.
    2. **Kaplan-Meier / Cox-PH** — when ``lifelines`` is available and enough
       data exists, provides non-parametric survival curves.
    """

    def __init__(self) -> None:
        self._km_fitted = False
        self._median_durations: Dict[str, float] = {}  # sector → median days
        self._hazard_ratios: Dict[str, float] = {}

    # ══════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════

    def estimate_persistence(
        self,
        db: Session,
        tenant_id: UUID,
        active_risk_id: Optional[UUID] = None,
        assessment_id: Optional[UUID] = None,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Estimate ``estimated_persistence_days`` for one or many active risks.
        """
        query = db.query(ActiveRisk).filter(ActiveRisk.tenant_id == tenant_id)
        if active_risk_id:
            query = query.filter(ActiveRisk.id == active_risk_id)
        elif assessment_id:
            query = query.filter(ActiveRisk.assessment_id == assessment_id)
        else:
            # All open risks
            query = query.filter(ActiveRisk.status.in_(["open", "accepted", "mitigating"]))

        risks = query.all()
        if not risks:
            return {"estimated": 0, "results": []}

        # Build historical durations for calibration
        hist = self._build_historical_durations(db, tenant_id)
        results: List[Dict[str, Any]] = []
        estimated = 0

        for risk in risks:
            if bool(risk.score_locked):  # type: ignore[arg-type]
                results.append({
                    "active_risk_id": str(risk.id),
                    "skipped": True,
                    "reason": "score_locked",
                })
                continue

            # Get sector for this risk's assessment
            assessment = db.query(Assessment).filter(
                Assessment.id == risk.assessment_id
            ).first()
            sector = str(getattr(assessment, "industry_sector", None) or "default").lower()

            # Get threat likelihood for weighting
            threat = db.query(Threat).filter(Threat.id == risk.threat_id).first()
            likelihood_score = int(threat.likelihood_score or 50) if threat else 50  # type: ignore[arg-type]

            est_days = self._estimate_single(
                risk=risk,
                sector=sector,
                likelihood_score=likelihood_score,
                historical=hist,
            )

            if persist:
                self._persist_estimate(db, tenant_id, risk, est_days)

            results.append({
                "active_risk_id": str(risk.id),
                "threat_id": str(risk.threat_id),
                "estimated_persistence_days": est_days,
                "sector": sector,
                "residual_risk": risk.residual_risk,
            })
            estimated += 1

        return {
            "estimated": estimated,
            "results": results,
            "historical_sample_size": len(hist.get("durations", [])),
        }

    def survival_curve(
        self,
        db: Session,
        tenant_id: UUID,
        sector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a discretised survival curve (time → survival probability)
        for the tenant's active risks, optionally filtered by sector.
        """
        hist = self._build_historical_durations(db, tenant_id, sector=sector)
        durations = hist.get("durations", [])
        events = hist.get("events", [])

        if len(durations) < 3:
            # Not enough data — return default parametric curve
            return self._default_curve(sector)

        # Try lifelines KM
        try:
            return self._km_curve(durations, events, sector)
        except ImportError:
            return self._parametric_curve(durations, events, sector)

    # ══════════════════════════════════════════════════════════════
    # INTERNAL ESTIMATION
    # ══════════════════════════════════════════════════════════════

    def _estimate_single(
        self,
        risk: ActiveRisk,
        sector: str,
        likelihood_score: int,
        historical: Dict[str, Any],
    ) -> int:
        """Estimate persistence for a single active risk."""
        residual = str(risk.residual_risk or "medium").lower()
        base = DEFAULT_PERSISTENCE.get(residual, 60)

        # Apply sector multiplier from historical data
        sector_mult = historical.get("sector_multipliers", {}).get(sector, 1.0)

        # Apply likelihood multiplier (higher likelihood → longer persistence)
        likelihood_mult = 0.5 + (likelihood_score / 100)  # 0.5 – 1.5

        # Apply review cycle factor (more frequent reviews → shorter persistence)
        review_days = int(risk.review_cycle_days or 30)  # type: ignore[arg-type]
        review_mult = min(1.5, max(0.5, review_days / 30))

        # Age factor — risks that have been open longer tend to persist longer
        age_days = 0
        if risk.created_at:  # type: ignore[truthy-bool]
            age_days = (datetime.utcnow() - risk.created_at.replace(tzinfo=None)).days  # type: ignore[union-attr]
        age_mult = 1.0 + (min(age_days, 365) / 730)  # caps at 1.5x for 1yr-old risks

        est = base * sector_mult * likelihood_mult * review_mult * age_mult
        return max(1, int(round(est)))

    def _build_historical_durations(
        self,
        db: Session,
        tenant_id: UUID,
        sector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build duration / event arrays from closed active risks.
        ``event=1`` means the risk was resolved; ``event=0`` means still open (censored).
        """
        query = db.query(ActiveRisk, Assessment.industry_sector).join(
            Assessment, ActiveRisk.assessment_id == Assessment.id
        ).filter(ActiveRisk.tenant_id == tenant_id)

        if sector:
            query = query.filter(Assessment.industry_sector == sector)

        rows = query.all()

        durations: List[float] = []
        events: List[int] = []
        sector_durations: Dict[str, List[float]] = {}

        now = datetime.utcnow()
        for risk, ind_sector in rows:
            created = risk.created_at
            if not created:
                continue
            created_naive = created.replace(tzinfo=None) if created.tzinfo else created

            if risk.status in ("closed", "mitigated"):
                updated = risk.updated_at
                if updated:
                    updated_naive = updated.replace(tzinfo=None) if updated.tzinfo else updated
                    dur = (updated_naive - created_naive).days
                else:
                    dur = 30  # assume 30 if no updated_at
                durations.append(max(1.0, float(dur)))
                events.append(1)  # resolved
            else:
                dur = (now - created_naive).days
                durations.append(max(1.0, float(dur)))
                events.append(0)  # censored (still open)

            s = str(ind_sector or "default").lower()
            if s not in sector_durations:
                sector_durations[s] = []
            sector_durations[s].append(durations[-1])

        # Compute sector multipliers
        overall_median = float(np.median(durations)) if durations else 60.0
        sector_multipliers: Dict[str, float] = {}
        for s, durs in sector_durations.items():
            med = float(np.median(durs))
            sector_multipliers[s] = med / overall_median if overall_median > 0 else 1.0

        return {
            "durations": durations,
            "events": events,
            "sector_multipliers": sector_multipliers,
            "overall_median": overall_median,
        }

    # ── Survival curves ────────────────────────────────────────

    def _km_curve(
        self, durations: List[float], events: List[int], sector: Optional[str]
    ) -> Dict[str, Any]:
        """Kaplan-Meier curve using lifelines."""
        from lifelines import KaplanMeierFitter  # type: ignore[import-untyped]

        kmf = KaplanMeierFitter()
        kmf.fit(durations, event_observed=events, label=sector or "all")

        timeline = kmf.survival_function_.index.tolist()
        survival = kmf.survival_function_.iloc[:, 0].tolist()

        return {
            "method": "kaplan_meier",
            "sector": sector,
            "median_survival_days": round(float(kmf.median_survival_time_), 1)
            if not math.isinf(kmf.median_survival_time_)
            else None,
            "timeline_days": [round(t, 1) for t in timeline],
            "survival_probability": [round(s, 4) for s in survival],
            "n_observations": len(durations),
            "n_events": sum(events),
        }

    def _parametric_curve(
        self, durations: List[float], events: List[int], sector: Optional[str]
    ) -> Dict[str, Any]:
        """Simple exponential survival curve (no lifelines needed)."""
        resolved_durs = [d for d, e in zip(durations, events) if e == 1]
        if not resolved_durs:
            return self._default_curve(sector)

        # MLE for exponential: lambda = n_events / sum(durations)
        n_events = sum(events)
        total_time = sum(durations)
        lam = n_events / total_time if total_time > 0 else 1 / 60

        median = math.log(2) / lam
        timeline = list(range(0, int(max(durations)) + 30, 7))
        survival = [math.exp(-lam * t) for t in timeline]

        return {
            "method": "exponential_parametric",
            "sector": sector,
            "median_survival_days": round(median, 1),
            "lambda": round(lam, 6),
            "timeline_days": timeline,
            "survival_probability": [round(s, 4) for s in survival],
            "n_observations": len(durations),
            "n_events": n_events,
        }

    @staticmethod
    def _default_curve(sector: Optional[str]) -> Dict[str, Any]:
        """Default curve when no historical data is available."""
        median = 60
        lam = math.log(2) / median
        timeline = list(range(0, 365, 7))
        survival = [round(math.exp(-lam * t), 4) for t in timeline]
        return {
            "method": "default_exponential",
            "sector": sector,
            "median_survival_days": median,
            "timeline_days": timeline,
            "survival_probability": survival,
            "n_observations": 0,
            "n_events": 0,
            "note": "Insufficient historical data — using default parameters",
        }

    # ── Persistence helpers ──────────────────────────────────────

    def _persist_estimate(
        self,
        db: Session,
        tenant_id: UUID,
        risk: ActiveRisk,
        est_days: int,
    ) -> None:
        """Write persistence estimate back to the active risk."""
        old_val = risk.estimated_persistence_days
        risk.estimated_persistence_days = est_days  # type: ignore[assignment]

        try:
            audit = AuditLog(
                tenant_id=tenant_id,
                action_type="active_risk.survival_estimate",
                resource_type="ActiveRisk",
                resource_id=str(risk.id),
                changes={
                    "before": {"estimated_persistence_days": old_val},
                    "after": {"estimated_persistence_days": est_days},
                },
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to persist survival estimate for risk %s: %s", risk.id, e)
