# Configuration Reference

## Contents

- [File Location](#file-location)
- [Loading Configuration](#loading-configuration)
  - [Programmatic Loading](#programmatic-loading)
  - [From the Server](#from-the-server)
- [Complete Schema Reference](#complete-schema-reference)
- [Global Configuration](#global-configuration)
- [Connector Enabled Helpers](#connector-enabled-helpers)
- [Model Resolution](#model-resolution)
- [Switching Between Web Browser Providers](#switching-between-web-browser-providers)

---

firefly-dworkers uses YAML (or JSON) files to configure tenants. Each file defines the complete configuration for one tenant, including model selection, worker settings, connector credentials, and more.

---

## File Location

Tenant configuration files are loaded from the directory specified by the `DWORKERS_TENANT_CONFIG_DIR` environment variable, defaulting to `config/tenants/`.

Supported formats: `.yaml`, `.yml`, `.json`

---

## Loading Configuration

### Programmatic Loading

```python
from __future__ import annotations

from firefly_dworkers.tenants import load_tenant_config, load_all_tenants

# Load a single tenant
config = load_tenant_config("config/tenants/acme-corp.yaml")

# Load all tenants from a directory
configs = load_all_tenants("config/tenants/")
```

### From the Server

The server loads tenant configurations at startup and registers them in the `TenantRegistry`. Tenants are then accessible via the `/api/tenants` endpoints.

---

## Complete Schema Reference

Below is a fully annotated tenant YAML file showing every available field:

```yaml
# ============================================================================
# TENANT IDENTITY
# ============================================================================

# Required. Unique identifier for this tenant. Used as a key in the
# TenantRegistry and referenced in API calls.
id: acme-corp

# Required. Human-readable display name.
name: Acme Corporation

# ============================================================================
# MODELS
# ============================================================================

models:
  # Default model used by all workers unless overridden.
  # Format: "provider:model_name" (e.g., "openai:gpt-4o", "anthropic:claude-sonnet-4-20250514")
  default: openai:gpt-4o

  # Optional. Model specifically for research tasks.
  # Falls back to 'default' if empty.
  research: ""

  # Optional. Model specifically for analysis tasks.
  # Falls back to 'default' if empty.
  analysis: ""

# ============================================================================
# VERTICALS
# ============================================================================

# List of industry verticals to activate. Each vertical injects
# domain-specific system prompt fragments into worker instructions.
#
# Built-in verticals: banking, healthcare, technology, gaming, legal, consumer
verticals:
  - banking
  - technology

# ============================================================================
# WORKERS
# ============================================================================

workers:
  # Per-role worker configuration. Each role supports the same fields.

  analyst:
    # Whether this worker role is enabled for the tenant.
    enabled: true

    # Autonomy level: "manual", "semi_supervised", or "autonomous"
    #   manual           -- Checkpoint at every step, human approves all
    #   semi_supervised   -- Checkpoint at phase transitions and deliverables
    #   autonomous        -- No checkpoints, fully automated
    autonomy: semi_supervised

    # Custom instructions appended to the worker's system prompt.
    # Use this for tenant-specific guidance.
    custom_instructions: "Focus on regulatory compliance and risk assessment."

    # Maximum number of concurrent tasks this worker can handle.
    max_concurrent_tasks: 10

  researcher:
    enabled: true
    autonomy: autonomous
    custom_instructions: ""
    max_concurrent_tasks: 10

  data_analyst:
    enabled: true
    autonomy: semi_supervised
    custom_instructions: ""
    max_concurrent_tasks: 10

  manager:
    enabled: true
    autonomy: manual
    custom_instructions: ""
    max_concurrent_tasks: 10

# ============================================================================
# CONNECTORS
# ============================================================================

connectors:

  # -- Web Search ----------------------------------------------------------
  web_search:
    enabled: true
    provider: tavily          # "tavily" or "serpapi"
    api_key: "${TAVILY_API_KEY}"
    max_results: 10
    timeout: 30.0
    credential_ref: ""        # Optional vault reference

  # -- Web Browser ---------------------------------------------------------
  web_browser:
    enabled: false
    provider: "web_browser"        # "web_browser" or "flybrowser"
    llm_provider: "openai"         # LLM provider (for flybrowser only)
    llm_model: ""                  # Specific model (for flybrowser only)
    llm_api_key: "${OPENAI_API_KEY}" # LLM API key (for flybrowser only)
    headless: true                 # Run the browser in headless mode
    speed_preset: "balanced"       # "fast", "balanced", "thorough"
    timeout: 30.0

  # -- SharePoint ----------------------------------------------------------
  sharepoint:
    enabled: false
    tenant_id: "${AZURE_TENANT_ID}"
    site_url: "https://company.sharepoint.com/sites/consulting"
    client_id: "${SP_CLIENT_ID}"
    client_secret: "${SP_CLIENT_SECRET}"
    auth_type: client_credentials
    timeout: 30.0

  # -- Google Drive --------------------------------------------------------
  google_drive:
    enabled: false
    credentials_json: ""       # Path to credentials JSON file
    service_account_key: ""    # Path to service account key
    folder_id: ""              # Default folder ID
    scopes:
      - "https://www.googleapis.com/auth/drive.readonly"
    timeout: 30.0

  # -- Confluence ----------------------------------------------------------
  confluence:
    enabled: false
    base_url: "https://company.atlassian.net/wiki"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    space_key: CONSULT
    cloud: true
    timeout: 30.0

  # -- Amazon S3 -----------------------------------------------------------
  s3:
    enabled: false
    bucket: ""
    region: us-east-1
    aws_access_key_id: "${AWS_ACCESS_KEY_ID}"
    aws_secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
    prefix: ""                 # Key prefix for scoping
    endpoint_url: ""           # Custom endpoint (e.g., MinIO)
    timeout: 30.0

  # -- Jira ----------------------------------------------------------------
  jira:
    enabled: false
    base_url: "https://company.atlassian.net"
    username: "${JIRA_USERNAME}"
    api_token: "${JIRA_API_TOKEN}"
    project_key: CONSULT
    cloud: true
    timeout: 30.0

  # -- Asana ---------------------------------------------------------------
  asana:
    enabled: false
    access_token: "${ASANA_ACCESS_TOKEN}"
    workspace_gid: ""
    timeout: 30.0

  # -- Slack ---------------------------------------------------------------
  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"    # For Socket Mode
    default_channel: "#consulting-ops"
    timeout: 30.0

  # -- Microsoft Teams -----------------------------------------------------
  teams:
    enabled: false
    tenant_id: "${AZURE_TENANT_ID}"
    client_id: "${TEAMS_CLIENT_ID}"
    client_secret: "${TEAMS_CLIENT_SECRET}"
    team_id: ""
    timeout: 30.0

  # -- Email (SMTP/IMAP) ---------------------------------------------------
  email:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_use_tls: true
    imap_host: imap.gmail.com
    imap_port: 993
    username: "${EMAIL_USERNAME}"
    password: "${EMAIL_PASSWORD}"
    from_address: "dworkers@company.com"
    timeout: 30.0

  # -- SQL Database --------------------------------------------------------
  sql:
    enabled: false
    connection_string: "${DATABASE_URL}"
    read_only: true
    max_rows: 1000
    pool_size: 5
    timeout: 30.0

  # -- Generic HTTP API ----------------------------------------------------
  api:
    enabled: false
    base_url: ""
    default_headers: {}
    auth_type: ""              # "bearer", "basic", "api_key"
    auth_token: "${API_TOKEN}"
    timeout: 30.0

# ============================================================================
# KNOWLEDGE
# ============================================================================

knowledge:
  sources:
    - type: sharepoint
      url: "https://company.sharepoint.com/sites/consulting/docs"
      metadata:
        category: "internal-policies"
    - type: confluence
      url: "https://company.atlassian.net/wiki/spaces/CONSULT"
      metadata:
        category: "methodology"

# ============================================================================
# BRANDING
# ============================================================================

branding:
  company_name: Acme Corporation
  report_template: default     # Template name for report generation
  logo_url: ""                 # URL to company logo

# ============================================================================
# SECURITY
# ============================================================================

security:
  # Glob patterns for allowed model identifiers.
  allowed_models:
    - "openai:*"
    - "anthropic:*"

  # Data residency region (informational).
  data_residency: us-east-1

  # Whether to enable encryption for stored data.
  encryption_enabled: false
```

---

## Global Configuration

In addition to per-tenant YAML files, the `DworkersConfig` singleton controls platform-level settings via environment variables:

| Environment Variable | Type | Default | Description |
|---------------------|------|---------|-------------|
| `DWORKERS_DEFAULT_AUTONOMY` | string | `semi_supervised` | Default autonomy level for workers |
| `DWORKERS_TENANT_CONFIG_DIR` | string | `config/tenants` | Directory containing tenant YAML files |
| `DWORKERS_MAX_CONCURRENT_WORKERS` | int | `10` | Maximum concurrent worker instances |
| `DWORKERS_KNOWLEDGE_BACKEND` | string | `in_memory` | Knowledge backend type (`in_memory`, `file`, `postgres`, `mongodb`) |
| `DWORKERS_DEFAULT_FAILURE_STRATEGY` | string | `fail_pipeline` | How to handle step failures (`skip_downstream`, `fail_pipeline`, `ignore`) |

Access programmatically:

```python
from __future__ import annotations

from firefly_dworkers.config import get_config

config = get_config()
print(config.default_autonomy)        # "semi_supervised"
print(config.tenant_config_dir)       # "config/tenants"
print(config.max_concurrent_workers)  # 10
```

---

## Connector Enabled Helpers

The `ConnectorsConfig` model provides utility methods for querying enabled connectors:

```python
from __future__ import annotations

from firefly_dworkers.tenants import load_tenant_config

config = load_tenant_config("config/tenants/acme-corp.yaml")

# Get all enabled connectors
enabled = config.connectors.enabled_connectors()
for name, connector_config in enabled.items():
    print(f"{name}: provider={connector_config.provider}")

# Get a specific connector
web_cfg = config.connectors.get_connector("web_search")
print(f"Web search enabled: {web_cfg.enabled}")
```

---

## Model Resolution

The `ModelsConfig.resolve(purpose)` method returns the model for a given purpose, falling back to the default:

```python
from __future__ import annotations

from firefly_dworkers.tenants import load_tenant_config

config = load_tenant_config("config/tenants/acme-corp.yaml")

# Resolves to the "research" model if set, otherwise "default"
model = config.models.resolve("research")
```

---

## Switching Between Web Browser Providers

The `web_browser` connector supports two providers that implement the `WebBrowsingTool` port:

| Provider | Adapter Class | Description | Extra Required |
|----------|--------------|-------------|----------------|
| `web_browser` | `WebBrowserTool` | Lightweight HTTP+BeautifulSoup page fetching. No JavaScript support. | `web` |
| `flybrowser` | `FlyBrowserTool` | AI-driven browser automation with LLM-powered navigation, form filling, and data extraction. | `browser` |

To switch from the default HTTP adapter to the AI-driven FlyBrowser adapter, change the `provider` field and supply the required LLM credentials:

```yaml
connectors:
  web_browser:
    enabled: true

    # Option A: Lightweight HTTP fetcher (default)
    provider: "web_browser"

    # Option B: AI-driven browser -- uncomment and set credentials
    # provider: "flybrowser"
    # llm_provider: "openai"
    # llm_model: "gpt-4o"
    # llm_api_key: "${OPENAI_API_KEY}"
    # headless: true
    # speed_preset: "balanced"      # "fast", "balanced", "thorough"
```

When using `flybrowser`, install the browser extra:

```bash
pip install firefly-dworkers[browser]
```

The `FlyBrowserTool` accepts additional parameters beyond simple URL fetching:

- `instruction` -- Natural language instruction for the browser agent (e.g., "click the login button", "fill in the search form with 'AI consulting'").
- `action` -- Browser action mode: `"fetch"` (default), `"act"`, `"extract"`, or `"agent"`.
- `extract_schema` -- Optional JSON schema for structured data extraction.

---

## Related Documentation

- [Getting Started](getting-started.md) -- step-by-step tutorial using configuration
- [Tenants Overview](tenants/overview.md) -- multi-tenancy architecture details
- [Tools Overview](tools/overview.md) -- available tool adapters
- [CLI Reference](cli-reference.md) -- `dworkers init` generates config files
