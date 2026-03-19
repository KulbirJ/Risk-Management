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
    """Shared system prompt for all Bedrock calls."""
    return f"""You are a cybersecurity risk assessment expert. Analyze the provided information and produce a focused security analysis.

Return valid JSON with this exact structure:
{{
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
      "recommendations": [
        "Specific actionable mitigation step 1",
        "Specific actionable mitigation step 2"
      ]
    }}
  ]
}}

Rules:
- Return up to {max_findings} findings
- likelihood and impact must be integers 1-10
- catalogue_key MUST match one from the provided catalogue — pick closest match
- Each finding must have 2-3 specific, actionable recommendations
- severity must be one of: critical, high, medium, low
- Return ONLY the JSON object, no markdown, no explanation
- Identify SPECIFIC, CONCRETE threats — reference CVEs, misconfigurations, or architectural weaknesses where applicable
- Do NOT produce generic or vague findings"""


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
                    findings = self._analyze_evidence_file(
                        item["evidence"], assessment, catalogue_summary
                    )

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

        # 6. Now safe to delete the threats themselves
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

    def _analyze_evidence_file(
        self,
        evidence: Evidence,
        assessment: Assessment,
        catalogue_summary: str,
    ) -> List[Dict[str, Any]]:
        """Run Bedrock analysis on a single evidence file."""
        text = (evidence.extracted_text or "").strip()
        if not text:
            return []

        # Truncate to per-file limit
        if len(text) > MAX_CHARS_PER_FILE:
            text = text[:MAX_CHARS_PER_FILE] + f"\n... [truncated, {len(evidence.extracted_text)} total chars]"

        tech = ", ".join(assessment.tech_stack) if assessment.tech_stack else "Not specified"

        prompt = f"""Analyze this security-related document for threats and vulnerabilities.

Assessment Context: {assessment.title} ({assessment.overall_impact} impact)
Tech Stack: {tech}

Document: {evidence.file_name} (type: {evidence.document_type or 'other'})

Content:
{text}

Available Threat Catalogue:
{catalogue_summary}

Identify specific threats and vulnerabilities found in this document.
Reference specific CVEs, misconfigurations, or security weaknesses. Every finding must cite content from the document."""

        logger.info(f"Evidence file prompt ({evidence.file_name}): {len(prompt)} chars")

        response = self.bedrock.generate_structured_output(
            prompt=prompt,
            system_prompt=_system_prompt(MAX_FINDINGS_PER_FILE),
            max_tokens=5000,
        )

        if not response:
            logger.warning(f"Bedrock returned no response for {evidence.file_name}")
            return []

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
