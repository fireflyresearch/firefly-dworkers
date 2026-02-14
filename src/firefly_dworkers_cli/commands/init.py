"""``dworkers init`` -- Interactive project setup."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from firefly_dworkers_cli.ui.panels import info_panel, success_panel

_DEFAULT_TENANT_YAML = """\
# Firefly Dworkers -- Tenant Configuration
# See documentation for all available options.

id: "{tenant_id}"
name: "{tenant_name}"

models:
  default: "openai:gpt-5.2"
  research: ""
  analysis: ""

verticals: []

workers:
  analyst:
    enabled: true
    autonomy: "semi_supervised"
    max_concurrent_tasks: 10
  researcher:
    enabled: true
    autonomy: "semi_supervised"
    max_concurrent_tasks: 10
  data_analyst:
    enabled: true
    autonomy: "semi_supervised"
    max_concurrent_tasks: 10
  manager:
    enabled: true
    autonomy: "semi_supervised"
    max_concurrent_tasks: 10

connectors:
  web_search:
    enabled: false
    provider: "tavily"

knowledge:
  sources: []

branding:
  company_name: "{tenant_name}"
  report_template: "default"

security:
  allowed_models:
    - "openai:*"
    - "anthropic:*"
  encryption_enabled: false
"""

_DEFAULT_ENV_TEMPLATE = """\
# Firefly Dworkers -- Environment Variables
# Copy this file to .env and fill in the values.

# OpenAI
OPENAI_API_KEY=

# Anthropic
ANTHROPIC_API_KEY=

# Tavily (web search)
TAVILY_API_KEY=

# Server
DWORKERS_HOST=0.0.0.0
DWORKERS_PORT=8000
"""


def init(
    tenant_id: str = typer.Option(  # noqa: B008
        "",
        "--tenant-id",
        "-t",
        help="Tenant identifier. Prompted interactively if not supplied.",
    ),
    tenant_name: str = typer.Option(  # noqa: B008
        "",
        "--tenant-name",
        "-n",
        help="Human-readable tenant name. Prompted interactively if not supplied.",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        ".",
        "--output-dir",
        "-o",
        help="Directory to write generated files into.",
    ),
) -> None:
    """Initialize a new dworkers project with tenant configuration."""
    console = Console()

    info_panel("Project Initialization", "Setting up a new Firefly Dworkers project.", console=console)

    # Interactive prompts for missing values
    if not tenant_id:
        tenant_id = Prompt.ask("[bold cyan]Tenant ID[/bold cyan]", default="my-tenant", console=console)
    if not tenant_name:
        tenant_name = Prompt.ask("[bold cyan]Tenant Name[/bold cyan]", default="My Organization", console=console)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Write tenant YAML
    tenant_file = output_path / f"{tenant_id}.yaml"
    tenant_content = _DEFAULT_TENANT_YAML.format(tenant_id=tenant_id, tenant_name=tenant_name)

    if tenant_file.exists():
        overwrite = Confirm.ask(
            f"[bold yellow]{tenant_file}[/bold yellow] already exists. Overwrite?",
            default=False,
            console=console,
        )
        if not overwrite:
            console.print(f"  [dim]Skipped:[/dim] {tenant_file}")
        else:
            tenant_file.write_text(tenant_content)
            console.print(f"  [green]Wrote:[/green] {tenant_file}")
    else:
        tenant_file.write_text(tenant_content)
        console.print(f"  [green]Wrote:[/green] {tenant_file}")

    # Write .env template
    env_file = output_path / ".env"
    if env_file.exists():
        overwrite = Confirm.ask(
            f"[bold yellow]{env_file}[/bold yellow] already exists. Overwrite?",
            default=False,
            console=console,
        )
        if not overwrite:
            console.print(f"  [dim]Skipped:[/dim] {env_file}")
        else:
            env_file.write_text(_DEFAULT_ENV_TEMPLATE)
            console.print(f"  [green]Wrote:[/green] {env_file}")
    else:
        env_file.write_text(_DEFAULT_ENV_TEMPLATE)
        console.print(f"  [green]Wrote:[/green] {env_file}")

    console.print()
    success_panel(
        "Done",
        f"Project initialized for tenant [bold]{tenant_name}[/bold] ({tenant_id}).\nFiles written to: {output_path}",
        console=console,
    )
