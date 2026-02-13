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

        # Build guard middleware from tenant config and merge with user
        # middleware (guards come first so they run before user middleware).
        guard_middleware = self._build_guard_middleware(tenant_config)
        user_middleware = kwargs.pop("middleware", None) or []
        all_middleware = guard_middleware + list(user_middleware)

        super().__init__(
            name,
            model=resolved_model,
            instructions=instructions,
            tools=tools,
            auto_register=auto_register,
            middleware=all_middleware if all_middleware else None,
            **kwargs,
        )

    # -- Guard middleware builder ---------------------------------------------

    @staticmethod
    def _build_guard_middleware(config: TenantConfig) -> list[Any]:
        """Build guard middleware from tenant security config.

        Uses lazy imports so the guards module is optional -- if the
        framework security extras are not installed, an empty list is
        returned and no guards are applied.
        """
        middleware: list[Any] = []
        guards_cfg = config.security.guards

        try:
            from fireflyframework_genai.agents.builtin_middleware import (
                OutputGuardMiddleware,
                PromptGuardMiddleware,
            )
            from fireflyframework_genai.security.output_guard import OutputGuard
            from fireflyframework_genai.security.prompt_guard import PromptGuard
        except ImportError:
            return middleware

        if guards_cfg.prompt_guard_enabled:
            prompt_guard = PromptGuard(
                custom_patterns=guards_cfg.custom_prompt_patterns,
                sanitise=guards_cfg.sanitise_prompts,
                max_input_length=guards_cfg.max_input_length,
            )
            middleware.append(
                PromptGuardMiddleware(
                    guard=prompt_guard,
                    sanitise=guards_cfg.sanitise_prompts,
                ),
            )

        if guards_cfg.output_guard_enabled:
            output_guard = OutputGuard(
                custom_patterns=guards_cfg.custom_output_patterns or None,
                deny_patterns=guards_cfg.custom_deny_patterns,
                sanitise=guards_cfg.sanitise_outputs,
                max_output_length=guards_cfg.max_output_length,
            )
            middleware.append(
                OutputGuardMiddleware(
                    guard=output_guard,
                    sanitise=guards_cfg.sanitise_outputs,
                    block_categories=guards_cfg.output_block_categories,
                ),
            )

        return middleware

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
