"""Tests for the RetryPolicy helper."""

import pytest

from firefly_dworkers_cli.tui.retry_policy import RetryPolicy


class TestRetryPolicy:
    def test_default_max_retries(self):
        policy = RetryPolicy()
        assert policy.max_retries == 3

    def test_is_retryable_eof_error(self):
        policy = RetryPolicy()
        assert policy.is_retryable("EOF while parsing an object at line 1 column 58")

    def test_is_retryable_json_decode(self):
        policy = RetryPolicy()
        assert policy.is_retryable("Expecting value: line 1 column 1 (char 0)")

    def test_is_retryable_incomplete_response(self):
        policy = RetryPolicy()
        assert policy.is_retryable("Incomplete JSON")

    def test_not_retryable_generic_error(self):
        policy = RetryPolicy()
        assert not policy.is_retryable("Connection refused")

    def test_not_retryable_auth_error(self):
        policy = RetryPolicy()
        assert not policy.is_retryable("Authentication failed: invalid API key")

    def test_backoff_delay_exponential(self):
        policy = RetryPolicy(base_delay=2.0)
        assert policy.delay_for_attempt(1) == 2.0
        assert policy.delay_for_attempt(2) == 4.0
        assert policy.delay_for_attempt(3) == 8.0

    def test_should_retry_within_max(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(1, "EOF while parsing")
        assert policy.should_retry(2, "EOF while parsing")
        assert policy.should_retry(3, "EOF while parsing")

    def test_should_not_retry_over_max(self):
        policy = RetryPolicy(max_retries=3)
        assert not policy.should_retry(4, "EOF while parsing")

    def test_should_not_retry_non_retryable(self):
        policy = RetryPolicy()
        assert not policy.should_retry(1, "Connection refused")

    def test_format_retry_message(self):
        policy = RetryPolicy()
        msg = policy.format_retry_message("Leo", 3, 6, 2)
        assert "Retrying" in msg
        assert "Leo" in msg
        assert "2/3" in msg

    def test_format_failure_message(self):
        policy = RetryPolicy()
        msg = policy.format_failure_message("Leo", 3, 6, "EOF while parsing")
        assert "failed" in msg.lower()
        assert "Leo" in msg
