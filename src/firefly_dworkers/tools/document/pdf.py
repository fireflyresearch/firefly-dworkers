"""PDF generation tool -- converts Markdown/HTML to PDF."""

from __future__ import annotations

import asyncio
import base64
import logging
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

logger = logging.getLogger(__name__)


def _require_weasyprint() -> None:
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint required: pip install firefly-dworkers[pdf]")


# ── Professional default stylesheet ─────────────────────────────────────────

_PROFESSIONAL_CSS = """
body { font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #333; line-height: 1.6; }
h1 { font-size: 28px; color: #1a1a1a; border-bottom: 2px solid #1a73e8; padding-bottom: 8px; }
h2 { font-size: 22px; color: #333; margin-top: 24px; }
h3 { font-size: 18px; color: #555; }
p { margin: 12px 0; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background-color: #1a73e8; color: white; }
tr:nth-child(even) { background-color: #f9f9f9; }
img { max-width: 100%; height: auto; margin: 16px 0; }
.callout { background: #f0f7ff; border-left: 4px solid #1a73e8; padding: 12px 16px; margin: 16px 0; }
code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
pre { background: #f5f5f5; padding: 16px; border-radius: 4px; overflow-x: auto; }
"""


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

    # ── Core execution ───────────────────────────────────────────────────────

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

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _generate_sync(self, content: str, content_type: str, css: str) -> bytes:
        _require_weasyprint()

        html = self._markdown_to_html(content) if content_type == "markdown" else content

        # Apply CSS: use provided CSS, or fall back to professional defaults.
        effective_css = css or _PROFESSIONAL_CSS
        html = f"<style>{effective_css}</style>\n{html}"

        doc = weasyprint.HTML(string=html)
        return doc.write_pdf()

    @staticmethod
    def _markdown_to_html(md_content: str) -> str:
        """Convert Markdown to HTML.

        Prefers the ``markdown`` library (with tables and fenced-code
        extensions) when available, falling back to a simple regex-based
        converter.
        """
        try:
            import markdown

            return markdown.markdown(md_content, extensions=["tables", "fenced_code"])
        except ImportError:
            pass

        # Fallback: regex-based conversion
        return PDFTool._markdown_to_html_regex(md_content)

    @staticmethod
    def _markdown_to_html_regex(md_content: str) -> str:
        """Regex-based Markdown to HTML fallback."""
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

    # ── Image / chart embedding ──────────────────────────────────────────────

    @staticmethod
    def embed_image(image_bytes: bytes, mime_type: str = "image/png", alt: str = "") -> str:
        """Return an HTML ``<img>`` tag with the image as a base64 data URI.

        This does **not** require weasyprint and can be used independently
        to prepare HTML content with embedded images before PDF generation.
        """
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f'<img src="data:{mime_type};base64,{b64}" alt="{alt}" />'

    @staticmethod
    def embed_chart_image(chart: Any) -> str:
        """Render a :class:`~firefly_dworkers.design.models.ResolvedChart` to
        PNG and return an HTML ``<img>`` tag with the image as a base64 data
        URI.

        Requires ``matplotlib`` (used by :class:`ChartRenderer`).
        """
        from firefly_dworkers.design.charts import ChartRenderer

        renderer = ChartRenderer()
        png_bytes = renderer.render_to_image_sync(chart)
        return PDFTool.embed_image(png_bytes, alt=chart.title or "Chart")

    @staticmethod
    def professional_css() -> str:
        """Return the built-in professional CSS stylesheet.

        Useful when callers want to inspect or extend the defaults.
        """
        return _PROFESSIONAL_CSS
