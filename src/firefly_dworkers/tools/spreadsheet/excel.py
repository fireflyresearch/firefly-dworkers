"""Excel adapter for SpreadsheetPort."""

from __future__ import annotations

import asyncio
import io
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.models import (
    SheetData,
    SheetSpec,
    SpreadsheetOperation,
    WorkbookData,
)

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def _require_openpyxl() -> None:
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl required: pip install firefly-dworkers[data]")


@tool_registry.register("excel", category="spreadsheet")
class ExcelTool(SpreadsheetPort):
    """Read, create, and modify Excel (.xlsx) workbooks using openpyxl."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "excel",
            description="Read, create, and modify Excel (.xlsx) workbooks.",
            timeout=timeout,
            guards=guards,
        )

    async def _read_spreadsheet(
        self, source: str, sheet_name: str = ""
    ) -> WorkbookData:
        _require_openpyxl()
        return await asyncio.to_thread(self._read_sync, source, sheet_name)

    async def _create_spreadsheet(self, sheets: list[SheetSpec]) -> bytes:
        _require_openpyxl()
        return await asyncio.to_thread(self._create_sync, sheets)

    async def _modify_spreadsheet(
        self, source: str, operations: list[SpreadsheetOperation]
    ) -> bytes:
        _require_openpyxl()
        return await asyncio.to_thread(self._modify_sync, source, operations)

    # -- synchronous helpers ---------------------------------------------------

    def _read_sync(self, source: str, sheet_name: str) -> WorkbookData:
        wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
        sheets: list[SheetData] = []

        target_sheets = (
            [wb[sheet_name]]
            if sheet_name and sheet_name in wb.sheetnames
            else [wb.active]
        )

        for ws in target_sheets:
            headers: list[str] = []
            rows: list[list[Any]] = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    headers = [
                        str(c) if c is not None else f"col_{j}"
                        for j, c in enumerate(row)
                    ]
                else:
                    rows.append(list(row))

            sheets.append(
                SheetData(
                    name=ws.title or "",
                    headers=headers,
                    rows=rows,
                    row_count=len(rows),
                    col_count=len(headers),
                )
            )

        active_name = wb.active.title if wb.active else ""
        wb.close()

        return WorkbookData(
            sheets=sheets,
            active_sheet=active_name,
        )

    def _create_sync(self, sheets: list[SheetSpec]) -> bytes:
        wb = openpyxl.Workbook()
        # Remove the default sheet
        if wb.active:
            wb.remove(wb.active)

        for spec in sheets:
            ws = wb.create_sheet(title=spec.name)
            if spec.headers:
                ws.append(spec.headers)
            for row in spec.rows:
                ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _modify_sync(
        self, source: str, operations: list[SpreadsheetOperation]
    ) -> bytes:
        wb = openpyxl.load_workbook(source)

        for op in operations:
            if op.operation == "add_sheet":
                name = op.data.get("name", "Sheet")
                wb.create_sheet(title=name)
            elif op.operation == "add_rows":
                ws_name = op.sheet_name or (
                    wb.active.title if wb.active else ""
                )
                ws = wb[ws_name]
                for row in op.data.get("rows", []):
                    ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
