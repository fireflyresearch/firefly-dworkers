"""Tests for SpreadsheetPort abstract base."""

from __future__ import annotations

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.models import (
    CellData,
    CellSpec,
    SheetData,
    SheetSpec,
    SpreadsheetOperation,
    WorkbookData,
)


class FakeSpreadsheetTool(SpreadsheetPort):
    """Concrete implementation for testing the abstract base."""

    async def _read_spreadsheet(self, source, sheet_name=""):
        return WorkbookData(
            sheets=[SheetData(
                name="Sheet1",
                headers=["Name", "Value"],
                rows=[["Alice", 1], ["Bob", 2]],
                row_count=2,
                col_count=2,
            )],
            active_sheet="Sheet1",
        )

    async def _create_spreadsheet(self, sheets):
        return b"fake-xlsx-bytes"

    async def _modify_spreadsheet(self, source, operations):
        return b"modified-xlsx-bytes"


class TestSpreadsheetPort:
    def test_is_base_tool(self) -> None:
        assert isinstance(FakeSpreadsheetTool(), BaseTool)

    def test_is_spreadsheet_port(self) -> None:
        assert isinstance(FakeSpreadsheetTool(), SpreadsheetPort)

    def test_default_name(self) -> None:
        assert FakeSpreadsheetTool().name == "spreadsheet_port"

    def test_tags(self) -> None:
        tags = FakeSpreadsheetTool().tags
        assert "spreadsheet" in tags
        assert "data" in tags

    def test_parameters(self) -> None:
        param_names = [p.name for p in FakeSpreadsheetTool().parameters]
        assert "action" in param_names
        assert "source" in param_names
        assert "sheet_name" in param_names
        assert "sheets" in param_names
        assert "operations" in param_names

    async def test_execute_read(self) -> None:
        tool = FakeSpreadsheetTool()
        result = await tool.execute(action="read", source="test.xlsx")
        assert isinstance(result, dict)
        assert "sheets" in result
        assert result["active_sheet"] == "Sheet1"
        assert len(result["sheets"]) == 1
        assert result["sheets"][0]["headers"] == ["Name", "Value"]

    async def test_execute_create(self) -> None:
        tool = FakeSpreadsheetTool()
        sheets = [SheetSpec(name="Data", headers=["A", "B"], rows=[[1, 2]])]
        result = await tool.execute(
            action="create", sheets=[s.model_dump() for s in sheets]
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_execute_modify(self) -> None:
        tool = FakeSpreadsheetTool()
        ops = [SpreadsheetOperation(operation="add_rows", sheet_name="Sheet1", data={"rows": [[3, 4]]})]
        result = await tool.execute(
            action="modify",
            source="test.xlsx",
            operations=[o.model_dump() for o in ops],
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_execute_unknown_action_raises(self) -> None:
        tool = FakeSpreadsheetTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="unknown", source="test.xlsx")


class TestSpreadsheetModels:
    def test_cell_data(self) -> None:
        cell = CellData(row=0, col=0, value="hello", formula="", formatted_value="hello")
        assert cell.row == 0
        assert cell.col == 0
        assert cell.value == "hello"

    def test_cell_data_defaults(self) -> None:
        cell = CellData(row=1, col=2)
        assert cell.value is None
        assert cell.formula == ""
        assert cell.formatted_value == ""

    def test_sheet_data_defaults(self) -> None:
        sheet = SheetData(name="Sheet1")
        assert sheet.headers == []
        assert sheet.rows == []
        assert sheet.row_count == 0
        assert sheet.col_count == 0

    def test_sheet_data_with_data(self) -> None:
        sheet = SheetData(
            name="Data",
            headers=["Name", "Value"],
            rows=[["A", 1], ["B", 2]],
            row_count=2,
            col_count=2,
        )
        assert len(sheet.rows) == 2
        assert sheet.headers == ["Name", "Value"]

    def test_workbook_data_defaults(self) -> None:
        wb = WorkbookData()
        assert wb.sheets == []
        assert wb.active_sheet == ""
        assert wb.metadata == {}

    def test_workbook_data_with_sheets(self) -> None:
        wb = WorkbookData(
            sheets=[SheetData(name="S1"), SheetData(name="S2")],
            active_sheet="S1",
        )
        assert len(wb.sheets) == 2
        assert wb.active_sheet == "S1"

    def test_cell_spec(self) -> None:
        spec = CellSpec(row=0, col=0, value="hello")
        assert spec.value == "hello"
        assert spec.formula == ""

    def test_cell_spec_with_formula(self) -> None:
        spec = CellSpec(row=0, col=0, formula="=SUM(A1:A10)")
        assert spec.formula == "=SUM(A1:A10)"

    def test_sheet_spec(self) -> None:
        spec = SheetSpec(name="Revenue", headers=["Q1", "Q2"], rows=[[100, 200]])
        assert spec.name == "Revenue"
        assert spec.headers == ["Q1", "Q2"]
        assert len(spec.rows) == 1

    def test_sheet_spec_defaults(self) -> None:
        spec = SheetSpec(name="Empty")
        assert spec.headers == []
        assert spec.rows == []

    def test_spreadsheet_operation(self) -> None:
        op = SpreadsheetOperation(
            operation="add_rows",
            sheet_name="Sheet1",
            data={"rows": [[1, 2, 3]]},
        )
        assert op.operation == "add_rows"
        assert op.sheet_name == "Sheet1"
        assert op.data["rows"] == [[1, 2, 3]]

    def test_spreadsheet_operation_defaults(self) -> None:
        op = SpreadsheetOperation(operation="add_sheet")
        assert op.sheet_name == ""
        assert op.data == {}
