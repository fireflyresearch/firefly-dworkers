"""DocumentDesignerWorker -- document design digital worker."""

from __future__ import annotations

import logging
from typing import Any

from firefly_dworkers.exceptions import VerticalNotFoundError
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import designer_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory

logger = logging.getLogger(__name__)


@worker_factory.register(
    WorkerRole.DESIGNER,
    description="Designer — document design & creative work",
    tags=["designer", "creative"],
    display_name="Noor",
    avatar="N",
    avatar_color="magenta",
    tagline="Document design and creative work",
)
class DocumentDesignerWorker(BaseWorker):
    """Digital worker specialised in document design and creative direction.

    Transforms structured content into polished, visually compelling
    deliverables — presentations, reports, spreadsheets, and PDFs.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        checkpoint_handler: Any = None,
        **kwargs: Any,
    ) -> None:
        worker_settings = tenant_config.workers.settings_for("designer")
        resolved_autonomy = autonomy_level or AutonomyLevel(worker_settings.autonomy)

        toolkit = designer_toolkit(
            tenant_config,
            autonomy_level=resolved_autonomy,
            checkpoint_handler=checkpoint_handler,
        )
        worker_name = name or f"designer-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.DESIGNER,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Document designer worker",
            tags=["designer", "consulting"],
            **kwargs,
        )

        if checkpoint_handler is not None:
            self.checkpoint_handler = checkpoint_handler

    @staticmethod
    def _build_instructions(
        config: TenantConfig,
        *,
        user_profile: dict[str, str] | None = None,
    ) -> str:
        """Build role-specific system prompt using Jinja2 template."""
        from firefly_dworkers.prompts import get_worker_prompt, load_prompts
        from firefly_dworkers.verticals import get_vertical

        load_prompts()

        # Build verticals string from fragments
        vertical_parts: list[str] = []
        for v_name in config.verticals:
            try:
                v = get_vertical(v_name)
                vertical_parts.append(v.system_prompt_fragment)
            except VerticalNotFoundError:
                logger.debug("Skipping unknown vertical '%s'", v_name)
            except Exception:
                logger.warning("Failed to load vertical '%s'", v_name, exc_info=True)

        settings = config.workers.settings_for("designer")
        up = user_profile or {}
        return get_worker_prompt(
            "designer",
            company_name=config.branding.company_name,
            verticals="\n".join(vertical_parts),
            custom_instructions=settings.custom_instructions,
            autonomy_level=settings.autonomy,
            worker_display_name="Noor",
            user_name=up.get("name", "") or config.user_profile.name,
            user_role=up.get("role", "") or config.user_profile.role,
            user_company=up.get("company", "") or config.user_profile.company,
        )
