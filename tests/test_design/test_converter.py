"""Tests for DesignSpec -> tool-specific spec converters."""

from __future__ import annotations

import os

from firefly_dworkers.design.converter import (
    _build_content_zone,
    convert_design_spec_to_section_specs,
    convert_design_spec_to_sheet_specs,
    convert_design_spec_to_slide_specs,
    convert_resolved_chart_to_chart_spec,
    convert_section_design_to_section_spec,
    convert_sheet_design_to_sheet_spec,
    convert_slide_design_to_slide_spec,
    convert_styled_table_to_table_data,
    convert_styled_table_to_table_spec,
)
from firefly_dworkers.design.models import (
    ContentBlock,
    DataSeries,
    DesignProfile,
    DesignSpec,
    ImagePlacement,
    KeyMetric,
    LayoutZone,
    OutputType,
    PlaceholderZone,
    ResolvedChart,
    ResolvedImage,
    SectionDesign,
    SheetDesign,
    SlideDesign,
    StyledTable,
    TextStyle,
)
from firefly_dworkers.tools.presentation.models import ContentZone


def _make_profile(**kw):
    defaults = {"primary_color": "#003366", "heading_font": "Arial"}
    defaults.update(kw)
    return DesignProfile(**defaults)


class TestChartConversion:
    def test_series_converted_to_dict_format(self):
        chart = ResolvedChart(
            chart_type="bar",
            title="Revenue",
            categories=["Q1", "Q2"],
            series=[DataSeries(name="2025", values=[100, 200])],
            colors=["#ff0000"],
            show_legend=True,
            show_data_labels=False,
            stacked=True,
        )
        result = convert_resolved_chart_to_chart_spec(chart)
        assert result.chart_type == "bar"
        assert result.title == "Revenue"
        assert result.categories == ["Q1", "Q2"]
        assert result.series == [{"name": "2025", "values": [100, 200]}]
        assert result.colors == ["#ff0000"]
        assert result.show_legend is True
        assert result.show_data_labels is False
        assert result.stacked is True


class TestTableConversion:
    def test_table_conversion_with_profile(self):
        table = StyledTable(
            headers=["Name", "Value"],
            rows=[["A", "1"], ["B", "2"]],
            header_style=TextStyle(font_name="Calibri", color="#FFFFFF", font_size=12.0),
            alternating_rows=True,
            border_color="#999999",
        )
        profile = _make_profile(primary_color="#1a3c6d")
        result = convert_styled_table_to_table_spec(table, profile)
        assert result.headers == ["Name", "Value"]
        assert result.rows == [["A", "1"], ["B", "2"]]
        assert result.header_bg_color == "#1a3c6d"
        assert result.header_text_color == "#FFFFFF"
        assert result.font_name == "Calibri"
        assert result.alternating_rows is True
        assert result.border_color == "#999999"
        assert result.header_font_size == 12.0

    def test_table_without_profile(self):
        table = StyledTable(headers=["H"], rows=[["r"]])
        result = convert_styled_table_to_table_spec(table, None)
        assert result.header_bg_color == ""


