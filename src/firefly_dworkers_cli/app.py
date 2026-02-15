"""Main Typer application for the firefly-dworkers CLI."""

from __future__ import annotations

import click
import typer

from firefly_dworkers_cli.commands.check import check
from firefly_dworkers_cli.commands.init import init
from firefly_dworkers_cli.commands.install import install
from firefly_dworkers_cli.commands.serve import serve

app = typer.Typer(
    name="dworkers",
    help="Firefly Dworkers -- Digital Workers as a Service CLI.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        from firefly_dworkers_cli.ui.banner import show_banner

        show_banner()
        raise typer.Exit


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: B008
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    local: bool = typer.Option(  # noqa: B008
        False,
        "--local",
        help="Force local mode (skip server probe).",
    ),
    remote: str | None = typer.Option(  # noqa: B008
        None,
        "--remote",
        help="Force remote mode. Optionally pass server URL.",
    ),
    autonomy: str | None = typer.Option(  # noqa: B008
        None,
        "--autonomy",
        help="Override autonomy level.",
        click_type=click.Choice(["manual", "semi_supervised", "autonomous"]),
    ),
    resume: str | None = typer.Option(  # noqa: B008
        None,
        "--resume",
        "-r",
        help="Resume a project or conversation by ID or name.",
    ),
    project: str | None = typer.Option(  # noqa: B008
        None,
        "--project",
        "-p",
        help="Open or create a project by name or ID.",
    ),
) -> None:
    """Firefly Dworkers -- Digital Workers as a Service CLI."""
    if ctx.invoked_subcommand is None:
        from firefly_dworkers_cli.tui import DworkersApp

        mode = "auto"
        server_url = None
        if local:
            mode = "local"
        elif remote is not None:
            mode = "remote"
            if remote and remote != "True":
                server_url = remote

        result = DworkersApp(
            mode=mode,
            autonomy_override=autonomy,
            server_url=server_url,
            resume_id=resume,
            project_id=project,
        ).run()
        if result:
            print(result)


app.command(name="init")(init)
app.command(name="serve")(serve)
app.command(name="install")(install)
app.command(name="check")(check)
