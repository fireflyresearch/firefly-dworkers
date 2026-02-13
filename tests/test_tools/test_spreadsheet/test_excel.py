"""Tests for ExcelTool adapter."""

from __future__ import annotations

import io
import os
import tempfile

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.excel import ExcelTool
from firefly_dworkers.tools.spreadsheet.models import SheetSpec, SpreadsheetOperation


class TestExcelToolRegistration:
    def test_is_spreadsheet_port(self) -> None:
        assert issubclass(ExcelTool, SpreadsheetPort)

    def test_is_base_tool(self) -> None:
        assert issubclass(ExcelTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("excel")
        assert tool_registry.get_class("excel") is ExcelTool

    def test_category(self) -> None:
        assert tool_registry.get_category("excel") == "spreadsheet"

    def test_name(self) -> None:
        assert ExcelTool().name == "excel"


class TestExcelToolRead:
    async def test_read_spreadsheet(self) -> None:
        openpyxl = pytest.importorskip("openpyxl")

        # Create a minimal .xlsx in memory
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Name", "Value"])
        ws.append(["Alice", 100])
        ws.append(["Bob", 200])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = ExcelTool()
            result = await tool.execute(action="read", source=tmp_path)
            assert "sheets" in result
            assert len(result["sheets"]) == 1
            assert result["sheets"][0]["name"] == "Data"
            assert result["sheets"][0]["headers"] == ["Name", "Value"]
            assert len(result["sheets"][0]["rows"]) == 2
            assert result["sheets"][0]["rows"][0] == ["Alice", 100]
            assert result["sheets"][0]["rows"][1] == ["Bob", 200]
            assert result["active_sheet"] == "Data"
        finally:
            os.unlink(tmp_path)

    async def test_read_specific_sheet(self) -> None:
        openpyxl = pytest.importorskip("openpyxl")

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Sheet1"
        ws1.append(["A", "B"])
        ws1.append([1, 2])

        ws2 = wb.create_sheet("Sheet2")
        ws2.append(["X", "Y"])
        ws2.append([10, 20])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = ExcelTool()
            result = await tool.execute(action="read", source=tmp_path, sheet_name="Sheet2")
            assert len(result["sheets"]) == 1
            assert result["sheets"][0]["name"] == "Sheet2"
            assert result["sheets"][0]["headers"] == ["X", "Y"]
        finally:
            os.unlink(tmp_path)


class TestExcelToolCreate:
    async def test_create_spreadsheet_basic(self) -> None:
        pytest.importorskip("openpyxl")
        tool = ExcelTool()
        sheets = [
            SheetSpec(name="Revenue", headers=["Q1", "Q2"], rows=[[100, 200]]).model_dump(),
            SheetSpec(name="Expenses", headers=["Q1", "Q2"], rows=[[50, 75]]).model_dump(),
        ]
        result = await tool.execute(action="create", sheets=sheets)
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_create_spreadsheet_roundtrip(self) -> None:
        pytest.importorskip("openpyxl")
        tool = ExcelTool()

        # Create via the tool's internal method to get bytes
        sheets = [SheetSpec(name="Data", headers=["Name", "Value"], rows=[["Alice", 1]])]
        data = await tool._create_spreadsheet(sheets)

        # Write to temp and read back
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        try:
            result = await tool.execute(action="read", source=tmp_path)
            assert result["sheets"][0]["name"] == "Data"
            assert result["sheets"][0]["headers"] == ["Name", "Value"]
            assert result["sheets"][0]["rows"][0] == ["Alice", 1]
        finally:
            os.unlink(tmp_path)

    async def test_create_multiple_sheets(self) -> None:
        openpyxl = pytest.importorskip("openpyxl")
        tool = ExcelTool()

        sheets = [
            SheetSpec(name="Sheet1", headers=["A"], rows=[[1]]),
            SheetSpec(name="Sheet2", headers=["B"], rows=[[2]]),
        ]
        data = await tool._create_spreadsheet(sheets)

        # Verify by loading with openpyxl directly
        wb = openpyxl.load_workbook(io.BytesIO(data))
        assert "Sheet1" in wb.sheetnames
        assert "Sheet2" in wb.sheetnames
        wb.close()


class TestExcelToolModify:
    async def test_modify_add_rows(self) -> None:
        openpyxl = pytest.importorskip("openpyxl")

        # Create source workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Name", "Value"])
        ws.append(["Alice", 100])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = ExcelTool()
            result = await tool.execute(
                action="modify",
                source=tmp_path,
                operations=[
                    {
                        "operation": "add_rows",
                        "sheet_name": "Data",
                        "data": {"rows": [["Bob", 200], ["Charlie", 300]]},
                    }
                ],
            )
            assert result["success"] is True
            assert result["bytes_length"] > 0
        finally:
            os.unlink(tmp_path)

    async def test_modify_add_sheet(self) -> None:
        openpyxl = pytest.importorskip("openpyxl")

        # Create source workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(buf.read())
            tmp_path = f.name

        try:
            tool = ExcelTool()
            data = await tool._modify_spreadsheet(
                tmp_path,
                [
                    SpreadsheetOperation(
                        operation="add_sheet",
                        data={"name": "NewSheet"},
                    )
                ],
            )

            # Verify the new sheet exists
            result_wb = openpyxl.load_workbook(io.BytesIO(data))
            assert "NewSheet" in result_wb.sheetnames
            result_wb.close()
        finally:
            os.unlink(tmp_path)
