"""ManagerWorker -- project management digital worker."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import manager_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker


class ManagerWorker(BaseWorker):
    """Digital worker specialised in project management.

    Coordinates tasks, tracks progress, manages timelines, and ensures
    consulting deliverables are completed on schedule and within scope.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        **kwargs: Any,
    ) -> None:
        toolkit = manager_toolkit(tenant_config)
        worker_name = name or f"manager-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.MANAGER,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Project manager worker",
            tags=["manager", "consulting"],
            **kwargs,
        )

    @staticmethod
    def _build_instructions(config: TenantConfig) -> str:
        """Build role-specific system prompt with vertical fragments."""
        parts: list[str] = [
            "You are an expert project manager for consulting engagements. "
            "Your role is to coordinate tasks, manage timelines, track "
            "deliverables, and ensure projects are completed on schedule "
            "and within scope. Communicate clearly with stakeholders and "
            "escalate risks proactively.",
        ]

        for v_name in config.verticals:
            try:
                from firefly_dworkers.verticals import get_vertical

                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except Exception:  # noqa: BLE001
                pass

        settings = config.workers.settings_for("manager")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
