"""WebBrowsingTool -- abstract base for web browsing providers.

Defines the port (hexagonal architecture) for tools that navigate to URLs
and return page content.  Concrete adapters implement :meth:`_fetch_page`
to provide content from a specific browser backend (HTTP client, headless
browser, AI-driven browser, etc.).
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from pydantic import BaseModel


class BrowsingResult(BaseModel):
    """Structured result from a web browsing operation."""

    url: str
    text: str
    status_code: int = 200
    title: str = ""
    links: list[dict[str, str]] = []
    metadata: dict[str, Any] = {}


class WebBrowsingTool(BaseTool):
    """Abstract base for web browsing tools.

    Subclasses must implement :meth:`_fetch_page` to provide page content
    from a specific browser backend (e.g. HTTP + BeautifulSoup, Playwright,
    FlyBrowser).

    The ``_execute`` dispatcher calls ``_fetch_page`` for basic URL
    fetching.  Subclasses may extend ``_execute`` to support additional
    parameters (e.g. natural-language instructions for AI-driven browsers).
    """

    def __init__(
        self,
        name: str = "web_browsing",
        *,
        description: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        extra_parameters: Sequence[ParameterSpec] = (),
    ):
        parameters = [
            ParameterSpec(
                name="url",
                type_annotation="str",
                description="URL to navigate to",
                required=True,
            ),
            ParameterSpec(
                name="extract_links",
                type_annotation="bool",
                description="Also extract links from the page",
                required=False,
                default=False,
            ),
            *extra_parameters,
        ]
        super().__init__(
            name,
            description=description or "Navigate to a URL and extract page content",
            tags=["web", "browser", "browsing"],
            guards=guards,
            parameters=parameters,
            timeout=timeout,
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        url: str = kwargs["url"]
        extract_links: bool = kwargs.get("extract_links", False)
        result = await self._fetch_page(url, extract_links=extract_links)
        return result.model_dump()

    @abstractmethod
    async def _fetch_page(self, url: str, *, extract_links: bool = False) -> BrowsingResult:
        """Navigate to *url* and return page content.

        Parameters:
            url: The URL to fetch.
            extract_links: Whether to also extract hyperlinks.
        """
        ...
