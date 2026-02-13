"""S3Tool — document access via Amazon S3.

This adapter uses ``boto3`` for S3 operations.  Install with::

    pip install boto3
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError as _ClientError
    from botocore.exceptions import NoCredentialsError as _NoCredsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class S3Tool(DocumentStorageTool):
    """Amazon S3 document access via boto3.

    Configuration parameters:

    * ``bucket`` -- S3 bucket name.
    * ``region`` -- AWS region (defaults to ``us-east-1``).
    * ``aws_access_key_id`` / ``aws_secret_access_key`` -- explicit credentials.
      If omitted, boto3 falls back to its default credential chain
      (env vars, ``~/.aws/credentials``, instance profile).
    * ``prefix`` -- Key prefix to scope operations.
    * ``endpoint_url`` -- Custom endpoint for S3-compatible stores (MinIO, etc.).
    * ``timeout`` -- read timeout in seconds.
    """

    def __init__(
        self,
        *,
        bucket: str = "",
        region: str = "us-east-1",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        prefix: str = "",
        endpoint_url: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "s3",
            description="Access Amazon S3 buckets and objects",
            guards=guards,
        )
        self._bucket = bucket
        self._region = region
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._prefix = prefix.strip("/")
        self._endpoint_url = endpoint_url
        self._timeout = timeout
        self._client: Any | None = None

    def _ensure_deps(self) -> None:
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3Tool. Install with: pip install boto3"
            )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._ensure_deps()
        if not self._bucket:
            raise ConnectorError("S3Tool requires a bucket name")

        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._aws_access_key_id and self._aws_secret_access_key:
            kwargs["aws_access_key_id"] = self._aws_access_key_id
            kwargs["aws_secret_access_key"] = self._aws_secret_access_key
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url

        try:
            self._client = boto3.client("s3", **kwargs)
        except _NoCredsError as exc:
            raise ConnectorAuthError(f"S3 credential error: {exc}") from exc
        return self._client

    def _full_key(self, path: str) -> str:
        """Prepend the configured prefix to a path."""
        key = path.lstrip("/")
        if self._prefix:
            return f"{self._prefix}/{key}"
        return key

    # -- port implementation -------------------------------------------------

    async def _search(self, query: str) -> list[DocumentResult]:
        s3 = self._get_client()
        prefix = self._full_key(query)
        try:
            resp = await asyncio.to_thread(
                s3.list_objects_v2,
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=50,
            )
        except _ClientError as exc:
            raise ConnectorError(f"S3 search failed: {exc}") from exc

        return [
            DocumentResult(
                id=obj["Key"],
                name=obj["Key"].split("/")[-1],
                path=obj["Key"],
                size_bytes=obj.get("Size", 0),
                modified_at=obj.get("LastModified", "").isoformat() if hasattr(obj.get("LastModified", ""), "isoformat") else str(obj.get("LastModified", "")),
            )
            for obj in resp.get("Contents", [])
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        s3 = self._get_client()
        key = resource_id or self._full_key(path)
        if not key:
            raise ConnectorError("S3 read requires resource_id or path")

        try:
            resp = await asyncio.to_thread(
                s3.get_object, Bucket=self._bucket, Key=key
            )
        except _ClientError as exc:
            raise ConnectorError(f"S3 read failed for '{key}': {exc}") from exc

        body_bytes: bytes = await asyncio.to_thread(resp["Body"].read)
        content = body_bytes.decode("utf-8", errors="replace")

        return DocumentResult(
            id=key,
            name=key.split("/")[-1],
            path=key,
            content=content[:100_000],
            content_type=resp.get("ContentType", ""),
            size_bytes=resp.get("ContentLength", 0),
            modified_at=resp.get("LastModified", "").isoformat() if hasattr(resp.get("LastModified", ""), "isoformat") else "",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        s3 = self._get_client()
        prefix = self._full_key(path) if path and path != "/" else self._prefix
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            resp = await asyncio.to_thread(
                s3.list_objects_v2,
                Bucket=self._bucket,
                Prefix=prefix or "",
                Delimiter="/",
                MaxKeys=200,
            )
        except _ClientError as exc:
            raise ConnectorError(f"S3 list failed: {exc}") from exc

        results: list[DocumentResult] = []
        # Folders (common prefixes)
        for cp in resp.get("CommonPrefixes", []):
            results.append(
                DocumentResult(
                    id=cp["Prefix"],
                    name=cp["Prefix"].rstrip("/").split("/")[-1],
                    path=cp["Prefix"],
                    content_type="folder",
                )
            )
        # Files
        for obj in resp.get("Contents", []):
            results.append(
                DocumentResult(
                    id=obj["Key"],
                    name=obj["Key"].split("/")[-1],
                    path=obj["Key"],
                    size_bytes=obj.get("Size", 0),
                    modified_at=obj.get("LastModified", "").isoformat() if hasattr(obj.get("LastModified", ""), "isoformat") else str(obj.get("LastModified", "")),
                )
            )
        return results

    async def _write(self, path: str, content: str) -> DocumentResult:
        s3 = self._get_client()
        key = self._full_key(path)
        if not key:
            raise ConnectorError("S3 write requires a path")

        body = content.encode("utf-8")
        try:
            await asyncio.to_thread(
                s3.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="text/plain",
            )
        except _ClientError as exc:
            raise ConnectorError(f"S3 write failed for '{key}': {exc}") from exc

        return DocumentResult(
            id=key,
            name=key.split("/")[-1],
            path=key,
            content=content,
            size_bytes=len(body),
        )
