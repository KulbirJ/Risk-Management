"""S3 utilities for evidence file uploads."""
import boto3
from botocore.exceptions import ClientError
from typing import Tuple
from uuid import UUID, uuid4
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key
) if not settings.use_secrets_manager else boto3.client('s3', region_name=settings.aws_region)


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
    
    Usage (frontend):
        const formData = new FormData();
        Object.keys(fields).forEach(key => formData.append(key, fields[key]));
        formData.append('file', file);
        
        await fetch(presigned_url, {
            method: 'POST',
            body: formData
        });
    """
    try:
        response = s3_client.generate_presigned_post(
            Bucket=settings.s3_evidence_bucket,
            Key=s3_key,
            Fields={
                'Content-Type': content_type
            },
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', 1, 104857600]  # 1 byte to 100 MB
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
    
    Returns:
        presigned_url: Direct download URL valid for expiration seconds
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.s3_evidence_bucket,
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
        s3_client.delete_object(
            Bucket=settings.s3_evidence_bucket,
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
        s3_client.head_object(
            Bucket=settings.s3_evidence_bucket,
            Key=s3_key
        )
        return True
    except ClientError:
        return False
