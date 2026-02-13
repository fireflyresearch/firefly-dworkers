"""SQLClientTool — execute SQL queries against databases.

Supports SQLite (via ``aiosqlite``), PostgreSQL (via ``asyncpg``), and
generic DBAPI connections (via ``asyncio.to_thread``).

For SQLite, install ``aiosqlite``.  For PostgreSQL, install ``asyncpg``.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError

logger = logging.getLogger(__name__)

try:
    import aiosqlite

    AIOSQLITE_AVAILABLE = True
except ImportError:
    aiosqlite = None  # type: ignore[assignment]
    AIOSQLITE_AVAILABLE = False

try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None  # type: ignore[assignment]
    ASYNCPG_AVAILABLE = False


class SQLClientTool(BaseTool):
    """Execute SQL queries against a configured database.

    Configuration parameters:

    * ``connection_string`` -- Database connection string.
      - For SQLite: path to the ``.db`` file (e.g. ``/data/app.db`` or ``:memory:``).
      - For PostgreSQL: ``postgresql://user:pass@host:port/dbname``.
    * ``read_only`` -- If ``True``, only SELECT queries are allowed.
    * ``max_rows`` -- Maximum rows to return from a query.
    * ``timeout`` -- Query timeout in seconds.
    """

    def __init__(
        self,
        *,
        connection_string: str = "",
        read_only: bool = True,
        max_rows: int = 1000,
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(
            "sql_client",
            description="Execute SQL queries against a database",
            tags=["data", "sql", "database"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="query",
                    type_annotation="str",
                    description="SQL query to execute",
                    required=True,
                ),
                ParameterSpec(
                    name="max_rows",
                    type_annotation="int",
                    description="Maximum rows to return",
                    required=False,
                    default=max_rows,
                ),
            ],
        )
        self._connection_string = connection_string
        self._read_only = read_only
        self._max_rows = max_rows
        self._timeout = timeout

    def _detect_backend(self) -> str:
        cs = self._connection_string
        if not cs:
            raise ConnectorError("SQLClientTool requires connection_string")
        if cs.startswith("postgresql://") or cs.startswith("postgres://"):
            return "postgres"
        return "sqlite"

    def _validate_query(self, query: str) -> None:
        if self._read_only:
            normalized = query.strip().upper()
            if not normalized.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA", "SHOW", "DESCRIBE")):
                raise ConnectorError(
                    f"Read-only mode: only SELECT/WITH queries are allowed, got '{normalized[:20]}...'"
                )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs["query"]
        max_rows = kwargs.get("max_rows", self._max_rows)
        self._validate_query(query)

        backend = self._detect_backend()
        if backend == "sqlite":
            return await self._execute_sqlite(query, max_rows)
        if backend == "postgres":
            return await self._execute_postgres(query, max_rows)
        raise ConnectorError(f"Unsupported database backend: {backend}")

    async def _execute_sqlite(self, query: str, max_rows: int) -> dict[str, Any]:
        if AIOSQLITE_AVAILABLE:
            return await self._execute_sqlite_async(query, max_rows)
        return await self._execute_sqlite_sync(query, max_rows)

    async def _execute_sqlite_async(self, query: str, max_rows: int) -> dict[str, Any]:
        async with aiosqlite.connect(self._connection_string) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = await cursor.fetchmany(max_rows)
            rows = [dict(row) for row in raw_rows]
            return {
                "query": query,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(rows) >= max_rows,
            }

    async def _execute_sqlite_sync(self, query: str, max_rows: int) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            conn = sqlite3.connect(self._connection_string)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(query)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                raw_rows = cursor.fetchmany(max_rows)
                rows = [dict(row) for row in raw_rows]
                return {
                    "query": query,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": len(rows) >= max_rows,
                }
            finally:
                conn.close()

        return await asyncio.to_thread(_run)

    async def _execute_postgres(self, query: str, max_rows: int) -> dict[str, Any]:
        if not ASYNCPG_AVAILABLE:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. "
                "Install with: pip install asyncpg"
            )
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(self._connection_string),
                timeout=self._timeout,
            )
        except Exception as exc:
            raise ConnectorAuthError(f"PostgreSQL connection failed: {exc}") from exc

        try:
            records = await conn.fetch(query)
            rows = [dict(r) for r in records[:max_rows]]
            columns = list(rows[0].keys()) if rows else []
            return {
                "query": query,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(records) > max_rows,
            }
        finally:
            await conn.close()
