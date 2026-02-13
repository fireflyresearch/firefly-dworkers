"""Google Sheets adapter for SpreadsheetPort."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.models import (
    SheetData,
    SheetSpec,
    SpreadsheetOperation,
    WorkbookData,
)

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account as _sa
    from googleapiclient.discovery import build as _build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


def _hex_to_rgb_sheets(hex_color: str) -> dict[str, float]:
    """Convert a hex color string (e.g. '#1A73E8') to Google Sheets API color dict."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0,
    }


def _build_header_style_request(
    sheet_id: int,
    header_style: Any,
    col_count: int,
) -> dict[str, Any] | None:
    """Build a repeatCell request for header row styling."""
    from firefly_dworkers.design.models import TextStyle

    if not isinstance(header_style, TextStyle):
        return None

    text_format: dict[str, Any] = {}
    user_format: dict[str, Any] = {}
    format_parts: list[str] = []

    if header_style.font_name:
        text_format["fontFamily"] = header_style.font_name
    if header_style.font_size:
        text_format["fontSize"] = int(header_style.font_size)
    if header_style.bold:
        text_format["bold"] = True
    if header_style.italic:
        text_format["italic"] = True
    if header_style.color:
        text_format["foregroundColorStyle"] = {
            "rgbColor": _hex_to_rgb_sheets(header_style.color)
        }

    if text_format:
        user_format["textFormat"] = text_format
        format_parts.append("textFormat")

    if not format_parts:
        return None

    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": col_count,
            },
            "cell": {
                "userEnteredFormat": user_format,
            },
            "fields": "userEnteredFormat(" + ",".join(format_parts) + ")",
        }
    }


def _build_column_width_requests(
    sheet_id: int,
    column_widths: list[float],
) -> list[dict[str, Any]]:
    """Build updateDimensionProperties requests for column widths."""
    requests: list[dict[str, Any]] = []
    for i, width in enumerate(column_widths):
        if width > 0:
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": i,
                            "endIndex": i + 1,
                        },
                        "properties": {"pixelSize": int(width)},
                        "fields": "pixelSize",
                    }
                }
            )
    return requests


def _build_number_format_requests(
    sheet_id: int,
    number_formats: dict[str, str],
    col_count: int,
    row_count: int,
) -> list[dict[str, Any]]:
    """Build repeatCell requests for number formats.

    ``number_formats`` maps column name or index (as string) to a Sheets
    number format pattern (e.g. ``"$#,##0.00"``).  Column names are resolved
    by matching against the header list, but callers may also pass
    zero-based column indices as strings (e.g. ``"0"``, ``"2"``).
    """
    requests: list[dict[str, Any]] = []
    for col_key, fmt in number_formats.items():
        # Accept either an integer index or treat it as a column index string
        try:
            col_idx = int(col_key)
        except ValueError:
            continue  # column name resolution not available at this level
        if col_idx < 0 or col_idx >= col_count:
            continue
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,  # skip header
                        "endRowIndex": row_count + 1,  # data rows
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": fmt,
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
        )
    return requests


