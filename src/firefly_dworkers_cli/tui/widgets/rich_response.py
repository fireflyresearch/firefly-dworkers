"""Rich response rendering with clickable file paths and URLs.

Subclasses Textual's Markdown to pre-process AI response content:
- Detects file paths (e.g. src/app.py:42, /Users/foo/bar.py) and wraps as links
- Detects bare URLs (https://...) and wraps as markdown links
- Handles link clicks: opens files in $EDITOR, URLs in browser
"""

from __future__ import annotations

import os
import re
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

from textual.widgets import Markdown


# File path patterns to detect and linkify
# Matches: /absolute/path.py, ./relative/path.py, src/file.py:42, file.py:42:10
_FILE_PATH_RE = re.compile(
    r'(?<![(\["\'])'  # Not preceded by link syntax chars
    r'(?:'
    r'(?:/[\w./-]+)'  # Absolute path: /foo/bar.py
    r'|(?:\.\.?/[\w./-]+)'  # Relative: ./foo or ../foo
    r'|(?:[\w][\w./-]*\.(?:py|js|ts|tsx|jsx|rs|go|java|rb|c|cpp|h|hpp|css|html|md|yaml|yml|json|toml|sh|sql|xml))'  # file.ext
    r')'
    r'(?::(\d+)(?::(\d+))?)?'  # Optional :line:col
    r'(?![)\]"\w/])'  # Not followed by link syntax chars or more path
)

# Bare URL pattern (not already in markdown link syntax)
_BARE_URL_RE = re.compile(
    r'(?<!\]\()'  # Not preceded by ](
    r'(?<!["\'])'  # Not in quotes
    r'(https?://[^\s<>\)]+[^\s<>\).,;:!?\'")\]])'  # URL
)

# Already inside a markdown link [text](url) — skip these
_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# Inside code blocks — skip these
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```|`[^`]+`')


def linkify_paths(text: str) -> str:
    """Pre-process text to wrap file paths and bare URLs as markdown links.

    Skips content inside existing markdown links and code blocks.
    """
    # Collect regions to skip (code blocks and existing links)
    skip_regions: list[tuple[int, int]] = []
    for m in _CODE_BLOCK_RE.finditer(text):
        skip_regions.append((m.start(), m.end()))
    for m in _MARKDOWN_LINK_RE.finditer(text):
        skip_regions.append((m.start(), m.end()))

    def in_skip_region(pos: int) -> bool:
        return any(start <= pos < end for start, end in skip_regions)

    # Process bare URLs first (replace with markdown links)
    replacements: list[tuple[int, int, str]] = []

    for m in _BARE_URL_RE.finditer(text):
        if not in_skip_region(m.start()):
            url = m.group(1)
            replacements.append((m.start(), m.end(), f"[{url}]({url})"))

    # Process file paths
    for m in _FILE_PATH_RE.finditer(text):
        if not in_skip_region(m.start()):
            path_text = m.group(0)
            # Use file:// URI scheme for paths
            file_path = path_text.split(":")[0]  # Remove :line:col for URI
            if file_path.startswith("/"):
                uri = f"file://{file_path}"
            elif file_path.startswith("./") or file_path.startswith("../"):
                uri = f"file://{file_path}"
            else:
                uri = f"file://./{file_path}"
            replacements.append((m.start(), m.end(), f"[`{path_text}`]({uri})"))

    # Apply replacements in reverse order to preserve positions
    replacements.sort(key=lambda r: r[0], reverse=True)
    result = text
    for start, end, replacement in replacements:
        result = result[:start] + replacement + result[end:]

    return result


class RichResponseMarkdown(Markdown):
    """Markdown widget with enhanced response rendering.

    Pre-processes content to linkify file paths and bare URLs.
    Handles click events to open files in $EDITOR and URLs in browser.
    """

    def __init__(self, markdown: str = "", *, classes: str = "", **kwargs: Any) -> None:
        # Pre-process to add links
        processed = linkify_paths(markdown) if markdown else markdown
        super().__init__(processed, classes=classes, **kwargs)

    async def update(self, markdown: str) -> None:  # type: ignore[override]
        """Update content with linkification."""
        processed = linkify_paths(markdown) if markdown else markdown
        await super().update(processed)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Handle link clicks -- open files in editor, URLs in browser."""
        event.prevent_default()
        event.stop()
        href = event.href

        if href.startswith("file://"):
            self._open_file(href[7:])  # Strip file:// prefix
        elif href.startswith("http://") or href.startswith("https://"):
            self._open_url(href)

    def _open_file(self, path_with_line: str) -> None:
        """Open a file path in $EDITOR or fallback."""
        # Parse path:line:col
        parts = path_with_line.lstrip("./").split(":")
        file_path = parts[0]
        line = parts[1] if len(parts) > 1 else None

        # Resolve relative paths
        if not file_path.startswith("/"):
            file_path = str(Path.cwd() / file_path)

        # Check if file exists
        if not Path(file_path).exists():
            self.notify(f"File not found: {file_path}", severity="warning")
            return

        editor = os.environ.get("EDITOR", "")
        if not editor:
            # Try common editors
            for candidate in ("code", "vim", "nano"):
                try:
                    subprocess.run(["which", candidate], capture_output=True, check=True)  # noqa: S603, S607
                    editor = candidate
                    break
                except subprocess.CalledProcessError:
                    continue

        if not editor:
            self.notify(f"No $EDITOR set. Path: {file_path}", severity="information")
            return

        # Build editor command with line number support
        cmd = [editor]
        if editor in ("code", "code-insiders"):
            cmd.extend(["--goto", f"{file_path}:{line or 1}"])
        elif editor in ("vim", "nvim", "vi"):
            if line:
                cmd.extend([f"+{line}", file_path])
            else:
                cmd.append(file_path)
        elif editor == "nano":
            if line:
                cmd.extend([f"+{line}", file_path])
            else:
                cmd.append(file_path)
        elif editor in ("emacs", "emacsclient"):
            if line:
                cmd.extend([f"+{line}", file_path])
            else:
                cmd.append(file_path)
        else:
            cmd.append(file_path)

        try:
            subprocess.Popen(cmd, start_new_session=True)  # noqa: S603
        except OSError:
            self.notify(f"Failed to open: {file_path}", severity="error")

    def _open_url(self, url: str) -> None:
        """Open a URL in the default browser."""
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            self.notify(f"Failed to open: {url}", severity="error")
