"""Communication tools — abstract base for messaging providers."""

from __future__ import annotations

from firefly_dworkers.tools.communication.base import Message, MessageTool

__all__ = [
    "Message",
    "MessageTool",
]
