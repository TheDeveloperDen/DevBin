"""AWS S3 storage implementation."""

import logging
from typing import Any

from app.storage.storage_client import StorageClient


class S3StorageClient(StorageClient):
    """AWS S3 storage implementation."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        access_key: str = "",
        secret_key: str = "",
        endpoint_url: str | None = None,
    ):
        """
        Initialize S3 storage client.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key: AWS access key ID
            secret_key: AWS secret access key
            endpoint_url: Custom S3 endpoint URL (for S3-compatible services)
        """
        self.bucket_name = bucket_name
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client: Any = None

    async def _get_client(self):
        """Get or create aioboto3 S3 client."""
        if self._client is None:
            try:
                import aioboto3
            except ImportError:
                raise ImportError(
                    "aioboto3 is required for S3 storage. Install it with: pip install aioboto3"
                ) from None

            session = aioboto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            self._client = session.client("s3", endpoint_url=self.endpoint_url)

        return self._client

    async def put_object(self, key: str, data: bytes) -> None:
        """
        Store object in S3.

        Args:
            key: Object key in S3
            data: Binary data to store
        """
        client = await self._get_client()
        async with client as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
            )
        self.logger.debug("Stored object in S3: %s (%d bytes)", key, len(data))

    async def get_object(self, key: str) -> bytes | None:
        """
        Retrieve object from S3.

        Args:
            key: Object key in S3

        Returns:
            Binary data if found, None otherwise
        """
        client = await self._get_client()
        try:
            async with client as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=key)
                data = await response["Body"].read()
            self.logger.debug("Retrieved object from S3: %s (%d bytes)", key, len(data))
            return data
        except Exception as exc:
            # Check if it's a NoSuchKey error
            if hasattr(exc, "response") and exc.response.get("Error", {}).get("Code") == "NoSuchKey":
                self.logger.debug("Object not found in S3: %s", key)
                return None
            self.logger.error("Failed to get object from S3 %s: %s", key, exc)
            raise

    async def delete_object(self, key: str) -> None:
        """
        Delete object from S3.

        Args:
            key: Object key in S3
        """
        client = await self._get_client()
        async with client as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=key)
        self.logger.debug("Deleted object from S3: %s", key)

    async def exists(self, key: str) -> bool:
        """
        Check if object exists in S3.

        Args:
            key: Object key in S3

        Returns:
            True if object exists, False otherwise
        """
        client = await self._get_client()
        try:
            async with client as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys with given prefix in S3.

        Args:
            prefix: Key prefix to filter by (optional)

        Returns:
            List of keys matching the prefix
        """
        client = await self._get_client()
        keys = []

        async with client as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        keys.append(obj["Key"])

        return keys
