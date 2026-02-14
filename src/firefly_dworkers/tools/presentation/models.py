"""Data models for presentation tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from firefly_dworkers.design.models import ContentBlock, ImagePlacement, TextStyle


class TableSpec(BaseModel):
    """Specification for a table in a slide or document.

    All styling fields are optional with sensible defaults, so existing
    code passing ``{"headers": [...], "rows": [...]}`` dicts works unchanged.
    """

    headers: list[str]
    rows: list[list[str]]
    header_bg_color: str = ""  # hex, e.g. "#1a3c6d"
    header_text_color: str = "#FFFFFF"
    alternating_rows: bool = True
    alt_row_color: str = "#F5F5F5"
    border_color: str = "#CCCCCC"
    font_name: str = ""
    header_font_size: float = 10.0
    cell_font_size: float = 9.0
    column_widths: list[float] = Field(default_factory=list)  # inches


class ChartSpec(BaseModel):
    """Specification for a chart in a slide or document."""

    chart_type: str  # bar, line, pie, scatter, area
    title: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[dict[str, Any]] = Field(default_factory=list)  # [{"name": str, "values": list}]
    colors: list[str] = Field(default_factory=list)
    show_legend: bool = True
    show_data_labels: bool = False
    stacked: bool = False


class ContentZone(BaseModel):
    """Safe content area for a slide, in EMU."""

    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    title_ph_idx: int | None = None
    body_ph_idx: int | None = None
    placeholder_map: dict[str, int] = Field(default_factory=dict)
    # e.g. {"title": 21, "subtitle": 19, "date": 20}


class SlideSpec(BaseModel):
    """Specification for creating a slide."""

    layout: str = "Title and Content"
    title: str = ""
    subtitle: str = ""
    content: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    table: TableSpec | None = None
    chart: ChartSpec | None = None
    image_path: str = ""
    speaker_notes: str = ""
    title_style: TextStyle | None = None
    body_style: TextStyle | None = None
    background_color: str = ""
    background_image: str = ""
    transition: str = ""
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    images: list[ImagePlacement] = Field(default_factory=list)
    content_zone: ContentZone | None = None


class PlaceholderInfo(BaseModel):
    """Information about a placeholder in a slide layout."""

    idx: int
    name: str
    placeholder_type: str = ""
    width: float = 0.0
    height: float = 0.0


class ShapeInfo(BaseModel):
    """Information about a shape in a slide."""

    shape_type: str
    name: str = ""
    text: str = ""
    left: float = 0.0
    top: float = 0.0
    width: float = 0.0
    height: float = 0.0


class SlideData(BaseModel):
    """Parsed data from a slide."""

    index: int
    layout: str = ""
    title: str = ""
    content: str = ""
    placeholders: list[PlaceholderInfo] = Field(default_factory=list)
    shapes: list[ShapeInfo] = Field(default_factory=list)
    notes: str = ""


class PresentationData(BaseModel):
    """Parsed data from a presentation."""

    slides: list[SlideData] = Field(default_factory=list)
    master_layouts: list[str] = Field(default_factory=list)
    color_scheme: dict[str, str] = Field(default_factory=dict)
    fonts: list[str] = Field(default_factory=list)
    slide_width: float = 0.0
    slide_height: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SlideOperation(BaseModel):
    """An operation to modify a presentation."""

    operation: str  # add_slide, remove_slide, reorder, update_content
    slide_index: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
