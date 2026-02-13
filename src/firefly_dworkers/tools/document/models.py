"""Data models for document tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from firefly_dworkers.design.models import ImagePlacement, TextStyle


class TableData(BaseModel):
    """Table specification for documents."""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class SectionSpec(BaseModel):
    """Specification for a document section."""

    heading: str = ""
    heading_level: int = 1
    content: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    table: TableData | None = None
    page_break_before: bool = False
    heading_style: TextStyle | None = None
    body_style: TextStyle | None = None
    chart: Any | None = None
    images: list[ImagePlacement] = Field(default_factory=list)
    callout: str = ""
    numbered_list: list[str] = Field(default_factory=list)


class ParagraphData(BaseModel):
    """Parsed paragraph from a document."""

    text: str
    style: str = ""
    is_heading: bool = False
    heading_level: int = 0


class DocumentData(BaseModel):
    """Parsed data from a document."""

    title: str = ""
    paragraphs: list[ParagraphData] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    styles: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    color_theme: dict[str, str] = Field(default_factory=dict)


class DocumentOperation(BaseModel):
    """An operation to modify a document."""

    operation: str  # add_section, remove_section, update_content
    section_index: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
