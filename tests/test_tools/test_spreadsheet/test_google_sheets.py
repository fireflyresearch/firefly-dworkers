"""Tests for GoogleSheetsTool adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.design.models import TextStyle
from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.google_sheets import (
    GoogleSheetsTool,
    _build_column_width_requests,
    _build_header_style_request,
    _build_number_format_requests,
    _hex_to_rgb_sheets,
)
from firefly_dworkers.tools.spreadsheet.models import SheetSpec


class TestGoogleSheetsToolRegistration:
    def test_is_spreadsheet_port(self) -> None:
        assert issubclass(GoogleSheetsTool, SpreadsheetPort)

    def test_is_base_tool(self) -> None:
        assert issubclass(GoogleSheetsTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("google_sheets_spreadsheet")
        assert tool_registry.get_class("google_sheets_spreadsheet") is GoogleSheetsTool

    def test_category(self) -> None:
        assert tool_registry.get_category("google_sheets_spreadsheet") == "spreadsheet"

    def test_name(self) -> None:
        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        assert tool.name == "google_sheets"


class TestGoogleSheetsToolAuth:
    def test_requires_credentials(self) -> None:
        tool = GoogleSheetsTool()  # No credentials
        with pytest.raises((ConnectorAuthError, ImportError)):
            tool._get_service()

    def test_service_account_key_path(self) -> None:
        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        assert tool._service_account_key == "/fake/key.json"

    def test_credentials_json(self) -> None:
        tool = GoogleSheetsTool(credentials_json='{"type": "service_account"}')
        assert tool._credentials_json == '{"type": "service_account"}'


class TestHexToRgbSheets:
    def test_full_hex(self) -> None:
        result = _hex_to_rgb_sheets("#FF0000")
        assert abs(result["red"] - 1.0) < 0.01
        assert abs(result["green"]) < 0.01

    def test_short_hex(self) -> None:
        result = _hex_to_rgb_sheets("#00F")
        assert abs(result["blue"] - 1.0) < 0.01

    def test_no_hash(self) -> None:
        result = _hex_to_rgb_sheets("00FF00")
        assert abs(result["green"] - 1.0) < 0.01


class TestBuildHeaderStyleRequest:
    def test_with_full_style(self) -> None:
        style = TextStyle(font_name="Arial", font_size=12, bold=True, italic=True, color="#1A73E8")
        result = _build_header_style_request(0, style, 5)
        assert result is not None
        repeat = result["repeatCell"]
        assert repeat["range"]["sheetId"] == 0
        assert repeat["range"]["startRowIndex"] == 0
        assert repeat["range"]["endRowIndex"] == 1
        assert repeat["range"]["endColumnIndex"] == 5
        fmt = repeat["cell"]["userEnteredFormat"]
        assert fmt["textFormat"]["fontFamily"] == "Arial"
        assert fmt["textFormat"]["fontSize"] == 12
        assert fmt["textFormat"]["bold"] is True
        assert fmt["textFormat"]["italic"] is True
        assert "foregroundColorStyle" in fmt["textFormat"]
        assert "textFormat" in repeat["fields"]

    def test_with_font_only(self) -> None:
        style = TextStyle(font_name="Roboto")
        result = _build_header_style_request(1, style, 3)
        assert result is not None
        fmt = result["repeatCell"]["cell"]["userEnteredFormat"]
        assert fmt["textFormat"]["fontFamily"] == "Roboto"

    def test_empty_style_returns_none(self) -> None:
        style = TextStyle()
        result = _build_header_style_request(0, style, 5)
        assert result is None

    def test_non_textstyle_returns_none(self) -> None:
        result = _build_header_style_request(0, "not a style", 5)
        assert result is None

    def test_sheet_id_propagated(self) -> None:
        style = TextStyle(bold=True)
        result = _build_header_style_request(42, style, 2)
        assert result is not None
        assert result["repeatCell"]["range"]["sheetId"] == 42


class TestBuildColumnWidthRequests:
    def test_multiple_widths(self) -> None:
        result = _build_column_width_requests(0, [100, 200, 150])
        assert len(result) == 3
        assert result[0]["updateDimensionProperties"]["range"]["startIndex"] == 0
        assert result[0]["updateDimensionProperties"]["properties"]["pixelSize"] == 100
        assert result[1]["updateDimensionProperties"]["range"]["startIndex"] == 1
        assert result[1]["updateDimensionProperties"]["properties"]["pixelSize"] == 200
        assert result[2]["updateDimensionProperties"]["range"]["startIndex"] == 2

    def test_zero_width_skipped(self) -> None:
        result = _build_column_width_requests(0, [100, 0, 200])
        assert len(result) == 2
        indices = [r["updateDimensionProperties"]["range"]["startIndex"] for r in result]
        assert 0 in indices
        assert 2 in indices

    def test_empty_list(self) -> None:
        result = _build_column_width_requests(0, [])
        assert result == []

    def test_sheet_id_propagated(self) -> None:
        result = _build_column_width_requests(5, [120])
        assert result[0]["updateDimensionProperties"]["range"]["sheetId"] == 5


class TestBuildNumberFormatRequests:
    def test_valid_column_index(self) -> None:
        result = _build_number_format_requests(0, {"1": "$#,##0.00"}, col_count=3, row_count=10)
        assert len(result) == 1
        repeat = result[0]["repeatCell"]
        assert repeat["range"]["startRowIndex"] == 1
        assert repeat["range"]["endRowIndex"] == 11
        assert repeat["range"]["startColumnIndex"] == 1
        assert repeat["range"]["endColumnIndex"] == 2
        assert repeat["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == "$#,##0.00"

    def test_out_of_range_index_skipped(self) -> None:
        result = _build_number_format_requests(0, {"5": "#,##0"}, col_count=3, row_count=10)
        assert len(result) == 0

    def test_non_numeric_key_skipped(self) -> None:
        result = _build_number_format_requests(0, {"Revenue": "#,##0"}, col_count=3, row_count=10)
        assert len(result) == 0

    def test_multiple_formats(self) -> None:
        result = _build_number_format_requests(0, {"0": "#,##0", "2": "0.00%"}, col_count=3, row_count=5)
        assert len(result) == 2


class TestGoogleSheetsToolRead:
    async def test_read_spreadsheet_mocked(self) -> None:
        """Test read with mocked Google Sheets API."""
        mock_service = MagicMock()

        # Mock spreadsheet metadata
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [
                {"properties": {"title": "Sheet1"}},
                {"properties": {"title": "Sheet2"}},
            ],
        }

        # Mock values
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Name", "Value"],
                ["Alice", "100"],
                ["Bob", "200"],
            ],
        }

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_spreadsheet("fake-spreadsheet-id")
        assert len(result.sheets) == 1
        assert result.sheets[0].name == "Sheet1"
        assert result.sheets[0].headers == ["Name", "Value"]
        assert len(result.sheets[0].rows) == 2
        assert result.sheets[0].rows[0] == ["Alice", "100"]
        assert result.active_sheet == "Sheet1"

    async def test_read_specific_sheet_mocked(self) -> None:
        """Test reading a specific sheet by name."""
        mock_service = MagicMock()

        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [
                {"properties": {"title": "Sheet1"}},
                {"properties": {"title": "Revenue"}},
            ],
        }

        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Q1", "Q2"],
                ["100", "200"],
            ],
        }

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_spreadsheet("fake-id", sheet_name="Revenue")
        assert result.sheets[0].name == "Revenue"
        assert result.sheets[0].headers == ["Q1", "Q2"]

    async def test_read_empty_spreadsheet(self) -> None:
        """Test reading a spreadsheet with no data."""
        mock_service = MagicMock()

        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "Sheet1"}}],
        }

        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [],
        }

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_spreadsheet("fake-id")
        assert result.sheets[0].headers == []
        assert result.sheets[0].rows == []


class TestGoogleSheetsToolCreate:
    async def test_create_spreadsheet_mocked(self) -> None:
        """Test create with mocked Google Sheets API."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "new-sheet-id",
            "sheets": [{"properties": {"title": "Data", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [SheetSpec(name="Data", headers=["A", "B"], rows=[[1, 2]])]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"new-sheet-id"

    async def test_create_spreadsheet_empty(self) -> None:
        """Test creating an empty spreadsheet."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "empty-id",
            "sheets": [],
        }

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._create_spreadsheet([])
        assert result == b"empty-id"

    async def test_create_with_header_style(self) -> None:
        """Test that header_style produces repeatCell batch request."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "styled-sheet",
            "sheets": [{"properties": {"title": "Sales", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Sales",
                headers=["Product", "Revenue", "Margin"],
                rows=[["Widget", 1000, 0.2]],
                header_style=TextStyle(font_name="Arial", font_size=12, bold=True),
            )
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"styled-sheet"

        # Verify batchUpdate was called for formatting
        batch_calls = mock_service.spreadsheets.return_value.batchUpdate.call_args_list
        assert len(batch_calls) == 1
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        repeat_reqs = [r for r in reqs if "repeatCell" in r]
        assert len(repeat_reqs) >= 1
        header_req = repeat_reqs[0]["repeatCell"]
        assert header_req["range"]["startRowIndex"] == 0
        assert header_req["range"]["endRowIndex"] == 1
        assert header_req["range"]["endColumnIndex"] == 3
        fmt = header_req["cell"]["userEnteredFormat"]
        assert fmt["textFormat"]["fontFamily"] == "Arial"
        assert fmt["textFormat"]["bold"] is True

    async def test_create_with_column_widths(self) -> None:
        """Test that column_widths produce updateDimensionProperties requests."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "width-sheet",
            "sheets": [{"properties": {"title": "Data", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Data",
                headers=["Name", "Value"],
                rows=[["A", 1]],
                column_widths=[200, 150],
            )
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"width-sheet"

        batch_calls = mock_service.spreadsheets.return_value.batchUpdate.call_args_list
        assert len(batch_calls) == 1
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        dim_reqs = [r for r in reqs if "updateDimensionProperties" in r]
        assert len(dim_reqs) == 2
        assert dim_reqs[0]["updateDimensionProperties"]["properties"]["pixelSize"] == 200
        assert dim_reqs[1]["updateDimensionProperties"]["properties"]["pixelSize"] == 150

    async def test_create_with_number_formats(self) -> None:
        """Test that number_formats produce repeatCell requests for data columns."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "fmt-sheet",
            "sheets": [{"properties": {"title": "Finance", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Finance",
                headers=["Name", "Revenue", "Margin"],
                rows=[["Widget", 1000, 0.2], ["Gadget", 2000, 0.3]],
                number_formats={"1": "$#,##0.00", "2": "0.00%"},
            )
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"fmt-sheet"

        batch_calls = mock_service.spreadsheets.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        fmt_reqs = [r for r in reqs if "repeatCell" in r]
        assert len(fmt_reqs) == 2

        # Check revenue column format
        rev_req = [r for r in fmt_reqs if r["repeatCell"]["range"]["startColumnIndex"] == 1]
        assert len(rev_req) == 1
        assert rev_req[0]["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == "$#,##0.00"
        assert rev_req[0]["repeatCell"]["range"]["startRowIndex"] == 1
        assert rev_req[0]["repeatCell"]["range"]["endRowIndex"] == 3  # 2 data rows + header skip

        # Check margin column format
        margin_req = [r for r in fmt_reqs if r["repeatCell"]["range"]["startColumnIndex"] == 2]
        assert len(margin_req) == 1
        assert margin_req[0]["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == "0.00%"

    async def test_create_with_all_formatting(self) -> None:
        """Test creating with header style, column widths, and number formats together."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "all-fmt-sheet",
            "sheets": [{"properties": {"title": "Report", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Report",
                headers=["Category", "Amount"],
                rows=[["Sales", 5000]],
                header_style=TextStyle(bold=True, font_size=14),
                column_widths=[180, 120],
                number_formats={"1": "#,##0"},
            )
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"all-fmt-sheet"

        batch_calls = mock_service.spreadsheets.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # Should have: 1 repeatCell for header + 2 updateDimensionProperties + 1 repeatCell for number format = 4
        assert len(reqs) == 4

    async def test_create_without_formatting_no_batch_update(self) -> None:
        """Test that creating without formatting features doesn't call batchUpdate."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "plain-sheet",
            "sheets": [{"properties": {"title": "Data", "sheetId": 0}}],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Data",
                headers=["A", "B"],
                rows=[[1, 2]],
            )
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"plain-sheet"

        # batchUpdate should not be called since there's no formatting
        mock_service.spreadsheets.return_value.batchUpdate.assert_not_called()

    async def test_create_with_multiple_sheets_formatting(self) -> None:
        """Test formatting across multiple sheets."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "multi-sheet",
            "sheets": [
                {"properties": {"title": "Sales", "sheetId": 0}},
                {"properties": {"title": "Costs", "sheetId": 1}},
            ],
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sheets = [
            SheetSpec(
                name="Sales",
                headers=["Item", "Revenue"],
                rows=[["X", 100]],
                header_style=TextStyle(bold=True),
            ),
            SheetSpec(
                name="Costs",
                headers=["Item", "Cost"],
                rows=[["Y", 50]],
                column_widths=[200, 100],
            ),
        ]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"multi-sheet"

        batch_calls = mock_service.spreadsheets.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # 1 repeatCell for Sales headers + 2 updateDimensionProperties for Costs columns
        assert len(reqs) == 3

        # Verify different sheet IDs
        repeat_reqs = [r for r in reqs if "repeatCell" in r]
        assert repeat_reqs[0]["repeatCell"]["range"]["sheetId"] == 0

        dim_reqs = [r for r in reqs if "updateDimensionProperties" in r]
        for dr in dim_reqs:
            assert dr["updateDimensionProperties"]["range"]["sheetId"] == 1


class TestGoogleSheetsToolModify:
    async def test_modify_add_rows(self) -> None:
        """Test modify with add_rows operation."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.spreadsheet.models import SpreadsheetOperation

        ops = [
            SpreadsheetOperation(
                operation="add_rows",
                sheet_name="Sheet1",
                data={"rows": [["Charlie", 300]]},
            )
        ]
        result = await tool._modify_spreadsheet("sheet-id", ops)
        assert result == b"sheet-id"

    async def test_modify_add_sheet(self) -> None:
        """Test modify with add_sheet operation."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.spreadsheet.models import SpreadsheetOperation

        ops = [
            SpreadsheetOperation(
                operation="add_sheet",
                data={"name": "New Sheet"},
            )
        ]
        result = await tool._modify_spreadsheet("sheet-id", ops)
        assert result == b"sheet-id"

    async def test_modify_no_operations(self) -> None:
        """Test modify with no operations."""
        mock_service = MagicMock()

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._modify_spreadsheet("sheet-id", [])
        assert result == b"sheet-id"
