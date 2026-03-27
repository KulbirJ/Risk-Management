"""AlienVault OTX client — Dual-track enrichment (CVE + Technique-based pulses)."""
import logging
from typing import Optional, List
import httpx

from ...core.config import settings

logger = logging.getLogger(__name__)

OTX_TIMEOUT = 20  # seconds


class OTXService:
    """
    Fetch threat intelligence pulses from AlienVault OTX.
    
    Track A: Query by CVE ID → pulse count, adversary names, targeted countries.
    Track B: Query by ATT&CK technique ID → pulse count, related adversaries.
    """

    def __init__(self):
        self.base_url = settings.otx_api_base
        self.api_key = settings.otx_api_key

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-OTX-API-KEY"] = self.api_key
        return headers

    async def get_pulses_by_cve(self, cve_id: str) -> Optional[dict]:
        """
        Fetch OTX pulses referencing a specific CVE.
        
        Returns:
          - pulse_count, adversary_names, targeted_countries
          - recent_pulse_date, tags
        """
        if not cve_id:
            return None

        url = f"{self.base_url}/indicators/CVE/{cve_id}/general"
        try:
            async with httpx.AsyncClient(timeout=OTX_TIMEOUT) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json()

            pulse_info = data.get("pulse_info", {})
            pulses = pulse_info.get("pulses", [])

            adversaries = set()
            countries = set()
            tags = set()
            recent_date = None

            for pulse in pulses[:50]:  # Cap processing
                for adv in pulse.get("adversary", "") or "":
                    pass  # adversary is a string, not list
                adv = pulse.get("adversary", "")
                if adv:
                    adversaries.add(adv)
                for tag in pulse.get("tags", []):
                    tags.add(tag.lower())
                for tc in pulse.get("targeted_countries", []):
                    countries.add(tc)
                created = pulse.get("created", "")
                if created and (not recent_date or created > recent_date):
                    recent_date = created

            return {
                "cve_id": cve_id.upper(),
                "pulse_count": pulse_info.get("count", len(pulses)),
                "adversary_names": sorted(adversaries),
                "targeted_countries": sorted(countries),
                "tags": sorted(tags)[:20],
                "recent_pulse_date": recent_date,
            }

        except httpx.HTTPStatusError as e:
            logger.warning(f"OTX HTTP error for CVE {cve_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"OTX fetch error for CVE {cve_id}: {e}")
            return None

    async def get_pulses_by_technique(self, technique_id: str) -> Optional[dict]:
        """
        Track B: Fetch OTX pulses referencing a MITRE ATT&CK technique ID.
        
        Returns:
          - pulse_count, adversary_names, tags
        """
        if not technique_id:
            return None

        # OTX does not have a direct technique endpoint; search by tag
        url = f"{self.base_url}/search/pulses"
        params = {"q": technique_id, "limit": 20}

        try:
            async with httpx.AsyncClient(timeout=OTX_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=self._headers())
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", [])

            adversaries = set()
            tags = set()
            recent_date = None

            for pulse in results:
                adv = pulse.get("adversary", "")
                if adv:
                    adversaries.add(adv)
                for tag in pulse.get("tags", []):
                    tags.add(tag.lower())
                modified = pulse.get("modified", "")
                if modified and (not recent_date or modified > recent_date):
                    recent_date = modified

            return {
                "technique_id": technique_id,
                "pulse_count": data.get("count", len(results)),
                "adversary_names": sorted(adversaries),
                "tags": sorted(tags)[:20],
                "recent_pulse_date": recent_date,
            }

        except httpx.HTTPStatusError as e:
            logger.warning(f"OTX HTTP error for technique {technique_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"OTX fetch error for technique {technique_id}: {e}")
            return None

    def build_feature_vector_cve(self, otx_data: Optional[dict]) -> dict:
        """Numeric features from CVE-based OTX data."""
        if not otx_data:
            return {"otx_cve_pulse_count": 0, "otx_cve_adversary_count": 0}
        return {
            "otx_cve_pulse_count": otx_data.get("pulse_count", 0),
            "otx_cve_adversary_count": len(otx_data.get("adversary_names", [])),
            "otx_cve_country_count": len(otx_data.get("targeted_countries", [])),
        }

    def build_feature_vector_technique(self, otx_data: Optional[dict]) -> dict:
        """Numeric features from technique-based OTX data."""
        if not otx_data:
            return {"otx_tech_pulse_count": 0, "otx_tech_adversary_count": 0}
        return {
            "otx_tech_pulse_count": otx_data.get("pulse_count", 0),
            "otx_tech_adversary_count": len(otx_data.get("adversary_names", [])),
        }
