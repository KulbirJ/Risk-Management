"""Service layer for compliance framework management and control mappings."""
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from ..models.models import (
    ComplianceFramework, ComplianceControl, ComplianceMapping,
    Threat, Assessment, AuditLog,
)

logger = logging.getLogger(__name__)


# ═══ Framework CRUD ═════════════════════════════════════════════════════════

def list_frameworks(db: Session, tenant_id: str) -> list:
    stmt = select(ComplianceFramework).where(
        ComplianceFramework.tenant_id == tenant_id,
        ComplianceFramework.is_active == True,
    ).order_by(ComplianceFramework.name)
    frameworks = db.execute(stmt).scalars().all()

    # attach control counts
    results = []
    for fw in frameworks:
        count_stmt = select(func.count(ComplianceControl.id)).where(
            ComplianceControl.framework_id == fw.id,
            ComplianceControl.tenant_id == tenant_id,
        )
        count = db.execute(count_stmt).scalar() or 0
        results.append({**fw.__dict__, "control_count": count})
    return results


def get_framework(db: Session, tenant_id: str, framework_id: UUID) -> Optional[ComplianceFramework]:
    stmt = select(ComplianceFramework).where(
        ComplianceFramework.id == framework_id,
        ComplianceFramework.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_framework(db: Session, tenant_id: str, user_id: str, data: dict) -> ComplianceFramework:
    fw = ComplianceFramework(tenant_id=tenant_id, **data)
    db.add(fw)
    db.commit()
    db.refresh(fw)
    _audit(db, tenant_id, user_id, "CREATE", "compliance_framework", str(fw.id))
    return fw


# ═══ Control CRUD ═══════════════════════════════════════════════════════════

def list_controls(
    db: Session, tenant_id: str, framework_id: UUID,
    family: Optional[str] = None, skip: int = 0, limit: int = 200,
) -> list:
    stmt = select(ComplianceControl).where(
        ComplianceControl.tenant_id == tenant_id,
        ComplianceControl.framework_id == framework_id,
    )
    if family:
        stmt = stmt.where(ComplianceControl.family == family)
    stmt = stmt.order_by(ComplianceControl.control_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_control(db: Session, tenant_id: str, control_id: UUID) -> Optional[ComplianceControl]:
    stmt = select(ComplianceControl).where(
        ComplianceControl.id == control_id,
        ComplianceControl.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_control(db: Session, tenant_id: str, user_id: str, data: dict) -> ComplianceControl:
    ctrl = ComplianceControl(tenant_id=tenant_id, **data)
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


# ═══ Mapping CRUD ═══════════════════════════════════════════════════════════

def list_mappings(
    db: Session, tenant_id: str,
    assessment_id: Optional[UUID] = None,
    framework_id: Optional[UUID] = None,
    threat_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> list:
    stmt = select(ComplianceMapping).where(ComplianceMapping.tenant_id == tenant_id)
    if assessment_id:
        stmt = stmt.where(ComplianceMapping.assessment_id == assessment_id)
    if threat_id:
        stmt = stmt.where(ComplianceMapping.threat_id == threat_id)
    if status:
        stmt = stmt.where(ComplianceMapping.status == status)
    if framework_id:
        stmt = stmt.join(ComplianceControl).where(ComplianceControl.framework_id == framework_id)
    return db.execute(stmt).scalars().all()


def create_mapping(db: Session, tenant_id: str, user_id: str, data: dict) -> ComplianceMapping:
    mapping = ComplianceMapping(tenant_id=tenant_id, **data)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    _audit(db, tenant_id, user_id, "CREATE", "compliance_mapping", str(mapping.id))
    return mapping


def update_mapping(db: Session, tenant_id: str, user_id: str, mapping_id: UUID, data: dict) -> Optional[ComplianceMapping]:
    stmt = select(ComplianceMapping).where(
        ComplianceMapping.id == mapping_id,
        ComplianceMapping.tenant_id == tenant_id,
    )
    mapping = db.execute(stmt).scalar_one_or_none()
    if not mapping:
        return None
    old_status = mapping.status
    for k, v in data.items():
        if v is not None:
            setattr(mapping, k, v)
    db.commit()
    db.refresh(mapping)
    _audit(db, tenant_id, user_id, "UPDATE", "compliance_mapping", str(mapping.id),
           changes={"status": {"old": old_status, "new": mapping.status}})
    return mapping


def delete_mapping(db: Session, tenant_id: str, user_id: str, mapping_id: UUID) -> bool:
    stmt = select(ComplianceMapping).where(
        ComplianceMapping.id == mapping_id,
        ComplianceMapping.tenant_id == tenant_id,
    )
    mapping = db.execute(stmt).scalar_one_or_none()
    if not mapping:
        return False
    db.delete(mapping)
    db.commit()
    _audit(db, tenant_id, user_id, "DELETE", "compliance_mapping", str(mapping_id))
    return True


# ═══ Compliance Summary ════════════════════════════════════════════════════

def get_compliance_summary(
    db: Session, tenant_id: str,
    assessment_id: Optional[UUID] = None,
) -> list:
    """Return per-framework compliance posture summary."""
    frameworks_stmt = select(ComplianceFramework).where(
        ComplianceFramework.tenant_id == tenant_id,
        ComplianceFramework.is_active == True,
    )
    frameworks = db.execute(frameworks_stmt).scalars().all()

    summaries = []
    for fw in frameworks:
        total = db.execute(
            select(func.count(ComplianceControl.id)).where(
                ComplianceControl.framework_id == fw.id,
                ComplianceControl.tenant_id == tenant_id,
            )
        ).scalar() or 0

        # Count mappings by status for this framework
        mapping_base = (
            select(
                ComplianceMapping.status,
                func.count(ComplianceMapping.id).label("cnt"),
            )
            .join(ComplianceControl, ComplianceMapping.control_id == ComplianceControl.id)
            .where(
                ComplianceMapping.tenant_id == tenant_id,
                ComplianceControl.framework_id == fw.id,
            )
        )
        if assessment_id:
            mapping_base = mapping_base.where(ComplianceMapping.assessment_id == assessment_id)
        mapping_base = mapping_base.group_by(ComplianceMapping.status)

        rows = db.execute(mapping_base).all()
        status_counts = {r[0]: r[1] for r in rows}

        mapped = sum(status_counts.values())
        compliant = status_counts.get("compliant", 0)
        non_compliant = status_counts.get("non_compliant", 0)
        partial = status_counts.get("partially_compliant", 0)
        na = status_counts.get("not_applicable", 0)
        not_assessed = total - mapped

        # compliance % = (compliant + na) / total * 100
        denom = total - na if (total - na) > 0 else 1
        pct = round((compliant / denom) * 100, 1) if denom > 0 else 0.0

        summaries.append({
            "framework_id": str(fw.id),
            "framework_name": fw.name,
            "framework_key": fw.key,
            "total_controls": total,
            "mapped_controls": mapped,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partially_compliant": partial,
            "not_applicable": na,
            "not_assessed": not_assessed,
            "compliance_pct": pct,
        })
    return summaries


# ═══ Seed frameworks with controls ═════════════════════════════════════════

def seed_frameworks(db: Session, tenant_id: str) -> dict:
    """Seed standard compliance frameworks and their top-level controls for a tenant."""
    results = {"frameworks_created": 0, "controls_created": 0}

    for fw_data in _FRAMEWORK_SEED_DATA:
        # Check if framework already exists for tenant
        existing = db.execute(
            select(ComplianceFramework).where(
                ComplianceFramework.tenant_id == tenant_id,
                ComplianceFramework.key == fw_data["key"],
            )
        ).scalar_one_or_none()
        if existing:
            continue

        fw = ComplianceFramework(
            tenant_id=tenant_id,
            key=fw_data["key"],
            name=fw_data["name"],
            version=fw_data.get("version"),
            description=fw_data.get("description"),
        )
        db.add(fw)
        db.flush()
        results["frameworks_created"] += 1

        for ctrl_data in fw_data.get("controls", []):
            ctrl = ComplianceControl(
                tenant_id=tenant_id,
                framework_id=fw.id,
                control_id=ctrl_data["control_id"],
                title=ctrl_data["title"],
                description=ctrl_data.get("description"),
                family=ctrl_data.get("family"),
                priority=ctrl_data.get("priority"),
            )
            db.add(ctrl)
            results["controls_created"] += 1

    db.commit()
    logger.info(f"Seeded compliance data for tenant {tenant_id}: {results}")
    return results


# ═══ Helpers ════════════════════════════════════════════════════════════════

def _audit(db, tenant_id, user_id, action, entity_type, entity_id, changes=None):
    try:
        log = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            action_type=action,
            resource_type=entity_type,
            resource_id=entity_id,
            changes=changes or {},
        )
        db.add(log)
        db.commit()
    except Exception:
        logger.warning(f"Failed to write audit log for {action} {entity_type}")


# ═══ Seed Data ══════════════════════════════════════════════════════════════

_FRAMEWORK_SEED_DATA = [
    {
        "key": "nist-800-53",
        "name": "NIST SP 800-53 Rev 5",
        "version": "Rev 5",
        "description": "Security and Privacy Controls for Information Systems and Organizations",
        "controls": [
            # Access Control (AC)
            {"control_id": "AC-1", "title": "Policy and Procedures", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-2", "title": "Account Management", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-3", "title": "Access Enforcement", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-4", "title": "Information Flow Enforcement", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-5", "title": "Separation of Duties", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-6", "title": "Least Privilege", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-7", "title": "Unsuccessful Logon Attempts", "family": "Access Control", "priority": "P1"},
            {"control_id": "AC-17", "title": "Remote Access", "family": "Access Control", "priority": "P1"},
            # Audit and Accountability (AU)
            {"control_id": "AU-1", "title": "Policy and Procedures", "family": "Audit and Accountability", "priority": "P1"},
            {"control_id": "AU-2", "title": "Event Logging", "family": "Audit and Accountability", "priority": "P1"},
            {"control_id": "AU-3", "title": "Content of Audit Records", "family": "Audit and Accountability", "priority": "P1"},
            {"control_id": "AU-6", "title": "Audit Record Review, Analysis, and Reporting", "family": "Audit and Accountability", "priority": "P1"},
            {"control_id": "AU-12", "title": "Audit Record Generation", "family": "Audit and Accountability", "priority": "P1"},
            # Configuration Management (CM)
            {"control_id": "CM-1", "title": "Policy and Procedures", "family": "Configuration Management", "priority": "P1"},
            {"control_id": "CM-2", "title": "Baseline Configuration", "family": "Configuration Management", "priority": "P1"},
            {"control_id": "CM-6", "title": "Configuration Settings", "family": "Configuration Management", "priority": "P1"},
            {"control_id": "CM-7", "title": "Least Functionality", "family": "Configuration Management", "priority": "P1"},
            {"control_id": "CM-8", "title": "System Component Inventory", "family": "Configuration Management", "priority": "P1"},
            # Identification and Authentication (IA)
            {"control_id": "IA-1", "title": "Policy and Procedures", "family": "Identification and Authentication", "priority": "P1"},
            {"control_id": "IA-2", "title": "Identification and Authentication (Organizational Users)", "family": "Identification and Authentication", "priority": "P1"},
            {"control_id": "IA-4", "title": "Identifier Management", "family": "Identification and Authentication", "priority": "P1"},
            {"control_id": "IA-5", "title": "Authenticator Management", "family": "Identification and Authentication", "priority": "P1"},
            # Incident Response (IR)
            {"control_id": "IR-1", "title": "Policy and Procedures", "family": "Incident Response", "priority": "P1"},
            {"control_id": "IR-4", "title": "Incident Handling", "family": "Incident Response", "priority": "P1"},
            {"control_id": "IR-5", "title": "Incident Monitoring", "family": "Incident Response", "priority": "P1"},
            {"control_id": "IR-6", "title": "Incident Reporting", "family": "Incident Response", "priority": "P1"},
            # Risk Assessment (RA)
            {"control_id": "RA-1", "title": "Policy and Procedures", "family": "Risk Assessment", "priority": "P1"},
            {"control_id": "RA-3", "title": "Risk Assessment", "family": "Risk Assessment", "priority": "P1"},
            {"control_id": "RA-5", "title": "Vulnerability Monitoring and Scanning", "family": "Risk Assessment", "priority": "P1"},
            # System and Communications Protection (SC)
            {"control_id": "SC-1", "title": "Policy and Procedures", "family": "System and Communications Protection", "priority": "P1"},
            {"control_id": "SC-7", "title": "Boundary Protection", "family": "System and Communications Protection", "priority": "P1"},
            {"control_id": "SC-8", "title": "Transmission Confidentiality and Integrity", "family": "System and Communications Protection", "priority": "P1"},
            {"control_id": "SC-12", "title": "Cryptographic Key Establishment and Management", "family": "System and Communications Protection", "priority": "P1"},
            {"control_id": "SC-13", "title": "Cryptographic Protection", "family": "System and Communications Protection", "priority": "P1"},
            {"control_id": "SC-28", "title": "Protection of Information at Rest", "family": "System and Communications Protection", "priority": "P1"},
            # System and Information Integrity (SI)
            {"control_id": "SI-1", "title": "Policy and Procedures", "family": "System and Information Integrity", "priority": "P1"},
            {"control_id": "SI-2", "title": "Flaw Remediation", "family": "System and Information Integrity", "priority": "P1"},
            {"control_id": "SI-3", "title": "Malicious Code Protection", "family": "System and Information Integrity", "priority": "P1"},
            {"control_id": "SI-4", "title": "System Monitoring", "family": "System and Information Integrity", "priority": "P1"},
            {"control_id": "SI-5", "title": "Security Alerts, Advisories, and Directives", "family": "System and Information Integrity", "priority": "P1"},
        ],
    },
    {
        "key": "iso-27001",
        "name": "ISO/IEC 27001:2022",
        "version": "2022",
        "description": "Information security management systems — Requirements (Annex A controls)",
        "controls": [
            # Annex A.5 — Organizational controls
            {"control_id": "A.5.1", "title": "Policies for information security", "family": "Organizational Controls"},
            {"control_id": "A.5.2", "title": "Information security roles and responsibilities", "family": "Organizational Controls"},
            {"control_id": "A.5.3", "title": "Segregation of duties", "family": "Organizational Controls"},
            {"control_id": "A.5.7", "title": "Threat intelligence", "family": "Organizational Controls"},
            {"control_id": "A.5.8", "title": "Information security in project management", "family": "Organizational Controls"},
            {"control_id": "A.5.10", "title": "Acceptable use of information and other associated assets", "family": "Organizational Controls"},
            {"control_id": "A.5.23", "title": "Information security for use of cloud services", "family": "Organizational Controls"},
            {"control_id": "A.5.24", "title": "Information security incident management planning and preparation", "family": "Organizational Controls"},
            {"control_id": "A.5.25", "title": "Assessment and decision on information security events", "family": "Organizational Controls"},
            {"control_id": "A.5.29", "title": "Information security during disruption", "family": "Organizational Controls"},
            {"control_id": "A.5.30", "title": "ICT readiness for business continuity", "family": "Organizational Controls"},
            # Annex A.6 — People controls
            {"control_id": "A.6.1", "title": "Screening", "family": "People Controls"},
            {"control_id": "A.6.3", "title": "Information security awareness, education and training", "family": "People Controls"},
            {"control_id": "A.6.5", "title": "Responsibilities after termination or change of employment", "family": "People Controls"},
            # Annex A.7 — Physical controls
            {"control_id": "A.7.1", "title": "Physical security perimeters", "family": "Physical Controls"},
            {"control_id": "A.7.4", "title": "Physical security monitoring", "family": "Physical Controls"},
            # Annex A.8 — Technological controls
            {"control_id": "A.8.1", "title": "User endpoint devices", "family": "Technological Controls"},
            {"control_id": "A.8.2", "title": "Privileged access rights", "family": "Technological Controls"},
            {"control_id": "A.8.3", "title": "Information access restriction", "family": "Technological Controls"},
            {"control_id": "A.8.5", "title": "Secure authentication", "family": "Technological Controls"},
            {"control_id": "A.8.7", "title": "Protection against malware", "family": "Technological Controls"},
            {"control_id": "A.8.8", "title": "Management of technical vulnerabilities", "family": "Technological Controls"},
            {"control_id": "A.8.9", "title": "Configuration management", "family": "Technological Controls"},
            {"control_id": "A.8.12", "title": "Data leakage prevention", "family": "Technological Controls"},
            {"control_id": "A.8.15", "title": "Logging", "family": "Technological Controls"},
            {"control_id": "A.8.16", "title": "Monitoring activities", "family": "Technological Controls"},
            {"control_id": "A.8.20", "title": "Networks security", "family": "Technological Controls"},
            {"control_id": "A.8.24", "title": "Use of cryptography", "family": "Technological Controls"},
            {"control_id": "A.8.25", "title": "Secure development life cycle", "family": "Technological Controls"},
            {"control_id": "A.8.28", "title": "Secure coding", "family": "Technological Controls"},
        ],
    },
    {
        "key": "cis-v8",
        "name": "CIS Controls v8",
        "version": "v8",
        "description": "Center for Internet Security Critical Security Controls",
        "controls": [
            {"control_id": "CIS-1", "title": "Inventory and Control of Enterprise Assets", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-2", "title": "Inventory and Control of Software Assets", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-3", "title": "Data Protection", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-4", "title": "Secure Configuration of Enterprise Assets and Software", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-5", "title": "Account Management", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-6", "title": "Access Control Management", "family": "Basic Hygiene", "priority": "IG1"},
            {"control_id": "CIS-7", "title": "Continuous Vulnerability Management", "family": "Foundational", "priority": "IG1"},
            {"control_id": "CIS-8", "title": "Audit Log Management", "family": "Foundational", "priority": "IG1"},
            {"control_id": "CIS-9", "title": "Email and Web Browser Protections", "family": "Foundational", "priority": "IG1"},
            {"control_id": "CIS-10", "title": "Malware Defenses", "family": "Foundational", "priority": "IG1"},
            {"control_id": "CIS-11", "title": "Data Recovery", "family": "Foundational", "priority": "IG1"},
            {"control_id": "CIS-12", "title": "Network Infrastructure Management", "family": "Foundational", "priority": "IG2"},
            {"control_id": "CIS-13", "title": "Network Monitoring and Defense", "family": "Foundational", "priority": "IG2"},
            {"control_id": "CIS-14", "title": "Security Awareness and Skills Training", "family": "Organizational", "priority": "IG1"},
            {"control_id": "CIS-15", "title": "Service Provider Management", "family": "Organizational", "priority": "IG2"},
            {"control_id": "CIS-16", "title": "Application Software Security", "family": "Organizational", "priority": "IG2"},
            {"control_id": "CIS-17", "title": "Incident Response Management", "family": "Organizational", "priority": "IG1"},
            {"control_id": "CIS-18", "title": "Penetration Testing", "family": "Organizational", "priority": "IG3"},
        ],
    },
]
