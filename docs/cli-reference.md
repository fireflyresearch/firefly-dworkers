# CLI Reference

## Contents

- [Global Options](#global-options)
- [Commands](#commands)
  - [dworkers init](#dworkers-init)
  - [dworkers serve](#dworkers-serve)
  - [dworkers install](#dworkers-install)
  - [dworkers check](#dworkers-check)
- [Entry Points](#entry-points)
- [Integration with the Server](#integration-with-the-server)

---

The `dworkers` command-line interface is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for a polished terminal experience. The CLI is included automatically when you install dworkers via the [installer](../README.md#installation).

---

## Global Options

```
dworkers [OPTIONS] COMMAND [ARGS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-v` | Show the version banner and exit |
| `--help` | | Show help message and exit |

Running `dworkers` without any command displays the ASCII art banner and version information.

---

## Commands

### dworkers init

Initialize a new dworkers project with tenant configuration files. When run without options, the command prompts interactively for the tenant ID and name.

```bash
dworkers init [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--tenant-id` | `-t` | (interactive prompt) | Tenant identifier |
| `--tenant-name` | `-n` | (interactive prompt) | Human-readable tenant name |
| `--output-dir` | `-o` | `.` (current directory) | Directory to write generated files into |

**What it creates:**

The command generates two files in the output directory:

- `<tenant-id>.yaml` -- Tenant configuration YAML with models, workers, connectors, knowledge, branding, and security sections pre-populated with defaults.
- `.env` -- Environment variable template with placeholders for `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `DWORKERS_HOST`, and `DWORKERS_PORT`.

If either file already exists, the command asks for confirmation before overwriting.

**Examples:**

```bash
# Interactive mode (prompts for tenant ID and name)
dworkers init

# Non-interactive with explicit options
dworkers init --tenant-id acme-corp --tenant-name "Acme Corporation"

# Write files to a specific directory
dworkers init -t acme-corp -n "Acme Corporation" -o config/tenants
```

---

### dworkers serve

Start the dworkers API server. Requires the `server` extra to be installed (use the **Server** or **Full** profile during installation). If server dependencies are missing, the command prints an error and exits with code 1.

```bash
dworkers serve [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--host` | `-h` | `0.0.0.0` | Bind address |
| `--port` | `-p` | `8000` | Bind port |
| `--reload` | `-r` | `false` | Enable auto-reload for development |

**Examples:**

```bash
# Start with defaults (binds to 0.0.0.0:8000)
dworkers serve

# Custom host and port
dworkers serve --host 127.0.0.1 --port 9000

# Development mode with auto-reload
dworkers serve --reload

# Combined short flags
dworkers serve -h 127.0.0.1 -p 9000 -r
```

The server runs on [Uvicorn](https://www.uvicorn.org/) with the factory pattern, invoking `firefly_dworkers_server.app:create_dworkers_app`. Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

---

### dworkers install

Install optional dependency groups for firefly-dworkers. When run without options, the command presents an interactive menu to select which extras to install.

```bash
dworkers install [OPTIONS]
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--extra` | `-e` | (interactive prompt) | Extra group to install. Can be repeated for multiple groups. |
| `--all` | `-a` | `false` | Install all optional extras at once |

**Available extras:**

| Extra | Description |
|-------|-------------|
| `web` | Web search and scraping (httpx, beautifulsoup4, feedparser) |
| `sharepoint` | SharePoint integration (msal, office365) |
| `google` | Google Drive integration (google-api-python-client) |
| `confluence` | Confluence integration (atlassian-python-api) |
| `jira` | Jira integration (atlassian-python-api) |
| `slack` | Slack integration (slack-sdk) |
| `teams` | Microsoft Teams integration (msgraph-sdk) |
| `email` | Email integration (aiosmtplib) |
| `data` | Data processing (pandas, openpyxl) |
| `server` | API server (fastapi, uvicorn) |

**Examples:**

```bash
# Interactive mode (prompts for each extra group)
dworkers install

# Install a single extra
dworkers install --extra web

# Install multiple extras
dworkers install --extra web --extra server --extra data

# Install all extras at once
dworkers install --all

# Short flags
dworkers install -e sharepoint -e slack
```

The command installs the selected extras into the current environment. If the installation fails, the command exits with a non-zero return code.

---

### dworkers check

Verify the local environment for dworkers readiness. This command takes no options.

```bash
dworkers check
```

The command performs the following checks and reports the result in a Rich-formatted table:

**Checks performed:**

| Category | What is checked | Pass condition |
|----------|----------------|----------------|
| Python version | `sys.version_info` | >= 3.13 |
| Core dependencies | `firefly_dworkers`, `pydantic`, `pyyaml` | Module is importable |
| CLI dependencies | `typer`, `rich` | Module is importable |
| Server dependencies | `fastapi`, `uvicorn` | Module is importable |
| Web/data dependencies | `httpx`, `pandas` | Module is importable |
| Tenant config files | `*.yaml` / `*.yml` in current directory | File exists |
| Environment file | `.env` in current directory | File exists |

Each check reports one of three statuses:
- **PASS** -- requirement is met (with version or path details)
- **FAIL** -- requirement is not met (e.g., Python version too old)
- **SKIP** -- optional item not found (e.g., module not installed, no YAML files)

At the end, a summary line shows how many checks passed out of the total.

**Example:**

```bash
dworkers check

# Sample output:
#
#   Environment Check
#   -----------------------------------------
#   Check                   Status   Details
#   Python version          PASS     3.13.2
#   firefly-dworkers        PASS     installed
#   pydantic                PASS     2.10.0
#   pyyaml                  PASS     installed
#   typer (cli)             PASS     installed
#   rich (cli)              PASS     installed
#   fastapi (server)        SKIP     not installed
#   uvicorn (server)        SKIP     not installed
#   httpx (web)             PASS     installed
#   pandas (data)           SKIP     not installed
#   Tenant config: acme.yaml  PASS   /path/to/acme.yaml
#   Environment file (.env)   PASS   /path/to/.env
#
#   10/12 checks passed.
```

---

## Entry Points

The CLI can be invoked in two ways:

```bash
# Via the installed script (requires [cli] extra)
dworkers --version

# Via Python module
python -m firefly_dworkers_cli --version
```

---

## Integration with the Server

The `dworkers serve` command is equivalent to:

```bash
python -m firefly_dworkers_server
```

Both start the same FastAPI application with Uvicorn. The CLI version adds Rich-formatted output, configuration validation, and banner display.

---

## Related Documentation

- [Getting Started](getting-started.md) -- quick start tutorial using the CLI
- [Configuration](configuration.md) -- tenant YAML reference
- [API Reference](api-reference.md) -- REST API started by `dworkers serve`
