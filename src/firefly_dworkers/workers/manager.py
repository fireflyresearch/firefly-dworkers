"""ManagerWorker -- project management digital worker."""

from __future__ import annotations

import logging
from typing import Any

from firefly_dworkers.exceptions import VerticalNotFoundError
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import manager_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory

logger = logging.getLogger(__name__)


@worker_factory.register(WorkerRole.MANAGER)
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
        from firefly_dworkers.verticals import get_vertical

        parts: list[str] = [
            "You are an expert project manager for consulting engagements. "
            "Your role is to coordinate tasks, manage timelines, track "
            "deliverables, and ensure projects are completed on schedule "
            "and within scope. Communicate clearly with stakeholders and "
            "escalate risks proactively.",
        ]

        for v_name in config.verticals:
            try:
                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except VerticalNotFoundError:
                logger.debug("Skipping unknown vertical '%s'", v_name)
            except Exception:
                logger.warning("Failed to load vertical '%s'", v_name, exc_info=True)

        settings = config.workers.settings_for("manager")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
