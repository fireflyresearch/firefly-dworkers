"""ProcessMappingTool — generate structured process maps from descriptions."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol, ParameterSpec

from firefly_dworkers.tools.consulting.base import ConsultingTool
from firefly_dworkers.tools.registry import tool_registry

_DEFAULT_ACTOR_VERBS: tuple[str, ...] = (
    "will", "does", "performs", "sends", "receives",
    "reviews", "creates", "submits", "approves",
)

_DEFAULT_STEP_SPLIT_PATTERN = r"[\n.]"


@tool_registry.register("process_mapping", category="consulting")
class ProcessMappingTool(ConsultingTool):
    """Take process descriptions and generate structured process maps.

    Extracts steps, actors, inputs, and outputs from textual process
    descriptions.  This tool structures and organises information — it does not
    call external APIs.

    Configuration parameters:

    * ``actor_verbs`` -- Verb stems used to detect actors in step text.
    * ``step_split_pattern`` -- Regex pattern for splitting text into steps.
    * ``default_process_name`` -- Fallback name when not specified at call time.
    """

    def __init__(
        self,
        *,
        actor_verbs: Sequence[str] | None = None,
        step_split_pattern: str = _DEFAULT_STEP_SPLIT_PATTERN,
        default_process_name: str = "Unnamed Process",
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(
            "process_mapping",
            description="Generate structured process maps (steps, actors, inputs, outputs) from descriptions",
            tags=["consulting", "process", "mapping"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="description",
                    type_annotation="str",
                    description="Textual description of the process",
                    required=True,
                ),
                ParameterSpec(
                    name="process_name",
                    type_annotation="str",
                    description="Name of the process",
                    required=False,
                    default=default_process_name,
                ),
            ],
        )
        self._actor_verbs = tuple(actor_verbs) if actor_verbs else _DEFAULT_ACTOR_VERBS
        self._step_split_pattern = step_split_pattern
        self._default_process_name = default_process_name

    def _build_actor_regex(self) -> re.Pattern[str]:
        """Build compiled regex for actor detection from configured verbs."""
        verbs_alt = "|".join(re.escape(v) for v in self._actor_verbs)
        return re.compile(
            rf"(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:{verbs_alt})",
            re.IGNORECASE,
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        description = kwargs["description"]
        process_name = kwargs.get("process_name", self._default_process_name)

        # Parse lines/sentences as steps
        raw_steps = [s.strip() for s in re.split(self._step_split_pattern, description) if s.strip()]

        steps: list[dict[str, Any]] = []
        actors: set[str] = set()
        actor_re = self._build_actor_regex()

        for i, step_text in enumerate(raw_steps, 1):
            actor_match = actor_re.match(step_text)
            actor = actor_match.group(1) if actor_match else ""
            if actor:
                actors.add(actor)

            steps.append({
                "number": i,
                "description": step_text,
                "actor": actor,
                "inputs": [],
                "outputs": [],
            })

        return {
            "process_name": process_name,
            "steps": steps,
            "step_count": len(steps),
            "actors": sorted(actors),
        }
