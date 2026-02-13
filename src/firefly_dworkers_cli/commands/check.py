"""``dworkers check`` -- Verify environment and configuration."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from rich.console import Console

from firefly_dworkers_cli.ui.panels import ACCENT, status_table

_PASS = "[green]PASS[/green]"
_FAIL = "[red]FAIL[/red]"
_SKIP = "[yellow]SKIP[/yellow]"


def _check_python_version() -> tuple[str, str, str]:
    """Check that Python >= 3.13."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 13):
        return ("Python version", _PASS, version_str)
    return ("Python version", _FAIL, f"{version_str} (requires >=3.13)")


def _check_module(module_name: str, label: str) -> tuple[str, str, str]:
    """Check whether a Python module is importable."""
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "__version__", "installed")
        return (label, _PASS, str(version))
    except ImportError:
        return (label, _SKIP, "not installed")


def _check_file(path: Path, label: str) -> tuple[str, str, str]:
    """Check whether a file exists on disk."""
    if path.exists():
        return (label, _PASS, str(path))
    return (label, _SKIP, f"not found: {path}")


def check() -> None:
    """Check the local environment for dworkers readiness."""
    console = Console()

    rows: list[tuple[str, str, str]] = []

    # Python version
    rows.append(_check_python_version())

    # Core dependencies
    rows.append(_check_module("firefly_dworkers", "firefly-dworkers"))
    rows.append(_check_module("pydantic", "pydantic"))
    rows.append(_check_module("yaml", "pyyaml"))

    # Optional dependencies
    rows.append(_check_module("typer", "typer (cli)"))
    rows.append(_check_module("rich", "rich (cli)"))
    rows.append(_check_module("fastapi", "fastapi (server)"))
    rows.append(_check_module("uvicorn", "uvicorn (server)"))
    rows.append(_check_module("httpx", "httpx (web)"))
    rows.append(_check_module("pandas", "pandas (data)"))

    # Tenant config files
    cwd = Path.cwd()
    yaml_files = list(cwd.glob("*.yaml")) + list(cwd.glob("*.yml"))
    if yaml_files:
        for yf in yaml_files:
            rows.append(_check_file(yf, f"Tenant config: {yf.name}"))
    else:
        rows.append(("Tenant config (*.yaml)", _SKIP, "no YAML files in current directory"))

    # .env file
    rows.append(_check_file(cwd / ".env", "Environment file (.env)"))

    console.print()
    status_table("Environment Check", rows, console=console)
    console.print()

    # Summary
    pass_count = sum(1 for _, s, _ in rows if "PASS" in s)
    total = len(rows)
    console.print(f"  [{ACCENT}]{pass_count}/{total}[/{ACCENT}] checks passed.\n")
