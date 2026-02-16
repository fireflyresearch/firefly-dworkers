"""Tests for dynamic plan detection in AI responses."""

from firefly_dworkers_cli.tui.app import DworkersApp


def _make_app():
    app = DworkersApp.__new__(DworkersApp)
    return app


class TestPlanDetection:
    def test_detects_structured_plan(self):
        app = _make_app()
        content = """Here's my plan:

1. [researcher] Investigate competitor pricing
2. [analyst] Size the market opportunity
3. [analyst] Create positioning recommendations
4. [manager] Synthesize into final strategy
"""
        result = app._detect_plan(content)
        assert result is not None
        assert len(result) == 4
        assert result[0] == ("researcher", "Investigate competitor pricing")
        assert result[3] == ("manager", "Synthesize into final strategy")

    def test_no_plan_in_regular_response(self):
        app = _make_app()
        content = "Sure, I can help with that. The market is growing at 15% annually."
        result = app._detect_plan(content)
        assert result is None

    def test_ignores_single_step(self):
        app = _make_app()
        content = "1. [analyst] Do the analysis"
        result = app._detect_plan(content)
        assert result is None

    def test_detects_plan_with_surrounding_text(self):
        app = _make_app()
        content = """I'll create a plan for this:

1. [researcher] Research the market
2. [analyst] Analyze findings

I'll start executing once you approve."""
        result = app._detect_plan(content)
        assert result is not None
        assert len(result) == 2

    def test_roles_lowercased(self):
        app = _make_app()
        content = """Plan:
1. [Researcher] Do research
2. [Analyst] Do analysis
"""
        result = app._detect_plan(content)
        assert result is not None
        assert result[0][0] == "researcher"
        assert result[1][0] == "analyst"


class TestMultiWordRoles:
    def test_detects_multi_word_role(self):
        app = _make_app()
        content = """Plan:
1. [content writer] Draft the blog post
2. [data analyst] Review the metrics
"""
        result = app._detect_plan(content)
        assert result is not None
        assert len(result) == 2
        assert result[0] == ("content_writer", "Draft the blog post")
        assert result[1] == ("data_analyst", "Review the metrics")

    def test_normalizes_spaces_to_underscores(self):
        app = _make_app()
        content = """Plan:
1. [Communications Specialist] Localize content
2. [strategist] Define strategy
"""
        result = app._detect_plan(content)
        assert result is not None
        assert result[0][0] == "communications_specialist"
        assert result[1][0] == "strategist"

    def test_mixed_single_and_multi_word_roles(self):
        app = _make_app()
        content = """Plan:
1. [researcher] Gather data
2. [content writer] Draft content
3. [manager] Review and approve
"""
        result = app._detect_plan(content)
        assert result is not None
        assert len(result) == 3
        assert result[0][0] == "researcher"
        assert result[1][0] == "content_writer"
        assert result[2][0] == "manager"
