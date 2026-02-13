"""Tests for WebBrowsingTool abstract base and the FlyBrowser adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.web.browser import WebBrowserTool
from firefly_dworkers.tools.web.browsing import BrowsingResult, WebBrowsingTool
from firefly_dworkers.tools.web.flybrowser import FlyBrowserTool

# ---------------------------------------------------------------------------
# Fake adapter for testing the abstract base
# ---------------------------------------------------------------------------


class FakeBrowsingTool(WebBrowsingTool):
    """Concrete implementation for testing the abstract base."""

    async def _fetch_page(self, url: str, *, extract_links: bool = False) -> BrowsingResult:
        links = [{"text": "Example", "href": "https://example.com"}] if extract_links else []
        return BrowsingResult(
            url=url,
            text=f"Content of {url}",
            status_code=200,
            title=f"Title of {url}",
            links=links,
        )


# ---------------------------------------------------------------------------
# WebBrowsingTool abstract base tests
# ---------------------------------------------------------------------------


class TestWebBrowsingTool:
    """Tests for the WebBrowsingTool abstract base (port)."""

    def test_is_base_tool(self) -> None:
        assert isinstance(FakeBrowsingTool(), BaseTool)

    def test_is_web_browsing_tool(self) -> None:
        assert isinstance(FakeBrowsingTool(), WebBrowsingTool)

    def test_default_name(self) -> None:
        assert FakeBrowsingTool().name == "web_browsing"

    def test_custom_name(self) -> None:
        tool = FakeBrowsingTool("my_browser")
        assert tool.name == "my_browser"

    def test_tags(self) -> None:
        tags = FakeBrowsingTool().tags
        assert "web" in tags
        assert "browser" in tags
        assert "browsing" in tags

    def test_parameters(self) -> None:
        param_names = [p.name for p in FakeBrowsingTool().parameters]
        assert "url" in param_names
        assert "extract_links" in param_names

    def test_extra_parameters(self) -> None:
        from fireflyframework_genai.tools.base import ParameterSpec

        extra = [ParameterSpec(name="instruction", type_annotation="str", description="test")]
        tool = FakeBrowsingTool(extra_parameters=extra)
        param_names = [p.name for p in tool.parameters]
        assert "url" in param_names
        assert "instruction" in param_names

    async def test_execute_returns_dict(self) -> None:
        tool = FakeBrowsingTool()
        result = await tool.execute(url="https://example.com")
        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"
        assert result["text"] == "Content of https://example.com"
        assert result["status_code"] == 200

    async def test_execute_with_links(self) -> None:
        tool = FakeBrowsingTool()
        result = await tool.execute(url="https://example.com", extract_links=True)
        assert len(result["links"]) == 1
        assert result["links"][0]["text"] == "Example"

    async def test_execute_without_links(self) -> None:
        tool = FakeBrowsingTool()
        result = await tool.execute(url="https://example.com", extract_links=False)
        assert result["links"] == []


# ---------------------------------------------------------------------------
# BrowsingResult model tests
# ---------------------------------------------------------------------------


class TestBrowsingResult:
    def test_defaults(self) -> None:
        result = BrowsingResult(url="https://example.com", text="hello")
        assert result.status_code == 200
        assert result.title == ""
        assert result.links == []
        assert result.metadata == {}

    def test_full(self) -> None:
        result = BrowsingResult(
            url="https://example.com",
            text="content",
            status_code=200,
            title="Example",
            links=[{"text": "Link", "href": "/path"}],
            metadata={"provider": "test"},
        )
        d = result.model_dump()
        assert d["url"] == "https://example.com"
        assert d["metadata"]["provider"] == "test"


# ---------------------------------------------------------------------------
# WebBrowserTool (HTTP adapter) inherits WebBrowsingTool
# ---------------------------------------------------------------------------


class TestWebBrowserToolInheritance:
    """Verify the HTTP adapter properly extends the port."""

    def test_is_web_browsing_tool(self) -> None:
        assert issubclass(WebBrowserTool, WebBrowsingTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("web_browser")
        assert tool_registry.get_class("web_browser") is WebBrowserTool

    def test_category(self) -> None:
        assert tool_registry.get_category("web_browser") == "web"


# ---------------------------------------------------------------------------
# FlyBrowserTool adapter tests
# ---------------------------------------------------------------------------


class TestFlyBrowserTool:
    """Tests for the FlyBrowser adapter."""

    def test_is_web_browsing_tool(self) -> None:
        assert issubclass(FlyBrowserTool, WebBrowsingTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("flybrowser")
        assert tool_registry.get_class("flybrowser") is FlyBrowserTool

    def test_category(self) -> None:
        assert tool_registry.get_category("flybrowser") == "web"

    def test_name(self) -> None:
        tool = FlyBrowserTool()
        assert tool.name == "flybrowser"

    def test_tags(self) -> None:
        tags = FlyBrowserTool().tags
        assert "web" in tags
        assert "browser" in tags

    def test_extra_parameters(self) -> None:
        tool = FlyBrowserTool()
        param_names = [p.name for p in tool.parameters]
        assert "url" in param_names
        assert "instruction" in param_names
        assert "action" in param_names
        assert "extract_schema" in param_names

    def test_constructor_defaults(self) -> None:
        tool = FlyBrowserTool()
        assert tool._llm_provider == "openai"
        assert tool._headless is True
        assert tool._speed_preset == "balanced"

    def test_constructor_custom(self) -> None:
        tool = FlyBrowserTool(
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-5-20250929",
            headless=False,
            speed_preset="thorough",
        )
        assert tool._llm_provider == "anthropic"
        assert tool._llm_model == "claude-sonnet-4-5-20250929"
        assert tool._headless is False
        assert tool._speed_preset == "thorough"

    def test_require_flybrowser_raises_when_unavailable(self) -> None:
        tool = FlyBrowserTool()
        with patch("firefly_dworkers.tools.web.flybrowser.FLYBROWSER_AVAILABLE", False), pytest.raises(
            ImportError, match="flybrowser required"
        ):
            tool._require_flybrowser()

    async def test_fetch_page_raises_when_unavailable(self) -> None:
        tool = FlyBrowserTool()
        with patch("firefly_dworkers.tools.web.flybrowser.FLYBROWSER_AVAILABLE", False), pytest.raises(
            ImportError, match="flybrowser required"
        ):
            await tool._fetch_page("https://example.com")

    async def test_execute_fetch_delegates_to_base(self) -> None:
        """When action='fetch' and no instruction, uses _fetch_page."""
        tool = FlyBrowserTool()
        fake_result = BrowsingResult(url="https://example.com", text="test")
        with patch.object(tool, "_fetch_page", new_callable=AsyncMock, return_value=fake_result):
            result = await tool.execute(url="https://example.com", action="fetch")
            assert result["url"] == "https://example.com"
            tool._fetch_page.assert_awaited_once()

    async def test_execute_act_uses_flybrowser(self) -> None:
        """When action='act' with instruction, delegates to FlyBrowser.act."""
        tool = FlyBrowserTool()

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.data = {"clicked": True}
        mock_response.error = None
        mock_response.execution.iterations = 3
        mock_response.execution.duration_seconds = 2.5

        mock_browser = AsyncMock()
        mock_browser.goto = AsyncMock()
        mock_browser.act = AsyncMock(return_value=mock_response)
        mock_browser.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.tools.web.flybrowser.FLYBROWSER_AVAILABLE", True), patch(
            "firefly_dworkers.tools.web.flybrowser.FlyBrowser", return_value=mock_browser
        ):
            result = await tool.execute(
                url="https://example.com",
                instruction="click the login button",
                action="act",
            )
            assert result["success"] is True
            assert result["action"] == "act"
            assert result["data"] == {"clicked": True}
            mock_browser.goto.assert_awaited_once_with("https://example.com")
            mock_browser.act.assert_awaited_once()

    async def test_execute_extract_uses_flybrowser(self) -> None:
        """When action='extract', delegates to FlyBrowser.extract."""
        tool = FlyBrowserTool()

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.data = [{"name": "Product", "price": "$19.99"}]
        mock_response.error = None
        mock_response.execution.iterations = 2
        mock_response.execution.duration_seconds = 1.0

        mock_browser = AsyncMock()
        mock_browser.goto = AsyncMock()
        mock_browser.extract = AsyncMock(return_value=mock_response)
        mock_browser.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.tools.web.flybrowser.FLYBROWSER_AVAILABLE", True), patch(
            "firefly_dworkers.tools.web.flybrowser.FlyBrowser", return_value=mock_browser
        ):
            result = await tool.execute(
                url="https://shop.example.com",
                instruction="extract product prices",
                action="extract",
            )
            assert result["success"] is True
            assert result["action"] == "extract"
            mock_browser.extract.assert_awaited_once()

    async def test_execute_agent_uses_flybrowser(self) -> None:
        """When action='agent', delegates to FlyBrowser.agent."""
        tool = FlyBrowserTool()

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.data = "Task completed"
        mock_response.error = None
        mock_response.execution.iterations = 10
        mock_response.execution.duration_seconds = 15.0

        mock_browser = AsyncMock()
        mock_browser.goto = AsyncMock()
        mock_browser.agent = AsyncMock(return_value=mock_response)
        mock_browser.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.tools.web.flybrowser.FLYBROWSER_AVAILABLE", True), patch(
            "firefly_dworkers.tools.web.flybrowser.FlyBrowser", return_value=mock_browser
        ):
            result = await tool.execute(
                url="https://example.com",
                instruction="find and compare pricing plans",
                action="agent",
            )
            assert result["success"] is True
            assert result["action"] == "agent"
            assert result["iterations"] == 10
            mock_browser.agent.assert_awaited_once()


# ---------------------------------------------------------------------------
# Toolkit integration with FlyBrowser provider
# ---------------------------------------------------------------------------


class TestToolkitBrowserProvider:
    """Test that toolkits.py correctly selects browser provider."""

    def test_default_provider_is_web_browser(self) -> None:
        from firefly_dworkers.tenants.config import TenantConfig

        config = TenantConfig(id="test", name="Test")
        assert config.connectors.web_browser.provider == "web_browser"

    def test_flybrowser_provider_config(self) -> None:
        from firefly_dworkers.tenants.config import TenantConfig

        config = TenantConfig(
            id="test",
            name="Test",
            connectors={"web_browser": {"provider": "flybrowser", "llm_provider": "anthropic"}},
        )
        assert config.connectors.web_browser.provider == "flybrowser"
        assert config.connectors.web_browser.llm_provider == "anthropic"

    def test_default_toolkit_uses_web_browser(self) -> None:
        from firefly_dworkers.tenants.config import TenantConfig
        from firefly_dworkers.tools.toolkits import _build_web_tools

        config = TenantConfig(id="test", name="Test")
        tools = _build_web_tools(config)
        browser_tools = [t for t in tools if t.name in ("web_browser", "flybrowser")]
        assert len(browser_tools) == 1
        assert isinstance(browser_tools[0], WebBrowserTool)

    def test_flybrowser_toolkit_creates_flybrowser(self) -> None:
        from firefly_dworkers.tenants.config import TenantConfig
        from firefly_dworkers.tools.toolkits import _build_web_tools

        config = TenantConfig(
            id="test",
            name="Test",
            connectors={"web_browser": {"provider": "flybrowser"}},
        )
        tools = _build_web_tools(config)
        browser_tools = [t for t in tools if t.name in ("web_browser", "flybrowser")]
        assert len(browser_tools) == 1
        assert isinstance(browser_tools[0], FlyBrowserTool)
