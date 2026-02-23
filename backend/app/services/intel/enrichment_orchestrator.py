"""
Dual-Track Enrichment Orchestrator — Phase 1 core engine.

Coordinates Track A (CVE-based) and Track B (Non-CVE / ATT&CK-based) enrichment
for each threat, merges results into a unified feature vector, and persists to
the threat_intel_enrichments table.
"""
import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ...core.config import settings
from ...models.models import (
    Threat, ThreatIntelEnrichment, ThreatAttackMapping,
    AttackTechnique, AttackGroup, Assessment,
)
from .nvd_service import NVDService
from .cisa_kev_service import CISAKEVService
from .otx_service import OTXService
from .github_exploit_service import GitHubExploitService
from .sector_frequency_service import SectorFrequencyService

logger = logging.getLogger(__name__)


class EnrichmentOrchestrator:
    """
    Runs dual-track enrichment for a set of threats.

    Track A (CVE-based): NVD → CISA KEV → OTX by CVE → GitHub PoC
    Track B (Non-CVE):   ATT&CK Groups → OTX by technique → Sector Frequency
    
    Both tracks produce normalised feature vectors that are merged into a single
    unified vector stored on ThreatIntelEnrichment records.
    """

    def __init__(self):
        self.nvd = NVDService()
        self.kev = CISAKEVService()
        self.otx = OTXService()
        self.github = GitHubExploitService()
        self.sector = SectorFrequencyService()

    async def enrich_threats(
        self,
        db: Session,
        tenant_id: UUID,
        threat_ids: Optional[List[UUID]] = None,
        assessment_id: Optional[UUID] = None,
        force_refresh: bool = False,
    ) -> dict:
        """
        Run dual-track enrichment for the given threats or all threats in an assessment.
        
        Returns summary dict with counts and errors.
        """
        # Resolve threat list
        query = db.query(Threat).filter(Threat.tenant_id == tenant_id)
        if threat_ids:
            query = query.filter(Threat.id.in_(threat_ids))
        elif assessment_id:
            query = query.filter(Threat.assessment_id == assessment_id)
        else:
            return {"error": "Must specify threat_ids or assessment_id"}

        threats = query.all()
        if not threats:
            return {"threats_enriched": 0, "errors": ["No threats found"]}

        # Determine sector from assessment
        sector = "default"
        if assessment_id:
            assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
            if assessment and getattr(assessment, 'industry_sector', None):
                sector = str(assessment.industry_sector).lower()
        elif threats:
            assessment = db.query(Assessment).filter(
                Assessment.id == threats[0].assessment_id
            ).first()
            if assessment and getattr(assessment, 'industry_sector', None):
                sector = str(assessment.industry_sector).lower()

        results = {
            "threats_enriched": 0,
            "enrichments_created": 0,
            "enrichments_updated": 0,
            "errors": [],
            "feature_summary": {},
        }

        for threat in threats:
            try:
                enrichment_count = await self._enrich_single_threat(
                    db, tenant_id, threat, sector, force_refresh
                )
                results["threats_enriched"] += 1
                results["enrichments_created"] += enrichment_count.get("created", 0)
                results["enrichments_updated"] += enrichment_count.get("updated", 0)
            except Exception as e:
                error_msg = f"Error enriching threat {threat.id}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results

    async def _enrich_single_threat(
        self,
        db: Session,
        tenant_id: UUID,
        threat: Threat,
        sector: str,
        force_refresh: bool,
    ) -> dict:
        """Enrich a single threat with both tracks."""
        counts = {"created": 0, "updated": 0}
        unified_features: Dict[str, Any] = {}
        cache_ttl = timedelta(hours=settings.intel_cache_ttl_hours)

        # ──────────────── TRACK A: CVE-based ────────────────
        cve_ids = list(threat.cve_ids or [])  # type: ignore[arg-type]
        has_cves = len(cve_ids) > 0

        if has_cves:
            for cve_id in cve_ids[:5]:  # Cap at 5 CVEs per threat
                # NVD
                nvd_result = await self._fetch_and_store(
                    db, tenant_id, threat.id, "nvd", cve_id,
                    self.nvd.get_cve, self.nvd.build_feature_vector,
                    cache_ttl, force_refresh, counts
                )
                if nvd_result:
                    unified_features.update(nvd_result)

                # CISA KEV
                kev_result = await self._fetch_and_store(
                    db, tenant_id, threat.id, "cisa_kev", cve_id,
                    self.kev.check_cve, self.kev.build_feature_vector,
                    cache_ttl, force_refresh, counts
                )
                if kev_result:
                    unified_features.update(kev_result)

                # OTX by CVE
                otx_cve_result = await self._fetch_and_store(
                    db, tenant_id, threat.id, "otx_cve", cve_id,
                    self.otx.get_pulses_by_cve, self.otx.build_feature_vector_cve,
                    cache_ttl, force_refresh, counts
                )
                if otx_cve_result:
                    unified_features.update(otx_cve_result)

                # GitHub PoC
                github_result = await self._fetch_and_store(
                    db, tenant_id, threat.id, "github_poc", cve_id,
                    self.github.search_exploits, self.github.build_feature_vector,
                    cache_ttl, force_refresh, counts
                )
                if github_result:
                    unified_features.update(github_result)

        # ──────────────── TRACK B: Non-CVE / ATT&CK-based ────────────────

        # ATT&CK technique-based enrichment (runs for ALL threats, CVE or not)
        technique_ids = self._get_mapped_technique_ids(db, str(threat.id))  # type: ignore[arg-type]

        if technique_ids:
            # OTX by technique (aggregate across all mapped techniques)
            agg_tech_pulses = 0
            agg_tech_adversaries = set()
            for tech_mitre_id in technique_ids[:5]:
                otx_tech = await self.otx.get_pulses_by_technique(tech_mitre_id)
                if otx_tech:
                    agg_tech_pulses += otx_tech.get("pulse_count", 0)
                    agg_tech_adversaries.update(otx_tech.get("adversary_names", []))

            otx_tech_features = {
                "otx_tech_pulse_count": agg_tech_pulses,
                "otx_tech_adversary_count": len(agg_tech_adversaries),
            }
            unified_features.update(otx_tech_features)

            # ATT&CK Groups (how many known threat groups use these techniques)
            group_count, group_names = self._count_attack_groups(db, technique_ids)
            unified_features["attack_group_count"] = group_count
            unified_features["attack_group_names"] = group_names[:10]

            # Store attack_group enrichment record
            self._upsert_enrichment(
                db, tenant_id, threat.id, "attack_group",
                source_id=",".join(technique_ids[:5]),
                raw_data={"group_count": group_count, "group_names": group_names[:10]},
                feature_vector={"attack_group_count": group_count},
                severity_score=min(100, group_count * 15),  # More groups → higher severity
                cache_ttl=cache_ttl, counts=counts,
            )

        # Sector frequency (runs for ALL threats with a catalogue_key)
        cat_key = str(threat.catalogue_key) if threat.catalogue_key else None  # type: ignore[truthy-bool]
        if cat_key:
            freq_data = self.sector.get_frequency(sector, cat_key)
            freq_features = self.sector.build_feature_vector(freq_data)
            unified_features.update(freq_features)

            self._upsert_enrichment(
                db, tenant_id, threat.id, "sector_freq",
                source_id=f"{sector}:{cat_key}",
                raw_data=freq_data or {},
                feature_vector=freq_features,
                severity_score=freq_data.get("sector_percentile", 50) if freq_data else 50,
                cache_ttl=timedelta(days=30),  # Sector data is static
                counts=counts,
            )

        # Technique count feature
        unified_features["mapped_technique_count"] = len(technique_ids)
        unified_features["has_cve"] = 1 if has_cves else 0
        unified_features["cve_count"] = len(cve_ids)

        # ──────────────── Compute preliminary likelihood score ────────────────
        likelihood_score = self._compute_likelihood_score(unified_features)

        # Update the threat record
        threat.intel_enriched = True  # type: ignore[assignment]
        threat.likelihood_score = likelihood_score  # type: ignore[assignment]
        threat.likelihood_score_rationale = unified_features  # type: ignore[assignment]

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update threat {threat.id}: {e}")

        return counts

    async def _fetch_and_store(
        self, db, tenant_id, threat_id, source, source_id,
        fetch_fn, feature_fn, cache_ttl, force_refresh, counts
    ) -> Optional[dict]:
        """Fetch from external API, compute features, and store enrichment record."""
        # Check cache
        if not force_refresh:
            existing = db.query(ThreatIntelEnrichment).filter(
                ThreatIntelEnrichment.threat_id == threat_id,
                ThreatIntelEnrichment.source == source,
                ThreatIntelEnrichment.source_id == source_id,
                ThreatIntelEnrichment.is_stale == False,
            ).first()
            if existing and existing.expires_at and existing.expires_at > datetime.utcnow():
                return existing.feature_vector

        # Fetch from external API
        try:
            raw_data = await fetch_fn(source_id)
        except Exception as e:
            logger.warning(f"Fetch error {source}/{source_id}: {e}")
            return None

        if raw_data is None:
            return None

        # Compute features
        features = feature_fn(raw_data)
        severity = self._estimate_severity(source, raw_data)

        self._upsert_enrichment(
            db, tenant_id, threat_id, source, source_id,
            raw_data, features, severity, cache_ttl, counts
        )

        return features

    def _upsert_enrichment(
        self, db, tenant_id, threat_id, source, source_id,
        raw_data, feature_vector, severity_score, cache_ttl, counts
    ):
        """Insert or update an enrichment record."""
        existing = db.query(ThreatIntelEnrichment).filter(
            ThreatIntelEnrichment.threat_id == threat_id,
            ThreatIntelEnrichment.source == source,
        ).first()

        now = datetime.utcnow()

        if existing:
            existing.source_id = source_id
            existing.raw_data = raw_data
            existing.feature_vector = feature_vector
            existing.severity_score = severity_score
            existing.fetched_at = now
            existing.expires_at = now + cache_ttl
            existing.is_stale = False
            counts["updated"] += 1
        else:
            enrichment = ThreatIntelEnrichment(
                tenant_id=tenant_id,
                threat_id=threat_id,
                source=source,
                source_id=source_id,
                raw_data=raw_data,
                feature_vector=feature_vector,
                severity_score=severity_score,
                fetched_at=now,
                expires_at=now + cache_ttl,
            )
            db.add(enrichment)
            counts["created"] += 1

        try:
            db.flush()
        except Exception as e:
            db.rollback()
            logger.error(f"DB error upserting enrichment {source}/{source_id}: {e}")

    def _get_mapped_technique_ids(self, db: Session, threat_id) -> List[str]:
        """Get MITRE IDs of techniques mapped to this threat."""
        mappings = (
            db.query(AttackTechnique.mitre_id)
            .join(ThreatAttackMapping, ThreatAttackMapping.technique_id == AttackTechnique.id)
            .filter(ThreatAttackMapping.threat_id == threat_id)
            .all()
        )
        return [m[0] for m in mappings if m[0]]

    def _count_attack_groups(self, db: Session, technique_mitre_ids: List[str]) -> tuple:
        """Count ATT&CK groups that use any of the given techniques."""
        if not technique_mitre_ids:
            return 0, []

        # AttackGroup stores technique STIX IDs — we need to map mitre_ids to stix_ids
        stix_ids = (
            db.query(AttackTechnique.stix_id)
            .filter(AttackTechnique.mitre_id.in_(technique_mitre_ids))
            .all()
        )
        stix_id_set = {s[0] for s in stix_ids}

        if not stix_id_set:
            return 0, []

        groups = db.query(AttackGroup).all()
        matching_groups = []
        for group in groups:
            group_techniques = set(list(group.technique_ids or []))  # type: ignore[arg-type]
            if group_techniques & stix_id_set:
                matching_groups.append(group.name)

        return len(matching_groups), sorted(matching_groups)

    def _estimate_severity(self, source: str, raw_data: dict) -> int:
        """Estimate a 0-100 severity score from raw data."""
        if source == "nvd":
            cvss = raw_data.get("cvss_v3_score", 0)
            return min(100, int(cvss * 10))
        elif source == "cisa_kev":
            # KEV-listed = high severity by definition
            return 85 if raw_data.get("known_ransomware_use") else 75
        elif source == "otx_cve":
            pulses = raw_data.get("pulse_count", 0)
            return min(100, pulses * 5)
        elif source == "github_poc":
            count = raw_data.get("repo_count", 0)
            return min(100, count * 10)
        return 50

    def _compute_likelihood_score(self, features: dict) -> int:
        """
        Compute a preliminary likelihood score (0-100) from the unified feature vector.
        
        This is a rule-based heuristic. Phase 2 replaces this with an ML model.
        
        Weights:
          - CVSS score (0-10 → 0-30 points)
          - KEV listed (+20 points)
          - KEV ransomware (+5 points)
          - OTX pulse count (0-15 points)
          - GitHub PoC count (0-10 points)
          - ATT&CK group count (0-10 points)
          - Sector percentile (0-10 points)
        """
        score = 0.0

        # CVSS score contribution (max 30 points)
        cvss = features.get("nvd_cvss_score", 0)
        score += min(30, cvss * 3)

        # KEV listed (20 points)
        if features.get("kev_listed", 0):
            score += 20
            if features.get("kev_ransomware", 0):
                score += 5

        # OTX activity (max 15 points)
        otx_cve_pulses = features.get("otx_cve_pulse_count", 0)
        otx_tech_pulses = features.get("otx_tech_pulse_count", 0)
        total_pulses = otx_cve_pulses + otx_tech_pulses
        score += min(15, total_pulses * 1.5)

        # GitHub PoC (max 10 points)
        poc_count = features.get("github_poc_count", 0)
        score += min(10, poc_count * 2)

        # ATT&CK groups (max 10 points)
        group_count = features.get("attack_group_count", 0)
        score += min(10, group_count * 2)

        # Sector frequency percentile (max 10 points)
        percentile = features.get("sector_percentile", 50)
        score += (percentile / 100) * 10

        # Non-CVE base: if no CVE but has techniques, give minimum floor
        if not features.get("has_cve") and features.get("mapped_technique_count", 0) > 0:
            score = max(score, 15)  # Floor of 15 for mapped threats without CVE

        return min(100, max(0, int(round(score))))

    async def get_enrichment_summary(
        self, db: Session, tenant_id: UUID, threat_id: UUID
    ) -> Optional[dict]:
        """Get combined enrichment summary for a single threat."""
        threat = db.query(Threat).filter(
            Threat.id == threat_id,
            Threat.tenant_id == tenant_id,
        ).first()
        if not threat:
            return None

        enrichments = db.query(ThreatIntelEnrichment).filter(
            ThreatIntelEnrichment.threat_id == threat_id,
        ).all()

        sources = []
        cve_data = {}
        otx_data = {}
        exploit_data = {}
        sector_frequency = {}
        attack_groups = []
        most_recent = None

        for e in enrichments:
            src = str(e.source)
            fetched = e.fetched_at
            sources.append(src)
            if fetched and (most_recent is None or fetched > most_recent):  # type: ignore[operator]
                most_recent = fetched

            if src == "nvd":
                cve_data["nvd"] = e.raw_data
            elif src == "cisa_kev":
                cve_data["kev"] = e.raw_data
            elif src in ("otx_cve", "otx_technique"):
                otx_data[src] = e.raw_data
            elif src == "github_poc":
                exploit_data = e.raw_data or {}  # type: ignore[assignment]
            elif src == "sector_freq":
                sector_frequency = e.raw_data or {}  # type: ignore[assignment]
            elif src == "attack_group":
                raw = e.raw_data or {}  # type: ignore[assignment]
                attack_groups = raw.get("group_names", []) if isinstance(raw, dict) else []

        return {
            "threat_id": str(threat.id),
            "threat_title": threat.title,
            "intel_enriched": threat.intel_enriched,
            "likelihood_score": threat.likelihood_score,
            "sources": sources,
            "feature_vector": threat.likelihood_score_rationale,
            "cve_data": cve_data if cve_data else None,
            "otx_data": otx_data if otx_data else None,
            "exploit_data": exploit_data or None,  # type: ignore[truthy-bool]
            "sector_frequency": sector_frequency or None,  # type: ignore[truthy-bool]
            "attack_groups": [{"name": g} for g in attack_groups] if attack_groups else None,
            "enriched_at": most_recent.isoformat() if most_recent else None,  # type: ignore[union-attr]
        }
