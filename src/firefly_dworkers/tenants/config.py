from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelsConfig(BaseModel):
    default: str = "openai:gpt-4o"
    research: str = ""
    analysis: str = ""

    def resolve(self, purpose: str) -> str:
        value = getattr(self, purpose, "") or self.default
        return value


class WorkerConfig(BaseModel):
    class WorkerSettings(BaseModel):
        enabled: bool = True
        autonomy: Literal["manual", "semi_supervised", "autonomous"] = "semi_supervised"
        custom_instructions: str = ""
        max_concurrent_tasks: int = 10

    analyst: WorkerSettings = Field(default_factory=WorkerSettings)
    researcher: WorkerSettings = Field(default_factory=WorkerSettings)
    data_analyst: WorkerSettings = Field(default_factory=WorkerSettings)
    manager: WorkerSettings = Field(default_factory=WorkerSettings)

    def settings_for(self, role: str) -> WorkerSettings:
        return getattr(self, role)


# ---------------------------------------------------------------------------
# Connector configuration models — typed per-adapter settings
# ---------------------------------------------------------------------------


class BaseConnectorConfig(BaseModel, extra="allow"):
    """Base for all connector configs. Every connector has an enabled flag,
    an optional provider hint, and an optional credential_ref for vault
    integration."""

    enabled: bool = False
    provider: str = ""
    credential_ref: str = ""
    timeout: float = 30.0


class WebSearchConnectorConfig(BaseConnectorConfig):
    """Web search provider configuration."""

    provider: str = "tavily"
    api_key: str = ""
    max_results: int = 10


class SharePointConnectorConfig(BaseConnectorConfig):
    """SharePoint adapter configuration."""

    tenant_id: str = ""
    site_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    auth_type: str = "client_credentials"


class GoogleDriveConnectorConfig(BaseConnectorConfig):
    """Google Drive adapter configuration."""

    credentials_json: str = ""
    service_account_key: str = ""
    folder_id: str = ""
    scopes: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/drive.readonly"],
    )


class ConfluenceConnectorConfig(BaseConnectorConfig):
    """Confluence adapter configuration."""

    base_url: str = ""
    username: str = ""
    api_token: str = ""
    space_key: str = ""
    cloud: bool = True


class S3ConnectorConfig(BaseConnectorConfig):
    """Amazon S3 adapter configuration."""

    bucket: str = ""
    region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    prefix: str = ""
    endpoint_url: str = ""


class JiraConnectorConfig(BaseConnectorConfig):
    """Jira adapter configuration."""

    base_url: str = ""
    username: str = ""
    api_token: str = ""
    project_key: str = ""
    cloud: bool = True


class AsanaConnectorConfig(BaseConnectorConfig):
    """Asana adapter configuration."""

    access_token: str = ""
    workspace_gid: str = ""


class SlackConnectorConfig(BaseConnectorConfig):
    """Slack adapter configuration."""

    bot_token: str = ""
    app_token: str = ""
    default_channel: str = ""


class TeamsConnectorConfig(BaseConnectorConfig):
    """Microsoft Teams adapter configuration."""

    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    team_id: str = ""


class EmailConnectorConfig(BaseConnectorConfig):
    """Email (SMTP/IMAP) adapter configuration."""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    imap_host: str = ""
    imap_port: int = 993
    username: str = ""
    password: str = ""
    from_address: str = ""


class SQLConnectorConfig(BaseConnectorConfig):
    """SQL database connector configuration."""

    connection_string: str = ""
    read_only: bool = True
    max_rows: int = 1000
    pool_size: int = 5


class APIConnectorConfig(BaseConnectorConfig):
    """Generic HTTP API connector configuration."""

    base_url: str = ""
    default_headers: dict[str, str] = Field(default_factory=dict)
    auth_type: str = ""
    auth_token: str = ""


class ConnectorsConfig(BaseModel, extra="allow"):
    """Typed connector configuration registry.

    Each field is a structured Pydantic model so that YAML/JSON configs are
    validated at load time. The ``enabled_connectors`` method returns only
    connectors with ``enabled=True``.
    """

    web_search: WebSearchConnectorConfig = Field(default_factory=WebSearchConnectorConfig)
    sharepoint: SharePointConnectorConfig = Field(default_factory=SharePointConnectorConfig)
    google_drive: GoogleDriveConnectorConfig = Field(default_factory=GoogleDriveConnectorConfig)
    confluence: ConfluenceConnectorConfig = Field(default_factory=ConfluenceConnectorConfig)
    s3: S3ConnectorConfig = Field(default_factory=S3ConnectorConfig)
    jira: JiraConnectorConfig = Field(default_factory=JiraConnectorConfig)
    asana: AsanaConnectorConfig = Field(default_factory=AsanaConnectorConfig)
    slack: SlackConnectorConfig = Field(default_factory=SlackConnectorConfig)
    teams: TeamsConnectorConfig = Field(default_factory=TeamsConnectorConfig)
    email: EmailConnectorConfig = Field(default_factory=EmailConnectorConfig)
    sql: SQLConnectorConfig = Field(default_factory=SQLConnectorConfig)
    api: APIConnectorConfig = Field(default_factory=APIConnectorConfig)

    def enabled_connectors(self) -> dict[str, BaseConnectorConfig]:
        """Return only connectors where ``enabled=True``."""
        result: dict[str, BaseConnectorConfig] = {}
        for name in type(self).model_fields:
            cfg = getattr(self, name)
            if isinstance(cfg, BaseConnectorConfig) and cfg.enabled:
                result[name] = cfg
        return result

    def get_connector(self, name: str) -> BaseConnectorConfig:
        """Get a connector config by name, raising if not a known field."""
        if not hasattr(self, name):
            raise ValueError(f"Unknown connector '{name}'")
        return getattr(self, name)


class KnowledgeSourceConfig(BaseModel):
    type: str
    url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeConfig(BaseModel):
    sources: list[KnowledgeSourceConfig] = Field(default_factory=list)


class BrandingConfig(BaseModel):
    company_name: str = ""
    report_template: str = "default"
    logo_url: str = ""


class SecurityConfig(BaseModel):
    allowed_models: list[str] = Field(default_factory=lambda: ["openai:*", "anthropic:*"])
    data_residency: str = ""
    encryption_enabled: bool = False


class TenantConfig(BaseModel):
    id: str
    name: str
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    verticals: list[str] = Field(default_factory=list)
    workers: WorkerConfig = Field(default_factory=WorkerConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
