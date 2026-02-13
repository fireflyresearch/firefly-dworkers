"""GapAnalysisTool — identify gaps between current and desired state."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class GapAnalysisTool(BaseTool):
    """Take current state and desired state descriptions and identify gaps.

    Produces a structured list of gaps with severity and recommendations.
    This tool structures and organises information — it does not call external
    APIs.
    """

    def __init__(self, *, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "gap_analysis",
            description="Identify gaps between current state and desired state",
            tags=["consulting", "analysis", "gap"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="current_state",
                    type_annotation="str",
                    description="Description of the current state",
                    required=True,
                ),
                ParameterSpec(
                    name="desired_state",
                    type_annotation="str",
                    description="Description of the desired/target state",
                    required=True,
                ),
                ParameterSpec(
                    name="domain",
                    type_annotation="str",
                    description="Domain or area being analysed",
                    required=False,
                    default="general",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        current_state = kwargs["current_state"]
        desired_state = kwargs["desired_state"]
        domain = kwargs.get("domain", "general")

        # Extract key items from each state description
        current_items = {s.strip().lower() for s in current_state.replace(".", "\n").split("\n") if s.strip()}
        desired_items = {s.strip().lower() for s in desired_state.replace(".", "\n").split("\n") if s.strip()}

        # Items in desired but not in current are gaps
        gap_items = desired_items - current_items
        # Items in current but not in desired may be surplus
        surplus_items = current_items - desired_items
        # Items in both are covered
        covered_items = current_items & desired_items

        gaps = [
            {
                "description": item,
                "severity": "medium",
                "recommendation": f"Address gap: {item}",
            }
            for item in sorted(gap_items)
        ]

        return {
            "domain": domain,
            "gaps": gaps,
            "gap_count": len(gaps),
            "covered_count": len(covered_items),
            "surplus_count": len(surplus_items),
            "current_items": sorted(current_items),
            "desired_items": sorted(desired_items),
        }
