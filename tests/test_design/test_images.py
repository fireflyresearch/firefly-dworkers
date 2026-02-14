"""Tests for ImageResolver -- resolving ImageRequest to ResolvedImage bytes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from firefly_dworkers.design.images import ImageResolver
from firefly_dworkers.design.models import ImageRequest, ResolvedImage


# ── Helpers ─────────────────────────────────────────────────────────────────

# Minimal valid PNG (1x1 pixel, transparent)
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _file_request(path: str, *, alt_text: str = "test image") -> ImageRequest:
    return ImageRequest(name="logo", source_type="file", file_path=path, alt_text=alt_text)


def _url_request(url: str = "https://example.com/img.png", *, alt_text: str = "url image") -> ImageRequest:
    return ImageRequest(name="banner", source_type="url", url=url, alt_text=alt_text)


# ── File resolution ────────────────────────────────────────────────────────


class TestImageResolverFile:
    """Tests for resolving images from local files."""

    async def test_resolve_file(self) -> None:
        """Read a temp PNG file and verify bytes match."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(_TINY_PNG)
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert isinstance(result, ResolvedImage)
        assert result.data == _TINY_PNG
        assert result.mime_type == "image/png"
        assert result.alt_text == "test image"

        # Cleanup
        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_detects_mime_jpg(self) -> None:
        """Verify .jpg extension is detected as image/jpeg."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\xff\xd8\xff\xe0fake-jpeg")
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert result.mime_type == "image/jpeg"
        assert result.data == b"\xff\xd8\xff\xe0fake-jpeg"

        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_detects_mime_gif(self) -> None:
        """Verify .gif extension is detected as image/gif."""
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
            tmp.write(b"GIF89a-fake")
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert result.mime_type == "image/gif"

        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_detects_mime_svg(self) -> None:
        """Verify .svg extension is detected as image/svg+xml."""
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            tmp.write(b"<svg></svg>")
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert result.mime_type == "image/svg+xml"

        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_detects_mime_webp(self) -> None:
        """Verify .webp extension is detected as image/webp."""
        with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as tmp:
            tmp.write(b"RIFF\x00\x00\x00\x00WEBP")
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert result.mime_type == "image/webp"

        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_unknown_ext_defaults_png(self) -> None:
        """Unknown file extension defaults to image/png."""
        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp:
            tmp.write(b"BM-fake-bitmap")
            tmp.flush()
            path = tmp.name

        resolver = ImageResolver()
        result = await resolver.resolve(_file_request(path))

        assert result.mime_type == "image/png"  # default fallback

        Path(path).unlink(missing_ok=True)

    async def test_resolve_file_not_found(self) -> None:
        """Non-existent file should raise FileNotFoundError."""
        resolver = ImageResolver()
        with pytest.raises(FileNotFoundError):
            await resolver.resolve(_file_request("/nonexistent/path/image.png"))


# ── URL resolution ─────────────────────────────────────────────────────────


class TestImageResolverUrl:
    """Tests for resolving images from URLs via httpx."""

    async def test_resolve_url(self) -> None:
        """Mock httpx to return fake PNG bytes and verify result."""
        mock_response = MagicMock()
        mock_response.content = _TINY_PNG
        mock_response.headers = {"content-type": "image/png; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.design.images.httpx.AsyncClient", return_value=mock_client):
            resolver = ImageResolver()
            result = await resolver.resolve(_url_request())

        assert isinstance(result, ResolvedImage)
        assert result.data == _TINY_PNG
        assert result.mime_type == "image/png"
        assert result.alt_text == "url image"

    async def test_resolve_url_extracts_content_type(self) -> None:
        """Verify content-type header is used for mime_type."""
        mock_response = MagicMock()
        mock_response.content = b"fake-jpeg"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.design.images.httpx.AsyncClient", return_value=mock_client):
            resolver = ImageResolver()
            result = await resolver.resolve(_url_request())

        assert result.mime_type == "image/jpeg"

    async def test_resolve_url_error(self) -> None:
        """HTTP error should propagate as httpx.HTTPStatusError."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.design.images.httpx.AsyncClient", return_value=mock_client):
            resolver = ImageResolver()
            with pytest.raises(httpx.HTTPStatusError):
                await resolver.resolve(_url_request())


