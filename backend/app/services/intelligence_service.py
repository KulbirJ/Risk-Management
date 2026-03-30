"""Intelligence service for AI-powered assessment enrichment.

Uses async Lambda self-invocation with per-item Bedrock calls.
Each input (assessment metadata, individual evidence files) gets its own
focused Bedrock call, keeping prompts small and responses fast.
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.models import (
    Assessment, Threat, Recommendation, ThreatCatalogue, Evidence, IntelligenceJob,
    ThreatAttackMapping, KillChain, ActiveRisk, ThreatIntelEnrichment,
)
from ..services.bedrock_service import bedrock_service
from ..core.config import settings

logger = logging.getLogger(__name__)

# Max chars of evidence text per Bedrock call
MAX_CHARS_PER_FILE = 15000
# Max findings from assessment metadata analysis
MAX_FINDINGS_METADATA = 5
# Max findings from a single evidence file analysis
MAX_FINDINGS_PER_FILE = 8


def _system_prompt(max_findings: int) -> str:
    """Shared system prompt for all Bedrock calls (backward-compatible wrapper)."""
    return _system_prompt_for_type("other", max_findings)


def _system_prompt_for_type(document_type: str, max_findings: int) -> str:
    """Return a document-type-specific system prompt with the appropriate analyst persona."""

    _JSON_SCHEMA = """Return valid JSON with this exact structure:
{{
  "summary": "2-3 sentence plain-English summary of what was found in this document",
  "risk_indicators": {{
    "critical_vulns": 0,
    "high_vulns": 0,
    "exposed_services": [],
    "missing_controls": [],
    "compliance_gaps": [],
    "secrets_found": 0,
    "key_concerns": ["one-liner concern"]
  }},
  "findings": [
    {{
      "vulnerability": "Brief vulnerability title",
      "description": "What the vulnerability is and why it matters",
      "severity": "critical|high|medium|low",
      "catalogue_key": "matching key from threat catalogue",
      "likelihood": 7,
      "impact": 8,
      "justification": "Why these scores were assigned",
      "source": "what input this finding came from",
      "cve_ids": ["CVE-2023-1234", "CVE-2024-5678"],
      "recommendations": [
        "Specific actionable mitigation step 1",
        "Specific actionable mitigation step 2"
      ]
    }}
  ]
}}"""

    _COMMON_RULES = f"""Rules:
- Return up to {max_findings} findings
- likelihood and impact must be integers 1-10
- catalogue_key MUST match one from the provided catalogue — pick closest match
- Each finding must have 2-3 specific, actionable recommendations
- severity must be one of: critical, high, medium, low
- cve_ids MUST be populated with any CVE identifiers mentioned in the document (e.g. CVE-2023-1234). Use an empty array [] if none apply.
- Return ONLY the JSON object, no markdown, no explanation
- Identify SPECIFIC, CONCRETE threats — reference CVEs, misconfigurations, or architectural weaknesses where applicable
- Do NOT produce generic or vague findings
- The "summary" field must be a concise 2-3 sentence overview of the document's security posture
- The "risk_indicators" field must reflect what you actually found — use 0 / empty arrays where nothing applies"""

    _PERSONAS = {
        "vulnerability_scan": f"""You are a senior vulnerability triage analyst. You specialize in analyzing vulnerability scan outputs (Nessus, Qualys, OpenVAS, nmap, etc.) and prioritizing remediation.

When analyzing this scan output:
- Prioritize findings by real-world exploitability, not just CVSS score alone
- Identify false positives where context suggests the finding is non-exploitable
- Group related CVEs that affect the same component or attack surface
- Assess blast radius — what could an attacker reach from each vulnerable service?
- Flag any CVEs known to be actively exploited in the wild (CISA KEV candidates)
- Note missing patches, end-of-life software, and unsupported versions
- Identify exposed administrative interfaces and default credentials

{_JSON_SCHEMA}

