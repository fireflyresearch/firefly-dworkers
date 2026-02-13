"""``dworkers serve`` -- Start the FastAPI development server."""

from __future__ import annotations

import typer
from rich.console import Console

from firefly_dworkers_cli.ui.panels import error_panel, info_panel


def serve(
    host: str = typer.Option(  # noqa: B008
        "0.0.0.0",
        "--host",
        "-h",
        help="Bind address.",
    ),
    port: int = typer.Option(  # noqa: B008
        8000,
        "--port",
        "-p",
        help="Bind port.",
    ),
    reload: bool = typer.Option(  # noqa: B008
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development.",
    ),
) -> None:
    """Start the Firefly Dworkers API server."""
    console = Console()

    # Lazy import -- server extras may not be installed
    try:
        import uvicorn  # noqa: F401  # isort: skip

        from firefly_dworkers_server.app import create_dworkers_app  # noqa: F401
    except ImportError:
        error_panel(
            "Missing Dependencies",
            'Server extras are not installed.\nRun: [bold]pip install "firefly-dworkers[server]"[/bold]',
            console=console,
        )
        raise typer.Exit(code=1) from None

    reload_label = "[green]on[/green]" if reload else "[dim]off[/dim]"
    info_panel(
        "Firefly Dworkers Server",
        f"Host:   [bold]{host}[/bold]\n"
        f"Port:   [bold]{port}[/bold]\n"
        f"Reload: {reload_label}\n"
        f"URL:    [bold cyan]http://{host}:{port}[/bold cyan]",
        console=console,
    )

    uvicorn.run(
        "firefly_dworkers_server.app:create_dworkers_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
