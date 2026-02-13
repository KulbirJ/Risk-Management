"""Intelligence service for AI-powered assessment enrichment."""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.models import Assessment, Threat, ActiveRisk, Recommendation, ThreatCatalogue
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
        Enrich an assessment with AI-generated insights.
        
        Args:
            db: Database session
            assessment_id: Assessment UUID
            tenant_id: Tenant UUID
            
        Returns:
            Dict with enrichment results and statistics
        """
        # Get assessment
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

        try:
            # Step 1: Extract vulnerabilities from assessment description
            vulnerabilities = self._extract_vulnerabilities(assessment)
            results["vulnerabilities_identified"] = len(vulnerabilities)

            if not vulnerabilities:
                logger.warning("No vulnerabilities identified in assessment")
                results["status"] = "completed_no_findings"
                return results

            # Step 2: Map threats and create active risks
            for vuln in vulnerabilities:
                try:
                    # Find matching threats from catalogue
                    catalogue_threats = self._map_threats_to_vulnerability(db, vuln, tenant_id)
                    
                    for cat_threat in catalogue_threats:
                        # Create Threat record from catalogue
                        threat = self._create_threat_from_catalogue(
                            db=db,
                            assessment=assessment,
                            catalogue_threat=cat_threat,
                            vulnerability=vuln
                        )
                        
                        if not threat:
                            continue
                        
                        # Calculate risk score
                        risk_data = self._calculate_risk_score(vuln, cat_threat, assessment)
                        
                        # Create active risk
                        active_risk = self._create_active_risk(
                            db=db,
                            assessment=assessment,
                            threat=threat,
                            risk_data=risk_data,
                            vulnerability=vuln
                        )
                        
                        if active_risk:
                            results["risks_created"] += 1
                            results["threats_mapped"] += 1
                            
                            # Generate mitigation recommendations
                            recommendations = self._generate_recommendations(
                                db=db,
                                active_risk=active_risk,
                                vulnerability=vuln,
                                catalogue_threat=cat_threat
                            )
                            results["recommendations_generated"] += len(recommendations)

                except Exception as e:
                    logger.error(f"Error processing vulnerability: {e}")
                    results["errors"].append(str(e))
                    db.rollback()  # Roll back failed vulnerability processing

            db.commit()
            logger.info(f"Assessment enrichment completed: {results}")

        except Exception as e:
            logger.error(f"Assessment enrichment failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
            db.rollback()

        return results

    def _extract_vulnerabilities(self, assessment: Assessment) -> List[Dict[str, Any]]:
        """Extract vulnerabilities from assessment description using AI."""
        system_prompt = """You are a cybersecurity expert analyzing compliance assessments.
Extract all vulnerabilities, security issues, and compliance gaps from the assessment description.
For each vulnerability, provide:
- title: Brief descriptive title
- description: Detailed explanation
- severity: One of [critical, high, medium, low]
- confidence: Float 0.0-1.0 indicating your confidence
- affected_systems: List of affected systems/components
- cve_ids: List of any CVE identifiers mentioned (if applicable)"""

        prompt = f"""Assessment Title: {assessment.title}
Assessment Impact: {assessment.overall_impact}
Assessment Description:
{assessment.description or 'No description provided'}

Extract all vulnerabilities, security issues, and compliance gaps from this assessment.
Output valid JSON array of vulnerability objects."""

        response = self.bedrock.generate_structured_output(
            prompt=prompt,
            system_prompt=system_prompt
        )

        if not response:
            logger.warning("No response from Bedrock for vulnerability extraction")
            return []

        # Handle both array and object with vulnerabilities key
        if isinstance(response, list):
            vulnerabilities = response
        elif isinstance(response, dict) and 'vulnerabilities' in response:
            vulnerabilities = response['vulnerabilities']
        else:
            logger.warning(f"Unexpected response format: {type(response)}")
            return []

        # Filter by confidence threshold
        filtered = [
            v for v in vulnerabilities
            if v.get('confidence', 0) >= self.confidence_threshold
        ]

        logger.info(f"Extracted {len(filtered)} vulnerabilities (filtered from {len(vulnerabilities)})")
        return filtered

    def _map_threats_to_vulnerability(
        self,
        db: Session,
        vulnerability: Dict[str, Any],
        tenant_id: str
    ) -> List[ThreatCatalogue]:
        """Map threats from catalogue to a vulnerability using AI."""
        # Get all active threats from catalogue for tenant
        catalogue_threats = db.query(ThreatCatalogue).filter(
            ThreatCatalogue.tenant_id == tenant_id,
            ThreatCatalogue.is_active == True
        ).all()

        if not catalogue_threats:
            logger.warning("No threats in catalogue")
            return []

        # Create threat catalogue summary
        threat_catalogue = "\n".join([
            f"- ID: {t.id}, Category: {t.category or 'General'}, Name: {t.name}, Description: {t.description[:200]}"
            for t in catalogue_threats[:50]  # Limit to avoid token limits
        ])

        system_prompt = """You are a threat intelligence analyst.
