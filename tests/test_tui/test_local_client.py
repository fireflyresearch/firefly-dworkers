"""Tests for LocalClient attachment handling and factory metadata."""

from __future__ import annotations

import base64

import pytest

from firefly_dworkers_cli.tui.backend.local import LocalClient
from firefly_dworkers_cli.tui.backend.models import FileAttachment


class TestBuildMultimodalContent:
    """Test LocalClient._build_multimodal_content() conversion logic."""

    def test_text_only_no_attachments(self):
        result = LocalClient._build_multimodal_content("hello", [])
        assert result == ["hello"]

    def test_image_attachment(self):
        att = FileAttachment(
            filename="photo.png",
            media_type="image/png",
            data=b"\x89PNG\r\n",
            size=6,
        )
        result = LocalClient._build_multimodal_content("look at this", [att])
        assert len(result) == 2
        assert result[0] == "look at this"
        # The second element should be an ImageUrl or fallback string.
        second = result[1]
        if hasattr(second, "url"):
            assert second.url.startswith("data:image/png;base64,")
        else:
            # Fallback when framework types not available.
            assert "Image" in str(second) or "base64" in str(second)

    def test_pdf_attachment(self):
        att = FileAttachment(
            filename="report.pdf",
            media_type="application/pdf",
            data=b"%PDF-1.4",
            size=8,
        )
        result = LocalClient._build_multimodal_content("summarize", [att])
        assert len(result) == 2
        second = result[1]
        if hasattr(second, "url"):
            assert second.url.startswith("data:application/pdf;base64,")
        else:
            assert "Document" in str(second) or "pdf" in str(second).lower()

    def test_text_file_fallback(self):
        content = b"def hello():\n    pass\n"
        att = FileAttachment(
            filename="main.py",
            media_type="text/plain",
            data=content,
            size=len(content),
        )
        result = LocalClient._build_multimodal_content("review this", [att])
        assert len(result) == 2
        second = result[1]
        # With or without framework types, should contain the code content.
        if isinstance(second, str):
            assert "main.py" in second or "hello" in second

    def test_multiple_attachments(self):
        att1 = FileAttachment(
            filename="a.png", media_type="image/png", data=b"img", size=3,
        )
        att2 = FileAttachment(
            filename="b.txt", media_type="text/plain", data=b"text", size=4,
        )
        result = LocalClient._build_multimodal_content("analyze", [att1, att2])
        assert len(result) == 3
        assert result[0] == "analyze"


class TestFactoryMetadata:
    """Test that worker factory stores metadata from registration."""

    def test_factory_stores_description(self):
        from firefly_dworkers.workers.factory import WorkerFactory
        from firefly_dworkers.types import WorkerRole

        factory = WorkerFactory()

        @factory.register(
            WorkerRole.ANALYST,
            description="Test analyst",
            tags=["test"],
        )
        class FakeAnalyst:
            pass

        meta = factory.get_metadata(WorkerRole.ANALYST)
        assert meta.description == "Test analyst"
        assert meta.tags == ["test"]
        assert meta.cls is FakeAnalyst

    def test_factory_metadata_not_found(self):
        from firefly_dworkers.workers.factory import WorkerFactory
        from firefly_dworkers.types import WorkerRole

        factory = WorkerFactory()
        with pytest.raises(KeyError):
            factory.get_metadata(WorkerRole.ANALYST)

    def test_factory_description_defaults_empty(self):
        from firefly_dworkers.workers.factory import WorkerFactory
        from firefly_dworkers.types import WorkerRole

        factory = WorkerFactory()

        @factory.register(WorkerRole.DESIGNER)
        class FakeDesigner:
            pass

        meta = factory.get_metadata(WorkerRole.DESIGNER)
        assert meta.description == ""
        assert meta.tags == []


class TestFactoryIdentityFields:
    def test_factory_stores_display_name(self):
        from firefly_dworkers.workers.factory import WorkerFactory
        from firefly_dworkers.types import WorkerRole

        factory = WorkerFactory()

        @factory.register(
            WorkerRole.ANALYST,
            description="Test analyst",
            display_name="Leo",
            avatar="L",
            avatar_color="blue",
            tagline="Strategic analysis",
        )
        class FakeAnalyst:
            pass

        meta = factory.get_metadata(WorkerRole.ANALYST)
        assert meta.display_name == "Leo"
        assert meta.avatar == "L"
        assert meta.avatar_color == "blue"
        assert meta.tagline == "Strategic analysis"

    def test_factory_identity_defaults_empty(self):
        from firefly_dworkers.workers.factory import WorkerFactory
        from firefly_dworkers.types import WorkerRole

        factory = WorkerFactory()

        @factory.register(WorkerRole.DESIGNER)
        class FakeDesigner:
            pass

        meta = factory.get_metadata(WorkerRole.DESIGNER)
        assert meta.display_name == ""
        assert meta.avatar == ""
        assert meta.avatar_color == ""
        assert meta.tagline == ""
