"""Tests for ProjectStore with SQLite index."""
from __future__ import annotations

from pathlib import Path

import pytest


class TestProjectStore:
    def test_store_creates_db(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        assert (tmp_path / "projects" / "index.db").exists()

    def test_create_project(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("Q4 Analysis", description="Market analysis")
        assert proj.name == "Q4 Analysis"
        assert proj.id.startswith("proj_")
        assert proj.status == "active"

    def test_list_projects(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        store.create_project("Project A")
        store.create_project("Project B")
        projects = store.list_projects()
        assert len(projects) == 2

    def test_get_project(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        created = store.create_project("Test")
        fetched = store.get_project(created.id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_archive_project(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("To Archive")
        store.archive_project(proj.id)
        fetched = store.get_project(proj.id)
        assert fetched.status == "archived"

    def test_link_conversation(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("Test")
        store.link_conversation(proj.id, "conv_abc123")
        fetched = store.get_project(proj.id)
        assert "conv_abc123" in fetched.conversation_ids

    def test_search_projects(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        store.create_project("EV Market Analysis", description="Electric vehicle research")
        results = store.search_projects("electric")
        assert len(results) >= 1

    def test_detect_local_project(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        import json
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("Local Project")
        # Create .dworkers/project.json in a fake working directory
        local_dir = tmp_path / "my-project" / ".dworkers"
        local_dir.mkdir(parents=True)
        (local_dir / "project.json").write_text(json.dumps({"project_id": proj.id}))
        detected = store.detect_local_project(tmp_path / "my-project")
        assert detected == proj.id

    def test_detect_local_project_not_found(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        assert store.detect_local_project(tmp_path / "empty") is None


class TestProjectMemoryPersistence:
    def test_save_and_load_memory(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("Test")
        store.save_memory(proj.id, {"market_size": "$4.2B", "growth": "12%"})
        loaded = store.load_memory(proj.id)
        assert loaded["market_size"] == "$4.2B"

    def test_load_memory_empty(self, tmp_path: Path):
        from firefly_dworkers_cli.tui.backend.project_store import ProjectStore
        store = ProjectStore(global_dir=tmp_path / "projects")
        proj = store.create_project("Test")
        assert store.load_memory(proj.id) == {}