class TestContentBlockFlattening:
    def test_text_blocks_become_content(self):
        slide = SlideDesign(
            title="Test",
            content_blocks=[
                ContentBlock(block_type="text", text="Hello world"),
                ContentBlock(block_type="text", text="Second paragraph"),
            ],
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert "Hello world" in result.content
        assert "Second paragraph" in result.content

    def test_bullet_blocks_become_bullet_points(self):
        slide = SlideDesign(
            title="Test",
            content_blocks=[
                ContentBlock(block_type="bullets", bullet_points=["Point 1", "Point 2"]),
            ],
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.bullet_points == ["Point 1", "Point 2"]

    def test_metric_blocks_become_content(self):
        slide = SlideDesign(
            title="KPIs",
            content_blocks=[
                ContentBlock(
                    block_type="metric",
                    metric=KeyMetric(label="Revenue", value="$1M"),
                ),
            ],
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert "Revenue: $1M" in result.content


class TestChartRefResolution:
    def test_chart_ref_resolved_from_spec(self):
        resolved = ResolvedChart(
            chart_type="line",
            title="Trend",
            categories=["Jan", "Feb"],
            series=[DataSeries(name="Sales", values=[10, 20])],
        )
        slide = SlideDesign(title="Chart Slide", chart_ref="my_chart")
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.PRESENTATION,
            charts={"my_chart": resolved},
        )
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.chart is not None
        assert result.chart.chart_type == "line"
        assert result.chart.title == "Trend"

    def test_missing_chart_ref_graceful(self):
        slide = SlideDesign(title="No Chart", chart_ref="nonexistent")
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.chart is None


class TestImageRefResolution:
    def test_image_ref_writes_temp_file(self, tmp_path):
        img_data = b"\x89PNG\r\n\x1a\nfake-png-data"
        resolved = ResolvedImage(data=img_data, mime_type="image/png", alt_text="logo")
        slide = SlideDesign(title="Image Slide", image_ref="logo")
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.PRESENTATION,
            images={"logo": resolved},
        )
        result = convert_slide_design_to_slide_spec(slide, spec, temp_dir=str(tmp_path))
        assert result.image_path != ""
        assert os.path.exists(result.image_path)
        with open(result.image_path, "rb") as f:
            assert f.read() == img_data

    def test_missing_image_ref_graceful(self):
        slide = SlideDesign(title="No Image", image_ref="nonexistent")
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.image_path == ""


class TestConvertDesignSpecToSlideSpecs:
    def test_converts_all_slides(self):
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.PRESENTATION,
            slides=[
                SlideDesign(title="Slide 1"),
                SlideDesign(title="Slide 2"),
                SlideDesign(title="Slide 3"),
            ],
        )
        results = convert_design_spec_to_slide_specs(spec)
        assert len(results) == 3
        assert results[0].title == "Slide 1"
        assert results[2].title == "Slide 3"

    def test_empty_slides(self):
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        results = convert_design_spec_to_slide_specs(spec)
        assert results == []

    def test_direct_fields_mapped(self):
        slide = SlideDesign(
            layout="Two Content",
            title="My Title",
            subtitle="My Sub",
            speaker_notes="Notes here",
            transition="fade",
            background="#f0f0f0",
            title_style=TextStyle(font_name="Arial", bold=True),
            images=[ImagePlacement(image_ref="img1", width=5.0, height=3.0)],
        )
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.PRESENTATION,
            slides=[slide],
        )
        result = convert_design_spec_to_slide_specs(spec)[0]
        assert result.layout == "Two Content"
        assert result.title == "My Title"
        assert result.subtitle == "My Sub"
        assert result.speaker_notes == "Notes here"
        assert result.transition == "fade"
        assert result.background_color == "#f0f0f0"
        assert result.title_style is not None
        assert result.title_style.font_name == "Arial"
        assert len(result.images) == 1


# ── Content zone threading tests ──────────────────────────────────────────


def _make_layout_zone(
    name: str = "Title and Content",
    title_idx: int = 0,
    body_idx: int = 1,
    phs: list[PlaceholderZone] | None = None,
) -> LayoutZone:
    if phs is None:
        phs = [
            PlaceholderZone(idx=title_idx, name="Title", ph_type="title", left=0.5, top=0.3, width=9.0, height=0.8),
            PlaceholderZone(idx=body_idx, name="Content", ph_type="body", left=0.5, top=1.5, width=9.0, height=5.0),
            PlaceholderZone(idx=10, name="Date", ph_type="date_time", left=0.5, top=7.0, width=2.0, height=0.3),
        ]
    return LayoutZone(
        layout_name=name,
        placeholders=phs,
        content_left=0.5,
        content_top=1.5,
        content_width=9.0,
        content_height=5.0,
        title_ph_idx=title_idx,
        body_ph_idx=body_idx,
    )


