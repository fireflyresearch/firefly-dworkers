"""Application factory for the dworkers platform server.

Extends the framework's :func:`create_genai_app` with dworkers-specific
API routers for workers, plans, projects, tenants, knowledge, and
observability (tracing + usage metrics).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def _configure_observability(app: FastAPI) -> None:
    """Wire HTTP-level observability middleware (W3C Trace Context)."""
    try:
        from fireflyframework_genai.exposure.rest.middleware import (
            add_trace_propagation_middleware,
        )

        add_trace_propagation_middleware(app)
    except ImportError:
        pass  # Framework REST middleware not available


def create_dworkers_app(
    *,
    title: str = "Firefly Dworkers",
    version: str = "0.1.0",
) -> FastAPI:
    """Create the dworkers FastAPI application.

    Extends the framework's base app with dworkers-specific routes
    for workers, plans, tenants, knowledge management, and observability.

    Parameters:
        title: Application title for OpenAPI docs.
        version: Application version string.

    Returns:
        A configured :class:`~fastapi.FastAPI` instance.
    """
    from fireflyframework_genai.exposure.rest.app import create_genai_app

    app = create_genai_app(title=title, version=version)

    # Wire HTTP-level observability (trace propagation)
    _configure_observability(app)

    # Include dworkers-specific routers
    from firefly_dworkers_server.api.knowledge import router as knowledge_router
    from firefly_dworkers_server.api.observability import (
        router as observability_router,
    )
    from firefly_dworkers_server.api.plans import router as plans_router
    from firefly_dworkers_server.api.projects import router as projects_router
    from firefly_dworkers_server.api.tenants import router as tenants_router
    from firefly_dworkers_server.api.workers import router as workers_router

    app.include_router(workers_router, prefix="/api/workers", tags=["workers"])
    app.include_router(plans_router, prefix="/api/plans", tags=["plans"])
    app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
    app.include_router(tenants_router, prefix="/api/tenants", tags=["tenants"])
    app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])
    app.include_router(
        observability_router,
        prefix="/api/observability",
        tags=["observability"],
    )

    return app
