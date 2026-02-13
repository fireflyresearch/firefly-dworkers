from __future__ import annotations

import threading

from firefly_dworkers.exceptions import TenantNotFoundError
from firefly_dworkers.tenants.config import TenantConfig


class TenantRegistry:
    def __init__(self):
        self._tenants: dict[str, TenantConfig] = {}
        self._lock = threading.Lock()

    def register(self, config: TenantConfig) -> None:
        with self._lock:
            self._tenants[config.id] = config

    def get(self, tenant_id: str) -> TenantConfig:
        with self._lock:
            if tenant_id not in self._tenants:
                raise TenantNotFoundError(f"Tenant '{tenant_id}' not registered")
            return self._tenants[tenant_id]

    def has(self, tenant_id: str) -> bool:
        with self._lock:
            return tenant_id in self._tenants

    def unregister(self, tenant_id: str) -> None:
        with self._lock:
            self._tenants.pop(tenant_id, None)

    def list_tenants(self) -> list[str]:
        with self._lock:
            return list(self._tenants.keys())

    def clear(self) -> None:
        with self._lock:
            self._tenants.clear()


tenant_registry = TenantRegistry()
