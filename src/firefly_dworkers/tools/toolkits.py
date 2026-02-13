"""ToolKit factories — build per-worker ToolKits from tenant configuration.

Each factory reads ``tenant_config.connectors`` to determine which providers
to instantiate, then bundles the resulting tools into a
:class:`~fireflyframework_genai.tools.toolkit.ToolKit` keyed to a worker role.

Switching from one provider to another (e.g. Tavily to SerpAPI) is purely a
YAML / configuration change — no code modifications required.
"""

from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool
from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig

# ---------------------------------------------------------------------------
# Internal builder helpers
# ---------------------------------------------------------------------------


def _build_web_tools(config: TenantConfig) -> list[BaseTool]:
    """Build web tools from tenant connector config."""
    tools: list[BaseTool] = []

    ws_cfg = config.connectors.web_search
    enabled = getattr(ws_cfg, "enabled", False)
    provider = getattr(ws_cfg, "provider", "tavily")
    api_key = getattr(ws_cfg, "api_key", "") or getattr(ws_cfg, "credential_ref", "")

    if enabled:
        if provider == "tavily":
            from firefly_dworkers.tools.web.tavily import TavilySearchTool

            tools.append(TavilySearchTool(api_key=api_key))
        elif provider == "serpapi":
            from firefly_dworkers.tools.web.serpapi import SerpAPISearchTool

            tools.append(SerpAPISearchTool(api_key=api_key))

    from firefly_dworkers.tools.web.browser import WebBrowserTool

    tools.append(WebBrowserTool())
    return tools


def _build_storage_tools(config: TenantConfig) -> list[BaseTool]:
    """Build storage tools for enabled connectors."""
    tools: list[BaseTool] = []

    for attr_name, import_path in [
        ("sharepoint", "firefly_dworkers.tools.storage.sharepoint.SharePointTool"),
        ("google_drive", "firefly_dworkers.tools.storage.google_drive.GoogleDriveTool"),
        ("confluence", "firefly_dworkers.tools.storage.confluence.ConfluenceTool"),
    ]:
        cfg = getattr(config.connectors, attr_name, None)
        if cfg is None:
            continue
        enabled = getattr(cfg, "enabled", False)
        if enabled:
            import importlib

            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            tools.append(tool_class())

    return tools


def _build_communication_tools(config: TenantConfig) -> list[BaseTool]:
    """Build communication tools for enabled connectors."""
    tools: list[BaseTool] = []

    for attr_name, import_path in [
        ("slack", "firefly_dworkers.tools.communication.slack.SlackTool"),
        ("teams", "firefly_dworkers.tools.communication.teams.TeamsTool"),
        ("email", "firefly_dworkers.tools.communication.email.EmailTool"),
    ]:
        cfg = getattr(config.connectors, attr_name, None)
        if cfg is None:
            continue
        enabled = getattr(cfg, "enabled", False)
        if enabled:
            import importlib

            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            tools.append(tool_class())

    return tools


def _build_project_tools(config: TenantConfig) -> list[BaseTool]:
    """Build project management tools for enabled connectors."""
    tools: list[BaseTool] = []

    cfg = getattr(config.connectors, "jira", None)
    if cfg is not None and getattr(cfg, "enabled", False):
        from firefly_dworkers.tools.project.jira import JiraTool

        tools.append(JiraTool())

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

    from firefly_dworkers.tools.consulting.report_generation import ReportGenerationTool
    from firefly_dworkers.tools.web.rss import RSSFeedTool

    tools.append(ReportGenerationTool())
    tools.append(RSSFeedTool())

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

    from firefly_dworkers.tools.consulting.documentation import DocumentationTool
    from firefly_dworkers.tools.consulting.gap_analysis import GapAnalysisTool
    from firefly_dworkers.tools.consulting.process_mapping import ProcessMappingTool
    from firefly_dworkers.tools.consulting.report_generation import ReportGenerationTool
    from firefly_dworkers.tools.consulting.requirement_gathering import (
        RequirementGatheringTool,
    )

    tools.extend(
        [
            RequirementGatheringTool(),
            ProcessMappingTool(),
            GapAnalysisTool(),
            ReportGenerationTool(),
            DocumentationTool(),
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

    from firefly_dworkers.tools.consulting.report_generation import ReportGenerationTool
    from firefly_dworkers.tools.data.api_client import GenericAPITool
    from firefly_dworkers.tools.data.csv_excel import SpreadsheetTool

    tools.extend([SpreadsheetTool(), GenericAPITool(), ReportGenerationTool()])

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

    from firefly_dworkers.tools.consulting.documentation import DocumentationTool
    from firefly_dworkers.tools.consulting.report_generation import ReportGenerationTool

    tools.extend([ReportGenerationTool(), DocumentationTool()])

    return ToolKit(
        f"manager-{config.id}",
        tools,
        description="Manager tools",
        tags=["manager"],
    )
