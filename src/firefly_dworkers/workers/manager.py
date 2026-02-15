"""ManagerWorker -- project management digital worker.

When provided with specialist workers, can use DelegationRouter
to intelligently route tasks and PlanAndExecute for planning.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from firefly_dworkers.exceptions import VerticalNotFoundError
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import manager_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy imports -- these framework modules are optional dependencies.
# We expose module-level helpers so tests can patch a single location.
# ---------------------------------------------------------------------------


def _import_delegation() -> tuple[Any, Any, Any, Any]:
    """Lazily import delegation classes.  Raises ImportError when absent."""
    from fireflyframework_genai.agents.delegation import (
        CapabilityStrategy,
        ContentBasedStrategy,
        DelegationRouter,
        RoundRobinStrategy,
    )

    return DelegationRouter, ContentBasedStrategy, CapabilityStrategy, RoundRobinStrategy


def _import_plan_and_execute() -> Any:
    """Lazily import PlanAndExecutePattern.  Raises ImportError when absent."""
    from fireflyframework_genai.reasoning.plan_and_execute import (
        PlanAndExecutePattern,
    )

    return PlanAndExecutePattern


# For patching convenience in tests -- re-export at module level
try:
    DelegationRouter, ContentBasedStrategy, CapabilityStrategy, RoundRobinStrategy = _import_delegation()
except ImportError:
    DelegationRouter = None  # type: ignore[assignment,misc]
    ContentBasedStrategy = None  # type: ignore[assignment,misc]
    CapabilityStrategy = None  # type: ignore[assignment,misc]
    RoundRobinStrategy = None  # type: ignore[assignment,misc]


@worker_factory.register(
    WorkerRole.MANAGER,
    description="Manager — team lead who routes tasks & launches plans",
    tags=["manager", "orchestration"],
    display_name="Amara",
    avatar="A",
    avatar_color="green",
    tagline="Your team lead — routes tasks and launches plans",
)
class ManagerWorker(BaseWorker):
    """Digital worker specialised in project management.

    Coordinates tasks, tracks progress, manages timelines, and ensures
    consulting deliverables are completed on schedule and within scope.

    When provided with specialist workers, can use DelegationRouter
    to intelligently route tasks and PlanAndExecute for planning.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        specialists: Sequence[BaseWorker] | None = None,
        delegation_strategy: str = "content",
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
            description="Project manager worker that coordinates specialist workers",
            tags=["manager", "consulting", "delegation"],
            **kwargs,
        )

        self._specialists: list[Any] = list(specialists) if specialists else []
        self._delegation_strategy = delegation_strategy
        self._router: Any | None = None
        self._planner: Any | None = None

    # -- Properties ----------------------------------------------------------

    @property
    def router(self) -> Any | None:
        """The delegation router, lazily initialised when specialists are set."""
        if self._router is None and self._specialists:
            self._router = self._create_router()
        return self._router

    @property
    def planner(self) -> Any | None:
        """The planning pattern, lazily initialised."""
        if self._planner is None:
            try:
                pattern_cls = _import_plan_and_execute()
                self._planner = pattern_cls(max_steps=15, allow_replan=True)
            except ImportError:
                logger.debug("PlanAndExecutePattern not available")
        return self._planner

    # -- Public API ----------------------------------------------------------

    def set_specialists(self, specialists: Sequence[BaseWorker]) -> None:
        """Set or update the pool of specialist workers for delegation."""
        self._specialists = list(specialists)
        self._router = None  # Reset so it's recreated on next access

    async def delegate(self, prompt: str) -> Any:
        """Delegate a task to the most appropriate specialist.

        Uses DelegationRouter if available, otherwise runs directly.
        """
        if self.router:
            return await self.router.route(prompt)
        return await self.run(prompt)

    async def plan_and_execute(self, brief: str) -> Any:
        """Plan tasks from a brief and execute them.

        Uses PlanAndExecute pattern if available, otherwise runs directly.
        """
        if self.planner:
            return await self.planner.execute(self, input=brief)
        return await self.run(brief)

    # -- Internal helpers ----------------------------------------------------

    def _create_router(self) -> Any | None:
        """Create a DelegationRouter with the configured strategy."""
        try:
            router_cls, content_cls, cap_cls, rr_cls = _import_delegation()

            strategies: dict[str, Any] = {
                "content": lambda: content_cls(),
                "capability": lambda: cap_cls(required_tag="consulting"),
                "round_robin": lambda: rr_cls(),
            }
            strategy_factory = strategies.get(self._delegation_strategy, strategies["content"])
            return router_cls(
                agents=self._specialists,
                strategy=strategy_factory(),
                memory=self.memory,
            )
        except ImportError:
            logger.debug("DelegationRouter not available")
            return None

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

        settings = config.workers.settings_for("manager")
        return get_worker_prompt(
            "manager",
            company_name=config.branding.company_name,
            verticals="\n".join(vertical_parts),
            custom_instructions=settings.custom_instructions,
            worker_display_name="Amara",
            user_name=(user_profile or {}).get("name", ""),
            user_role=(user_profile or {}).get("role", ""),
            user_company=(user_profile or {}).get("company", ""),
        )
