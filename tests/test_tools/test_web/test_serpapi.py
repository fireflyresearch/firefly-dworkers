"""Tests for SerpAPISearchTool."""

from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.web.serpapi import SerpAPISearchTool


class TestSerpAPISearchTool:
    def test_instantiation(self):
        tool = SerpAPISearchTool(api_key="test-key")
        assert tool is not None

    def test_name(self):
        tool = SerpAPISearchTool(api_key="test-key")
        assert tool.name == "web_search"

    def test_tags(self):
        tool = SerpAPISearchTool(api_key="test-key")
        assert "web" in tool.tags
        assert "search" in tool.tags

    def test_is_base_tool(self):
        tool = SerpAPISearchTool(api_key="test-key")
        assert isinstance(tool, BaseTool)

    def test_max_results_default(self):
        tool = SerpAPISearchTool(api_key="test-key")
        assert tool._max_results == 10

    def test_max_results_custom(self):
        tool = SerpAPISearchTool(api_key="test-key", max_results=3)
        assert tool._max_results == 3

    def test_parameters(self):
        tool = SerpAPISearchTool(api_key="test-key")
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "max_results" in param_names

    def test_api_key_stored(self):
        tool = SerpAPISearchTool(api_key="my-serpapi-key")
        assert tool._api_key == "my-serpapi-key"

    def test_config_params(self):
        tool = SerpAPISearchTool(
            api_key="key",
            base_url="https://custom.serpapi.com/search.json",
            timeout=45.0,
            max_snippet_length=300,
            max_results=15,
        )
        assert tool._base_url == "https://custom.serpapi.com/search.json"
        assert tool._timeout == 45.0
        assert tool._max_snippet_length == 300
        assert tool._max_results == 15

    def test_default_config_values(self):
        tool = SerpAPISearchTool(api_key="key")
        assert tool._base_url == "https://serpapi.com/search.json"
        assert tool._timeout == 30.0
        assert tool._max_snippet_length == 500
