"""Data models for the design intelligence pipeline.

Three-stage pipeline:
- ContentBrief: what other workers hand off (content + context)
- DesignProfile: design DNA extracted from reference templates
- DesignSpec: fully resolved blueprint that tools render
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OutputType(StrEnum):
    """Supported output format types."""

    PRESENTATION = "presentation"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PDF = "pdf"


class TextStyle(BaseModel):
    """Typography and text formatting specification."""

    font_name: str = ""
    font_size: float = 0
    bold: bool = False
    italic: bool = False
    color: str = ""  # hex color
    alignment: str = "left"


class KeyMetric(BaseModel):
    """A single key performance metric with optional change indicator."""

    label: str
    value: str
    change: str = ""
    icon: str = ""


class StyledTable(BaseModel):
    """Table data with optional styling for headers and cells."""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    header_style: TextStyle | None = None
    cell_style: TextStyle | None = None
    alternating_rows: bool = False
    border_color: str = ""


class ImagePlacement(BaseModel):
    """Positioning and sizing for an image on a slide or page."""

    image_ref: str = ""
    file_path: str = ""
    width: float = 0.0
    height: float = 0.0
    left: float = 0.0
    top: float = 0.0
    alt_text: str = ""


class ContentBlock(BaseModel):
    """A block of content within a slide or section."""

    block_type: str = "text"  # text, bullets, metric, callout
    text: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    metric: KeyMetric | None = None
    style: TextStyle | None = None


class DataSeries(BaseModel):
    """A named series of data values for charts."""

    name: str
    values: list[float | int | str] = Field(default_factory=list)


class DataSet(BaseModel):
    """A complete dataset with categories and series for chart rendering."""

    name: str
    description: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[DataSeries] = Field(default_factory=list)
    suggested_chart_type: str = ""


class ImageRequest(BaseModel):
    """Request for an image from various sources."""

    name: str
    source_type: str  # ai_generate, url, file, stock
    prompt: str = ""
    url: str = ""
    file_path: str = ""
    alt_text: str = ""


class ContentSection(BaseModel):
    """A section of content within a ContentBrief."""

    heading: str = ""
    content: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    key_metrics: list[KeyMetric] = Field(default_factory=list)
    chart_ref: str = ""
    image_ref: str = ""
    table_data: StyledTable | None = None
    emphasis: str = "normal"
    speaker_notes: str = ""


class ContentBrief(BaseModel):
    """What other workers hand off: content plus context for design."""

    output_type: OutputType
    title: str
    sections: list[ContentSection] = Field(default_factory=list)
    audience: str = ""
    tone: str = ""
    purpose: str = ""
    reference_template: str = ""
    brand_colors: list[str] = Field(default_factory=list)
    brand_fonts: list[str] = Field(default_factory=list)
    datasets: list[DataSet] = Field(default_factory=list)
    image_requests: list[ImageRequest] = Field(default_factory=list)


class DesignProfile(BaseModel):
    """Design DNA extracted from reference templates."""

    primary_color: str = ""
    secondary_color: str = ""
    accent_color: str = ""
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    color_palette: list[str] = Field(default_factory=list)
    heading_font: str = ""
    body_font: str = ""
    font_sizes: dict[str, float] = Field(default_factory=dict)
    available_layouts: list[str] = Field(default_factory=list)
    preferred_layouts: dict[str, str] = Field(default_factory=dict)
    margins: dict[str, float] = Field(default_factory=dict)
    line_spacing: float = 1.15
    styles: list[str] = Field(default_factory=list)
    master_slide_names: list[str] = Field(default_factory=list)


class ResolvedChart(BaseModel):
    """A fully resolved chart ready for rendering."""

    chart_type: str  # bar, line, pie, scatter, area, waterfall, doughnut
    title: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[DataSeries] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    show_legend: bool = True
    show_data_labels: bool = False
    stacked: bool = False


class ResolvedImage(BaseModel):
    """A fully resolved image with binary data ready for embedding."""

    data: bytes = b""
    mime_type: str = "image/png"
    alt_text: str = ""
    width: float = 0.0
    height: float = 0.0


class SlideDesign(BaseModel):
    """Design specification for a single presentation slide."""

    layout: str = "Title and Content"
    title: str = ""
    subtitle: str = ""
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    chart_ref: str = ""
    image_ref: str = ""
    table: StyledTable | None = None
    speaker_notes: str = ""
    transition: str = ""
    title_style: TextStyle | None = None
    body_style: TextStyle | None = None
    background: str = ""
    images: list[ImagePlacement] = Field(default_factory=list)


class SectionDesign(BaseModel):
    """Design specification for a document section."""

    heading: str = ""
    heading_level: int = 1
    content: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    numbered_list: list[str] = Field(default_factory=list)
    chart_ref: str = ""
    image_ref: str = ""
    table: StyledTable | None = None
    callout: str = ""
    page_break_before: bool = False
    heading_style: TextStyle | None = None
    body_style: TextStyle | None = None
    images: list[ImagePlacement] = Field(default_factory=list)


class SheetDesign(BaseModel):
    """Design specification for a spreadsheet sheet."""

    name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    chart_ref: str = ""
    header_style: TextStyle | None = None
    cell_style: TextStyle | None = None
    column_widths: list[float] = Field(default_factory=list)
    number_formats: dict[str, str] = Field(default_factory=dict)


class DiagramSpec(BaseModel):
    """Specification for generating a diagram."""

    diagram_type: str = "flowchart"  # flowchart, architecture, sequence
    dot_source: str = ""  # DOT/Graphviz language source
    mermaid_source: str = ""  # Mermaid source (optional)
    title: str = ""


class DesignSpec(BaseModel):
    """Fully resolved design blueprint that tools render."""

    profile: DesignProfile
    output_type: OutputType
    slides: list[SlideDesign] = Field(default_factory=list)
    document_sections: list[SectionDesign] = Field(default_factory=list)
    sheets: list[SheetDesign] = Field(default_factory=list)
    charts: dict[str, ResolvedChart] = Field(default_factory=dict)
    images: dict[str, ResolvedImage] = Field(default_factory=dict)
