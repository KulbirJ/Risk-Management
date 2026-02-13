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
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output from the model.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            response_schema: Expected JSON schema (for validation)
            
        Returns:
            Parsed JSON dict or None if failed
        """
        # Add JSON formatting instruction to prompt
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        full_prompt = prompt + json_instruction
        
        response_text = self.invoke_model(full_prompt, system_prompt)
        
        if not response_text:
            return None
        
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
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return None

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Basic schema validation - checks if required keys exist."""
        required_keys = schema.get('required', [])
        return all(key in data for key in required_keys)


# Global instance
bedrock_service = BedrockService()
