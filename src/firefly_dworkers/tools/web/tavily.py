"""TavilySearchTool — web search via the Tavily API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.tools.web.search import SearchResult, WebSearchTool

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False


class TavilySearchTool(WebSearchTool):
    """Web search using the Tavily API.

    Requires an API key from `<https://tavily.com>`_ and the ``httpx`` package.
    """

    def __init__(
        self,
        *,
        api_key: str,
        max_results: int = 10,
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(max_results=max_results, guards=guards)
        self._api_key = api_key

    async def _search(self, query: str, max_results: int) -> list[SearchResult]:
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx required for TavilySearchTool — install with: pip install httpx")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", "")[:500],
            )
            for r in data.get("results", [])
        ]
