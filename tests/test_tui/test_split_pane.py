"""Tests for the SplitPaneContainer widget."""

from firefly_dworkers_cli.tui.widgets.split_pane import SplitPaneContainer, grid_dimensions


class TestGridDimensions:
    def test_1_agent(self):
        assert grid_dimensions(1) == (1, 1)

    def test_2_agents(self):
        assert grid_dimensions(2) == (2, 1)

    def test_3_agents(self):
        assert grid_dimensions(3) == (2, 2)

    def test_4_agents(self):
        assert grid_dimensions(4) == (2, 2)

    def test_5_agents(self):
        assert grid_dimensions(5) == (3, 2)

    def test_6_agents(self):
        assert grid_dimensions(6) == (3, 2)


class TestSplitPaneContainer:
    def test_create(self):
        container = SplitPaneContainer(agent_count=4)
        assert container._agent_count == 4

    def test_focused_index_default(self):
        container = SplitPaneContainer(agent_count=3)
        assert container._focused_index == 0

    def test_focus_next(self):
        container = SplitPaneContainer(agent_count=3)
        container.focus_next_lane()
        assert container._focused_index == 1

    def test_focus_next_wraps(self):
        container = SplitPaneContainer(agent_count=3)
        container._focused_index = 2
        container.focus_next_lane()
        assert container._focused_index == 0

    def test_focus_prev(self):
        container = SplitPaneContainer(agent_count=3)
        container._focused_index = 2
        container.focus_prev_lane()
        assert container._focused_index == 1

    def test_focus_prev_wraps(self):
        container = SplitPaneContainer(agent_count=3)
        container._focused_index = 0
        container.focus_prev_lane()
        assert container._focused_index == 2

    def test_focus_by_number(self):
        container = SplitPaneContainer(agent_count=4)
        container.focus_lane(3)  # 1-indexed
        assert container._focused_index == 2  # 0-indexed

    def test_focus_by_number_out_of_range(self):
        container = SplitPaneContainer(agent_count=3)
        container.focus_lane(5)  # out of range
        assert container._focused_index == 0  # unchanged
