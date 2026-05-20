import boto3
from botocore.config import Config
from app.infrastructure.config import settings

_client = None


def get_r2_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def upload_bytes(key: str, data: bytes, content_type: str = "audio/ogg") -> str:
    """Upload bytes to R2. Returns the key (use as permanent reference)."""
    get_r2_client().put_object(
        Bucket=settings.r2_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Temporary download URL for the audio file."""
    return get_r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
