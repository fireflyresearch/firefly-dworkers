"""LocalClient -- calls the dworkers Python APIs directly."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from firefly_dworkers.sdk.models import ProjectEvent, StreamEvent
from firefly_dworkers_cli.tui.backend.models import (
    ConnectorStatus,
    ConversationSummary,
    FileAttachment,
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


def _build_participant_context(
    participants: list[tuple[str, str, str]],
    current_role: str,
) -> str:
    """Build conversation context prefix for a worker prompt.

    Args:
        participants: List of (role, display_name, tagline) tuples.
        current_role: The role receiving this prompt (excluded from list).
    """
    others = [
        (role, name, tagline)
        for role, name, tagline in participants
        if role != current_role and role != "user"
    ]
    if not others:
        return ""
    labels = [f"{name} (@{role})" for role, name, tagline in others]
    return f"[Conversation participants: {', '.join(labels)}]\n\n"


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
                # Pull description and identity from factory metadata (registered at import time).
                try:
                    meta = worker_factory.get_metadata(role)
                    description = meta.description
                    display_name = meta.display_name or role.value.replace("_", " ").title()
                    tagline = meta.tagline
                    avatar = meta.avatar
                    avatar_color = meta.avatar_color
                except KeyError:
                    description = ""
                    display_name = role.value.replace("_", " ").title()
                    tagline = ""
                    avatar = ""
                    avatar_color = ""
                # Try to determine available tools from toolkit factory.
                tool_names: list[str] = []
                try:
                    from firefly_dworkers.tools.toolkits import (
                        analyst_toolkit,
                        data_analyst_toolkit,
                        designer_toolkit,
                        manager_toolkit,
                        researcher_toolkit,
                    )

                    toolkit_map = {
                        "manager": manager_toolkit,
                        "analyst": analyst_toolkit,
                        "researcher": researcher_toolkit,
                        "data_analyst": data_analyst_toolkit,
                        "designer": designer_toolkit,
                    }
                    role_key = role.value if hasattr(role, "value") else role
                    factory_fn = toolkit_map.get(role_key)
                    if factory_fn:
                        toolkit = factory_fn(config)
                        if hasattr(toolkit, "tools"):
                            tool_names = [t.name for t in toolkit.tools][:5]
                except Exception:
                    pass  # Tools are best-effort

                workers.append(
                    WorkerInfo(
                        role=role.value,
                        name=display_name,
                        description=description,
                        tagline=tagline,
                        avatar=avatar,
                        avatar_color=avatar_color,
                        enabled=settings.enabled,
                        autonomy=settings.autonomy,
                        model=config.models.default,
                        tools=tool_names,
                    )
                )
            return workers
        except Exception:
            logger.debug("list_workers failed, returning defaults", exc_info=True)
            return [
                WorkerInfo(role="manager", name="Amara", avatar="A", avatar_color="green", tagline="Your team lead"),
                WorkerInfo(role="analyst", name="Leo", avatar="L", avatar_color="blue", tagline="Strategic analysis"),
                WorkerInfo(role="researcher", name="Yuki", avatar="Y", avatar_color="cyan", tagline="Deep research"),
                WorkerInfo(role="data_analyst", name="Kofi", avatar="K", avatar_color="yellow", tagline="Data processing"),
                WorkerInfo(role="designer", name="Noor", avatar="N", avatar_color="magenta", tagline="Creative design"),
            ]

    @staticmethod
    def _build_multimodal_content(
        prompt: str, attachments: list[FileAttachment],
    ) -> list:
        """Convert a text prompt + file attachments into a UserContent list.

        The framework's ``FireflyAgent.run_stream()`` accepts
        ``str | Sequence[UserContent]``.  When attachments are present we
        build a list: the text prompt first, then each attachment converted
        to the appropriate framework content type.
        """
        import base64

        content: list = [prompt]
        for att in attachments:
            b64 = base64.b64encode(att.data).decode()
            data_url = f"data:{att.media_type};base64,{b64}"
            if att.media_type.startswith("image/"):
                try:
                    from fireflyframework_genai.types import ImageUrl
                    content.append(ImageUrl(url=data_url))
                except ImportError:
                    content.append(f"[Image: {att.filename}]")
            elif att.media_type == "application/pdf":
                try:
                    from fireflyframework_genai.types import DocumentUrl
                    content.append(DocumentUrl(url=data_url))
                except ImportError:
                    content.append(f"[Document: {att.filename}]")
            else:
                try:
                    from fireflyframework_genai.types import BinaryContent
                    content.append(BinaryContent(data=att.data, media_type=att.media_type))
                except ImportError:
                    # Fallback: embed text content directly.
                    try:
                        text_content = att.data.decode("utf-8")
                        content.append(f"--- {att.filename} ---\n{text_content}")
                    except UnicodeDecodeError:
                        content.append(f"[Binary file: {att.filename}]")
        return content

    async def run_worker(
        self,
        role: str,
        prompt: str,
        *,
        attachments: list[FileAttachment] | None = None,
        tenant_id: str = "default",
        conversation_id: str | None = None,
        message_history: list | None = None,
        participants: list[tuple[str, str, str]] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        try:
            self._ensure_workers_registered()
            from firefly_dworkers.tenants.registry import tenant_registry
            from firefly_dworkers.types import WorkerRole
            from firefly_dworkers.workers.factory import worker_factory

            config = tenant_registry.get(tenant_id)
            try:
                worker_role = WorkerRole(role)
            except ValueError:
                worker_role = WorkerRole.ANALYST  # fallback for unknown roles
                logger.info("Unknown role %r, falling back to analyst", role)
            worker = worker_factory.create(
                worker_role, config, name=f"{role}-tui"
            )
            if self._checkpoint_handler is not None and hasattr(worker, "checkpoint_handler"):
                worker.checkpoint_handler = self._checkpoint_handler

            # Wire up delegation for manager when multiple agents present.
            if role == "manager" and participants:
                agent_roles = [r for r, _, _ in participants if r not in ("user", "manager")]
                if len(agent_roles) >= 2 and hasattr(worker, "set_specialists"):
                    try:
                        specialists = []
                        for agent_role in agent_roles:
                            specialist = worker_factory.create(
                                WorkerRole(agent_role), config, name=f"{agent_role}-delegate"
                            )
                            specialists.append(specialist)
                        worker.set_specialists(specialists)
                    except Exception:
                        pass  # Delegation is best-effort; fall back to manager handling directly

            # Build multimodal content if attachments are provided.
            input_content: str | list = prompt
            if attachments:
                input_content = self._build_multimodal_content(prompt, attachments)

            if participants:
                context_prefix = _build_participant_context(participants, role)
                if context_prefix:
                    if isinstance(input_content, str):
                        input_content = context_prefix + input_content
                    elif isinstance(input_content, list):
                        input_content[0] = context_prefix + str(input_content[0])

            # Prefer streaming when available.
            # FireflyAgent.run_stream() returns an async context manager
            # (not an async generator), so we use ``async with await ...``.
            # Build run_stream kwargs, including conversation history when available.
            stream_kwargs: dict[str, Any] = {"streaming_mode": "incremental"}
            if message_history is not None:
                stream_kwargs["message_history"] = message_history

            if hasattr(worker, "run_stream") and callable(worker.run_stream):
                async with await worker.run_stream(
                    input_content, **stream_kwargs,
                ) as stream:
                    # Attempt to capture tool events from underlying pydantic-ai stream.
                    raw_stream = getattr(stream, "_stream", None)
                    if raw_stream is not None and hasattr(raw_stream, "__aiter__"):
                        try:
                            async for event in raw_stream:
                                ek = getattr(event, "event_kind", None)
                                if ek == "part_delta":
                                    delta = getattr(event, "delta", None)
                                    if delta is not None:
                                        content_delta = getattr(delta, "content_delta", None)
                                        if content_delta:
                                            yield StreamEvent(type="token", content=content_delta)
                                elif ek == "part_start":
                                    part = getattr(event, "part", None)
                                    if part is not None:
                                        tool_name = getattr(part, "tool_name", None)
                                        if tool_name:
                                            args: dict[str, Any] = {}
                                            raw_args = getattr(part, "args", None)
                                            if raw_args:
                                                try:
                                                    args = (
                                                        json.loads(raw_args)
                                                        if isinstance(raw_args, str)
                                                        else (
                                                            dict(raw_args)
                                                            if hasattr(raw_args, "items")
                                                            else {}
                                                        )
                                                    )
                                                except Exception:
                                                    args = {"raw": str(raw_args)}
                                            yield StreamEvent(
                                                type="tool_call",
                                                content=tool_name,
                                                metadata={
                                                    "tool_name": tool_name,
                                                    "params": args,
                                                    "status": "running",
                                                },
                                            )
                            yield StreamEvent(type="complete", content="")
                        except Exception:
                            # If raw stream iteration fails, fall back to stream_tokens.
                            logger.debug(
                                "Raw stream iteration failed, falling back to stream_tokens",
                                exc_info=True,
                            )
                            async for token in stream.stream_tokens():
                                yield StreamEvent(type="token", content=token)
                            yield StreamEvent(type="complete", content="")
                    else:
                        # Standard path: stream_tokens only.
                        async for token in stream.stream_tokens():
                            yield StreamEvent(type="token", content=token)
                        yield StreamEvent(type="complete", content="")
            else:
                result = await worker.run(input_content)
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
        """Return usage statistics from the framework's default tracker."""
        try:
            from fireflyframework_genai.observability.usage import default_usage_tracker

            summary = default_usage_tracker.get_summary()
            avg_ms = (
                summary.total_latency_ms / summary.total_requests
                if summary.total_requests
                else 0.0
            )
            return UsageStats(
                total_tokens=summary.total_tokens,
                total_cost_usd=summary.total_cost_usd,
                tasks_completed=summary.total_requests,
                avg_response_ms=avg_ms,
                by_model=summary.by_model,
                by_worker=summary.by_agent,
            )
        except ImportError:
            logger.debug("Framework usage tracker not available")
            return UsageStats()

    # -- Conversations --------------------------------------------------------

    async def list_conversations(
        self, tenant_id: str = "default"
    ) -> list[ConversationSummary]:
        from firefly_dworkers_cli.tui.backend.store import ConversationStore

        store = ConversationStore()
        return store.list_conversations()
