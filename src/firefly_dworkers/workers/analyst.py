"""AnalystWorker -- consulting analyst digital worker."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import analyst_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker


class AnalystWorker(BaseWorker):
    """Digital worker specialised in consulting analysis.

    Analyses business processes, gathers requirements, identifies gaps,
    and produces actionable recommendations.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        **kwargs: Any,
    ) -> None:
        toolkit = analyst_toolkit(tenant_config)
        worker_name = name or f"analyst-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.ANALYST,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Consulting analyst worker",
            tags=["analyst", "consulting"],
            **kwargs,
        )

    @staticmethod
    def _build_instructions(config: TenantConfig) -> str:
        """Build role-specific system prompt with vertical fragments."""
        parts: list[str] = [
            "You are an expert consulting analyst. Your role is to analyze "
            "business processes, gather requirements, identify gaps, and "
            "produce actionable recommendations.",
        ]

        # Add vertical-specific fragments
        for v_name in config.verticals:
            try:
                from firefly_dworkers.verticals import get_vertical

                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except Exception:  # noqa: BLE001
                pass

        # Add custom instructions from tenant config
        settings = config.workers.settings_for("analyst")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
