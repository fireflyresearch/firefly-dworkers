"""Tests for the agent greeting prompt."""

from firefly_dworkers_cli.tui.app import DworkersApp

GREETING_PROMPT = DworkersApp.GREETING_PROMPT


def test_greeting_prompt_exists():
    assert GREETING_PROMPT
    assert "introduce" in GREETING_PROMPT.lower() or "invited" in GREETING_PROMPT.lower()


def test_greeting_prompt_requests_brevity():
    assert "brief" in GREETING_PROMPT.lower() or "1-2" in GREETING_PROMPT
