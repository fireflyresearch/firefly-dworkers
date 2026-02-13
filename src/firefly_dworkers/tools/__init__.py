"""Tools layer -- abstract bases and concrete providers for dworkers.

This package defines standardized tool interfaces that follow the
fireflyframework-genai BaseTool pattern. Each sub-package provides abstract
bases for a connector category (web, storage, communication, project) that
concrete providers implement.

Importing this package triggers self-registration of all concrete tool
classes in the :data:`tool_registry`.
"""

from __future__ import annotations

# Import concrete tool modules to trigger @tool_registry.register decorators.
import firefly_dworkers.tools.communication.email  # noqa: F401
import firefly_dworkers.tools.communication.slack  # noqa: F401
import firefly_dworkers.tools.communication.teams  # noqa: F401
import firefly_dworkers.tools.consulting.documentation  # noqa: F401
import firefly_dworkers.tools.consulting.gap_analysis  # noqa: F401
import firefly_dworkers.tools.consulting.process_mapping  # noqa: F401
import firefly_dworkers.tools.consulting.report_generation  # noqa: F401
import firefly_dworkers.tools.consulting.requirement_gathering  # noqa: F401
import firefly_dworkers.tools.data.api_client  # noqa: F401
import firefly_dworkers.tools.data.csv_excel  # noqa: F401
import firefly_dworkers.tools.data.sql  # noqa: F401
import firefly_dworkers.tools.project.asana  # noqa: F401
import firefly_dworkers.tools.project.jira  # noqa: F401
import firefly_dworkers.tools.storage.confluence  # noqa: F401
import firefly_dworkers.tools.storage.google_drive  # noqa: F401
import firefly_dworkers.tools.storage.s3  # noqa: F401
import firefly_dworkers.tools.storage.sharepoint  # noqa: F401
import firefly_dworkers.tools.presentation.powerpoint  # noqa: F401
import firefly_dworkers.tools.web.browser  # noqa: F401
import firefly_dworkers.tools.web.flybrowser  # noqa: F401
import firefly_dworkers.tools.web.rss  # noqa: F401
import firefly_dworkers.tools.web.serpapi  # noqa: F401
import firefly_dworkers.tools.web.tavily  # noqa: F401
from firefly_dworkers.tools.registry import ToolRegistry, tool_registry

__all__ = [
    "ToolRegistry",
    "tool_registry",
]
