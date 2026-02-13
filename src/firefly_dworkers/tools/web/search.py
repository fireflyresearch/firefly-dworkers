"""WebSearchTool — abstract base for internet search providers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search result returned by a web search provider."""

    title: str
    url: str
    snippet: str


class WebSearchTool(BaseTool):
    """Abstract base for internet search tools.

    Subclasses must implement :meth:`_search` to provide results from a
    specific search provider (e.g. Google, Bing, Brave, SerpAPI).
    """

    def __init__(self, *, max_results: int = 10, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "web_search",
            description="Search the internet for information relevant to consulting tasks",
            tags=["web", "search", "research"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="query",
                    type_annotation="str",
                    description="Search query",
                    required=True,
                ),
                ParameterSpec(
                    name="max_results",
                    type_annotation="int",
                    description="Maximum number of results",
                    required=False,
                    default=max_results,
                ),
            ],
        )
        self._max_results = max_results

    async def _execute(self, **kwargs: Any) -> list[dict[str, str]]:
        query = kwargs["query"]
        max_results = kwargs.get("max_results", self._max_results)
        results = await self._search(query, max_results)
        return [r.model_dump() for r in results]

    @abstractmethod
    async def _search(self, query: str, max_results: int) -> list[SearchResult]: ...