{_COMMON_RULES}""",

        "architecture_doc": f"""You are a senior security architect reviewer. You specialize in reviewing system architecture documents, network diagrams, and design documents to identify security gaps.

When analyzing this architecture document:
- Identify missing security controls (no WAF, no encryption at rest, no MFA, missing SIEM integration)
- Evaluate trust boundaries — where does trusted meet untrusted traffic?
- Assess network segmentation — are high-value assets isolated from general traffic?
- Flag overly permissive access patterns (e.g., 0.0.0.0/0 ingress rules, wildcard IAM policies)
- Identify data flow risks — where does sensitive data transit without encryption?
- Check for single points of failure in security-critical paths
- Note any publicly exposed management interfaces or debug endpoints
- Identify missing logging/monitoring at critical junctions

{_JSON_SCHEMA}

{_COMMON_RULES}""",

        "policy": f"""You are a senior GRC (Governance, Risk, Compliance) analyst. You specialize in performing gap analysis on security policies, standards, and compliance documentation.

When analyzing this policy document:
- Perform gap analysis against common frameworks (NIST CSF, ISO 27001, SOC 2, HIPAA, PCI DSS) based on the content
- Identify missing controls that industry standards require but the policy doesn't address
- Flag weak or ambiguous language — "should" vs "shall", "may" vs "must"
- Note outdated references to deprecated standards or technologies
- Identify gaps between stated policy and typical real-world implementation challenges
- Check for missing incident response procedures, data classification, access reviews
- Assess policy maturity — is it aspirational or operational with measurable controls?
- Look for conflicting statements or contradictions within the document

{_JSON_SCHEMA}

{_COMMON_RULES}""",

        "config": f"""You are a senior security configuration auditor. You specialize in reviewing system configurations, infrastructure-as-code, and deployment settings for security issues.

When analyzing this configuration:
- Check for hardcoded secrets (API keys, passwords, tokens, connection strings)
- Identify default credentials or weak authentication settings
- Flag overly permissive settings (debug mode, verbose error logging in production, open CORS)
- Look for missing TLS/encryption configuration
- Check for disabled security features (no rate limiting, no CSRF protection, no input validation)
- Identify exposed management ports or administrative interfaces
- Flag insecure protocol usage (HTTP instead of HTTPS, FTP instead of SFTP, telnet)
- Check for missing security headers and CSP configuration

{_JSON_SCHEMA}

{_COMMON_RULES}""",

        "network_diagram": f"""You are a senior network security analyst. You specialize in reviewing network topology diagrams and infrastructure visualizations to identify security risks.

When analyzing this network diagram:
- Map the network topology and identify all trust zones / security boundaries
- Identify servers, databases, firewalls, load balancers, and their interconnections
- Flag missing network segmentation between different trust levels
- Identify direct internet exposure of sensitive internal services
- Check for missing firewalls or security appliances at critical junctions
- Note any flat network designs that allow lateral movement
- Identify missing DMZ configurations for public-facing services
- Flag any management networks that are not isolated

{_JSON_SCHEMA}

{_COMMON_RULES}""",
    }

    persona = _PERSONAS.get(document_type)
    if persona:
        return persona

    # Default: general threat analyst
    return f"""You are a cybersecurity risk assessment expert. Analyze the provided information and produce a focused security analysis.

{_JSON_SCHEMA}

