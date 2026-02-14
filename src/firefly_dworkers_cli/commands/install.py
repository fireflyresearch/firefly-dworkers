"""``dworkers install`` -- Interactive extras installer."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm

from firefly_dworkers_cli.ui.panels import error_panel, info_panel, success_panel

_AVAILABLE_EXTRAS: list[tuple[str, str]] = [
    ("web", "Web search and scraping (httpx, beautifulsoup4, feedparser)"),
    ("sharepoint", "SharePoint integration (msal, office365)"),
    ("google", "Google Drive integration (google-api-python-client)"),
    ("confluence", "Confluence integration (atlassian-python-api)"),
    ("jira", "Jira integration (atlassian-python-api)"),
    ("slack", "Slack integration (slack-sdk)"),
    ("teams", "Microsoft Teams integration (msgraph-sdk)"),
    ("email", "Email integration (aiosmtplib)"),
    ("data", "Data processing (pandas, openpyxl)"),
    ("server", "API server (fastapi, uvicorn)"),
]


def install(
    extras: list[str] = typer.Option(  # noqa: B008
        None,
        "--extra",
        "-e",
        help="Extra group to install. Can be repeated. If omitted, interactive selection is used.",
    ),
    all_extras: bool = typer.Option(  # noqa: B008
        False,
        "--all",
        "-a",
        help="Install all optional extras.",
    ),
) -> None:
    """Install optional dependency groups for firefly-dworkers."""
    console = Console()

    if all_extras:
        selected = [name for name, _ in _AVAILABLE_EXTRAS]
    elif extras:
        valid_names = {name for name, _ in _AVAILABLE_EXTRAS}
        for e in extras:
            if e not in valid_names:
                error_panel("Invalid Extra", f"Unknown extra: [bold]{e}[/bold]", console=console)
                raise typer.Exit(code=1)
        selected = list(extras)
    else:
        # Interactive selection
        info_panel(
            "Extras Selection",
            "Select which optional dependency groups to install.",
            console=console,
        )
        console.print()

        selected = []
        for name, description in _AVAILABLE_EXTRAS:
            if Confirm.ask(f"  [bold cyan]{name}[/bold cyan] -- {description}", default=False, console=console):
                selected.append(name)

    if not selected:
        console.print("[dim]No extras selected. Nothing to install.[/dim]")
        raise typer.Exit

    extras_str = ",".join(selected)
    install_spec = f"firefly-dworkers[{extras_str}]"

    console.print()

    # Prefer uv, fall back to pip
    if shutil.which("uv") or Path(sys.executable).parent.joinpath("uv").exists():
        install_cmd = [sys.executable, "-m", "uv", "pip", "install", install_spec]
        tool_name = "uv pip"
    else:
        install_cmd = [sys.executable, "-m", "pip", "install", install_spec]
        tool_name = "pip"

    info_panel(
        "Installing",
        f"Running: [bold]{tool_name} install {install_spec}[/bold]",
        console=console,
    )
    console.print()

    result = subprocess.run(install_cmd, check=False)

    console.print()
    if result.returncode == 0:
        success_panel("Complete", f"Successfully installed extras: [bold]{extras_str}[/bold]", console=console)
    else:
        error_panel(
            "Installation Failed",
            f"{tool_name} install exited with code {result.returncode}.",
            console=console,
        )
        raise typer.Exit(code=result.returncode)
