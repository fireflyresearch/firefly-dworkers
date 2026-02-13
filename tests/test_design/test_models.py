"""Comprehensive tests for design intelligence data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from firefly_dworkers.design.models import (
    ContentBlock,
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    DesignProfile,
    DesignSpec,
    ImagePlacement,
    ImageRequest,
    KeyMetric,
    OutputType,
    ResolvedChart,
    ResolvedImage,
    SectionDesign,
    SheetDesign,
    SlideDesign,
    StyledTable,
    TextStyle,
)


# ── OutputType ────────────────────────────────────────────────────────────


class TestOutputType:
    def test_values(self):
        assert OutputType.PRESENTATION == "presentation"
        assert OutputType.DOCUMENT == "document"
        assert OutputType.SPREADSHEET == "spreadsheet"
        assert OutputType.PDF == "pdf"

    def test_is_str(self):
        assert isinstance(OutputType.PRESENTATION, str)

    def test_all_members(self):
        assert set(OutputType) == {
            OutputType.PRESENTATION,
            OutputType.DOCUMENT,
            OutputType.SPREADSHEET,
            OutputType.PDF,
        }


# ── TextStyle ─────────────────────────────────────────────────────────────


class TestTextStyle:
    def test_defaults(self):
        ts = TextStyle()
        assert ts.font_name == ""
        assert ts.font_size == 0
        assert ts.bold is False
        assert ts.italic is False
        assert ts.color == ""
        assert ts.alignment == "left"

    def test_full_construction(self):
        ts = TextStyle(
            font_name="Arial",
            font_size=14.5,
            bold=True,
            italic=True,
            color="#ff0000",
            alignment="center",
        )
        assert ts.font_name == "Arial"
        assert ts.font_size == 14.5
        assert ts.bold is True
        assert ts.italic is True
        assert ts.color == "#ff0000"
        assert ts.alignment == "center"

    def test_serialization_round_trip(self):
        ts = TextStyle(font_name="Helvetica", font_size=12, bold=True)
        data = ts.model_dump()
        ts2 = TextStyle.model_validate(data)
        assert ts == ts2

    def test_json_round_trip(self):
        ts = TextStyle(font_name="Times", font_size=10)
        json_str = ts.model_dump_json()
        ts2 = TextStyle.model_validate_json(json_str)
        assert ts == ts2


# ── KeyMetric ─────────────────────────────────────────────────────────────


class TestKeyMetric:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            KeyMetric()

    def test_minimal(self):
        km = KeyMetric(label="Revenue", value="$1M")
        assert km.label == "Revenue"
        assert km.value == "$1M"
        assert km.change == ""
        assert km.icon == ""

    def test_full_construction(self):
        km = KeyMetric(label="Revenue", value="$1M", change="+15%", icon="trending_up")
        assert km.change == "+15%"
        assert km.icon == "trending_up"


# ── StyledTable ───────────────────────────────────────────────────────────


class TestStyledTable:
    def test_defaults(self):
        st = StyledTable()
        assert st.headers == []
        assert st.rows == []
        assert st.header_style is None
        assert st.cell_style is None
        assert st.alternating_rows is False
        assert st.border_color == ""

    def test_full_construction(self):
        st = StyledTable(
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
            header_style=TextStyle(bold=True),
            cell_style=TextStyle(font_size=10),
            alternating_rows=True,
            border_color="#cccccc",
        )
        assert len(st.headers) == 2
        assert len(st.rows) == 2
        assert st.header_style.bold is True
        assert st.alternating_rows is True

    def test_mutable_default_isolation(self):
        """Ensure default lists are not shared between instances."""
        st1 = StyledTable()
        st2 = StyledTable()
        st1.headers.append("X")
        assert st2.headers == []


# ── ImagePlacement ────────────────────────────────────────────────────────


class TestImagePlacement:
    def test_defaults(self):
        ip = ImagePlacement()
        assert ip.image_ref == ""
        assert ip.file_path == ""
        assert ip.width == 0.0
        assert ip.height == 0.0
        assert ip.left == 0.0
        assert ip.top == 0.0
        assert ip.alt_text == ""

    def test_full_construction(self):
        ip = ImagePlacement(
            image_ref="logo",
            file_path="/tmp/logo.png",
            width=100.0,
            height=50.0,
            left=10.0,
            top=20.0,
            alt_text="Company logo",
        )
        assert ip.image_ref == "logo"
        assert ip.width == 100.0


# ── ContentBlock ──────────────────────────────────────────────────────────


class TestContentBlock:
    def test_defaults(self):
        cb = ContentBlock()
        assert cb.block_type == "text"
        assert cb.text == ""
        assert cb.bullet_points == []
        assert cb.metric is None
        assert cb.style is None

    def test_text_block(self):
        cb = ContentBlock(block_type="text", text="Hello world")
        assert cb.text == "Hello world"

    def test_metric_block(self):
        km = KeyMetric(label="Users", value="10K")
        cb = ContentBlock(block_type="metric", metric=km)
        assert cb.metric.label == "Users"

    def test_bullets_block(self):
        cb = ContentBlock(
            block_type="bullets",
            bullet_points=["Point 1", "Point 2", "Point 3"],
        )
        assert len(cb.bullet_points) == 3

    def test_mutable_default_isolation(self):
        cb1 = ContentBlock()
        cb2 = ContentBlock()
        cb1.bullet_points.append("item")
        assert cb2.bullet_points == []


# ── DataSeries ────────────────────────────────────────────────────────────


class TestDataSeries:
    def test_required_name(self):
        with pytest.raises(ValidationError):
            DataSeries()

    def test_minimal(self):
        ds = DataSeries(name="Sales")
        assert ds.name == "Sales"
        assert ds.values == []

    def test_mixed_values(self):
        ds = DataSeries(name="Mixed", values=[1, 2.5, "N/A", 4])
        assert ds.values == [1, 2.5, "N/A", 4]


# ── DataSet ───────────────────────────────────────────────────────────────


class TestDataSet:
    def test_required_name(self):
        with pytest.raises(ValidationError):
            DataSet()

    def test_minimal(self):
        ds = DataSet(name="Q1 Data")
        assert ds.name == "Q1 Data"
        assert ds.description == ""
        assert ds.categories == []
        assert ds.series == []
        assert ds.suggested_chart_type == ""

    def test_full_construction(self):
        ds = DataSet(
            name="Quarterly Sales",
            description="Sales by quarter",
            categories=["Q1", "Q2", "Q3", "Q4"],
            series=[
                DataSeries(name="2024", values=[100, 120, 115, 140]),
                DataSeries(name="2025", values=[110, 130, 125, 150]),
            ],
            suggested_chart_type="bar",
        )
        assert len(ds.series) == 2
        assert ds.series[0].values[0] == 100


# ── ImageRequest ──────────────────────────────────────────────────────────


class TestImageRequest:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ImageRequest()

    def test_ai_generate(self):
        ir = ImageRequest(
            name="hero_image",
            source_type="ai_generate",
            prompt="A futuristic cityscape at sunset",
            alt_text="Futuristic city",
        )
        assert ir.source_type == "ai_generate"
        assert ir.prompt != ""

    def test_url_source(self):
        ir = ImageRequest(
            name="photo",
            source_type="url",
            url="https://example.com/photo.jpg",
        )
        assert ir.url == "https://example.com/photo.jpg"

    def test_file_source(self):
        ir = ImageRequest(
            name="logo",
            source_type="file",
            file_path="/tmp/logo.png",
        )
        assert ir.file_path == "/tmp/logo.png"


# ── ContentSection ────────────────────────────────────────────────────────


class TestContentSection:
    def test_defaults(self):
        cs = ContentSection()
        assert cs.heading == ""
        assert cs.content == ""
        assert cs.bullet_points == []
        assert cs.key_metrics == []
        assert cs.chart_ref == ""
        assert cs.image_ref == ""
        assert cs.table_data is None
        assert cs.emphasis == "normal"
        assert cs.speaker_notes == ""

    def test_full_construction(self):
        cs = ContentSection(
            heading="Revenue Overview",
            content="Revenue grew 15% YoY.",
            bullet_points=["Growth in APAC", "Strong SaaS retention"],
            key_metrics=[
                KeyMetric(label="Revenue", value="$10M", change="+15%"),
                KeyMetric(label="Customers", value="500"),
            ],
            chart_ref="revenue_chart",
            image_ref="revenue_img",
            table_data=StyledTable(
                headers=["Region", "Revenue"],
                rows=[["APAC", "$4M"], ["EMEA", "$6M"]],
            ),
            emphasis="high",
            speaker_notes="Discuss APAC growth in detail.",
        )
        assert cs.heading == "Revenue Overview"
        assert len(cs.key_metrics) == 2
        assert cs.table_data.headers == ["Region", "Revenue"]


# ── ContentBrief ──────────────────────────────────────────────────────────


class TestContentBrief:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ContentBrief()

    def test_minimal(self):
        cb = ContentBrief(
            output_type=OutputType.PRESENTATION,
            title="Q1 Report",
        )
        assert cb.output_type == OutputType.PRESENTATION
        assert cb.title == "Q1 Report"
        assert cb.sections == []
        assert cb.audience == ""
        assert cb.tone == ""
        assert cb.purpose == ""
        assert cb.reference_template == ""
        assert cb.brand_colors == []
        assert cb.brand_fonts == []
        assert cb.datasets == []
        assert cb.image_requests == []

    def test_output_type_from_string(self):
        cb = ContentBrief(
            output_type="document",
            title="Test",
        )
        assert cb.output_type == OutputType.DOCUMENT

    def test_full_construction(self):
        cb = ContentBrief(
            output_type=OutputType.PRESENTATION,
            title="Annual Report",
            sections=[
                ContentSection(heading="Intro", content="Welcome"),
                ContentSection(heading="Financials", content="Strong year"),
            ],
            audience="Board of Directors",
            tone="formal",
            purpose="Annual review",
            reference_template="corporate_template.pptx",
            brand_colors=["#003366", "#ff9900"],
            brand_fonts=["Calibri", "Arial"],
            datasets=[DataSet(name="Revenue")],
            image_requests=[
                ImageRequest(name="logo", source_type="file", file_path="/tmp/logo.png"),
            ],
        )
        assert len(cb.sections) == 2
        assert cb.audience == "Board of Directors"
        assert len(cb.brand_colors) == 2
        assert len(cb.datasets) == 1
        assert len(cb.image_requests) == 1

    def test_invalid_output_type(self):
        with pytest.raises(ValidationError):
            ContentBrief(output_type="invalid_type", title="Test")

    def test_serialization_round_trip(self):
        cb = ContentBrief(
            output_type=OutputType.DOCUMENT,
            title="Test Doc",
            sections=[ContentSection(heading="Section 1")],
            brand_colors=["#000000"],
        )
        data = cb.model_dump()
        cb2 = ContentBrief.model_validate(data)
        assert cb2.title == cb.title
        assert cb2.output_type == cb.output_type
        assert len(cb2.sections) == 1

    def test_json_round_trip(self):
        cb = ContentBrief(
            output_type=OutputType.SPREADSHEET,
            title="Budget",
        )
        json_str = cb.model_dump_json()
        cb2 = ContentBrief.model_validate_json(json_str)
        assert cb2 == cb


# ── DesignProfile ─────────────────────────────────────────────────────────


class TestDesignProfile:
    def test_defaults(self):
        dp = DesignProfile()
        assert dp.primary_color == ""
        assert dp.secondary_color == ""
        assert dp.accent_color == ""
        assert dp.background_color == "#ffffff"
        assert dp.text_color == "#333333"
        assert dp.color_palette == []
        assert dp.heading_font == ""
        assert dp.body_font == ""
        assert dp.font_sizes == {}
        assert dp.available_layouts == []
        assert dp.preferred_layouts == {}
        assert dp.margins == {}
        assert dp.line_spacing == 1.15
        assert dp.styles == []
        assert dp.master_slide_names == []

    def test_full_construction(self):
        dp = DesignProfile(
            primary_color="#003366",
            secondary_color="#ff9900",
            accent_color="#00cc66",
            background_color="#f5f5f5",
            text_color="#222222",
            color_palette=["#003366", "#ff9900", "#00cc66"],
            heading_font="Georgia",
            body_font="Arial",
            font_sizes={"h1": 28.0, "h2": 22.0, "body": 11.0},
            available_layouts=["Title Slide", "Title and Content", "Blank"],
            preferred_layouts={"intro": "Title Slide", "content": "Title and Content"},
            margins={"top": 1.0, "bottom": 1.0, "left": 0.75, "right": 0.75},
            line_spacing=1.5,
            styles=["Heading 1", "Heading 2", "Normal"],
            master_slide_names=["Office Theme"],
        )
        assert dp.primary_color == "#003366"
        assert dp.font_sizes["h1"] == 28.0
        assert len(dp.available_layouts) == 3

    def test_mutable_default_isolation(self):
        dp1 = DesignProfile()
        dp2 = DesignProfile()
        dp1.color_palette.append("#000000")
        assert dp2.color_palette == []


# ── ResolvedChart ─────────────────────────────────────────────────────────


class TestResolvedChart:
    def test_required_chart_type(self):
        with pytest.raises(ValidationError):
            ResolvedChart()

    def test_minimal(self):
        rc = ResolvedChart(chart_type="bar")
        assert rc.chart_type == "bar"
        assert rc.title == ""
        assert rc.categories == []
        assert rc.series == []
        assert rc.colors == []
        assert rc.show_legend is True
        assert rc.show_data_labels is False
        assert rc.stacked is False

    def test_full_construction(self):
        rc = ResolvedChart(
            chart_type="line",
            title="Monthly Trend",
            categories=["Jan", "Feb", "Mar"],
            series=[
                DataSeries(name="Revenue", values=[100, 110, 120]),
                DataSeries(name="Cost", values=[80, 85, 90]),
            ],
            colors=["#003366", "#ff9900"],
            show_legend=True,
            show_data_labels=True,
            stacked=False,
        )
        assert len(rc.series) == 2
        assert rc.show_data_labels is True


# ── ResolvedImage ─────────────────────────────────────────────────────────


class TestResolvedImage:
    def test_defaults(self):
        ri = ResolvedImage()
        assert ri.data == b""
        assert ri.mime_type == "image/png"
        assert ri.alt_text == ""
        assert ri.width == 0.0
        assert ri.height == 0.0

    def test_with_data(self):
        ri = ResolvedImage(
            data=b"\x89PNG\r\n",
            mime_type="image/png",
            alt_text="Logo",
            width=200.0,
            height=100.0,
        )
        assert ri.data == b"\x89PNG\r\n"
        assert ri.alt_text == "Logo"

    def test_json_round_trip(self):
        ri = ResolvedImage(data=b"test_bytes", mime_type="image/jpeg")
        json_str = ri.model_dump_json()
        ri2 = ResolvedImage.model_validate_json(json_str)
        assert ri2.data == b"test_bytes"
        assert ri2.mime_type == "image/jpeg"


# ── SlideDesign ───────────────────────────────────────────────────────────


class TestSlideDesign:
    def test_defaults(self):
        sd = SlideDesign()
        assert sd.layout == "Title and Content"
        assert sd.title == ""
        assert sd.subtitle == ""
        assert sd.content_blocks == []
        assert sd.chart_ref == ""
        assert sd.image_ref == ""
        assert sd.table is None
        assert sd.speaker_notes == ""
        assert sd.transition == ""
        assert sd.title_style is None
        assert sd.body_style is None
        assert sd.background == ""
        assert sd.images == []

    def test_full_construction(self):
        sd = SlideDesign(
            layout="Two Content",
            title="Slide Title",
            subtitle="Subtitle",
            content_blocks=[
                ContentBlock(block_type="text", text="Main point"),
                ContentBlock(
                    block_type="bullets",
                    bullet_points=["A", "B"],
                ),
            ],
            chart_ref="chart_1",
            image_ref="img_1",
            table=StyledTable(headers=["X", "Y"], rows=[["1", "2"]]),
            speaker_notes="Talk about this...",
            transition="fade",
            title_style=TextStyle(font_size=24, bold=True),
            body_style=TextStyle(font_size=12),
            background="#f0f0f0",
            images=[
                ImagePlacement(image_ref="logo", width=50, height=50),
            ],
        )
        assert sd.layout == "Two Content"
        assert len(sd.content_blocks) == 2
        assert sd.table.headers == ["X", "Y"]
        assert len(sd.images) == 1


# ── SectionDesign ─────────────────────────────────────────────────────────


class TestSectionDesign:
    def test_defaults(self):
        sd = SectionDesign()
        assert sd.heading == ""
        assert sd.heading_level == 1
        assert sd.content == ""
        assert sd.bullet_points == []
        assert sd.numbered_list == []
        assert sd.chart_ref == ""
        assert sd.image_ref == ""
        assert sd.table is None
        assert sd.callout == ""
        assert sd.page_break_before is False
        assert sd.heading_style is None
        assert sd.body_style is None
        assert sd.images == []

    def test_full_construction(self):
        sd = SectionDesign(
            heading="Introduction",
            heading_level=2,
            content="This section introduces the topic.",
            bullet_points=["Point 1", "Point 2"],
            numbered_list=["Step 1", "Step 2"],
            chart_ref="chart_intro",
            image_ref="img_intro",
            table=StyledTable(headers=["A"], rows=[["1"]]),
            callout="Important note here.",
            page_break_before=True,
            heading_style=TextStyle(font_size=18, bold=True),
            body_style=TextStyle(font_size=11),
            images=[ImagePlacement(image_ref="diagram")],
        )
        assert sd.heading == "Introduction"
        assert sd.heading_level == 2
        assert sd.page_break_before is True
        assert len(sd.images) == 1


# ── SheetDesign ───────────────────────────────────────────────────────────


class TestSheetDesign:
    def test_required_name(self):
        with pytest.raises(ValidationError):
            SheetDesign()

    def test_minimal(self):
        sd = SheetDesign(name="Sheet1")
        assert sd.name == "Sheet1"
        assert sd.headers == []
        assert sd.rows == []
        assert sd.chart_ref == ""
        assert sd.header_style is None
        assert sd.cell_style is None
        assert sd.column_widths == []
        assert sd.number_formats == {}

    def test_full_construction(self):
        sd = SheetDesign(
            name="Revenue",
            headers=["Month", "Revenue", "Cost"],
            rows=[
                ["Jan", 100000, 80000],
                ["Feb", 110000, 85000],
            ],
            chart_ref="revenue_chart",
            header_style=TextStyle(bold=True, font_size=11),
            cell_style=TextStyle(font_size=10),
            column_widths=[15.0, 12.0, 12.0],
            number_formats={"Revenue": "#,##0", "Cost": "#,##0"},
        )
        assert sd.name == "Revenue"
        assert len(sd.rows) == 2
        assert sd.rows[0][1] == 100000
        assert len(sd.column_widths) == 3

    def test_mixed_row_types(self):
        """SheetDesign rows accept Any types."""
        sd = SheetDesign(
            name="Mixed",
            rows=[["text", 42, 3.14, True, None]],
        )
        assert sd.rows[0] == ["text", 42, 3.14, True, None]


# ── DesignSpec ────────────────────────────────────────────────────────────


class TestDesignSpec:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            DesignSpec()

    def test_minimal_presentation(self):
        ds = DesignSpec(
            profile=DesignProfile(),
            output_type=OutputType.PRESENTATION,
        )
        assert ds.output_type == OutputType.PRESENTATION
        assert ds.slides == []
        assert ds.document_sections == []
        assert ds.sheets == []
        assert ds.charts == {}
        assert ds.images == {}

    def test_presentation_spec(self):
        ds = DesignSpec(
            profile=DesignProfile(
                primary_color="#003366",
                heading_font="Arial",
            ),
            output_type=OutputType.PRESENTATION,
            slides=[
                SlideDesign(layout="Title Slide", title="Welcome"),
                SlideDesign(
                    layout="Title and Content",
                    title="Overview",
                    content_blocks=[ContentBlock(text="Key findings")],
                ),
            ],
            charts={
                "chart_1": ResolvedChart(
                    chart_type="bar",
                    categories=["Q1", "Q2"],
                    series=[DataSeries(name="Rev", values=[100, 120])],
                ),
            },
            images={
                "logo": ResolvedImage(data=b"png_data", alt_text="Logo"),
            },
        )
        assert len(ds.slides) == 2
        assert "chart_1" in ds.charts
        assert "logo" in ds.images
        assert ds.charts["chart_1"].chart_type == "bar"

    def test_document_spec(self):
        ds = DesignSpec(
            profile=DesignProfile(),
            output_type=OutputType.DOCUMENT,
            document_sections=[
                SectionDesign(heading="Introduction", heading_level=1),
                SectionDesign(heading="Details", heading_level=2, content="Some text."),
            ],
        )
        assert ds.output_type == OutputType.DOCUMENT
        assert len(ds.document_sections) == 2

    def test_spreadsheet_spec(self):
        ds = DesignSpec(
            profile=DesignProfile(),
            output_type=OutputType.SPREADSHEET,
            sheets=[
                SheetDesign(name="Summary", headers=["A", "B"]),
                SheetDesign(name="Details", headers=["X", "Y", "Z"]),
            ],
        )
        assert len(ds.sheets) == 2

    def test_output_type_from_string(self):
        ds = DesignSpec(
            profile=DesignProfile(),
            output_type="pdf",
        )
        assert ds.output_type == OutputType.PDF

    def test_serialization_round_trip(self):
        ds = DesignSpec(
            profile=DesignProfile(primary_color="#000"),
            output_type=OutputType.PRESENTATION,
            slides=[SlideDesign(title="Test")],
            charts={
                "c1": ResolvedChart(chart_type="pie"),
            },
        )
        data = ds.model_dump()
        ds2 = DesignSpec.model_validate(data)
        assert ds2.profile.primary_color == "#000"
        assert len(ds2.slides) == 1
        assert "c1" in ds2.charts

    def test_json_round_trip(self):
        ds = DesignSpec(
            profile=DesignProfile(),
            output_type=OutputType.DOCUMENT,
            document_sections=[SectionDesign(heading="H1")],
        )
        json_str = ds.model_dump_json()
        ds2 = DesignSpec.model_validate_json(json_str)
        assert ds2.output_type == OutputType.DOCUMENT
        assert len(ds2.document_sections) == 1

    def test_mutable_default_isolation(self):
        ds1 = DesignSpec(profile=DesignProfile(), output_type=OutputType.PRESENTATION)
        ds2 = DesignSpec(profile=DesignProfile(), output_type=OutputType.PRESENTATION)
        ds1.slides.append(SlideDesign(title="Added"))
        assert ds2.slides == []
