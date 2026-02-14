"""Converters from DesignSpec models to presentation tool SlideSpec models."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from firefly_dworkers.design.models import (
    ContentBlock,
    DesignProfile,
    DesignSpec,
    ResolvedChart,
    SlideDesign,
    StyledTable,
)
from firefly_dworkers.tools.presentation.models import (
    ChartSpec,
    SlideSpec,
    TableSpec,
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
            ext = ".png" if "png" in img.mime_type else ".jpg"
            td = temp_dir or tempfile.mkdtemp(prefix="firefly_img_")
            path = os.path.join(td, f"{slide.image_ref}{ext}")
            with open(path, "wb") as f:
                f.write(img.data)
            image_path = path

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
