"""RSSFeedTool — concrete tool for reading RSS/Atom feeds."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

try:
    import feedparser

    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None  # type: ignore[assignment]
    FEEDPARSER_AVAILABLE = False


class RSSFeedTool(BaseTool):
    """Read and parse RSS/Atom feeds for news and updates.

    Uses the feedparser library which is an optional dependency.
    """

    def __init__(self, *, max_entries: int = 10, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "rss_feed",
            description="Read and parse RSS/Atom feeds for news and updates",
            tags=["web", "rss", "news"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="url",
                    type_annotation="str",
                    description="RSS feed URL",
                    required=True,
                ),
                ParameterSpec(
                    name="max_entries",
                    type_annotation="int",
                    description="Maximum entries to return",
                    required=False,
                    default=max_entries,
                ),
            ],
        )
        self._max_entries = max_entries

    async def _execute(self, **kwargs: Any) -> list[dict[str, str]]:
        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser required. Install with: pip install feedparser")

        url: str = kwargs["url"]
        max_entries: int = kwargs.get("max_entries", self._max_entries)

        feed = await asyncio.to_thread(feedparser.parse, url)

        entries = []
        for entry in feed.entries[:max_entries]:
            entries.append(
                {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "summary": getattr(entry, "summary", "")[:500],
                    "published": getattr(entry, "published", ""),
                }
            )
        return entries
