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
    database_url: str = "postgresql://admin:password@localhost:5432/multitenantpostgresdb"
    db_echo: bool = False
    db_name: str = "multitenantpostgresdb"
    db_secret_name: str = "compliance-platform/db/credentials"
    db_secret_arn: Optional[str] = None

    # AWS
    aws_region: str = "ca-west-1"
    aws_account_id: str = "031195399879"

    # S3
    s3_bucket_evidence: str = "compliance-platform-dev-evidence"
    s3_bucket_region: str = "ca-west-1"

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
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
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
    max_upload_size_mb: int = 500
    evidence_retention_days: int = 365

    # Phase 1: AI/Intelligence (not used in Phase 0)
    bedrock_enabled: bool = False
    bedrock_model_id: str = "anthropic.claude-v2"
    bedrock_region: str = "ca-west-1"
    openai_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