Match the vulnerability to relevant threats from the threat catalogue.
Return the threat IDs that are most relevant (up to 5 threats)."""

        prompt = f"""Vulnerability:
Title: {vulnerability.get('title', 'Unknown')}
Description: {vulnerability.get('description', '')}
Severity: {vulnerability.get('severity', 'unknown')}

Threat Catalogue:
{threat_catalogue}

Which threat IDs from the catalogue are most relevant to this vulnerability?
Return JSON object with key "threat_ids" as array of UUID strings."""

        response = self.bedrock.generate_structured_output(prompt=prompt, system_prompt=system_prompt)

        if not response or 'threat_ids' not in response:
            logger.warning("No threat mapping generated")
            return []

        threat_ids = response['threat_ids'][:5]  # Limit to top 5

        # Fetch the matching catalogue threats
        matched_catalogue_threats = db.query(ThreatCatalogue).filter(
            ThreatCatalogue.id.in_(threat_ids),
            ThreatCatalogue.tenant_id == tenant_id
        ).all()

        # Return as Threat Catalogue objects (will be converted to Threat records when creating ActiveRisk)
        logger.info(f"Mapped {len(matched_catalogue_threats)} threats to vulnerability")
        return matched_catalogue_threats

    def _create_threat_from_catalogue(
        self,
        db: Session,
        assessment: Assessment,
        catalogue_threat: ThreatCatalogue,
        vulnerability: Dict[str, Any]
    ) -> Optional[Threat]:
        """Create a Threat record from a catalogue threat match."""
        try:
            threat = Threat(
                tenant_id=assessment.tenant_id,
                assessment_id=assessment.id,
                catalogue_key=catalogue_threat.catalogue_key,
                title=f"{vulnerability.get('title', 'Unknown Vulnerability')} - {catalogue_threat.name}",
                description=catalogue_threat.description,
                detected_by="ai_intelligence",
                likelihood=catalogue_threat.default_likelihood,
                impact=catalogue_threat.default_impact,
                severity=vulnerability.get('severity', 'medium'),
                status="identified",
                ai_rationale=f"AI-mapped threat from catalogue based on vulnerability analysis. Confidence: {vulnerability.get('confidence', 0):.2f}"
            )
            
            db.add(threat)
            db.flush()  # Get the ID
            
            logger.info(f"Created threat {threat.id} from catalogue {catalogue_threat.catalogue_key}")
            return threat
            
        except Exception as e:
            logger.error(f"Failed to create threat from catalogue: {e}")
            return None

    def _calculate_risk_score(
        self,
        vulnerability: Dict[str, Any],
        catalogue_threat: ThreatCatalogue,
        assessment: Assessment
    ) -> Dict[str, Any]:
        """Calculate risk score and impact using AI."""
        system_prompt = """You are a risk assessment expert.
Calculate the risk score based on vulnerability severity, threat likelihood, and potential impact.
Use a scale of 1-10 for likelihood and impact.
Provide specific justification for your scores."""

        prompt = f"""Vulnerability:
Title: {vulnerability.get('title')}
Severity: {vulnerability.get('severity')}
Description: {vulnerability.get('description', '')[:500]}

Threat:
Category: {catalogue_threat.category or 'General'}
Name: {catalogue_threat.name}
Description: {catalogue_threat.description[:500] if catalogue_threat.description else 'N/A'}

Assessment Context:
Title: {assessment.title}
Impact: {assessment.overall_impact}
Status: {assessment.status}

