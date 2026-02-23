"""
Phase 4 — DBSCAN Threat Clustering Service.

Groups threats by feature-vector similarity using density-based clustering
(DBSCAN).  Identifies threat families and outlier threats that may need
special attention.

Key outputs:
* Cluster assignments per threat
* Cluster summaries (centroid, dominant features, member count)
* Outlier identification (DBSCAN label == -1)
* Silhouette score for cluster quality

Uses scikit-learn's DBSCAN — same dependency as Phase 2.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from ...models.models import Assessment, Threat
from ..ml.scoring_service import FEATURE_KEYS, _features_to_array

logger = logging.getLogger(__name__)


class ClusteringService:
    """
    Groups threats into clusters based on their unified feature vectors.

    Algorithm: DBSCAN (Density-Based Spatial Clustering of Applications
    with Noise).  Advantages over k-means:
    * Doesn't require pre-specifying k
    * Naturally identifies outliers (noise points)
    * Finds arbitrarily-shaped clusters

    Workflow:
    1. Extract feature vectors from enriched threats
    2. Standardise features
    3. Run DBSCAN
    4. Compute cluster summaries + quality metrics
    """

    def cluster_assessment(
        self,
        db: Session,
        tenant_id: UUID,
        assessment_id: UUID,
        *,
        eps: float = 0.8,
        min_samples: int = 2,
    ) -> Dict[str, Any]:
        """
        Cluster all enriched threats in an assessment.

        Parameters
        ----------
        eps : float
            Maximum distance between two samples to be considered neighbours.
            Lower → tighter clusters.
        min_samples : int
            Minimum cluster size (including the core point).

        Returns
        -------
        dict  with ``clusters``, ``outliers``, ``quality``, ``threats``.
        """
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler

        # ── Gather data ──────────────────────────────────────────
        threats = (
            db.query(Threat)
            .filter(
                Threat.assessment_id == assessment_id,
                Threat.tenant_id == tenant_id,
                Threat.intel_enriched == True,
            )
            .all()
        )

        if not threats:
            return self._empty_result(assessment_id, "No enriched threats found")

        X_raw: List[np.ndarray] = []
        threat_meta: List[Dict[str, Any]] = []

        for t in threats:
            fv: dict = dict(t.likelihood_score_rationale or {})  # type: ignore[arg-type]
            if not fv:
                continue
            X_raw.append(_features_to_array(fv))
            threat_meta.append({
                "threat_id": str(t.id),
                "title": t.title,
                "likelihood_score": int(t.likelihood_score or 0),  # type: ignore[arg-type]
                "severity": t.severity,
                "catalogue_key": t.catalogue_key,
            })

        if len(X_raw) < 2:
            return self._empty_result(assessment_id, "Need ≥2 enriched threats to cluster")

        X = np.array(X_raw)

        # ── Standardise ─────────────────────────────────────────
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # ── DBSCAN ──────────────────────────────────────────────
        db_model = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean")
        labels = db_model.fit_predict(X_scaled)

        # ── Quality metric ──────────────────────────────────────
        n_clusters = len(set(labels) - {-1})
        quality: Dict[str, Any] = {
            "n_clusters": n_clusters,
            "n_outliers": int(np.sum(labels == -1)),
            "n_threats": len(labels),
        }

        if n_clusters >= 2:
            try:
                from sklearn.metrics import silhouette_score
                quality["silhouette_score"] = round(
                    float(silhouette_score(X_scaled, labels)), 4
                )
            except Exception:
                quality["silhouette_score"] = None

        # ── Build cluster summaries ─────────────────────────────
        clusters: Dict[int, Dict[str, Any]] = {}
        cluster_members: Dict[int, List[int]] = defaultdict(list)

        for i, lbl in enumerate(labels):
            cluster_members[int(lbl)].append(i)

        for lbl, indices in cluster_members.items():
            if lbl == -1:
                continue  # outliers handled separately

            member_vectors = X[indices]
            centroid = np.mean(member_vectors, axis=0)

            # Dominant features: top 5 by centroid value
            top_indices = np.argsort(centroid)[::-1][:5]
            dominant_features = [
                {"feature": FEATURE_KEYS[fi], "mean_value": round(float(centroid[fi]), 4)}
                for fi in top_indices
                if centroid[fi] > 0
            ]

            members = [threat_meta[i] for i in indices]
            avg_score = round(float(np.mean([m["likelihood_score"] for m in members])), 1)

            # Infer cluster label from dominant features
            cluster_label = self._infer_cluster_label(dominant_features, members)

            clusters[lbl] = {
                "cluster_id": lbl,
                "label": cluster_label,
                "size": len(indices),
                "avg_likelihood_score": avg_score,
                "dominant_features": dominant_features,
                "members": members,
            }

        # ── Outliers ────────────────────────────────────────────
        outlier_indices = cluster_members.get(-1, [])
        outliers = [
            {
                **threat_meta[i],
                "nearest_cluster": self._find_nearest_cluster(
                    X_scaled[i], X_scaled, labels, i
                ),
            }
            for i in outlier_indices
        ]

        # ── Thread assignments back to threat dicts ─────────────
        threat_assignments = []
        for i, meta in enumerate(threat_meta):
            threat_assignments.append({
                **meta,
                "cluster_id": int(labels[i]),
                "is_outlier": int(labels[i]) == -1,
            })

        return {
            "assessment_id": str(assessment_id),
            "clusters": list(clusters.values()),
            "outliers": outliers,
            "quality": quality,
            "threats": threat_assignments,
            "parameters": {"eps": eps, "min_samples": min_samples},
        }

    # ══════════════════════════════════════════════════════════════
    # CROSS-ASSESSMENT CLUSTERING
    # ══════════════════════════════════════════════════════════════

    def cluster_tenant_threats(
        self,
        db: Session,
        tenant_id: UUID,
        *,
        eps: float = 0.8,
        min_samples: int = 2,
    ) -> Dict[str, Any]:
        """
        Cluster ALL enriched threats across the tenant.
        Useful for identifying organisation-wide threat patterns.
        """
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler

        threats = (
            db.query(Threat)
            .filter(Threat.tenant_id == tenant_id, Threat.intel_enriched == True)
            .all()
        )

        if len(threats) < 2:
            return self._empty_result(None, "Need ≥2 enriched threats")

        X_raw: List[np.ndarray] = []
        threat_meta: List[Dict[str, Any]] = []

        for t in threats:
            fv: dict = dict(t.likelihood_score_rationale or {})  # type: ignore[arg-type]
            if not fv:
                continue
            X_raw.append(_features_to_array(fv))
            threat_meta.append({
                "threat_id": str(t.id),
                "assessment_id": str(t.assessment_id),
                "title": t.title,
                "likelihood_score": int(t.likelihood_score or 0),  # type: ignore[arg-type]
                "severity": t.severity,
                "catalogue_key": t.catalogue_key,
            })

        if len(X_raw) < 2:
            return self._empty_result(None, "Need ≥2 enriched threats with features")

        X = np.array(X_raw)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        db_model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db_model.fit_predict(X_scaled)

        n_clusters = len(set(labels) - {-1})
        quality: Dict[str, Any] = {
            "n_clusters": n_clusters,
            "n_outliers": int(np.sum(labels == -1)),
            "n_threats": len(labels),
        }

        if n_clusters >= 2:
            try:
                from sklearn.metrics import silhouette_score
                quality["silhouette_score"] = round(
                    float(silhouette_score(X_scaled, labels)), 4
                )
            except Exception:
                pass

        threat_assignments = []
        for i, meta in enumerate(threat_meta):
            threat_assignments.append({
                **meta,
                "cluster_id": int(labels[i]),
                "is_outlier": int(labels[i]) == -1,
            })

        return {
            "scope": "tenant",
            "clusters_found": n_clusters,
            "quality": quality,
            "threats": threat_assignments,
            "parameters": {"eps": eps, "min_samples": min_samples},
        }

    # ══════════════════════════════════════════════════════════════
    # SIMILARITY SEARCH
    # ══════════════════════════════════════════════════════════════

    def find_similar_threats(
        self,
        db: Session,
        tenant_id: UUID,
        threat_id: UUID,
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """
        Find the N most similar threats to a given threat by
        cosine similarity of feature vectors.
        """
        target = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not target:
            return {"error": f"Threat {threat_id} not found"}

        target_fv: dict = dict(target.likelihood_score_rationale or {})  # type: ignore[arg-type]
        if not target_fv:
            return {"error": "Target threat has no feature vector"}

        target_arr = _features_to_array(target_fv)

        # Get all other enriched threats
        others = (
            db.query(Threat)
            .filter(
                Threat.tenant_id == tenant_id,
                Threat.intel_enriched == True,
                Threat.id != threat_id,
            )
            .all()
        )

        similarities: List[Dict[str, Any]] = []
        for t in others:
            fv: dict = dict(t.likelihood_score_rationale or {})  # type: ignore[arg-type]
            if not fv:
                continue
            other_arr = _features_to_array(fv)

            # Cosine similarity
            dot = np.dot(target_arr, other_arr)
            norm_a = np.linalg.norm(target_arr)
            norm_b = np.linalg.norm(other_arr)
            if norm_a > 0 and norm_b > 0:
                sim = float(dot / (norm_a * norm_b))
            else:
                sim = 0.0

            similarities.append({
                "threat_id": str(t.id),
                "title": t.title,
                "assessment_id": str(t.assessment_id),
                "likelihood_score": int(t.likelihood_score or 0),  # type: ignore[arg-type]
                "similarity": round(sim, 4),
            })

        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "target_threat_id": str(threat_id),
            "target_title": target.title,
            "similar_threats": similarities[:top_n],
            "total_compared": len(similarities),
        }

    # ══════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _infer_cluster_label(
        dominant_features: List[Dict[str, Any]],
        members: List[Dict[str, Any]],
    ) -> str:
        """Infer a human-readable label for a cluster."""
        if not dominant_features:
            return "Unknown"

        top = dominant_features[0]["feature"]

        label_map = {
            "nvd_cvss_score": "CVE-Heavy",
            "kev_listed": "KEV-Listed",
            "kev_ransomware": "Ransomware-Associated",
            "github_poc_count": "Exploit-Available",
            "github_star_total": "Popular-Exploits",
            "otx_cve_pulse_count": "High-Intel-Activity",
            "otx_tech_pulse_count": "ATT&CK-Technique-Active",
            "attack_group_count": "APT-Targeted",
            "sector_freq_annual": "Sector-Frequent",
            "sector_percentile": "Sector-Prevalent",
            "mapped_technique_count": "Technique-Rich",
            "has_cve": "CVE-Associated",
            "cve_count": "Multi-CVE",
        }

        return label_map.get(top, f"Feature:{top}")

    @staticmethod
    def _find_nearest_cluster(
        point: np.ndarray,
        X: np.ndarray,
        labels: np.ndarray,
        self_idx: int,
    ) -> int:
        """Find the nearest non-outlier cluster for an outlier point."""
        cluster_labels = set(labels) - {-1}
        if not cluster_labels:
            return -1

        best_cluster = -1
        best_dist = float("inf")

        for cl in cluster_labels:
            mask = labels == cl
            cluster_points = X[mask]
            centroid = np.mean(cluster_points, axis=0)
            dist = float(np.linalg.norm(point - centroid))
            if dist < best_dist:
                best_dist = dist
                best_cluster = cl

        return best_cluster

    @staticmethod
    def _empty_result(
        assessment_id: Optional[UUID],
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "assessment_id": str(assessment_id) if assessment_id else None,
            "clusters": [],
            "outliers": [],
            "quality": {"n_clusters": 0, "n_outliers": 0, "n_threats": 0},
            "threats": [],
            "note": reason,
        }
