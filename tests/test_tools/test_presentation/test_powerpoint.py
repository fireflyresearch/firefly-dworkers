"""Tests for PowerPointTool adapter."""

from __future__ import annotations

import io
import os
import tempfile

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.models import SlideSpec
from firefly_dworkers.tools.presentation.powerpoint import PowerPointTool
from firefly_dworkers.tools.registry import tool_registry


class TestPowerPointToolRegistration:
    def test_is_presentation_tool(self) -> None:
        assert issubclass(PowerPointTool, PresentationTool)

    def test_is_base_tool(self) -> None:
        assert issubclass(PowerPointTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("powerpoint")
        assert tool_registry.get_class("powerpoint") is PowerPointTool

    def test_category(self) -> None:
        assert tool_registry.get_category("powerpoint") == "presentation"

    def test_name(self) -> None:
        assert PowerPointTool().name == "powerpoint"


class TestPowerPointToolRead:
    async def test_read_presentation(self) -> None:
        pptx = pytest.importorskip("pptx")

        # Create a minimal .pptx in memory
        prs = pptx.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "Test Title"
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = PowerPointTool()
            result = await tool.execute(action="read", source=tmp_path)
            assert "slides" in result
            assert len(result["slides"]) == 1
            assert result["slides"][0]["title"] == "Test Title"
        finally:
            os.unlink(tmp_path)


class TestPowerPointToolCreate:
    async def test_create_presentation_basic(self) -> None:
        pytest.importorskip("pptx")
        tool = PowerPointTool()
        slides = [
            SlideSpec(title="Slide 1", content="Hello world").model_dump(),
            SlideSpec(title="Slide 2", bullet_points=["A", "B", "C"]).model_dump(),
        ]
        result = await tool.execute(action="create", slides=slides)
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_create_with_table(self) -> None:
        pytest.importorskip("pptx")
        tool = PowerPointTool()
        slides = [
            SlideSpec(
                title="Data Table",
                table={"headers": ["Name", "Value"], "rows": [["A", "1"]]},
            ).model_dump(),
        ]
        result = await tool.execute(action="create", slides=slides)
        assert result["success"] is True


class TestPowerPointToolPublicAPI:
    async def test_create_returns_bytes(self) -> None:
        pytest.importorskip("pptx")
        tool = PowerPointTool()
        result = await tool.create(slides=[SlideSpec(title="Slide 1", content="Hello")])
        assert isinstance(result, bytes)
        assert len(result) > 0

    async def test_create_and_save(self, tmp_path) -> None:
        pytest.importorskip("pptx")
        tool = PowerPointTool()
        out = str(tmp_path / "test.pptx")
        path = await tool.create_and_save(out, slides=[SlideSpec(title="Test")])
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    async def test_artifact_bytes_after_execute(self) -> None:
        pytest.importorskip("pptx")
        tool = PowerPointTool()
        await tool.execute(action="create", slides=[SlideSpec(title="T").model_dump()])
        assert tool.artifact_bytes is not None
        assert len(tool.artifact_bytes) > 0
