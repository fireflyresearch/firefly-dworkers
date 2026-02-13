"""ProjectOrchestrator -- multi-agent collaboration on consulting projects."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from firefly_dworkers.orchestration.workspace import ProjectWorkspace
from firefly_dworkers.sdk.models import ProjectEvent
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import WorkerRole

logger = logging.getLogger(__name__)


class ProjectOrchestrator:
    """Orchestrates multi-agent collaboration on consulting projects.

    Flow:
    1. Manager decomposes project brief using GoalDecomposition
    2. For each task, delegate to the appropriate specialist worker
    3. Workers share findings via the project workspace
    4. Manager synthesises final deliverables

    Parameters:
        config: Tenant configuration for worker creation.
        project_id: Unique project identifier.
    """

    def __init__(
        self,
        config: TenantConfig,
        *,
        project_id: str = "",
    ) -> None:
        self._config = config
        self._project_id = project_id or "default"
        self._workspace = ProjectWorkspace(self._project_id)

    # -- Public API -----------------------------------------------------------

    async def run(self, brief: str) -> dict[str, Any]:
        """Run the project synchronously, returning a result dict.

        Returns:
            A dict with keys ``"success"``, ``"deliverables"``, and
            ``"duration_ms"``.
        """
        t0 = time.perf_counter()
        deliverables: dict[str, Any] = {}
        success = True

        try:
            # Phase 1: Decompose the brief
            decomposition = await self._decompose(brief)

            # Phase 2: Execute tasks via delegation
            task_results = await self._execute_tasks(decomposition)

            # Phase 3: Synthesise deliverables
            deliverables = await self._synthesize(brief, task_results)

        except Exception as exc:
            logger.exception("Project '%s' failed", self._project_id)
            success = False
            deliverables = {"error": str(exc)}

        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "success": success,
            "deliverables": deliverables,
            "duration_ms": elapsed,
        }

    async def run_stream(self, brief: str) -> AsyncIterator[ProjectEvent]:
        """Run the project, yielding events as progress is made."""
        t0 = time.perf_counter()

        yield ProjectEvent(
            type="project_start",
            content=self._project_id,
            metadata={"brief": brief[:200]},
        )

        try:
            # Phase 1: Decompose
            yield ProjectEvent(type="phase_start", content="decomposition")
            decomposition = await self._decompose(brief)
            yield ProjectEvent(
                type="phase_complete",
                content="decomposition",
                metadata={"tasks": len(decomposition)},
            )

            # Phase 2: Execute tasks
            yield ProjectEvent(type="phase_start", content="execution")
            task_results: dict[str, Any] = {}
            for i, (role, task) in enumerate(decomposition):
                yield ProjectEvent(
                    type="task_assigned",
                    content=task,
                    metadata={"worker_role": role, "task_index": i},
                )
                try:
                    result = await self._execute_single_task(role, task)
                    task_results[f"task_{i}"] = result
                    yield ProjectEvent(
                        type="task_complete",
                        content=task,
                        metadata={"worker_role": role, "task_index": i},
                    )
                except Exception as exc:
                    logger.warning("Task %d failed: %s", i, exc)
                    yield ProjectEvent(
                        type="task_error",
                        content=str(exc),
                        metadata={"worker_role": role, "task_index": i},
                    )

            yield ProjectEvent(type="phase_complete", content="execution")

            # Phase 3: Synthesise
            yield ProjectEvent(type="phase_start", content="synthesis")
            await self._synthesize(brief, task_results)
            yield ProjectEvent(type="phase_complete", content="synthesis")

            elapsed = (time.perf_counter() - t0) * 1000
            yield ProjectEvent(
                type="project_complete",
                content=self._project_id,
                metadata={"success": True, "duration_ms": elapsed},
            )

        except Exception as exc:
            logger.exception("Project '%s' streaming failed", self._project_id)
            yield ProjectEvent(type="error", content=str(exc))

    # -- Internal helpers -----------------------------------------------------

    async def _decompose(self, brief: str) -> list[tuple[str, str]]:
        """Decompose the brief into ``(worker_role, task_description)`` pairs.

        Uses GoalDecomposition via the Manager worker.  Falls back to a
        simple two-task split when decomposition is unavailable.
        """
        from firefly_dworkers.workers.factory import worker_factory

        manager = worker_factory.create(WorkerRole.MANAGER, self._config, name=f"manager-{self._project_id}")
        manager.memory = self._workspace.memory

        try:
            from fireflyframework_genai.reasoning.goal_decomposition import (
                GoalDecompositionPattern,
            )

            decomposer = GoalDecompositionPattern(max_steps=20)
            result = await decomposer.execute(manager, input=brief)

            # Parse the decomposition output into role-task pairs
            tasks: list[tuple[str, str]] = []
            if hasattr(result, "output") and result.output:
                output = result.output if isinstance(result.output, str) else str(result.output)
                tasks = self._map_to_workers(output)

            if not tasks:
                # Fallback: assign the full brief to analyst
                tasks = [("analyst", brief)]

            return tasks

        except Exception:
            logger.warning(
                "GoalDecomposition failed, falling back to simple decomposition",
                exc_info=True,
            )
            # Simple fallback: split work between analyst and researcher
            return [
                ("researcher", f"Research background and context for: {brief}"),
                ("analyst", f"Analyze and provide recommendations for: {brief}"),
            ]

    async def _execute_tasks(self, tasks: list[tuple[str, str]]) -> dict[str, Any]:
        """Execute all tasks sequentially, collecting results."""
        results: dict[str, Any] = {}
        for i, (role, task) in enumerate(tasks):
            try:
                result = await self._execute_single_task(role, task)
                results[f"task_{i}"] = result
                # Store result in workspace for other workers to reference
                self._workspace.set_fact(f"task_{i}_result", result)
            except Exception as exc:
                logger.warning("Task %d (%s) failed: %s", i, role, exc)
                results[f"task_{i}"] = {"error": str(exc)}
        return results

    async def _execute_single_task(self, role: str, task: str) -> str:
        """Execute a single task using the appropriate worker."""
        from firefly_dworkers.workers.factory import worker_factory

        try:
            worker_role = WorkerRole(role)
        except ValueError:
            worker_role = WorkerRole.ANALYST  # fallback for unknown roles

        worker = worker_factory.create(worker_role, self._config, name=f"{role}-{self._project_id}")
        worker.memory = self._workspace.memory

        # Include workspace context in the prompt
        context = self._workspace.get_context()
        prompt = f"{task}\n\nShared workspace context:\n{context}" if context else task

        result = await worker.run(prompt)
        output = str(result.output) if hasattr(result, "output") else str(result)
        return output

    async def _synthesize(self, brief: str, task_results: dict[str, Any]) -> dict[str, Any]:
        """Synthesise final deliverables from task results."""
        from firefly_dworkers.workers.factory import worker_factory

        manager = worker_factory.create(
            WorkerRole.MANAGER,
            self._config,
            name=f"manager-synthesis-{self._project_id}",
        )
        manager.memory = self._workspace.memory

        # Build synthesis prompt with workspace context
        results_summary = "\n".join(f"Task {k}: {v}" for k, v in task_results.items())
        context = self._workspace.get_context()
        prompt = (
            f"Original brief: {brief}\n\n"
            f"Task results:\n{results_summary}\n\n"
        )
        if context:
            prompt += f"Workspace context:\n{context}\n\n"
        prompt += "Please synthesize a final deliverable from these results."

        try:
            result = await manager.run(prompt)
            output = str(result.output) if hasattr(result, "output") else str(result)
            return {"summary": output, "task_results": task_results}
        except Exception as exc:
            logger.warning("Synthesis failed: %s", exc)
            return {"task_results": task_results, "synthesis_error": str(exc)}

    @staticmethod
    def _map_to_workers(decomposition_output: str) -> list[tuple[str, str]]:
        """Map decomposition output to worker role-task pairs.

        Uses simple keyword matching to assign tasks to appropriate roles.

        .. note::
            Task 15 will replace this with DelegationRouter +
            ContentBasedStrategy for intelligent LLM-based routing.
        """
        tasks: list[tuple[str, str]] = []
        lines = [line.strip() for line in decomposition_output.split("\n") if line.strip()]

        role_keywords: dict[str, list[str]] = {
            "researcher": [
                "research",
                "investigate",
                "survey",
                "literature",
                "background",
                "explore",
            ],
            "analyst": [
                "analyze",
                "recommend",
                "evaluate",
                "assess",
                "compare",
                "review",
            ],
            "data_analyst": [
                "data",
                "statistics",
                "metrics",
                "quantitative",
                "numbers",
                "dataset",
            ],
            "manager": [
                "coordinate",
                "plan",
                "schedule",
                "timeline",
                "milestone",
            ],
        }

        for line in lines:
            lower = line.lower()
            assigned_role = "analyst"  # default
            for role, keywords in role_keywords.items():
                if any(kw in lower for kw in keywords):
                    assigned_role = role
                    break
            tasks.append((assigned_role, line))

        return tasks
