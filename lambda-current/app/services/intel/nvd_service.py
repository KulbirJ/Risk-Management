"""NVD (National Vulnerability Database) client — Track A: CVE-based enrichment."""
import logging
from typing import Optional
import httpx
from datetime import datetime, timedelta

from ...core.config import settings

logger = logging.getLogger(__name__)

# Rate limiting: NVD allows 5 req/30s without key, 50 req/30s with key
NVD_TIMEOUT = 30  # seconds


class NVDService:
    """Fetch CVE details from the NVD 2.0 REST API."""

    def __init__(self):
        self.base_url = settings.nvd_api_base
        self.api_key = settings.nvd_api_key

    async def get_cve(self, cve_id: str) -> Optional[dict]:
        """
        Fetch a single CVE record from NVD.

        Returns a normalised dict with:
          - cvss_v3_score, cvss_v3_vector, severity
          - epss_score (if available via /cves endpoint metrics)
          - cwe_ids, references, description
          - published_date, last_modified_date
        """
        if not cve_id or not cve_id.upper().startswith("CVE-"):
            return None

        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=NVD_TIMEOUT) as client:
                resp = await client.get(
                    self.base_url,
                    params={"cveId": cve_id.upper()},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            vulnerabilities = data.get("vulnerabilities", [])
            if not vulnerabilities:
                logger.info(f"NVD: No data for {cve_id}")
                return None

            cve_item = vulnerabilities[0].get("cve", {})
            return self._normalise(cve_id, cve_item)

        except httpx.HTTPStatusError as e:
            logger.warning(f"NVD HTTP error for {cve_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"NVD fetch error for {cve_id}: {e}")
            return None

    def _normalise(self, cve_id: str, cve_item: dict) -> dict:
        """Extract key fields from the NVD CVE 2.0 response."""
        metrics = cve_item.get("metrics", {})

        # CVSS v3.1 first, then v3.0, then v2.0
        cvss_v3 = None
        for key in ("cvssMetricV31", "cvssMetricV30"):
            metric_list = metrics.get(key, [])
            if metric_list:
                cvss_v3 = metric_list[0].get("cvssData", {})
                break

        cvss_score = cvss_v3.get("baseScore", 0) if cvss_v3 else 0
        cvss_vector = cvss_v3.get("vectorString", "") if cvss_v3 else ""
        severity = cvss_v3.get("baseSeverity", "UNKNOWN") if cvss_v3 else "UNKNOWN"

        # EPSS score (included in NVD 2.0 metrics when available)
        epss_score = None
        epss_list = metrics.get("cvssMetricV2", [])
        # EPSS is not directly in NVD 2.0 — we'll set to None and can query FIRST EPSS API separately

        # CWE IDs
        cwe_ids = []
        for weakness in cve_item.get("weaknesses", []):
            for desc in weakness.get("description", []):
                if desc.get("value", "").startswith("CWE-"):
                    cwe_ids.append(desc["value"])

        # Description
        descriptions = cve_item.get("descriptions", [])
        description = ""
        for d in descriptions:
            if d.get("lang") == "en":
                description = d.get("value", "")
                break

        # References
        references = [
            ref.get("url", "")
            for ref in cve_item.get("references", [])[:10]
        ]

        published = cve_item.get("published", "")
        last_modified = cve_item.get("lastModified", "")

        return {
            "cve_id": cve_id.upper(),
            "cvss_v3_score": cvss_score,
            "cvss_v3_vector": cvss_vector,
            "severity": severity,
            "epss_score": epss_score,
            "cwe_ids": cwe_ids,
            "description": description[:500],  # Truncate for storage
            "references": references,
            "published_date": published,
            "last_modified_date": last_modified,
        }

    def build_feature_vector(self, nvd_data: dict) -> dict:
        """Convert NVD data to numeric feature vector for ML."""
        if not nvd_data:
            return {}

        cvss = nvd_data.get("cvss_v3_score", 0)
        severity_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0, "UNKNOWN": 0}
        severity_num = severity_map.get(nvd_data.get("severity", "UNKNOWN"), 0)

        # Days since publication (recency matters)
        days_since_pub = 365  # default
        pub_date = nvd_data.get("published_date", "")
        if pub_date:
            try:
                pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                days_since_pub = max(0, (datetime.now(pub_dt.tzinfo) - pub_dt).days)
            except Exception:
                pass

        return {
            "nvd_cvss_score": round(cvss, 1),
            "nvd_severity_num": severity_num,
            "nvd_days_since_pub": days_since_pub,
            "nvd_cwe_count": len(nvd_data.get("cwe_ids", [])),
            "nvd_ref_count": len(nvd_data.get("references", [])),
            "nvd_epss_score": nvd_data.get("epss_score") or 0.0,
        }
