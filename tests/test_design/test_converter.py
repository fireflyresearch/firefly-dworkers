"""Tests for DesignSpec -> SlideSpec converters."""

from __future__ import annotations

import os

from firefly_dworkers.design.converter import (
    convert_design_spec_to_slide_specs,
    convert_resolved_chart_to_chart_spec,
    convert_slide_design_to_slide_spec,
    convert_styled_table_to_table_spec,
)
from firefly_dworkers.design.models import (
    ContentBlock,
    DataSeries,
    DesignProfile,
    DesignSpec,
    ImagePlacement,
    KeyMetric,
    OutputType,
    ResolvedChart,
    ResolvedImage,
    SlideDesign,
    StyledTable,
    TextStyle,
)


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
