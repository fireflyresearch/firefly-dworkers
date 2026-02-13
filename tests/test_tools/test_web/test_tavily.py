"""Tests for TavilySearchTool."""

from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.web.tavily import TavilySearchTool


class TestTavilySearchTool:
    def test_instantiation(self):
        tool = TavilySearchTool(api_key="test-key")
        assert tool is not None

    def test_name(self):
        tool = TavilySearchTool(api_key="test-key")
        assert tool.name == "web_search"

    def test_tags(self):
        tool = TavilySearchTool(api_key="test-key")
        assert "web" in tool.tags
        assert "search" in tool.tags

    def test_is_base_tool(self):
        tool = TavilySearchTool(api_key="test-key")
        assert isinstance(tool, BaseTool)

    def test_max_results_default(self):
        tool = TavilySearchTool(api_key="test-key")
        assert tool._max_results == 10

    def test_max_results_custom(self):
        tool = TavilySearchTool(api_key="test-key", max_results=5)
        assert tool._max_results == 5

    def test_parameters(self):
        tool = TavilySearchTool(api_key="test-key")
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "max_results" in param_names

    def test_api_key_stored(self):
        tool = TavilySearchTool(api_key="my-secret-key")
        assert tool._api_key == "my-secret-key"

    def test_config_params(self):
        tool = TavilySearchTool(
            api_key="key",
            base_url="https://custom.tavily.com/search",
            timeout=60.0,
            max_snippet_length=200,
            max_results=20,
        )
        assert tool._base_url == "https://custom.tavily.com/search"
        assert tool._timeout == 60.0
        assert tool._max_snippet_length == 200
        assert tool._max_results == 20

    def test_default_config_values(self):
        tool = TavilySearchTool(api_key="key")
        assert tool._base_url == "https://api.tavily.com/search"
        assert tool._timeout == 30.0
        assert tool._max_snippet_length == 500
