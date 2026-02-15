"""Project persistence to ~/.dworkers/projects/.

SQLite database (index.db) provides fast listing and FTS search.
JSON files are the source of truth for project data.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

import yaml

from firefly_dworkers_cli.tui.backend.models import (
    CustomAgentDefinition,
    Project,
    ProjectSummary,
)


class ProjectStore:
    """File-backed project storage with SQLite index."""

    def __init__(self, global_dir: Path | None = None) -> None:
        self._global = global_dir or Path.home() / ".dworkers" / "projects"
        self._global.mkdir(parents=True, exist_ok=True)
        self._db_path = self._global / "index.db"
        self._init_db()

    def _init_db(self) -> None:
        with self._db() as conn:
            conn.executescript("""\
                CREATE TABLE IF NOT EXISTS projects (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'active',
                    conversation_count INTEGER NOT NULL DEFAULT 0,
                    participant_count  INTEGER NOT NULL DEFAULT 0
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
                    project_id, name, description
                );
            """)

    @contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- CRUD -----------------------------------------------------------------

    def create_project(self, name: str, description: str = "") -> Project:
        now = datetime.now(UTC)
        proj = Project(
            id=f"proj_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self._save_project(proj)
        self._upsert_row(proj)
        return proj

    def get_project(self, project_id: str) -> Project | None:
        path = self._global / f"{project_id}.json"
        if not path.exists():
            return None
        return Project.model_validate_json(path.read_text())

    def list_projects(self, status: str = "active") -> list[ProjectSummary]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        return [
            ProjectSummary(
                id=r["id"],
                name=r["name"],
                status=r["status"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                conversation_count=r["conversation_count"],
                participant_count=r["participant_count"],
            )
            for r in rows
        ]

    def update_project(self, project: Project) -> None:
        project.updated_at = datetime.now(UTC)
        self._save_project(project)
        self._upsert_row(project)

    def archive_project(self, project_id: str) -> None:
        proj = self.get_project(project_id)
        if proj:
            proj.status = "archived"
            self.update_project(proj)

    # -- Linking --------------------------------------------------------------

    def link_conversation(self, project_id: str, conv_id: str) -> None:
        proj = self.get_project(project_id)
        if proj and conv_id not in proj.conversation_ids:
            proj.conversation_ids.append(conv_id)
            self.update_project(proj)

    def unlink_conversation(self, project_id: str, conv_id: str) -> None:
        proj = self.get_project(project_id)
        if proj and conv_id in proj.conversation_ids:
            proj.conversation_ids.remove(conv_id)
            self.update_project(proj)

    # -- Search ---------------------------------------------------------------

    def search_projects(self, query: str) -> list[ProjectSummary]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT project_id FROM projects_fts WHERE projects_fts MATCH ? LIMIT 20",
                (query,),
            ).fetchall()
        ids = [r["project_id"] for r in rows]
        if not ids:
            return []
        # Return summaries for matching projects regardless of status
        with self._db() as conn:
            placeholders = ",".join("?" for _ in ids)
            result_rows = conn.execute(
                f"SELECT * FROM projects WHERE id IN ({placeholders}) ORDER BY updated_at DESC",
                ids,
            ).fetchall()
        return [
            ProjectSummary(
                id=r["id"],
                name=r["name"],
                status=r["status"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                conversation_count=r["conversation_count"],
                participant_count=r["participant_count"],
            )
            for r in result_rows
        ]

    # -- Local binding --------------------------------------------------------

    def bind_local(self, project_id: str, local_dir: Path) -> None:
        dworkers_dir = local_dir / ".dworkers"
        dworkers_dir.mkdir(parents=True, exist_ok=True)
        (dworkers_dir / "project.json").write_text(
            json.dumps({"project_id": project_id}, indent=2)
        )

    def detect_local_project(self, cwd: Path) -> str | None:
        current = cwd
        for _ in range(10):  # Walk up max 10 levels
            candidate = current / ".dworkers" / "project.json"
            if candidate.exists():
                data = json.loads(candidate.read_text())
                return data.get("project_id")
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    # -- Memory persistence ---------------------------------------------------

    def save_memory(self, project_id: str, facts: dict[str, Any]) -> None:
        proj_dir = self._global / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "memory.json").write_text(
            json.dumps(facts, indent=2, default=str)
        )

    def load_memory(self, project_id: str) -> dict[str, Any]:
        path = self._global / project_id / "memory.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    # -- Agent persistence ----------------------------------------------------

    def save_agent(self, project_id: str, agent: CustomAgentDefinition) -> None:
        agents_dir = self._global / project_id / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        safe_name = agent.id.replace(" ", "_").lower()
        path = agents_dir / f"{safe_name}.yaml"
        path.write_text(yaml.dump(agent.model_dump(mode="json"), default_flow_style=False))

    def list_agents(self, project_id: str) -> list[CustomAgentDefinition]:
        agents_dir = self._global / project_id / "agents"
        if not agents_dir.exists():
            return []
        agents = []
        for path in agents_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            agents.append(CustomAgentDefinition.model_validate(data))
        return agents

    def get_agent(self, project_id: str, agent_id: str) -> CustomAgentDefinition | None:
        for agent in self.list_agents(project_id):
            if agent.id == agent_id:
                return agent
        return None

    def remove_agent(self, project_id: str, agent_id: str) -> bool:
        agents_dir = self._global / project_id / "agents"
        if not agents_dir.exists():
            return False
        safe_name = agent_id.replace(" ", "_").lower()
        path = agents_dir / f"{safe_name}.yaml"
        if path.exists():
            path.unlink()
            return True
        return False

    # -- Private helpers ------------------------------------------------------

    def _save_project(self, proj: Project) -> None:
        path = self._global / f"{proj.id}.json"
        path.write_text(proj.model_dump_json(indent=2))

    def _upsert_row(self, proj: Project) -> None:
        with self._db() as conn:
            conn.execute(
                """\
                INSERT INTO projects
                    (id, name, description, created_at, updated_at, status,
                     conversation_count, participant_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    updated_at = excluded.updated_at,
                    status = excluded.status,
                    conversation_count = excluded.conversation_count,
                    participant_count = excluded.participant_count
                """,
                (
                    proj.id, proj.name, proj.description,
                    proj.created_at.isoformat(), proj.updated_at.isoformat(),
                    proj.status, len(proj.conversation_ids), len(proj.participants),
                ),
            )
            # Upsert FTS
            conn.execute("DELETE FROM projects_fts WHERE project_id = ?", (proj.id,))
            conn.execute(
                "INSERT INTO projects_fts (project_id, name, description) VALUES (?, ?, ?)",
                (proj.id, proj.name, proj.description),
            )
