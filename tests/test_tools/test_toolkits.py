"""Tests for ToolKit factory functions."""

from __future__ import annotations

from unittest.mock import patch

from fireflyframework_genai.tools import FallbackComposer, SequentialComposer
from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import (
    _build_document_tools,
    _build_presentation_tools,
    _build_research_chain,
    _build_resilient_search,
    _build_spreadsheet_tools,
    _build_web_tools,
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


class TestToolResilience:
    """Tests for FallbackComposer and SequentialComposer integration."""

    def _make_config(self, **connector_overrides: dict) -> TenantConfig:
        """Build a TenantConfig with optional connector overrides."""
        connectors = {
            "web_search": {"enabled": True, "provider": "tavily", "api_key": "test-key"},
            **connector_overrides,
        }
        return TenantConfig(id="test", name="Test", connectors=connectors)

    # -- FallbackComposer tests -----------------------------------------------

    def test_web_search_uses_fallback_composer(self) -> None:
        """When web search is enabled, _build_resilient_search returns a FallbackComposer."""
        result = _build_resilient_search("tavily", "test-key")
        assert isinstance(result, FallbackComposer)

    def test_fallback_composer_has_primary_first(self) -> None:
        """Primary provider is the first tool in the fallback chain."""
        result = _build_resilient_search("tavily", "test-key")
        assert isinstance(result, FallbackComposer)
        # First tool should be from the primary provider (Tavily)
        assert result._tools[0].name == "web_search"
        # Verify it's actually TavilySearchTool by checking type name
        assert "Tavily" in type(result._tools[0]).__name__

    def test_fallback_has_alternative_provider(self) -> None:
        """Alternative provider is included as a fallback."""
        result = _build_resilient_search("tavily", "test-key")
        assert isinstance(result, FallbackComposer)
        assert len(result._tools) >= 2
        # Second tool should be SerpAPI
        assert "SerpAPI" in type(result._tools[1]).__name__

    def test_no_fallback_when_single_provider(self) -> None:
        """When only one provider is available, returns it directly (no FallbackComposer)."""
        from firefly_dworkers.tools.registry import tool_registry

        # Temporarily pretend serpapi does not exist
        with patch.object(tool_registry, "has", side_effect=lambda n: n == "tavily"):
            result = _build_resilient_search("tavily", "test-key")
        # Should be a plain tool, not a FallbackComposer
        assert not isinstance(result, FallbackComposer)
        assert result is not None
        assert result.name == "web_search"

    def test_fallback_import_error_returns_primary(self) -> None:
        """When FallbackComposer can't be imported, returns the primary tool."""
        with patch.dict("sys.modules", {"fireflyframework_genai.tools": None}):
            # The lazy import inside _build_resilient_search should fail
            result = _build_resilient_search("tavily", "test-key")
        # Should still get a tool back (the primary)
        assert result is not None
        assert result.name == "web_search"

    def test_disabled_search_no_fallback(self) -> None:
        """Disabled web search produces no search tool at all."""
        cfg = self._make_config(
            web_search={"enabled": False, "provider": "tavily", "api_key": "key"},
        )
        tools = _build_web_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "web_search" not in tool_names

    def test_fallback_composer_name(self) -> None:
        """Composed tool has name 'web_search'."""
        result = _build_resilient_search("tavily", "test-key")
        assert result is not None
        assert result.name == "web_search"

    def test_fallback_composer_description(self) -> None:
        """Composed tool has a descriptive description."""
        result = _build_resilient_search("tavily", "test-key")
        assert result is not None
        assert "tavily" in result.description.lower()
        assert "fallback" in result.description.lower()

    # -- SequentialComposer / research chain tests ----------------------------

    def test_research_chain_created(self) -> None:
        """SequentialComposer chain exists in researcher toolkit when available."""
        cfg = self._make_config()
        chain = _build_research_chain(cfg)
        assert chain is not None
        assert isinstance(chain, SequentialComposer)
        assert chain.name == "research_chain"

    def test_research_chain_import_fallback(self) -> None:
        """When SequentialComposer is unavailable, chain is not added."""
        cfg = self._make_config()
        with patch.dict("sys.modules", {"fireflyframework_genai.tools": None}):
            chain = _build_research_chain(cfg)
        assert chain is None


class TestProductivityTools:
    """Tests for productivity tool builders and their integration with role toolkits."""

    def _make_config(self, **connector_overrides: dict) -> TenantConfig:
        """Build a TenantConfig with optional connector overrides."""
        connectors = {
            "web_search": {"enabled": True, "provider": "tavily", "api_key": "test-key"},
            **connector_overrides,
        }
        return TenantConfig(id="test", name="Test", connectors=connectors)

    # -- analyst + presentation -----------------------------------------------

    def test_analyst_has_presentation_tools_when_enabled(self) -> None:
        """Presentation enabled -> powerpoint in analyst toolkit."""
        cfg = self._make_config(presentation={"enabled": True, "provider": "powerpoint"})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "powerpoint" in tool_names

    def test_analyst_has_document_tools_when_enabled(self) -> None:
        """Document enabled -> word in analyst toolkit."""
        cfg = self._make_config(document={"enabled": True, "provider": "word"})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "word" in tool_names

    def test_analyst_no_presentation_when_disabled(self) -> None:
        """Presentation disabled -> no powerpoint in analyst toolkit."""
        cfg = self._make_config(presentation={"enabled": False})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "powerpoint" not in tool_names

    def test_analyst_no_document_when_disabled(self) -> None:
        """Document disabled -> no word in analyst toolkit."""
        cfg = self._make_config(document={"enabled": False})
        kit = analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "word" not in tool_names

    # -- data_analyst + spreadsheet / vision / data ---------------------------

    def test_data_analyst_has_spreadsheet_tools_when_enabled(self) -> None:
        """Spreadsheet enabled -> excel in data_analyst toolkit."""
        cfg = self._make_config(spreadsheet={"enabled": True, "provider": "excel"})
        kit = data_analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "excel" in tool_names

    def test_data_analyst_has_vision_tools(self) -> None:
        """Vision tools always included in data_analyst toolkit."""
        cfg = self._make_config()
        kit = data_analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "vision_analysis" in tool_names

    def test_data_analyst_has_sql_when_enabled(self) -> None:
        """SQL enabled -> sql_client in data_analyst toolkit."""
        cfg = self._make_config(sql={"enabled": True, "connection_string": "sqlite://"})
        kit = data_analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "sql_client" in tool_names

    def test_data_analyst_no_spreadsheet_when_disabled(self) -> None:
        """Spreadsheet disabled -> no excel in data_analyst toolkit."""
        cfg = self._make_config(spreadsheet={"enabled": False})
        kit = data_analyst_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "excel" not in tool_names

    # -- manager + presentation / document / asana ----------------------------

    def test_manager_has_presentation_when_enabled(self) -> None:
        """Presentation enabled -> powerpoint in manager toolkit."""
        cfg = self._make_config(presentation={"enabled": True, "provider": "powerpoint"})
        kit = manager_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "powerpoint" in tool_names

    def test_manager_has_document_when_enabled(self) -> None:
        """Document enabled -> word in manager toolkit."""
        cfg = self._make_config(document={"enabled": True, "provider": "word"})
        kit = manager_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "word" in tool_names

    def test_manager_has_asana_when_enabled(self) -> None:
        """Asana enabled -> asana in manager toolkit."""
        cfg = self._make_config(asana={"enabled": True})
        kit = manager_toolkit(cfg)
        tool_names = [t.name for t in kit.tools]
        assert "asana" in tool_names

    # -- Google provider variants ---------------------------------------------

    def test_google_slides_provider(self) -> None:
        """Presentation provider=google_slides -> google_slides tool."""
        cfg = self._make_config(
            presentation={"enabled": True, "provider": "google_slides"},
        )
        tools = _build_presentation_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "google_slides" in tool_names
        assert "powerpoint" not in tool_names

    def test_google_docs_provider(self) -> None:
        """Document provider=google_docs -> google_docs tool."""
        cfg = self._make_config(
            document={"enabled": True, "provider": "google_docs"},
        )
        tools = _build_document_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "google_docs" in tool_names
        assert "word" not in tool_names

    def test_google_sheets_provider(self) -> None:
        """Spreadsheet provider=google_sheets_spreadsheet -> google_sheets tool."""
        cfg = self._make_config(
            spreadsheet={"enabled": True, "provider": "google_sheets_spreadsheet"},
        )
        tools = _build_spreadsheet_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "google_sheets" in tool_names
        assert "excel" not in tool_names

    # -- PDF inclusion --------------------------------------------------------

    def test_pdf_included_with_presentation(self) -> None:
        """PDF tool included alongside presentation tools."""
        cfg = self._make_config(
            presentation={"enabled": True, "provider": "powerpoint"},
        )
        tools = _build_presentation_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "pdf" in tool_names

    def test_pdf_included_with_document(self) -> None:
        """PDF tool included alongside document tools."""
        cfg = self._make_config(
            document={"enabled": True, "provider": "word"},
        )
        tools = _build_document_tools(cfg)
        tool_names = [t.name for t in tools]
        assert "pdf" in tool_names
