"""S3 utilities for evidence file uploads."""
import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Optional
from uuid import UUID, uuid4
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """Get a fresh S3 client using boto3 default credential chain.
    
    Creates a new client each time to avoid stale credential issues.
    In Lambda, boto3 automatically uses the execution role's temporary
    credentials (access key + secret + session token) from the environment.
    """
    return boto3.client('s3', region_name=settings.s3_bucket_region)


def generate_evidence_s3_key(
    tenant_id: UUID,
    assessment_id: UUID,
    file_name: str
) -> str:
    """Generate S3 object key for evidence file."""
    file_id = uuid4()
    return f"evidence/{tenant_id}/{assessment_id}/{file_id}/{file_name}"


def generate_presigned_upload_url(
    s3_key: str,
    content_type: str,
    expiration: int = 3600
) -> Tuple[str, dict]:
    """
    Generate presigned URL for direct client upload to S3.
    
    Returns:
        Tuple of (presigned_url, fields) for HTML form or fetch upload
    """
    try:
        max_size = settings.max_upload_size_mb * 1024 * 1024
        s3 = get_s3_client()
        response = s3.generate_presigned_post(
            Bucket=settings.s3_bucket_evidence,
            Key=s3_key,
            Fields={
                'Content-Type': content_type
            },
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', 1, max_size]
            ],
            ExpiresIn=expiration
        )
        
        return response['url'], response['fields']
    
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise Exception(f"Failed to generate upload URL: {str(e)}")


def generate_presigned_download_url(
    s3_key: str,
    expiration: int = 3600
) -> str:
    """
    Generate presigned URL for downloading evidence file from S3.
    """
    try:
        s3 = get_s3_client()
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.s3_bucket_evidence,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        return url
    
    except ClientError as e:
        logger.error(f"Error generating presigned download URL: {str(e)}")
        raise Exception(f"Failed to generate download URL: {str(e)}")


def delete_evidence_from_s3(s3_key: str) -> bool:
    """Delete evidence file from S3."""
    try:
        s3 = get_s3_client()
        s3.delete_object(
            Bucket=settings.s3_bucket_evidence,
            Key=s3_key
        )
        logger.info(f"Deleted S3 object: {s3_key}")
        return True
    
    except ClientError as e:
        logger.error(f"Error deleting S3 object {s3_key}: {str(e)}")
        return False


def verify_s3_upload(s3_key: str) -> bool:
    """Verify that file was successfully uploaded to S3."""
    try:
        s3 = get_s3_client()
        s3.head_object(
            Bucket=settings.s3_bucket_evidence,
            Key=s3_key
        )
        return True
    except ClientError:
        return False


def get_s3_object_content(s3_key: str) -> bytes:
    """Download file content from S3."""
    try:
        s3 = get_s3_client()
        response = s3.get_object(
            Bucket=settings.s3_bucket_evidence,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Error reading S3 object {s3_key}: {str(e)}")
        raise Exception(f"Failed to read file from S3: {str(e)}")
