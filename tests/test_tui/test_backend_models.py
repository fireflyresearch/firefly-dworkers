"""Tests for TUI backend models — FileAttachment, FileAttachmentPayload, etc."""

from __future__ import annotations

import base64

import pytest

from firefly_dworkers_cli.tui.backend.models import (
    EXTENSION_MIME_MAP,
    MAX_ATTACHMENT_SIZE,
    MAX_ATTACHMENTS,
    FileAttachment,
    WorkerInfo,
)
from firefly_dworkers.sdk.models import FileAttachmentPayload, RunWorkerRequest


class TestFileAttachment:
    def test_create(self):
        att = FileAttachment(
            filename="test.png",
            media_type="image/png",
            data=b"\x89PNG\r\n",
            size=6,
        )
        assert att.filename == "test.png"
        assert att.media_type == "image/png"
        assert att.data == b"\x89PNG\r\n"
        assert att.size == 6

    def test_text_file(self):
        content = b"Hello, world!"
        att = FileAttachment(
            filename="hello.txt",
            media_type="text/plain",
            data=content,
            size=len(content),
        )
        assert att.data.decode("utf-8") == "Hello, world!"

    def test_size_matches_data(self):
        data = b"x" * 1024
        att = FileAttachment(
            filename="data.bin",
            media_type="application/octet-stream",
            data=data,
            size=len(data),
        )
        assert att.size == 1024


class TestFileAttachmentPayload:
    def test_create(self):
        data = b"raw content"
        b64 = base64.b64encode(data).decode()
        payload = FileAttachmentPayload(
            filename="doc.pdf",
            media_type="application/pdf",
            data_b64=b64,
        )
        assert payload.filename == "doc.pdf"
        assert payload.media_type == "application/pdf"
        assert base64.b64decode(payload.data_b64) == data

    def test_roundtrip(self):
        """Verify base64 encode/decode roundtrip."""
        original = b"\x00\x01\x02\xff\xfe\xfd"
        b64 = base64.b64encode(original).decode()
        payload = FileAttachmentPayload(
            filename="binary.bin",
            media_type="application/octet-stream",
            data_b64=b64,
        )
        decoded = base64.b64decode(payload.data_b64)
        assert decoded == original


class TestRunWorkerRequestAttachments:
    def test_default_empty_attachments(self):
        req = RunWorkerRequest(worker_role="analyst", prompt="hello")
        assert req.attachments == []

    def test_with_attachments(self):
        payload = FileAttachmentPayload(
            filename="test.png",
            media_type="image/png",
            data_b64=base64.b64encode(b"fake").decode(),
        )
        req = RunWorkerRequest(
            worker_role="analyst",
            prompt="analyze this",
            attachments=[payload],
        )
        assert len(req.attachments) == 1
        assert req.attachments[0].filename == "test.png"


class TestExtensionMimeMap:
    @pytest.mark.parametrize(
        "ext,expected",
        [
            (".png", "image/png"),
            (".jpg", "image/jpeg"),
            (".pdf", "application/pdf"),
            (".py", "text/plain"),
            (".json", "application/json"),
            (".md", "text/markdown"),
        ],
    )
    def test_known_extensions(self, ext, expected):
        assert EXTENSION_MIME_MAP[ext] == expected


class TestWorkerInfoDescription:
    def test_description_field(self):
        w = WorkerInfo(role="analyst", name="Analyst", description="Analysis worker")
        assert w.description == "Analysis worker"

    def test_description_defaults_empty(self):
        w = WorkerInfo(role="analyst", name="Analyst")
        assert w.description == ""


class TestWorkerInfoIdentity:
    def test_tagline_field(self):
        w = WorkerInfo(role="analyst", name="Leo", tagline="Strategic analysis")
        assert w.tagline == "Strategic analysis"

    def test_avatar_fields(self):
        w = WorkerInfo(role="manager", name="Amara", avatar="A", avatar_color="green")
        assert w.avatar == "A"
        assert w.avatar_color == "green"

    def test_identity_defaults_empty(self):
        w = WorkerInfo(role="analyst", name="Analyst")
        assert w.tagline == ""
        assert w.avatar == ""
        assert w.avatar_color == ""


class TestConstants:
    def test_max_attachment_size(self):
        assert MAX_ATTACHMENT_SIZE == 10 * 1024 * 1024

    def test_max_attachments(self):
        assert MAX_ATTACHMENTS == 5
