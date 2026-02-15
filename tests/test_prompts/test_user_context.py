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


class TestSharedFactsInPrompts:
    @pytest.fixture(autouse=True)
    def _load(self):
        load_prompts()

    @pytest.mark.parametrize("role", ["manager", "analyst", "researcher", "data_analyst", "designer"])
    def test_shared_facts_appear_in_prompt(self, role):
        prompt = get_worker_prompt(
            role,
            shared_facts={"analysis_result": "Revenue grew 12%", "market_size": "$4.2B"},
        )
        assert "Revenue grew 12%" in prompt
        assert "SHARED WORKSPACE" in prompt

    @pytest.mark.parametrize("role", ["manager", "analyst", "researcher", "data_analyst", "designer"])
    def test_no_shared_facts_section_when_empty(self, role):
        prompt = get_worker_prompt(role)
        assert "SHARED WORKSPACE" not in prompt


class TestCustomAgentTemplate:
    @pytest.fixture(autouse=True)
    def _load(self):
        load_prompts()

    def test_custom_agent_prompt_renders(self):
        prompt = get_worker_prompt(
            "custom_agent",
            worker_display_name="Security Auditor",
            mission="Audit code for security vulnerabilities.",
            skills=["Research", "Code review"],
        )
        assert "Security Auditor" in prompt
        assert "Audit code for security vulnerabilities" in prompt
        assert "Research" in prompt

    def test_custom_agent_without_shared_facts(self):
        prompt = get_worker_prompt(
            "custom_agent",
            mission="Test mission.",
            skills=["Research"],
        )
        assert "SHARED WORKSPACE" not in prompt
