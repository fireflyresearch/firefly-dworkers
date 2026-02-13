"""Tests for skill prompt templates."""

from __future__ import annotations

import pytest
from fireflyframework_genai.prompts.registry import prompt_registry

from firefly_dworkers.prompts import _loader, get_skill_prompt, load_prompts

SKILL_NAMES = ["powerpoint", "word", "excel", "slides", "vlm_analysis", "pdf"]


class TestSkillPrompts:
    def setup_method(self) -> None:
        prompt_registry.clear()
        _loader._loaded = False

    def test_load_discovers_skill_templates(self) -> None:
        keys = load_prompts()

        for name in SKILL_NAMES:
            assert f"skill/{name}" in keys

    def test_get_skill_prompt_powerpoint(self) -> None:
        load_prompts()

        result = get_skill_prompt("powerpoint")
        assert isinstance(result, str)
        assert "PowerPoint" in result

    def test_get_skill_prompt_word(self) -> None:
        load_prompts()

        result = get_skill_prompt("word")
        assert isinstance(result, str)
        assert "Word" in result

    def test_get_skill_prompt_excel(self) -> None:
        load_prompts()

        result = get_skill_prompt("excel")
        assert isinstance(result, str)
        assert "Excel" in result

    def test_get_skill_prompt_slides(self) -> None:
        load_prompts()

        result = get_skill_prompt("slides")
        assert isinstance(result, str)
        assert "Google Slides" in result

    def test_get_skill_prompt_vlm(self) -> None:
        load_prompts()

        result = get_skill_prompt("vlm_analysis")
        assert isinstance(result, str)
        assert "Vision" in result

    def test_get_skill_prompt_pdf(self) -> None:
        load_prompts()

        result = get_skill_prompt("pdf")
        assert isinstance(result, str)
        assert "PDF" in result

    def test_get_skill_prompt_unknown_raises(self) -> None:
        load_prompts()

        with pytest.raises(KeyError, match="nonexistent"):
            get_skill_prompt("nonexistent")

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_prompts_contain_capabilities(self, skill_name: str) -> None:
        load_prompts()

        result = get_skill_prompt(skill_name)
        assert "Capabilities" in result

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_prompts_contain_best_practices(self, skill_name: str) -> None:
        load_prompts()

        result = get_skill_prompt(skill_name)
        assert "Best practices" in result

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_prompts_contain_output_format(self, skill_name: str) -> None:
        load_prompts()

        result = get_skill_prompt(skill_name)
        assert "Output format" in result
