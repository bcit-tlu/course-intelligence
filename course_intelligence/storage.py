"""S3-compatible object storage wrapper (MinIO locally, any S3 in prod).

Reads endpoint/credentials/bucket from config:
  s3_endpoint_url, s3_access_key, s3_secret_key, s3_bucket
"""

from __future__ import annotations

import logging
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig

from course_intelligence.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# Local dev fallback — matches the docker-compose minio service with its
# published port (9000) on localhost.
_LOCAL_DEV_ENDPOINT = "http://localhost:9000"


def _get_client():
    """Create an S3 client from config."""
    return boto3.client(
        "s3",
        endpoint_url=DEFAULT_CONFIG.get("s3_endpoint_url") or _LOCAL_DEV_ENDPOINT,
        aws_access_key_id=DEFAULT_CONFIG.get("s3_access_key") or "minioadmin",
        aws_secret_access_key=DEFAULT_CONFIG.get("s3_secret_key") or "minioadmin",
        config=BotoConfig(signature_version="s3v4"),
    )


def _bucket() -> str:
    return DEFAULT_CONFIG.get("s3_bucket") or "uploads"


def upload_fileobj(fileobj: BinaryIO, key: str) -> str:
    """Stream a file-like object to storage. Returns the object key.

    Uses multipart upload under the hood, so large files are not
    buffered fully in memory.
    """
    client = _get_client()
    client.upload_fileobj(fileobj, _bucket(), key)
    logger.info("Uploaded object: s3://%s/%s", _bucket(), key)
    return key


def download_file(key: str, dest_path: str) -> str:
    """Download an object to a local path. Returns the path."""
    client = _get_client()
    client.download_file(_bucket(), key, dest_path)
    logger.info("Downloaded object: s3://%s/%s -> %s", _bucket(), key, dest_path)
    return dest_path


def delete_object(key: str) -> None:
    """Delete an object from storage."""
    client = _get_client()
    client.delete_object(Bucket=_bucket(), Key=key)
    logger.info("Deleted object: s3://%s/%s", _bucket(), key)


def object_exists(key: str) -> bool:
    """Check whether an object exists."""
    client = _get_client()
    try:
        client.head_object(Bucket=_bucket(), Key=key)
        return True
    except client.exceptions.ClientError:
        return False
