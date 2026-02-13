"""GenericAPITool — make HTTP API calls."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False


class GenericAPITool(BaseTool):
    """Make HTTP API calls to external services.

    Supports GET and POST methods with JSON payloads.  Requires ``httpx``
    (install with ``pip install httpx``).
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        default_headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
    ):
        super().__init__(
            "api_client",
            description="Make HTTP API calls to external services",
            tags=["data", "api", "http"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="method",
                    type_annotation="str",
                    description="HTTP method: GET or POST",
                    required=True,
                ),
                ParameterSpec(
                    name="url",
                    type_annotation="str",
                    description="URL to call (appended to base_url if configured)",
                    required=True,
                ),
                ParameterSpec(
                    name="body",
                    type_annotation="str",
                    description="JSON request body (for POST)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="headers",
                    type_annotation="str",
                    description="Additional headers as JSON string",
                    required=False,
                    default="",
                ),
            ],
        )
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._default_headers = default_headers or {}
        self._http_timeout = timeout

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx required for GenericAPITool — install with: pip install httpx")

        method = kwargs["method"].upper()
        url = kwargs["url"]
        if self._base_url and not url.startswith(("http://", "https://")):
            url = f"{self._base_url}/{url.lstrip('/')}"

        import json

        headers = dict(self._default_headers)
        extra_headers = kwargs.get("headers", "")
        if extra_headers:
            headers.update(json.loads(extra_headers))

        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                body = kwargs.get("body", "")
                json_body = json.loads(body) if body else None
                response = await client.post(url, headers=headers, json=json_body)
            else:
                raise ValueError(f"Unsupported HTTP method '{method}'; use GET or POST")

            response.raise_for_status()

        return {
            "status_code": response.status_code,
            "body": response.text[:10000],
            "headers": dict(response.headers),
        }
