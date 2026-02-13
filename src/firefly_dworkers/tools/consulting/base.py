"""ConsultingTool -- abstract base for all consulting-domain tools.

Provides a shared foundation for the five consulting tools
(report generation, requirement gathering, process mapping,
gap analysis, documentation) with a default ``"consulting"`` tag.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class ConsultingTool(BaseTool):
    """Abstract base for consulting-domain tools.

    Ensures all consulting tools share the ``"consulting"`` tag and
    provides a consistent constructor pattern.  Subclasses still
    implement :meth:`_execute` as with any :class:`BaseTool`.
    """

    def __init__(
        self,
        name: str,
        *,
        description: str,
        tags: Sequence[str] = (),
        guards: Sequence[GuardProtocol] = (),
        parameters: Sequence[ParameterSpec] = (),
        **kwargs: Any,
    ) -> None:
        # Merge "consulting" tag with any subclass-provided tags
        merged_tags = list(dict.fromkeys(["consulting", *tags]))
        super().__init__(
            name,
            description=description,
            tags=merged_tags,
            guards=guards,
            parameters=parameters,
            **kwargs,
        )
