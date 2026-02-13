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


class ConnectorsConfig(BaseModel, extra="allow"):
    web_search: dict[str, Any] = Field(default_factory=dict)
    sharepoint: dict[str, Any] = Field(default_factory=dict)
    google_drive: dict[str, Any] = Field(default_factory=dict)
    confluence: dict[str, Any] = Field(default_factory=dict)
    jira: dict[str, Any] = Field(default_factory=dict)
    slack: dict[str, Any] = Field(default_factory=dict)
    teams: dict[str, Any] = Field(default_factory=dict)
    email: dict[str, Any] = Field(default_factory=dict)

    def enabled_connectors(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for name in self.model_fields:
            cfg = getattr(self, name)
            if isinstance(cfg, dict) and cfg.get("enabled"):
                result[name] = cfg
        return result


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
