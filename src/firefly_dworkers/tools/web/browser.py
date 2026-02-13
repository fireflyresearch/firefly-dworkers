"""WebBrowserTool -- HTTP-based web browsing adapter.

Uses httpx for async HTTP requests and beautifulsoup4 for HTML parsing.
This is the lightweight adapter for simple page fetching without
JavaScript execution or interactive browsing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.web.browsing import BrowsingResult, WebBrowsingTool

# Optional dependency check
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    BS4_AVAILABLE = False


@tool_registry.register("web_browser", category="web")
class WebBrowserTool(WebBrowsingTool):
    """Fetch and extract text content from a web page URL.

    Uses httpx for async HTTP requests and beautifulsoup4 for HTML parsing.
    Both are optional dependencies; the tool degrades gracefully when
    beautifulsoup4 is unavailable (returns raw HTML) and raises an
    ImportError when httpx is missing.
    """

    def __init__(self, *, timeout: float = 30.0, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "web_browser",
            description="Fetch and extract text content from a web page URL",
            timeout=timeout,
            guards=guards,
        )

    async def _fetch_page(self, url: str, *, extract_links: bool = False) -> BrowsingResult:
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx required. Install with: pip install httpx")

        async with httpx.AsyncClient(timeout=self._timeout or 30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        title = ""
        text = html[:10000]
        links: list[dict[str, Any]] = []

        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            text = soup.get_text(separator="\n", strip=True)[:10000]
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            if extract_links:
                links = [
                    {"text": a.get_text(strip=True), "href": a.get("href", "")} for a in soup.find_all("a", href=True)
                ][:50]

        return BrowsingResult(
            url=url,
            text=text,
            status_code=response.status_code,
            title=title,
            links=links,
        )
