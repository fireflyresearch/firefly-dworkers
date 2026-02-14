"""VLM-based visual validation for presentation quality.

Sends slide preview PNGs to a Claude vision model via ``fireflyframework-genai``
for consulting-quality evaluation. This is an optional quality gate — basic
PPTX generation works without it.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Data models ────────────────────────────────────────────────────────────


class SlideIssue(BaseModel):
    """A single quality issue identified on a slide."""

    slide_index: int
    severity: str  # minor, moderate, critical
    category: str  # alignment, color, typography, spacing, chart, table
    description: str
    suggestion: str


class SlideValidationFeedback(BaseModel):
    """Structured VLM output for a single slide evaluation."""

    score: float = Field(ge=0, le=10)
    issues: list[SlideIssue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Aggregated validation result across all slides."""

    overall_score: float = Field(ge=0, le=10)
    issues: list[SlideIssue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    summary: str = ""


# ── System prompt ──────────────────────────────────────────────────────────

SLIDE_EVALUATION_PROMPT = """\
You are a senior presentation designer at a top-tier consulting firm \
(McKinsey, Bain, BCG). Evaluate this slide preview image for visual quality.

Rate the slide from 0-10 where:
- 0-3: Unacceptable (poor layout, clashing colors, unreadable text)
- 4-5: Needs improvement (functional but unprofessional)
- 6-7: Acceptable (clean, readable, reasonable styling)
- 8-9: Professional (polished, cohesive, consulting-quality)
- 10: Exceptional (perfect layout, typography, and visual hierarchy)

Evaluate these criteria:
1. **Alignment** — Are elements properly aligned? Is there visual balance?
2. **Color** — Are colors cohesive, professional, and accessible?
3. **Typography** — Are fonts readable, consistent, and well-sized?
4. **Spacing** — Is whitespace used effectively? No crowding?
5. **Charts** — Are data visualizations clear with proper labels?
6. **Tables** — Are tables styled with clear headers and alternating rows?
7. **Visual Hierarchy** — Is the information hierarchy clear?

For each issue found, provide the category, severity, description, and suggestion.
Also note strengths of the slide design.\
"""


# ── Validator ──────────────────────────────────────────────────────────────


class SlideValidator:
    """Validates PPTX quality by sending preview images to a VLM.

    Parameters
    ----------
    model : str
        Model identifier for the VLM agent (e.g. ``"claude-sonnet-4-5-20250929"``).
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929") -> None:
        self._model = model
        self._agent: Any = None

    def _get_agent(self) -> Any:
        """Lazy-init the FireflyAgent for slide evaluation."""
        if self._agent is not None:
            return self._agent

        from fireflyframework_genai.agents.base import FireflyAgent

        self._agent = FireflyAgent(
            "slide-quality-reviewer",
            model=self._model,
            instructions=SLIDE_EVALUATION_PROMPT,
            output_type=SlideValidationFeedback,
            auto_register=False,
        )
        return self._agent

    async def validate(self, pptx_path: str) -> ValidationResult:
        """Validate all slides in a PPTX file.

        Renders previews via :class:`SlidePreviewRenderer`, then sends each
        to the VLM for quality evaluation. Returns an aggregated result.
        """
        from fireflyframework_genai.types import BinaryContent

        from firefly_dworkers.design.preview import SlidePreviewRenderer

        renderer = SlidePreviewRenderer(dpi=150)
        png_list = await renderer.render_presentation(pptx_path)

        if not png_list:
            return ValidationResult(
                overall_score=0.0,
                summary="No slides found in presentation.",
            )

        agent = self._get_agent()
        all_issues: list[SlideIssue] = []
        all_strengths: list[str] = []
        scores: list[float] = []

        for idx, png_bytes in enumerate(png_list):
            try:
                result = await agent.run(
                    [
                        f"Evaluate slide {idx + 1} of {len(png_list)}.",
                        BinaryContent(data=png_bytes, media_type="image/png"),
                    ]
                )
                feedback: SlideValidationFeedback = result.output
                scores.append(feedback.score)
                # Stamp slide_index onto each issue
                for issue in feedback.issues:
                    issue.slide_index = idx
                all_issues.extend(feedback.issues)
                all_strengths.extend(feedback.strengths)
            except Exception:
                logger.warning("VLM evaluation failed for slide %d", idx, exc_info=True)
                scores.append(0.0)

        overall = sum(scores) / len(scores) if scores else 0.0

        # Build summary
        critical = sum(1 for i in all_issues if i.severity == "critical")
        moderate = sum(1 for i in all_issues if i.severity == "moderate")
        summary = (
            f"Evaluated {len(png_list)} slide(s). "
            f"Average score: {overall:.1f}/10. "
            f"Issues: {critical} critical, {moderate} moderate, "
            f"{len(all_issues) - critical - moderate} minor."
        )

        return ValidationResult(
            overall_score=round(overall, 1),
            issues=all_issues,
            strengths=all_strengths,
            summary=summary,
        )