class TestBuildContentZone:
    def test_content_zone_from_layout_zone(self):
        """Verify EMU conversion correct."""
        zone = _make_layout_zone()
        cz = _build_content_zone(zone)
        assert isinstance(cz, ContentZone)
        assert cz.left == int(0.5 * 914400)
        assert cz.top == int(1.5 * 914400)
        assert cz.width == int(9.0 * 914400)
        assert cz.height == int(5.0 * 914400)
        assert cz.title_ph_idx == 0
        assert cz.body_ph_idx == 1

    def test_placeholder_map_built(self):
        """Verify title/body/date mapped."""
        zone = _make_layout_zone()
        cz = _build_content_zone(zone)
        assert cz.placeholder_map["title"] == 0
        assert cz.placeholder_map["body"] == 1
        assert cz.placeholder_map["date"] == 10

    def test_cover_layout_llm_classified_phs_mapped(self):
        """Verify LLM-classified ph_types flow through to placeholder_map."""
        phs = [
            PlaceholderZone(idx=21, name="Title 1", ph_type="title", left=1, top=1, width=6, height=1),
            PlaceholderZone(idx=19, name="Empresa Cliente", ph_type="client_name", left=1, top=5, width=4, height=0.5),
            PlaceholderZone(idx=20, name="Fecha", ph_type="date", left=5, top=5, width=3, height=0.5),
        ]
        zone = LayoutZone(
            layout_name="Portada",
            placeholders=phs,
            content_left=1.0, content_top=2.0, content_width=8.0, content_height=4.0,
            title_ph_idx=21, body_ph_idx=None,
        )
        cz = _build_content_zone(zone)
        assert cz.placeholder_map["title"] == 21
        assert cz.placeholder_map["client_name"] == 19
        assert cz.placeholder_map["date"] == 20

    def test_unclassified_custom_phs_not_in_map(self):
        """Custom placeholders that LLM couldn't classify are excluded from map."""
        phs = [
            PlaceholderZone(idx=0, name="Title", ph_type="title", left=0.5, top=0.3, width=9, height=0.8),
            PlaceholderZone(idx=22, name="Decoración", ph_type="custom", left=0, top=0, width=10, height=0.1),
        ]
        zone = LayoutZone(
            layout_name="Content",
            placeholders=phs,
            content_left=0.5, content_top=1.5, content_width=9.0, content_height=5.0,
            title_ph_idx=0, body_ph_idx=None,
        )
        cz = _build_content_zone(zone)
        assert "title" in cz.placeholder_map
        assert 22 not in cz.placeholder_map.values()


class TestContentZoneInConverter:
    def test_no_content_zone_when_no_layout_zones(self):
        """Verify None when profile has no layout_zones."""
        slide = SlideDesign(title="Test", layout="Title and Content")
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.PRESENTATION)
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.content_zone is None

    def test_content_zone_threaded_from_profile(self):
        """Verify content_zone populated when layout_zones available."""
        layout_zone = _make_layout_zone()
        profile = _make_profile(layout_zones={"Title and Content": layout_zone})
        slide = SlideDesign(title="Test", layout="Title and Content")
        spec = DesignSpec(profile=profile, output_type=OutputType.PRESENTATION, slides=[slide])
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.content_zone is not None
        assert result.content_zone.title_ph_idx == 0
        assert result.content_zone.body_ph_idx == 1
        assert result.content_zone.left == int(0.5 * 914400)

    def test_content_zone_none_for_unknown_layout(self):
        """Verify None when slide layout doesn't match any layout_zone."""
        layout_zone = _make_layout_zone(name="Title and Content")
        profile = _make_profile(layout_zones={"Title and Content": layout_zone})
        slide = SlideDesign(title="Test", layout="Unknown Layout")
        spec = DesignSpec(profile=profile, output_type=OutputType.PRESENTATION, slides=[slide])
        result = convert_slide_design_to_slide_spec(slide, spec)
        assert result.content_zone is None


# ── Document converter tests ─────────────────────────────────────────────


class TestStyledTableToTableData:
    def test_headers_and_rows_mapped(self):
        table = StyledTable(
            headers=["Name", "Value"],
            rows=[["A", "1"], ["B", "2"]],
            header_style=TextStyle(font_name="Calibri"),
        )
        result = convert_styled_table_to_table_data(table)
        assert result.headers == ["Name", "Value"]
        assert result.rows == [["A", "1"], ["B", "2"]]


