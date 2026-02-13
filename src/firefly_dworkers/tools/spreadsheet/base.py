"""Abstract port for spreadsheet tools."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.tools.spreadsheet.models import (
    SheetSpec,
    SpreadsheetOperation,
    WorkbookData,
)


class SpreadsheetPort(BaseTool):
    """Abstract port for spreadsheet tools (Excel, Google Sheets)."""

    def __init__(
        self,
        name: str = "spreadsheet_port",
        *,
        description: str = "",
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
        extra_parameters: Sequence[ParameterSpec] = (),
    ) -> None:
        params = [
            ParameterSpec(
                name="action",
                type_annotation="str",
                description="Action: read, create, or modify.",
                required=True,
            ),
            ParameterSpec(
                name="source",
                type_annotation="str",
                description="File path or spreadsheet ID.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="sheet_name",
                type_annotation="str",
                description="Sheet name to read from.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="sheets",
                type_annotation="list",
                description="List of SheetSpec dicts for creating spreadsheets.",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="operations",
                type_annotation="list",
                description="List of SpreadsheetOperation dicts.",
                required=False,
                default=[],
            ),
            *extra_parameters,
        ]
        super().__init__(
            name,
            description=description or "Create, read, and modify spreadsheets.",
            tags=["spreadsheet", "data"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action = kwargs.get("action", "read")
        if action == "read":
            source = kwargs["source"]
            sheet_name = kwargs.get("sheet_name", "")
            result = await self._read_spreadsheet(source, sheet_name)
            return result.model_dump()
        elif action == "create":
            sheets_raw = kwargs.get("sheets", [])
            sheets = [SheetSpec.model_validate(s) for s in sheets_raw]
            data = await self._create_spreadsheet(sheets)
            return {"bytes_length": len(data), "success": True}
        elif action == "modify":
            source = kwargs["source"]
            ops_raw = kwargs.get("operations", [])
            ops = [SpreadsheetOperation.model_validate(o) for o in ops_raw]
            data = await self._modify_spreadsheet(source, ops)
            return {"bytes_length": len(data), "success": True}
        else:
            raise ValueError(f"Unknown action: {action}")

    @abstractmethod
    async def _read_spreadsheet(self, source: str, sheet_name: str = "") -> WorkbookData: ...

    @abstractmethod
    async def _create_spreadsheet(self, sheets: list[SheetSpec]) -> bytes: ...

    @abstractmethod
    async def _modify_spreadsheet(self, source: str, operations: list[SpreadsheetOperation]) -> bytes: ...
