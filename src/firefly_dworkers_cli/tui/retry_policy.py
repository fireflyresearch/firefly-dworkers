"""Retry policy for plan step execution.

Detects retryable errors (JSON parsing, EOF, incomplete response) and provides
exponential backoff delays. Non-retryable errors (auth, connection) fail immediately.
"""

from __future__ import annotations

import re

# Patterns that indicate a retryable (transient/model) error
_RETRYABLE_PATTERNS = [
    re.compile(r"EOF while parsing", re.IGNORECASE),
    re.compile(r"Expecting (?:value|property name|',')", re.IGNORECASE),
    re.compile(r"Incomplete JSON", re.IGNORECASE),
    re.compile(r"Unterminated string", re.IGNORECASE),
    re.compile(r"Invalid (?:control character|escape)", re.IGNORECASE),
    re.compile(r"Extra data", re.IGNORECASE),
    re.compile(r"JSONDecodeError", re.IGNORECASE),
]


class RetryPolicy:
    """Encapsulates retry logic for plan step execution."""

    def __init__(self, max_retries: int = 3, base_delay: float = 2.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay

    def is_retryable(self, error_msg: str) -> bool:
        """Check if the error message indicates a retryable failure."""
        return any(p.search(error_msg) for p in _RETRYABLE_PATTERNS)

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the backoff delay in seconds for the given attempt number."""
        return self.base_delay * (2 ** (attempt - 1))

    def should_retry(self, attempt: int, error_msg: str) -> bool:
        """Determine if a retry should be attempted."""
        return attempt <= self.max_retries and self.is_retryable(error_msg)

    def format_retry_message(
        self, agent_name: str, step: int, total: int, attempt: int
    ) -> str:
        """Format a user-facing retry message."""
        return (
            f"\u27f3 Retrying step {step}/{total} ({agent_name})... "
            f"(attempt {attempt}/{self.max_retries})"
        )

    def format_failure_message(
        self, agent_name: str, step: int, total: int, error_msg: str
    ) -> str:
        """Format a user-facing failure message after all retries exhausted."""
        return (
            f"\u2717 Step {step}/{total} ({agent_name}) failed after "
            f"{self.max_retries} attempts: {error_msg}. "
            f"Continuing with remaining steps."
        )
