"""Tests for ProjectOrchestrator and ProjectWorkspace."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator
from firefly_dworkers.orchestration.workspace import ProjectWorkspace
from firefly_dworkers.sdk.models import ProjectEvent
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import WorkerRole

# Patch targets -- worker_factory and GoalDecompositionPattern are
# imported lazily inside methods, so we patch at the source module.
_FACTORY_PATCH = "firefly_dworkers.workers.factory.worker_factory"
_DECOMP_PATCH = "fireflyframework_genai.reasoning.goal_decomposition.GoalDecompositionPattern"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> TenantConfig:
    """Create a minimal TenantConfig for testing."""
    return TenantConfig(id="test-tenant", name="Test Tenant")


def _make_mock_worker(output: str = "mock output") -> MagicMock:
    """Create a mock worker whose ``run()`` returns an object with ``.output``."""
    worker = MagicMock()
    mock_result = MagicMock()
    mock_result.output = output
    worker.run = AsyncMock(return_value=mock_result)
    # memory setter -- allow assignment
    worker.memory = None
    return worker


def _make_mock_decomposition_result(output: str, success: bool = True) -> MagicMock:
    """Create a mock GoalDecompositionPattern result."""
    result = MagicMock()
    result.output = output
    result.success = success
    result.steps_taken = 3
    result.trace = []
    return result


# ===========================================================================
# ProjectWorkspace tests
# ===========================================================================


class TestProjectWorkspace:
    def test_workspace_creates_with_project_id(self) -> None:
        """ProjectWorkspace should store the project_id."""
        ws = ProjectWorkspace("proj-1")
        assert ws.project_id == "proj-1"

    def test_workspace_set_and_get_fact(self) -> None:
        """Setting and getting a fact should round-trip."""
        ws = ProjectWorkspace("proj-2")
        ws.set_fact("market_size", "$10B")
        assert ws.get_fact("market_size") == "$10B"

    def test_workspace_get_fact_default(self) -> None:
        """Getting a missing fact should return the default."""
        ws = ProjectWorkspace("proj-3")
        assert ws.get_fact("missing", "fallback") == "fallback"

    def test_workspace_get_all_facts(self) -> None:
        """get_all_facts should return all stored facts."""
        ws = ProjectWorkspace("proj-4")
        ws.set_fact("key1", "val1")
        ws.set_fact("key2", "val2")
        facts = ws.get_all_facts()
        assert facts["key1"] == "val1"
        assert facts["key2"] == "val2"

    def test_workspace_get_context(self) -> None:
        """get_context should return a readable string summary."""
        ws = ProjectWorkspace("proj-5")
        ws.set_fact("competitor", "Acme Corp")
        ctx = ws.get_context()
        assert "competitor" in ctx
        assert "Acme Corp" in ctx

    def test_workspace_memory_property(self) -> None:
        """The memory property should return the forked MemoryManager."""
        from fireflyframework_genai.memory.manager import MemoryManager

        ws = ProjectWorkspace("proj-6")
        assert isinstance(ws.memory, MemoryManager)

    def test_workspace_accepts_external_memory(self) -> None:
        """ProjectWorkspace should accept an external MemoryManager."""
        from fireflyframework_genai.memory.manager import MemoryManager

        base = MemoryManager()
        ws = ProjectWorkspace("proj-7", memory=base)
        ws.set_fact("test", "value")
        assert ws.get_fact("test") == "value"


# ===========================================================================
# ProjectOrchestrator tests
# ===========================================================================


class TestProjectOrchestratorInit:
    def test_init_stores_config_and_project_id(self) -> None:
        """The orchestrator should store config and project_id."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="my-proj")
        assert orch._config is config
        assert orch._project_id == "my-proj"

    def test_init_default_project_id(self) -> None:
        """When project_id is empty, it defaults to 'default'."""
        config = _make_config()
        orch = ProjectOrchestrator(config)
        assert orch._project_id == "default"

    def test_init_creates_workspace(self) -> None:
        """The orchestrator should create a ProjectWorkspace."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="ws-test")
        assert isinstance(orch._workspace, ProjectWorkspace)
        assert orch._workspace.project_id == "ws-test"


class TestProjectOrchestratorRun:
    @pytest.mark.anyio()
    async def test_run_returns_result_dict(self) -> None:
        """run() should return a dict with success, deliverables, duration_ms."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="run-test")

        mock_worker = _make_mock_worker("analysis complete")

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, side_effect=ImportError("not available")),
        ):
            mock_factory.create.return_value = mock_worker
            result = await orch.run("Analyze the market")

        assert "success" in result
        assert "deliverables" in result
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], float)

    @pytest.mark.anyio()
    async def test_run_with_successful_decomposition(self) -> None:
        """run() should use GoalDecomposition when available."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="decomp-test")

        mock_worker = _make_mock_worker("task result")
        decomp_result = _make_mock_decomposition_result("Research market trends\nAnalyze competitor pricing")

        mock_decomposer = MagicMock()
        mock_decomposer.execute = AsyncMock(return_value=decomp_result)

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, return_value=mock_decomposer),
        ):
            mock_factory.create.return_value = mock_worker
            result = await orch.run("Full market analysis")

        assert result["success"] is True
        assert "deliverables" in result
        # The decomposer should have been called
        mock_decomposer.execute.assert_called_once()

    @pytest.mark.anyio()
    async def test_run_with_fallback_decomposition(self) -> None:
        """When GoalDecomposition fails, run() should use fallback tasks."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="fallback-test")

        mock_worker = _make_mock_worker("fallback output")

        mock_decomposer = MagicMock()
        mock_decomposer.execute = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, return_value=mock_decomposer),
        ):
            mock_factory.create.return_value = mock_worker
            result = await orch.run("Analyze something")

        assert result["success"] is True
        # Factory called for: manager (decompose), researcher, analyst, manager (synthesis)
        assert mock_factory.create.call_count >= 3

    @pytest.mark.anyio()
    async def test_run_handles_decomposition_failure(self) -> None:
        """When the entire run raises, success should be False."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="error-test")

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.side_effect = RuntimeError("factory exploded")
            result = await orch.run("Analyze something")

        assert result["success"] is False
        assert "error" in result["deliverables"]


class TestProjectOrchestratorRunStream:
    @pytest.mark.anyio()
    async def test_run_stream_yields_project_events(self) -> None:
        """run_stream() should yield ProjectEvent instances."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="stream-test")

        mock_worker = _make_mock_worker("streamed output")

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, side_effect=ImportError("not available")),
        ):
            mock_factory.create.return_value = mock_worker

            events: list[ProjectEvent] = []
            async for event in orch.run_stream("Test brief"):
                events.append(event)
                assert isinstance(event, ProjectEvent)

        assert len(events) > 0

    @pytest.mark.anyio()
    async def test_run_stream_yields_start_and_complete(self) -> None:
        """run_stream() should yield project_start and project_complete events."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="events-test")

        mock_worker = _make_mock_worker("output")

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, side_effect=ImportError("not available")),
        ):
            mock_factory.create.return_value = mock_worker

            events: list[ProjectEvent] = []
            async for event in orch.run_stream("Test brief"):
                events.append(event)

        event_types = [e.type for e in events]
        assert event_types[0] == "project_start"
        assert event_types[-1] == "project_complete"

        # Check that project_start has the correct content
        assert events[0].content == "events-test"
        assert events[0].metadata["brief"] == "Test brief"

    @pytest.mark.anyio()
    async def test_run_stream_handles_task_errors(self) -> None:
        """run_stream() should emit task_error events when tasks fail."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="task-err-test")

        # Worker that fails on run
        fail_worker = MagicMock()
        fail_worker.run = AsyncMock(side_effect=RuntimeError("task failed"))
        fail_worker.memory = None

        # Manager worker for decompose and synthesis
        manager_worker = _make_mock_worker("synthesis output")

        def create_side_effect(role, config, **kwargs):
            name = kwargs.get("name", "")
            # Manager workers for decomposition and synthesis
            if "manager" in name:
                return manager_worker
            # Specialist workers that fail
            return fail_worker

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, side_effect=ImportError("not available")),
        ):
            mock_factory.create.side_effect = create_side_effect

            events: list[ProjectEvent] = []
            async for event in orch.run_stream("Test brief"):
                events.append(event)

        event_types = [e.type for e in events]
        assert "task_error" in event_types

    @pytest.mark.anyio()
    async def test_run_stream_truncates_long_brief(self) -> None:
        """run_stream() should truncate briefs longer than 200 chars in metadata."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="trunc-test")

        long_brief = "x" * 500
        mock_worker = _make_mock_worker("output")

        with (
            patch(_FACTORY_PATCH) as mock_factory,
            patch(_DECOMP_PATCH, side_effect=ImportError("not available")),
        ):
            mock_factory.create.return_value = mock_worker

            events: list[ProjectEvent] = []
            async for event in orch.run_stream(long_brief):
                events.append(event)

        start_event = events[0]
        assert len(start_event.metadata["brief"]) == 200

    @pytest.mark.anyio()
    async def test_run_stream_error_on_catastrophic_failure(self) -> None:
        """run_stream() should yield an error event on catastrophic failure."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="catastrophic-test")

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.side_effect = RuntimeError("total failure")

            events: list[ProjectEvent] = []
            async for event in orch.run_stream("Test brief"):
                events.append(event)

        event_types = [e.type for e in events]
        assert "project_start" in event_types
        assert "error" in event_types


