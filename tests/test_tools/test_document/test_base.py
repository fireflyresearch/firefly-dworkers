"""Tests for DocumentTool abstract base."""

from __future__ import annotations

import os

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.models import (
    DocumentData,
    DocumentOperation,
    ParagraphData,
    SectionSpec,
    TableData,
)


class FakeDocumentTool(DocumentTool):
    """Concrete implementation for testing the abstract base."""

    async def _read_document(self, source):
        return DocumentData(
            title="Test Title",
            paragraphs=[ParagraphData(text="Hello", style="Normal")],
            styles=["Normal"],
        )

    async def _create_document(self, title, sections):
        return b"fake-docx-bytes"

    async def _modify_document(self, source, operations):
        return b"modified-docx-bytes"


class TestDocumentTool:
    def test_is_base_tool(self) -> None:
        assert isinstance(FakeDocumentTool(), BaseTool)

    def test_is_document_tool(self) -> None:
        assert isinstance(FakeDocumentTool(), DocumentTool)

    def test_default_name(self) -> None:
        assert FakeDocumentTool().name == "document"

    def test_tags(self) -> None:
        tags = FakeDocumentTool().tags
        assert "document" in tags

    def test_parameters(self) -> None:
        param_names = [p.name for p in FakeDocumentTool().parameters]
        assert "action" in param_names
        assert "source" in param_names
        assert "title" in param_names
        assert "sections" in param_names
        assert "operations" in param_names

    async def test_execute_read(self) -> None:
        tool = FakeDocumentTool()
        result = await tool.execute(action="read", source="test.docx")
        assert isinstance(result, dict)
        assert "paragraphs" in result
        assert result["title"] == "Test Title"

    async def test_execute_create(self) -> None:
        tool = FakeDocumentTool()
        sections = [SectionSpec(heading="Intro", content="Body text")]
        result = await tool.execute(
            action="create",
            title="My Doc",
            sections=[s.model_dump() for s in sections],
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_execute_modify(self) -> None:
        tool = FakeDocumentTool()
        ops = [DocumentOperation(operation="add_section", data={"heading": "New"})]
        result = await tool.execute(
            action="modify",
            source="test.docx",
            operations=[o.model_dump() for o in ops],
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_execute_unknown_action_raises(self) -> None:
        tool = FakeDocumentTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="unknown", source="test.docx")

    async def test_artifact_bytes_none_initially(self) -> None:
        assert FakeDocumentTool().artifact_bytes is None

    async def test_artifact_bytes_after_create(self) -> None:
        tool = FakeDocumentTool()
        await tool.execute(action="create", sections=[SectionSpec(heading="Test").model_dump()])
        assert tool.artifact_bytes == b"fake-docx-bytes"

    async def test_artifact_bytes_none_after_read(self) -> None:
        tool = FakeDocumentTool()
        await tool.execute(action="create", sections=[SectionSpec(heading="Test").model_dump()])
        await tool.execute(action="read", source="test.docx")
        assert tool.artifact_bytes is None

    async def test_create_returns_bytes(self) -> None:
        tool = FakeDocumentTool()
        result = await tool.create(sections=[SectionSpec(heading="Test")])
        assert result == b"fake-docx-bytes"

    async def test_create_and_save(self, tmp_path) -> None:
        tool = FakeDocumentTool()
        out = str(tmp_path / "test.docx")
        path = await tool.create_and_save(out, sections=[SectionSpec(heading="Test")])
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b"fake-docx-bytes"

    async def test_modify_returns_bytes(self) -> None:
        tool = FakeDocumentTool()
        result = await tool.modify("src.docx")
        assert result == b"modified-docx-bytes"

    async def test_modify_and_save(self, tmp_path) -> None:
        tool = FakeDocumentTool()
        out = str(tmp_path / "modified.docx")
        path = await tool.modify_and_save("src.docx", out)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b"modified-docx-bytes"


class TestDocumentModels:
    def test_section_spec_defaults(self) -> None:
        spec = SectionSpec(heading="Test")
        assert spec.heading_level == 1
        assert spec.content == ""
        assert spec.bullet_points == []
        assert spec.table is None
        assert spec.page_break_before is False

    def test_section_spec_with_table(self) -> None:
        table = TableData(headers=["Name", "Value"], rows=[["A", "1"]])
        spec = SectionSpec(heading="Data", table=table)
        assert spec.table is not None
        assert spec.table.headers == ["Name", "Value"]
        assert len(spec.table.rows) == 1

    def test_table_data_defaults(self) -> None:
        table = TableData()
        assert table.headers == []
        assert table.rows == []

    def test_paragraph_data(self) -> None:
        para = ParagraphData(text="Hello", style="Heading 1", is_heading=True, heading_level=1)
        assert para.text == "Hello"
        assert para.is_heading is True
        assert para.heading_level == 1

    def test_document_data_defaults(self) -> None:
        data = DocumentData()
        assert data.title == ""
        assert data.paragraphs == []
        assert data.metadata == {}
        assert data.styles == []

    def test_document_operation(self) -> None:
        op = DocumentOperation(operation="add_section", section_index=2, data={"heading": "New"})
        assert op.operation == "add_section"
        assert op.section_index == 2
        assert op.data["heading"] == "New"
