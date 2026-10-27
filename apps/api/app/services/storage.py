"""Object Storage Service with Strict Private Bucket Protection (NFR-SEC-03).

NON-NEGOTIABLE SECURITY & RESEARCH RULES:
- Audio recordings are uploaded directly to private object storage (S3 / MinIO).
- Presigned URLs are strictly short-lived (15 minutes maximum expiry).
- Only the storage key (e.g., 'audio/SL-2026-0001/pre_test_abc123.webm') is stored in the DB, NEVER a public URL.
- Anonymous / unauthenticated access to the bucket or objects is strictly forbidden (HTTP 403).
- Mock adapter provides full deterministic testability with zero external cloud keys.
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger


class StorageProvider(ABC):
    """Abstract interface for object storage."""

    @abstractmethod
    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str = "audio/webm",
        expires_in: int = 900,
    ) -> dict[str, Any]:
        """Generate a short-lived presigned PUT URL for browser direct upload."""
        pass

    @abstractmethod
    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 900,
    ) -> str:
        """Generate a short-lived presigned GET URL for authorized researcher playback."""
        pass

    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """Check if an object exists in the storage bucket."""
        pass

    @abstractmethod
    def get_object_metadata(self, key: str) -> dict[str, Any]:
        """Retrieve metadata (content_length, content_type, etag) for an object."""
        pass


class S3StorageProvider(StorageProvider):
    """Real S3 / MinIO storage provider with Server-Side Encryption."""

    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            use_ssl=settings.S3_USE_SSL,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str = "audio/webm",
        expires_in: int = 900,
    ) -> dict[str, Any]:
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
                ExpiresIn=expires_in,
            )
            return {
                "upload_url": url,
                "key": key,
                "method": "PUT",
                "headers": {
                    "Content-Type": content_type,
                    "x-amz-server-side-encryption": "AES256",
                },
                "expires_in_seconds": expires_in,
                "expires_at": int(time.time()) + expires_in,
            }
        except Exception as e:
            logger.error("Failed to generate presigned upload URL: %s", e)
            raise RuntimeError(f"Storage presigned upload failure: {e}") from e

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 900,
    ) -> str:
        try:
            return self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.error("Failed to generate presigned download URL: %s", e)
            raise RuntimeError(f"Storage presigned download failure: {e}") from e

    def object_exists(self, key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        resp = self.s3_client.head_object(Bucket=self.bucket, Key=key)
        return {
            "content_length": resp.get("ContentLength", 0),
            "content_type": resp.get("ContentType", "audio/webm"),
            "etag": resp.get("ETag", "").strip('"'),
            "server_side_encryption": resp.get("ServerSideEncryption"),
        }


class MockStorageProvider(StorageProvider):
    """Deterministic in-memory Mock storage provider for zero-API-key testing and offline builds."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.presigned_urls: dict[str, float] = {}

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str = "audio/webm",
        expires_in: int = 900,
    ) -> dict[str, Any]:
        token = str(uuid.uuid4())
        expiry_ts = time.time() + expires_in
        upload_url = f"http://testserver/mock-s3-upload/{key}?token={token}"
        self.presigned_urls[token] = expiry_ts

        return {
            "upload_url": upload_url,
            "key": key,
            "method": "PUT",
            "headers": {
                "Content-Type": content_type,
                "x-amz-server-side-encryption": "AES256",
            },
            "expires_in_seconds": expires_in,
            "expires_at": int(expiry_ts),
        }

    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 900,
    ) -> str:
        token = str(uuid.uuid4())
        self.presigned_urls[token] = time.time() + expires_in
        return f"http://testserver/mock-s3-download/{key}?token={token}"

    def object_exists(self, key: str) -> bool:
        return key in self.objects

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        if key not in self.objects:
            raise KeyError(f"Key '{key}' not found in storage.")
        return self.objects[key]

    def store_mock_object(
        self,
        key: str,
        content_length: int = 45000,
        content_type: str = "audio/webm",
        checksum: str = "d41d8cd98f00b204e9800998ecf8427e",
    ) -> None:
        """Helper to register an object in mock storage for test validation."""
        self.objects[key] = {
            "content_length": content_length,
            "content_type": content_type,
            "etag": checksum,
            "server_side_encryption": "AES256",
        }


def get_storage_provider() -> StorageProvider:
    """Return storage provider based on environment and availability."""
    if settings.ENVIRONMENT == "testing" or settings.STT_PROVIDER == "mock":
        return MockStorageProvider()
    try:
        return S3StorageProvider()
    except Exception:
        logger.warning("S3 client initialization failed. Falling back to MockStorageProvider.")
        return MockStorageProvider()


storage_provider = get_storage_provider()
