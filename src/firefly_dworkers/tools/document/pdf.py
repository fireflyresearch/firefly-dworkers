"""PDF generation tool -- converts Markdown/HTML to PDF."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.tools.registry import tool_registry

try:
    import weasyprint

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False


def _require_weasyprint() -> None:
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint required: pip install firefly-dworkers[pdf]")


@tool_registry.register("pdf", category="document")
class PDFTool(BaseTool):
    """Generate PDF files from Markdown or HTML content."""

    def __init__(
        self,
        *,
        default_css: str = "",
        timeout: float = 120.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        params = [
            ParameterSpec(
                name="action",
                type_annotation="str",
                description="Action: generate (from HTML/Markdown).",
                required=True,
            ),
            ParameterSpec(
                name="content",
                type_annotation="str",
                description="HTML or Markdown content to convert to PDF.",
                required=True,
            ),
            ParameterSpec(
                name="content_type",
                type_annotation="str",
                description="Content type: 'html' or 'markdown'. Default: 'markdown'.",
                required=False,
                default="markdown",
            ),
            ParameterSpec(
                name="css",
                type_annotation="str",
                description="Optional CSS stylesheet content.",
                required=False,
                default="",
            ),
        ]
        super().__init__(
            "pdf",
            description="Generate PDF files from Markdown or HTML content.",
            tags=["pdf", "document", "generation"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )
        self._default_css = default_css
        self._last_artifact: bytes | None = None

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action = kwargs.get("action", "generate")
        if action != "generate":
            raise ValueError(f"Unknown action: {action}. Only 'generate' is supported.")

        content = kwargs["content"]
        content_type = kwargs.get("content_type", "markdown")
        css = kwargs.get("css", "") or self._default_css

        pdf_bytes = await asyncio.to_thread(self._generate_sync, content, content_type, css)
        self._last_artifact = pdf_bytes
        return {
            "bytes_length": len(pdf_bytes),
            "success": True,
        }

    @property
    def artifact_bytes(self) -> bytes | None:
        """Bytes from the last generate operation, or ``None``."""
        return self._last_artifact

    async def generate(self, content: str, *, content_type: str = "markdown", css: str = "") -> bytes:
        """Generate a PDF and return the raw bytes."""
        return await asyncio.to_thread(
            self._generate_sync, content, content_type, css or self._default_css
        )

    async def generate_and_save(
        self, output_path: str, content: str, *, content_type: str = "markdown", css: str = ""
    ) -> str:
        """Generate a PDF and save it to *output_path*. Returns the absolute path."""
        data = await self.generate(content, content_type=content_type, css=css)
        with open(output_path, "wb") as f:
            f.write(data)
        return os.path.abspath(output_path)

    def _generate_sync(self, content: str, content_type: str, css: str) -> bytes:
        _require_weasyprint()

        html = self._markdown_to_html(content) if content_type == "markdown" else content

        if css:
            html = f"<style>{css}</style>\n{html}"

        doc = weasyprint.HTML(string=html)
        return doc.write_pdf()

    @staticmethod
    def _markdown_to_html(md_content: str) -> str:
        """Convert Markdown to HTML using simple regex-based conversion."""
        import re

        html = md_content

        # Headers
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # Line breaks to paragraphs
        paragraphs = html.split("\n\n")
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith("<h") and not p.startswith("<"):
                p = f"<p>{p}</p>"
            processed.append(p)
        html = "\n".join(processed)

        return html
