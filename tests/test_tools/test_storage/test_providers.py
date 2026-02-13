"""Tests for concrete storage providers (SharePoint, Google Drive, Confluence, S3).

These tests mock external API calls to validate configuration, error handling,
and business logic without requiring real credentials or network access.

NOTE: ``BaseTool.execute()`` wraps all exceptions in ``ToolError``, so tests
that exercise ``execute()`` must catch ``ToolError`` (the original exception is
its ``__cause__``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fireflyframework_genai.exceptions import ToolError
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

    def test_config_params(self):
        tool = SharePointTool(
            tenant_id="t1",
            site_url="https://example.sharepoint.com",
            client_id="c1",
            client_secret="s1",
            drive_id="d1",
            timeout=60.0,
        )
        assert tool._tenant_id == "t1"
        assert tool._site_url == "https://example.sharepoint.com"
        assert tool._client_id == "c1"
        assert tool._client_secret == "s1"
        assert tool._drive_id == "d1"
        assert tool._timeout == 60.0

    async def test_search_auth_error_when_missing_credentials(self):
        tool = SharePointTool(site_url="https://example.sharepoint.com")
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="tenant_id"):
            await tool.execute(action="search", query="report")

    async def test_search_requires_site_or_drive(self):
        tool = SharePointTool(tenant_id="t", client_id="c", client_secret="s")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="site_url or drive_id"):
            await tool.execute(action="search", query="report")

    async def test_search_with_mocked_graph_api(self):
        tool = SharePointTool(tenant_id="t", client_id="c", client_secret="s", drive_id="drive-123")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        tool._graph_get = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "value": [
                    {
                        "id": "item-1",
                        "name": "report.docx",
                        "parentReference": {"path": "/root/docs"},
                        "file": {"mimeType": "application/docx"},
                        "size": 1024,
                        "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                        "webUrl": "https://example.sharepoint.com/docs/report.docx",
                    }
                ]
            }
        )
        result = await tool.execute(action="search", query="report")
        assert len(result) == 1
        assert result[0]["id"] == "item-1"
        assert result[0]["name"] == "report.docx"

    async def test_read_with_mocked_graph_api(self):
        tool = SharePointTool(tenant_id="t", client_id="c", client_secret="s", drive_id="drive-123")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        tool._graph_get = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "id": "item-1",
                "name": "readme.txt",
                "parentReference": {"path": "/root"},
                "file": {"mimeType": "text/plain"},
                "size": 100,
                "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                "webUrl": "https://example.sharepoint.com/readme.txt",
                "@microsoft.graph.downloadUrl": "https://download.example.com/readme.txt",
            }
        )
        # Mock httpx for download
        mock_resp = MagicMock()
        mock_resp.text = "Hello, World!"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.tools.storage.sharepoint.httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(action="read", resource_id="item-1")
        assert result["id"] == "item-1"
        assert result["content"] == "Hello, World!"

    async def test_list_with_mocked_graph_api(self):
        tool = SharePointTool(tenant_id="t", client_id="c", client_secret="s", drive_id="drive-123")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        tool._graph_get = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "value": [
                    {
                        "id": "f1",
                        "name": "folder1",
                        "size": 0,
                        "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                        "webUrl": "url1",
                    },
                    {
                        "id": "f2",
                        "name": "file.txt",
                        "file": {"mimeType": "text/plain"},
                        "size": 256,
                        "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                        "webUrl": "url2",
                    },
                ]
            }
        )
        result = await tool.execute(action="list", path="/docs")
        assert len(result) == 2
        assert result[0]["name"] == "folder1"
        assert result[1]["name"] == "file.txt"

    async def test_write_with_mocked_graph_api(self):
        tool = SharePointTool(tenant_id="t", client_id="c", client_secret="s", drive_id="drive-123")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        tool._graph_put = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "id": "new-item",
                "name": "new.txt",
                "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                "webUrl": "https://example.sharepoint.com/new.txt",
            }
        )
        result = await tool.execute(action="write", path="/docs/new.txt", content="Hello World")
        assert result["id"] == "new-item"
        assert result["content"] == "Hello World"
        assert result["size_bytes"] == len(b"Hello World")


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

    def test_config_params(self):
        tool = GoogleDriveTool(
            service_account_key="/path/to/key.json",
            folder_id="folder-abc",
            timeout=45.0,
        )
        assert tool._service_account_key == "/path/to/key.json"
        assert tool._folder_id == "folder-abc"
        assert tool._timeout == 45.0

    async def test_auth_error_when_missing_credentials(self):
        """Without credentials, we expect either a dep check error or auth error."""
        tool = GoogleDriveTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="service_account_key|credentials_json"):
            await tool.execute(action="search", query="budget")

    async def test_search_with_mocked_service(self):
        tool = GoogleDriveTool(service_account_key="/fake/key.json", folder_id="root-folder")
        mock_files = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "files": [
                {
                    "id": "f1",
                    "name": "budget.xlsx",
                    "mimeType": "application/xlsx",
                    "size": "2048",
                    "modifiedTime": "2025-01-01T00:00:00Z",
                    "webViewLink": "https://drive.google.com/f1",
                    "parents": ["root-folder"],
                },
            ]
        }
        mock_files.list.return_value = mock_list
        mock_svc = MagicMock()
        mock_svc.files.return_value = mock_files

        tool._service = mock_svc
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="search", query="budget")
        assert len(result) == 1
        assert result[0]["id"] == "f1"
        assert result[0]["name"] == "budget.xlsx"

    async def test_list_with_mocked_service(self):
        tool = GoogleDriveTool(service_account_key="/fake/key.json")
        mock_files = MagicMock()
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "files": [
                {
                    "id": "f1",
                    "name": "doc.txt",
                    "mimeType": "text/plain",
                    "size": "100",
                    "modifiedTime": "2025-01-01T00:00:00Z",
                    "webViewLink": "url",
                },
                {
                    "id": "f2",
                    "name": "img.png",
                    "mimeType": "image/png",
                    "size": "5000",
                    "modifiedTime": "2025-01-01T00:00:00Z",
                    "webViewLink": "url2",
                },
            ]
        }
        mock_files.list.return_value = mock_list
        mock_svc = MagicMock()
        mock_svc.files.return_value = mock_files

        tool._service = mock_svc
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list", path="folder-id")
        assert len(result) == 2

    async def test_write_with_mocked_service(self):
        tool = GoogleDriveTool(service_account_key="/fake/key.json", folder_id="root-folder")
        mock_files = MagicMock()
        mock_create = MagicMock()
        mock_create.execute.return_value = {"id": "new-f1", "name": "file.txt", "webViewLink": "url"}
        mock_files.create.return_value = mock_create
        mock_svc = MagicMock()
        mock_svc.files.return_value = mock_files

        tool._service = mock_svc
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        # Need to mock _MediaUpload since google-api-python-client may not be installed
        with patch.object(
            __import__("firefly_dworkers.tools.storage.google_drive", fromlist=["google_drive"]),
            "_MediaUpload",
            MagicMock(),
            create=True,
        ):
            result = await tool.execute(action="write", path="/docs/file.txt", content="Content")
        assert result["id"] == "new-f1"
        assert result["content"] == "Content"


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

    def test_config_params(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="user", api_token="tok", space_key="ENG")
        assert tool._base_url == "https://wiki.example.com"
        assert tool._username == "user"
        assert tool._api_token == "tok"
        assert tool._space_key == "ENG"

    async def test_auth_error_when_missing_credentials(self):
        tool = ConfluenceTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="base_url|username|api_token"):
            await tool.execute(action="search", query="architecture")

    async def test_search_with_mocked_client(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="u", api_token="t", space_key="ENG")
        mock_client = MagicMock()
        mock_client.cql.return_value = {
            "results": [
                {
                    "content": {
                        "id": "12345",
                        "title": "Architecture Overview",
                        "_links": {"webui": "/spaces/ENG/pages/12345"},
                    }
                }
            ]
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="search", query="architecture")
        assert len(result) == 1
        assert result[0]["id"] == "12345"
        assert result[0]["name"] == "Architecture Overview"

    async def test_read_with_mocked_client(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="u", api_token="t")
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = {
            "id": "12345",
            "title": "My Page",
            "body": {"storage": {"value": "<p>Page content</p>"}},
            "version": {"when": "2025-01-01T00:00:00Z"},
            "_links": {"webui": "/spaces/ENG/pages/12345"},
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="read", resource_id="12345")
        assert result["id"] == "12345"
        assert result["content"] == "<p>Page content</p>"
        assert result["content_type"] == "text/html"

    async def test_list_with_mocked_client(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="u", api_token="t", space_key="ENG")
        mock_client = MagicMock()
        mock_client.get_all_pages_from_space.return_value = [
            {"id": "1", "title": "Page A", "_links": {"webui": "/p/1"}, "version": {"when": "2025-01-01"}},
            {"id": "2", "title": "Page B", "_links": {"webui": "/p/2"}, "version": {"when": "2025-01-02"}},
        ]
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list", path="ENG")
        assert len(result) == 2

    async def test_write_with_mocked_client(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="u", api_token="t", space_key="ENG")
        mock_client = MagicMock()
        mock_client.create_page.return_value = {
            "id": "99",
            "title": "New Page",
            "_links": {"webui": "/p/99"},
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="write", path="/pages/New Page", content="<p>Hello</p>")
        assert result["id"] == "99"
        assert result["content"] == "<p>Hello</p>"

    async def test_list_requires_space(self):
        tool = ConfluenceTool(base_url="https://wiki.example.com", username="u", api_token="t")
        tool._client = MagicMock()
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="space_key"):
            await tool.execute(action="list", path="")


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

    def test_config_params(self):
        tool = S3Tool(
            bucket="my-bucket",
            region="eu-west-1",
            aws_access_key_id="AKIA...",
            aws_secret_access_key="secret",
            prefix="data/v1",
            endpoint_url="http://localhost:9000",
        )
        assert tool._bucket == "my-bucket"
        assert tool._region == "eu-west-1"
        assert tool._aws_access_key_id == "AKIA..."
        assert tool._prefix == "data/v1"
        assert tool._endpoint_url == "http://localhost:9000"

    async def test_requires_bucket(self):
        tool = S3Tool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="bucket"):
            await tool.execute(action="search", query="logs")

    async def test_search_with_mocked_client(self):
        tool = S3Tool(bucket="my-bucket", region="us-east-1")
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "logs/app.log", "Size": 1024, "LastModified": "2025-01-01"},
                {"Key": "logs/error.log", "Size": 512, "LastModified": "2025-01-02"},
            ]
        }
        tool._client = mock_s3
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="search", query="logs")
        assert len(result) == 2
        assert result[0]["name"] == "app.log"
        assert result[0]["size_bytes"] == 1024

    async def test_read_with_mocked_client(self):
        tool = S3Tool(bucket="my-bucket", region="us-east-1")
        mock_body = MagicMock()
        mock_body.read.return_value = b"file content here"

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "text/plain",
            "ContentLength": 17,
            "LastModified": "2025-01-01",
        }
        tool._client = mock_s3
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="read", resource_id="data/file.txt")
        assert result["content"] == "file content here"
        assert result["content_type"] == "text/plain"

    async def test_list_with_mocked_client(self):
        tool = S3Tool(bucket="my-bucket", region="us-east-1", prefix="data")
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "CommonPrefixes": [{"Prefix": "data/subdir/"}],
            "Contents": [{"Key": "data/file.txt", "Size": 100, "LastModified": "2025-01-01"}],
        }
        tool._client = mock_s3
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list", path="/")
        assert len(result) == 2
        # First item is a folder
        assert result[0]["content_type"] == "folder"
        # Second item is a file
        assert result[1]["name"] == "file.txt"

    async def test_write_with_mocked_client(self):
        tool = S3Tool(bucket="my-bucket", region="us-east-1")
        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {}
        tool._client = mock_s3
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="write", path="docs/new.txt", content="new data")
        assert result["id"] == "docs/new.txt"
        assert result["content"] == "new data"
        assert result["size_bytes"] == len(b"new data")

    def test_full_key_with_prefix(self):
        tool = S3Tool(bucket="b", prefix="project/v1")
        assert tool._full_key("file.txt") == "project/v1/file.txt"
        assert tool._full_key("/file.txt") == "project/v1/file.txt"

    def test_full_key_without_prefix(self):
        tool = S3Tool(bucket="b")
        assert tool._full_key("file.txt") == "file.txt"
