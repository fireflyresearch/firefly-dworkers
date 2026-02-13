"""GapAnalysisTool — identify gaps between current and desired state."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol, ParameterSpec

from firefly_dworkers.tools.consulting.base import ConsultingTool
from firefly_dworkers.tools.registry import tool_registry


@tool_registry.register("gap_analysis", category="consulting")
class GapAnalysisTool(ConsultingTool):
    """Take current state and desired state descriptions and identify gaps.

    Produces a structured list of gaps with severity and recommendations.
    This tool structures and organises information — it does not call external
    APIs.

    Configuration parameters:

    * ``default_severity`` -- Severity label assigned to detected gaps.
    * ``default_domain`` -- Fallback domain label when not specified at call
      time.
    * ``recommendation_template`` -- Python format string for gap
      recommendations (receives ``{item}``).
    * ``item_split_pattern`` -- Regex pattern used to split state descriptions
      into individual items.
    * ``case_sensitive`` -- If ``True``, gap comparison is case-sensitive.
    """

    def __init__(
        self,
        *,
        default_severity: str = "medium",
        default_domain: str = "general",
        recommendation_template: str = "Address gap: {item}",
        item_split_pattern: str = r"[\n.]",
        case_sensitive: bool = False,
        guards: Sequence[GuardProtocol] = (),
    ):
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
                    default=default_domain,
                ),
            ],
        )
        self._default_severity = default_severity
        self._default_domain = default_domain
        self._recommendation_template = recommendation_template
        self._split_pattern = item_split_pattern
        self._case_sensitive = case_sensitive

    def _extract_items(self, text: str) -> set[str]:
        """Split text into a set of trimmed items."""
        items = {s.strip() for s in re.split(self._split_pattern, text) if s.strip()}
        if not self._case_sensitive:
            items = {s.lower() for s in items}
        return items

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        current_state = kwargs["current_state"]
        desired_state = kwargs["desired_state"]
        domain = kwargs.get("domain", self._default_domain)

        current_items = self._extract_items(current_state)
        desired_items = self._extract_items(desired_state)

        # Items in desired but not in current are gaps
        gap_items = desired_items - current_items
        # Items in current but not in desired may be surplus
        surplus_items = current_items - desired_items
        # Items in both are covered
        covered_items = current_items & desired_items

        gaps = [
            {
                "description": item,
                "severity": self._default_severity,
                "recommendation": self._recommendation_template.format(item=item),
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
