"""Observability API router -- usage metrics and cost tracking."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class UsageResponse(BaseModel):
    """Usage summary response."""

    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_requests: int = 0
    total_latency_ms: float = 0.0
    by_agent: dict[str, Any] = Field(default_factory=dict)
    by_model: dict[str, Any] = Field(default_factory=dict)


def _get_usage_summary() -> dict[str, Any]:
    """Get usage summary from framework's default tracker."""
    try:
        from fireflyframework_genai.observability.usage import default_usage_tracker

        summary = default_usage_tracker.get_summary()
        return {
            "total_tokens": summary.total_tokens,
            "total_cost_usd": summary.total_cost_usd,
            "total_requests": summary.total_requests,
            "total_latency_ms": summary.total_latency_ms,
            "by_agent": summary.by_agent,
            "by_model": summary.by_model,
        }
    except ImportError:
        return {}


@router.get("/usage")
async def get_usage() -> UsageResponse:
    """Get global usage metrics."""
    data = _get_usage_summary()
    return UsageResponse(**data)


@router.get("/usage/{agent_name}")
async def get_agent_usage(agent_name: str) -> UsageResponse:
    """Get usage metrics for a specific agent/worker."""
    try:
        from fireflyframework_genai.observability.usage import default_usage_tracker

        summary = default_usage_tracker.get_summary_for_agent(agent_name)
        return UsageResponse(
            total_tokens=summary.total_tokens,
            total_cost_usd=summary.total_cost_usd,
            total_requests=summary.total_requests,
            total_latency_ms=summary.total_latency_ms,
            by_agent=summary.by_agent,
            by_model=summary.by_model,
        )
    except ImportError:
        return UsageResponse()
