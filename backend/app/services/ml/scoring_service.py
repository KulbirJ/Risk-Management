"""
Phase 2 — Predictive ML Scoring Service.

Trains a gradient-boosted model (or Random Forest fallback) on the unified
feature vectors produced by Phase 1's EnrichmentOrchestrator.  The model
replaces the rule-based ``_compute_likelihood_score`` with a calibrated
probabilistic likelihood score (0-100).

Design constraints
------------------
* Must run inside AWS Lambda (≤250 MB zipped).  scikit-learn + numpy fit;
  xgboost is available as an optional Lambda layer.
* When no trained model is available the service falls back to the Phase 1
  rule-based scorer so the platform degrades gracefully.
* Respects ``score_locked`` on ActiveRisk — ML never overwrites a
  human-locked score.
* Produces SHAP-style feature-importance explanations stored in
  ``likelihood_score_rationale``.
"""

from __future__ import annotations

import logging
import json
import math
import pickle
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from ...models.models import (
    ActiveRisk,
    Assessment,
    AuditLog,
    Threat,
    ThreatIntelEnrichment,
)

logger = logging.getLogger(__name__)

# ── Feature vector key ordering (must match training & inference) ──────────
FEATURE_KEYS: List[str] = [
    # Track A (CVE-based)
    "nvd_cvss_score",
    "nvd_severity_num",
    "nvd_days_since_published",
    "nvd_cwe_count",
    "nvd_ref_count",
    "nvd_epss_score",
    "kev_listed",
    "kev_ransomware",
    "kev_days_since_added",
    "otx_cve_pulse_count",
    "otx_cve_adversary_count",
    "otx_cve_country_count",
    "github_poc_count",
    "github_star_total",
    "github_has_recent_poc",
    # Track B (Non-CVE / ATT&CK)
    "otx_tech_pulse_count",
    "otx_tech_adversary_count",
    "attack_group_count",
    "sector_freq_annual",
    "sector_percentile",
    "sector_relative_ratio",
    # Meta
    "mapped_technique_count",
    "has_cve",
    "cve_count",
]

NUM_FEATURES = len(FEATURE_KEYS)


def _features_to_array(feature_dict: Dict[str, Any]) -> np.ndarray:
    """Convert a feature dict to a fixed-length numpy array."""
    return np.array(
        [float(feature_dict.get(k, 0.0)) for k in FEATURE_KEYS],
        dtype=np.float64,
    )


def _safe_float(val: Any) -> float:
    """Coerce a value to float, returning 0.0 on failure."""
    try:
        v = float(val)
        return 0.0 if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return 0.0


# ═══════════════════════════════════════════════════════════════════
# Core ML scoring class
# ═══════════════════════════════════════════════════════════════════

