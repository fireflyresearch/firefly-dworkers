"""Tests for PresentationTool abstract base."""

from __future__ import annotations

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.models import (
    ChartSpec,
    PresentationData,
    SlideData,
    SlideSpec,
    TableSpec,
)


class FakePresentationTool(PresentationTool):
    """Concrete implementation for testing the abstract base."""

    async def _read_presentation(self, source):
        return PresentationData(
            slides=[SlideData(index=0, layout="Title Slide", title="Test")],
            master_layouts=["Title Slide"],
        )

    async def _create_presentation(self, template, slides):
        return b"fake-pptx-bytes"

    async def _modify_presentation(self, source, operations):
        return b"modified-pptx-bytes"


class TestPresentationTool:
    def test_is_base_tool(self) -> None:
        assert isinstance(FakePresentationTool(), BaseTool)

    def test_is_presentation_tool(self) -> None:
        assert isinstance(FakePresentationTool(), PresentationTool)

    def test_default_name(self) -> None:
        assert FakePresentationTool().name == "presentation"

    def test_tags(self) -> None:
        tags = FakePresentationTool().tags
        assert "presentation" in tags
        assert "document" in tags

    def test_parameters(self) -> None:
        param_names = [p.name for p in FakePresentationTool().parameters]
        assert "action" in param_names
        assert "source" in param_names

    async def test_execute_read(self) -> None:
        tool = FakePresentationTool()
        result = await tool.execute(action="read", source="test.pptx")
        assert isinstance(result, dict)
        assert "slides" in result

    async def test_execute_create(self) -> None:
        tool = FakePresentationTool()
        slides = [SlideSpec(title="Title", content="Body")]
        result = await tool.execute(action="create", slides=[s.model_dump() for s in slides])
        assert "bytes_length" in result

    async def test_execute_unknown_action_raises(self) -> None:
        tool = FakePresentationTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="unknown", source="test.pptx")


class TestPresentationModels:
    def test_slide_spec_defaults(self) -> None:
        spec = SlideSpec(title="Test")
        assert spec.layout == "Title and Content"
        assert spec.bullet_points == []

    def test_chart_spec(self) -> None:
        chart = ChartSpec(
            chart_type="bar",
            title="Revenue",
            categories=["Q1", "Q2"],
            series=[{"name": "2025", "values": [100, 200]}],
        )
        assert chart.chart_type == "bar"

    def test_table_spec(self) -> None:
        table = TableSpec(
            headers=["Name", "Value"],
            rows=[["A", "1"], ["B", "2"]],
        )
        assert len(table.rows) == 2

    def test_presentation_data(self) -> None:
        data = PresentationData(
            slides=[SlideData(index=0, layout="Blank", title="")],
            master_layouts=["Blank"],
        )
        assert len(data.slides) == 1
