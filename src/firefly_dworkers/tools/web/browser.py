"""WebBrowserTool — concrete tool for fetching and parsing web pages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

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


class WebBrowserTool(BaseTool):
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
            tags=["web", "browser", "scraping"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="url",
                    type_annotation="str",
                    description="URL to fetch",
                    required=True,
                ),
                ParameterSpec(
                    name="extract_links",
                    type_annotation="bool",
                    description="Also extract links",
                    required=False,
                    default=False,
                ),
            ],
            timeout=timeout,
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        url: str = kwargs["url"]
        extract_links: bool = kwargs.get("extract_links", False)

        if not HTTPX_AVAILABLE:
            raise ImportError("httpx required. Install with: pip install httpx")

        async with httpx.AsyncClient(timeout=self._timeout or 30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            text = soup.get_text(separator="\n", strip=True)
            result: dict[str, Any] = {"url": url, "text": text[:10000], "status_code": response.status_code}
            if extract_links:
                links = [
                    {"text": a.get_text(strip=True), "href": a.get("href", "")} for a in soup.find_all("a", href=True)
                ]
                result["links"] = links[:50]
            return result

        return {"url": url, "text": html[:10000], "status_code": response.status_code}
