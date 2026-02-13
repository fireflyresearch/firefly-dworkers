"""ImageResolver -- resolves ImageRequest objects to ResolvedImage with actual bytes.

Supports four source types:
- **file**: reads bytes from a local file path
- **url**: fetches bytes over HTTP using ``httpx``
- **ai_generate**: placeholder for AI image generation (e.g. DALL-E)
- **stock**: placeholder for stock photo API search
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

from firefly_dworkers.design.models import ImageRequest, ResolvedImage

if TYPE_CHECKING:
    pass


class ImageResolver:
    """Resolves ImageRequest objects to ResolvedImage with actual bytes."""

    def __init__(
        self,
        *,
        ai_provider: str = "",
        ai_api_key: str = "",
        stock_provider: str = "",
        stock_api_key: str = "",
    ) -> None:
        self._ai_provider = ai_provider
        self._ai_api_key = ai_api_key
        self._stock_provider = stock_provider
        self._stock_api_key = stock_api_key

    # ── Public API ──────────────────────────────────────────────────────────

    async def resolve(self, request: ImageRequest) -> ResolvedImage:
        """Resolve a single image request to bytes."""
        if request.source_type == "file":
            return await self._resolve_file(request)
        elif request.source_type == "url":
            return await self._resolve_url(request)
        elif request.source_type == "ai_generate":
            return await self._resolve_ai(request)
        elif request.source_type == "stock":
            return await self._resolve_stock(request)
        else:
            raise ValueError(f"Unknown source_type: {request.source_type}")

    async def resolve_all(self, requests: list[ImageRequest]) -> dict[str, ResolvedImage]:
        """Resolve all requests in parallel. Returns ``{name: ResolvedImage}``."""
        results = await asyncio.gather(
            *(self.resolve(r) for r in requests),
            return_exceptions=True,
        )
        resolved: dict[str, ResolvedImage] = {}
        for req, result in zip(requests, results):
            if isinstance(result, ResolvedImage):
                resolved[req.name] = result
            else:
                # Failed resolution -- store empty image with descriptive alt_text
                resolved[req.name] = ResolvedImage(alt_text=req.alt_text or f"Failed: {result}")
        return resolved

    # ── Private resolvers ───────────────────────────────────────────────────

    async def _resolve_file(self, request: ImageRequest) -> ResolvedImage:
        """Read image bytes from local file."""
        data = await asyncio.to_thread(self._read_file_sync, request.file_path)
        mime = self._detect_mime(request.file_path)
        return ResolvedImage(data=data, mime_type=mime, alt_text=request.alt_text)

    async def _resolve_url(self, request: ImageRequest) -> ResolvedImage:
        """Fetch image bytes from URL using httpx."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(request.url)
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/png").split(";")[0]
            return ResolvedImage(data=resp.content, mime_type=mime, alt_text=request.alt_text)

    async def _resolve_ai(self, request: ImageRequest) -> ResolvedImage:
        """Generate image using AI provider (placeholder -- raises if no API key)."""
        if not self._ai_api_key:
            raise ValueError("AI image generation requires ai_api_key")
        # Placeholder: In production, call OpenAI DALL-E API or similar
        raise NotImplementedError(f"AI image generation via {self._ai_provider} not yet implemented")

    async def _resolve_stock(self, request: ImageRequest) -> ResolvedImage:
        """Fetch from stock photo API (placeholder -- raises if no API key)."""
        if not self._stock_api_key:
            raise ValueError("Stock image search requires stock_api_key")
        raise NotImplementedError(f"Stock image search via {self._stock_provider} not yet implemented")

    # ── Private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _read_file_sync(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def _detect_mime(path: str) -> str:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        return {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "webp": "image/webp",
        }.get(ext, "image/png")
