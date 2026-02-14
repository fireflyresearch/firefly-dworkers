"""ToolKit factories -- build per-worker ToolKits from tenant configuration.

Each factory reads ``tenant_config.connectors`` to determine which providers
to instantiate, then bundles the resulting tools into a
:class:`~fireflyframework_genai.tools.toolkit.ToolKit` keyed to a worker role.

Switching from one provider to another (e.g. Tavily to SerpAPI) is purely a
YAML / configuration change -- no code modifications required.

Tool classes are discovered via :data:`tool_registry` -- concrete tools
self-register when their modules are imported (triggered by
:mod:`firefly_dworkers.tools.__init__`).
"""

from __future__ import annotations

import contextlib
from typing import Any

from fireflyframework_genai.tools.base import BaseTool
from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.registry import tool_registry

# ---------------------------------------------------------------------------
# Internal builder helpers
# ---------------------------------------------------------------------------

# Known web-search provider keys (in preferred fallback order).
_WEB_SEARCH_PROVIDERS = ("tavily", "serpapi")


def _build_resilient_search(primary_provider: str, api_key: str) -> BaseTool | Any | None:
    """Build a resilient web search tool with fallback.

    Creates the primary provider and wraps it with a
    :class:`~fireflyframework_genai.tools.FallbackComposer` that includes
    alternative providers as fallbacks.
    """
    if not tool_registry.has(primary_provider):
        return None

    primary = tool_registry.create(primary_provider, api_key=api_key)

    # Build fallback chain: primary provider + all other web_search providers
    fallbacks: list[Any] = []
    for p in _WEB_SEARCH_PROVIDERS:
        if p != primary_provider and tool_registry.has(p):
            with contextlib.suppress(Exception):
                fallbacks.append(tool_registry.create(p, api_key=api_key))

    if not fallbacks:
        return primary  # No fallbacks available, return primary alone

    try:
        from fireflyframework_genai.tools import FallbackComposer

        return FallbackComposer(
            "web_search",
            tools=[primary, *fallbacks],
            description=f"Resilient web search ({primary_provider} with fallbacks)",
        )
    except ImportError:
        return primary  # FallbackComposer not available, use primary


def _build_research_chain(config: TenantConfig) -> BaseTool | Any | None:
    """Build a sequential search-then-report chain.

    Chains web search with report generation for automated research workflows
    using :class:`~fireflyframework_genai.tools.SequentialComposer`.
    """
    search_tools = _build_web_tools(config)
    search = next((t for t in search_tools if t.name == "web_search"), None)

    if search is None:
        return None

    if not tool_registry.has("report_generation"):
        return None

    report = tool_registry.create("report_generation")

    try:
        from fireflyframework_genai.tools import SequentialComposer

        return SequentialComposer(
            "research_chain",
            tools=[search, report],
            description="Search web then generate report from results",
        )
    except ImportError:
        return None


def _build_web_tools(config: TenantConfig) -> list[Any]:
    """Build web tools from tenant connector config."""
    tools: list[Any] = []

    # -- Search tool (Tavily, SerpAPI, etc.) ---------------------------------
    ws_cfg = config.connectors.web_search
    enabled = getattr(ws_cfg, "enabled", False)
    provider = getattr(ws_cfg, "provider", "tavily")
    api_key = getattr(ws_cfg, "api_key", "") or getattr(ws_cfg, "credential_ref", "")

    if enabled:
        search_tool = _build_resilient_search(provider, api_key)
        if search_tool is not None:
            tools.append(search_tool)

    # -- Browser tool (web_browser or flybrowser) ----------------------------
    wb_cfg = config.connectors.web_browser
    browser_provider = getattr(wb_cfg, "provider", "web_browser")

    if browser_provider == "flybrowser" and tool_registry.has("flybrowser"):
        tools.append(
            tool_registry.create(
                "flybrowser",
                llm_provider=getattr(wb_cfg, "llm_provider", "openai"),
                llm_model=getattr(wb_cfg, "llm_model", None) or None,
                llm_api_key=getattr(wb_cfg, "llm_api_key", None) or None,
                headless=getattr(wb_cfg, "headless", True),
                timeout=getattr(wb_cfg, "timeout", 60.0),
                speed_preset=getattr(wb_cfg, "speed_preset", "balanced"),
            )
        )
    else:
        tools.append(tool_registry.create("web_browser"))

    return tools


