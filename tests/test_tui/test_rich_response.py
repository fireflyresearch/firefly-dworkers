"""Tests for RichResponseMarkdown widget."""

import pytest

from firefly_dworkers_cli.tui.widgets.rich_response import (
    RichResponseMarkdown,
    linkify_paths,
)


class TestLinkifyPaths:
    """Test file path and URL detection/linkification."""

    def test_absolute_path(self):
        text = "See /Users/foo/bar.py for details"
        result = linkify_paths(text)
        assert "[`/Users/foo/bar.py`](file:///Users/foo/bar.py)" in result

    def test_relative_path(self):
        text = "Check ./src/app.py"
        result = linkify_paths(text)
        assert "[`./src/app.py`](file://./src/app.py)" in result

    def test_path_with_extension(self):
        text = "Edit src/theme.py to change styles"
        result = linkify_paths(text)
        assert "file://" in result
        assert "src/theme.py" in result

    def test_path_with_line_number(self):
        text = "Error at src/app.py:42"
        result = linkify_paths(text)
        assert "src/app.py:42" in result
        assert "file://" in result

    def test_bare_url(self):
        text = "Visit https://example.com/docs for info"
        result = linkify_paths(text)
        assert "[https://example.com/docs](https://example.com/docs)" in result

    def test_skips_code_blocks(self):
        text = "```python\nfrom src/app.py import foo\n```"
        result = linkify_paths(text)
        # Should NOT linkify inside code blocks
        assert "file://" not in result

    def test_skips_inline_code(self):
        text = "Run `src/app.py` to start"
        result = linkify_paths(text)
        # Should NOT linkify inside inline code
        assert "file://" not in result

    def test_skips_existing_markdown_links(self):
        text = "See [docs](https://example.com) for info"
        result = linkify_paths(text)
        # Should NOT double-wrap existing links
        assert result.count("](") == 1

    def test_no_paths_no_change(self):
        text = "Just some plain text with no paths"
        result = linkify_paths(text)
        assert result == text

    def test_slash_in_normal_word_not_linkified(self):
        """Regression: /regional inside 'small/regional' should NOT be matched."""
        text = "The firm is relatively small/regional and not widely covered"
        result = linkify_paths(text)
        assert "file://" not in result
        assert result == text

    def test_single_segment_absolute_path_not_linkified(self):
        """Single-segment paths like /foo should not be linkified."""
        text = "The /tmp directory"
        result = linkify_paths(text)
        assert "file://" not in result

    def test_multi_segment_absolute_path_linkified(self):
        """Multi-segment paths like /usr/bin should be linkified."""
        text = "See /usr/bin/python for details"
        result = linkify_paths(text)
        assert "file:///usr/bin/python" in result

    def test_multiple_paths(self):
        text = "Compare src/app.py and src/theme.py"
        result = linkify_paths(text)
        assert result.count("file://") == 2


class TestRichResponseMarkdown:
    """Test the RichResponseMarkdown widget."""

    def test_constructor_processes_content(self):
        widget = RichResponseMarkdown("See /tmp/test.py", classes="msg-content")
        assert widget is not None

    def test_empty_content(self):
        widget = RichResponseMarkdown("", classes="msg-content")
        assert widget is not None

    def test_plain_text(self):
        widget = RichResponseMarkdown("Hello world", classes="msg-content")
        assert widget is not None
