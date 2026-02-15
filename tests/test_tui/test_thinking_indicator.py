"""Tests for the enhanced thinking indicator with rotating verbs."""

import pytest

from firefly_dworkers_cli.tui.widgets.thinking_indicator import (
    THINKING_VERBS,
    ThinkingIndicator,
)


class TestThinkingVerbs:
    def test_verb_pool_has_at_least_15_entries(self):
        assert len(THINKING_VERBS) >= 15

    def test_each_verb_ends_with_ellipsis(self):
        for emoji, verb in THINKING_VERBS:
            assert verb.endswith("..."), f"Verb missing ellipsis: {verb}"

    def test_each_verb_has_emoji(self):
        for emoji, verb in THINKING_VERBS:
            assert len(emoji) > 0, f"Missing emoji for verb: {verb}"

    def test_no_duplicate_verbs(self):
        verbs = [v for _, v in THINKING_VERBS]
        assert len(verbs) == len(set(verbs))


class TestThinkingIndicatorInit:
    def test_creates_with_random_verb(self):
        indicator = ThinkingIndicator()
        text = str(indicator.render())
        found = any(verb in text for _, verb in THINKING_VERBS)
        assert found, f"Initial text '{text}' doesn't contain any thinking verb"

    def test_verb_rotation_advances_index(self):
        indicator = ThinkingIndicator()
        first_verb_idx = indicator._verb_index
        indicator._rotate_verb()
        second_verb_idx = indicator._verb_index
        assert first_verb_idx != second_verb_idx
