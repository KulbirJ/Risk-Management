from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import json


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # App
    debug: bool = False
    log_level: str = "INFO"
    app_name: str = "Compliance Platform MVP - Phase 0"
    app_version: str = "0.1.0"

    # Database
    database_url: str = "postgresql://admin:password@localhost:5432/postgres"
    db_echo: bool = False
    db_name: str = "postgres"
    db_secret_name: str = "postgresql_admin"
    db_secret_arn: Optional[str] = None

    # AWS
    aws_region: str = "ca-west-1"
    aws_account_id: str = "031195399879"

    # S3
    s3_bucket_evidence: str = "compliance-platform-evidence-dev"
    s3_bucket_region: str = "ca-west-1"

    # AWS Credentials (optional - uses IAM role in Lambda)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Cognito / Auth
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: Optional[str] = None
    cognito_region: str = "ca-west-1"
    cognito_domain: str = "compliance-platform-dev"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_secret_key: str = "dev-secret-key-phase-0-only"
    jwt_expiration_hours: int = 24

    # Secrets Manager (for AWS deployment)
    use_secrets_manager: bool = False
    secrets_manager_region: str = "ca-west-1"

    # Local Development
    use_localstack: bool = False
    localstack_endpoint_url: Optional[str] = None

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173,https://main.d2kda7m9vuv8zf.amplifyapp.com,https://main.d2qj9v0aax9a6c.amplifyapp.com"
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        """Parse CORS origins from string."""
        if isinstance(v, list):
            return ",".join(v)
        return v
    
    @property
    def get_origins(self) -> list[str]:
        """Get origins as a list."""
        if isinstance(self.allowed_origins, str):
            try:
                parsed = json.loads(self.allowed_origins)
                return parsed if isinstance(parsed, list) else [self.allowed_origins]
            except (json.JSONDecodeError, TypeError, ValueError):
                return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return self.allowed_origins

    # File Upload
    max_upload_size_mb: int = 50
    evidence_retention_days: int = 365
    allowed_upload_types: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv,application/json,application/xml,text/xml,text/plain,image/png,image/jpeg,image/gif,image/webp"

    # Intelligence Layer / AI
    bedrock_enabled: bool = True
    bedrock_model_id: str = "amazon.nova-pro-v1:0"
    bedrock_fallback_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_region: str = "us-east-1"
    bedrock_max_tokens: int = 5000
    bedrock_temperature: float = 0.3
    intelligence_confidence_threshold: float = 0.7
    openai_api_key: Optional[str] = None

    # MITRE ATT&CK Integration
    attack_taxii_url: str = "https://attack-taxii.mitre.org/api/v21/collections/1f5f1533-f617-4ca8-9ab4-6a02367fa019/objects/"
    attack_stix_bundle_url: str = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    attack_cache_ttl_days: int = 7             # How often to refresh cached ATT&CK data
    attack_auto_map_confidence_threshold: int = 60   # 0-100; suggestions below this are not auto-saved
    attack_max_techniques_per_prompt: int = 60 # Limit techniques sent to Bedrock per call
    attack_sync_enabled: bool = True

    # ─── Threat Intelligence Enrichment (Phase 1) ───
    intel_cache_ttl_hours: int = 24            # Default cache TTL for enrichment data
    nvd_api_base: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    nvd_api_key: Optional[str] = None          # Optional NVD API key for higher rate limits
    cisa_kev_url: str = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    otx_api_base: str = "https://otx.alienvault.com/api/v1"
    otx_api_key: Optional[str] = None          # AlienVault OTX API key
    github_exploit_search_url: str = "https://api.github.com/search/repositories"
    github_pat: Optional[str] = None           # GitHub Personal Access Token for search API
    intel_s3_bucket: Optional[str] = None      # S3 bucket for caching large intel payloads
    sector_threat_frequency_path: str = "app/data/sector_threat_frequency.json"  # Static reference data
    # ML model registry — uses the same evidence bucket under the ml-models/ prefix
    # Override to point to a dedicated bucket if desired
    ml_model_s3_bucket: Optional[str] = None   # defaults to s3_bucket_evidence
    ml_model_s3_prefix: str = "ml-models/likelihood"  # candidate/ and latest/ sub-prefixes

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
