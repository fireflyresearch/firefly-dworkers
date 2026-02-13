"""RequirementGatheringTool — extract structured requirements from text."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class RequirementGatheringTool(BaseTool):
    """Take interview notes or documents and extract structured requirements.

    Categorises requirements into functional, non-functional, and constraints.
    This tool structures and organises information — it does not call external
    APIs.
    """

    def __init__(self, *, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "requirement_gathering",
            description="Extract structured requirements (functional, non-functional, constraints) from text",
            tags=["consulting", "requirements", "analysis"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="notes",
                    type_annotation="str",
                    description="Interview notes or document text to analyse",
                    required=True,
                ),
                ParameterSpec(
                    name="project_name",
                    type_annotation="str",
                    description="Project name for context",
                    required=False,
                    default="Unnamed Project",
                ),
                ParameterSpec(
                    name="categories",
                    type_annotation="str",
                    description="Comma-separated requirement categories to look for",
                    required=False,
                    default="functional,non-functional,constraints",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        notes = kwargs["notes"]
        project_name = kwargs.get("project_name", "Unnamed Project")
        categories_raw = kwargs.get("categories", "functional,non-functional,constraints")
        categories = [c.strip() for c in categories_raw.split(",")]

        # Split notes into sentences for classification
        sentences = [s.strip() for s in re.split(r"[.\n]", notes) if s.strip()]

        requirements: dict[str, list[str]] = {cat: [] for cat in categories}

        for sentence in sentences:
            lower = sentence.lower()
            if any(kw in lower for kw in ("must", "shall", "should", "need", "require", "want")):
                if any(kw in lower for kw in ("performance", "security", "scalab", "reliab", "availab", "uptime")):
                    target = "non-functional" if "non-functional" in categories else categories[0]
                elif any(kw in lower for kw in ("limit", "constraint", "budget", "deadline", "restrict", "cannot")):
                    target = "constraints" if "constraints" in categories else categories[-1]
                else:
                    target = "functional" if "functional" in categories else categories[0]
                requirements[target].append(sentence)
            elif any(kw in lower for kw in ("limit", "constraint", "budget", "cannot", "no more than")):
                target = "constraints" if "constraints" in categories else categories[-1]
                requirements[target].append(sentence)

        total = sum(len(v) for v in requirements.values())

        return {
            "project": project_name,
            "requirements": requirements,
            "total_count": total,
            "source_sentences": len(sentences),
            "categories": categories,
        }