class MLScoringService:
    """
    Predictive likelihood scoring backed by scikit-learn.

    Lifecycle
    ---------
    1. ``train()`` — build model from existing enriched threats.
    2. ``score_threat()`` / ``score_batch()`` — predict likelihood for new or
       updated threats.
    3. ``explain()`` — return per-feature importance for a single threat.

    The trained model is serialised as a pickle blob and can optionally be
    persisted to S3 for cross-Lambda sharing (future).
    """

    def __init__(self) -> None:
        self._model: Any = None  # sklearn estimator
        self._model_meta: Dict[str, Any] = {}
        self._scaler: Any = None  # StandardScaler
        self._feature_importances: Optional[np.ndarray] = None

    # ── property helpers ──────────────────────────────────────────

    @property
    def is_trained(self) -> bool:
        return self._model is not None

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "trained": self.is_trained,
            "algorithm": self._model_meta.get("algorithm", "none"),
            "trained_at": self._model_meta.get("trained_at"),
            "training_samples": self._model_meta.get("n_samples", 0),
            "feature_count": NUM_FEATURES,
            "feature_keys": FEATURE_KEYS,
            "metrics": self._model_meta.get("metrics", {}),
        }

    # ══════════════════════════════════════════════════════════════
    # TRAINING
    # ══════════════════════════════════════════════════════════════

    def train(
        self,
        db: Session,
        tenant_id: UUID,
        *,
        min_samples: int = 10,
        algorithm: str = "random_forest",
    ) -> Dict[str, Any]:
        """
        Train (or re-train) the scoring model on all enriched threats
        belonging to *tenant_id*.

        Parameters
        ----------
        algorithm : str
            ``"random_forest"`` (default) or ``"gradient_boosting"``.
        min_samples : int
            Minimum number of labelled threats required to train.

        Returns
        -------
        dict  with keys ``trained``, ``n_samples``, ``metrics``, ``algorithm``.
        """
        from sklearn.ensemble import (
            GradientBoostingClassifier,
            RandomForestClassifier,
        )
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler

        # ── Gather training data ─────────────────────────────────
        X, y, threat_ids = self._build_training_set(db, tenant_id)

        if len(X) < min_samples:
            return {
                "trained": False,
                "reason": f"Only {len(X)} enriched threats (need ≥{min_samples})",
                "n_samples": len(X),
            }

        # ── Scale features ───────────────────────────────────────
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # ── Bin y into classes (Low / Medium / High / Critical) ──
        # y is 0-100 likelihood_score → 4-class ordinal
        y_cls = self._bin_scores(y)

        # ── Select algorithm ─────────────────────────────────────
        if algorithm == "gradient_boosting":
            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42,
            )
        else:
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                random_state=42,
                class_weight="balanced",
            )

        # ── Cross-validated metrics ──────────────────────────────
        cv_folds = min(5, len(X_scaled))
        if cv_folds < 2:
            cv_folds = 2
        cv_scores = cross_val_score(model, X_scaled, y_cls, cv=cv_folds, scoring="accuracy")
        metrics = {
            "cv_accuracy_mean": round(float(np.mean(cv_scores)), 4),
            "cv_accuracy_std": round(float(np.std(cv_scores)), 4),
        }

        # ── Fit final model on all data ──────────────────────────
        model.fit(X_scaled, y_cls)

        self._model = model
        self._scaler = scaler
        self._feature_importances = model.feature_importances_
        self._model_meta = {
            "algorithm": algorithm,
            "trained_at": datetime.utcnow().isoformat(),
            "n_samples": len(X),
            "metrics": metrics,
            "class_labels": ["low", "medium", "high", "critical"],
        }

        logger.info(
            "ML model trained: %s, n=%d, cv_acc=%.3f",
            algorithm,
            len(X),
            metrics["cv_accuracy_mean"],
        )
        return {"trained": True, "n_samples": len(X), "metrics": metrics, "algorithm": algorithm}

    # ══════════════════════════════════════════════════════════════
    # INFERENCE
    # ══════════════════════════════════════════════════════════════

    def score_threat(
        self,
        db: Session,
        tenant_id: UUID,
        threat_id: UUID,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Score a single threat and optionally persist the result."""
        threat = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            return {"error": f"Threat {threat_id} not found"}

        features: dict = dict(threat.likelihood_score_rationale or {})  # type: ignore[arg-type]
        if not features:
            return {"error": "Threat has no feature vector — run enrichment first"}

        score, label, explanation = self._predict_single(features)

        result = {
            "threat_id": str(threat_id),
            "ml_likelihood_score": score,
            "ml_likelihood_label": label,
            "explanation": explanation,
            "model_info": {
                "algorithm": self._model_meta.get("algorithm", "rule_based"),
                "trained_at": self._model_meta.get("trained_at"),
            },
        }

        if persist:
            self._persist_score(db, tenant_id, threat, score, label, explanation)

        return result

    def score_batch(
        self,
        db: Session,
        tenant_id: UUID,
        threat_ids: Optional[List[UUID]] = None,
        assessment_id: Optional[UUID] = None,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Score multiple threats, respecting ``score_locked``."""
        query = db.query(Threat).filter(Threat.tenant_id == tenant_id)
        if threat_ids:
            query = query.filter(Threat.id.in_(threat_ids))
        elif assessment_id:
            query = query.filter(Threat.assessment_id == assessment_id)
        else:
            return {"error": "Provide threat_ids or assessment_id"}

        threats = query.all()
        results: List[Dict[str, Any]] = []
        scored = 0
        skipped_locked = 0
        skipped_no_features = 0

        for threat in threats:
            features: dict = dict(threat.likelihood_score_rationale or {})  # type: ignore[arg-type]
            if not features:
                skipped_no_features += 1
                continue

            # Check if ActiveRisk is score_locked
            active_risk = (
                db.query(ActiveRisk)
                .filter(ActiveRisk.threat_id == threat.id)
                .first()
            )
            if active_risk and bool(active_risk.score_locked):  # type: ignore[arg-type]
                skipped_locked += 1
                results.append({
                    "threat_id": str(threat.id),
                    "skipped": True,
                    "reason": "score_locked",
                })
                continue

            score, label, explanation = self._predict_single(features)

            if persist:
                self._persist_score(db, tenant_id, threat, score, label, explanation)

            results.append({
                "threat_id": str(threat.id),
                "ml_likelihood_score": score,
                "ml_likelihood_label": label,
            })
            scored += 1

        return {
            "scored": scored,
            "skipped_locked": skipped_locked,
            "skipped_no_features": skipped_no_features,
            "total": len(threats),
            "results": results,
        }

    # ══════════════════════════════════════════════════════════════
    # EXPLAINABILITY
    # ══════════════════════════════════════════════════════════════

    def explain(
        self,
        db: Session,
        tenant_id: UUID,
        threat_id: UUID,
    ) -> Dict[str, Any]:
        """
        Return feature-level importance for a single threat's score.

        Uses permutation-style explanation when a trained model exists,
        falls back to rule-weight decomposition otherwise.
        """
        threat = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            return {"error": f"Threat {threat_id} not found"}

        features: dict = dict(threat.likelihood_score_rationale or {})  # type: ignore[arg-type]
        if not features:
            return {"error": "No feature vector available"}

        if self.is_trained and self._feature_importances is not None:
            return self._explain_with_model(features, threat)
        else:
            return self._explain_rule_based(features, threat)

    def _explain_with_model(
        self, features: Dict[str, Any], threat: Threat
    ) -> Dict[str, Any]:
        """Model-based explanation using feature importances × feature values."""
        arr = _features_to_array(features)
        importances = self._feature_importances
        if importances is None:
            return self._explain_rule_based(features, threat)

        # Contribution = importance × scaled_value
        if self._scaler is not None:
            arr_scaled = self._scaler.transform(arr.reshape(1, -1))[0]
        else:
            arr_scaled = arr

        contributions: List[Dict[str, Any]] = []
        for i, key in enumerate(FEATURE_KEYS):
            imp = float(importances[i])
            val = float(arr[i])
            scaled_val = float(arr_scaled[i])
            contribution = imp * abs(scaled_val)
            contributions.append({
                "feature": key,
                "value": round(val, 4),
                "importance": round(imp, 4),
                "contribution": round(contribution, 4),
            })

        # Sort by absolute contribution descending
        contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)

        return {
            "threat_id": str(threat.id),
            "threat_title": threat.title,
            "likelihood_score": threat.likelihood_score,
            "method": "model_feature_importance",
            "top_factors": contributions[:10],
            "all_factors": contributions,
            "model_algorithm": self._model_meta.get("algorithm"),
        }

    def _explain_rule_based(
        self, features: Dict[str, Any], threat: Threat
    ) -> Dict[str, Any]:
        """Decompose the rule-based score into per-component contributions."""
        components = []

        # CVSS
        cvss = _safe_float(features.get("nvd_cvss_score", 0))
        cvss_pts = min(30, cvss * 3)
        components.append({"feature": "nvd_cvss_score", "value": cvss, "points": round(cvss_pts, 1), "max": 30})

        # KEV
        kev = _safe_float(features.get("kev_listed", 0))
        kev_pts = 20 if kev else 0
        kev_rw = _safe_float(features.get("kev_ransomware", 0))
        kev_pts += 5 if kev_rw else 0
        components.append({"feature": "kev_listed+ransomware", "value": int(kev), "points": kev_pts, "max": 25})

        # OTX
        otx_cve = _safe_float(features.get("otx_cve_pulse_count", 0))
        otx_tech = _safe_float(features.get("otx_tech_pulse_count", 0))
        otx_pts = min(15, (otx_cve + otx_tech) * 1.5)
        components.append({"feature": "otx_pulse_count", "value": otx_cve + otx_tech, "points": round(otx_pts, 1), "max": 15})

        # GitHub
        poc = _safe_float(features.get("github_poc_count", 0))
        poc_pts = min(10, poc * 2)
        components.append({"feature": "github_poc_count", "value": poc, "points": round(poc_pts, 1), "max": 10})

        # ATT&CK groups
        grp = _safe_float(features.get("attack_group_count", 0))
        grp_pts = min(10, grp * 2)
        components.append({"feature": "attack_group_count", "value": grp, "points": round(grp_pts, 1), "max": 10})

        # Sector
        pct = _safe_float(features.get("sector_percentile", 50))
        sec_pts = (pct / 100) * 10
        components.append({"feature": "sector_percentile", "value": pct, "points": round(sec_pts, 1), "max": 10})

        return {
            "threat_id": str(threat.id),
            "threat_title": threat.title,
            "likelihood_score": threat.likelihood_score,
            "method": "rule_based_decomposition",
            "components": components,
            "total_points": sum(c["points"] for c in components),
            "max_possible": 100,
        }

    # ══════════════════════════════════════════════════════════════
    # BIAS MONITORING
    # ══════════════════════════════════════════════════════════════

    def bias_report(
        self,
        db: Session,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate a bias monitoring report: score distributions per sector.
        """
        threats = (
            db.query(Threat, Assessment.industry_sector)
            .join(Assessment, Threat.assessment_id == Assessment.id)
            .filter(Threat.tenant_id == tenant_id, Threat.intel_enriched == True)
            .all()
        )
        if not threats:
            return {"sectors": {}, "total_threats": 0}

        sector_scores: Dict[str, List[int]] = {}
        for threat, sector in threats:
            s = str(sector or "unknown").lower()
            if s not in sector_scores:
                sector_scores[s] = []
            sector_scores[s].append(int(threat.likelihood_score or 0))

        report: Dict[str, Any] = {}
        for sector, scores in sector_scores.items():
            arr = np.array(scores, dtype=np.float64)
            report[sector] = {
                "count": len(scores),
                "mean": round(float(np.mean(arr)), 2),
                "median": round(float(np.median(arr)), 2),
                "std": round(float(np.std(arr)), 2),
                "min": int(np.min(arr)),
                "max": int(np.max(arr)),
                "quartiles": {
                    "q25": round(float(np.percentile(arr, 25)), 2),
                    "q50": round(float(np.percentile(arr, 50)), 2),
                    "q75": round(float(np.percentile(arr, 75)), 2),
                },
            }

        return {
            "sectors": report,
            "total_threats": len(threats),
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ══════════════════════════════════════════════════════════════
    # MODEL PERSISTENCE
    # ══════════════════════════════════════════════════════════════

    def export_model(self) -> Optional[bytes]:
        """Serialise the current model to bytes (pickle)."""
        if not self.is_trained:
            return None
        buf = BytesIO()
        pickle.dump(
            {
                "model": self._model,
                "scaler": self._scaler,
                "meta": self._model_meta,
                "feature_importances": self._feature_importances,
            },
            buf,
        )
        return buf.getvalue()

    def import_model(self, data: bytes) -> Dict[str, Any]:
        """Load a previously exported model."""
        payload = pickle.loads(data)  # noqa: S301
        self._model = payload["model"]
        self._scaler = payload["scaler"]
        self._model_meta = payload["meta"]
        self._feature_importances = payload.get("feature_importances")
        logger.info("ML model imported: %s", self._model_meta.get("algorithm"))
        return self.model_info

    # ══════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _bin_scores(y: np.ndarray) -> np.ndarray:
        """Bin 0-100 scores into ordinal classes."""
        bins = np.digitize(y, [25, 50, 75])  # 0=low, 1=med, 2=high, 3=crit
        return bins

    @staticmethod
    def _label_from_bin(bin_val: int) -> str:
        return ["low", "medium", "high", "critical"][min(bin_val, 3)]

    @staticmethod
    def _score_from_proba(proba: np.ndarray) -> int:
        """Convert class probabilities to a 0-100 score."""
        # Weighted sum: low=12.5, med=37.5, high=62.5, crit=87.5
        centres = np.array([12.5, 37.5, 62.5, 87.5])
        score = float(np.dot(proba, centres))
        return min(100, max(0, int(round(score))))

    def _build_training_set(
        self, db: Session, tenant_id: UUID
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Extract feature matrix X and target vector y from enriched threats."""
        threats = (
            db.query(Threat)
            .filter(
                Threat.tenant_id == tenant_id,
                Threat.intel_enriched == True,
            )
            .all()
        )

        X_rows: List[np.ndarray] = []
        y_rows: List[float] = []
        ids: List[str] = []

        for t in threats:
            fv: dict = dict(t.likelihood_score_rationale or {})  # type: ignore[arg-type]
            if not fv:
                continue
            X_rows.append(_features_to_array(fv))
            y_rows.append(float(t.likelihood_score or 0))  # type: ignore[arg-type]
            ids.append(str(t.id))

        if not X_rows:
            return np.empty((0, NUM_FEATURES)), np.empty(0), []

        return np.array(X_rows), np.array(y_rows), ids

    def _predict_single(
        self, features: Dict[str, Any]
    ) -> Tuple[int, str, Dict[str, Any]]:
        """
        Predict score + label + explanation dict for a single feature dict.

        Falls back to rule-based scoring when no model is trained.
        """
        if not self.is_trained:
            score = self._rule_based_score(features)
            label = self._label_from_bin(np.digitize(score, [25, 50, 75]))
            explanation = {"method": "rule_based", "note": "No ML model trained yet"}
            return score, label, explanation

        arr = _features_to_array(features).reshape(1, -1)
        arr_scaled = self._scaler.transform(arr)
        proba = self._model.predict_proba(arr_scaled)[0]

        score = self._score_from_proba(proba)
        predicted_class = int(self._model.predict(arr_scaled)[0])
        label = self._label_from_bin(predicted_class)

        # Top features
        importances = self._feature_importances
        top_indices = np.argsort(importances)[::-1][:5]  # type: ignore[index]
        top_features = [
            {"feature": FEATURE_KEYS[i], "importance": round(float(importances[i]), 4)}  # type: ignore[index]
            for i in top_indices
        ]

        explanation = {
            "method": "ml_model",
            "algorithm": self._model_meta.get("algorithm"),
            "class_probabilities": {
                "low": round(float(proba[0]), 4),
                "medium": round(float(proba[1]), 4),
                "high": round(float(proba[2]), 4),
                "critical": round(float(proba[3]), 4),
            },
            "top_features": top_features,
        }
        return score, label, explanation

    @staticmethod
    def _rule_based_score(features: Dict[str, Any]) -> int:
        """Mirror of EnrichmentOrchestrator._compute_likelihood_score."""
        score = 0.0
        cvss = _safe_float(features.get("nvd_cvss_score", 0))
        score += min(30, cvss * 3)
        if _safe_float(features.get("kev_listed", 0)):
            score += 20
            if _safe_float(features.get("kev_ransomware", 0)):
                score += 5
        otx_cve = _safe_float(features.get("otx_cve_pulse_count", 0))
        otx_tech = _safe_float(features.get("otx_tech_pulse_count", 0))
        score += min(15, (otx_cve + otx_tech) * 1.5)
        poc = _safe_float(features.get("github_poc_count", 0))
        score += min(10, poc * 2)
        grp = _safe_float(features.get("attack_group_count", 0))
        score += min(10, grp * 2)
        pct = _safe_float(features.get("sector_percentile", 50))
        score += (pct / 100) * 10
        if not features.get("has_cve") and features.get("mapped_technique_count", 0) > 0:
            score = max(score, 15)
        return min(100, max(0, int(round(score))))

    def _persist_score(
        self,
        db: Session,
        tenant_id: UUID,
        threat: Threat,
        score: int,
        label: str,
        explanation: Dict[str, Any],
    ) -> None:
        """Write ML score back to the threat and its active risk."""
        # Update threat
        old_score = threat.likelihood_score
        threat.likelihood_score = score  # type: ignore[assignment]

        # Merge explanation into the rationale
        rationale: dict = dict(threat.likelihood_score_rationale or {})  # type: ignore[arg-type]
        rationale["_ml_score"] = score
        rationale["_ml_label"] = label
        rationale["_ml_explanation"] = explanation
        threat.likelihood_score_rationale = rationale  # type: ignore[assignment]

        # Update ActiveRisk.risk_score if it exists and is not locked
        active_risk = (
            db.query(ActiveRisk)
            .filter(ActiveRisk.threat_id == threat.id)
            .first()
        )
        if active_risk and not bool(active_risk.score_locked):  # type: ignore[arg-type]
            # Map 0-100 likelihood to 1-10 for the risk register
            likelihood_1_10 = max(1, min(10, int(round(score / 10))))
            active_risk.likelihood = likelihood_1_10  # type: ignore[assignment]
            impact_1_10 = int(active_risk.impact or 5)  # type: ignore[arg-type]
            active_risk.risk_score = int(round(likelihood_1_10 * impact_1_10))  # type: ignore[assignment]

        # Audit log
        try:
            audit = AuditLog(
                tenant_id=tenant_id,
                action_type="threat.ml_score",
                resource_type="Threat",
                resource_id=str(threat.id),
                changes={
                    "before": {"likelihood_score": old_score},
                    "after": {"likelihood_score": score, "ml_label": label},
                },
            )
            db.add(audit)
        except Exception:
            pass

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to persist ML score for threat %s: %s", threat.id, e)
