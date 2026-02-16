"""Tests for the ToolBlock widget."""

from firefly_dworkers_cli.tui.widgets.tool_block import ToolBlock


class TestToolBlock:
    def test_create_minimal(self):
        tb = ToolBlock(tool_name="Read", params={"file_path": "src/app.py"})
        assert tb._tool_name == "Read"
        assert tb._status == "running"

    def test_format_minimal_read(self):
        tb = ToolBlock(tool_name="Read", params={"file_path": "src/app.py"})
        text = tb._format_minimal()
        assert "Read" in text
        assert "src/app.py" in text
        assert "\u00b7\u00b7\u00b7" in text  # running indicator

    def test_format_minimal_bash(self):
        tb = ToolBlock(tool_name="Bash", params={"command": "git status"})
        text = tb._format_minimal()
        assert "Bash" in text
        assert "git status" in text

    def test_format_minimal_grep(self):
        tb = ToolBlock(tool_name="Grep", params={"pattern": "TODO", "path": "src/"})
        text = tb._format_minimal()
        assert "Grep" in text
        assert "TODO" in text

    def test_format_minimal_unknown_tool(self):
        tb = ToolBlock(tool_name="CustomTool", params={"foo": "bar"})
        text = tb._format_minimal()
        assert "CustomTool" in text
        # Unknown tools don't show params in minimal mode
        assert "bar" not in text

    def test_mark_complete(self):
        tb = ToolBlock(tool_name="Read", params={})
        tb.mark_complete(duration_ms=120, result_preview="42 lines")
        assert tb._status == "complete"
        assert tb._duration_ms == 120
        assert tb._result_preview == "42 lines"

    def test_mark_complete_format(self):
        tb = ToolBlock(tool_name="Read", params={"file_path": "src/app.py"})
        tb.mark_complete(duration_ms=120)
        text = tb._format_minimal()
        assert "120ms" in text
        assert "\u2713" in text  # checkmark

    def test_mark_error(self):
        tb = ToolBlock(tool_name="Read", params={})
        tb.mark_error("File not found")
        assert tb._status == "error"
        assert "\u2717" in tb._format_minimal()  # X mark

    def test_format_verbose(self):
        tb = ToolBlock(tool_name="Read", params={"file_path": "src/app.py", "limit": 50})
        tb.mark_complete(duration_ms=120, result_preview="42 lines read")
        text = tb._format_verbose()
        assert "file_path" in text
        assert "120ms" in text
        assert "42 lines" in text

    def test_set_verbose_toggle(self):
        tb = ToolBlock(tool_name="Read", params={"file_path": "x.py"})
        assert tb._verbose is False
        tb.set_verbose(True)
        assert tb._verbose is True

    def test_long_param_truncated(self):
        long_path = "a" * 100
        tb = ToolBlock(tool_name="Read", params={"file_path": long_path})
        text = tb._format_minimal()
        assert "..." in text
        assert len(text) < 200

    def test_key_param_summary_empty(self):
        tb = ToolBlock(tool_name="UnknownTool", params={"x": 1})
        assert tb._key_param_summary() == ""
