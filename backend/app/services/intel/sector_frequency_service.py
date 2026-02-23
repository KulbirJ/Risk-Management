"""Sector-specific threat frequency — Track B: Non-CVE enrichment."""
import json
import logging
import os
from typing import Optional

from ...core.config import settings

logger = logging.getLogger(__name__)


class SectorFrequencyService:
    """
    Look up annualised threat incident frequency for a given sector + threat type.
    
    Uses static reference data derived from Verizon DBIR, IBM X-Force, and ENISA reports.
    """

    def __init__(self):
        self._data: Optional[dict] = None

    def _load(self) -> dict:
        if self._data is not None:
            return self._data

        # Resolve path relative to this file's location, which works in both
        # local dev and Lambda (where CWD-relative paths fail).
        # __file__ = .../backend/app/services/intel/sector_frequency_service.py
        # data file = .../backend/app/data/sector_threat_frequency.json
        _here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(_here, "..", "..", "data", "sector_threat_frequency.json"))

        # Allow override via settings (absolute paths only to avoid CWD ambiguity)
        configured = settings.sector_threat_frequency_path
        if configured and os.path.isabs(configured):
            path = configured

        try:
            with open(path, "r") as f:
                self._data = json.load(f)
            logger.info(f"Loaded sector threat frequency data from {path}")
        except FileNotFoundError:
            logger.warning(f"Sector frequency file not found: {path}")
            self._data = {"sectors": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in sector frequency file: {e}")
            self._data = {"sectors": {}}

        return self._data

    def get_frequency(self, sector: str, catalogue_key: str) -> Optional[dict]:
        """
        Get threat frequency for a specific sector and catalogue key.

        Args:
            sector: Industry sector slug (e.g., "finance", "healthcare")
            catalogue_key: Threat catalogue key (e.g., "ransomware", "phishing")

        Returns:
            Dict with frequency and percentile data, or None.
        """
        data = self._load()
        sectors = data.get("sectors", {})

        # Fall back to "default" if sector not found
        sector_data = sectors.get(sector, sectors.get("default", {}))
        threats = sector_data.get("threats", {})

        freq = threats.get(catalogue_key)
        if freq is None:
            # Try common aliases
            alias_map = {
                "malware": "malicious_code",
                "dos": "denial_of_service",
                "brute_force": "credential_theft",
                "sql_injection": "web_application_attack",
                "xss": "web_application_attack",
            }
            alt_key = alias_map.get(catalogue_key)
            if alt_key:
                freq = threats.get(alt_key)

        if freq is None:
            return None

        # Compute percentile relative to all threats in this sector
        all_freqs = sorted(threats.values())
        rank = sum(1 for f in all_freqs if f <= freq)
        percentile = round(rank / len(all_freqs) * 100) if all_freqs else 50

        # Compute frequency relative to cross-sector average
        default_threats = sectors.get("default", {}).get("threats", {})
        avg_freq = default_threats.get(catalogue_key, 50)
        relative_ratio = round(freq / avg_freq, 2) if avg_freq > 0 else 1.0

        return {
            "sector": sector,
            "catalogue_key": catalogue_key,
            "annual_frequency_per_1k": freq,
            "sector_percentile": percentile,
            "relative_to_average": relative_ratio,
            "sector_display_name": sector_data.get("display_name", sector),
        }

    def get_all_sectors(self) -> list:
        """Return list of available sectors."""
        data = self._load()
        return [
            {"slug": k, "display_name": v.get("display_name", k)}
            for k, v in data.get("sectors", {}).items()
            if k != "_meta"
        ]

    def build_feature_vector(self, freq_data: Optional[dict]) -> dict:
        """Numeric features from sector frequency data."""
        if not freq_data:
            return {
                "sector_freq_annual": 0,
                "sector_percentile": 50,
                "sector_relative_ratio": 1.0,
            }
        return {
            "sector_freq_annual": freq_data.get("annual_frequency_per_1k", 0),
            "sector_percentile": freq_data.get("sector_percentile", 50),
            "sector_relative_ratio": freq_data.get("relative_to_average", 1.0),
        }
