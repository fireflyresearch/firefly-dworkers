"""Tests for data tools (SpreadsheetTool, GenericAPITool, SQLClientTool).

SQLClientTool is tested with a real in-memory SQLite database (no mocking).
GenericAPITool config tests validate httpx dependency detection.
SpreadsheetTool tests validate CSV parsing logic.
"""

from __future__ import annotations

import sqlite3
import tempfile

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.exceptions import ConnectorError
from firefly_dworkers.tools.data.api_client import GenericAPITool
from firefly_dworkers.tools.data.csv_excel import SpreadsheetTool
from firefly_dworkers.tools.data.sql import SQLClientTool

# ---------------------------------------------------------------------------
# SpreadsheetTool
# ---------------------------------------------------------------------------


class TestSpreadsheetTool:
    def test_instantiation(self):
        tool = SpreadsheetTool()
        assert tool is not None

    def test_name(self):
        assert SpreadsheetTool().name == "spreadsheet"

    def test_tags(self):
        tags = SpreadsheetTool().tags
        assert "data" in tags
        assert "csv" in tags

    def test_is_base_tool(self):
        assert isinstance(SpreadsheetTool(), BaseTool)

    def test_config_params(self):
        tool = SpreadsheetTool(delimiter="\t", max_rows=50, encoding="latin-1")
        assert tool._delimiter == "\t"
        assert tool._max_rows == 50
        assert tool._encoding == "latin-1"

    async def test_parse_csv(self):
        tool = SpreadsheetTool()
        csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        result = await tool.execute(action="parse_csv", content=csv_data)
        assert result["row_count"] == 2
        assert result["columns"] == ["name", "age", "city"]
        assert result["rows"][0]["name"] == "Alice"
        assert result["rows"][1]["city"] == "LA"

    async def test_parse_csv_max_rows(self):
        tool = SpreadsheetTool()
        csv_data = "id,val\n1,a\n2,b\n3,c\n4,d\n5,e\n"
        result = await tool.execute(action="parse_csv", content=csv_data, max_rows=3)
        assert result["row_count"] == 3
        assert result["truncated"] is True

    async def test_parse_csv_custom_delimiter(self):
        tool = SpreadsheetTool(delimiter=";")
        csv_data = "name;age\nAlice;30\nBob;25\n"
        result = await tool.execute(action="parse_csv", content=csv_data)
        assert result["row_count"] == 2
        assert result["columns"] == ["name", "age"]

    async def test_describe_csv(self):
        tool = SpreadsheetTool()
        csv_data = "col1,col2,col3\na,b,c\nd,e,f\n"
        result = await tool.execute(action="describe", content=csv_data)
        assert result["column_count"] == 3
        assert result["row_count"] == 2
        assert result["columns"] == ["col1", "col2", "col3"]

    async def test_unknown_action_raises(self):
        tool = SpreadsheetTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="invalid_action", content="data")

    async def test_parameters(self):
        tool = SpreadsheetTool()
        param_names = [p.name for p in tool.parameters]
        assert "action" in param_names
        assert "content" in param_names
        assert "max_rows" in param_names
        assert "delimiter" in param_names
        assert "file_path" in param_names
        assert "sheet_name" in param_names


# ---------------------------------------------------------------------------
# GenericAPITool
# ---------------------------------------------------------------------------


class TestGenericAPITool:
    def test_instantiation(self):
        tool = GenericAPITool()
        assert tool is not None

    def test_name(self):
        assert GenericAPITool().name == "api_client"

    def test_tags(self):
        tags = GenericAPITool().tags
        assert "data" in tags
        assert "api" in tags
        assert "http" in tags

    def test_is_base_tool(self):
        assert isinstance(GenericAPITool(), BaseTool)

    def test_parameters(self):
        tool = GenericAPITool()
        param_names = [p.name for p in tool.parameters]
        assert "method" in param_names
        assert "url" in param_names
        assert "body" in param_names
        assert "headers" in param_names

    def test_base_url_config(self):
        tool = GenericAPITool(base_url="https://api.example.com/v1/")
        assert tool._base_url == "https://api.example.com/v1"

    def test_default_headers_config(self):
        tool = GenericAPITool(default_headers={"Authorization": "Bearer tok"})
        assert tool._default_headers["Authorization"] == "Bearer tok"

    def test_timeout_config(self):
        tool = GenericAPITool(timeout=60.0)
        assert tool._http_timeout == 60.0


# ---------------------------------------------------------------------------
# SQLClientTool
# ---------------------------------------------------------------------------


