"""Tests for concrete storage providers (SharePoint, Google Drive, Confluence, S3)."""

from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.storage.confluence import ConfluenceTool
from firefly_dworkers.tools.storage.google_drive import GoogleDriveTool
from firefly_dworkers.tools.storage.s3 import S3Tool
from firefly_dworkers.tools.storage.sharepoint import SharePointTool

# ---------------------------------------------------------------------------
# SharePointTool
# ---------------------------------------------------------------------------


class TestSharePointTool:
    def test_instantiation(self):
        tool = SharePointTool()
        assert tool is not None

    def test_name(self):
        assert SharePointTool().name == "sharepoint"

    def test_tags(self):
        tags = SharePointTool().tags
        assert "storage" in tags
        assert "sharepoint" in tags

    def test_is_base_tool(self):
        assert isinstance(SharePointTool(), BaseTool)

    async def test_search(self):
        tool = SharePointTool()
        result = await tool.execute(action="search", query="report")
        assert len(result) == 1
        assert "configure credentials" in result[0]["content"]

    async def test_read(self):
        tool = SharePointTool()
        result = await tool.execute(action="read", resource_id="doc-1")
        assert result["id"] == "doc-1"
        assert "configure credentials" in result["content"]

    async def test_list(self):
        tool = SharePointTool()
        result = await tool.execute(action="list", path="/sites/docs")
        assert len(result) == 1
        assert "configure credentials" in result[0]["content"]

    async def test_write(self):
        tool = SharePointTool()
        result = await tool.execute(action="write", path="/docs/new.txt", content="Hello World")
        assert "11 chars" in result["content"]
        assert "configure credentials" in result["content"]

    def test_config_params(self):
        tool = SharePointTool(tenant_id="t1", site_url="https://example.sharepoint.com", credential_ref="ref1")
        assert tool._tenant_id == "t1"
        assert tool._site_url == "https://example.sharepoint.com"
        assert tool._credential_ref == "ref1"


# ---------------------------------------------------------------------------
# GoogleDriveTool
# ---------------------------------------------------------------------------


class TestGoogleDriveTool:
    def test_instantiation(self):
        tool = GoogleDriveTool()
        assert tool is not None

    def test_name(self):
        assert GoogleDriveTool().name == "google_drive"

    def test_tags(self):
        tags = GoogleDriveTool().tags
        assert "storage" in tags
        assert "google_drive" in tags

    def test_is_base_tool(self):
        assert isinstance(GoogleDriveTool(), BaseTool)

    async def test_search(self):
        tool = GoogleDriveTool()
        result = await tool.execute(action="search", query="budget")
        assert len(result) == 1
        assert "Google Drive" in result[0]["content"]

    async def test_read(self):
        tool = GoogleDriveTool()
        result = await tool.execute(action="read", resource_id="file-abc")
        assert result["id"] == "file-abc"

    async def test_list(self):
        tool = GoogleDriveTool()
        result = await tool.execute(action="list", path="/shared")
        assert len(result) == 1

    async def test_write(self):
        tool = GoogleDriveTool()
        result = await tool.execute(action="write", path="/docs/file.txt", content="Content")
        assert "7 chars" in result["content"]


# ---------------------------------------------------------------------------
# ConfluenceTool
# ---------------------------------------------------------------------------


class TestConfluenceTool:
    def test_instantiation(self):
        tool = ConfluenceTool()
        assert tool is not None

    def test_name(self):
        assert ConfluenceTool().name == "confluence"

    def test_tags(self):
        tags = ConfluenceTool().tags
        assert "storage" in tags
        assert "confluence" in tags

    def test_is_base_tool(self):
        assert isinstance(ConfluenceTool(), BaseTool)

    async def test_search(self):
        tool = ConfluenceTool()
        result = await tool.execute(action="search", query="architecture")
        assert len(result) == 1
        assert "Confluence" in result[0]["content"]

    async def test_read(self):
        tool = ConfluenceTool()
        result = await tool.execute(action="read", resource_id="page-1")
        assert result["id"] == "page-1"

    async def test_list(self):
        tool = ConfluenceTool()
        result = await tool.execute(action="list", path="/spaces/ENG")
        assert len(result) == 1

    async def test_write(self):
        tool = ConfluenceTool()
        result = await tool.execute(action="write", path="/pages/new", content="New page content")
        assert "16 chars" in result["content"]

    def test_config_params(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="user", api_token="tok", space_key="ENG")
        assert tool._base_url == "https://wiki.example.com"
        assert tool._space_key == "ENG"


# ---------------------------------------------------------------------------
# S3Tool
# ---------------------------------------------------------------------------


class TestS3Tool:
    def test_instantiation(self):
        tool = S3Tool()
        assert tool is not None

    def test_name(self):
        assert S3Tool().name == "s3"

    def test_tags(self):
        tags = S3Tool().tags
        assert "storage" in tags
        assert "s3" in tags

    def test_is_base_tool(self):
        assert isinstance(S3Tool(), BaseTool)

    async def test_search(self):
        tool = S3Tool()
        result = await tool.execute(action="search", query="logs")
        assert len(result) == 1
        assert "S3" in result[0]["content"]

    async def test_read(self):
        tool = S3Tool()
        result = await tool.execute(action="read", resource_id="obj-key")
        assert result["id"] == "obj-key"

    async def test_list(self):
        tool = S3Tool()
        result = await tool.execute(action="list", path="/bucket/prefix")
        assert len(result) == 1

    async def test_write(self):
        tool = S3Tool()
        result = await tool.execute(action="write", path="/bucket/file.txt", content="data")
        assert "4 chars" in result["content"]

    def test_config_params(self):
        tool = S3Tool(bucket="my-bucket", region="eu-west-1")
        assert tool._bucket == "my-bucket"
        assert tool._region == "eu-west-1"
