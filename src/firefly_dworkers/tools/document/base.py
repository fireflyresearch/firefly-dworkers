"""Abstract port for document creation and analysis."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.tools.document.models import (
    DocumentData,
    DocumentOperation,
    SectionSpec,
)


class DocumentTool(BaseTool):
    """Abstract port for document tools (Word, Google Docs)."""

    def __init__(
        self,
        name: str = "document",
        *,
        description: str = "",
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
        extra_parameters: Sequence[ParameterSpec] = (),
    ) -> None:
        params = [
            ParameterSpec(
                name="action",
                type_annotation="str",
                description="Action: read, create, or modify.",
                required=True,
            ),
            ParameterSpec(
                name="source",
                type_annotation="str",
                description="File path or URL of the document.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="title",
                type_annotation="str",
                description="Title for creating a new document.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="sections",
                type_annotation="list",
                description="List of SectionSpec dicts for creating documents.",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="operations",
                type_annotation="list",
                description="List of DocumentOperation dicts for modifying.",
                required=False,
                default=[],
            ),
            *extra_parameters,
        ]
        super().__init__(
            name,
            description=description or "Create, read, and modify documents.",
            tags=["document"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action = kwargs.get("action", "read")
        if action == "read":
            source = kwargs["source"]
            result = await self._read_document(source)
            return result.model_dump()
        elif action == "create":
            title = kwargs.get("title", "")
            sections_raw = kwargs.get("sections", [])
            sections = [SectionSpec.model_validate(s) for s in sections_raw]
            data = await self._create_document(title, sections)
            return {"bytes_length": len(data), "success": True}
        elif action == "modify":
            source = kwargs["source"]
            ops_raw = kwargs.get("operations", [])
            ops = [DocumentOperation.model_validate(o) for o in ops_raw]
            data = await self._modify_document(source, ops)
            return {"bytes_length": len(data), "success": True}
        else:
            raise ValueError(f"Unknown action: {action}")

    @abstractmethod
    async def _read_document(self, source: str) -> DocumentData: ...

    @abstractmethod
    async def _create_document(self, title: str, sections: list[SectionSpec]) -> bytes: ...

    @abstractmethod
    async def _modify_document(self, source: str, operations: list[DocumentOperation]) -> bytes: ...
