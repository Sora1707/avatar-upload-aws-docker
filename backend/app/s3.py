import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

# Load credentials from .env (automatically provided by Docker Compose)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

UPLOAD_EXPIRE = 300
DOWNLOAD_EXPIRE = 900

# Initialize the standard AWS S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def generate_upload_url(object_key: str, expires_in: int = UPLOAD_EXPIRE) -> str:
    """Generates a presigned URL to PUT (upload) a file directly to S3."""
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": AWS_S3_BUCKET_NAME,
                "Key": object_key,
                "ContentType": "image/png"  # Restricts uploads to PNG for consistency
            },
            ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Upload Sign Error: {str(e)}")

def generate_download_url(object_key: str, expires_in: int = DOWNLOAD_EXPIRE) -> str:
    """Generates a temporary presigned URL to GET (view) a private S3 object."""
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": AWS_S3_BUCKET_NAME,
                "Key": object_key
            },
            ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Download Sign Error: {str(e)}")