"""End-to-end integration tests for the firefly-dworkers platform.

These tests exercise the full stack from tenant config through workers,
plans, knowledge, and the server API -- without requiring a real LLM.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic_ai.models.test import TestModel

from firefly_dworkers.autonomy.levels import should_checkpoint
from firefly_dworkers.config import DworkersConfig, get_config, reset_config
from firefly_dworkers.knowledge import (
    DocumentIndexer,
    KnowledgeRepository,
    KnowledgeRetriever,
)
from firefly_dworkers.plans import PlanBuilder, plan_registry
from firefly_dworkers.tenants.config import (
    ConnectorsConfig,
    TenantConfig,
    WebSearchConnectorConfig,
)
from firefly_dworkers.tenants.registry import tenant_registry
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.verticals import get_vertical, list_verticals
from firefly_dworkers.workers import (
    AnalystWorker,
    DataAnalystWorker,
    ManagerWorker,
    ResearcherWorker,
    worker_registry,
)
from firefly_dworkers_server.app import create_dworkers_app


class TestFullStack:
    """Integration tests that exercise the full stack."""

    def _make_tenant_config(self) -> TenantConfig:
        return TenantConfig(
            id="integration-test",
            name="Integration Test Tenant",
            verticals=["technology", "healthcare"],
            connectors=ConnectorsConfig(
                web_search=WebSearchConnectorConfig(enabled=True, provider="tavily", api_key="test-key"),
            ),
        )

    def test_tenant_config_to_workers(self):
        """Create a tenant config and instantiate all 4 worker types."""
        config = self._make_tenant_config()

        analyst = AnalystWorker(config, model=TestModel(), auto_register=False)
        researcher = ResearcherWorker(config, model=TestModel(), auto_register=False)
        data_analyst = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        manager = ManagerWorker(config, model=TestModel(), auto_register=False)

        assert analyst.role == WorkerRole.ANALYST
        assert researcher.role == WorkerRole.RESEARCHER
        assert data_analyst.role == WorkerRole.DATA_ANALYST
        assert manager.role == WorkerRole.MANAGER

        # All workers should have default autonomy from config
        for w in [analyst, researcher, data_analyst, manager]:
            assert w.autonomy_level == AutonomyLevel.SEMI_SUPERVISED

    def test_tenant_config_with_custom_autonomy(self):
        """Workers respect per-role autonomy overrides."""
        config = self._make_tenant_config()
        analyst = AnalystWorker(
            config,
            model=TestModel(),
            autonomy_level=AutonomyLevel.AUTONOMOUS,
            auto_register=False,
        )
        assert analyst.autonomy_level == AutonomyLevel.AUTONOMOUS

    def test_verticals_in_worker_instructions(self):
        """Worker instructions include vertical-specific content."""
        config = self._make_tenant_config()
        analyst = AnalystWorker(config, model=TestModel(), auto_register=False)

        # Check that verticals are loaded
        available = list_verticals()
        assert "technology" in available
        assert "healthcare" in available

        # The worker's instructions should contain vertical prompt fragments
        tech = get_vertical("technology")
        assert tech.system_prompt_fragment != ""

        # Instructions are stored internally on BaseWorker
        assert hasattr(analyst, "_instructions_text")
        assert isinstance(analyst._instructions_text, str)
        assert len(analyst._instructions_text) > 0

    def test_worker_instructions_contain_vertical_content(self):
        """Verify vertical prompt fragments are actually embedded in instructions."""
        config = self._make_tenant_config()
        analyst = AnalystWorker(config, model=TestModel(), auto_register=False)

        tech = get_vertical("technology")
        healthcare = get_vertical("healthcare")

        # Both vertical fragments should appear in the analyst instructions
        assert tech.system_prompt_fragment in analyst._instructions_text
        assert healthcare.system_prompt_fragment in analyst._instructions_text

    def test_knowledge_full_cycle(self):
        """Index documents, search, and retrieve context."""
        repo = KnowledgeRepository()
        indexer = DocumentIndexer(chunk_size=100, chunk_overlap=20)

        # Index two documents
        ids1 = indexer.index_text(
            "report://q1-analysis",
            "The Q1 revenue growth was driven by digital transformation initiatives. "
            "Cloud migration projects contributed 40% of new revenue.",
            repository=repo,
        )
        ids2 = indexer.index_text(
            "report://market-trends",
            "Healthcare technology spending is projected to increase by 15% in 2026. "
            "AI-driven diagnostics is the fastest growing segment.",
            repository=repo,
        )

        assert len(ids1) > 0
        assert len(ids2) > 0

        # Search
        retriever = KnowledgeRetriever(repo)
        results = retriever.retrieve("cloud migration")
        assert len(results) > 0
        assert any("cloud" in r.content.lower() for r in results)

        # Context string for prompt injection
        context = retriever.get_context_string("healthcare")
        assert context != ""
        assert "healthcare" in context.lower()

    def test_knowledge_source_isolation(self):
        """Two different repos don't share data."""
        repo_a = KnowledgeRepository(scope_id="tenant-a")
        repo_b = KnowledgeRepository(scope_id="tenant-b")
        indexer = DocumentIndexer(chunk_size=500, chunk_overlap=50)

        indexer.index_text(
            "source://alpha",
            "Alpha tenant document about cloud computing",
            repository=repo_a,
        )
        indexer.index_text(
            "source://beta",
            "Beta tenant document about healthcare",
            repository=repo_b,
        )

        # Repo A should find cloud, not healthcare
        results_a = repo_a.search("cloud")
        assert len(results_a) > 0
        results_a_health = repo_a.search("healthcare")
        assert len(results_a_health) == 0

        # Repo B should find healthcare, not cloud
        results_b = repo_b.search("healthcare")
        assert len(results_b) > 0
        results_b_cloud = repo_b.search("cloud")
        assert len(results_b_cloud) == 0

    def test_plan_template_to_dag(self):
        """Build a plan DAG from a template."""
        config = self._make_tenant_config()
        plan = plan_registry.get("customer-segmentation")

        assert plan.name == "customer-segmentation"
        assert len(plan.steps) >= 4
        plan.validate()  # Should not raise

        # Build a DAG (without creating real workers)
        builder = PlanBuilder(plan, config)
        dag = builder.build_dag()

        # Verify DAG structure
        assert len(dag.nodes) == len(plan.steps)
        # Check topological sort works (no cycles)
        order = dag.topological_sort()
        assert len(order) == len(plan.steps)

    def test_all_plan_templates_valid(self):
        """All registered plan templates pass validation and can build DAGs."""
        config = self._make_tenant_config()

        for plan_name in plan_registry.list_plans():
            plan = plan_registry.get(plan_name)
            plan.validate()

            builder = PlanBuilder(plan, config)
            dag = builder.build_dag()
            assert len(dag.nodes) == len(plan.steps)

    def test_worker_registry_isolation(self):
        """Workers registered in worker_registry don't leak between tests."""
        worker_registry.clear()
        config = self._make_tenant_config()

        analyst = AnalystWorker(config, model=TestModel(), auto_register=False)
        worker_registry.register(analyst)

        assert worker_registry.has(analyst.name)
        assert len(worker_registry.list_workers()) == 1

        worker_registry.clear()
        assert len(worker_registry.list_workers()) == 0

    def test_tenant_registry_round_trip(self):
        """Register a tenant config, retrieve it, and verify contents."""
        config = self._make_tenant_config()
        tenant_registry.register(config)

        try:
            assert tenant_registry.has("integration-test")
            retrieved = tenant_registry.get("integration-test")
            assert retrieved.id == "integration-test"
            assert retrieved.name == "Integration Test Tenant"
            assert "technology" in retrieved.verticals
        finally:
            tenant_registry.unregister("integration-test")

    def test_autonomy_levels_integrate_with_workers(self):
        """Autonomy level affects checkpoint behavior."""
        # SEMI_SUPERVISED: checkpoint on phase transitions
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "phase_transition") is True
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "intermediate_step") is False

        # AUTONOMOUS: never checkpoint
        assert should_checkpoint(AutonomyLevel.AUTONOMOUS, "phase_transition") is False

        # MANUAL: always checkpoint
        assert should_checkpoint(AutonomyLevel.MANUAL, "intermediate_step") is True

    def test_global_config_singleton(self):
        """DworkersConfig singleton lifecycle."""
        reset_config()
        cfg = get_config()
        assert isinstance(cfg, DworkersConfig)
        assert cfg.default_autonomy == "semi_supervised"

        # Same instance returned on second call
        cfg2 = get_config()
        assert cfg is cfg2

        reset_config()

    def test_plan_dag_topological_order_respects_dependencies(self):
        """The topological sort of a plan DAG respects step dependencies."""
        plan = plan_registry.get("customer-segmentation")
        config = self._make_tenant_config()
        builder = PlanBuilder(plan, config)
        dag = builder.build_dag()

        order = dag.topological_sort()

        # gather-requirements must come before research-market and analyze-data
        idx = {name: i for i, name in enumerate(order)}
        assert idx["gather-requirements"] < idx["research-market"]
        assert idx["gather-requirements"] < idx["analyze-data"]
        # synthesize-report must come after both research-market and analyze-data
        assert idx["synthesize-report"] > idx["research-market"]
        assert idx["synthesize-report"] > idx["analyze-data"]
        # project-review is last
        assert idx["project-review"] > idx["synthesize-report"]

    def test_all_six_verticals_registered(self):
        """All 6 industry verticals are available."""
        available = list_verticals()
        expected = {"technology", "healthcare", "banking", "legal", "consumer", "gaming"}
        assert expected.issubset(set(available))


