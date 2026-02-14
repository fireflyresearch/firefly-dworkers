"""LocalClient -- calls the dworkers Python APIs directly."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from firefly_dworkers.sdk.models import ProjectEvent, StreamEvent
from firefly_dworkers_cli.tui.backend.models import (
    ConnectorStatus,
    ConversationSummary,
    PlanInfo,
    UsageStats,
    WorkerInfo,
)

logger = logging.getLogger(__name__)

# Category mapping for connector names.
_CONNECTOR_CATEGORIES: dict[str, str] = {
    "web_search": "search",
    "web_browser": "search",
    "sharepoint": "storage",
    "google_drive": "storage",
    "confluence": "storage",
    "s3": "storage",
    "jira": "project_management",
    "asana": "project_management",
    "slack": "messaging",
    "teams": "messaging",
    "email": "messaging",
    "sql": "data",
    "api": "data",
    "presentation": "document",
    "document": "document",
    "spreadsheet": "document",
    "vision": "analysis",
    "image_generation": "media",
    "stock_images": "media",
}


class LocalClient:
    """Backend that calls the dworkers Python APIs directly.

    All imports from ``firefly_dworkers`` are done lazily inside methods so
    this module can be imported even when optional core dependencies are not
    installed.
    """

    _workers_imported: bool = False

    def __init__(self, *, checkpoint_handler: Any | None = None) -> None:
        self._checkpoint_handler = checkpoint_handler

    @classmethod
    def _ensure_workers_registered(cls) -> None:
        """Import the workers package once to trigger self-registration."""
        if not cls._workers_imported:
            try:
                import firefly_dworkers.workers  # noqa: F401 — triggers @worker_factory.register
                cls._workers_imported = True
            except Exception:
                logger.debug("Failed to import workers package", exc_info=True)

    # -- Workers --------------------------------------------------------------

    async def list_workers(self, tenant_id: str = "default") -> list[WorkerInfo]:
        try:
            self._ensure_workers_registered()
            from firefly_dworkers.tenants.registry import tenant_registry
            from firefly_dworkers.workers.factory import worker_factory

            roles = worker_factory.list_roles()
            config = tenant_registry.get(tenant_id)
            workers: list[WorkerInfo] = []
            for role in roles:
                settings = config.workers.settings_for(role.value)
                workers.append(
                    WorkerInfo(
                        role=role.value,
                        name=role.value.replace("_", " ").title(),
                        enabled=settings.enabled,
                        autonomy=settings.autonomy,
                        model=config.models.default,
                    )
                )
            return workers
        except Exception:
            logger.debug("list_workers failed, returning defaults", exc_info=True)
            return [
                WorkerInfo(role="analyst", name="Analyst"),
                WorkerInfo(role="researcher", name="Researcher"),
                WorkerInfo(role="data_analyst", name="Data Analyst"),
                WorkerInfo(role="manager", name="Manager"),
                WorkerInfo(role="designer", name="Designer"),
            ]

    async def run_worker(
        self,
        role: str,
        prompt: str,
        *,
        tenant_id: str = "default",
        conversation_id: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        try:
            self._ensure_workers_registered()
            from firefly_dworkers.tenants.registry import tenant_registry
            from firefly_dworkers.types import WorkerRole
            from firefly_dworkers.workers.factory import worker_factory

            config = tenant_registry.get(tenant_id)
            worker_role = WorkerRole(role)
            worker = worker_factory.create(
                worker_role, config, name=f"{role}-tui"
            )
            if self._checkpoint_handler is not None and hasattr(worker, "checkpoint_handler"):
                worker.checkpoint_handler = self._checkpoint_handler
            result = await worker.run(prompt)
            output = str(result.output) if hasattr(result, "output") else str(result)
            yield StreamEvent(type="complete", content=output)
        except Exception as exc:
            logger.warning("run_worker failed: %s", exc, exc_info=True)
            yield StreamEvent(type="error", content=str(exc))

    # -- Projects -------------------------------------------------------------

    async def run_project(
        self,
        brief: str,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[ProjectEvent]:
        try:
            from firefly_dworkers.orchestration.orchestrator import (
                ProjectOrchestrator,
            )
            from firefly_dworkers.tenants.registry import tenant_registry

            config = tenant_registry.get(tenant_id)
            orchestrator = ProjectOrchestrator(config)
            async for event in orchestrator.run_stream(brief):
                yield event
        except Exception as exc:
            logger.warning("run_project failed: %s", exc, exc_info=True)
            yield ProjectEvent(type="error", content=str(exc))

    # -- Plans ----------------------------------------------------------------

    async def list_plans(self) -> list[PlanInfo]:
        try:
            from firefly_dworkers.plans.registry import plan_registry

            plan_names = plan_registry.list_plans()
            plans: list[PlanInfo] = []
            for name in plan_names:
                plan = plan_registry.get(name)
                worker_roles = sorted(
                    {step.worker_role.value for step in plan.steps}
                )
                plans.append(
                    PlanInfo(
                        name=plan.name,
                        description=plan.description,
                        steps=len(plan.steps),
                        worker_roles=worker_roles,
                    )
                )
            return plans
        except Exception:
            logger.debug("list_plans failed, returning empty", exc_info=True)
            return []

    async def execute_plan(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[StreamEvent]:
        try:
            self._ensure_workers_registered()
            from firefly_dworkers.plans.builder import PlanBuilder
            from firefly_dworkers.plans.registry import plan_registry
            from firefly_dworkers.tenants.registry import tenant_registry

            plan = plan_registry.get(name)
            config = tenant_registry.get(tenant_id)

            step_names = [s.step_id for s in plan.steps]
            yield StreamEvent(
                type="token",
                content=(
                    f"**Executing plan:** {plan.name}\n"
                    f"**Steps ({len(plan.steps)}):** {', '.join(step_names)}\n\n"
                ),
            )

            # Build and run the pipeline
            builder = PlanBuilder(plan, config)
            engine = builder.build()
            result = await engine.run(inputs=inputs or {})

            # Report results per node
            for node_id, node_result in result.outputs.items():
                if node_result.skipped:
                    yield StreamEvent(
                        type="token",
                        content=f"**{node_id}:** _skipped_\n\n",
                    )
                elif node_result.success:
                    output = str(node_result.output) if node_result.output else "(no output)"
                    yield StreamEvent(
                        type="token",
                        content=f"**{node_id}:** {output}\n\n",
                    )
                else:
                    yield StreamEvent(
                        type="token",
                        content=f"**{node_id}:** Error — {node_result.error}\n\n",
                    )

            # Final summary
            status = "completed successfully" if result.success else "completed with errors"
            duration = f"{result.total_duration_ms:.0f}ms" if result.total_duration_ms else "N/A"
            yield StreamEvent(
                type="complete",
                content=f"\n---\n**Plan {status}** in {duration}.",
            )
        except Exception as exc:
            logger.warning("execute_plan failed: %s", exc, exc_info=True)
            yield StreamEvent(type="error", content=str(exc))

    # -- Tenants --------------------------------------------------------------

    async def list_tenants(self) -> list[str]:
        try:
            from firefly_dworkers.tenants.registry import tenant_registry

            return tenant_registry.list_tenants()
        except Exception:
            logger.debug("list_tenants failed, returning default", exc_info=True)
            return ["default"]

    # -- Connectors -----------------------------------------------------------

    async def list_connectors(
        self, tenant_id: str = "default"
    ) -> list[ConnectorStatus]:
        try:
            from firefly_dworkers.tenants.registry import tenant_registry

            config = tenant_registry.get(tenant_id)
            connectors: list[ConnectorStatus] = []
            for field_name in type(config.connectors).model_fields:
                cfg = getattr(config.connectors, field_name)
                enabled = getattr(cfg, "enabled", False)
                provider = getattr(cfg, "provider", "")
                connectors.append(
                    ConnectorStatus(
                        name=field_name,
                        category=_CONNECTOR_CATEGORIES.get(field_name, "other"),
                        configured=enabled,
                        provider=provider,
                    )
                )
            return connectors
        except Exception:
            logger.debug(
                "list_connectors failed, returning empty", exc_info=True
            )
            return []

    # -- Usage ----------------------------------------------------------------

    async def get_usage_stats(self, tenant_id: str = "default") -> UsageStats:
        """Return usage statistics.

        Token tracking is done client-side in app.py via word-count
        heuristic. Core-level usage tracking is planned for a future release.
        """
        return UsageStats()

    # -- Conversations --------------------------------------------------------

    async def list_conversations(
        self, tenant_id: str = "default"
    ) -> list[ConversationSummary]:
        from firefly_dworkers_cli.tui.backend.store import ConversationStore

        store = ConversationStore()
        return store.list_conversations()
