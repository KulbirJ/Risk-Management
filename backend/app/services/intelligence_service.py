"""Intelligence service for AI-powered assessment enrichment.

Uses a SINGLE Bedrock call to stay within API Gateway's 29-second timeout.
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.models import Assessment, Threat, ActiveRisk, Recommendation, ThreatCatalogue, Evidence
from ..services.bedrock_service import bedrock_service
from ..core.config import settings

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Service for AI-powered assessment enrichment and analysis."""

    def __init__(self):
        """Initialize intelligence service."""
        self.bedrock = bedrock_service
        self.confidence_threshold = settings.intelligence_confidence_threshold

    def enrich_assessment(
        self,
        db: Session,
        assessment_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Enrich an assessment with AI-generated insights using a single Bedrock call.
        """
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()

        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        logger.info(f"Starting AI enrichment for assessment {assessment_id}")

        results = {
            "assessment_id": assessment_id,
            "status": "completed",
            "vulnerabilities_identified": 0,
            "threats_mapped": 0,
            "risks_created": 0,
            "recommendations_generated": 0,
            "errors": []
        }

        # Get threat catalogue for context
        catalogue_threats = db.query(ThreatCatalogue).filter(
            ThreatCatalogue.tenant_id == tenant_id,
            ThreatCatalogue.is_active == True
        ).all()

        catalogue_summary = "\n".join([
            f"- catalogue_key: {t.catalogue_key}, name: {t.name}, category: {t.category or 'General'}"
            for t in catalogue_threats[:20]
        ]) if catalogue_threats else "No threat catalogue available"

        # Build catalogue lookup
        catalogue_map = {t.catalogue_key: t for t in catalogue_threats}

        # Fetch uploaded evidence with extracted text for this assessment
        evidence_docs = db.query(Evidence).filter(
            Evidence.assessment_id == assessment_id,
            Evidence.tenant_id == tenant_id,
            Evidence.status == "ready",
            Evidence.extracted_text.isnot(None)
        ).order_by(Evidence.created_at.desc()).all()

        evidence_context = self._build_evidence_context(evidence_docs)

        try:
            # SINGLE Bedrock call for the entire analysis
            ai_results = self._run_comprehensive_analysis(assessment, catalogue_summary, evidence_context)

            if not ai_results:
                results["status"] = "completed_no_findings"
                return results

            findings = ai_results.get("findings", [])
            results["vulnerabilities_identified"] = len(findings)

            if not findings:
                results["status"] = "completed_no_findings"
                return results

            # Process each finding and create DB records
            for finding in findings:
                try:
                    # Match to catalogue threat
                    matched_key = finding.get("catalogue_key", "")
                    cat_threat = catalogue_map.get(matched_key)

                    # Create Threat record
                    severity = finding.get("severity", "medium")
                    vuln_title = finding.get("vulnerability", "Unknown Vulnerability")[:200]

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
                        ai_rationale=finding.get("justification", "AI-identified threat")
                    )
                    db.add(threat)
                    db.flush()
                    results["threats_mapped"] += 1

                    # Calculate scores from AI output
                    likelihood = min(max(int(finding.get("likelihood", 5)), 1), 10)
                    impact = min(max(int(finding.get("impact", 5)), 1), 10)
                    risk_score = min(max(likelihood * impact, 1), 100)

                    # Create ActiveRisk
                    risk_title = f"{vuln_title} - {cat_threat.name if cat_threat else 'Risk'}"
                    active_risk = ActiveRisk(
                        tenant_id=assessment.tenant_id,
                        assessment_id=assessment.id,
                        threat_id=threat.id,
                        title=risk_title[:255],
                        risk_score=risk_score,
                        likelihood=likelihood,
                        impact=impact,
                        residual_risk=self._residual_from_score(risk_score),
                        status="open",
                        detected_by="ai_intelligence",
                        ai_rationale=finding.get("justification", ""),
                        extra_data={
                            "ai_generated": True,
                            "model": settings.bedrock_model_id,
                            "severity": severity
                        }
                    )
                    db.add(active_risk)
                    db.flush()
                    results["risks_created"] += 1

                    # Create Recommendations from AI output
                    for rec in finding.get("recommendations", [])[:3]:
                        rec_title = rec if isinstance(rec, str) else rec.get("title", "Mitigation")
                        rec_desc = rec if isinstance(rec, str) else rec.get("description", rec.get("title", ""))
                        recommendation = Recommendation(
                            tenant_id=assessment.tenant_id,
                            active_risk_id=active_risk.id,
                            title=str(rec_title)[:255],
                            description=str(rec_desc),
                            text=str(rec_desc),
                            priority=finding.get("severity", "medium").capitalize(),
                            status="open",
                            ai_generated=True,
                            estimated_effort="medium",
                            cost_estimate="medium"
                        )
                        db.add(recommendation)
                        results["recommendations_generated"] += 1

                except Exception as e:
                    logger.error(f"Error processing finding: {e}")
                    results["errors"].append(str(e))
                    db.rollback()

            db.commit()
            logger.info(f"Assessment enrichment completed: {results}")

        except Exception as e:
            logger.error(f"Assessment enrichment failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
            db.rollback()

        return results

    def _run_comprehensive_analysis(
        self,
        assessment: Assessment,
        catalogue_summary: str,
        evidence_context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Run a single comprehensive AI analysis covering vulns, threats, risks, and recommendations."""

        system_prompt = """You are a cybersecurity risk assessment expert. Analyze the assessment and produce a comprehensive security analysis in a SINGLE response.

You MUST return valid JSON with this exact structure:
{
  "findings": [
    {
      "vulnerability": "Brief vulnerability title",
      "description": "What the vulnerability is and why it matters",
      "severity": "critical|high|medium|low",
      "catalogue_key": "matching key from threat catalogue",
      "likelihood": 7,
      "impact": 8,
      "justification": "Why these scores were assigned",
      "recommendations": [
        "Specific actionable mitigation step 1",
        "Specific actionable mitigation step 2"
      ]
    }
  ]
}

Rules:
- Return 3-7 findings maximum
- likelihood and impact must be integers 1-10
- catalogue_key must match one from the provided catalogue, pick the closest match
- Each finding should have 2-3 specific recommendations
- severity must be one of: critical, high, medium, low
- Return ONLY the JSON object, no other text
- If uploaded evidence (vulnerability scans, architecture docs, etc.) is provided, use that information to identify SPECIFIC, CONCRETE threats rather than generic ones. Reference specific CVEs, misconfigurations, or architectural weaknesses found in the evidence."""

        prompt = f"""Assessment Title: {assessment.title}
Overall Impact: {assessment.overall_impact}
System Background: {assessment.system_background or 'Not specified'}
Scope: {assessment.scope or 'Not specified'}
Tech Stack: {', '.join(assessment.tech_stack) if assessment.tech_stack else 'Not specified'}

Description:
{assessment.description or 'No description provided'}

Available Threat Catalogue Keys:
{catalogue_summary}"""

        # Append evidence context if available
        if evidence_context:
            prompt += f"""

=== UPLOADED EVIDENCE & DOCUMENTS ===
The following evidence has been uploaded for this assessment. Use this information to produce more specific and accurate findings:

{evidence_context}
=== END EVIDENCE ==="""

        prompt += "\n\nAnalyze this assessment and return the comprehensive JSON analysis."

        response = self.bedrock.generate_structured_output(
            prompt=prompt,
            system_prompt=system_prompt
        )

        if not response:
            logger.warning("No response from Bedrock")
            return None

        # Handle various response formats
        if isinstance(response, dict):
            return response
        elif isinstance(response, list):
            return {"findings": response}

        logger.warning(f"Unexpected response format: {type(response)}")
        return None

    def _build_evidence_context(self, evidence_docs: list) -> str:
        """
        Build a text context block from uploaded evidence documents.
        Truncates to fit within Bedrock token limits.
        """
        if not evidence_docs:
            return ""

        MAX_EVIDENCE_CHARS = 15000  # Keep evidence context under ~4K tokens
        sections = []
        total_chars = 0

        for doc in evidence_docs:
            text = (doc.extracted_text or "").strip()
            if not text:
                continue

            doc_type = doc.document_type or "other"
            header = f"[{doc_type.upper()}] {doc.file_name}"

            # Budget chars per document
            remaining = MAX_EVIDENCE_CHARS - total_chars
            if remaining <= 200:
                sections.append(f"\n... ({len(evidence_docs) - len(sections)} more documents not included due to size limits)")
                break

            if len(text) > remaining:
                text = text[:remaining] + f"\n... [truncated, {len(doc.extracted_text)} total chars]"

            sections.append(f"--- {header} ---\n{text}")
            total_chars += len(text) + len(header) + 10

        return "\n\n".join(sections)

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
