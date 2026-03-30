"""
ML Microservice Client — HTTP adapter for the external CVE enrichment + scoring service.

Calls the separate cyber-risk-ml-training Lambda microservice which runs
XGBoost v3 (28 features, 3-tier enrichment: CISA KEV, Exploit-DB, OSV,
NVD CPE, GitHub, OTX, Metasploit, Censys).

Falls back to built-in intel services when the ML service is unavailable
and settings.ml_service_fallback is True.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

# Re-usable timeout config
_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=float(settings.ml_service_timeout),
    write=5.0,
    pool=5.0,
)


class MLServiceClient:
    """Thin HTTP client for the external ML microservice."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ml_service_url).rstrip("/")
        self.enabled = bool(self.base_url)

    # ── Public API ────────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Ping the ML service /health endpoint."""
        if not self.enabled:
            return {"status": "disabled"}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def enrich_and_score_batch(
        self, threats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call POST /enrich-and-score with a batch of threats.

        Parameters
        ----------
        threats : list of dict
            Each dict must contain:
              - threat_id : str (UUID)
              - cve_ids   : list[str]  (e.g. ["CVE-2021-44228"])

        Returns
        -------
        dict with keys:
          - results       : list of per-threat enrichment dicts
          - threats_scored: int
          - errors        : list[str]
        """
        if not self.enabled:
            raise RuntimeError("ML service is not configured (ml_service_url is empty)")

        payload = {"threats": threats}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/enrich-and-score",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Convenience: single-threat scoring ────────────────────────────────

    async def enrich_and_score_single(
        self, threat_id: str, cve_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Score a single threat and return its result dict, or None on error."""
        try:
            batch = await self.enrich_and_score_batch(
                [{"threat_id": threat_id, "cve_ids": cve_ids}]
            )
            results = batch.get("results", [])
            return results[0] if results else None
        except Exception as exc:
            logger.warning("ML service single-threat call failed: %s", exc)
            return None

    # ── Feature mapping helpers ───────────────────────────────────────────

    @staticmethod
    def map_ml_features_to_platform(ml_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate the 28 v3 feature names returned by the ML microservice
        into the platform's unified feature-vector field names used by
        the EnrichmentOrchestrator / MLScoringService.

        Keys the platform already uses are passed through; ML-only keys
        are prefixed with ``ml_`` to avoid collisions.
        """
        mapped: Dict[str, Any] = {}

        # Direct mappings (platform ↔ ML service use same names)
        direct = [
            "cvss_score", "epss_score", "days_since_published",
            "in_cisa_kev", "has_public_poc", "poc_count",
            "affected_packages_count", "has_fixed_version",
            "requires_authentication", "requires_user_interaction",
            "scope_changed", "in_github_advisories", "github_affected_count",
            "patch_available", "otx_threat_score", "malware_associated",
            "active_exploits", "metasploit_modules", "has_metasploit_module",
            "censys_exposed_count", "has_censys_data",
            "is_critical_cvss", "is_high_cvss",
        ]
        for key in direct:
            if key in ml_features:
                mapped[key] = ml_features[key]

        # Categorical / encoded features — store raw and encoded
        categoricals = [
            "attack_vector", "primary_ecosystem",
            "min_exploit_difficulty", "module_rank", "module_type",
        ]
        for key in categoricals:
            if key in ml_features:
                mapped[f"ml_{key}"] = ml_features[key]

        return mapped
