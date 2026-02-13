"""Storage tools — abstract base for document storage providers."""

from __future__ import annotations

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool

__all__ = [
    "DocumentResult",
    "DocumentStorageTool",
]
