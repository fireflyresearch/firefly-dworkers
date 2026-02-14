"""Tests for VLM visual refinement loop."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.design.refinement import (
    PositionFix,
    RefinementFeedback,
    VisualRefiner,
)


def _make_pptx_bytes() -> bytes:
    """Create a minimal valid PPTX in memory and return its bytes."""
    pptx_mod = pytest.importorskip("pptx")
    prs = pptx_mod.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Test"
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


class TestApplyFixes:
    def test_apply_fixes_moves_shape(self) -> None:
        """Verify new_left/top applied to shape."""
        pptx_mod = pytest.importorskip("pptx")
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        title.text = "Move Me"
        shape_name = title.name
        buf = io.BytesIO()
        prs.save(buf)
        original = buf.getvalue()

        fix = PositionFix(
            slide_index=0,
            shape_name=shape_name,
            issue="too far left",
            fix_type="move",
            new_left=914400,  # 1 inch
            new_top=1828800,  # 2 inches
        )
        result = VisualRefiner._apply_fixes(original, [fix])

        # Verify the shape was moved
        prs2 = pptx_mod.Presentation(io.BytesIO(result))
        moved_shape = None
        for shape in prs2.slides[0].shapes:
            if shape.name == shape_name:
                moved_shape = shape
                break
        assert moved_shape is not None
        assert moved_shape.left == 914400
        assert moved_shape.top == 1828800

    def test_apply_fixes_resizes_shape(self) -> None:
        """Verify new_width/height applied to shape."""
        pptx_mod = pytest.importorskip("pptx")
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        title.text = "Resize Me"
        shape_name = title.name
        buf = io.BytesIO()
        prs.save(buf)
        original = buf.getvalue()

        fix = PositionFix(
            slide_index=0,
            shape_name=shape_name,
            issue="too wide",
            fix_type="resize",
            new_width=4572000,
            new_height=914400,
        )
        result = VisualRefiner._apply_fixes(original, [fix])

        prs2 = pptx_mod.Presentation(io.BytesIO(result))
        resized = None
        for shape in prs2.slides[0].shapes:
            if shape.name == shape_name:
                resized = shape
                break
        assert resized is not None
        assert resized.width == 4572000
        assert resized.height == 914400

    def test_apply_fixes_unknown_shape_ignored(self) -> None:
        """Fix targeting nonexistent shape name doesn't crash."""
        pptx_mod = pytest.importorskip("pptx")
        original = _make_pptx_bytes()
        fix = PositionFix(
            slide_index=0,
            shape_name="NonexistentShape",
            fix_type="move",
            new_left=0,
        )
        result = VisualRefiner._apply_fixes(original, [fix])
        # Should return valid PPTX unchanged
        prs = pptx_mod.Presentation(io.BytesIO(result))
        assert len(prs.slides) == 1


class TestVisualRefinerLoop:
    async def test_max_iterations_respected(self) -> None:
        """Stops after max_iterations even if not acceptable."""
        pytest.importorskip("pptx")
        original = _make_pptx_bytes()

        refiner = VisualRefiner(vlm_model="test", max_iterations=2)

        # VLM always returns not acceptable with a fix
        never_acceptable = RefinementFeedback(
            slide_index=0,
            score=3.0,
            is_acceptable=False,
            position_fixes=[
                PositionFix(
                    slide_index=0,
                    shape_name="NonexistentShape",  # won't match, but loop continues
                    fix_type="move",
                    new_left=100,
                )
            ],
        )

        with (
            patch.object(
                refiner, "_render_slides", new_callable=AsyncMock,
                return_value=[b"fake_png"],
            ),
            patch.object(
                refiner, "_evaluate_slide", new_callable=AsyncMock,
                return_value=never_acceptable,
            ) as mock_eval,
        ):
            result = await refiner.refine(original)
            # Should have been called once per slide per iteration
            assert mock_eval.call_count == 2  # 2 iterations x 1 slide
            assert isinstance(result, bytes)
            assert len(result) > 0

    async def test_all_acceptable_skips_further_iterations(self) -> None:
        """When all slides acceptable, no re-render needed."""
        pytest.importorskip("pptx")
        original = _make_pptx_bytes()

        refiner = VisualRefiner(vlm_model="test", max_iterations=3)

        acceptable = RefinementFeedback(
            slide_index=0, score=8.0, is_acceptable=True, position_fixes=[]
        )

        with (
            patch.object(
                refiner, "_render_slides", new_callable=AsyncMock,
                return_value=[b"fake_png"],
            ) as mock_render,
            patch.object(
                refiner, "_evaluate_slide", new_callable=AsyncMock,
                return_value=acceptable,
            ),
        ):
            result = await refiner.refine(original)
            # Only 1 render call (first iteration), stops because acceptable
            assert mock_render.call_count == 1
            assert isinstance(result, bytes)

    async def test_refine_returns_original_when_render_fails(self) -> None:
        """Graceful fallback when rendering fails."""
        pytest.importorskip("pptx")
        original = _make_pptx_bytes()

        refiner = VisualRefiner(vlm_model="test", max_iterations=2)

        with patch.object(
            refiner, "_render_slides", new_callable=AsyncMock,
            side_effect=RuntimeError("render failed"),
        ):
            result = await refiner.refine(original)
            assert result == original

    async def test_refine_returns_original_when_vlm_fails(self) -> None:
        """Graceful fallback when VLM evaluation fails."""
        pytest.importorskip("pptx")
        original = _make_pptx_bytes()

        refiner = VisualRefiner(vlm_model="test", max_iterations=2)

        with (
            patch.object(
                refiner, "_render_slides", new_callable=AsyncMock,
                return_value=[b"fake_png"],
            ),
            patch.object(
                refiner, "_evaluate_slide", new_callable=AsyncMock,
                side_effect=RuntimeError("VLM unavailable"),
            ),
        ):
            result = await refiner.refine(original)
            # All evaluations failed → all_acceptable stays True → returns current
            assert isinstance(result, bytes)
            assert len(result) > 0
