"""SerpAPISearchTool — web search via the SerpAPI endpoint."""

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


class SerpAPISearchTool(WebSearchTool):
    """Web search using the SerpAPI service.

    Requires an API key from `<https://serpapi.com>`_ and the ``httpx`` package.

    Configuration parameters:

    * ``api_key`` -- SerpAPI API key (required).
    * ``base_url`` -- SerpAPI endpoint URL.
    * ``timeout`` -- HTTP request timeout in seconds.
    * ``max_snippet_length`` -- Maximum character length for result snippets.
    * ``max_results`` -- Default maximum number of results to return.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://serpapi.com/search.json",
        timeout: float = 30.0,
        max_snippet_length: int = 500,
        max_results: int = 10,
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(max_results=max_results, guards=guards)
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_snippet_length = max_snippet_length

    async def _search(self, query: str, max_results: int) -> list[SearchResult]:
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx required for SerpAPISearchTool — install with: pip install httpx")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                self._base_url,
                params={
                    "api_key": self._api_key,
                    "q": query,
                    "num": max_results,
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", "")[:self._max_snippet_length],
            )
            for r in data.get("organic_results", [])[:max_results]
        ]
