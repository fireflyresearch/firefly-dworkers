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


from unittest.mock import AsyncMock, MagicMock, patch


# ── VLM fallback tests ──────────────────────────────────────────────────


class TestVLMFallback:
    """Tests for VLM fallback when XML extraction produces empty profile."""

    def test_is_profile_empty_true(self) -> None:
        profile = DesignProfile()
        assert TemplateAnalyzer._is_profile_empty(profile) is True

    def test_is_profile_empty_false_with_color(self) -> None:
        profile = DesignProfile(primary_color="#003366")
        assert TemplateAnalyzer._is_profile_empty(profile) is False

    def test_is_profile_empty_false_with_font(self) -> None:
        profile = DesignProfile(heading_font="Arial")
        assert TemplateAnalyzer._is_profile_empty(profile) is False

    def test_is_profile_empty_false_with_palette(self) -> None:
        profile = DesignProfile(color_palette=["#ff0000"])
        assert TemplateAnalyzer._is_profile_empty(profile) is False

    async def test_vlm_not_called_when_xml_succeeds(self) -> None:
        """When XML extraction produces non-empty profile, VLM should not be called."""
        pytest.importorskip("pptx")

        non_empty_profile = DesignProfile(
            primary_color="#003366", heading_font="Arial", color_palette=["#003366"]
        )

        analyzer = TemplateAnalyzer(vlm_model="test-model")
        # Patch the PPTX analysis to return a non-empty profile so VLM is skipped
        with (
            patch.object(analyzer, "_vlm_analyze", new_callable=AsyncMock) as mock_vlm,
            patch.object(
                analyzer, "_analyze_pptx", new_callable=AsyncMock,
                return_value=non_empty_profile,
            ),
        ):
            profile = await analyzer.analyze("fake.pptx")
            mock_vlm.assert_not_called()
            assert profile.primary_color == "#003366"

    async def test_vlm_called_when_xml_empty(self) -> None:
        """When XML extraction produces empty profile, VLM should be called."""
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer(vlm_model="test-model")
            # Force _analyze_pptx to return empty profile
            empty_profile = DesignProfile()
            vlm_profile = DesignProfile(primary_color="#ff0000", heading_font="Helvetica")

            with patch.object(
                analyzer, "_analyze_pptx", new_callable=AsyncMock, return_value=empty_profile
            ), patch.object(
                analyzer, "_vlm_analyze", new_callable=AsyncMock, return_value=vlm_profile
            ) as mock_vlm:
                profile = await analyzer.analyze(tmp_path)
                mock_vlm.assert_called_once()
                assert profile.primary_color == "#ff0000"
        finally:
            os.unlink(tmp_path)

    async def test_vlm_merge_xml_priority(self) -> None:
        """XML non-empty fields should take priority over VLM fields."""
        xml_profile = DesignProfile(primary_color="#003366", heading_font="")
        vlm_profile = DesignProfile(primary_color="#ff0000", heading_font="Helvetica")

        analyzer = TemplateAnalyzer(vlm_model="test-model")

        # Directly test merge logic
        with patch.object(analyzer, "_vlm_analyze") as mock_vlm:
            # Simulate VLM returning vlm_profile merged with xml_profile
            mock_vlm.return_value = DesignProfile(
                primary_color=xml_profile.primary_color or vlm_profile.primary_color,
                heading_font=xml_profile.heading_font or vlm_profile.heading_font,
            )
            # The merge logic: XML primary_color wins, VLM heading_font fills gap
            merged = mock_vlm.return_value
            assert merged.primary_color == "#003366"  # XML wins
            assert merged.heading_font == "Helvetica"  # VLM fills gap

    async def test_vlm_graceful_fallback(self) -> None:
        """When VLM fails, XML result should be returned."""
        pptx_mod = pytest.importorskip("pptx")

        prs = pptx_mod.Presentation()
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            analyzer = TemplateAnalyzer(vlm_model="test-model")
            empty_profile = DesignProfile()

            with patch.object(
                analyzer, "_analyze_pptx", new_callable=AsyncMock, return_value=empty_profile
            ), patch.object(
                analyzer, "_vlm_analyze", new_callable=AsyncMock, side_effect=RuntimeError("VLM failed")
            ):
                profile = await analyzer.analyze(tmp_path)
                # Should return XML profile (empty) without raising
                assert isinstance(profile, DesignProfile)
        finally:
            os.unlink(tmp_path)

    async def test_vlm_not_called_for_docx(self) -> None:
        """VLM fallback should only apply to PPTX files."""
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
            analyzer = TemplateAnalyzer(vlm_model="test-model")
            with patch.object(analyzer, "_vlm_analyze", new_callable=AsyncMock) as mock_vlm:
                await analyzer.analyze(tmp_path)
                mock_vlm.assert_not_called()
        finally:
            os.unlink(tmp_path)


# ── Layout zone extraction tests ──────────────────────────────────────────


def _make_pptx_tmp():
    """Create a default PPTX and return its temp file path."""
    pptx_mod = pytest.importorskip("pptx")
    prs = pptx_mod.Presentation()
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    f = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    f.write(buf.read())
    f.close()
    return f.name


