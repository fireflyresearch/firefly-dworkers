"""Tests for the task progress block widget."""

import pytest

from firefly_dworkers_cli.tui.widgets.task_progress import TaskProgressBlock


class TestTaskProgressBlock:
    def test_create_with_no_tasks(self):
        """Simple mode — no task tree, just spinner."""
        block = TaskProgressBlock()
        assert block._tasks == []
        assert block._current_task is None

    def test_create_with_tasks(self):
        tasks = [
            {"name": "Set up models", "subtasks": ["Write test", "Implement"], "done": [True, False]},
            {"name": "Build store", "subtasks": ["Create class"], "done": [False]},
        ]
        block = TaskProgressBlock(tasks=tasks)
        assert len(block._tasks) == 2
        assert block._current_task == 0

    def test_mark_subtask_done(self):
        tasks = [
            {"name": "Task A", "subtasks": ["sub1", "sub2"], "done": [False, False]},
        ]
        block = TaskProgressBlock(tasks=tasks)
        block.mark_subtask_done(0, 0)
        assert block._tasks[0]["done"][0] is True
        assert block._tasks[0]["done"][1] is False

    def test_advance_task(self):
        tasks = [
            {"name": "Task A", "subtasks": [], "done": []},
            {"name": "Task B", "subtasks": [], "done": []},
        ]
        block = TaskProgressBlock(tasks=tasks)
        assert block._current_task == 0
        block.advance_task()
        assert block._current_task == 1

    def test_advance_past_end_stays(self):
        tasks = [{"name": "Only task", "subtasks": [], "done": []}]
        block = TaskProgressBlock(tasks=tasks)
        block.advance_task()
        assert block._current_task == 0  # stays at last

    def test_format_tree_no_tasks(self):
        block = TaskProgressBlock()
        tree = block._format_tree()
        assert tree == ""

    def test_format_tree_with_tasks(self):
        tasks = [
            {"name": "Set up models", "subtasks": ["Write test", "Implement"], "done": [True, False]},
        ]
        block = TaskProgressBlock(tasks=tasks)
        block._current_task = 0
        tree = block._format_tree()
        assert "■ Set up models" in tree
        assert "✓" in tree  # done marker
        assert "○" in tree  # pending marker
