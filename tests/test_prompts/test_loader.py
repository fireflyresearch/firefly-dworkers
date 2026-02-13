"""Tests for the Jinja2 prompt management system."""

from __future__ import annotations

import pytest
from fireflyframework_genai.prompts.registry import prompt_registry

from firefly_dworkers.prompts import _loader, get_worker_prompt, load_prompts


class TestPromptLoader:
    def setup_method(self) -> None:
        prompt_registry.clear()
        _loader._loaded = False

    def test_load_prompts_registers_worker_templates(self) -> None:
        load_prompts()

        assert prompt_registry.has("worker/analyst")
        assert prompt_registry.has("worker/researcher")
        assert prompt_registry.has("worker/data_analyst")
        assert prompt_registry.has("worker/manager")

    def test_get_worker_prompt_returns_string(self) -> None:
        load_prompts()

        result = get_worker_prompt("analyst", company_name="Acme Corp")
        assert isinstance(result, str)
        assert "Acme Corp" in result

    def test_get_worker_prompt_includes_verticals(self) -> None:
        load_prompts()

        result = get_worker_prompt(
            "analyst",
            company_name="TestCo",
            verticals="Specialise in banking and financial services.",
        )
        assert "banking" in result.lower()

    def test_get_worker_prompt_includes_custom_instructions(self) -> None:
        load_prompts()

        result = get_worker_prompt(
            "researcher",
            company_name="TestCo",
            custom_instructions="Always cite sources in APA format.",
        )
        assert "Always cite sources in APA format." in result

    def test_get_worker_prompt_unknown_role_raises(self) -> None:
        load_prompts()

        with pytest.raises(KeyError, match="nonexistent"):
            get_worker_prompt("nonexistent")

    def test_load_prompts_idempotent(self) -> None:
        load_prompts()
        load_prompts()

        # Should not raise and templates should still be registered
        assert prompt_registry.has("worker/analyst")
        assert prompt_registry.has("worker/researcher")
        assert prompt_registry.has("worker/data_analyst")
        assert prompt_registry.has("worker/manager")
