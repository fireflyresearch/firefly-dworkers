"""Tests for WordTool adapter."""

from __future__ import annotations

import io
import os
import tempfile

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.models import SectionSpec
from firefly_dworkers.tools.document.word import WordTool
from firefly_dworkers.tools.registry import tool_registry


class TestWordToolRegistration:
    def test_is_document_tool(self) -> None:
        assert issubclass(WordTool, DocumentTool)

    def test_is_base_tool(self) -> None:
        assert issubclass(WordTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("word")
        assert tool_registry.get_class("word") is WordTool

    def test_category(self) -> None:
        assert tool_registry.get_category("word") == "document"

    def test_name(self) -> None:
        assert WordTool().name == "word"


class TestWordToolRead:
    async def test_read_document(self) -> None:
        docx = pytest.importorskip("docx")

        # Create a minimal .docx in memory
        doc = docx.Document()
        doc.add_heading("Test Title", level=0)
        doc.add_paragraph("Hello world")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = WordTool()
            result = await tool.execute(action="read", source=tmp_path)
            assert "paragraphs" in result
            assert len(result["paragraphs"]) >= 2
            # First paragraph should be the title heading
            assert result["title"] == "Test Title"
        finally:
            os.unlink(tmp_path)

    async def test_read_detects_headings(self) -> None:
        docx = pytest.importorskip("docx")

        doc = docx.Document()
        doc.add_heading("Chapter 1", level=1)
        doc.add_paragraph("Some content")
        doc.add_heading("Section 1.1", level=2)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = WordTool()
            result = await tool.execute(action="read", source=tmp_path)
            headings = [p for p in result["paragraphs"] if p["is_heading"]]
            assert len(headings) == 2
            assert headings[0]["heading_level"] == 1
            assert headings[1]["heading_level"] == 2
        finally:
            os.unlink(tmp_path)


class TestWordToolCreate:
    async def test_create_document_basic(self) -> None:
        pytest.importorskip("docx")
        tool = WordTool()
        sections = [
            SectionSpec(heading="Introduction", content="Hello world").model_dump(),
            SectionSpec(heading="Details", bullet_points=["A", "B", "C"]).model_dump(),
        ]
        result = await tool.execute(action="create", title="My Document", sections=sections)
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_create_with_table(self) -> None:
        pytest.importorskip("docx")
        tool = WordTool()
        sections = [
            SectionSpec(
                heading="Data Table",
                table={"headers": ["Name", "Value"], "rows": [["A", "1"]]},
            ).model_dump(),
        ]
        result = await tool.execute(action="create", title="Table Doc", sections=sections)
        assert result["success"] is True

    async def test_create_with_page_break(self) -> None:
        pytest.importorskip("docx")
        tool = WordTool()
        sections = [
            SectionSpec(heading="Page 1", content="First page content").model_dump(),
            SectionSpec(heading="Page 2", content="Second page", page_break_before=True).model_dump(),
        ]
        result = await tool.execute(action="create", title="Multi-page", sections=sections)
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_create_roundtrip(self) -> None:
        """Create a document and then read it back to verify content."""
        pytest.importorskip("docx")

        tool = WordTool()
        # Create via the tool's sync method directly to get bytes
        sections = [SectionSpec(heading="Chapter 1", heading_level=1, content="Body text")]
        data = await tool._create_document("Round Trip", sections)

        # Write to temp file and read back
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            result = await tool.execute(action="read", source=tmp_path)
            assert result["title"] == "Round Trip"
            heading_texts = [p["text"] for p in result["paragraphs"] if p["is_heading"]]
            assert "Chapter 1" in heading_texts
        finally:
            os.unlink(tmp_path)


class TestWordToolModify:
    async def test_modify_add_section(self) -> None:
        docx = pytest.importorskip("docx")

        # Create a minimal doc
        doc = docx.Document()
        doc.add_heading("Original", level=1)
        doc.add_paragraph("Original content")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = WordTool()
            result = await tool.execute(
                action="modify",
                source=tmp_path,
                operations=[
                    {
                        "operation": "add_section",
                        "data": {"heading": "New Section", "content": "Added content", "heading_level": 2},
                    }
                ],
            )
            assert result["success"] is True
            assert result["bytes_length"] > 0
        finally:
            os.unlink(tmp_path)
