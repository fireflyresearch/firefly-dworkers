"""Tests that all worker prompts include personality and brevity sections."""

from pathlib import Path

PROMPT_DIR = Path("src/firefly_dworkers/prompts/workers")
WORKERS = ["manager", "analyst", "researcher", "data_analyst", "designer"]


class TestPromptPersonality:
    def test_all_workers_have_response_style(self):
        for worker in WORKERS:
            template = (PROMPT_DIR / f"{worker}.j2").read_text()
            assert "## Response Style" in template, (
                f"{worker}.j2 missing '## Response Style' section"
            )

    def test_all_workers_have_personality(self):
        for worker in WORKERS:
            template = (PROMPT_DIR / f"{worker}.j2").read_text()
            assert "## Your Personality" in template, (
                f"{worker}.j2 missing '## Your Personality' section"
            )

    def test_brevity_instructions_present(self):
        for worker in WORKERS:
            template = (PROMPT_DIR / f"{worker}.j2").read_text()
            assert "Casual" in template or "casual" in template, (
                f"{worker}.j2 missing casual response guidance"
            )
