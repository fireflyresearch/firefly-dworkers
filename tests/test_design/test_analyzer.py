"""Tests for TemplateAnalyzer — design DNA extraction from documents."""

from __future__ import annotations

import io
import os
import tempfile

import pytest

from firefly_dworkers.design.analyzer import TemplateAnalyzer
from firefly_dworkers.design.models import DesignProfile


# ── Format detection ────────────────────────────────────────────────────────


class TestTemplateAnalyzerDetectFormat:
    def test_pptx(self) -> None:
        assert TemplateAnalyzer()._detect_format("deck.pptx") == "pptx"

    def test_docx(self) -> None:
        assert TemplateAnalyzer()._detect_format("report.docx") == "docx"

    def test_xlsx(self) -> None:
        assert TemplateAnalyzer()._detect_format("data.xlsx") == "xlsx"

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            TemplateAnalyzer()._detect_format("file.txt")

    def test_case_insensitive(self) -> None:
        assert TemplateAnalyzer()._detect_format("DECK.PPTX") == "pptx"

    def test_path_with_directories(self) -> None:
        assert TemplateAnalyzer()._detect_format("/tmp/reports/q1/deck.pptx") == "pptx"

    def test_no_extension_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            TemplateAnalyzer()._detect_format("noextension")

    def test_pdf_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            TemplateAnalyzer()._detect_format("report.pdf")


# ── PPTX analysis ──────────────────────────────────────────────────────────


class TestTemplateAnalyzerPptx:
    async def test_analyze_pptx_returns_profile(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)

            assert isinstance(profile, DesignProfile)
            assert len(profile.available_layouts) > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_pptx_extracts_layouts(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_pptx(tmp_path)

            # Default presentation has standard layouts
            assert "Title Slide" in profile.available_layouts or len(profile.available_layouts) > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_pptx_extracts_dimensions(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_pptx(tmp_path)

            # Default PPTX has slide dimensions
            assert "slide_width_emu" in profile.margins
            assert "slide_height_emu" in profile.margins
            assert profile.margins["slide_width_emu"] > 0
            assert profile.margins["slide_height_emu"] > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_pptx_extracts_fonts(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_pptx(tmp_path)

            # Default theme should have fonts defined
            assert isinstance(profile.heading_font, str)
            assert isinstance(profile.body_font, str)
        finally:
            os.unlink(tmp_path)

    async def test_analyze_pptx_extracts_colors(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_pptx(tmp_path)

            # Default theme has color palette
            assert isinstance(profile.color_palette, list)
        finally:
            os.unlink(tmp_path)


# ── DOCX analysis ──────────────────────────────────────────────────────────


class TestTemplateAnalyzerDocx:
    async def test_analyze_docx_returns_profile(self) -> None:
        docx_mod = pytest.importorskip("docx")

        doc = docx_mod.Document()
        doc.add_heading("Test Title", level=1)
        doc.add_paragraph("Body content here.")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)

            assert isinstance(profile, DesignProfile)
            assert len(profile.styles) > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_docx_extracts_styles(self) -> None:
        docx_mod = pytest.importorskip("docx")

        doc = docx_mod.Document()
        doc.add_heading("Heading 1", level=1)
        doc.add_heading("Heading 2", level=2)
        doc.add_paragraph("Normal text.")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_docx(tmp_path)

            assert "Normal" in profile.styles
            assert "Heading 1" in profile.styles
        finally:
            os.unlink(tmp_path)

    async def test_analyze_docx_extracts_margins(self) -> None:
        docx_mod = pytest.importorskip("docx")

        doc = docx_mod.Document()
        doc.add_paragraph("Content")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_docx(tmp_path)

            # Default document should have margin values
            assert len(profile.margins) > 0
            for key in ("left", "right", "top", "bottom"):
                assert key in profile.margins
                assert profile.margins[key] > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_docx_fonts_are_strings(self) -> None:
        docx_mod = pytest.importorskip("docx")

        doc = docx_mod.Document()
        doc.add_paragraph("Content")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_docx(tmp_path)

            # Font fields should always be strings, even if empty
            assert isinstance(profile.heading_font, str)
            assert isinstance(profile.body_font, str)
        finally:
            os.unlink(tmp_path)


# ── XLSX analysis ──────────────────────────────────────────────────────────


class TestTemplateAnalyzerXlsx:
    async def test_analyze_xlsx_returns_profile(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")

        wb = openpyxl_mod.Workbook()
        ws = wb.active
        ws.title = "Summary"
        ws["A1"] = "Hello"
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)

            assert isinstance(profile, DesignProfile)
        finally:
            os.unlink(tmp_path)

    async def test_analyze_xlsx_extracts_sheet_names(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")

        wb = openpyxl_mod.Workbook()
        ws = wb.active
        ws.title = "Revenue"
        wb.create_sheet("Costs")
        wb.create_sheet("Summary")
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_xlsx(tmp_path)

            assert "Revenue" in profile.available_layouts
            assert "Costs" in profile.available_layouts
            assert "Summary" in profile.available_layouts
        finally:
            os.unlink(tmp_path)

    async def test_analyze_xlsx_extracts_font(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")

        wb = openpyxl_mod.Workbook()
        ws = wb.active
        ws["A1"] = "Data"
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer._analyze_xlsx(tmp_path)

            # Font fields should be strings
            assert isinstance(profile.body_font, str)
        finally:
            os.unlink(tmp_path)


# ── Integration: analyze dispatches correctly ──────────────────────────────


class TestTemplateAnalyzerDispatch:
    async def test_analyze_dispatches_to_pptx(self) -> None:
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            profile = await TemplateAnalyzer().analyze(tmp_path)
            assert isinstance(profile, DesignProfile)
            # PPTX-specific: should have layouts
            assert len(profile.available_layouts) > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_dispatches_to_docx(self) -> None:
        docx_mod = pytest.importorskip("docx")

        doc = docx_mod.Document()
        doc.add_paragraph("Content")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            profile = await TemplateAnalyzer().analyze(tmp_path)
            assert isinstance(profile, DesignProfile)
            # DOCX-specific: should have styles
            assert len(profile.styles) > 0
        finally:
            os.unlink(tmp_path)

    async def test_analyze_dispatches_to_xlsx(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")

        wb = openpyxl_mod.Workbook()
        ws = wb.active
        ws.title = "Data"
        ws["A1"] = "test"
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            profile = await TemplateAnalyzer().analyze(tmp_path)
            assert isinstance(profile, DesignProfile)
            assert "Data" in profile.available_layouts
        finally:
            os.unlink(tmp_path)
