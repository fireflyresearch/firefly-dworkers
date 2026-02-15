"""Integration tests for new TUI widgets wired into app.py."""

from firefly_dworkers_cli.tui.app import DworkersApp
from firefly_dworkers_cli.tui.widgets.task_progress import TaskProgressBlock
from firefly_dworkers_cli.tui.widgets.interactive_question import InteractiveQuestion


class TestAppImports:
    def test_task_progress_importable(self):
        assert TaskProgressBlock is not None

    def test_interactive_question_importable(self):
        assert InteractiveQuestion is not None

    def test_app_has_format_status_hints(self):
        assert hasattr(DworkersApp, "_format_status_hints")
        result = DworkersApp._format_status_hints(is_streaming=False, has_question=False, private_role=None)
        assert isinstance(result, str)
