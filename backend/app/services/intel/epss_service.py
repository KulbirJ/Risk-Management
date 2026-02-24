"""
EPSS (Exploit Prediction Scoring System) service.

EPSS is a daily-updated machine-learning model maintained by FIRST.org that
estimates the probability (0-1) that a CVE will be exploited in the wild
within the next 30 days.  It is backed by real exploitation telemetry from
millions of sensors and updated every 24 hours.

API: https://api.first.org/data/v1/epss  — free, no API key required.

Outputs two feature-vector signals:
  epss_score       float 0-1   — exploitation probability
  epss_percentile  float 0-1   — relative rank vs all CVEs (~99 = top 1%)
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

EPSS_API_BASE = "https://api.first.org/data/v1/epss"
_CACHE: Dict[str, dict] = {}          # in-memory CVE→result cache (Lambda warm)
_CACHE_TTL = timedelta(hours=24)       # refresh every 24 h (matches EPSS update cadence)


class EPSSService:
    """
    Thin async wrapper around the FIRST.org EPSS API.

    Fetches a batch of CVE scores in a single request (comma-separated),
    with an in-Lambda memory cache to avoid re-fetching across invocations
    in the same warm execution environment.
    """

    async def get_scores(self, cve_ids: List[str]) -> Dict[str, dict]:
        """
        Fetch EPSS scores for one or more CVE IDs.

        Parameters
        ----------
        cve_ids : list of str
            e.g. ["CVE-2023-44487", "CVE-2021-44228"]

        Returns
        -------
        dict  keyed by CVE ID  →  {"epss_score": float, "epss_percentile": float}
        Missing CVEs get default zeros.
        """
        if not cve_ids:
            return {}

        results: Dict[str, dict] = {}
        missing: List[str] = []

        for cve in cve_ids:
            if cve in _CACHE:
                results[cve] = _CACHE[cve]
            else:
                missing.append(cve)

        if missing:
            fetched = await self._fetch_batch(missing)
            for cve, data in fetched.items():
                _CACHE[cve] = data
                results[cve] = data

        # Ensure all requested CVEs have an entry
        for cve in cve_ids:
            if cve not in results:
                results[cve] = {"epss_score": 0.0, "epss_percentile": 0.0}

        return results

    async def get_score(self, cve_id: str) -> dict:
        """Convenience wrapper for a single CVE."""
        scores = await self.get_scores([cve_id])
        return scores.get(cve_id, {"epss_score": 0.0, "epss_percentile": 0.0})

    def build_feature_vector(self, scores_by_cve: Dict[str, dict]) -> dict:
        """
        Aggregate per-CVE EPSS scores into a threat-level feature vector.

        Takes the maximum epss_score and the corresponding percentile across
        all CVEs associated with a threat (worst-case signal).
        """
        if not scores_by_cve:
            return {"epss_score": 0.0, "epss_percentile": 0.0}

        max_score = 0.0
        max_percentile = 0.0
        for data in scores_by_cve.values():
            s = float(data.get("epss_score", 0))
            p = float(data.get("epss_percentile", 0))
            if s > max_score:
                max_score = s
                max_percentile = p

        return {
            "epss_score": round(max_score, 6),
            "epss_percentile": round(max_percentile, 6),
        }

    # ── internal ─────────────────────────────────────────────────

    async def _fetch_batch(self, cve_ids: List[str]) -> Dict[str, dict]:
        """
        Call the EPSS API with a comma-separated list of CVE IDs.
        Returns a dict keyed by CVE ID.
        """
        try:
            import httpx
            params = {"cve": ",".join(cve_ids), "scope": "time-series"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(EPSS_API_BASE, params={"cve": ",".join(cve_ids)})
                resp.raise_for_status()
                data = resp.json()

            out: Dict[str, dict] = {}
            for entry in data.get("data", []):
                cve = entry.get("cve", "")
                if cve:
                    out[cve] = {
                        "epss_score": float(entry.get("epss", 0)),
                        "epss_percentile": float(entry.get("percentile", 0)),
                    }
            logger.debug("EPSS: fetched %d scores for %d CVEs", len(out), len(cve_ids))
            return out

        except Exception as e:
            logger.warning("EPSS fetch failed for %s: %s — using zeros", cve_ids[:3], e)
            return {}
