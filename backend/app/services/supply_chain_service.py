"""
Supply Chain Risk Assessment Service
Implements the CCCS ITSAP.10.070 3-step framework:
  Step 1 — Technology Sensitivity  (weight 35%)
  Step 2 — Supplier Confidence     (weight 40%)
  Step 3 — Deployment Risk         (weight 25%)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..models.models import (
    SupplyChainAssessment,
    SupplyChainDependency,
    SupplyChainVendor,
)
from ..schemas.schemas import (
    SBOMParseRequest,
    SBOMParseResponse,
    SCEnrichDependenciesResponse,
    SCRiskScoreResponse,
    SupplyChainAssessmentCreate,
    SupplyChainAssessmentRead,
    SupplyChainAssessmentUpdate,
    SupplyChainDependencyCreate,
    SupplyChainDependencyRead,
    SupplyChainDependencyUpdate,
    SupplyChainVendorCreate,
    SupplyChainVendorRead,
    SupplyChainVendorUpdate,
)

logger = logging.getLogger(__name__)

# ── CCCS risk level → numeric (1=Low, 2=Medium, 3=High) ──────────────────────

_LEVEL_NUM = {"Low": 1, "Medium": 2, "High": 3}
_NUM_LEVEL = {1: "Low", 2: "Medium", 3: "High"}


def _level_to_num(value: str, default: int = 2) -> int:
    return _LEVEL_NUM.get(value, default)


def _score_to_risk_level(score: int) -> str:
    """Map 0-100 score to Low / Medium / High / Critical."""
    if score < 34:
        return "Low"
    if score < 55:
        return "Medium"
    if score < 75:
        return "High"
    return "Critical"


# ── Step 2 — Supplier Confidence scoring ─────────────────────────────────────

def _compute_vendor_risk_score(vendor: SupplyChainVendor) -> tuple[int, str]:
    """
    Returns (vendor_risk_score 0-100, supplier_confidence_level).
    CCCS Step 2 factors:
      • FOCI risk            (25%)
      • Geopolitical risk    (25%)
      • Business practices   (20%)
      • Cyber maturity avg   (30%) — data_protection + vuln_mgmt + security_policies
    """
    foci = _level_to_num(vendor.foci_risk)
    geo = _level_to_num(vendor.geopolitical_risk)
    biz = _level_to_num(vendor.business_practices_risk)
    dp = _level_to_num(vendor.data_protection_maturity)
    vm = _level_to_num(vendor.vuln_mgmt_maturity)
    sp = _level_to_num(vendor.security_policies_maturity)
    cyber_avg = (dp + vm + sp) / 3.0

    # Cert bonus: −0.2 per recognised cert (up to −0.6)
    cert_bonus = min(len(vendor.security_certifications or []) * 0.2, 0.6)

    weighted = foci * 0.25 + geo * 0.25 + biz * 0.20 + cyber_avg * 0.30
    weighted = max(1.0, weighted - cert_bonus)

    # Normalise to 0-100 (range 1-3 → 0-100)
    score = round((weighted - 1) / 2 * 100)

    # Supplier confidence: HIGH means trustworthy (low risk score)
    if score < 34:
        confidence = "High"
    elif score < 67:
        confidence = "Medium"
    else:
        confidence = "Low"

    return score, confidence


# ── CCCS ITSAP.10.070 overall risk scoring ────────────────────────────────────

def _compute_overall_risk(
    technology_sensitivity: str,
    avg_supplier_risk_score: float,
    cyber_defense_level: str,
) -> tuple[int, str]:
    """
    Step 1 (35%) + Step 2 (40%) + Step 3 (25%) = overall 0-100 score.
    Deployment Risk is inverse of cyber_defense_level:
      High defense → Low deployment risk → lower score.
    """
    sens = _level_to_num(technology_sensitivity)
    supplier_norm = avg_supplier_risk_score / 100 * 2 + 1  # map 0-100 → 1-3
    defense = _level_to_num(cyber_defense_level)
    deploy_risk = 4 - defense  # High defense=3 → deploy_risk=1 (low)

    weighted = sens * 0.35 + supplier_norm * 0.40 + deploy_risk * 0.25
    score = round((weighted - 1) / 2 * 100)
    score = max(0, min(100, score))
    return score, _score_to_risk_level(score)


# ─────────────────────────────────────────────────────────────────────────────
# Assessment CRUD
# ─────────────────────────────────────────────────────────────────────────────

def list_assessments(
    db: Session,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
) -> list[SupplyChainAssessmentRead]:
    stmt = (
        select(SupplyChainAssessment)
        .where(SupplyChainAssessment.tenant_id == tenant_id)
        .order_by(SupplyChainAssessment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(SupplyChainAssessment.status == status)
    rows = db.execute(stmt).scalars().all()

    results: list[SupplyChainAssessmentRead] = []
    for row in rows:
        vendor_stmt = select(func.count()).select_from(SupplyChainVendor).where(
            SupplyChainVendor.assessment_id == row.id
        )
        vendor_count = db.execute(vendor_stmt).scalar_one()
        dep_stmt = select(func.count()).select_from(SupplyChainDependency).where(
            SupplyChainDependency.assessment_id == row.id
        )
        dep_count = db.execute(dep_stmt).scalar_one()
        crit_stmt = select(func.count()).select_from(SupplyChainDependency).where(
            SupplyChainDependency.assessment_id == row.id,
            SupplyChainDependency.risk_level.in_(["High", "Critical"]),
        )
        crit_count = db.execute(crit_stmt).scalar_one()

        read_obj = SupplyChainAssessmentRead.model_validate(row)
        read_obj.vendor_count = vendor_count
        read_obj.dependency_count = dep_count
        read_obj.critical_dependency_count = crit_count
        results.append(read_obj)
    return results


def get_assessment(
    db: Session, tenant_id: UUID, assessment_id: UUID
) -> SupplyChainAssessment | None:
    stmt = select(SupplyChainAssessment).where(
        SupplyChainAssessment.id == assessment_id,
        SupplyChainAssessment.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_assessment(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    payload: SupplyChainAssessmentCreate,
) -> SupplyChainAssessment:
    obj = SupplyChainAssessment(
        id=uuid4(),
        tenant_id=tenant_id,
        owner_user_id=user_id,
        **payload.model_dump(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_assessment(
    db: Session,
    assessment: SupplyChainAssessment,
    payload: SupplyChainAssessmentUpdate,
) -> SupplyChainAssessment:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, field, value)
    assessment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)
    return assessment


def delete_assessment(db: Session, assessment: SupplyChainAssessment) -> None:
    db.delete(assessment)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Vendor CRUD
# ─────────────────────────────────────────────────────────────────────────────

def list_vendors(
    db: Session, tenant_id: UUID, assessment_id: UUID
) -> list[SupplyChainVendorRead]:
    stmt = select(SupplyChainVendor).where(
        SupplyChainVendor.tenant_id == tenant_id,
        SupplyChainVendor.assessment_id == assessment_id,
    )
    rows = db.execute(stmt).scalars().all()
    results: list[SupplyChainVendorRead] = []
    for row in rows:
        dep_count_stmt = select(func.count()).select_from(SupplyChainDependency).where(
            SupplyChainDependency.vendor_id == row.id
        )
        dep_count = db.execute(dep_count_stmt).scalar_one()
        read_obj = SupplyChainVendorRead.model_validate(row)
        read_obj.dependency_count = dep_count
        results.append(read_obj)
    return results


def get_vendor(
    db: Session, tenant_id: UUID, vendor_id: UUID
) -> SupplyChainVendor | None:
    stmt = select(SupplyChainVendor).where(
        SupplyChainVendor.id == vendor_id,
        SupplyChainVendor.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_vendor(
    db: Session,
    tenant_id: UUID,
    payload: SupplyChainVendorCreate,
) -> SupplyChainVendor:
    data = payload.model_dump()
    obj = SupplyChainVendor(id=uuid4(), tenant_id=tenant_id, **data)
    score, confidence = _compute_vendor_risk_score(obj)
    obj.supplier_risk_score = score
    obj.supplier_confidence_level = confidence
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_vendor(
    db: Session,
    vendor: SupplyChainVendor,
    payload: SupplyChainVendorUpdate,
) -> SupplyChainVendor:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    score, confidence = _compute_vendor_risk_score(vendor)
    vendor.supplier_risk_score = score
    vendor.supplier_confidence_level = confidence
    vendor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vendor)
    return vendor


def delete_vendor(db: Session, vendor: SupplyChainVendor) -> None:
    db.delete(vendor)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Dependency CRUD
# ─────────────────────────────────────────────────────────────────────────────

def list_dependencies(
    db: Session,
    tenant_id: UUID,
    assessment_id: UUID,
    vendor_id: Optional[UUID] = None,
    risk_level: Optional[str] = None,
) -> list[SupplyChainDependency]:
    stmt = select(SupplyChainDependency).where(
        SupplyChainDependency.tenant_id == tenant_id,
        SupplyChainDependency.assessment_id == assessment_id,
    )
    if vendor_id:
        stmt = stmt.where(SupplyChainDependency.vendor_id == vendor_id)
    if risk_level:
        stmt = stmt.where(SupplyChainDependency.risk_level == risk_level)
    return db.execute(stmt).scalars().all()


def get_dependency(
    db: Session, tenant_id: UUID, dep_id: UUID
) -> SupplyChainDependency | None:
    stmt = select(SupplyChainDependency).where(
        SupplyChainDependency.id == dep_id,
        SupplyChainDependency.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_dependency(
    db: Session,
    tenant_id: UUID,
    payload: SupplyChainDependencyCreate,
) -> SupplyChainDependency:
    data = payload.model_dump()
    cve_ids = data.pop("cve_ids", []) or []
    cvss_score = data.get("cvss_score")
    obj = SupplyChainDependency(id=uuid4(), tenant_id=tenant_id, cve_ids=cve_ids, **data)
    # Basic rule-based score until ML enrichment runs
    obj.risk_score, obj.risk_level = _rule_based_dep_score(cve_ids, cvss_score, False, False)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_dependency(
    db: Session,
    dep: SupplyChainDependency,
    payload: SupplyChainDependencyUpdate,
) -> SupplyChainDependency:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dep, field, value)
    dep.risk_score, dep.risk_level = _rule_based_dep_score(
        dep.cve_ids or [], dep.cvss_score, dep.is_in_cisa_kev, dep.has_public_poc
    )
    dep.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dep)
    return dep


def delete_dependency(db: Session, dep: SupplyChainDependency) -> None:
    db.delete(dep)
    db.commit()


def _rule_based_dep_score(
    cve_ids: list[str],
    cvss_score: Optional[float],
    in_kev: bool,
    has_poc: bool,
) -> tuple[int, str]:
    """Simple rule-based scoring before ML enrichment."""
    score = 0
    if cve_ids:
        score += min(len(cve_ids) * 10, 30)
    if cvss_score is not None:
        score += int(cvss_score / 10 * 50)
    if in_kev:
        score += 20
    if has_poc:
        score += 10
    score = min(score, 100)
    return score, _score_to_risk_level(score)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Scoring (recalculate whole assessment)
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_risk_score(
    db: Session, tenant_id: UUID, assessment: SupplyChainAssessment
) -> SCRiskScoreResponse:
    vendors = db.execute(
        select(SupplyChainVendor).where(
            SupplyChainVendor.assessment_id == assessment.id,
            SupplyChainVendor.tenant_id == tenant_id,
        )
    ).scalars().all()

    vendor_scores: list[dict[str, Any]] = []
    for v in vendors:
        score, confidence = _compute_vendor_risk_score(v)
        v.supplier_risk_score = score
        v.supplier_confidence_level = confidence
        vendor_scores.append(
            {"vendor_id": str(v.id), "name": v.name, "risk_score": score, "confidence": confidence}
        )

    avg_supplier = (
        sum(v["risk_score"] for v in vendor_scores) / len(vendor_scores)
        if vendor_scores
        else 50.0  # neutral default when no vendors
    )

    overall_score, overall_level = _compute_overall_risk(
        assessment.technology_sensitivity,
        avg_supplier,
        assessment.cyber_defense_level,
    )

    assessment.overall_risk_score = overall_score
    assessment.overall_risk_level = overall_level
    assessment.updated_at = datetime.now(timezone.utc)
    db.commit()

    deps = db.execute(
        select(SupplyChainDependency).where(
            SupplyChainDependency.assessment_id == assessment.id,
            SupplyChainDependency.risk_level.in_(["High", "Critical"]),
        )
    ).scalars().all()

    return SCRiskScoreResponse(
        assessment_id=assessment.id,
        technology_sensitivity=assessment.technology_sensitivity,
        avg_supplier_risk=round(avg_supplier, 1),
        deployment_risk=_num_to_deploy_risk(assessment.cyber_defense_level),
        overall_risk_score=overall_score,
        overall_risk_level=overall_level,
        vendor_scores=vendor_scores,
        dependency_critical_count=len(deps),
    )


def _num_to_deploy_risk(cyber_defense_level: str) -> str:
    """Convert cyber defense level to deployment risk label."""
    mapping = {"High": "Low", "Medium": "Medium", "Low": "High"}
    return mapping.get(cyber_defense_level, "Medium")


# ─────────────────────────────────────────────────────────────────────────────
# SBOM Parsing — CycloneDX JSON + SPDX JSON
# ─────────────────────────────────────────────────────────────────────────────

def parse_sbom(
    assessment_id: UUID,
    tenant_id: UUID,
    payload: SBOMParseRequest,
) -> SBOMParseResponse:
    sbom = payload.sbom_content
    fmt = (payload.sbom_format or "cyclonedx").lower()
    warnings: list[str] = []
    components: list[SupplyChainDependencyCreate] = []

    if fmt == "cyclonedx" or "components" in sbom:
        components, warnings = _parse_cyclonedx(sbom, assessment_id, tenant_id, warnings)
    elif fmt == "spdx" or "packages" in sbom:
        components, warnings = _parse_spdx(sbom, assessment_id, tenant_id, warnings)
    else:
        warnings.append("Unrecognised SBOM format; attempted CycloneDX parse.")
        components, warnings = _parse_cyclonedx(sbom, assessment_id, tenant_id, warnings)

    return SBOMParseResponse(
        format_detected=fmt,
        component_count=len(components),
        components=components,
        warnings=warnings,
    )


def _parse_cyclonedx(
    sbom: dict,
    assessment_id: UUID,
    tenant_id: UUID,
    warnings: list[str],
) -> tuple[list[SupplyChainDependencyCreate], list[str]]:
    raw_components = sbom.get("components", [])
    if not raw_components:
        warnings.append("No 'components' array found in CycloneDX SBOM.")
    result: list[SupplyChainDependencyCreate] = []
    for comp in raw_components:
        pkg_type = _infer_package_type(comp.get("type", ""), comp.get("purl", ""))
        cve_ids: list[str] = []
        cvss: Optional[float] = None
        for vuln in comp.get("vulnerabilities", []):
            vid = vuln.get("id", "")
            if vid.startswith("CVE-"):
                cve_ids.append(vid)
            for rating in vuln.get("ratings", []):
                if rating.get("method", "").upper() == "CVSSV3":
                    try:
                        cvss = max(cvss or 0.0, float(rating["score"]))
                    except (ValueError, TypeError):
                        pass
        result.append(
            SupplyChainDependencyCreate(
                assessment_id=assessment_id,
                name=comp.get("name", "unknown"),
                version=comp.get("version"),
                package_type=pkg_type,
                source="direct",
                license=_extract_cdx_license(comp),
                repository_url=comp.get("externalReferences", [{}])[0].get("url")
                if comp.get("externalReferences")
                else None,
                sbom_source="cyclonedx",
                cve_ids=cve_ids,
                cvss_score=cvss,
            )
        )
    return result, warnings


def _parse_spdx(
    sbom: dict,
    assessment_id: UUID,
    tenant_id: UUID,
    warnings: list[str],
) -> tuple[list[SupplyChainDependencyCreate], list[str]]:
    packages = sbom.get("packages", [])
    if not packages:
        warnings.append("No 'packages' array found in SPDX SBOM.")
    result: list[SupplyChainDependencyCreate] = []
    for pkg in packages:
        if pkg.get("name", "").lower() in {"", "sbom"}:
            continue
        license_str = pkg.get("licenseConcluded") or pkg.get("licenseDeclared")
        result.append(
            SupplyChainDependencyCreate(
                assessment_id=assessment_id,
                name=pkg.get("name", "unknown"),
                version=pkg.get("versionInfo"),
                package_type=_infer_package_type("", pkg.get("downloadLocation", "")),
                source="direct",
                license=license_str if license_str not in {"NOASSERTION", "NONE"} else None,
                repository_url=pkg.get("downloadLocation"),
                sbom_source="spdx",
                cve_ids=[],
                cvss_score=None,
            )
        )
    return result, warnings


def _infer_package_type(comp_type: str, purl: str) -> str:
    purl = purl.lower()
    if "pkg:npm" in purl:
        return "npm"
    if "pkg:pypi" in purl:
        return "pip"
    if "pkg:maven" in purl:
        return "maven"
    if "pkg:nuget" in purl:
        return "nuget"
    if "pkg:gem" in purl:
        return "gem"
    if "pkg:golang" in purl:
        return "go"
    if "pkg:cargo" in purl:
        return "cargo"
    if comp_type.lower() in {"container", "docker"}:
        return "container"
    return comp_type or "unknown"


def _extract_cdx_license(comp: dict) -> Optional[str]:
    licenses = comp.get("licenses", [])
    if not licenses:
        return None
    first = licenses[0]
    if "license" in first:
        return first["license"].get("id") or first["license"].get("name")
    if "expression" in first:
        return first["expression"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ML Enrichment for dependencies
# ─────────────────────────────────────────────────────────────────────────────

def enrich_dependencies_with_ml(
    db: Session,
    tenant_id: UUID,
    assessment_id: UUID,
    dependency_ids: Optional[list[UUID]] = None,
) -> SCEnrichDependenciesResponse:
    """
    Call the ML microservice for dependencies that have CVEs.
    Falls back gracefully if ML_SERVICE_URL is not configured.
    """
    try:
        from ..services.ml_service_client import MLServiceClient  # type: ignore
        ml_client = MLServiceClient()
    except Exception:
        return SCEnrichDependenciesResponse(
            enriched=0, skipped=0, errors=["ML service client not available."]
        )

    stmt = select(SupplyChainDependency).where(
        SupplyChainDependency.tenant_id == tenant_id,
        SupplyChainDependency.assessment_id == assessment_id,
        SupplyChainDependency.ml_enriched.is_(False),
    )
    if dependency_ids:
        stmt = stmt.where(SupplyChainDependency.id.in_(dependency_ids))

    deps = db.execute(stmt).scalars().all()

    enriched_count = 0
    skipped_count = 0
    errors: list[str] = []

    for dep in deps:
        cve_ids = dep.cve_ids or []
        if not cve_ids:
            skipped_count += 1
            continue
        try:
            result = ml_client.enrich_and_score_single(
                threat_id=str(dep.id), cve_ids=cve_ids
            )
            if result:
                dep.risk_score = int(result.get("risk_score", 0) * 100)
                dep.risk_level = result.get("severity", _score_to_risk_level(dep.risk_score))
                dep.is_in_cisa_kev = bool(result.get("in_cisa_kev", False))
                dep.has_public_poc = bool(result.get("has_public_poc", False))
                dep.has_patch = bool(result.get("has_patch", False))
                dep.epss_score = result.get("epss_score") or result.get("epss")
                dep.feature_vector = result.get("feature_vector")
                dep.ml_enriched = True
                dep.enriched_at = datetime.now(timezone.utc)
                enriched_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            errors.append(f"{dep.name}: {exc}")
            skipped_count += 1

    db.commit()
    return SCEnrichDependenciesResponse(
        enriched=enriched_count, skipped=skipped_count, errors=errors
    )
