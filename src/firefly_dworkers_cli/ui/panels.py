"""Rich panel and table helpers for consistent CLI output styling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Sequence

# -- Color scheme --
ACCENT = "bright_yellow"
HEADING = "bold cyan"
SUCCESS = "bold green"
WARNING = "bold yellow"
ERROR = "bold red"
DIM = "dim"


def get_console() -> Console:
    """Return a shared Rich console instance."""
    return Console()


def info_panel(title: str, body: str, *, console: Console | None = None) -> None:
    """Display an informational panel."""
    if console is None:
        console = get_console()
    panel = Panel(body, title=f"[{HEADING}]{title}[/{HEADING}]", border_style=ACCENT, expand=False)
    console.print(panel)


def success_panel(title: str, body: str, *, console: Console | None = None) -> None:
    """Display a success panel."""
    if console is None:
        console = get_console()
    panel = Panel(body, title=f"[{SUCCESS}]{title}[/{SUCCESS}]", border_style="green", expand=False)
    console.print(panel)


def error_panel(title: str, body: str, *, console: Console | None = None) -> None:
    """Display an error panel."""
    if console is None:
        console = get_console()
    panel = Panel(body, title=f"[{ERROR}]{title}[/{ERROR}]", border_style="red", expand=False)
    console.print(panel)


def status_table(
    title: str,
    rows: Sequence[tuple[str, str, str]],
    *,
    console: Console | None = None,
) -> None:
    """Display a status table with name, status, and detail columns.

    Parameters
    ----------
    title:
        Table title.
    rows:
        Sequence of (name, status, detail) tuples.
    console:
        Optional Rich console instance.
    """
    if console is None:
        console = get_console()

    table = Table(title=f"[{HEADING}]{title}[/{HEADING}]", border_style=ACCENT, expand=False)
    table.add_column("Check", style="bold white", min_width=25)
    table.add_column("Status", justify="center", min_width=10)
    table.add_column("Details", style=DIM)

    for name, status, detail in rows:
        table.add_row(name, status, detail)

    console.print(table)