# ── AI generation ──────────────────────────────────────────────────────────


class TestImageResolverAi:
    """Tests for AI image generation."""

    async def test_no_api_key_raises(self) -> None:
        """Missing ai_api_key should raise ValueError."""
        resolver = ImageResolver()
        with pytest.raises(ValueError, match="ai_api_key"):
            await resolver.resolve(
                ImageRequest(name="test", source_type="ai_generate", prompt="a cat sitting on a desk")
            )

    async def test_ai_generate_openai(self) -> None:
        """Mock OpenAI DALL-E 3 POST response and verify PNG bytes."""
        import base64

        fake_png = b"\x89PNG\r\nfake-generated-image"
        b64_data = base64.b64encode(fake_png).decode()

        # Mock the POST to OpenAI
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"data": [{"b64_json": b64_data}]}
        mock_post_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_post_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.design.images.httpx.AsyncClient", return_value=mock_client):
            resolver = ImageResolver(ai_provider="openai", ai_api_key="sk-test-key")
            result = await resolver.resolve(
                ImageRequest(name="test", source_type="ai_generate", prompt="a cat")
            )

        assert isinstance(result, ResolvedImage)
        assert result.data == fake_png
        assert result.mime_type == "image/png"

    async def test_ai_missing_api_key(self) -> None:
        """Missing ai_api_key should raise ValueError."""
        resolver = ImageResolver(ai_provider="openai")
        with pytest.raises(ValueError, match="ai_api_key"):
            await resolver.resolve(
                ImageRequest(name="test", source_type="ai_generate", prompt="test")
            )

    async def test_unsupported_ai_provider(self) -> None:
        """Unsupported AI provider should raise ValueError."""
        resolver = ImageResolver(ai_provider="midjourney", ai_api_key="key-123")
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            await resolver.resolve(
                ImageRequest(name="test", source_type="ai_generate", prompt="test")
            )


# ── Stock image ────────────────────────────────────────────────────────────


class TestImageResolverStock:
    """Tests for stock photo API."""

    async def test_no_api_key_raises(self) -> None:
        """Missing stock_api_key should raise ValueError."""
        resolver = ImageResolver()
        with pytest.raises(ValueError, match="stock_api_key"):
            await resolver.resolve(ImageRequest(name="test", source_type="stock", prompt="office workspace"))

    async def test_stock_search_unsplash(self) -> None:
        """Mock Unsplash search + download and verify JPEG bytes."""
        fake_jpeg = b"\xff\xd8\xff\xe0fake-stock-image"

        # Mock search response
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {
            "results": [
                {
                    "urls": {"regular": "https://images.unsplash.com/photo-123"},
                    "alt_description": "office workspace",
                }
            ]
        }
        mock_search_response.raise_for_status = MagicMock()

        # Mock image download response
        mock_img_response = MagicMock()
        mock_img_response.content = fake_jpeg
        mock_img_response.headers = {"content-type": "image/jpeg"}
        mock_img_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_search_response, mock_img_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("firefly_dworkers.design.images.httpx.AsyncClient", return_value=mock_client):
            resolver = ImageResolver(stock_provider="unsplash", stock_api_key="key-123")
            result = await resolver.resolve(
                ImageRequest(name="test", source_type="stock", prompt="office workspace")
            )

        assert isinstance(result, ResolvedImage)
        assert result.data == fake_jpeg
        assert result.mime_type == "image/jpeg"

    async def test_unsupported_stock_provider(self) -> None:
        """Unsupported stock provider should raise ValueError."""
        resolver = ImageResolver(stock_provider="shutterstock", stock_api_key="key-123")
        with pytest.raises(ValueError, match="Unsupported stock provider"):
            await resolver.resolve(
                ImageRequest(name="test", source_type="stock", prompt="test")
            )


