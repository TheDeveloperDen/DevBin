"""MinIO storage implementation (S3-compatible)."""

from app.storage.s3_storage import S3StorageClient


class MinIOStorageClient(S3StorageClient):
    """MinIO storage implementation (inherits from S3 client)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
    ):
        """
        Initialize MinIO storage client.

        Args:
            bucket_name: MinIO bucket name
            endpoint_url: MinIO server endpoint (e.g., "minio:9000")
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Use HTTPS (default: True)
        """
        # MinIO uses the S3 client with a custom endpoint
        protocol = "https" if secure else "http"
        full_endpoint = f"{protocol}://{endpoint_url}"

        super().__init__(
            bucket_name=bucket_name,
            region="us-east-1",  # MinIO doesn't use regions but S3 client requires it
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=full_endpoint,
        )
