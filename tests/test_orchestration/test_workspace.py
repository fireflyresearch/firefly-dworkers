"""Tests for workspace snapshot and restore."""
from __future__ import annotations
import json
from pathlib import Path


class TestWorkspaceSnapshot:
    def test_snapshot_returns_dict(self):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        ws = ProjectWorkspace("test_project")
        ws.set_fact("key1", "value1")
        snapshot = ws.snapshot()
        assert isinstance(snapshot, dict)
        assert snapshot["project_id"] == "test_project"
        assert snapshot["facts"]["key1"] == "value1"

    def test_restore_from_snapshot(self):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        ws1 = ProjectWorkspace("test_project")
        ws1.set_fact("result", "analysis complete")
        snapshot = ws1.snapshot()
        ws2 = ProjectWorkspace("test_project_2")
        ws2.restore(snapshot)
        assert ws2.get_fact("result") == "analysis complete"

    def test_save_to_file(self, tmp_path: Path):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        ws = ProjectWorkspace("test_project")
        ws.set_fact("data", "important")
        path = tmp_path / "workspace.json"
        ws.save_to_file(path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["facts"]["data"] == "important"

    def test_load_from_file(self, tmp_path: Path):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        path = tmp_path / "workspace.json"
        path.write_text(json.dumps({"project_id": "test_project", "facts": {"loaded": "yes"}}))
        ws = ProjectWorkspace("test_project")
        ws.load_from_file(path)
        assert ws.get_fact("loaded") == "yes"


class TestWorkspaceReuse:
    def test_workspace_accepts_existing_facts(self):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        ws = ProjectWorkspace("test_reuse")
        ws.restore({"facts": {"prior_result": "42%"}})
        assert ws.get_fact("prior_result") == "42%"

    def test_workspace_preserves_facts_across_operations(self):
        from firefly_dworkers.orchestration.workspace import ProjectWorkspace
        ws = ProjectWorkspace("test_persist")
        ws.set_fact("finding_1", "Revenue grew 12%")
        ws.set_fact("finding_2", "Market expanding")
        snapshot = ws.snapshot()
        ws2 = ProjectWorkspace("test_persist_2")
        ws2.restore(snapshot)
        assert ws2.get_fact("finding_1") == "Revenue grew 12%"
        assert ws2.get_fact("finding_2") == "Market expanding"
