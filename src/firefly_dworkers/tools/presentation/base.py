"""Abstract port for presentation creation and analysis."""

from __future__ import annotations

import os
from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.tools.presentation.models import (
    PresentationData,
    SlideOperation,
    SlideSpec,
)


class PresentationTool(BaseTool):
    """Abstract port for presentation tools (PowerPoint, Google Slides)."""

    def __init__(
        self,
        name: str = "presentation",
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
                description="File path or URL of the presentation.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="template",
                type_annotation="str",
                description="Template file path for creating presentations.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="slides",
                type_annotation="list",
                description="List of SlideSpec dicts for creating slides.",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="operations",
                type_annotation="list",
                description="List of SlideOperation dicts for modifying.",
                required=False,
                default=[],
            ),
            *extra_parameters,
        ]
        super().__init__(
            name,
            description=description or "Create, read, and modify presentations.",
            tags=["presentation", "document"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )
        self._last_artifact: bytes | None = None

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action = kwargs.get("action", "read")
        if action == "read":
            source = kwargs["source"]
            self._last_artifact = None
            result = await self._read_presentation(source)
            return result.model_dump()
        elif action == "create":
            template = kwargs.get("template", "")
            slides_raw = kwargs.get("slides", [])
            slides = [SlideSpec.model_validate(s) for s in slides_raw]
            data = await self._create_presentation(template, slides)
            self._last_artifact = data
            return {"bytes_length": len(data), "success": True}
        elif action == "modify":
            source = kwargs["source"]
            ops_raw = kwargs.get("operations", [])
            ops = [SlideOperation.model_validate(o) for o in ops_raw]
            data = await self._modify_presentation(source, ops)
            self._last_artifact = data
            return {"bytes_length": len(data), "success": True}
        else:
            raise ValueError(f"Unknown action: {action}")

    @property
    def artifact_bytes(self) -> bytes | None:
        """Bytes from the last create/modify operation, or ``None``."""
        return self._last_artifact

    async def create(self, *, template: str = "", slides: list[SlideSpec] | None = None) -> bytes:
        """Create a presentation and return the raw file bytes."""
        return await self._create_presentation(template, slides or [])

    async def create_and_save(
        self, output_path: str, *, template: str = "", slides: list[SlideSpec] | None = None
    ) -> str:
        """Create a presentation and save it to *output_path*. Returns the absolute path."""
        data = await self.create(template=template, slides=slides)
        with open(output_path, "wb") as f:
            f.write(data)
        return os.path.abspath(output_path)

    async def modify(self, source: str, *, operations: list[SlideOperation] | None = None) -> bytes:
        """Modify a presentation and return the raw file bytes."""
        return await self._modify_presentation(source, operations or [])

    async def modify_and_save(
        self, source: str, output_path: str, *, operations: list[SlideOperation] | None = None
    ) -> str:
        """Modify a presentation and save it to *output_path*. Returns the absolute path."""
        data = await self.modify(source, operations=operations)
        with open(output_path, "wb") as f:
            f.write(data)
        return os.path.abspath(output_path)

    @abstractmethod
    async def _read_presentation(self, source: str) -> PresentationData: ...

    @abstractmethod
    async def _create_presentation(self, template: str, slides: list[SlideSpec]) -> bytes: ...

    @abstractmethod
    async def _modify_presentation(self, source: str, operations: list[SlideOperation]) -> bytes: ...