def _build_storage_tools(config: TenantConfig) -> list[BaseTool]:
    """Build storage tools for enabled connectors."""
    tools: list[BaseTool] = []

    for attr_name in ("sharepoint", "google_drive", "confluence"):
        cfg = getattr(config.connectors, attr_name, None)
        if cfg is None:
            continue
        enabled = getattr(cfg, "enabled", False)
        if enabled and tool_registry.has(attr_name):
            tools.append(tool_registry.create(attr_name))

    return tools


def _build_communication_tools(config: TenantConfig) -> list[BaseTool]:
    """Build communication tools for enabled connectors."""
    tools: list[BaseTool] = []

    for attr_name in ("slack", "teams", "email"):
        cfg = getattr(config.connectors, attr_name, None)
        if cfg is None:
            continue
        enabled = getattr(cfg, "enabled", False)
        if enabled and tool_registry.has(attr_name):
            tools.append(tool_registry.create(attr_name))

    return tools


def _build_project_tools(config: TenantConfig) -> list[BaseTool]:
    """Build project management tools for enabled connectors."""
    tools: list[BaseTool] = []

    # Jira
    cfg = getattr(config.connectors, "jira", None)
    if cfg is not None and getattr(cfg, "enabled", False) and tool_registry.has("jira"):
        tools.append(tool_registry.create("jira"))

    # Asana
    cfg = getattr(config.connectors, "asana", None)
    if cfg is not None and getattr(cfg, "enabled", False) and tool_registry.has("asana"):
        tools.append(tool_registry.create("asana"))

    return tools


def _build_presentation_tools(config: TenantConfig) -> list[BaseTool]:
    """Build presentation tools from tenant connector config."""
    tools: list[BaseTool] = []
    cfg = config.connectors.presentation
    if not getattr(cfg, "enabled", False):
        return tools
    provider = getattr(cfg, "provider", "powerpoint")
    if tool_registry.has(provider):
        tools.append(tool_registry.create(provider))
    # Always include PDF for presentation export
    if tool_registry.has("pdf"):
        tools.append(tool_registry.create("pdf"))
    return tools


def _build_document_tools(config: TenantConfig) -> list[BaseTool]:
    """Build document tools from tenant connector config."""
    tools: list[BaseTool] = []
    cfg = config.connectors.document
    if not getattr(cfg, "enabled", False):
        return tools
    provider = getattr(cfg, "provider", "word")
    if tool_registry.has(provider):
        tools.append(tool_registry.create(provider))
    # Always include PDF for document export
    if tool_registry.has("pdf"):
        tools.append(tool_registry.create("pdf"))
    return tools


def _build_spreadsheet_tools(config: TenantConfig) -> list[BaseTool]:
    """Build spreadsheet tools from tenant connector config."""
    tools: list[BaseTool] = []
    cfg = config.connectors.spreadsheet
    if not getattr(cfg, "enabled", False):
        return tools
    provider = getattr(cfg, "provider", "excel")
    if tool_registry.has(provider):
        tools.append(tool_registry.create(provider))
    return tools


def _build_data_tools(config: TenantConfig) -> list[BaseTool]:
    """Build data analysis tools from tenant connector config."""
    tools: list[BaseTool] = []
    sql_cfg = config.connectors.sql
    if getattr(sql_cfg, "enabled", False) and tool_registry.has("sql"):
        tools.append(tool_registry.create("sql"))
    return tools


def _build_vision_tools(config: TenantConfig) -> list[BaseTool]:
    """Build vision analysis tools from tenant connector config."""
    tools: list[BaseTool] = []
    cfg = config.connectors.vision
    if not getattr(cfg, "enabled", False):
        return tools
    provider = getattr(cfg, "provider", "vision_analysis")
    if tool_registry.has(provider):
        tools.append(tool_registry.create(provider))
    return tools


# ---------------------------------------------------------------------------
# Public factory functions
# ---------------------------------------------------------------------------