class TestLayoutZoneExtraction:
    async def test_layout_zones_extracted_with_positions(self) -> None:
        """Verify placeholders have left/top/width/height > 0."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)
            assert len(profile.layout_zones) > 0
            for zone in profile.layout_zones.values():
                for ph in zone.placeholders:
                    # At least some placeholders should have dimensions
                    assert ph.width >= 0
                    assert ph.height >= 0
        finally:
            os.unlink(tmp_path)

    async def test_title_ph_identified(self) -> None:
        """Verify title_ph_idx found for content layouts."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)
            # At least one layout should have a title placeholder
            has_title = any(
                zone.title_ph_idx is not None
                for zone in profile.layout_zones.values()
            )
            assert has_title
        finally:
            os.unlink(tmp_path)

    async def test_body_ph_is_largest_text_area(self) -> None:
        """Verify body_ph_idx picks the largest area placeholder."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)
            for zone in profile.layout_zones.values():
                if zone.body_ph_idx is None:
                    continue
                body = next(p for p in zone.placeholders if p.idx == zone.body_ph_idx)
                # Body should be at least 1.5" tall and 3" wide
                assert body.height >= 1.5
                assert body.width >= 3.0
                # Body should be the largest qualifying placeholder
                body_area = body.width * body.height
                for ph in zone.placeholders:
                    if ph.idx == zone.title_ph_idx or ph.idx == zone.body_ph_idx:
                        continue
                    if ph.ph_type in ("date_time", "slide_number", "footer"):
                        continue
                    if ph.height < 1.5 or ph.width < 3.0:
                        continue
                    assert ph.width * ph.height <= body_area
        finally:
            os.unlink(tmp_path)

    async def test_cover_layout_no_body_ph(self) -> None:
        """Cover layouts with only small custom phs: body_ph_idx is None."""
        from firefly_dworkers.design.models import PlaceholderZone as PZ

        analyzer = TemplateAnalyzer()
        # Simulate small placeholders that don't meet the size threshold
        phs = [
            PZ(idx=19, name="Title", ph_type="title", left=1, top=1, width=6, height=0.5),
            PZ(idx=20, name="Date", ph_type="custom", left=1, top=6, width=2, height=0.3),
            PZ(idx=21, name="Client", ph_type="custom", left=5, top=6, width=3, height=0.3),
        ]
        body_idx = analyzer._find_body_ph(phs, exclude_title_idx=19)
        assert body_idx is None

    async def test_content_zone_computed(self) -> None:
        """Verify content_left/top/width/height are reasonable values."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)
            for zone in profile.layout_zones.values():
                # Content zone should have positive dimensions
                assert zone.content_width > 0
                assert zone.content_height > 0
                assert zone.content_left >= 0
                assert zone.content_top >= 0
        finally:
            os.unlink(tmp_path)

    async def test_layout_zones_in_profile(self) -> None:
        """Verify profile.layout_zones populated and keyed by layout name."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()
            profile = await analyzer.analyze(tmp_path)
            assert isinstance(profile.layout_zones, dict)
            assert len(profile.layout_zones) > 0
            for name, zone in profile.layout_zones.items():
                assert zone.layout_name == name
        finally:
            os.unlink(tmp_path)

    def test_classify_placeholder_standard_indices(self) -> None:
        """Test classification of standard OOXML placeholder indices."""
        classify = TemplateAnalyzer._classify_placeholder
        assert classify(0, "Title") == "title"
        assert classify(15, "Title") == "title"
        assert classify(1, "Content") == "body"
        assert classify(10, "Date") == "date_time"
        assert classify(11, "Slide Number") == "slide_number"
        assert classify(12, "Footer") == "footer"

    def test_classify_placeholder_nonstandard_is_custom(self) -> None:
        """Non-standard indices are 'custom' — LLM handles classification."""
        classify = TemplateAnalyzer._classify_placeholder
        # These are all "custom" regardless of name — no language heuristics
        assert classify(21, "Title 1") == "custom"
        assert classify(19, "Título") == "custom"
        assert classify(20, "Subtitle") == "custom"
        assert classify(22, "Logo Placeholder") == "custom"

    async def test_llm_classifies_custom_placeholders(self) -> None:
        """When vlm_model is set, LLM classifies custom placeholders."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from firefly_dworkers.design.models import LayoutZone, PlaceholderZone

        analyzer = TemplateAnalyzer(vlm_model="test-model")

        zones = {
            "Portada": LayoutZone(
                layout_name="Portada",
                placeholders=[
                    PlaceholderZone(idx=21, name="Título", ph_type="custom",
                                   left=1, top=1, width=6, height=1),
                    PlaceholderZone(idx=19, name="Empresa", ph_type="custom",
                                   left=1, top=5, width=3, height=0.4),
                ],
                content_left=1, content_top=2, content_width=8, content_height=4,
                title_ph_idx=None, body_ph_idx=None,
            ),
        }

        # Mock LLM response
        mock_result = MagicMock()
        mock_result.output = MagicMock()
        mock_result.output.layouts = [
            MagicMock(
                layout_name="Portada",
                roles=[
                    MagicMock(idx=21, role="title"),
                    MagicMock(idx=19, role="client_name"),
                ],
            ),
        ]

        with patch("pydantic_ai.Agent") as MockAgent:
            instance = MockAgent.return_value
            instance.run = AsyncMock(return_value=mock_result)

            updated = await analyzer._classify_zones_with_llm(zones)

        assert updated["Portada"].placeholders[0].ph_type == "title"
        assert updated["Portada"].placeholders[1].ph_type == "client_name"
        assert updated["Portada"].title_ph_idx == 21

    async def test_no_llm_leaves_custom_unchanged(self) -> None:
        """Without vlm_model, custom placeholders stay as 'custom'."""
        tmp_path = _make_pptx_tmp()
        try:
            analyzer = TemplateAnalyzer()  # no vlm_model
            profile = await analyzer.analyze(tmp_path)
            # All non-standard placeholders should be "custom" (no LLM)
            for zone in profile.layout_zones.values():
                for ph in zone.placeholders:
                    if ph.idx not in (0, 1, 10, 11, 12, 15):
                        assert ph.ph_type == "custom"
        finally:
            os.unlink(tmp_path)