class TestSectionDesignToSectionSpec:
    def test_basic_fields(self):
        section = SectionDesign(
            heading="Introduction",
            heading_level=2,
            content="Welcome to the report.",
            bullet_points=["Point A", "Point B"],
            numbered_list=["Step 1", "Step 2"],
            callout="Important note",
            page_break_before=True,
            heading_style=TextStyle(font_name="Arial", bold=True),
            body_style=TextStyle(font_name="Calibri"),
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.DOCUMENT)
        result = convert_section_design_to_section_spec(section, spec)
        assert result.heading == "Introduction"
        assert result.heading_level == 2
        assert result.content == "Welcome to the report."
        assert result.bullet_points == ["Point A", "Point B"]
        assert result.numbered_list == ["Step 1", "Step 2"]
        assert result.callout == "Important note"
        assert result.page_break_before is True
        assert result.heading_style.font_name == "Arial"
        assert result.body_style.font_name == "Calibri"

    def test_chart_ref_resolved(self):
        chart = ResolvedChart(
            chart_type="bar",
            title="Revenue",
            categories=["Q1", "Q2"],
            series=[DataSeries(name="2025", values=[100, 200])],
        )
        section = SectionDesign(heading="Charts", chart_ref="rev_chart")
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.DOCUMENT,
            charts={"rev_chart": chart},
        )
        result = convert_section_design_to_section_spec(section, spec)
        assert result.chart is not None
        assert result.chart.chart_type == "bar"
        assert result.chart.title == "Revenue"

    def test_image_ref_resolved(self, tmp_path):
        img_data = b"\x89PNG\r\n\x1a\nfake-png-data"
        resolved = ResolvedImage(data=img_data, mime_type="image/png", alt_text="logo")
        section = SectionDesign(heading="Logo", image_ref="logo_img")
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.DOCUMENT,
            images={"logo_img": resolved},
        )
        result = convert_section_design_to_section_spec(section, spec, temp_dir=str(tmp_path))
        assert len(result.images) == 1
        img = result.images[0]
        assert img.file_path != ""
        assert os.path.exists(img.file_path)
        assert img.alt_text == "logo"
        with open(img.file_path, "rb") as f:
            assert f.read() == img_data

    def test_table_converted(self):
        section = SectionDesign(
            heading="Data",
            table=StyledTable(
                headers=["Col1", "Col2"],
                rows=[["a", "b"]],
            ),
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.DOCUMENT)
        result = convert_section_design_to_section_spec(section, spec)
        assert result.table is not None
        assert result.table.headers == ["Col1", "Col2"]
        assert result.table.rows == [["a", "b"]]


class TestDesignSpecToSectionSpecs:
    def test_converts_all_sections(self):
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.DOCUMENT,
            document_sections=[
                SectionDesign(heading="Section 1"),
                SectionDesign(heading="Section 2"),
                SectionDesign(heading="Section 3"),
            ],
        )
        results = convert_design_spec_to_section_specs(spec)
        assert len(results) == 3
        assert results[0].heading == "Section 1"
        assert results[2].heading == "Section 3"

    def test_empty_sections(self):
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.DOCUMENT)
        results = convert_design_spec_to_section_specs(spec)
        assert results == []


# ── Spreadsheet converter tests ──────────────────────────────────────────


class TestSheetDesignToSheetSpec:
    def test_basic_fields(self):
        sheet = SheetDesign(
            name="Revenue",
            headers=["Month", "Amount"],
            rows=[["Jan", 100], ["Feb", 200]],
            header_style=TextStyle(font_name="Arial", bold=True),
            cell_style=TextStyle(font_name="Calibri"),
            column_widths=[15.0, 12.0],
            number_formats={"B": "#,##0"},
        )
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.SPREADSHEET)
        result = convert_sheet_design_to_sheet_spec(sheet, spec)
        assert result.name == "Revenue"
        assert result.headers == ["Month", "Amount"]
        assert result.rows == [["Jan", 100], ["Feb", 200]]
        assert result.header_style.font_name == "Arial"
        assert result.cell_style.font_name == "Calibri"
        assert result.column_widths == [15.0, 12.0]
        assert result.number_formats == {"B": "#,##0"}

    def test_chart_ref_resolved(self):
        chart = ResolvedChart(
            chart_type="line",
            title="Trend",
            categories=["Q1", "Q2"],
            series=[DataSeries(name="Sales", values=[10, 20])],
        )
        sheet = SheetDesign(name="Sales", chart_ref="sales_chart")
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.SPREADSHEET,
            charts={"sales_chart": chart},
        )
        result = convert_sheet_design_to_sheet_spec(sheet, spec)
        assert result.chart is not None
        assert result.chart.chart_type == "line"

    def test_no_chart(self):
        sheet = SheetDesign(name="Plain")
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.SPREADSHEET)
        result = convert_sheet_design_to_sheet_spec(sheet, spec)
        assert result.chart is None


class TestDesignSpecToSheetSpecs:
    def test_converts_all_sheets(self):
        spec = DesignSpec(
            profile=_make_profile(),
            output_type=OutputType.SPREADSHEET,
            sheets=[
                SheetDesign(name="Sheet1"),
                SheetDesign(name="Sheet2"),
            ],
        )
        results = convert_design_spec_to_sheet_specs(spec)
        assert len(results) == 2
        assert results[0].name == "Sheet1"
        assert results[1].name == "Sheet2"

    def test_empty_sheets(self):
        spec = DesignSpec(profile=_make_profile(), output_type=OutputType.SPREADSHEET)
        results = convert_design_spec_to_sheet_specs(spec)
        assert results == []
