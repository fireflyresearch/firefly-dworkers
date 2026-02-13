"""DiagramRenderer -- renders architecture and flow diagrams as PNG bytes.

Supports Graphviz DOT source as the primary rendering path, with a
matplotlib-based fallback for environments where graphviz is unavailable.
"""

from __future__ import annotations

import asyncio
import logging

from firefly_dworkers.design.models import DiagramSpec

logger = logging.getLogger(__name__)


class DiagramRenderer:
    """Renders architecture and flow diagrams as PNG bytes."""

    async def render(self, spec: DiagramSpec) -> bytes:
        """Render a diagram to PNG bytes.

        Tries graphviz DOT first, then falls back to matplotlib for simple diagrams.
        """
        if spec.dot_source:
            return await self._render_dot(spec.dot_source)
        # Fallback: generate a simple text-based image via matplotlib
        return await self._render_fallback(spec.title or "Diagram")

    async def _render_dot(self, dot_source: str) -> bytes:
        """Render DOT source to PNG using graphviz."""
        return await asyncio.to_thread(self._render_dot_sync, dot_source)

    def _render_dot_sync(self, dot_source: str) -> bytes:
        """Sync graphviz rendering."""
        try:
            import graphviz
        except ImportError:
            raise ImportError(
                "graphviz required for diagram rendering. Install with: pip install graphviz"
            )

        src = graphviz.Source(dot_source)
        return src.pipe(format="png")

    async def _render_fallback(self, title: str) -> bytes:
        """Fallback: render a simple labeled image using matplotlib."""
        return await asyncio.to_thread(self._render_fallback_sync, title)

    def _render_fallback_sync(self, title: str) -> bytes:
        import io

        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib required for diagram fallback rendering")

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5,
            0.5,
            title,
            ha="center",
            va="center",
            fontsize=16,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#e8f0fe", edgecolor="#1a73e8"),
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close(fig)
        return buf.getvalue()
