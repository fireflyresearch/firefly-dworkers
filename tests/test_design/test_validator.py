"""Tests for SlideValidator -- VLM visual validation loop (mocked, no API calls)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.design.validator import (
    SLIDE_EVALUATION_PROMPT,
    SlideIssue,
    SlideValidationFeedback,
    SlideValidator,
    ValidationResult,
)


class TestValidationModels:
    """Tests for validator data models."""

    def test_validation_result_structure(self) -> None:
        result = ValidationResult(
            overall_score=7.5,
            issues=[
                SlideIssue(
                    slide_index=0,
                    severity="moderate",
                    category="alignment",
                    description="Title slightly off-center",
                    suggestion="Center the title text",
                )
            ],
            strengths=["Good color palette"],
            summary="1 slide evaluated.",
        )
        assert result.overall_score == 7.5
        assert len(result.issues) == 1
        assert result.issues[0].severity == "moderate"
        assert result.issues[0].category == "alignment"
        assert len(result.strengths) == 1

    def test_slide_validation_feedback_structure(self) -> None:
        feedback = SlideValidationFeedback(
            score=8.0,
            issues=[],
            strengths=["Clean layout", "Professional colors"],
        )
        assert feedback.score == 8.0
        assert len(feedback.strengths) == 2

    def test_system_prompt_criteria(self) -> None:
        """Verify the system prompt mentions key quality criteria."""
        prompt = SLIDE_EVALUATION_PROMPT.lower()
        assert "alignment" in prompt
        assert "color" in prompt
        assert "typography" in prompt
        assert "spacing" in prompt
        assert "chart" in prompt
        assert "table" in prompt
        assert "mckinsey" in prompt or "bain" in prompt


class TestSlideValidatorWithMock:
    """Tests for the SlideValidator flow with mocked agent (no API calls)."""

    async def test_validator_with_mocked_agent(self) -> None:
        """Mock agent, verify flow end-to-end."""
        pptx_mod = pytest.importorskip("pptx")
        pytest.importorskip("matplotlib")

        import tempfile

        # Create a minimal PPTX
        prs = pptx_mod.Presentation()
        prs.slides.add_slide(prs.slide_layouts[6])
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            prs.save(f.name)
            tmp_path = f.name

        # Mock the FireflyAgent
        mock_feedback = SlideValidationFeedback(
            score=8.5,
            issues=[
                SlideIssue(
                    slide_index=0,
                    severity="minor",
                    category="spacing",
                    description="Slight crowding at bottom",
                    suggestion="Add more bottom margin",
                )
            ],
            strengths=["Clean layout"],
        )
        mock_result = MagicMock()
        mock_result.output = mock_feedback

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        validator = SlideValidator(model="test-model")
        validator._agent = mock_agent  # Inject mock

        result = await validator.validate(tmp_path)
        assert isinstance(result, ValidationResult)
        assert result.overall_score == 8.5
        assert len(result.issues) == 1
        assert result.issues[0].category == "spacing"
        assert "1 slide" in result.summary
        mock_agent.run.assert_called_once()

    async def test_validator_multi_slide(self) -> None:
        """Validate multi-slide presentation with varying scores."""
        pptx_mod = pytest.importorskip("pptx")
        pytest.importorskip("matplotlib")

        import tempfile

        prs = pptx_mod.Presentation()
        prs.slides.add_slide(prs.slide_layouts[6])
        prs.slides.add_slide(prs.slide_layouts[6])
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            prs.save(f.name)
            tmp_path = f.name

        feedbacks = [
            SlideValidationFeedback(score=9.0, issues=[], strengths=["Excellent"]),
            SlideValidationFeedback(score=7.0, issues=[
                SlideIssue(
                    slide_index=1, severity="moderate", category="color",
                    description="Low contrast", suggestion="Increase contrast",
                ),
            ], strengths=["Good structure"]),
        ]
        call_count = 0

        async def mock_run(messages):
            nonlocal call_count
            result = MagicMock()
            result.output = feedbacks[call_count]
            call_count += 1
            return result

        mock_agent = MagicMock()
        mock_agent.run = mock_run

        validator = SlideValidator(model="test-model")
        validator._agent = mock_agent

        result = await validator.validate(tmp_path)
        assert result.overall_score == 8.0  # (9+7)/2
        assert len(result.issues) == 1
        assert "2 slide" in result.summary

    async def test_validator_handles_agent_error(self) -> None:
        """Validator should not crash when agent raises an error."""
        pptx_mod = pytest.importorskip("pptx")
        pytest.importorskip("matplotlib")

        import tempfile

        prs = pptx_mod.Presentation()
        prs.slides.add_slide(prs.slide_layouts[6])
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            prs.save(f.name)
            tmp_path = f.name

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("API error"))

        validator = SlideValidator(model="test-model")
        validator._agent = mock_agent

        result = await validator.validate(tmp_path)
        assert result.overall_score == 0.0
        assert "1 slide" in result.summary
