"""Tests for ToolRegistry."""

from __future__ import annotations

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.registry import ToolRegistry, tool_registry


class _DummyTool(BaseTool):
    """Minimal tool for registry tests."""

    def __init__(self, **kwargs):
        super().__init__("dummy", description="dummy tool")

    async def _execute(self, **kwargs):
        return {}


class TestToolRegistry:
    """Test ToolRegistry operations."""

    def test_register_and_create(self) -> None:
        registry = ToolRegistry()

        @registry.register("my_tool", category="testing")
        class MyTool(_DummyTool):
            pass

        tool = registry.create("my_tool")
        assert isinstance(tool, MyTool)

    def test_create_missing_raises(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.create("nonexistent")

    def test_get_class(self) -> None:
        registry = ToolRegistry()

        @registry.register("cls_tool", category="testing")
        class ClsTool(_DummyTool):
            pass

        assert registry.get_class("cls_tool") is ClsTool

    def test_has(self) -> None:
        registry = ToolRegistry()

        @registry.register("has_tool", category="testing")
        class HasTool(_DummyTool):
            pass

        assert registry.has("has_tool") is True
        assert registry.has("missing") is False

    def test_list_tools(self) -> None:
        registry = ToolRegistry()

        @registry.register("a", category="testing")
        class ATool(_DummyTool):
            pass

        @registry.register("b", category="testing")
        class BTool(_DummyTool):
            pass

        names = registry.list_tools()
        assert "a" in names
        assert "b" in names

    def test_list_by_category(self) -> None:
        registry = ToolRegistry()

        @registry.register("web1", category="web")
        class Web1(_DummyTool):
            pass

        @registry.register("store1", category="storage")
        class Store1(_DummyTool):
            pass

        @registry.register("web2", category="web")
        class Web2(_DummyTool):
            pass

        web_tools = registry.list_by_category("web")
        assert sorted(web_tools) == ["web1", "web2"]

    def test_get_category(self) -> None:
        registry = ToolRegistry()

        @registry.register("cat_tool", category="my_category")
        class CatTool(_DummyTool):
            pass

        assert registry.get_category("cat_tool") == "my_category"

    def test_clear(self) -> None:
        registry = ToolRegistry()

        @registry.register("to_clear", category="testing")
        class ToClear(_DummyTool):
            pass

        assert registry.has("to_clear") is True
        registry.clear()
        assert registry.has("to_clear") is False
        assert registry.list_tools() == []

    def test_create_with_kwargs(self) -> None:
        registry = ToolRegistry()

        @registry.register("kw_tool", category="testing")
        class KwTool(_DummyTool):
            def __init__(self, *, label: str = "default"):
                super().__init__()
                self.label = label

        tool = registry.create("kw_tool", label="custom")
        assert tool.label == "custom"

    def test_decorator_returns_original_class(self) -> None:
        registry = ToolRegistry()

        @registry.register("orig", category="testing")
        class OrigTool(_DummyTool):
            pass

        assert OrigTool.__name__ == "OrigTool"
        assert registry.get_class("orig") is OrigTool

    def test_duplicate_registration_raises(self) -> None:
        """Registering a different class under the same name raises ValueError."""
        registry = ToolRegistry()

        @registry.register("dup", category="testing")
        class First(_DummyTool):
            pass

        with pytest.raises(ValueError, match="already registered"):

            @registry.register("dup", category="testing")
            class Second(_DummyTool):
                pass

    def test_idempotent_registration_same_class(self) -> None:
        """Re-registering the same class under the same name is allowed."""
        registry = ToolRegistry()

        @registry.register("idem", category="testing")
        class MyTool(_DummyTool):
            pass

        # Should not raise -- same class, same name
        registry.register("idem", category="testing")(MyTool)
        assert registry.get_class("idem") is MyTool

    def test_module_level_registry_exists(self) -> None:
        """Verify the module-level singleton exists."""
        assert isinstance(tool_registry, ToolRegistry)

    def test_module_level_registry_has_tools(self) -> None:
        """After importing tools package, registry should have entries."""
        import firefly_dworkers.tools  # noqa: F401

        assert tool_registry.has("tavily")
        assert tool_registry.has("serpapi")
        assert tool_registry.has("web_browser")
        assert tool_registry.has("flybrowser")
        assert tool_registry.has("rss_feed")
        assert tool_registry.has("sharepoint")
        assert tool_registry.has("google_drive")
        assert tool_registry.has("confluence")
        assert tool_registry.has("s3")
        assert tool_registry.has("slack")
        assert tool_registry.has("teams")
        assert tool_registry.has("email")
        assert tool_registry.has("jira")
        assert tool_registry.has("asana")
        assert tool_registry.has("spreadsheet")
        assert tool_registry.has("api_client")
        assert tool_registry.has("sql")
        assert tool_registry.has("report_generation")
        assert tool_registry.has("requirement_gathering")
        assert tool_registry.has("process_mapping")
        assert tool_registry.has("gap_analysis")
        assert tool_registry.has("documentation")

    def test_module_level_registry_categories(self) -> None:
        """Verify tools are in the correct categories."""
        import firefly_dworkers.tools  # noqa: F401

        assert tool_registry.get_category("tavily") == "web_search"
        assert tool_registry.get_category("flybrowser") == "web"
        assert tool_registry.get_category("sharepoint") == "storage"
        assert tool_registry.get_category("slack") == "communication"
        assert tool_registry.get_category("jira") == "project"
        assert tool_registry.get_category("spreadsheet") == "data"
        assert tool_registry.get_category("report_generation") == "consulting"