Calculate the risk score and provide:
- likelihood: Integer 1-10 (probability of exploitation)
- impact: Integer 1-10 (severity of consequences)
- risk_score: Integer 1-100 (combined risk metric)
- justification: String explaining the scores

Return valid JSON object."""

        response = self.bedrock.generate_structured_output(prompt=prompt, system_prompt=system_prompt)

        if not response:
            # Fallback to basic calculation based on severity
            severity_map = {"critical": 9, "high": 7, "medium": 5, "low": 3}
            base_score = severity_map.get(vulnerability.get('severity', 'medium'), 5)
            
            return {
                "likelihood": base_score,
                "impact": base_score,
                "risk_score": base_score * 10,
                "justification": "AI-generated scores unavailable, using severity-based defaults"
            }

        return response

    def _create_active_risk(
        self,
        db: Session,
        assessment: Assessment,
        threat: Threat,
        risk_data: Dict[str, Any],
        vulnerability: Dict[str, Any]
    ) -> Optional[ActiveRisk]:
        """Create an active risk from AI analysis."""
        try:
            # Build a descriptive title from vuln + threat
            vuln_title = vulnerability.get('title', 'Unknown Vulnerability')
            risk_title = f"{vuln_title} - {threat.title or 'Risk'}"

            active_risk = ActiveRisk(
                tenant_id=assessment.tenant_id,
                assessment_id=assessment.id,
                threat_id=threat.id,
                title=risk_title[:255],
                risk_score=risk_data.get('risk_score', 50),
                likelihood=risk_data.get('likelihood', 5),
                impact=risk_data.get('impact', 5),
                residual_risk=self._residual_from_score(risk_data.get('risk_score', 50)),
                status="open",
                detected_by="ai_intelligence",
                ai_rationale=risk_data.get('justification', ''),
                extra_data={
                    "vulnerability": vulnerability,
                    "ai_generated": True,
                    "model": settings.bedrock_model_id
                }
            )
            
            db.add(active_risk)
            db.flush()  # Get the ID
            
            logger.info(f"Created active risk {active_risk.id} with score {active_risk.risk_score}")
            return active_risk

        except Exception as e:
            logger.error(f"Failed to create active risk: {e}")
            return None

    def _generate_recommendations(
        self,
        db: Session,
        active_risk: ActiveRisk,
        vulnerability: Dict[str, Any],
        catalogue_threat: ThreatCatalogue
    ) -> List[Recommendation]:
        """Generate mitigation recommendations using AI."""
        system_prompt = """You are a cybersecurity remediation expert.
Generate specific, actionable mitigation recommendations.
Each recommendation should be clear, practical, and prioritized."""

        prompt = f"""Vulnerability:
{vulnerability.get('title')}
{vulnerability.get('description', '')}

Threat:
{catalogue_threat.name} - {catalogue_threat.category or 'General'}
{catalogue_threat.description[:300] if catalogue_threat.description else 'N/A'}

Risk Score: {active_risk.risk_score}

Generate 2-4 specific mitigation recommendations.
Return JSON object with key "recommendations", each having:
- title: Brief action title
- description: Detailed implementation steps
- priority: One of [critical, high, medium, low]
- estimated_effort: One of [low, medium, high]
- cost_estimate: One of [low, medium, high]"""

        response = self.bedrock.generate_structured_output(prompt=prompt, system_prompt=system_prompt)

        if not response or 'recommendations' not in response:
            logger.warning("No recommendations generated")
            return []

        created_recommendations = []

        for rec_data in response['recommendations'][:4]:  # Limit to 4
            try:
                recommendation = Recommendation(
                    tenant_id=active_risk.tenant_id,
                    active_risk_id=active_risk.id,
                    title=rec_data.get('title', 'Mitigation recommended'),
                    description=rec_data.get('description', ''),
                    text=rec_data.get('description', ''),
                    priority=rec_data.get('priority', 'medium'),
                    estimated_effort=rec_data.get('estimated_effort', 'medium'),
                    cost_estimate=rec_data.get('cost_estimate', 'medium'),
                    status="open",
                    ai_generated=True
                )
                
                db.add(recommendation)
                created_recommendations.append(recommendation)

            except Exception as e:
                logger.error(f"Failed to create recommendation: {e}")

        db.flush()
        logger.info(f"Generated {len(created_recommendations)} recommendations")
        return created_recommendations


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
