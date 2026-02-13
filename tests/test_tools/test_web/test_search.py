"""Tests for WebSearchTool abstract base."""

from __future__ import annotations

from firefly_dworkers.tools.web.search import SearchResult, WebSearchTool


class FakeSearchTool(WebSearchTool):
    """Concrete implementation for testing."""

    async def _search(self, query: str, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Result for {query}",
                url="https://example.com",
                snippet=f"About {query}",
            )
        ]


class TestWebSearchTool:
    async def test_execute(self):
        tool = FakeSearchTool()
        result = await tool.execute(query="AI consulting")
        assert len(result) == 1
        assert result[0]["title"] == "Result for AI consulting"
        assert result[0]["url"] == "https://example.com"
        assert result[0]["snippet"] == "About AI consulting"

    def test_name(self):
        assert FakeSearchTool().name == "web_search"

    def test_tags(self):
        tags = FakeSearchTool().tags
        assert "web" in tags
        assert "search" in tags
        assert "research" in tags

    def test_description(self):
        tool = FakeSearchTool()
        assert "search" in tool.description.lower()

    async def test_max_results_default(self):
        tool = FakeSearchTool()
        assert tool._max_results == 10

    async def test_max_results_custom(self):
        tool = FakeSearchTool(max_results=5)
        assert tool._max_results == 5

    async def test_max_results_kwarg_override(self):
        tool = FakeSearchTool(max_results=10)
        result = await tool.execute(query="test", max_results=3)
        assert isinstance(result, list)

    def test_parameters(self):
        tool = FakeSearchTool()
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "max_results" in param_names

    def test_is_base_tool(self):
        from fireflyframework_genai.tools.base import BaseTool

        assert isinstance(FakeSearchTool(), BaseTool)
