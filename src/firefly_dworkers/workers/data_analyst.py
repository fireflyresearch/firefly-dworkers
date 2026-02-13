"""DataAnalystWorker -- data analysis digital worker."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import data_analyst_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker


class DataAnalystWorker(BaseWorker):
    """Digital worker specialised in data analysis.

    Processes spreadsheets, queries databases, calls APIs, and produces
    data-driven insights and visualisations for consulting deliverables.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        **kwargs: Any,
    ) -> None:
        toolkit = data_analyst_toolkit(tenant_config)
        worker_name = name or f"data-analyst-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.DATA_ANALYST,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Data analyst worker",
            tags=["data_analyst", "consulting"],
            **kwargs,
        )

    @staticmethod
    def _build_instructions(config: TenantConfig) -> str:
        """Build role-specific system prompt with vertical fragments."""
        parts: list[str] = [
            "You are an expert data analyst. Your role is to process, analyze, "
            "and interpret data from multiple sources. Produce clear, data-driven "
            "insights, statistical summaries, and visualisations that inform "
            "consulting recommendations.",
        ]

        for v_name in config.verticals:
            try:
                from firefly_dworkers.verticals import get_vertical

                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except Exception:  # noqa: BLE001
                pass

        settings = config.workers.settings_for("data_analyst")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
