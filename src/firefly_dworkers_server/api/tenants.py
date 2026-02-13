"""Tenants API router -- list and inspect tenant configurations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from firefly_dworkers.exceptions import TenantNotFoundError

router = APIRouter()


@router.get("")
async def list_tenants() -> list[str]:
    """List registered tenant IDs."""
    from firefly_dworkers.tenants.registry import tenant_registry

    return tenant_registry.list_tenants()


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str) -> dict:
    """Get tenant configuration by ID."""
    from firefly_dworkers.tenants.registry import tenant_registry

    try:
        config = tenant_registry.get(tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return config.model_dump()
