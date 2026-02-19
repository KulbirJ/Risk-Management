"""AWS Bedrock service for AI model interactions."""
import json
import logging
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError
from ..core.config import settings

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock foundation models."""

    def __init__(self):
        """Initialize Bedrock client."""
        self.enabled = settings.bedrock_enabled
        self.region = settings.bedrock_region
        self.model_id = settings.bedrock_model_id
        self.fallback_model_id = settings.bedrock_fallback_model_id
        self.max_tokens = settings.bedrock_max_tokens
        self.temperature = settings.bedrock_temperature
        
        if self.enabled:
            try:
                self.client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=self.region
                )
                logger.info(f"Bedrock service initialized with model: {self.model_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
                self.client = None
        else:
            self.client = None
            logger.info("Bedrock service is disabled")

    def invoke_model(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_fallback: bool = False
    ) -> Optional[str]:
        """
        Invoke a Bedrock model with the given prompt.
        
        Args:
            prompt: User prompt/question
            system_prompt: System instructions for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            use_fallback: Use fallback model (Claude) instead of primary
            
        Returns:
            Generated text response or None if failed
        """
        if not self.enabled or not self.client:
            logger.warning("Bedrock is not enabled or client not initialized")
            return None

        model_id = self.fallback_model_id if use_fallback else self.model_id
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        # Enforce per-model max token limits
        if "amazon.nova" in model_id:
            max_tokens = min(max_tokens, 10000)  # Nova Pro hard limit: 10240
        elif "anthropic.claude" in model_id and "haiku" in model_id:
            max_tokens = min(max_tokens, 4096)   # Claude Haiku limit
        elif "anthropic.claude" in model_id:
            max_tokens = min(max_tokens, 4096)   # Claude 3 default safe limit

        try:
            # Determine model family and format request accordingly
            if "anthropic.claude" in model_id:
                return self._invoke_claude(prompt, system_prompt, max_tokens, temperature, model_id)
            elif "amazon.nova" in model_id:
                return self._invoke_nova(prompt, system_prompt, max_tokens, temperature, model_id)
            elif "amazon.titan" in model_id:
                return self._invoke_titan(prompt, max_tokens, temperature, model_id)
            else:
                logger.error(f"Unsupported model: {model_id}")
                return None

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"Bedrock ClientError ({error_code}): {e}")
            
            # Retry with fallback model if primary fails
            if not use_fallback and self.fallback_model_id:
                logger.info("Retrying with fallback model...")
                return self.invoke_model(prompt, system_prompt, max_tokens, temperature, use_fallback=True)
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error invoking Bedrock: {e}")
            return None

    def _invoke_claude(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        model_id: str
    ) -> Optional[str]:
        """Invoke Claude model via Bedrock."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt

        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        
        if response_body.get('content') and len(response_body['content']) > 0:
            return response_body['content'][0].get('text', '')
        
        return None

    def _invoke_nova(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        model_id: str
    ) -> Optional[str]:
        """Invoke Amazon Nova model via Bedrock."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        body = {
            "messages": messages,
            "inferenceConfig": {
                "max_new_tokens": max_tokens,
                "temperature": temperature
            }
        }
        
        if system_prompt:
            body["system"] = [{"text": system_prompt}]

        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        
        # Nova response format
        if response_body.get('output') and response_body['output'].get('message'):
            content = response_body['output']['message'].get('content', [])
            if content and len(content) > 0:
                return content[0].get('text', '')
        
        return None

    def _invoke_titan(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        model_id: str
    ) -> Optional[str]:
        """Invoke Amazon Titan model via Bedrock."""
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
        }

        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        
        # Titan response format
        results = response_body.get('results', [])
        if results and len(results) > 0:
            return results[0].get('outputText', '')
        
        return None

    def generate_structured_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output from the model.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            response_schema: Expected JSON schema (for validation)
            max_tokens: Override max tokens for this call
            
        Returns:
            Parsed JSON dict or None if failed
        """
        # Add JSON formatting instruction to prompt
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        full_prompt = prompt + json_instruction
        
        response_text = self.invoke_model(full_prompt, system_prompt, max_tokens=max_tokens)
        
        if not response_text:
            logger.warning(f"invoke_model returned no text (enabled={self.enabled}, client={'yes' if self.client else 'no'})")
            return None
        
        logger.info(f"Bedrock raw response length: {len(response_text)} chars")
        
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            parsed = json.loads(response_text)
            
            # Basic schema validation if provided
            if response_schema and not self._validate_schema(parsed, response_schema):
                logger.warning("Response does not match expected schema")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, attempting truncated recovery: {e}")
            # Try to recover partial JSON (output was likely truncated by max_tokens)
            recovered = self._recover_truncated_json(response_text)
            if recovered:
                logger.info(f"Recovered {len(recovered.get('findings', []))} findings from truncated response")
                return recovered
            logger.error(f"Could not recover truncated JSON")
            logger.debug(f"Raw response: {response_text[:500]}")
            return None

    def _recover_truncated_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Attempt to recover findings from truncated JSON output."""
        import re
        try:
            # Find all complete finding objects in the truncated text
            # Look for complete JSON objects within the findings array
            findings = []
            # Find everything after "findings": [
            match = re.search(r'"findings"\s*:\s*\[', text)
            if not match:
                return None
            
            array_start = match.end()
            # Find each complete {...} block
            depth = 0
            obj_start = None
            for i in range(array_start, len(text)):
                if text[i] == '{':
                    if depth == 0:
                        obj_start = i
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0 and obj_start is not None:
                        try:
                            obj = json.loads(text[obj_start:i+1])
                            findings.append(obj)
                        except json.JSONDecodeError:
                            pass
                        obj_start = None
            
            if findings:
                return {"findings": findings}
            return None
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return None

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Basic schema validation - checks if required keys exist."""
        required_keys = schema.get('required', [])
        return all(key in data for key in required_keys)

    # ------------------------------------------------------------------
    # MITRE ATT&CK – technique mapping
    # ------------------------------------------------------------------

    def map_threat_to_attack_techniques(
        self,
        threat_title: str,
        threat_description: str,
        candidate_techniques: List[Dict[str, Any]],
        confidence_threshold: int = 60,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Ask Bedrock to map a threat to MITRE ATT&CK techniques.

        candidate_techniques is a list of dicts with keys:
          id, mitre_id, name, tactic_shortname, description

        Returns a list of dicts:
          {technique_id, mitre_id, technique_name, tactic_shortname,
           confidence_score (0-100), mapping_rationale}
        """
        if not self.enabled or not self.client:
            logger.warning("Bedrock disabled – skipping ATT&CK mapping")
            return None

        techniques_context = "\n".join(
            f"- [{t['mitre_id']}] {t['name']} (tactic: {t.get('tactic_shortname', 'unknown')}): "
            f"{(t.get('description') or '')[:120]}"
            for t in candidate_techniques
        )

        system_prompt = """You are a MITRE ATT&CK mapping expert.
Given a cybersecurity threat, identify the most relevant ATT&CK techniques from the provided list.

Return valid JSON only – no markdown, no extra text:
{
  "mappings": [
    {
      "mitre_id": "T1566",
      "technique_name": "Phishing",
      "tactic_shortname": "initial-access",
      "confidence_score": 85,
      "mapping_rationale": "The threat involves email-based deception matching phishing technique"
    }
  ]
}

Rules:
- Return 2-6 mappings maximum
- confidence_score must be an integer 0-100
- Only include techniques from the provided list
- Only include mappings with confidence >= """ + str(confidence_threshold) + """
- Return ONLY valid JSON"""

        user_prompt = f"""Threat: {threat_title}

Description: {threat_description or 'No description provided'}

Available ATT&CK techniques:
{techniques_context}

Map this threat to the most relevant techniques above."""

        try:
            raw = self.invoke_model(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.2,
            )
            if not raw:
                return None

            data = self._extract_json(raw)
            if not data:
                return None

            mappings = data.get("mappings", [])
            logger.info(f"ATT&CK mapping returned {len(mappings)} suggestions for '{threat_title}'")
            return mappings

        except Exception as exc:
            logger.error(f"ATT&CK technique mapping failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # MITRE ATT&CK – kill chain scenario generation
    # ------------------------------------------------------------------

    def generate_kill_chain_scenario(
        self,
        threat_title: str,
        threat_description: str,
        mapped_techniques: List[Dict[str, Any]],
        assessment_context: Optional[str] = None,
        threat_actor: Optional[str] = None,
        include_detection_hints: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a realistic attack kill chain scenario for a threat.

        mapped_techniques: list of dicts with keys mitre_id, technique_name, tactic_shortname

        Returns a dict:
        {
          scenario_name, description, threat_actor,
          stages: [
            {stage_number, tactic_name, technique_name, mitre_id,
             description, actor_behavior, detection_hint}
          ]
        }
        """
        if not self.enabled or not self.client:
            logger.warning("Bedrock disabled – skipping kill chain generation")
            return None

        tech_list = "\n".join(
            f"  - [{t.get('mitre_id', '')}] {t.get('technique_name', '')} ({t.get('tactic_shortname', '')})"
            for t in mapped_techniques
        )

        actor_hint = (
            f"Assume the threat actor is: {threat_actor}."
            if threat_actor
            else "Assume a skilled, motivated threat actor."
        )

        detection_instruction = (
            "For each stage, include a brief detection_hint describing how a defender could detect the activity."
            if include_detection_hints
            else "Set detection_hint to null for all stages."
        )

        system_prompt = f"""You are an expert threat modeler specializing in MITRE ATT&CK kill chains.
Generate a realistic, plausible multi-stage attack scenario for the given threat.

{actor_hint}

Return valid JSON only – no markdown, no commentary:
{{
  "scenario_name": "Short descriptive title",
  "description": "1-2 sentence overview of the attack scenario",
  "threat_actor": "Name or type of attacker",
  "stages": [
    {{
      "stage_number": 1,
      "tactic_name": "Initial Access",
      "technique_name": "Spearphishing Link",
      "mitre_id": "T1566.002",
      "description": "What happens at this stage",
      "actor_behavior": "What the attacker does specifically",
      "detection_hint": "How a defender could detect this"
    }}
  ]
}}

Rules:
- Include 4-8 stages covering the full attack lifecycle
- Use ONLY techniques from the provided mapped techniques list (or well-known related techniques)
- Stages must follow a logical progression: Reconnaissance → Initial Access → ... → Impact
- actor_behavior must be specific and plausible
- {detection_instruction}
- Return ONLY valid JSON"""

        user_prompt = f"""Threat: {threat_title}

Description: {threat_description or 'No description provided'}

{"Assessment context: " + assessment_context if assessment_context else ""}

Mapped ATT&CK techniques:
{tech_list if tech_list else "  (none pre-mapped – use common techniques for this threat type)"}

Generate the kill chain attack scenario."""

        try:
            raw = self.invoke_model(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.4,
            )
            if not raw:
                return None

            data = self._extract_json(raw)
            if not data or "stages" not in data:
                logger.warning("Kill chain response missing 'stages' key")
                return None

            logger.info(
                f"Kill chain generated for '{threat_title}': "
                f"{len(data.get('stages', []))} stages"
            )
            return data

        except Exception as exc:
            logger.error(f"Kill chain generation failed: {exc}")
            return None


# Global instance
bedrock_service = BedrockService()
