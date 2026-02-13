"""Tests for ChartRenderer -- rendering ResolvedChart to PNG, PPTX, and XLSX."""

from __future__ import annotations

import pytest

from firefly_dworkers.design.charts import ChartRenderer
from firefly_dworkers.design.models import DataSeries, ResolvedChart


# ── Helpers ─────────────────────────────────────────────────────────────────


def _bar_chart(**overrides: object) -> ResolvedChart:
    defaults: dict[str, object] = {
        "chart_type": "bar",
        "title": "Revenue",
        "categories": ["Q1", "Q2", "Q3"],
        "series": [DataSeries(name="2025", values=[100, 200, 300])],
    }
    defaults.update(overrides)
    return ResolvedChart(**defaults)  # type: ignore[arg-type]


def _line_chart() -> ResolvedChart:
    return ResolvedChart(
        chart_type="line",
        title="Trend",
        categories=["Jan", "Feb", "Mar"],
        series=[DataSeries(name="Sales", values=[10, 20, 30])],
    )


def _pie_chart() -> ResolvedChart:
    return ResolvedChart(
        chart_type="pie",
        title="Market Share",
        categories=["A", "B", "C"],
        series=[DataSeries(name="Share", values=[40, 35, 25])],
    )


def _scatter_chart() -> ResolvedChart:
    return ResolvedChart(
        chart_type="scatter",
        title="Scatter",
        categories=[],
        series=[DataSeries(name="Points", values=[1, 4, 9, 16])],
    )


def _area_chart() -> ResolvedChart:
    return ResolvedChart(
        chart_type="area",
        title="Coverage",
        categories=["W1", "W2", "W3"],
        series=[DataSeries(name="Coverage", values=[60, 70, 80])],
    )


def _doughnut_chart() -> ResolvedChart:
    return ResolvedChart(
        chart_type="doughnut",
        title="Distribution",
        categories=["X", "Y", "Z"],
        series=[DataSeries(name="Dist", values=[50, 30, 20])],
    )


# ── render_to_image (matplotlib) ───────────────────────────────────────────


