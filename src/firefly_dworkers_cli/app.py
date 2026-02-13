"""Main Typer application for the firefly-dworkers CLI."""

from __future__ import annotations

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
) -> None:
    """Firefly Dworkers -- Digital Workers as a Service CLI."""
    if ctx.invoked_subcommand is None:
        from firefly_dworkers_cli.ui.banner import show_banner

        show_banner()
        raise typer.Exit


app.command(name="init")(init)
app.command(name="serve")(serve)
app.command(name="install")(install)
app.command(name="check")(check)
