"""Presentation tools -- PowerPoint and Google Slides."""

from __future__ import annotations

from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.models import (
    ChartSpec,
    PlaceholderInfo,
    PresentationData,
    ShapeInfo,
    SlideData,
    SlideOperation,
    SlideSpec,
    TableSpec,
)
from firefly_dworkers.tools.presentation.powerpoint import PowerPointTool

__all__ = [
    "ChartSpec",
    "PlaceholderInfo",
    "PowerPointTool",
    "PresentationData",
    "PresentationTool",
    "ShapeInfo",
    "SlideData",
    "SlideOperation",
    "SlideSpec",
    "TableSpec",
]
