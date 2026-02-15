"""Tests for the enhanced thinking indicator with rotating verbs."""

import pytest

from firefly_dworkers_cli.tui.widgets.thinking_indicator import (
    SPINNER_FRAMES,
    THINKING_VERBS,
    ThinkingIndicator,
)


class TestThinkingVerbs:
    def test_verb_pool_has_at_least_15_entries(self):
        assert len(THINKING_VERBS) >= 15

    def test_each_verb_ends_with_ellipsis(self):
        for verb in THINKING_VERBS:
            assert verb.endswith("..."), f"Verb missing ellipsis: {verb}"

    def test_no_emoji_in_verbs(self):
        for verb in THINKING_VERBS:
            # Verbs should be plain ASCII text, no emoji codepoints
            assert all(ord(c) < 0x1F600 for c in verb), f"Emoji found in verb: {verb}"

    def test_no_duplicate_verbs(self):
        assert len(THINKING_VERBS) == len(set(THINKING_VERBS))


class TestSpinnerFrames:
    def test_frames_are_single_characters(self):
        for frame in SPINNER_FRAMES:
            assert len(frame) == 1, f"Frame should be a single char: {frame!r}"

    def test_frames_are_ascii(self):
        for frame in SPINNER_FRAMES:
            assert all(ord(c) < 128 for c in frame), f"Non-ASCII in frame: {frame!r}"

    def test_no_emoji_in_frames(self):
        for frame in SPINNER_FRAMES:
            assert all(ord(c) < 0x1F600 for c in frame), f"Emoji found in frame: {frame!r}"


class TestThinkingIndicatorInit:
    def test_creates_with_random_verb(self):
        indicator = ThinkingIndicator()
        text = str(indicator.render())
        found = any(verb in text for verb in THINKING_VERBS)
        assert found, f"Initial text '{text}' doesn't contain any thinking verb"

    def test_initial_text_has_spinner_char(self):
        indicator = ThinkingIndicator()
        text = str(indicator.render())
        has_spinner = any(frame in text for frame in SPINNER_FRAMES)
        assert has_spinner, f"Initial text should contain a spinner char: {text!r}"

    def test_verb_rotation_advances_index(self):
        indicator = ThinkingIndicator()
        first_verb_idx = indicator._verb_index
        indicator._rotate_verb()
        second_verb_idx = indicator._verb_index
        assert first_verb_idx != second_verb_idx
