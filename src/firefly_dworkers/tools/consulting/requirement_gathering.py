"""RequirementGatheringTool — extract structured requirements from text."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol, ParameterSpec

from firefly_dworkers.tools.consulting.base import ConsultingTool
from firefly_dworkers.tools.registry import tool_registry

_DEFAULT_FUNCTIONAL_KEYWORDS: tuple[str, ...] = (
    "must", "shall", "should", "need", "require", "want",
)
_DEFAULT_NONFUNCTIONAL_KEYWORDS: tuple[str, ...] = (
    "performance", "security", "scalab", "reliab", "availab", "uptime",
)
_DEFAULT_CONSTRAINT_KEYWORDS: tuple[str, ...] = (
    "limit", "constraint", "budget", "deadline", "restrict", "cannot",
    "no more than",
)


@tool_registry.register("requirement_gathering", category="consulting")
class RequirementGatheringTool(ConsultingTool):
    """Take interview notes or documents and extract structured requirements.

    Categorises requirements into functional, non-functional, and constraints.
    This tool structures and organises information — it does not call external
    APIs.

    Configuration parameters:

    * ``default_categories`` -- Default comma-separated requirement categories.
    * ``functional_keywords`` -- Keywords that signal a functional requirement.
    * ``nonfunctional_keywords`` -- Keywords that upgrade a functional
      requirement to non-functional.
    * ``constraint_keywords`` -- Keywords that indicate a constraint.
    * ``sentence_split_pattern`` -- Regex pattern used to split text into
      sentences.
    """

    def __init__(
        self,
        *,
        default_categories: str = "functional,non-functional,constraints",
        functional_keywords: Sequence[str] | None = None,
        nonfunctional_keywords: Sequence[str] | None = None,
        constraint_keywords: Sequence[str] | None = None,
        sentence_split_pattern: str = r"[.\n]",
        guards: Sequence[GuardProtocol] = (),
    ):
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
                    default=default_categories,
                ),
            ],
        )
        self._default_categories = default_categories
        self._functional_kw = tuple(functional_keywords) if functional_keywords else _DEFAULT_FUNCTIONAL_KEYWORDS
        self._nonfunctional_kw = tuple(nonfunctional_keywords) if nonfunctional_keywords else _DEFAULT_NONFUNCTIONAL_KEYWORDS
        self._constraint_kw = tuple(constraint_keywords) if constraint_keywords else _DEFAULT_CONSTRAINT_KEYWORDS
        self._split_pattern = sentence_split_pattern

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        notes = kwargs["notes"]
        project_name = kwargs.get("project_name", "Unnamed Project")
        categories_raw = kwargs.get("categories", self._default_categories)
        categories = [c.strip() for c in categories_raw.split(",")]

        # Split notes into sentences for classification
        sentences = [s.strip() for s in re.split(self._split_pattern, notes) if s.strip()]

        requirements: dict[str, list[str]] = {cat: [] for cat in categories}

        for sentence in sentences:
            lower = sentence.lower()
            if any(kw in lower for kw in self._functional_kw):
                if any(kw in lower for kw in self._nonfunctional_kw):
                    target = "non-functional" if "non-functional" in categories else categories[0]
                elif any(kw in lower for kw in self._constraint_kw):
                    target = "constraints" if "constraints" in categories else categories[-1]
                else:
                    target = "functional" if "functional" in categories else categories[0]
                requirements[target].append(sentence)
            elif any(kw in lower for kw in self._constraint_kw):
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
