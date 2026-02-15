"""Tests for participant context injection into prompts."""


def test_build_participant_context_empty():
    from firefly_dworkers_cli.tui.backend.local import _build_participant_context
    assert _build_participant_context([], "manager") == ""


def test_build_participant_context_single_agent():
    from firefly_dworkers_cli.tui.backend.local import _build_participant_context
    result = _build_participant_context(
        [("analyst", "Leo", "Strategic analysis")],
        "manager",
    )
    assert "Leo" in result
    assert "analyst" in result


def test_build_participant_context_excludes_self():
    from firefly_dworkers_cli.tui.backend.local import _build_participant_context
    result = _build_participant_context(
        [("analyst", "Leo", "Analysis"), ("manager", "Amara", "Management")],
        "manager",
    )
    assert "Leo" in result
    assert "Amara" not in result


def test_build_participant_context_multiple():
    from firefly_dworkers_cli.tui.backend.local import _build_participant_context
    result = _build_participant_context(
        [
            ("analyst", "Leo", "Analysis"),
            ("researcher", "Yuki", "Research"),
        ],
        "analyst",
    )
    assert "Yuki" in result
    assert "Leo" not in result