class TestServerIntegration:
    """Integration tests using the FastAPI test client."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200

    def test_plans_available(self):
        resp = self.client.get("/api/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert "customer-segmentation" in plans
        assert "market-analysis" in plans
        assert "process-improvement" in plans
        assert "technology-assessment" in plans

    def test_plan_details(self):
        resp = self.client.get("/api/plans/customer-segmentation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "customer-segmentation"
        assert len(data["steps"]) >= 4

    def test_plan_step_structure(self):
        """Each plan step has the expected fields."""
        resp = self.client.get("/api/plans/customer-segmentation")
        assert resp.status_code == 200
        data = resp.json()
        for step in data["steps"]:
            assert "step_id" in step
            assert "name" in step
            assert "worker_role" in step

    def test_knowledge_index_and_search_roundtrip(self):
        """Full round-trip: index via API, search via API."""
        # Index
        resp = self.client.post(
            "/api/knowledge/index",
            json={
                "source": "integration://test-doc",
                "content": "Machine learning models improve customer segmentation accuracy by 35%",
                "tenant_id": "integration-test",
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["chunk_ids"]) > 0

        # Search
        resp = self.client.post(
            "/api/knowledge/search",
            json={
                "query": "machine learning",
                "tenant_id": "integration-test",
                "max_results": 5,
            },
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        assert any("machine learning" in r["content"].lower() for r in results)

    def test_knowledge_search_empty_tenant(self):
        """Searching an empty knowledge store returns zero results."""
        resp = self.client.post(
            "/api/knowledge/search",
            json={
                "query": "nonexistent content",
                "tenant_id": "empty-tenant-12345",
                "max_results": 5,
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 0

    def test_nonexistent_plan_returns_404(self):
        resp = self.client.get("/api/plans/nonexistent-plan")
        assert resp.status_code == 404

    def test_execute_plan_returns_sse(self):
        """Execute plan endpoint now returns SSE streaming response."""
        resp = self.client.post(
            "/api/plans/execute",
            json={
                "plan_name": "customer-segmentation",
                "tenant_id": "integration-test",
                "inputs": {"industry": "technology"},
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_list_workers_endpoint(self):
        """Workers listing endpoint responds."""
        resp = self.client.get("/api/workers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_tenants_endpoint(self):
        """Tenants listing endpoint responds."""
        resp = self.client.get("/api/tenants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
