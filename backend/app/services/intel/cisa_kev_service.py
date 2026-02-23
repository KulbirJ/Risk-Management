"""CISA Known Exploited Vulnerabilities (KEV) client — Track A: CVE-based enrichment."""
import logging
from typing import Optional, Set
import httpx
from datetime import datetime

from ...core.config import settings

logger = logging.getLogger(__name__)

CISA_TIMEOUT = 30  # seconds


class CISAKEVService:
    """Check CVEs against the CISA Known Exploited Vulnerabilities catalogue."""

    def __init__(self):
        self.kev_url = settings.cisa_kev_url
        self._kev_cache: dict = {}  # {cve_id: kev_entry}
        self._cache_loaded_at: Optional[datetime] = None

    async def _load_catalogue(self, force: bool = False) -> None:
        """Download and cache the full KEV catalogue (updated daily by CISA)."""
        if not force and self._kev_cache and self._cache_loaded_at:
            age_hours = (datetime.utcnow() - self._cache_loaded_at).total_seconds() / 3600
            if age_hours < settings.intel_cache_ttl_hours:
                return

        try:
            async with httpx.AsyncClient(timeout=CISA_TIMEOUT) as client:
                resp = await client.get(self.kev_url)
                resp.raise_for_status()
                data = resp.json()

            vulnerabilities = data.get("vulnerabilities", [])
            self._kev_cache = {
                v["cveID"]: v for v in vulnerabilities if "cveID" in v
            }
            self._cache_loaded_at = datetime.utcnow()
            logger.info(f"CISA KEV: Loaded {len(self._kev_cache)} entries")

        except Exception as e:
            logger.error(f"CISA KEV load error: {e}")

    async def check_cve(self, cve_id: str) -> Optional[dict]:
        """
        Check if a CVE is in the KEV catalogue.

        Returns normalised dict:
          - is_kev: True
          - vendor_project, product, vulnerability_name
          - date_added, due_date, required_action
          - known_ransomware_campaign_use
        """
        if not cve_id:
            return None

        await self._load_catalogue()

        entry = self._kev_cache.get(cve_id.upper())
        if not entry:
            return None

        return {
            "cve_id": cve_id.upper(),
            "is_kev": True,
            "vendor_project": entry.get("vendorProject", ""),
            "product": entry.get("product", ""),
            "vulnerability_name": entry.get("vulnerabilityName", ""),
            "date_added": entry.get("dateAdded", ""),
            "due_date": entry.get("dueDate", ""),
            "required_action": entry.get("requiredAction", ""),
            "known_ransomware_use": entry.get("knownRansomwareCampaignUse", "Unknown") == "Known",
            "notes": entry.get("notes", ""),
        }

    async def get_kev_cve_set(self) -> Set[str]:
        """Return the set of all CVE IDs in the KEV catalogue."""
        await self._load_catalogue()
        return set(self._kev_cache.keys())

    def build_feature_vector(self, kev_data: Optional[dict]) -> dict:
        """Convert KEV data to numeric features."""
        if not kev_data:
            return {
                "kev_listed": 0,
                "kev_ransomware": 0,
                "kev_days_since_added": 0,
            }

        days_since_added = 0
        date_added = kev_data.get("date_added", "")
        if date_added:
            try:
                added_dt = datetime.strptime(date_added, "%Y-%m-%d")
                days_since_added = max(0, (datetime.utcnow() - added_dt).days)
            except Exception:
                pass

        return {
            "kev_listed": 1,
            "kev_ransomware": 1 if kev_data.get("known_ransomware_use") else 0,
            "kev_days_since_added": days_since_added,
        }