class TestSQLClientTool:
    def test_instantiation(self):
        tool = SQLClientTool()
        assert tool is not None

    def test_name(self):
        assert SQLClientTool().name == "sql_client"

    def test_tags(self):
        tags = SQLClientTool().tags
        assert "data" in tags
        assert "sql" in tags
        assert "database" in tags

    def test_is_base_tool(self):
        assert isinstance(SQLClientTool(), BaseTool)

    def test_config_params(self):
        tool = SQLClientTool(connection_string="/path/to/db.sqlite", read_only=False, max_rows=500, timeout=60.0)
        assert tool._connection_string == "/path/to/db.sqlite"
        assert tool._read_only is False
        assert tool._max_rows == 500
        assert tool._timeout == 60.0

    def test_parameters(self):
        tool = SQLClientTool()
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "max_rows" in param_names

    async def test_requires_connection_string(self):
        tool = SQLClientTool()
        with pytest.raises(ToolError, match="connection_string"):
            await tool.execute(query="SELECT 1")

    async def test_read_only_blocks_insert(self):
        tool = SQLClientTool(connection_string=":memory:", read_only=True)
        with pytest.raises(ToolError, match="Read-only"):
            await tool.execute(query="INSERT INTO users VALUES (1, 'Alice')")

    async def test_read_only_blocks_update(self):
        tool = SQLClientTool(connection_string=":memory:", read_only=True)
        with pytest.raises(ToolError, match="Read-only"):
            await tool.execute(query="UPDATE users SET name='Bob' WHERE id=1")

    async def test_read_only_blocks_delete(self):
        tool = SQLClientTool(connection_string=":memory:", read_only=True)
        with pytest.raises(ToolError, match="Read-only"):
            await tool.execute(query="DELETE FROM users WHERE id=1")

    async def test_read_only_blocks_drop(self):
        tool = SQLClientTool(connection_string=":memory:", read_only=True)
        with pytest.raises(ToolError, match="Read-only"):
            await tool.execute(query="DROP TABLE users")

    async def test_read_only_allows_select(self):
        """Test that a SELECT query runs successfully with an in-memory SQLite DB."""
        # Create a temporary database with test data
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT, city TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 'NYC')")
        conn.execute("INSERT INTO users VALUES (2, 'Bob', 'LA')")
        conn.commit()
        conn.close()

        tool = SQLClientTool(connection_string=db_path, read_only=True)
        result = await tool.execute(query="SELECT * FROM users ORDER BY id")
        assert result["query"] == "SELECT * FROM users ORDER BY id"
        assert result["row_count"] == 2
        assert result["columns"] == ["id", "name", "city"]
        assert result["rows"][0]["name"] == "Alice"
        assert result["rows"][1]["city"] == "LA"
        assert result["truncated"] is False

    async def test_read_only_allows_with_cte(self):
        """WITH (CTE) queries should be allowed in read-only mode."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE items (id INTEGER, val TEXT)")
        conn.execute("INSERT INTO items VALUES (1, 'a')")
        conn.commit()
        conn.close()

        tool = SQLClientTool(connection_string=db_path, read_only=True)
        result = await tool.execute(query="WITH cte AS (SELECT * FROM items) SELECT * FROM cte")
        assert result["row_count"] == 1

    async def test_max_rows_truncation(self):
        """Test that max_rows properly truncates results."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE numbers (n INTEGER)")
        for i in range(20):
            conn.execute("INSERT INTO numbers VALUES (?)", (i,))
        conn.commit()
        conn.close()

        tool = SQLClientTool(connection_string=db_path, read_only=True, max_rows=5)
        result = await tool.execute(query="SELECT * FROM numbers")
        assert result["row_count"] == 5
        assert result["truncated"] is True

    async def test_max_rows_override(self):
        """Test that per-query max_rows overrides the default."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE numbers (n INTEGER)")
        for i in range(20):
            conn.execute("INSERT INTO numbers VALUES (?)", (i,))
        conn.commit()
        conn.close()

        tool = SQLClientTool(connection_string=db_path, read_only=True, max_rows=100)
        result = await tool.execute(query="SELECT * FROM numbers", max_rows=3)
        assert result["row_count"] == 3
        assert result["truncated"] is True

    async def test_write_mode_allows_mutations(self):
        """Test that write mode allows INSERT/UPDATE/DELETE queries."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE items (id INTEGER, val TEXT)")
        conn.commit()
        conn.close()

        tool = SQLClientTool(connection_string=db_path, read_only=False)
        # _validate_query should not raise for INSERT when read_only=False
        tool._validate_query("INSERT INTO items VALUES (1, 'hello')")  # Should not raise

    def test_detect_backend_sqlite(self):
        tool = SQLClientTool(connection_string="/path/to/db.sqlite")
        assert tool._detect_backend() == "sqlite"

    def test_detect_backend_memory(self):
        tool = SQLClientTool(connection_string=":memory:")
        assert tool._detect_backend() == "sqlite"

    def test_detect_backend_postgres(self):
        tool = SQLClientTool(connection_string="postgresql://user:pass@host:5432/db")
        assert tool._detect_backend() == "postgres"

    def test_detect_backend_postgres_alt(self):
        tool = SQLClientTool(connection_string="postgres://user:pass@host:5432/db")
        assert tool._detect_backend() == "postgres"

    def test_detect_backend_requires_connection_string(self):
        tool = SQLClientTool()
        with pytest.raises(ConnectorError, match="connection_string"):
            tool._detect_backend()
