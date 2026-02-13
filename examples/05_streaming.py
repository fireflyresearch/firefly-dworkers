"""Streaming example — real-time token output.

Demonstrates async streaming with ``run_stream()`` and
``stream_tokens()`` so that tokens appear as they are generated.
"""

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.workers.analyst import AnalystWorker

config = TenantConfig(
    id="demo",
    name="Demo Corp",
    models={"default": "anthropic:claude-sonnet-4-5-20250929"},
    branding={"company_name": "Demo Corp"},
)


async def main() -> None:
    worker = AnalystWorker(config)
    stream_ctx = await worker.run_stream(
        "Briefly outline three strategies a consulting firm can use "
        "to differentiate itself in the AI advisory market.",
        streaming_mode="incremental",
    )
    async with stream_ctx as stream:
        async for token in stream.stream_tokens():
            print(token, end="", flush=True)
    print()  # trailing newline


asyncio.run(main())
