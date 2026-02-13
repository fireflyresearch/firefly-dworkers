"""ProcessMappingTool — generate structured process maps from descriptions."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class ProcessMappingTool(BaseTool):
    """Take process descriptions and generate structured process maps.

    Extracts steps, actors, inputs, and outputs from textual process
    descriptions.  This tool structures and organises information — it does not
    call external APIs.
    """

    def __init__(self, *, guards: Sequence[GuardProtocol] = ()):
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
                    default="Unnamed Process",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        description = kwargs["description"]
        process_name = kwargs.get("process_name", "Unnamed Process")

        # Parse lines/sentences as steps
        raw_steps = [s.strip() for s in re.split(r"[\n.]", description) if s.strip()]

        steps: list[dict[str, Any]] = []
        actors: set[str] = set()

        for i, step_text in enumerate(raw_steps, 1):
            # Try to extract actor from patterns like "The <actor> does X" or "<Actor> performs Y"
            actor_match = re.match(r"(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:will|does|performs|sends|receives|reviews|creates|submits|approves)", step_text, re.IGNORECASE)
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
