"""Tests for DocumentStorageTool abstract base."""

from __future__ import annotations

import pytest

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool


class FakeStorageTool(DocumentStorageTool):
    """Concrete implementation for testing."""

    async def _search(self, query: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="doc-1",
                name=f"Result for {query}",
                path="/docs/result.txt",
                content=f"Content about {query}",
            )
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        return DocumentResult(
            id=resource_id,
            name="test.txt",
            path=path or "/docs/test.txt",
            content="File content here",
            content_type="text/plain",
            size_bytes=17,
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        return [
            DocumentResult(id="doc-1", name="file1.txt", path=f"{path}/file1.txt"),
            DocumentResult(id="doc-2", name="file2.txt", path=f"{path}/file2.txt"),
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        return DocumentResult(
            id="doc-new",
            name=path.split("/")[-1] if "/" in path else path,
            path=path,
            content=content,
            size_bytes=len(content),
        )


class TestDocumentStorageTool:
    async def test_search_action(self):
        tool = FakeStorageTool("test_storage")
        result = await tool.execute(action="search", query="quarterly report")
        assert len(result) == 1
        assert result[0]["name"] == "Result for quarterly report"
        assert result[0]["id"] == "doc-1"

    async def test_read_action(self):
        tool = FakeStorageTool("test_storage")
        result = await tool.execute(action="read", resource_id="doc-1")
        assert result["id"] == "doc-1"
        assert result["content"] == "File content here"
        assert result["content_type"] == "text/plain"

    async def test_list_action(self):
        tool = FakeStorageTool("test_storage")
        result = await tool.execute(action="list", path="/docs")
        assert len(result) == 2
        assert result[0]["path"] == "/docs/file1.txt"
        assert result[1]["path"] == "/docs/file2.txt"

    async def test_write_action(self):
        tool = FakeStorageTool("test_storage")
        result = await tool.execute(action="write", path="/docs/new.txt", content="Hello")
        assert result["id"] == "doc-new"
        assert result["content"] == "Hello"
        assert result["size_bytes"] == 5

    async def test_unknown_action_raises(self):
        tool = FakeStorageTool("test_storage")
        with pytest.raises(Exception, match="Unknown action"):
            await tool.execute(action="delete")

    def test_name(self):
        tool = FakeStorageTool("sharepoint")
        assert tool.name == "sharepoint"

    def test_tags(self):
        tool = FakeStorageTool("gdrive")
        assert "storage" in tool.tags
        assert "documents" in tool.tags
        assert "gdrive" in tool.tags

    def test_description_default(self):
        tool = FakeStorageTool("sharepoint")
        assert "sharepoint" in tool.description

    def test_description_custom(self):
        tool = FakeStorageTool("sharepoint", description="SharePoint document storage")
        assert tool.description == "SharePoint document storage"

    def test_parameters(self):
        tool = FakeStorageTool("test_storage")
        param_names = [p.name for p in tool.parameters]
        assert "action" in param_names
        assert "path" in param_names
        assert "query" in param_names
        assert "content" in param_names
        assert "resource_id" in param_names

    def test_is_base_tool(self):
        from fireflyframework_genai.tools.base import BaseTool

        assert isinstance(FakeStorageTool("test"), BaseTool)