class TestChartRendererImage:
    """Tests for PNG rendering via matplotlib."""

    async def test_render_bar_chart_to_png(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_bar_chart())
        assert len(png_bytes) > 0
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_line_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_line_chart())
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_pie_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_pie_chart())
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_scatter_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_scatter_chart())
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_area_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_area_chart())
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_doughnut_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_doughnut_chart())
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_with_custom_dimensions(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        png_bytes = await renderer.render_to_image(_bar_chart(), width=400, height=300)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_with_colors(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = _bar_chart(colors=["#ff0000", "#00ff00", "#0000ff"])
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_with_data_labels(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = _bar_chart(show_data_labels=True)
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_stacked_bar_chart(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = ResolvedChart(
            chart_type="bar",
            title="Stacked Revenue",
            categories=["Q1", "Q2"],
            series=[
                DataSeries(name="Product A", values=[100, 150]),
                DataSeries(name="Product B", values=[80, 120]),
            ],
            stacked=True,
        )
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_multi_series_bar(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = ResolvedChart(
            chart_type="bar",
            title="Multi-Series",
            categories=["Q1", "Q2", "Q3"],
            series=[
                DataSeries(name="2024", values=[100, 200, 300]),
                DataSeries(name="2025", values=[120, 220, 320]),
            ],
        )
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_chart_without_title(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = _bar_chart(title="")
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_chart_without_legend(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = _bar_chart(show_legend=False)
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"

    async def test_render_unknown_type_falls_back(self) -> None:
        pytest.importorskip("matplotlib")
        renderer = ChartRenderer()
        chart = ResolvedChart(
            chart_type="waterfall",
            title="Fallback",
            categories=["A", "B"],
            series=[DataSeries(name="S1", values=[10, 20])],
        )
        png_bytes = await renderer.render_to_image(chart)
        assert png_bytes[:4] == b"\x89PNG"


# ── render_for_pptx (native python-pptx charts) ────────────────────────────


class TestChartRendererPptx:
    """Tests for native PPTX chart generation."""

    def test_render_bar_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
        renderer.render_for_pptx(_bar_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1
        assert chart_shapes[0].chart.chart_title.text_frame.text == "Revenue"

    def test_render_line_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(_line_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_pie_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(_pie_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_scatter_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(_scatter_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_doughnut_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(_doughnut_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_area_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(_area_chart(), slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_stacked_bar_chart_on_slide(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        chart = _bar_chart(stacked=True)
        renderer.render_for_pptx(chart, slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_chart_with_legend_disabled(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        chart = _bar_chart(show_legend=False)
        renderer.render_for_pptx(chart, slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1
        assert chart_shapes[0].chart.has_legend is False

    def test_render_chart_without_title(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        chart = _bar_chart(title="")
        renderer.render_for_pptx(chart, slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_custom_position(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        renderer.render_for_pptx(
            _bar_chart(),
            slide,
            left=500000,
            top=500000,
            width=5000000,
            height=3000000,
        )

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1

    def test_render_unknown_type_falls_back(self) -> None:
        pptx_mod = pytest.importorskip("pptx")
        renderer = ChartRenderer()
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        chart = ResolvedChart(
            chart_type="waterfall",
            title="Fallback",
            categories=["A", "B"],
            series=[DataSeries(name="S1", values=[10, 20])],
        )
        renderer.render_for_pptx(chart, slide)

        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1


# ── render_for_xlsx (native openpyxl charts) ────────────────────────────────


class TestChartRendererXlsx:
    """Tests for native XLSX chart generation."""

    def test_render_bar_chart_on_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_bar_chart(), ws)
        assert len(ws._charts) == 1

    def test_render_line_chart_on_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_line_chart(), ws)
        assert len(ws._charts) == 1

    def test_render_pie_chart_on_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_pie_chart(), ws)
        assert len(ws._charts) == 1

    def test_render_area_chart_on_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_area_chart(), ws)
        assert len(ws._charts) == 1

    def test_render_doughnut_chart_on_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_doughnut_chart(), ws)
        assert len(ws._charts) == 1

    def test_render_chart_with_title(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_bar_chart(), ws)
        # openpyxl wraps the title in a Title object; verify it was set
        title_obj = ws._charts[0].title
        assert title_obj is not None
        # Extract text from the Title's rich text paragraphs
        text_parts = [r.t for p in title_obj.tx.rich.paragraphs for r in p.r]
        assert "Revenue" in text_parts

    def test_render_chart_at_custom_cell(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_bar_chart(), ws, cell="A10")
        assert len(ws._charts) == 1

    def test_render_stacked_bar_chart(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        chart = _bar_chart(stacked=True)
        renderer.render_for_xlsx(chart, ws)
        assert len(ws._charts) == 1
        assert ws._charts[0].grouping == "stacked"

    def test_render_chart_without_legend(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        chart = _bar_chart(show_legend=False)
        renderer.render_for_xlsx(chart, ws)
        assert len(ws._charts) == 1
        assert ws._charts[0].legend is None

    def test_render_unknown_type_falls_back(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        chart = ResolvedChart(
            chart_type="waterfall",
            title="Fallback",
            categories=["A", "B"],
            series=[DataSeries(name="S1", values=[10, 20])],
        )
        renderer.render_for_xlsx(chart, ws)
        assert len(ws._charts) == 1

    def test_data_written_to_helper_area(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_bar_chart(), ws)
        # Data is written starting at column 50 (AX)
        assert ws.cell(row=2, column=50).value == "2025"
        assert ws.cell(row=2, column=51).value == 100.0

    def test_multiple_charts_on_same_worksheet(self) -> None:
        openpyxl_mod = pytest.importorskip("openpyxl")
        renderer = ChartRenderer()
        wb = openpyxl_mod.Workbook()
        ws = wb.active
        renderer.render_for_xlsx(_bar_chart(), ws, cell="E1")
        renderer.render_for_xlsx(_line_chart(), ws, cell="E20")
        assert len(ws._charts) == 2
