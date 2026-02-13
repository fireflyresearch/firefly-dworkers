"""Word document adapter for DocumentTool."""

from __future__ import annotations

import asyncio
import io
from collections.abc import Sequence

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.models import (
    DocumentData,
    DocumentOperation,
    ParagraphData,
    SectionSpec,
)
from firefly_dworkers.tools.registry import tool_registry

try:
    import docx

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def _require_docx() -> None:
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx required: pip install firefly-dworkers[document]")


@tool_registry.register("word", category="document")
class WordTool(DocumentTool):
    """Read, create, and modify Word (.docx) documents using python-docx."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "word",
            description="Read, create, and modify Word (.docx) documents.",
            timeout=timeout,
            guards=guards,
        )

    async def _read_document(self, source: str) -> DocumentData:
        _require_docx()
        return await asyncio.to_thread(self._read_sync, source)

    async def _create_document(self, title: str, sections: list[SectionSpec]) -> bytes:
        _require_docx()
        return await asyncio.to_thread(self._create_sync, title, sections)

    async def _modify_document(self, source: str, operations: list[DocumentOperation]) -> bytes:
        _require_docx()
        return await asyncio.to_thread(self._modify_sync, source, operations)

    # -- Sync implementations --

    def _read_sync(self, source: str) -> DocumentData:
        doc = docx.Document(source)
        paragraphs = []
        styles: set[str] = set()

        for para in doc.paragraphs:
            is_heading = para.style.name.startswith("Heading")
            heading_level = 0
            if is_heading:
                try:
                    heading_level = int(para.style.name.split()[-1])
                except (ValueError, IndexError):
                    heading_level = 1
            paragraphs.append(
                ParagraphData(
                    text=para.text,
                    style=para.style.name,
                    is_heading=is_heading,
                    heading_level=heading_level,
                )
            )
            styles.add(para.style.name)

        title = ""
        for p in paragraphs:
            if p.text.strip():
                title = p.text.strip()
                break

        return DocumentData(
            title=title,
            paragraphs=paragraphs,
            styles=sorted(styles),
        )

    def _create_sync(self, title: str, sections: list[SectionSpec]) -> bytes:
        doc = docx.Document()

        if title:
            doc.add_heading(title, level=0)

        for section in sections:
            if section.page_break_before:
                doc.add_page_break()

            if section.heading:
                doc.add_heading(section.heading, level=section.heading_level)

            if section.content:
                doc.add_paragraph(section.content)

            for point in section.bullet_points:
                doc.add_paragraph(point, style="List Bullet")

            if section.table:
                headers = section.table.headers
                rows = section.table.rows
                if headers:
                    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
                    tbl.style = "Table Grid"
                    for i, header in enumerate(headers):
                        tbl.cell(0, i).text = header
                    for r, row in enumerate(rows):
                        for c, val in enumerate(row):
                            if c < len(headers):
                                tbl.cell(r + 1, c).text = str(val)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _modify_sync(self, source: str, operations: list[DocumentOperation]) -> bytes:
        doc = docx.Document(source)

        for op in operations:
            if op.operation == "add_section":
                heading = op.data.get("heading", "")
                content = op.data.get("content", "")
                level = op.data.get("heading_level", 1)
                if heading:
                    doc.add_heading(heading, level=level)
                if content:
                    doc.add_paragraph(content)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
