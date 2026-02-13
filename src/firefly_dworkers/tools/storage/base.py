"""DocumentStorageTool — abstract base for document storage providers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from pydantic import BaseModel


class DocumentResult(BaseModel):
    """Represents a document returned from a storage provider."""

    id: str
    name: str
    path: str = ""
    content: str = ""
    content_type: str = ""
    size_bytes: int = 0
    modified_at: str = ""
    url: str = ""


class DocumentStorageTool(BaseTool):
    """Abstract base for document storage tools.

    Subclasses must implement :meth:`_search`, :meth:`_read`, :meth:`_list`,
    and :meth:`_write` to provide access to a specific storage provider
    (e.g. SharePoint, Google Drive, Confluence).
    """

    def __init__(self, name: str, *, description: str = "", guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            name,
            description=description or f"Access documents via {name}",
            tags=["storage", "documents", name],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="action",
                    type_annotation="str",
                    description="One of: search, read, list, write",
                    required=True,
                ),
                ParameterSpec(
                    name="path",
                    type_annotation="str",
                    description="File or folder path",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="query",
                    type_annotation="str",
                    description="Search query (for search action)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="content",
                    type_annotation="str",
                    description="Content to write (for write action)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="resource_id",
                    type_annotation="str",
                    description="Resource ID (for read action)",
                    required=False,
                    default="",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        if action == "search":
            results = await self._search(kwargs.get("query", ""))
            return [r.model_dump() for r in results]
        if action == "read":
            result = await self._read(kwargs.get("resource_id", ""), kwargs.get("path", ""))
            return result.model_dump()
        if action == "list":
            results = await self._list(kwargs.get("path", ""))
            return [r.model_dump() for r in results]
        if action == "write":
            result = await self._write(kwargs.get("path", ""), kwargs.get("content", ""))
            return result.model_dump()
        raise ValueError(f"Unknown action '{action}'; expected search, read, list, or write")

    @abstractmethod
    async def _search(self, query: str) -> list[DocumentResult]: ...

    @abstractmethod
    async def _read(self, resource_id: str, path: str) -> DocumentResult: ...

    @abstractmethod
    async def _list(self, path: str) -> list[DocumentResult]: ...

    @abstractmethod
    async def _write(self, path: str, content: str) -> DocumentResult: ...
