"""Connectors API router -- list connector statuses for a tenant."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectorResponse(BaseModel):
    """Connector status response."""

    name: str
    category: str = "other"
    configured: bool = False
    provider: str = ""


_CONNECTOR_CATEGORIES: dict[str, str] = {
    "web_search": "search",
    "web_browser": "search",
    "sharepoint": "storage",
    "google_drive": "storage",
    "confluence": "storage",
    "s3": "storage",
    "jira": "project_management",
    "asana": "project_management",
    "slack": "messaging",
    "teams": "messaging",
    "email": "messaging",
    "sql": "data",
    "api": "data",
    "presentation": "document",
    "document": "document",
    "spreadsheet": "document",
    "vision": "analysis",
    "image_generation": "media",
    "stock_images": "media",
}


def _list_connectors(tenant_id: str) -> list[dict[str, Any]]:
    """List connector statuses from tenant config."""
    try:
        from firefly_dworkers.tenants.registry import tenant_registry

        config = tenant_registry.get(tenant_id)
        connectors: list[dict[str, Any]] = []
        for field_name in type(config.connectors).model_fields:
            cfg = getattr(config.connectors, field_name)
            enabled = getattr(cfg, "enabled", False)
            provider = getattr(cfg, "provider", "")
            connectors.append(
                {
                    "name": field_name,
                    "category": _CONNECTOR_CATEGORIES.get(field_name, "other"),
                    "configured": enabled,
                    "provider": provider,
                }
            )
        return connectors
    except Exception:
        logger.debug("Failed to list connectors for tenant %s", tenant_id, exc_info=True)
        return []


@router.get("")
async def list_connectors(tenant_id: str = "default") -> list[ConnectorResponse]:
    """List connector statuses for a tenant."""
    data = _list_connectors(tenant_id)
    return [ConnectorResponse(**c) for c in data]
