"""Tests for GoogleSheetsTool adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.spreadsheet.base import SpreadsheetPort
from firefly_dworkers.tools.spreadsheet.google_sheets import GoogleSheetsTool


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
        }
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {}

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.spreadsheet.models import SheetSpec

        sheets = [SheetSpec(name="Data", headers=["A", "B"], rows=[[1, 2]])]
        result = await tool._create_spreadsheet(sheets)
        assert result == b"new-sheet-id"

    async def test_create_spreadsheet_empty(self) -> None:
        """Test creating an empty spreadsheet."""
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "empty-id",
        }

        tool = GoogleSheetsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._create_spreadsheet([])
        assert result == b"empty-id"


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
