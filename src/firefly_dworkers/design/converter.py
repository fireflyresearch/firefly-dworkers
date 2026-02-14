"""Converters from DesignSpec models to tool-specific spec models.

Supports three output formats:
- Presentation: DesignSpec → list[SlideSpec]
- Document: DesignSpec → list[SectionSpec]
- Spreadsheet: DesignSpec → list[SheetSpec]
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from firefly_dworkers.design.models import (
    ContentBlock,
    DesignProfile,
    DesignSpec,
    ImagePlacement,
    LayoutZone,
    ResolvedChart,
    ResolvedImage,
    SectionDesign,
    SheetDesign,
    SlideDesign,
    StyledTable,
)
from firefly_dworkers.tools.presentation.models import (
    ChartSpec,
    ContentZone,
    SlideSpec,
    TableSpec,
)

_EMU_PER_INCH = 914400


def _build_content_zone(layout_zone: LayoutZone) -> ContentZone:
    """Convert LayoutZone (inches) to ContentZone (EMU) with placeholder map.

    Reads ``ph_type`` directly — all classification (including LLM-based
    classification of custom placeholders) is done upstream in the analyzer.
    No language-specific name heuristics here.
    """
    # Map of ph_type values that should appear in the placeholder_map.
    # "date_time" is normalized to "date" for consumers.
    _TYPE_TO_KEY = {"date_time": "date"}

    ph_map: dict[str, int] = {}
    for ph in layout_zone.placeholders:
        if ph.ph_type in ("custom", "slide_number", "footer", "decorative", "logo"):
            continue
        key = _TYPE_TO_KEY.get(ph.ph_type, ph.ph_type)
        ph_map[key] = ph.idx
    return ContentZone(
        left=int(layout_zone.content_left * _EMU_PER_INCH),
        top=int(layout_zone.content_top * _EMU_PER_INCH),
        width=int(layout_zone.content_width * _EMU_PER_INCH),
        height=int(layout_zone.content_height * _EMU_PER_INCH),
        title_ph_idx=layout_zone.title_ph_idx,
        body_ph_idx=layout_zone.body_ph_idx,
        placeholder_map=ph_map,
    )


def convert_resolved_chart_to_chart_spec(chart: ResolvedChart) -> ChartSpec:
    """Direct field mapping. series: list[DataSeries] -> list[dict]."""
    return ChartSpec(
        chart_type=chart.chart_type,
        title=chart.title,
        categories=list(chart.categories),
        series=[{"name": s.name, "values": list(s.values)} for s in chart.series],
        colors=list(chart.colors),
        show_legend=chart.show_legend,
        show_data_labels=chart.show_data_labels,
        stacked=chart.stacked,
    )


def convert_styled_table_to_table_spec(
    table: StyledTable,
    profile: DesignProfile | None = None,
) -> TableSpec:
    """Map headers, rows, alternating_rows, border_color direct.

    header_style.font_name -> font_name, header_style.color -> header_text_color.
    header_bg_color from profile.primary_color if available.
    """
    font_name = ""
    header_text_color = "#FFFFFF"
    header_font_size = 10.0
    cell_font_size = 9.0

    if table.header_style:
        if table.header_style.font_name:
            font_name = table.header_style.font_name
        if table.header_style.color:
            header_text_color = table.header_style.color
        if table.header_style.font_size:
            header_font_size = table.header_style.font_size

    if table.cell_style and table.cell_style.font_size:
        cell_font_size = table.cell_style.font_size

    header_bg_color = ""
    if profile and profile.primary_color:
        header_bg_color = profile.primary_color

    return TableSpec(
        headers=list(table.headers),
        rows=[list(row) for row in table.rows],
        header_bg_color=header_bg_color,
        header_text_color=header_text_color,
        alternating_rows=table.alternating_rows,
        border_color=table.border_color or "#CCCCCC",
        font_name=font_name,
        header_font_size=header_font_size,
        cell_font_size=cell_font_size,
    )


def _write_image_to_temp(resolved: ResolvedImage, name: str, temp_dir: str) -> str:
    """Write resolved image bytes to a temp file and return its path."""
    ext = ".png" if "png" in resolved.mime_type else ".jpg"
    path = os.path.join(temp_dir, f"{name}{ext}")
    with open(path, "wb") as f:
        f.write(resolved.data)
    return path


# ── Presentation conversions ────────────────────────────────────────────────


def convert_slide_design_to_slide_spec(
    slide: SlideDesign,
    spec: DesignSpec,
    *,
    temp_dir: str = "",
) -> SlideSpec:
    """Convert a single SlideDesign to a SlideSpec.

    Resolves chart_ref from spec.charts, image_ref from spec.images
    (writing bytes to a temp file). Flattens content_blocks so that
    text blocks become content and bullet blocks become bullet_points.
    """
    chart: ChartSpec | None = None
    if slide.chart_ref and slide.chart_ref in spec.charts:
        chart = convert_resolved_chart_to_chart_spec(spec.charts[slide.chart_ref])

    table: TableSpec | None = None
    if slide.table:
        table = convert_styled_table_to_table_spec(slide.table, spec.profile)

    image_path = ""
    if slide.image_ref and slide.image_ref in spec.images:
        img = spec.images[slide.image_ref]
        if img.data:
            td = temp_dir or tempfile.mkdtemp(prefix="firefly_img_")
            image_path = _write_image_to_temp(img, slide.image_ref, td)

    content_parts: list[str] = []
    bullet_points: list[str] = []
    for block in slide.content_blocks:
        if block.block_type == "text" and block.text:
            content_parts.append(block.text)
        elif block.block_type == "bullets" and block.bullet_points:
            bullet_points.extend(block.bullet_points)
        elif block.block_type == "metric" and block.metric:
            content_parts.append(f"{block.metric.label}: {block.metric.value}")
        elif block.block_type == "callout" and block.text:
            content_parts.append(block.text)

    # Build content zone from layout zones if available
    content_zone: ContentZone | None = None
    layout_zone = spec.profile.layout_zones.get(slide.layout)
    if layout_zone:
        content_zone = _build_content_zone(layout_zone)

    return SlideSpec(
        layout=slide.layout,
        title=slide.title,
        subtitle=slide.subtitle,
        content="\n".join(content_parts),
        bullet_points=bullet_points,
        table=table,
        chart=chart,
        image_path=image_path,
        speaker_notes=slide.speaker_notes,
        title_style=slide.title_style,
        body_style=slide.body_style,
        background_color=slide.background,
        transition=slide.transition,
        images=list(slide.images),
        content_zone=content_zone,
    )


def convert_design_spec_to_slide_specs(
    spec: DesignSpec,
    *,
    temp_dir: str = "",
) -> list[SlideSpec]:
    """Convert all slides in a DesignSpec to SlideSpecs.

    Creates a shared temp directory (via tempfile.mkdtemp) when temp_dir
    is empty, so all image files for the batch land in the same folder.
    """
    td = temp_dir or tempfile.mkdtemp(prefix="firefly_slides_")
    return [
        convert_slide_design_to_slide_spec(slide, spec, temp_dir=td)
        for slide in spec.slides
    ]


# ── Document conversions ────────────────────────────────────────────────────


def convert_styled_table_to_table_data(table: StyledTable) -> Any:
    """Convert StyledTable (design model) to TableData (document tool model)."""
    from firefly_dworkers.tools.document.models import TableData

    return TableData(
        headers=list(table.headers),
        rows=[list(row) for row in table.rows],
    )


def convert_section_design_to_section_spec(
    section: SectionDesign,
    spec: DesignSpec,
    *,
    temp_dir: str = "",
) -> Any:
    """Convert SectionDesign (LLM output) to SectionSpec (tool input)."""
    from firefly_dworkers.tools.document.models import SectionSpec

    # Resolve chart_ref → ResolvedChart
    chart = None
    if section.chart_ref and section.chart_ref in spec.charts:
        chart = spec.charts[section.chart_ref]

    # Resolve table → TableData
    table = None
    if section.table:
        table = convert_styled_table_to_table_data(section.table)

    # Resolve image_ref → ImagePlacement with temp file
    images = list(section.images)
    if section.image_ref and section.image_ref in spec.images:
        resolved = spec.images[section.image_ref]
        if resolved.data:
            td = temp_dir or tempfile.mkdtemp(prefix="firefly_doc_")
            img_path = _write_image_to_temp(resolved, section.image_ref, td)
            images.append(
                ImagePlacement(
                    file_path=img_path,
                    alt_text=resolved.alt_text,
                )
            )

    return SectionSpec(
        heading=section.heading,
        heading_level=section.heading_level,
        content=section.content,
        bullet_points=list(section.bullet_points),
        numbered_list=list(section.numbered_list),
        table=table,
        chart=chart,
        images=images,
        callout=section.callout,
        page_break_before=section.page_break_before,
        heading_style=section.heading_style,
        body_style=section.body_style,
    )


def convert_design_spec_to_section_specs(
    spec: DesignSpec,
    *,
    temp_dir: str = "",
) -> list[Any]:
    """Convert all document_sections in a DesignSpec to SectionSpecs."""
    td = temp_dir or tempfile.mkdtemp(prefix="firefly_doc_")
    return [
        convert_section_design_to_section_spec(s, spec, temp_dir=td)
        for s in spec.document_sections
    ]


# ── Spreadsheet conversions ─────────────────────────────────────────────────


def convert_sheet_design_to_sheet_spec(
    sheet: SheetDesign,
    spec: DesignSpec,
) -> Any:
    """Convert SheetDesign (LLM output) to SheetSpec (tool input)."""
    from firefly_dworkers.tools.spreadsheet.models import SheetSpec

    chart = None
    if sheet.chart_ref and sheet.chart_ref in spec.charts:
        chart = spec.charts[sheet.chart_ref]

    return SheetSpec(
        name=sheet.name,
        headers=list(sheet.headers),
        rows=[list(row) for row in sheet.rows],
        header_style=sheet.header_style,
        cell_style=sheet.cell_style,
        column_widths=list(sheet.column_widths),
        number_formats=dict(sheet.number_formats),
        chart=chart,
    )


def convert_design_spec_to_sheet_specs(spec: DesignSpec) -> list[Any]:
    """Convert all sheets in a DesignSpec to SheetSpecs."""
    return [
        convert_sheet_design_to_sheet_spec(s, spec) for s in spec.sheets
    ]
