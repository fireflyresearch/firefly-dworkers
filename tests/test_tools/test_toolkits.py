"""Tests for ToolKit factory functions."""

from __future__ import annotations

from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import (
    analyst_toolkit,
    data_analyst_toolkit,
    manager_toolkit,
    researcher_toolkit,
)


class TestToolkitFactories:
    """Tests for the four toolkit factory functions."""

    def _make_config(self, **connector_overrides: dict) -> TenantConfig:
        """Build a TenantConfig with optional connector overrides."""
        connectors = {
            "web_search": {"enabled": True, "provider": "tavily", "api_key": "test-key"},
            **connector_overrides,
        }
        return TenantConfig(id="test", name="Test", connectors=connectors)

    # -- researcher_toolkit ---------------------------------------------------

    def test_researcher_toolkit_type(self) -> None:
        kit = researcher_toolkit(self._make_config())
        assert isinstance(kit, ToolKit)

    def test_researcher_toolkit_has_tools(self) -> None:
        kit = researcher_toolkit(self._make_config())
        assert len(kit.tools) > 0

    def test_researcher_has_web_search(self) -> None:
        kit = researcher_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "web_search" in tool_names

    def test_researcher_has_web_browser(self) -> None:
        kit = researcher_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "web_browser" in tool_names

    def test_researcher_has_report_generation(self) -> None:
        kit = researcher_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "report_generation" in tool_names

    def test_researcher_has_rss_feed(self) -> None:
        kit = researcher_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "rss_feed" in tool_names

    def test_researcher_name_includes_tenant_id(self) -> None:
        kit = researcher_toolkit(self._make_config())
        assert "test" in kit.name

    def test_researcher_serpapi_provider(self) -> None:
        cfg = self._make_config(
            web_search={"enabled": True, "provider": "serpapi", "api_key": "serp-key"},
        )
        kit = researcher_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "web_search" in tool_names

    def test_researcher_web_search_disabled(self) -> None:
        cfg = self._make_config(
            web_search={"enabled": False, "provider": "tavily", "api_key": "key"},
        )
        kit = researcher_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        # Should not have web_search but should still have web_browser
        assert "web_search" not in tool_names
        assert "web_browser" in tool_names

    # -- analyst_toolkit ------------------------------------------------------

    def test_analyst_toolkit_type(self) -> None:
        kit = analyst_toolkit(self._make_config())
        assert isinstance(kit, ToolKit)

    def test_analyst_has_consulting_tools(self) -> None:
        kit = analyst_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "requirement_gathering" in tool_names
        assert "process_mapping" in tool_names
        assert "gap_analysis" in tool_names
        assert "report_generation" in tool_names
        assert "documentation" in tool_names

    def test_analyst_name_includes_tenant_id(self) -> None:
        kit = analyst_toolkit(self._make_config())
        assert "test" in kit.name

    # -- data_analyst_toolkit -------------------------------------------------

    def test_data_analyst_toolkit_type(self) -> None:
        kit = data_analyst_toolkit(self._make_config())
        assert isinstance(kit, ToolKit)

    def test_data_analyst_has_data_tools(self) -> None:
        kit = data_analyst_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "spreadsheet" in tool_names
        assert "api_client" in tool_names
        assert "report_generation" in tool_names

    def test_data_analyst_name_includes_tenant_id(self) -> None:
        kit = data_analyst_toolkit(self._make_config())
        assert "test" in kit.name

    # -- manager_toolkit ------------------------------------------------------

    def test_manager_toolkit_type(self) -> None:
        kit = manager_toolkit(self._make_config())
        assert isinstance(kit, ToolKit)

    def test_manager_has_consulting_tools(self) -> None:
        kit = manager_toolkit(self._make_config())
        tool_names = [t.name for t in kit.tools]
        assert "report_generation" in tool_names
        assert "documentation" in tool_names

    def test_manager_name_includes_tenant_id(self) -> None:
        kit = manager_toolkit(self._make_config())
        assert "test" in kit.name

    def test_manager_jira_enabled(self) -> None:
        cfg = self._make_config(jira={"enabled": True})
        kit = manager_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "jira" in tool_names

    def test_manager_jira_disabled(self) -> None:
        cfg = self._make_config(jira={"enabled": False})
        kit = manager_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "jira" not in tool_names

    # -- storage connector inclusion ------------------------------------------

    def test_researcher_includes_sharepoint_when_enabled(self) -> None:
        cfg = self._make_config(sharepoint={"enabled": True})
        kit = researcher_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "sharepoint" in tool_names

    def test_researcher_excludes_sharepoint_when_disabled(self) -> None:
        cfg = self._make_config(sharepoint={"enabled": False})
        kit = researcher_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "sharepoint" not in tool_names

    # -- communication connector inclusion ------------------------------------

    def test_analyst_includes_slack_when_enabled(self) -> None:
        cfg = self._make_config(slack={"enabled": True})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "slack" in tool_names

    def test_analyst_excludes_slack_when_disabled(self) -> None:
        cfg = self._make_config(slack={"enabled": False})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "slack" not in tool_names

    # -- as_pydantic_tools conversion -----------------------------------------

    def test_toolkit_pydantic_conversion(self) -> None:
        kit = researcher_toolkit(self._make_config())
        pydantic_tools = kit.as_pydantic_tools()
        assert len(pydantic_tools) > 0

    # -- tags -----------------------------------------------------------------

    def test_researcher_toolkit_tags(self) -> None:
        kit = researcher_toolkit(self._make_config())
        assert "researcher" in kit.tags

    def test_analyst_toolkit_tags(self) -> None:
        kit = analyst_toolkit(self._make_config())
        assert "analyst" in kit.tags

    def test_data_analyst_toolkit_tags(self) -> None:
        kit = data_analyst_toolkit(self._make_config())
        assert "data_analyst" in kit.tags

    def test_manager_toolkit_tags(self) -> None:
        kit = manager_toolkit(self._make_config())
        assert "manager" in kit.tags
