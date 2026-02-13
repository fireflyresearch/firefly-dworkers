"""ResearcherWorker -- consulting researcher digital worker."""

from __future__ import annotations

import logging
from typing import Any

from firefly_dworkers.exceptions import VerticalNotFoundError
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import researcher_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory

logger = logging.getLogger(__name__)


@worker_factory.register(WorkerRole.RESEARCHER)
class ResearcherWorker(BaseWorker):
    """Digital worker specialised in research.

    Conducts market research, competitive analysis, trend identification,
    and literature reviews to support consulting engagements.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        **kwargs: Any,
    ) -> None:
        toolkit = researcher_toolkit(tenant_config)
        worker_name = name or f"researcher-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.RESEARCHER,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Consulting researcher worker",
            tags=["researcher", "consulting"],
            **kwargs,
        )

    @staticmethod
    def _build_instructions(config: TenantConfig) -> str:
        """Build role-specific system prompt with vertical fragments."""
        from firefly_dworkers.verticals import get_vertical

        parts: list[str] = [
            "You are an expert consulting researcher. Your role is to conduct "
            "thorough market research, competitive analysis, trend identification, "
            "and literature reviews. Synthesize findings into clear, well-sourced "
            "reports that support strategic decision-making.",
        ]

        for v_name in config.verticals:
            try:
                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except VerticalNotFoundError:
                logger.debug("Skipping unknown vertical '%s'", v_name)
            except Exception:
                logger.warning("Failed to load vertical '%s'", v_name, exc_info=True)

        settings = config.workers.settings_for("researcher")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
