"""ImageResolver -- resolves ImageRequest objects to ResolvedImage with actual bytes.

Supports four source types:
- **file**: reads bytes from a local file path
- **url**: fetches bytes over HTTP using ``httpx``
- **ai_generate**: placeholder for AI image generation (e.g. DALL-E)
- **stock**: placeholder for stock photo API search
"""

from __future__ import annotations

import asyncio
import base64
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
        """Generate image using AI provider."""
        if not self._ai_api_key:
            raise ValueError("AI image generation requires ai_api_key")
        if self._ai_provider == "openai":
            return await self._resolve_ai_openai(request)
        raise ValueError(f"Unsupported AI provider: {self._ai_provider}")

    async def _resolve_ai_openai(self, request: ImageRequest) -> ResolvedImage:
        """Call OpenAI DALL-E 3 API to generate an image."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self._ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": request.prompt or request.name,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            b64_str = data["data"][0]["b64_json"]
            img_bytes = base64.b64decode(b64_str)
            return ResolvedImage(
                data=img_bytes,
                mime_type="image/png",
                alt_text=request.alt_text or request.prompt,
                width=1024.0,
                height=1024.0,
            )

    async def _resolve_stock(self, request: ImageRequest) -> ResolvedImage:
        """Fetch from stock photo API."""
        if not self._stock_api_key:
            raise ValueError("Stock image search requires stock_api_key")
        if self._stock_provider == "unsplash":
            return await self._resolve_stock_unsplash(request)
        raise ValueError(f"Unsupported stock provider: {self._stock_provider}")

    async def _resolve_stock_unsplash(self, request: ImageRequest) -> ResolvedImage:
        """Search Unsplash and download the first result."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={"query": request.prompt or request.name, "per_page": 1},
                headers={"Authorization": f"Client-ID {self._stock_api_key}"},
            )
            search_resp.raise_for_status()
            results = search_resp.json().get("results", [])
            if not results:
                raise ValueError(f"No Unsplash results for: {request.prompt or request.name}")
            image_url = results[0]["urls"]["regular"]
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            mime = img_resp.headers.get("content-type", "image/jpeg").split(";")[0]
            return ResolvedImage(
                data=img_resp.content,
                mime_type=mime,
                alt_text=request.alt_text or results[0].get("alt_description", ""),
            )

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
