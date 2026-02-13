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

from fireflyframework_genai.tools.base import BaseTool
from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.registry import tool_registry

# ---------------------------------------------------------------------------
# Internal builder helpers
# ---------------------------------------------------------------------------


def _build_web_tools(config: TenantConfig) -> list[BaseTool]:
    """Build web tools from tenant connector config."""
    tools: list[BaseTool] = []

    # -- Search tool (Tavily, SerpAPI, etc.) ---------------------------------
    ws_cfg = config.connectors.web_search
    enabled = getattr(ws_cfg, "enabled", False)
    provider = getattr(ws_cfg, "provider", "tavily")
    api_key = getattr(ws_cfg, "api_key", "") or getattr(ws_cfg, "credential_ref", "")

    if enabled and tool_registry.has(provider):
        tools.append(tool_registry.create(provider, api_key=api_key))

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

    cfg = getattr(config.connectors, "jira", None)
    if cfg is not None and getattr(cfg, "enabled", False) and tool_registry.has("jira"):
        tools.append(tool_registry.create("jira"))

    return tools


# ---------------------------------------------------------------------------
# Public factory functions
# ---------------------------------------------------------------------------


def researcher_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *researcher* worker role.

    Includes web search/browsing, storage connectors, report generation,
    and RSS feed tools.
    """
    tools: list[BaseTool] = []
    tools.extend(_build_web_tools(config))
    tools.extend(_build_storage_tools(config))

    tools.append(tool_registry.create("report_generation"))
    tools.append(tool_registry.create("rss_feed"))

    return ToolKit(
        f"researcher-{config.id}",
        tools,
        description="Researcher tools",
        tags=["researcher"],
    )


def analyst_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *analyst* worker role.

    Includes storage connectors, communication connectors, and all five
    consulting tools (requirement gathering, process mapping, gap analysis,
    report generation, documentation).
    """
    tools: list[BaseTool] = []
    tools.extend(_build_storage_tools(config))
    tools.extend(_build_communication_tools(config))

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

    Includes storage connectors, spreadsheet parsing, API client, and report
    generation.
    """
    tools: list[BaseTool] = []
    tools.extend(_build_storage_tools(config))

    tools.extend([
        tool_registry.create("spreadsheet"),
        tool_registry.create("api_client"),
        tool_registry.create("report_generation"),
    ])

    return ToolKit(
        f"data-analyst-{config.id}",
        tools,
        description="Data Analyst tools",
        tags=["data_analyst"],
    )


def manager_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for the *manager* worker role.

    Includes project management tools, communication connectors, report
    generation, and documentation.
    """
    tools: list[BaseTool] = []
    tools.extend(_build_project_tools(config))
    tools.extend(_build_communication_tools(config))

    tools.extend([
        tool_registry.create("report_generation"),
        tool_registry.create("documentation"),
    ])

    return ToolKit(
        f"manager-{config.id}",
        tools,
        description="Manager tools",
        tags=["manager"],
    )
