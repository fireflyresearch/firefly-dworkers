"""FlyBrowserTool -- AI-driven browser automation adapter.

Uses `flybrowser <https://github.com/fireflyresearch/flybrowser>`_ for
LLM-powered browser automation.  Supports natural-language instructions
for navigation, data extraction, and interaction -- going well beyond
simple HTTP fetching.

This is an optional adapter; the ``flybrowser`` package must be installed
separately.  When unavailable, the tool raises :class:`ImportError` at
execution time, not import time, so module registration still works.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol, ParameterSpec

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.web.browsing import BrowsingResult, WebBrowsingTool

# Lazy import -- flybrowser is an optional dependency.
try:
    from flybrowser import FlyBrowser

    FLYBROWSER_AVAILABLE = True
except ImportError:
    FlyBrowser = None  # type: ignore[assignment,misc]
    FLYBROWSER_AVAILABLE = False


@tool_registry.register("flybrowser", category="web")
class FlyBrowserTool(WebBrowsingTool):
    """AI-driven browser automation using FlyBrowser.

    Extends :class:`WebBrowsingTool` with natural-language *instruction*
    and *extract_schema* parameters, enabling LLM-powered interaction with
    web pages (clicking, typing, form filling, data extraction).

    When only a ``url`` is provided (no ``instruction``), behaves like a
    standard browser: navigates to the page and returns its text content.
    When an ``instruction`` is provided, delegates to
    :meth:`FlyBrowser.act`, :meth:`FlyBrowser.extract`, or
    :meth:`FlyBrowser.agent` depending on the ``action`` parameter.

    Configuration parameters:

    * ``llm_provider`` -- LLM provider for the browser agent
      (``"openai"``, ``"anthropic"``, ``"ollama"``).
    * ``llm_model`` -- Specific model name (defaults to provider default).
    * ``llm_api_key`` -- API key for the LLM provider.
    * ``headless`` -- Run the browser in headless mode.
    * ``timeout`` -- Default timeout in seconds.
    * ``speed_preset`` -- Performance preset: ``"fast"``, ``"balanced"``,
      ``"thorough"``.
    """

    def __init__(
        self,
        *,
        llm_provider: str = "openai",
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        headless: bool = True,
        timeout: float = 60.0,
        speed_preset: str = "balanced",
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(
            "flybrowser",
            description=(
                "AI-driven browser automation: navigate, interact, and "
                "extract data from web pages using natural language"
            ),
            timeout=timeout,
            guards=guards,
            extra_parameters=[
                ParameterSpec(
                    name="instruction",
                    type_annotation="str",
                    description=(
                        "Natural language instruction for the browser agent "
                        "(e.g. 'click the login button', 'fill in the search form')"
                    ),
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="action",
                    type_annotation="str",
                    description="Browser action: 'fetch' (default), 'act', 'extract', or 'agent'",
                    required=False,
                    default="fetch",
                ),
                ParameterSpec(
                    name="extract_schema",
                    type_annotation="dict",
                    description="Optional JSON schema for structured data extraction",
                    required=False,
                    default=None,
                ),
            ],
        )
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key
        self._headless = headless
        self._speed_preset = speed_preset

    def _require_flybrowser(self) -> None:
        if not FLYBROWSER_AVAILABLE:
            raise ImportError(
                "flybrowser required for FlyBrowserTool. "
                "Install with: pip install flybrowser"
            )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Dispatch to the appropriate FlyBrowser method.

        When no ``instruction`` is given, falls back to a simple page
        fetch (same as :class:`WebBrowserTool`).  When an ``instruction``
        is present, uses the FlyBrowser agent based on ``action``.
        """
        instruction: str = kwargs.get("instruction", "")
        action: str = kwargs.get("action", "fetch")

        if not instruction or action == "fetch":
            # Simple page fetch -- delegate to the abstract base
            return await super()._execute(**kwargs)

        # Instruction-based actions require FlyBrowser
        self._require_flybrowser()
        url: str = kwargs["url"]
        extract_schema = kwargs.get("extract_schema")

        async with FlyBrowser(
            llm_provider=self._llm_provider,
            llm_model=self._llm_model,
            api_key=self._llm_api_key,
            headless=self._headless,
            timeout=self._timeout or 60.0,
            speed_preset=self._speed_preset,
        ) as browser:
            await browser.goto(url)

            if action == "act":
                result = await browser.act(instruction, return_metadata=True)
            elif action == "extract":
                result = await browser.extract(
                    instruction,
                    schema=extract_schema,
                    return_metadata=True,
                )
            elif action == "agent":
                result = await browser.agent(instruction, return_metadata=True)
            else:
                result = await browser.act(instruction, return_metadata=True)

            return {
                "url": url,
                "action": action,
                "instruction": instruction,
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "iterations": result.execution.iterations,
                "duration_seconds": result.execution.duration_seconds,
            }

    async def _fetch_page(self, url: str, *, extract_links: bool = False) -> BrowsingResult:
        """Navigate to *url* using FlyBrowser and extract page content.

        When FlyBrowser is unavailable, falls back to a basic
        ``ImportError`` to guide the user toward installation.
        """
        self._require_flybrowser()

        async with FlyBrowser(
            llm_provider=self._llm_provider,
            llm_model=self._llm_model,
            api_key=self._llm_api_key,
            headless=self._headless,
            timeout=self._timeout or 60.0,
            speed_preset=self._speed_preset,
        ) as browser:
            await browser.goto(url)

            # Extract text content via the extract method
            result = await browser.extract(
                "Extract the main text content of this page",
                return_metadata=True,
            )

            text = str(result.data) if result.data else ""
            links: list[dict[str, str]] = []

            if extract_links:
                link_result = await browser.extract(
                    "Extract all hyperlinks as a list of objects with 'text' and 'href' fields",
                    schema={"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "href": {"type": "string"}}}},
                    return_metadata=True,
                )
                if isinstance(link_result.data, list):
                    links = link_result.data[:50]

            return BrowsingResult(
                url=url,
                text=text[:10000],
                title="",
                links=links,
                metadata={
                    "provider": "flybrowser",
                    "llm_provider": self._llm_provider,
                    "iterations": result.execution.iterations,
                    "duration_seconds": result.execution.duration_seconds,
                },
            )