class TestProjectOrchestratorInternal:
    @pytest.mark.anyio()
    async def test_execute_single_task_creates_worker(self) -> None:
        """_execute_single_task should create a worker via worker_factory."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="exec-test")

        mock_worker = _make_mock_worker("task output")

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.return_value = mock_worker
            result = await orch._execute_single_task("analyst", "Analyze trends")

        assert result == "task output"
        mock_factory.create.assert_called_once()
        mock_worker.run.assert_called_once()

    @pytest.mark.anyio()
    async def test_execute_single_task_invalid_role_fallback(self) -> None:
        """_execute_single_task with an invalid role should fall back to ANALYST."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="role-fallback-test")

        mock_worker = _make_mock_worker("fallback output")

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.return_value = mock_worker
            result = await orch._execute_single_task("unknown_role", "Do something")

        assert result == "fallback output"
        # Should have fallen back to WorkerRole.ANALYST
        call_args = mock_factory.create.call_args
        assert call_args[0][0] == WorkerRole.ANALYST

    @pytest.mark.anyio()
    async def test_synthesize_uses_manager(self) -> None:
        """_synthesize should create a MANAGER worker to synthesize results."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="synth-test")

        mock_worker = _make_mock_worker("final synthesis")

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.return_value = mock_worker

            result = await orch._synthesize(
                "Original brief",
                {"task_0": "result 0", "task_1": "result 1"},
            )

        assert result["summary"] == "final synthesis"
        assert result["task_results"]["task_0"] == "result 0"
        # Should have used WorkerRole.MANAGER
        call_args = mock_factory.create.call_args
        assert call_args[0][0] == WorkerRole.MANAGER

    @pytest.mark.anyio()
    async def test_synthesize_handles_failure(self) -> None:
        """_synthesize should return partial results when synthesis fails."""
        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="synth-fail-test")

        fail_worker = MagicMock()
        fail_worker.run = AsyncMock(side_effect=RuntimeError("synthesis error"))
        fail_worker.memory = None

        with patch(_FACTORY_PATCH) as mock_factory:
            mock_factory.create.return_value = fail_worker
            result = await orch._synthesize("Brief", {"task_0": "data"})

        assert "synthesis_error" in result
        assert result["task_results"]["task_0"] == "data"


class TestMapToWorkers:
    def test_map_to_workers_keyword_matching(self) -> None:
        """_map_to_workers should assign roles based on keywords."""
        output = (
            "Research the competitive landscape\n"
            "Analyze current market position\n"
            "Gather data and statistics on revenue\n"
            "Plan the project timeline"
        )
        tasks = ProjectOrchestrator._map_to_workers(output)

        assert len(tasks) == 4
        # "Research" -> researcher
        assert tasks[0][0] == "researcher"
        # "Analyze" -> analyst
        assert tasks[1][0] == "analyst"
        # "data" -> data_analyst
        assert tasks[2][0] == "data_analyst"
        # "plan" + "timeline" -> manager
        assert tasks[3][0] == "manager"

    def test_map_to_workers_default_is_analyst(self) -> None:
        """Lines without matching keywords should default to analyst."""
        output = "Do something generic\nAnother generic task"
        tasks = ProjectOrchestrator._map_to_workers(output)
        assert len(tasks) == 2
        assert all(role == "analyst" for role, _ in tasks)

    def test_map_to_workers_skips_empty_lines(self) -> None:
        """Empty lines should be skipped."""
        output = "Research trends\n\n\nAnalyze results\n"
        tasks = ProjectOrchestrator._map_to_workers(output)
        assert len(tasks) == 2

    def test_map_to_workers_empty_input(self) -> None:
        """Empty input should return an empty list."""
        tasks = ProjectOrchestrator._map_to_workers("")
        assert tasks == []

    def test_map_to_workers_case_insensitive(self) -> None:
        """Keyword matching should be case-insensitive."""
        output = "RESEARCH the market\nANALYZE the competition"
        tasks = ProjectOrchestrator._map_to_workers(output)
        assert tasks[0][0] == "researcher"
        assert tasks[1][0] == "analyst"
