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


@tool_registry.register("google_sheets_spreadsheet", category="spreadsheet")
class GoogleSheetsTool(SpreadsheetPort):
    """Read, create, and modify Google Sheets via Sheets API v4."""

    def __init__(
        self,
        *,
        service_account_key: str = "",
        credentials_json: str = "",
        scopes: Sequence[str] = (
            "https://www.googleapis.com/auth/spreadsheets",
        ),
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
                "google-api-python-client and google-auth required. "
                "Install with: pip install firefly-dworkers[google]"
            )

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        self._ensure_deps()

        if self._service_account_key:
            creds = _sa.Credentials.from_service_account_file(
                self._service_account_key, scopes=self._scopes
            )
        elif self._credentials_json:
            import json

            info = json.loads(self._credentials_json)
            creds = _sa.Credentials.from_service_account_info(
                info, scopes=self._scopes
            )
        else:
            raise ConnectorAuthError(
                "GoogleSheetsTool requires service_account_key or credentials_json"
            )

        self._service = _build("sheets", "v4", credentials=creds)
        return self._service

    # -- port implementation ---------------------------------------------------

    async def _read_spreadsheet(
        self, source: str, sheet_name: str = ""
    ) -> WorkbookData:
        svc = self._get_service()
        # Get spreadsheet metadata
        meta = await asyncio.to_thread(
            lambda: svc.spreadsheets().get(spreadsheetId=source).execute()
        )

        sheet_titles = [
            s["properties"]["title"] for s in meta.get("sheets", [])
        ]
        target = (
            sheet_name
            if sheet_name in sheet_titles
            else (sheet_titles[0] if sheet_titles else "Sheet1")
        )

        # Get values from target sheet
        result = await asyncio.to_thread(
            lambda: svc.spreadsheets()
            .values()
            .get(spreadsheetId=source, range=target)
            .execute()
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
            "sheets": (
                [{"properties": {"title": spec.name}} for spec in sheets]
                if sheets
                else []
            ),
        }

        result = await asyncio.to_thread(
            lambda: svc.spreadsheets().create(body=body).execute()
        )
        spreadsheet_id = result["spreadsheetId"]

        # Write data to sheets
        for spec in sheets:
            if spec.headers or spec.rows:
                values: list[list[Any]] = []
                if spec.headers:
                    values.append(spec.headers)
                values.extend(spec.rows)
                await asyncio.to_thread(
                    lambda _n=spec.name, _v=values: svc.spreadsheets()
                    .values()
                    .update(
                        spreadsheetId=spreadsheet_id,
                        range=f"{_n}!A1",
                        valueInputOption="RAW",
                        body={"values": _v},
                    )
                    .execute()
                )

        return spreadsheet_id.encode("utf-8")

    async def _modify_spreadsheet(
        self, source: str, operations: list[SpreadsheetOperation]
    ) -> bytes:
        svc = self._get_service()

        for op in operations:
            if op.operation == "add_rows" and op.sheet_name:
                rows = op.data.get("rows", [])
                if rows:
                    await asyncio.to_thread(
                        lambda _sn=op.sheet_name, _r=rows: svc.spreadsheets()
                        .values()
                        .append(
                            spreadsheetId=source,
                            range=f"{_sn}!A1",
                            valueInputOption="RAW",
                            body={"values": _r},
                        )
                        .execute()
                    )
            elif op.operation == "add_sheet":
                sheet_title = op.data.get("name", "New Sheet")
                await asyncio.to_thread(
                    lambda _t=sheet_title: svc.spreadsheets()
                    .batchUpdate(
                        spreadsheetId=source,
                        body={
                            "requests": [
                                {
                                    "addSheet": {
                                        "properties": {"title": _t}
                                    }
                                }
                            ]
                        },
                    )
                    .execute()
                )

        return source.encode("utf-8")
