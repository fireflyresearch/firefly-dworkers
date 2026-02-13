"""S3Tool — document access via Amazon S3."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool


class S3Tool(DocumentStorageTool):
    """Amazon S3 document access.

    Requires ``boto3`` for production use.
    The current implementation provides placeholder responses that allow the
    full architecture to work end-to-end while credentials are configured.
    """

    def __init__(
        self,
        *,
        bucket: str = "",
        region: str = "us-east-1",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        **kwargs: Any,
    ):
        super().__init__("s3", description="Access Amazon S3 buckets and objects")
        self._bucket = bucket
        self._region = region
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key

    async def _search(self, query: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="s3-placeholder",
                name=f"Search: {query}",
                path="",
                content=f"S3 search for '{query}' (configure credentials to enable)",
            )
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        return DocumentResult(
            id=resource_id or "s3-read",
            name=path or resource_id,
            content="S3 read (configure credentials to enable)",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="s3-list",
                name=path or "/",
                content="S3 listing (configure credentials to enable)",
            )
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        return DocumentResult(
            id="s3-write",
            name=path,
            content=f"Written {len(content)} chars to S3 (configure credentials to enable)",
        )
