"""Tests for DiagramRenderer -- rendering DiagramSpec to PNG bytes."""

from __future__ import annotations

import pytest

from firefly_dworkers.design.diagrams import DiagramRenderer
from firefly_dworkers.design.models import DiagramSpec


# ── DiagramSpec model tests ──────────────────────────────────────────────────


class TestDiagramSpec:
    def test_defaults(self) -> None:
        spec = DiagramSpec()
        assert spec.diagram_type == "flowchart"
        assert spec.dot_source == ""

    def test_with_dot(self) -> None:
        spec = DiagramSpec(dot_source="digraph { A -> B }")
        assert spec.dot_source == "digraph { A -> B }"


# ── DOT rendering (graphviz) ────────────────────────────────────────────────


class TestDiagramRendererDot:
    async def test_render_dot_produces_png(self) -> None:
        pytest.importorskip("graphviz")
        renderer = DiagramRenderer()
        spec = DiagramSpec(dot_source="digraph { A -> B -> C }")
        png = await renderer.render(spec)
        assert len(png) > 0
        assert png[:4] == b"\x89PNG"

    async def test_render_dot_complex(self) -> None:
        pytest.importorskip("graphviz")
        renderer = DiagramRenderer()
        spec = DiagramSpec(
            dot_source="digraph { rankdir=LR; A [shape=box]; B [shape=diamond]; A -> B -> C }"
        )
        png = await renderer.render(spec)
        assert png[:4] == b"\x89PNG"


# ── Fallback rendering (matplotlib) ─────────────────────────────────────────


class TestDiagramRendererFallback:
    async def test_render_fallback_produces_png(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = DiagramRenderer()
        spec = DiagramSpec(title="Architecture Overview")
        png = await renderer.render(spec)
        assert len(png) > 0
        assert png[:4] == b"\x89PNG"

    async def test_render_no_dot_no_title(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = DiagramRenderer()
        spec = DiagramSpec()
        png = await renderer.render(spec)
        assert png[:4] == b"\x89PNG"
