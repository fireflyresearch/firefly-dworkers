"""Tests for user context injection into worker prompts."""

from __future__ import annotations

import pytest

from firefly_dworkers.prompts import get_worker_prompt, load_prompts


class TestUserContextInPrompts:
    @pytest.fixture(autouse=True)
    def _load(self):
        load_prompts()

    @pytest.mark.parametrize("role", ["manager", "analyst", "researcher", "data_analyst", "designer"])
    def test_worker_prompt_includes_user_name(self, role):
        prompt = get_worker_prompt(
            role,
            user_name="Antonio",
            user_role="CTO",
            user_company="Firefly Research",
        )
        assert "Antonio" in prompt

    @pytest.mark.parametrize("role", ["manager", "analyst", "researcher", "data_analyst", "designer"])
    def test_worker_prompt_includes_worker_identity(self, role):
        prompt = get_worker_prompt(
            role,
            worker_display_name="TestName",
        )
        assert "TestName" in prompt

    @pytest.mark.parametrize("role", ["manager", "analyst", "researcher", "data_analyst", "designer"])
    def test_worker_prompt_omits_user_section_when_empty(self, role):
        prompt = get_worker_prompt(role)
        assert "USER CONTEXT" not in prompt
