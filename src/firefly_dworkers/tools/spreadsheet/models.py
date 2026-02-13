"""Data models for spreadsheet tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from firefly_dworkers.design.models import TextStyle


class CellData(BaseModel):
    """Data for a single cell."""

    row: int
    col: int
    value: Any = None
    formula: str = ""
    formatted_value: str = ""


class SheetData(BaseModel):
    """Parsed data from a single sheet."""

    name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    col_count: int = 0


class WorkbookData(BaseModel):
    """Parsed data from a workbook."""

    sheets: list[SheetData] = Field(default_factory=list)
    active_sheet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CellSpec(BaseModel):
    """Specification for writing cell data."""

    row: int
    col: int
    value: Any = None
    formula: str = ""
    number_format: str = ""
    style: TextStyle | None = None


class SheetSpec(BaseModel):
    """Specification for creating a sheet."""

    name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    header_style: TextStyle | None = None
    cell_style: TextStyle | None = None
    column_widths: list[float] = Field(default_factory=list)
    number_formats: dict[str, str] = Field(default_factory=dict)
    chart: Any | None = None
    cells: list[CellSpec] = Field(default_factory=list)


class SpreadsheetOperation(BaseModel):
    """An operation to modify a spreadsheet."""

    operation: str  # add_sheet, remove_sheet, write_cells, add_rows
    sheet_name: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
