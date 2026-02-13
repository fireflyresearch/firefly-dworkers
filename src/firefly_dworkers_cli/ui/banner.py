"""ASCII art banner for the firefly-dworkers CLI."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from firefly_dworkers._version import __version__

BANNER = r"""
    .___                    __
  __| _/_  _  _____________|  | __ ___________  ______
 / __ |\ \/ \/ /  _ \_  __ \  |/ // __ \_  __ \/  ___/
/ /_/ | \     (  <_> )  | \/    <\  ___/|  | \/\___ \
\____ |  \/\_/ \____/|__|  |__|_ \\___  >__|  /____  >
     \/                         \/    \/           \/
"""


def show_banner(console: Console | None = None) -> None:
    """Display the CLI banner with version information."""
    if console is None:
        console = Console()

    banner_text = Text(BANNER, style="bold bright_yellow")
    console.print(banner_text)
    console.print(
        f"  [bold cyan]Digital Workers as a Service[/bold cyan]  [dim]v{__version__}[/dim]",
    )
    console.print()
