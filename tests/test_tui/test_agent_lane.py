"""Tests for the AgentLane widget."""

from firefly_dworkers_cli.tui.widgets.agent_lane import AgentLane


class TestAgentLane:
    def test_create_with_role(self):
        lane = AgentLane(role="analyst", step_index=1, total_steps=3)
        assert lane._role == "analyst"
        assert lane._step_index == 1
        assert lane._status == "waiting"

    def test_mark_running(self):
        lane = AgentLane(role="analyst", step_index=1, total_steps=3)
        lane.mark_running()
        assert lane._status == "running"

    def test_mark_complete(self):
        lane = AgentLane(role="analyst", step_index=1, total_steps=3)
        lane.mark_complete(tokens=2143, duration_s=61.8)
        assert lane._status == "complete"
        assert lane._tokens == 2143
        assert lane._duration_s == 61.8

    def test_mark_error(self):
        lane = AgentLane(role="analyst", step_index=1, total_steps=3)
        lane.mark_error("Connection failed")
        assert lane._status == "error"

    def test_completion_summary(self):
        lane = AgentLane(role="analyst", step_index=1, total_steps=3)
        lane.mark_complete(tokens=2143, duration_s=61.8)
        summary = lane._completion_summary()
        assert "2,143" in summary
        assert "61.8s" in summary
        assert "\u2713" in summary
