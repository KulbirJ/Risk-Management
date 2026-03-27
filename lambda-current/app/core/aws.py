"""AWS utility functions for Secrets Manager and S3 integration."""
import json
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from .config import settings

logger = logging.getLogger(__name__)


class SecretsManagerClient:
    """Client for AWS Secrets Manager."""

    def __init__(self, region: str = settings.secrets_manager_region):
        """Initialize Secrets Manager client."""
        self.client = boto3.client("secretsmanager", region_name=region)
        self.region = region

    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve a secret from AWS Secrets Manager.
        
        Args:
            secret_name: Name or ARN of the secret
            
        Returns:
            Dictionary containing the secret value
        """
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # SecretString is returned for text secrets
            if "SecretString" in response:
                return json.loads(response["SecretString"])
            
            # SecretBinary is returned for binary secrets
            if "SecretBinary" in response:
                return response["SecretBinary"]
            
            logger.warning(f"Secret {secret_name} has no SecretString or SecretBinary")
            return {}
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                logger.error(f"Secret {secret_name} not found in Secrets Manager")
            elif error_code == "InvalidRequestException":
                logger.error(f"Invalid request for secret {secret_name}")
            elif error_code == "InvalidParameterException":
                logger.error(f"Invalid parameter for secret {secret_name}")
            elif error_code == "DecryptionFailure":
                logger.error(f"Unable to decrypt secret {secret_name}")
            elif error_code == "InternalServiceError":
                logger.error(f"Internal service error retrieving secret {secret_name}")
            else:
                logger.error(f"Error retrieving secret {secret_name}: {e}")
            raise


def get_db_url_from_secrets_manager(
    secret_name: str,
    region: str,
    db_name: str
) -> str:
    """
    Construct a PostgreSQL connection URL from credentials stored in Secrets Manager.
    
    Expects Secrets Manager secret to be JSON with keys:
    - host
    - port
    - username
    - password
    
    Args:
        secret_name: Name of the secret in Secrets Manager
        region: AWS region
        db_name: Database name
        
    Returns:
        PostgreSQL connection URL
        
    Example:
        "postgresql://user:password@host:5432/dbname"
    """
    client = SecretsManagerClient(region=region)
    secret_dict = client.get_secret(secret_name)
    
    host = secret_dict.get("host")
    port = secret_dict.get("port", 5432)
    username = secret_dict.get("username")
    password = secret_dict.get("password")
    
    if not all([host, username, password]):
        raise ValueError(f"Secret {secret_name} missing required fields: host, username, password")
    
    # Construct PostgreSQL URL
    db_url = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
    logger.info(f"Using database URL from Secrets Manager: postgresql://{username}@{host}:{port}/{db_name}")
    
    return db_url


class S3Client:
    """Client for AWS S3 operations."""

    def __init__(self, region: str = settings.aws_region):
        """Initialize S3 client."""
        self.client = boto3.client("s3", region_name=region)
        self.region = region
        self.bucket_name = settings.s3_bucket_evidence

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 600,
        method: str = "put_object"
    ) -> str:
        """
        Generate a presigned URL for S3 object upload or download.
        
        Args:
            object_key: S3 object key (path)
            expiration: URL expiration time in seconds (default 10 minutes)
            method: "put_object" for upload, "get_object" for download
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                method,
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key
                },
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned {method} URL for {object_key} (expires in {expiration}s)")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        """Get S3 object metadata."""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return {
                "size": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError as e:
            logger.error(f"Error getting object metadata for {object_key}: {e}")
            raise

    def delete_object(self, object_key: str) -> bool:
        """Delete an S3 object."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Deleted S3 object: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting object {object_key}: {e}")
            raise


class CognitoClient:
    """Client for AWS Cognito operations."""

    def __init__(self, region: str = settings.cognito_region):
        """Initialize Cognito client."""
        self.client = boto3.client("cognito-idp", region_name=region)
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.region = region

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user details by email."""
        try:
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f"email = \"{email}\""
            )
            if response.get("Users"):
                return response["Users"][0]
            return None
        except ClientError as e:
            logger.error(f"Error getting user {email} from Cognito: {e}")
            raise

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token from Cognito."""
        # Implementation depends on JWT library and Cognito configuration
        # This is a placeholder
        logger.debug("Token verification not yet implemented")
        return None


# Lazy initialization of AWS clients (only when needed)
_s3_client: Optional[S3Client] = None
_secrets_manager_client: Optional[SecretsManagerClient] = None
_cognito_client: Optional[CognitoClient] = None


def get_s3_client() -> S3Client:
    """Get or create S3 client (singleton)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client


def get_secrets_manager_client() -> SecretsManagerClient:
    """Get or create Secrets Manager client (singleton)."""
    global _secrets_manager_client
    if _secrets_manager_client is None:
        _secrets_manager_client = SecretsManagerClient()
    return _secrets_manager_client


def get_cognito_client() -> CognitoClient:
    """Get or create Cognito client (singleton)."""
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = CognitoClient()
    return _cognito_client
