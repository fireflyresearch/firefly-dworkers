"""Web tools — search, browser, and RSS feed tools."""

from __future__ import annotations

from firefly_dworkers.tools.web.browser import WebBrowserTool
from firefly_dworkers.tools.web.rss import RSSFeedTool
from firefly_dworkers.tools.web.search import SearchResult, WebSearchTool

__all__ = [
    "RSSFeedTool",
    "SearchResult",
    "WebBrowserTool",
    "WebSearchTool",
]
