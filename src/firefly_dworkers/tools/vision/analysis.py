"""VisionAnalysisTool -- analyse images with vision-capable language models."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.agents.base import FireflyAgent
from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from fireflyframework_genai.types import ImageUrl

from firefly_dworkers.tools.registry import tool_registry

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"})


@tool_registry.register("vision_analysis", category="vision")
class VisionAnalysisTool(BaseTool):
    """Analyse images using a vision-capable language model."""

    def __init__(
        self,
        *,
        vision_model: str = "",
        timeout: float = 120.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        params = [
            ParameterSpec(
                name="action",
                type_annotation="str",
                description="Action: 'analyze', 'compare', or 'render_and_analyze'.",
                required=True,
            ),
            ParameterSpec(
                name="image_path",
                type_annotation="str",
                description="Path or URL to the image (required for 'analyze').",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="prompt",
                type_annotation="str",
                description="Analysis prompt / question about the image(s).",
                required=True,
            ),
            ParameterSpec(
                name="image_a",
                type_annotation="str",
                description="First image path/URL (required for 'compare').",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="image_b",
                type_annotation="str",
                description="Second image path/URL (required for 'compare').",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="document_path",
                type_annotation="str",
                description="Path to a document file (required for 'render_and_analyze').",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="page",
                type_annotation="int",
                description="Page number for render_and_analyze (0-indexed).",
                required=False,
                default=0,
            ),
        ]
        super().__init__(
            "vision_analysis",
            description="Analyse images using a vision-capable language model.",
            tags=["vision", "image", "analysis", "multimodal"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )
        self._vision_model = vision_model
        self._agent: FireflyAgent | None = None

    # -- Lazy agent initialisation -------------------------------------------

    def _get_agent(self) -> FireflyAgent:
        if self._agent is None:
            self._agent = FireflyAgent(
                name="vision_analyzer",
                model=self._vision_model or None,
                instructions=(
                    "You are a visual analysis expert. Analyse images thoroughly "
                    "and provide detailed, structured observations."
                ),
                output_type=str,
                auto_register=False,
            )
        return self._agent

    # -- Execution dispatch --------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs.get("action", "")

        if action == "analyze":
            return await self._analyze(kwargs)
        if action == "compare":
            return await self._compare(kwargs)
        if action == "render_and_analyze":
            return await self._render_and_analyze(kwargs)

        raise ValueError(f"Unknown action: {action!r}. Use 'analyze', 'compare', or 'render_and_analyze'.")

    # -- Actions -------------------------------------------------------------

    async def _analyze(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        image_path: str = kwargs.get("image_path", "")
        prompt: str = kwargs["prompt"]

        if not image_path:
            raise ValueError("'image_path' is required for the 'analyze' action.")

        image_url = self._normalize_image_path(image_path)
        result = await self._get_agent().run([prompt, ImageUrl(url=image_url)])
        return {"analysis": result.output, "image_path": image_path}

    async def _compare(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        image_a: str = kwargs.get("image_a", "")
        image_b: str = kwargs.get("image_b", "")
        prompt: str = kwargs["prompt"]

        if not image_a or not image_b:
            raise ValueError("'image_a' and 'image_b' are required for the 'compare' action.")

        url_a = self._normalize_image_path(image_a)
        url_b = self._normalize_image_path(image_b)
        result = await self._get_agent().run([prompt, ImageUrl(url=url_a), ImageUrl(url=url_b)])
        return {"comparison": result.output, "image_a": image_a, "image_b": image_b}

    async def _render_and_analyze(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        document_path: str = kwargs.get("document_path", "")
        if not document_path:
            raise ValueError("'document_path' is required for the 'render_and_analyze' action.")

        ext = os.path.splitext(document_path)[1].lower()
        if ext in _IMAGE_EXTENSIONS:
            # Already an image -- delegate to analyze
            return await self._analyze({"image_path": document_path, "prompt": kwargs["prompt"]})

        raise ValueError(
            f"render_and_analyze requires a pre-rendered image path (got {ext!r}). "
            "Use the 'analyze' action with a screenshot instead."
        )

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _normalize_image_path(path: str) -> str:
        if path.startswith(("http://", "https://", "file://", "data:")):
            return path
        return f"file://{os.path.abspath(path)}"