@tool_registry.register("google_sheets_spreadsheet", category="spreadsheet")
class GoogleSheetsTool(SpreadsheetPort):
    """Read, create, and modify Google Sheets via Sheets API v4."""

    def __init__(
        self,
        *,
        service_account_key: str = "",
        credentials_json: str = "",
        scopes: Sequence[str] = ("https://www.googleapis.com/auth/spreadsheets",),
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "google_sheets",
            description="Read, create, and modify Google Sheets.",
            timeout=timeout,
            guards=guards,
        )
        self._service_account_key = service_account_key
        self._credentials_json = credentials_json
        self._scopes = list(scopes)
        self._service: Any | None = None

    def _ensure_deps(self) -> None:
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-api-python-client and google-auth required. Install with: pip install firefly-dworkers[google]"
            )

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        self._ensure_deps()

        if self._service_account_key:
            creds = _sa.Credentials.from_service_account_file(self._service_account_key, scopes=self._scopes)
        elif self._credentials_json:
            import json

            info = json.loads(self._credentials_json)
            creds = _sa.Credentials.from_service_account_info(info, scopes=self._scopes)
        else:
            raise ConnectorAuthError("GoogleSheetsTool requires service_account_key or credentials_json")

        self._service = _build("sheets", "v4", credentials=creds)
        return self._service

    # -- port implementation ---------------------------------------------------

    async def _read_spreadsheet(self, source: str, sheet_name: str = "") -> WorkbookData:
        svc = self._get_service()
        # Get spreadsheet metadata
        meta = await asyncio.to_thread(lambda: svc.spreadsheets().get(spreadsheetId=source).execute())

        sheet_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
        target = sheet_name if sheet_name in sheet_titles else (sheet_titles[0] if sheet_titles else "Sheet1")

        # Get values from target sheet
        result = await asyncio.to_thread(
            lambda: svc.spreadsheets().values().get(spreadsheetId=source, range=target).execute()
        )

        values = result.get("values", [])
        headers = values[0] if values else []
        rows = values[1:] if len(values) > 1 else []

        return WorkbookData(
            sheets=[
                SheetData(
                    name=target,
                    headers=headers,
                    rows=rows,
                    row_count=len(rows),
                    col_count=len(headers),
                )
            ],
            active_sheet=target,
        )

    async def _create_spreadsheet(self, sheets: list[SheetSpec]) -> bytes:
        svc = self._get_service()
        body: dict[str, Any] = {
            "properties": {"title": "Untitled Spreadsheet"},
            "sheets": ([{"properties": {"title": spec.name}} for spec in sheets] if sheets else []),
        }

        result = await asyncio.to_thread(lambda: svc.spreadsheets().create(body=body).execute())
        spreadsheet_id = result["spreadsheetId"]

        # Resolve sheet IDs from the create response
        sheet_id_map: dict[str, int] = {}
        for sheet_meta in result.get("sheets", []):
            props = sheet_meta.get("properties", {})
            sheet_id_map[props.get("title", "")] = props.get("sheetId", 0)

        # Write data to sheets
        for spec in sheets:
            if spec.headers or spec.rows:
                values: list[list[Any]] = []
                if spec.headers:
                    values.append(spec.headers)
                values.extend(spec.rows)
                await asyncio.to_thread(
                    lambda _n=spec.name, _v=values: (
                        svc.spreadsheets()
                        .values()
                        .update(
                            spreadsheetId=spreadsheet_id,
                            range=f"{_n}!A1",
                            valueInputOption="RAW",
                            body={"values": _v},
                        )
                        .execute()
                    )
                )

        # Build formatting requests for all sheets
        format_requests: list[dict[str, Any]] = []
        for spec in sheets:
            sid = sheet_id_map.get(spec.name, 0)
            col_count = len(spec.headers) if spec.headers else 0

            # --- Header styling ---
            if spec.header_style and col_count > 0:
                req = _build_header_style_request(sid, spec.header_style, col_count)
                if req:
                    format_requests.append(req)

            # --- Column widths ---
            if spec.column_widths:
                format_requests.extend(
                    _build_column_width_requests(sid, spec.column_widths)
                )

            # --- Number formats ---
            if spec.number_formats and col_count > 0:
                format_requests.extend(
                    _build_number_format_requests(
                        sid,
                        spec.number_formats,
                        col_count,
                        len(spec.rows),
                    )
                )

        if format_requests:
            await asyncio.to_thread(
                lambda: (
                    svc.spreadsheets()
                    .batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": format_requests},
                    )
                    .execute()
                )
            )

        return spreadsheet_id.encode("utf-8")

    async def _modify_spreadsheet(self, source: str, operations: list[SpreadsheetOperation]) -> bytes:
        svc = self._get_service()

        for op in operations:
            if op.operation == "add_rows" and op.sheet_name:
                rows = op.data.get("rows", [])
                if rows:
                    await asyncio.to_thread(
                        lambda _sn=op.sheet_name, _r=rows: (
                            svc.spreadsheets()
                            .values()
                            .append(
                                spreadsheetId=source,
                                range=f"{_sn}!A1",
                                valueInputOption="RAW",
                                body={"values": _r},
                            )
                            .execute()
                        )
                    )
            elif op.operation == "add_sheet":
                sheet_title = op.data.get("name", "New Sheet")
                await asyncio.to_thread(
                    lambda _t=sheet_title: (
                        svc.spreadsheets()
                        .batchUpdate(
                            spreadsheetId=source,
                            body={"requests": [{"addSheet": {"properties": {"title": _t}}}]},
                        )
                        .execute()
                    )
                )

        return source.encode("utf-8")