# ── resolve_all (parallel resolution) ──────────────────────────────────────


class TestImageResolverAll:
    """Tests for resolve_all parallel resolution."""

    async def test_resolve_all_parallel(self) -> None:
        """Two file requests should both resolve, dict keyed by name."""
        paths = []
        for suffix, name in [(".png", "logo"), (".jpg", "photo")]:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(_TINY_PNG)
                tmp.flush()
                paths.append((tmp.name, name))

        requests = [
            ImageRequest(name=name, source_type="file", file_path=path, alt_text=f"alt-{name}")
            for path, name in paths
        ]

        resolver = ImageResolver()
        result = await resolver.resolve_all(requests)

        assert len(result) == 2
        assert "logo" in result
        assert "photo" in result
        assert result["logo"].data == _TINY_PNG
        assert result["photo"].data == _TINY_PNG
        assert result["logo"].mime_type == "image/png"
        assert result["photo"].mime_type == "image/jpeg"

        # Cleanup
        for path, _ in paths:
            Path(path).unlink(missing_ok=True)

    async def test_resolve_all_handles_failures(self) -> None:
        """One good file and one bad path: good resolves, bad gets empty with alt_text."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(_TINY_PNG)
            tmp.flush()
            good_path = tmp.name

        requests = [
            ImageRequest(name="good", source_type="file", file_path=good_path, alt_text="good image"),
            ImageRequest(name="bad", source_type="file", file_path="/nonexistent/bad.png", alt_text=""),
        ]

        resolver = ImageResolver()
        result = await resolver.resolve_all(requests)

        assert len(result) == 2

        # Good image resolved successfully
        assert result["good"].data == _TINY_PNG
        assert result["good"].mime_type == "image/png"
        assert result["good"].alt_text == "good image"

        # Bad image has empty data and failure message in alt_text
        assert result["bad"].data == b""
        assert "Failed:" in result["bad"].alt_text

        Path(good_path).unlink(missing_ok=True)

    async def test_resolve_all_empty_list(self) -> None:
        """Empty request list returns empty dict."""
        resolver = ImageResolver()
        result = await resolver.resolve_all([])
        assert result == {}


# ── Unknown source type ────────────────────────────────────────────────────


class TestImageResolverUnknown:
    """Tests for unknown source_type handling."""

    async def test_unknown_source_type_raises(self) -> None:
        """Unknown source_type should raise ValueError."""
        resolver = ImageResolver()
        with pytest.raises(ValueError, match="Unknown"):
            await resolver.resolve(ImageRequest(name="test", source_type="magic"))


# ── detect_mime static method ──────────────────────────────────────────────


class TestDetectMime:
    """Unit tests for the _detect_mime static helper."""

    def test_png(self) -> None:
        assert ImageResolver._detect_mime("logo.png") == "image/png"

    def test_jpg(self) -> None:
        assert ImageResolver._detect_mime("photo.jpg") == "image/jpeg"

    def test_jpeg(self) -> None:
        assert ImageResolver._detect_mime("photo.jpeg") == "image/jpeg"

    def test_gif(self) -> None:
        assert ImageResolver._detect_mime("anim.gif") == "image/gif"

    def test_svg(self) -> None:
        assert ImageResolver._detect_mime("icon.svg") == "image/svg+xml"

    def test_webp(self) -> None:
        assert ImageResolver._detect_mime("hero.webp") == "image/webp"

    def test_no_extension(self) -> None:
        assert ImageResolver._detect_mime("noext") == "image/png"

    def test_unknown_extension(self) -> None:
        assert ImageResolver._detect_mime("file.tiff") == "image/png"
