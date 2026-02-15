"""Tests for intent classification."""
from __future__ import annotations


class TestHeuristicClassification:
    def test_short_question_is_chat(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        result = clf.heuristic_classify("What's the capital of France?")
        assert result == "LOW"

    def test_greeting_is_chat(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        assert clf.heuristic_classify("Hello") == "LOW"

    def test_project_keyword_is_high(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        result = clf.heuristic_classify(
            "Create a comprehensive competitive analysis report for the EV market "
            "with research on top competitors, data analysis of market trends, "
            "and a final presentation for the board."
        )
        assert result == "HIGH"

    def test_multi_step_is_high(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        result = clf.heuristic_classify(
            "First research the market, then analyze the competitors, "
            "and finally create a report with recommendations."
        )
        assert result == "HIGH"

    def test_ambiguous_request(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        result = clf.heuristic_classify(
            "Can you help me analyze our sales data from Q4?"
        )
        assert result == "AMBIGUOUS"

    def test_classify_returns_valid_values(self):
        from firefly_dworkers_cli.tui.backend.intent import IntentClassifier
        clf = IntentClassifier()
        for text in ["Hi", "Create a full market analysis report and presentation"]:
            result = clf.heuristic_classify(text)
            assert result in ("LOW", "HIGH", "AMBIGUOUS")
