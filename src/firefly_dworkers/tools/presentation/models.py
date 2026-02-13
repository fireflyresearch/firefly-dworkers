"""Data models for presentation tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TableSpec(BaseModel):
    """Specification for a table in a slide or document."""

    headers: list[str]
    rows: list[list[str]]


class ChartSpec(BaseModel):
    """Specification for a chart in a slide or document."""

    chart_type: str  # bar, line, pie, scatter, area
    title: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[dict[str, Any]] = Field(default_factory=list)  # [{"name": str, "values": list}]


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
