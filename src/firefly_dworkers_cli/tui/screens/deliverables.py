"""Deliverables screen — browse generated output files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Markdown, Static, Tree


class FilePreview(Vertical):
    DEFAULT_CSS = """
    FilePreview { width: 1fr; height: 1fr; background: #2A2A3E; border: round #313244; padding: 1 2; margin-left: 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._content = Markdown("Select a file to preview", classes="text-dim")

    def compose(self) -> ComposeResult:
        yield Static("Preview", classes="panel-title")
        yield self._content

    def show_file(self, path: Path) -> None:
        if not path.exists():
            self._content.update("File not found")
            return
        try:
            if path.suffix in (".md", ".txt", ".yaml", ".yml", ".json", ".csv"):
                text = path.read_text(errors="replace")[:5000]
                self._content.update(text)
            else:
                size = path.stat().st_size
                self._content.update(f"**{path.name}**\n\nType: {path.suffix}\nSize: {size:,} bytes\n\n*Binary file — use Export to open*")
        except Exception as e:
            self._content.update(f"Error reading file: {e}")


class DeliverablesScreen(Horizontal):
    DEFAULT_CSS = """
    DeliverablesScreen { height: 1fr; padding: 1 2; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._base_dir = Path.home() / ".dworkers" / "deliverables"
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="file-tree-container"):
            yield Static("\u25A3 Deliverables", classes="panel-title")
            yield Button("Open Folder", id="open-folder-btn")
            tree: Tree[str] = Tree("Deliverables", id="file-tree")
            tree.root.expand()
            yield tree
        yield FilePreview(id="file-preview")

    def on_mount(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._populate_tree()

    def _populate_tree(self) -> None:
        tree = self.query_one("#file-tree", Tree)
        tree.root.remove_children()
        self._add_directory(tree.root, self._base_dir)

    def _add_directory(self, node, path: Path) -> None:
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    branch = node.add(item.name, data=str(item))
                    self._add_directory(branch, item)
                else:
                    node.add_leaf(item.name, data=str(item))
        except PermissionError:
            pass

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            path = Path(event.node.data)
            if path.is_file():
                self._selected_path = path
                preview = self.query_one("#file-preview", FilePreview)
                preview.show_file(path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-folder-btn":
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(self._base_dir)])
            elif sys.platform == "linux":
                subprocess.Popen(["xdg-open", str(self._base_dir)])