{_COMMON_RULES}"""


class IntelligenceService:
    """Service for AI-powered assessment enrichment and analysis."""

    def __init__(self):
        """Initialize intelligence service."""
        self.bedrock = bedrock_service
        self.confidence_threshold = settings.intelligence_confidence_threshold

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def enrich_assessment(
        self,
        db: Session,
        assessment_id: str,
        tenant_id: str,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enrich an assessment with AI-generated insights.

        1. Clears previous AI-generated threats & recommendations.
        2. Builds a list of analysis items (assessment metadata + evidence files).
        3. Calls Bedrock once per item with a focused prompt.
        4. Saves findings to DB and returns aggregated results.
        """
        logger.info(f"Enriching assessment {assessment_id}")

        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id,
        ).first()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        logger.info(f"Assessment found: {assessment.title}")

        # ── Step 1: Clear old AI-generated data ─────────────────────
        cleared = self._clear_ai_generated_data(db, assessment_id, tenant_id)
        logger.info(f"Cleared {cleared['threats']} old AI threats, {cleared['recommendations']} old AI recommendations")

        results: Dict[str, Any] = {
            "assessment_id": assessment_id,
            "status": "completed",
            "vulnerabilities_identified": 0,
            "threats_mapped": 0,
            "risks_created": 0,
            "recommendations_generated": 0,
            "errors": [],
            "items_total": 0,
            "items_processed": 0,
        }

        # Get threat catalogue for context
        catalogue_threats = db.query(ThreatCatalogue).filter(
            ThreatCatalogue.tenant_id == tenant_id,
            ThreatCatalogue.is_active == True,
        ).all()

        catalogue_summary = "\n".join([
            f"- catalogue_key: {t.catalogue_key}, name: {t.name}, category: {t.category or 'General'}"
            for t in catalogue_threats[:20]
        ]) if catalogue_threats else "No threat catalogue available"

        catalogue_map = {t.catalogue_key: t for t in catalogue_threats}

        # Fetch evidence files with extracted text
        evidence_docs = db.query(Evidence).filter(
            Evidence.assessment_id == assessment_id,
            Evidence.tenant_id == tenant_id,
            Evidence.status == "ready",
            Evidence.extracted_text.isnot(None),
        ).order_by(Evidence.created_at.desc()).all()

        # ── Step 2: Build analysis items ────────────────────────────
        items: List[Dict[str, Any]] = []

        has_metadata = any([
            assessment.description,
            assessment.scope,
            assessment.system_background,
            assessment.tech_stack,
        ])
        if has_metadata:
            items.append({"type": "metadata", "label": "Assessment context"})

        for doc in evidence_docs:
            items.append({"type": "evidence", "label": doc.file_name, "evidence": doc})

        results["items_total"] = len(items)

        if not items:
            results["status"] = "completed_no_findings"
            results["errors"].append(
                "No assessment details or evidence files to analyze. "
                "Add a description/scope/tech stack or upload evidence files first."
            )
            return results

        # ── Pre-flight: verify Bedrock responds before looping ───────
        # A quick probe (max 10 tokens) catches auth/network failures fast
        # without burning the full step timeout on the first real call.
        if self.bedrock.enabled and self.bedrock.client:
            _probe = self.bedrock.invoke_model("Reply OK", max_tokens=10, temperature=0.0)
            if _probe is None:
                logger.error(
                    "Bedrock pre-flight check failed for assessment %s — skipping AI enrichment",
                    assessment_id,
                )
                results["status"] = "completed_no_findings"
                results["errors"].append(
                    "Bedrock is not responding (pre-flight check failed). "
                    "Skipping AI enrichment — check model access permissions, "
                    "IAM role, and network connectivity from Lambda to Bedrock."
                )
                return results
            logger.info("Bedrock pre-flight check passed — starting item analysis")

        # ── Step 3: Analyze each item ───────────────────────────────
        for i, item in enumerate(items):
            item_label = item["label"]
            try:
                logger.info(f"Analyzing item {i+1}/{len(items)}: {item_label}")

                if item["type"] == "metadata":
                    findings = self._analyze_assessment_metadata(
                        assessment, catalogue_summary
                    )
                else:
                    ev = item["evidence"]
                    fn = (ev.file_name or "").lower()
                    if fn.endswith(".nessus") or fn.endswith(".xml") and "nessus" in fn:
                        # Nessus XML: parse directly — no Bedrock needed, CVEs are structured
                        findings = self._extract_nessus_findings(ev, assessment, catalogue_summary)
                    else:
                        findings = self._analyze_evidence_file(ev, assessment, catalogue_summary)

                if findings:
                    self._process_findings(db, findings, assessment, catalogue_map, results)

                results["items_processed"] = i + 1

                # Push incremental progress to the job row
                if job_id:
                    self._update_job_progress(db, job_id, results)

            except Exception as e:
                logger.error(f"Error analyzing {item_label}: {e}")
                results["errors"].append(f"Error analyzing {item_label}: {str(e)}")
                results["items_processed"] = i + 1

        # Stamp evidence as enriched
        for doc in evidence_docs:
            doc.last_enriched_at = datetime.utcnow()
        db.commit()

        results["vulnerabilities_identified"] = results["threats_mapped"]

        if results["threats_mapped"] == 0:
            results["status"] = "completed_no_findings"

        logger.info(
            f"Enrichment complete: {results['threats_mapped']} threats, "
            f"{results['recommendations_generated']} recommendations"
        )
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clear_ai_generated_data(
        self, db: Session, assessment_id: str, tenant_id: str
    ) -> Dict[str, int]:
        """
        Delete all AI-generated threats and every record that FK-references them.

        Bulk DELETE (query.delete) bypasses ORM cascade rules — it sends SQL directly
        to PostgreSQL, which enforces FK constraints and will raise an IntegrityError
        if any referencing row still exists.  So we must delete children BEFORE parents,
        in FK-dependency order:

          ThreatAttackMapping -> Threat
          KillChain           -> Threat  (KillChainStage cascades from KillChain via ORM)
          ThreatIntelEnrichment -> Threat
          ActiveRisk          -> Threat
          Recommendation      -> Threat
          Threat              (safe to delete now)
        """
        # Collect AI-threat IDs once; used in all child deletes.
        ai_threat_ids = [
            t.id for t in db.query(Threat.id).filter(
                Threat.assessment_id == assessment_id,
                Threat.tenant_id == tenant_id,
                Threat.detected_by == "ai_intelligence",
            ).all()
        ]

        if not ai_threat_ids:
            # Also clean up orphaned AI recommendations (defensive)
            db.query(Recommendation).filter(
                Recommendation.assessment_id == assessment_id,
                Recommendation.tenant_id == tenant_id,
                Recommendation.ai_generated == True,
            ).delete(synchronize_session="fetch")
            db.commit()
            return {"threats": 0, "recommendations": 0}

        # 1. ATT&CK mappings
        db.query(ThreatAttackMapping).filter(
            ThreatAttackMapping.threat_id.in_(ai_threat_ids)
        ).delete(synchronize_session="fetch")

        # 2. Kill chains (KillChainStage rows will be removed by ORM cascade
        #    when the KillChain objects are expunged from session on commit)
        kill_chain_ids = [
            kc.id for kc in db.query(KillChain.id).filter(
                KillChain.threat_id.in_(ai_threat_ids)
            ).all()
        ]
        if kill_chain_ids:
            from ..models.models import KillChainStage
            db.query(KillChainStage).filter(
                KillChainStage.kill_chain_id.in_(kill_chain_ids)
            ).delete(synchronize_session="fetch")
            db.query(KillChain).filter(
                KillChain.id.in_(kill_chain_ids)
            ).delete(synchronize_session="fetch")

        # 3. Threat-intel enrichment cache
        db.query(ThreatIntelEnrichment).filter(
            ThreatIntelEnrichment.threat_id.in_(ai_threat_ids)
        ).delete(synchronize_session="fetch")

        # 4. Active risks linked to AI threats
        db.query(ActiveRisk).filter(
            ActiveRisk.threat_id.in_(ai_threat_ids)
        ).delete(synchronize_session="fetch")

        # 5. Recommendations (by threat_id AND any loose ai_generated ones)
        rec_count = db.query(Recommendation).filter(
            Recommendation.threat_id.in_(ai_threat_ids),
        ).delete(synchronize_session="fetch")
        rec_count += db.query(Recommendation).filter(
            Recommendation.assessment_id == assessment_id,
            Recommendation.tenant_id == tenant_id,
            Recommendation.ai_generated == True,
        ).delete(synchronize_session="fetch")

        # 6. Detach evidence from AI threats (nullify FK, don't delete files)
        db.query(Evidence).filter(
            Evidence.threat_id.in_(ai_threat_ids)
        ).update({Evidence.threat_id: None}, synchronize_session="fetch")

        # 7. Now safe to delete the threats themselves
        threat_count = db.query(Threat).filter(
            Threat.assessment_id == assessment_id,
            Threat.tenant_id == tenant_id,
            Threat.detected_by == "ai_intelligence",
        ).delete(synchronize_session="fetch")

        db.commit()
        return {"threats": threat_count, "recommendations": rec_count}

    def _analyze_assessment_metadata(
        self, assessment: Assessment, catalogue_summary: str
    ) -> List[Dict[str, Any]]:
        """Run Bedrock analysis on assessment metadata (description, scope, tech stack)."""
        tech = ", ".join(assessment.tech_stack) if assessment.tech_stack else "Not specified"

        prompt = f"""Analyze this security assessment for potential threats and vulnerabilities based on the described system, scope, and technology stack.

Assessment: {assessment.title}
Impact Level: {assessment.overall_impact}
System Background: {assessment.system_background or 'Not specified'}
Scope: {assessment.scope or 'Not specified'}
Tech Stack: {tech}

Description:
{assessment.description or 'Not provided'}

Available Threat Catalogue:
{catalogue_summary}

Identify threats and vulnerabilities specific to the described system, scope, and technologies.
Focus on architectural risks, known CVEs for the tech stack, and scope-related security gaps."""

        logger.info(f"Metadata prompt: {len(prompt)} chars")

        response = self.bedrock.generate_structured_output(
            prompt=prompt,
            system_prompt=_system_prompt(MAX_FINDINGS_METADATA),
            max_tokens=4000,
        )

        if not response:
            logger.warning("Bedrock returned no response for metadata analysis")
            return []

        findings = response.get("findings", [])
        # Tag each finding with its source
        for f in findings:
            f.setdefault("source", "Assessment metadata")
        return findings

    def _extract_nessus_findings(
        self,
        evidence: Evidence,
        assessment: Assessment,
        catalogue_summary: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse a .nessus XML file directly and return structured findings.

        Nessus XML has a well-defined schema — each <ReportItem> represents one
        vulnerability plugin hit on one host.  We extract CVE IDs, CVSS scores,
        severity, plugin name, and description directly without needing Bedrock.

        Only severity >= 2 (Medium+) is included; informational (0) and low
        severity (1) items are skipped to avoid noise.

        Severity mapping: Nessus 4→critical, 3→high, 2→medium, 1→low, 0→info.
        """
        import re
        import xml.etree.ElementTree as ET

        raw_xml = evidence.extracted_text or ""
        if not raw_xml:
            logger.warning("Nessus file %s has no extracted_text", evidence.file_name)
            return []

        # Build a simple catalogue keyword → key reverse-lookup for matching
        cat_keywords: Dict[str, str] = {}
        for line in catalogue_summary.splitlines():
            # line format: "- catalogue_key: foo, name: Bar Baz, category: ..."
            m = re.search(r"catalogue_key:\s*(\S+).*?name:\s*([^,]+)", line)
            if m:
                key, name = m.group(1).strip(), m.group(2).strip().lower()
                for word in name.split():
                    if len(word) > 4:
                        cat_keywords[word] = key

        _SEV_MAP = {4: "critical", 3: "high", 2: "medium", 1: "low", 0: "info"}
        _LIKELIHOOD_MAP = {4: 8, 3: 7, 2: 5, 1: 3, 0: 1}
        _IMPACT_MAP = {4: 9, 3: 7, 2: 5, 1: 3, 0: 1}

        findings: List[Dict[str, Any]] = []
        seen_plugins: set = set()  # deduplicate same plugin across multiple hosts

        try:
            # The extracted_text for XML is the tag:value flat text from document_parser.
            # We need the original XML — try to find it in the raw text or re-parse.
            # If extracted_text starts with XML we can use it; otherwise skip.
            text_to_parse = raw_xml.strip()

            # Find the actual XML — it may be prefixed by metadata lines
            xml_start = text_to_parse.find("<?xml")
            if xml_start == -1:
                xml_start = text_to_parse.find("<NessusClientData")
            if xml_start == -1:
                xml_start = text_to_parse.find("<NessusClientData_v2")
            if xml_start == -1:
                # Cannot find raw XML — fall back to Bedrock analysis
                logger.info(
                    "Nessus file %s: raw XML not found in extracted_text, "
                    "falling back to Bedrock analysis",
                    evidence.file_name,
                )
                return self._analyze_evidence_file(evidence, assessment, catalogue_summary)

            root = ET.fromstring(text_to_parse[xml_start:])
        except ET.ParseError as e:
            logger.warning(
                "Nessus XML parse error for %s: %s — falling back to Bedrock",
                evidence.file_name, e,
            )
            return self._analyze_evidence_file(evidence, assessment, catalogue_summary)

        for report_item in root.iter("ReportItem"):
            try:
                sev_int = int(report_item.get("severity", "0"))
                if sev_int < 2:  # skip informational + low
                    continue

                plugin_id = report_item.get("pluginID", "")
                plugin_name = report_item.get("pluginName", "Unknown Plugin")

                # Deduplicate: same plugin across multiple hosts → one finding
                if plugin_id and plugin_id in seen_plugins:
                    continue
                if plugin_id:
                    seen_plugins.add(plugin_id)

                # Extract CVE IDs
                cve_ids = [
                    el.text.strip()
                    for el in report_item.findall("cve")
                    if el.text and el.text.strip().upper().startswith("CVE-")
                ]

                # Fallback: scan description + synopsis for CVE patterns
                desc_text = " ".join(filter(None, [
                    getattr(report_item.find("description"), "text", None),
                    getattr(report_item.find("synopsis"), "text", None),
                ]))
                if not cve_ids and desc_text:
                    cve_ids = list(dict.fromkeys(
                        re.findall(r"CVE-\d{4}-\d{4,7}", desc_text, re.IGNORECASE)
                    ))

                # CVSS score
                cvss_el = report_item.find("cvss3_base_score") or report_item.find("cvss_base_score")
                cvss_score = cvss_el.text.strip() if cvss_el is not None and cvss_el.text else None

                # Solution / recommendations
                sol_el = report_item.find("solution")
                solution = sol_el.text.strip() if sol_el is not None and sol_el.text else "Apply vendor patch"

                # Affected host info for description enrichment
                host_name = ""
                for rh in root.iter("ReportHost"):
                    if report_item in list(rh):
                        host_name = rh.get("name", "")
                        break

                vuln_title = plugin_name[:200]
                description_parts = [desc_text or "See Nessus plugin output."]
                if host_name:
                    description_parts.append(f"Affected host: {host_name}")
                if cvss_score:
                    description_parts.append(f"CVSS score: {cvss_score}")
                if cve_ids:
                    description_parts.append(f"CVEs: {', '.join(cve_ids)}")
                description = "  ".join(description_parts)

                # Match to catalogue
                matched_key = "unmapped"
                title_lower = plugin_name.lower()
                for word, key in cat_keywords.items():
                    if word in title_lower:
                        matched_key = key
                        break

                findings.append({
                    "vulnerability": vuln_title,
                    "description": description[:800],
                    "severity": _SEV_MAP.get(sev_int, "medium"),
                    "catalogue_key": matched_key,
                    "likelihood": _LIKELIHOOD_MAP.get(sev_int, 5),
                    "impact": _IMPACT_MAP.get(sev_int, 5),
                    "justification": (
                        f"Nessus plugin {plugin_id} reported severity {sev_int}."
                        + (f" CVSS {cvss_score}." if cvss_score else "")
                        + (f" CVEs: {', '.join(cve_ids)}." if cve_ids else "")
                    ),
                    "source": evidence.file_name,
                    "cve_ids": cve_ids,
                    "recommendations": [solution],
                })

                if len(findings) >= MAX_FINDINGS_PER_FILE * 3:
                    # Cap total findings per file at 3× the Bedrock limit
                    break

            except Exception as exc_ri:
                logger.debug("Error parsing ReportItem in %s: %s", evidence.file_name, exc_ri)

        logger.info(
            "Nessus parser: %d findings (severity≥2) extracted from %s "
            "(%d unique plugin IDs, %d with CVEs)",
            len(findings), evidence.file_name,
            len(seen_plugins),
            sum(1 for f in findings if f["cve_ids"]),
        )

        # Store per-file analysis data on the Evidence record
        try:
            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            all_cves = []
            for f in findings:
                sev_counts[f.get("severity", "medium")] = sev_counts.get(f.get("severity", "medium"), 0) + 1
                all_cves.extend(f.get("cve_ids", []))

            summary = (
                f"Nessus scan of {evidence.file_name}: {len(findings)} findings "
                f"(severity≥Medium). {sev_counts['critical']} critical, "
                f"{sev_counts['high']} high, {sev_counts['medium']} medium. "
                f"{len(set(all_cves))} unique CVEs identified."
            )
            if hasattr(evidence, 'analysis_summary'):
                evidence.analysis_summary = summary
            if hasattr(evidence, 'analysis_findings'):
                evidence.analysis_findings = findings[:MAX_FINDINGS_PER_FILE]
            if hasattr(evidence, 'risk_indicators'):
                evidence.risk_indicators = {
                    "critical_vulns": sev_counts["critical"],
                    "high_vulns": sev_counts["high"],
                    "exposed_services": [],
                    "missing_controls": [],
                    "compliance_gaps": [],
                    "secrets_found": 0,
                    "key_concerns": [
                        f"{sev_counts['critical']} critical vulnerabilities found"
                    ] if sev_counts["critical"] > 0 else [],
                }
        except Exception as e:
            logger.debug(f"Could not store Nessus analysis fields: {e}")

        return findings

    def _analyze_evidence_file(
        self,
        evidence: Evidence,
        assessment: Assessment,
        catalogue_summary: str,
    ) -> List[Dict[str, Any]]:
        """Run Bedrock analysis on a single evidence file with document-type-specific prompts."""
        text = (evidence.extracted_text or "").strip()
        if not text:
            return []

        # Truncate to per-file limit
        if len(text) > MAX_CHARS_PER_FILE:
            text = text[:MAX_CHARS_PER_FILE] + f"\n... [truncated, {len(evidence.extracted_text)} total chars]"

        tech = ", ".join(assessment.tech_stack) if assessment.tech_stack else "Not specified"
        doc_type = evidence.document_type or "other"

        prompt = f"""Analyze this security-related document for threats and vulnerabilities.

Assessment Context: {assessment.title} ({assessment.overall_impact} impact)
Tech Stack: {tech}

Document: {evidence.file_name} (type: {doc_type})

Content:
{text}

Available Threat Catalogue:
{catalogue_summary}

Identify specific threats and vulnerabilities found in this document.
Reference specific CVEs, misconfigurations, or security weaknesses. Every finding must cite content from the document."""

        logger.info(f"Evidence file prompt ({evidence.file_name}, type={doc_type}): {len(prompt)} chars")

        response = self.bedrock.generate_structured_output(
            prompt=prompt,
            system_prompt=_system_prompt_for_type(doc_type, MAX_FINDINGS_PER_FILE),
            max_tokens=5000,
        )

        if not response:
            logger.warning(f"Bedrock returned no response for {evidence.file_name}")
            return []

        # Store per-file analysis summary and risk indicators on the Evidence record
        try:
            if hasattr(evidence, 'analysis_summary'):
                evidence.analysis_summary = response.get("summary")
            if hasattr(evidence, 'analysis_findings'):
                evidence.analysis_findings = response.get("findings", [])
            if hasattr(evidence, 'risk_indicators'):
                evidence.risk_indicators = response.get("risk_indicators")
        except Exception as e:
            logger.debug(f"Could not store analysis fields on evidence: {e}")

        findings = response.get("findings", [])
        for f in findings:
            f.setdefault("source", evidence.file_name)
        return findings

    def _process_findings(
        self,
        db: Session,
        findings: List[Dict[str, Any]],
        assessment: Assessment,
        catalogue_map: Dict[str, ThreatCatalogue],
        results: Dict[str, Any],
    ) -> None:
        """Process a list of findings: create Threat + Recommendation records in DB."""
        # Build a set of analyst-assessed threat titles to avoid duplicating them
        analyst_titles = {
            t.title.strip().lower()
            for t in db.query(Threat.title).filter(
                Threat.assessment_id == assessment.id,
                Threat.tenant_id == assessment.tenant_id,
                Threat.detected_by == "analyst_assessed",
            ).all()
        }

        for finding in findings:
            try:
                matched_key = finding.get("catalogue_key", "")
                cat_threat = catalogue_map.get(matched_key)

                severity = finding.get("severity", "medium")
                vuln_title = finding.get("vulnerability", "Unknown Vulnerability")[:200]

                # Skip if an analyst-assessed threat with a similar title already exists
                if vuln_title.strip().lower() in analyst_titles:
                    logger.info(f"Skipping AI finding '{vuln_title}' — already analyst-assessed")
                    continue

                threat = Threat(
                    tenant_id=assessment.tenant_id,
                    assessment_id=assessment.id,
                    catalogue_key=matched_key or "unmapped",
                    title=vuln_title,
                    description=finding.get("description", ""),
                    detected_by="ai_intelligence",
                    likelihood=cat_threat.default_likelihood if cat_threat else "Medium",
                    impact=cat_threat.default_impact if cat_threat else "Medium",
                    severity=severity,
                    status="identified",
                    ai_rationale=finding.get("justification", "AI-identified threat"),
                    cve_ids=finding.get("cve_ids", []),
                )
                db.add(threat)
                db.flush()
                results["threats_mapped"] += 1

                for rec in finding.get("recommendations", [])[:3]:
                    rec_title = rec if isinstance(rec, str) else rec.get("title", "Mitigation")
                    rec_desc = rec if isinstance(rec, str) else rec.get("description", rec.get("title", ""))
                    recommendation = Recommendation(
                        tenant_id=assessment.tenant_id,
                        assessment_id=assessment.id,
                        threat_id=threat.id,
                        title=str(rec_title)[:255],
                        description=str(rec_desc),
                        text=str(rec_desc),
                        priority=finding.get("severity", "medium").capitalize(),
                        status="open",
                        ai_generated=True,
                        estimated_effort="medium",
                        cost_estimate="medium",
                    )
                    db.add(recommendation)
                    results["recommendations_generated"] += 1

            except Exception as e:
                logger.error(f"Error processing finding '{finding.get('vulnerability', '?')}': {e}")
                results["errors"].append(str(e))

        db.commit()

    def _update_job_progress(
        self, db: Session, job_id: str, results: Dict[str, Any]
    ) -> None:
        """Update the intelligence job with incremental progress."""
        try:
            job = db.query(IntelligenceJob).filter(IntelligenceJob.id == job_id).first()
            if job:
                job.results = dict(results)  # copy so SQLAlchemy detects the change
                db.commit()
        except Exception:
            pass  # non-critical — don't let progress tracking break enrichment

    @staticmethod
    def _residual_from_score(score: int) -> str:
        """Convert numeric risk score to residual risk category."""
        if score >= 80:
            return "Critical"
        elif score >= 60:
            return "High"
        elif score >= 40:
            return "Medium"
        return "Low"


# Global instance
intelligence_service = IntelligenceService()