def researcher_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *researcher* worker role.

    Includes web search/browsing, storage connectors, report generation,
    RSS feed tools, and a research chain (search -> report) when the
    :class:`~fireflyframework_genai.tools.SequentialComposer` is available.
    """
    tools: list[Any] = []
    tools.extend(_build_web_tools(config))
    tools.extend(_build_storage_tools(config))

    tools.append(tool_registry.create("report_generation"))
    tools.append(tool_registry.create("rss_feed"))

    # Add research chain (search -> report) if composer is available
    chain = _build_research_chain(config)
    if chain is not None:
        tools.append(chain)

    return ToolKit(
        f"researcher-{config.id}",
        tools,
        description="Researcher tools",
        tags=["researcher"],
    )


def analyst_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *analyst* worker role.

    Includes storage connectors, communication connectors, presentation
    and document tools, and all five consulting tools (requirement gathering,
    process mapping, gap analysis, report generation, documentation).
    """
    tools: list[BaseTool] = []
    tools.extend(_build_storage_tools(config))
    tools.extend(_build_communication_tools(config))
    tools.extend(_build_presentation_tools(config))
    tools.extend(_build_document_tools(config))

    tools.extend(
        [
            tool_registry.create("requirement_gathering"),
            tool_registry.create("process_mapping"),
            tool_registry.create("gap_analysis"),
            tool_registry.create("report_generation"),
            tool_registry.create("documentation"),
        ]
    )

    return ToolKit(
        f"analyst-{config.id}",
        tools,
        description="Analyst tools",
        tags=["analyst"],
    )


def data_analyst_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *data analyst* worker role.

    Includes storage connectors, spreadsheet tools, data analysis tools,
    vision analysis, spreadsheet parsing, API client, and report generation.
    """
    tools: list[BaseTool] = []
    tools.extend(_build_storage_tools(config))
    tools.extend(_build_spreadsheet_tools(config))
    tools.extend(_build_data_tools(config))
    tools.extend(_build_vision_tools(config))

    tools.extend(
        [
            tool_registry.create("spreadsheet"),
            tool_registry.create("api_client"),
            tool_registry.create("report_generation"),
        ]
    )

    return ToolKit(
        f"data-analyst-{config.id}",
        tools,
        description="Data Analyst tools",
        tags=["data_analyst"],
    )


def manager_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *manager* worker role.

    Includes project management tools, communication connectors, all
    productivity tools (presentation, document, spreadsheet, vision),
    report generation, and documentation.
    """
    tools: list[BaseTool] = []
    tools.extend(_build_project_tools(config))
    tools.extend(_build_communication_tools(config))
    tools.extend(_build_presentation_tools(config))
    tools.extend(_build_document_tools(config))
    tools.extend(_build_spreadsheet_tools(config))
    tools.extend(_build_vision_tools(config))

    tools.extend(
        [
            tool_registry.create("report_generation"),
            tool_registry.create("documentation"),
        ]
    )

    return ToolKit(
        f"manager-{config.id}",
        tools,
        description="Manager tools",
        tags=["manager"],
    )


def designer_toolkit(
    config: TenantConfig,
    *,
    autonomy_level: Any = None,
    checkpoint_handler: Any = None,
) -> ToolKit:
    """Build a ToolKit for the *designer* worker role.

    Includes all productivity tools (presentation, document, spreadsheet),
    vision tools, storage connectors, report generation, and the design
    pipeline tool when registered.

    Parameters:
        config: Tenant configuration.
        autonomy_level: Autonomy level for design pipeline checkpoints.
        checkpoint_handler: Handler for autonomy checkpoints.
    """
    tools: list[Any] = []
    tools.extend(_build_presentation_tools(config))
    tools.extend(_build_document_tools(config))
    tools.extend(_build_spreadsheet_tools(config))
    tools.extend(_build_vision_tools(config))
    tools.extend(_build_storage_tools(config))

    tools.extend(
        [
            tool_registry.create("report_generation"),
        ]
    )

    # Add design pipeline tool if registered
    if tool_registry.has("design_pipeline"):
        model = config.models.default
        vlm_model = getattr(config.models, "vision", "") or ""
        pipeline_kwargs: dict[str, Any] = {
            "model": model,
            "vlm_model": vlm_model,
        }
        if autonomy_level is not None:
            pipeline_kwargs["autonomy_level"] = autonomy_level
        if checkpoint_handler is not None:
            pipeline_kwargs["checkpoint_handler"] = checkpoint_handler
        tools.append(tool_registry.create("design_pipeline", **pipeline_kwargs))

    return ToolKit(
        f"designer-{config.id}",
        tools,
        description="Designer tools",
        tags=["designer"],
    )
