"""Tests for the dworkers application server."""

from __future__ import annotations

from fastapi.testclient import TestClient

from firefly_dworkers_server.app import create_dworkers_app


class TestApp:
    """Test the dworkers app factory and health endpoint."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_health(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200

    def test_health_ready(self):
        resp = self.client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_health_live(self):
        resp = self.client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"


class TestWorkersRouter:
    """Test the /api/workers endpoints."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_list_workers(self):
        resp = self.client.get("/api/workers")
        assert resp.status_code == 200
        workers = resp.json()
        assert isinstance(workers, list)

    def test_run_worker(self):
        resp = self.client.post(
            "/api/workers/run",
            json={
                "worker_role": "analyst",
                "prompt": "Analyze market trends",
                "tenant_id": "default",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "worker_name" in data
        assert "role" in data
        assert data["role"] == "analyst"
        assert "output" in data


class TestPlansRouter:
    """Test the /api/plans endpoints."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_list_plans(self):
        resp = self.client.get("/api/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert isinstance(plans, list)
        assert "customer-segmentation" in plans

    def test_get_plan(self):
        resp = self.client.get("/api/plans/customer-segmentation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "customer-segmentation"
        assert "description" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    def test_get_plan_not_found(self):
        resp = self.client.get("/api/plans/nonexistent-plan")
        assert resp.status_code == 404

    def test_execute_plan(self):
        resp = self.client.post(
            "/api/plans/execute",
            json={
                "plan_name": "customer-segmentation",
                "tenant_id": "default",
                "inputs": {},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_name"] == "customer-segmentation"
        assert "success" in data


class TestTenantsRouter:
    """Test the /api/tenants endpoints."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_list_tenants(self):
        resp = self.client.get("/api/tenants")
        assert resp.status_code == 200
        tenants = resp.json()
        assert isinstance(tenants, list)

    def test_get_tenant_not_found(self):
        resp = self.client.get("/api/tenants/nonexistent-tenant")
        assert resp.status_code == 404


class TestKnowledgeRouter:
    """Test the /api/knowledge endpoints."""

    def setup_method(self):
        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_index_document(self):
        resp = self.client.post(
            "/api/knowledge/index",
            json={
                "source": "test://doc1",
                "content": "Artificial intelligence is transforming consulting",
                "tenant_id": "default",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["chunk_ids"]) > 0
        assert data["source"] == "test://doc1"

    def test_search_knowledge(self):
        # First index a document
        self.client.post(
            "/api/knowledge/index",
            json={
                "source": "test://doc-search",
                "content": "Artificial intelligence is transforming consulting",
                "tenant_id": "default",
            },
        )

        # Then search for it
        resp = self.client.post(
            "/api/knowledge/search",
            json={
                "query": "artificial intelligence",
                "tenant_id": "default",
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert "query" in results
        assert results["query"] == "artificial intelligence"
        assert "results" in results
        assert len(results["results"]) > 0

    def test_index_and_search_knowledge(self):
        """Full round-trip: index a document and search for it."""
        # Index a document
        resp = self.client.post(
            "/api/knowledge/index",
            json={
                "source": "test://roundtrip",
                "content": "Digital transformation strategies for enterprise companies",
                "tenant_id": "test-tenant",
                "metadata": {"category": "strategy"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["chunk_ids"]) > 0

        # Search for it
        resp = self.client.post(
            "/api/knowledge/search",
            json={
                "query": "digital transformation",
                "tenant_id": "test-tenant",
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results["results"]) > 0
        first_result = results["results"][0]
        assert "chunk_id" in first_result
        assert "source" in first_result
        assert "content" in first_result
        assert first_result["source"] == "test://roundtrip"


class TestAppFactory:
    """Test the app factory itself."""

    def test_create_dworkers_app_returns_fastapi_instance(self):
        from fastapi import FastAPI

        app = create_dworkers_app()
        assert isinstance(app, FastAPI)

    def test_create_dworkers_app_custom_title(self):
        app = create_dworkers_app(title="Custom Title", version="1.0.0")
        assert app.title == "Custom Title"
        assert app.version == "1.0.0"

    def test_package_exports(self):
        import firefly_dworkers_server

        assert hasattr(firefly_dworkers_server, "create_dworkers_app")
