from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from firefly_dworkers.exceptions import TenantError
from firefly_dworkers.tenants.config import TenantConfig

_current_tenant: ContextVar[TenantConfig | None] = ContextVar("_current_tenant", default=None)


def set_current_tenant(config: TenantConfig) -> Any:
    return _current_tenant.set(config)


def get_current_tenant() -> TenantConfig:
    tenant = _current_tenant.get()
    if tenant is None:
        raise TenantError("No tenant set in current context")
    return tenant


def reset_current_tenant(token: Any) -> None:
    _current_tenant.reset(token)
