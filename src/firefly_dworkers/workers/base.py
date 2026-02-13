"""BaseWorker -- foundation for all digital workers.

Extends :class:`~fireflyframework_genai.agents.base.FireflyAgent` with
worker-specific concerns: role, autonomy level, and tenant configuration.
"""

from __future__ import annotations

from typing import Any

from fireflyframework_genai.agents.base import FireflyAgent

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import AutonomyLevel, WorkerRole


class BaseWorker(FireflyAgent):
    """Base class for all digital workers.

    Resolves the model and autonomy level from :class:`TenantConfig` when
    not explicitly provided, and exposes worker-specific properties
    (:attr:`role`, :attr:`autonomy_level`, :attr:`tenant_config`).

    Parameters:
        name: Unique worker name.
        role: The :class:`WorkerRole` for this worker.
        tenant_config: Tenant-level configuration.
        model: Model string or instance.  Falls back to
            ``tenant_config.models.default`` when empty.
        autonomy_level: Explicit override; otherwise read from the
            tenant's per-role worker settings.
        instructions: System prompt text.
        tools: Sequence of tools / toolkits.
        auto_register: Whether to register in the framework's
            :class:`AgentRegistry`.  Defaults to ``False`` because workers
            use their own :class:`WorkerRegistry`.
        **kwargs: Forwarded to :class:`FireflyAgent`.
    """

    def __init__(
        self,
        name: str,
        *,
        role: WorkerRole,
        tenant_config: TenantConfig,
        model: Any = "",
        autonomy_level: AutonomyLevel | None = None,
        instructions: str | Any = "",
        tools: Any = (),
        auto_register: bool = False,
        **kwargs: Any,
    ) -> None:
        resolved_model = model or tenant_config.models.default
        worker_settings = tenant_config.workers.settings_for(role.value)

        self._role = role
        self._autonomy_level = autonomy_level or AutonomyLevel(worker_settings.autonomy)
        self._tenant_config = tenant_config
        self._instructions_text = instructions if isinstance(instructions, str) else ""

        super().__init__(
            name,
            model=resolved_model,
            instructions=instructions,
            tools=tools,
            auto_register=auto_register,
            **kwargs,
        )

    # -- Properties ----------------------------------------------------------

    @property
    def role(self) -> WorkerRole:
        """The worker's role."""
        return self._role

    @property
    def autonomy_level(self) -> AutonomyLevel:
        """The worker's autonomy level."""
        return self._autonomy_level

    @property
    def tenant_config(self) -> TenantConfig:
        """The tenant configuration bound to this worker."""
        return self._tenant_config
