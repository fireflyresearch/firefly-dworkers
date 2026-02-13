"""EmailTool — send and receive messages via SMTP/IMAP.

Uses ``aiosmtplib`` for sending and the stdlib ``imaplib`` for reading.
Install with::

    pip install firefly-dworkers[email]
"""

from __future__ import annotations

import asyncio
import email as _email_mod
import imaplib
import logging
from collections.abc import Sequence
from email.mime.text import MIMEText
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.communication.base import Message, MessageTool
from firefly_dworkers.tools.registry import tool_registry

logger = logging.getLogger(__name__)

try:
    import aiosmtplib

    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    aiosmtplib = None  # type: ignore[assignment]
    AIOSMTPLIB_AVAILABLE = False


@tool_registry.register("email", category="communication")
class EmailTool(MessageTool):
    """Email communication via SMTP (send) and IMAP (read).

    Configuration parameters:

    * ``smtp_host`` / ``smtp_port`` -- SMTP server for sending.
    * ``smtp_use_tls`` -- Whether to use STARTTLS (default ``True``).
    * ``imap_host`` / ``imap_port`` -- IMAP server for reading.
    * ``username`` / ``password`` -- Authentication credentials.
    * ``from_address`` -- Sender address (defaults to ``username``).
    * ``timeout`` -- Connection timeout in seconds.
    """

    def __init__(
        self,
        *,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_use_tls: bool = True,
        imap_host: str = "",
        imap_port: int = 993,
        username: str = "",
        password: str = "",
        from_address: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__("email", description="Send and receive messages via email", guards=guards)
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_use_tls = smtp_use_tls
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._username = username
        self._password = password
        self._from_address = from_address or username
        self._timeout = timeout

    # -- port implementation -------------------------------------------------

    async def _send(self, channel: str, content: str) -> Message:
        if not AIOSMTPLIB_AVAILABLE:
            raise ImportError(
                "aiosmtplib is required for EmailTool send. "
                "Install with: pip install firefly-dworkers[email]"
            )
        if not self._smtp_host:
            raise ConnectorError("EmailTool send requires smtp_host")
        if not self._username or not self._password:
            raise ConnectorAuthError("EmailTool requires username and password")

        msg = MIMEText(content)
        msg["From"] = self._from_address
        msg["To"] = channel
        msg["Subject"] = content[:80] if len(content) <= 80 else content[:77] + "..."

        await aiosmtplib.send(
            msg,
            hostname=self._smtp_host,
            port=self._smtp_port,
            username=self._username,
            password=self._password,
            start_tls=self._smtp_use_tls,
            timeout=self._timeout,
        )

        return Message(
            id=f"email-{hash(content) & 0xFFFFFFFF:08x}",
            channel=channel,
            sender=self._from_address,
            content=content,
        )

    async def _read(self, channel: str, message_id: str) -> list[Message]:
        if not self._imap_host:
            raise ConnectorError("EmailTool read requires imap_host")
        if not self._username or not self._password:
            raise ConnectorAuthError("EmailTool requires username and password")

        def _fetch() -> list[Message]:
            conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
            try:
                conn.login(self._username, self._password)
                mailbox = channel or "INBOX"
                conn.select(mailbox)

                if message_id:
                    _, data = conn.fetch(message_id, "(RFC822)")
                    ids_to_fetch = [message_id]
                else:
                    _, data = conn.search(None, "ALL")
                    ids_to_fetch = data[0].split()[-10:] if data[0] else []

                messages: list[Message] = []
                for uid in ids_to_fetch:
                    _, msg_data = conn.fetch(uid, "(RFC822)")
                    if msg_data[0] is None:
                        continue
                    raw = msg_data[0]
                    if isinstance(raw, tuple):
                        raw = raw[1]
                    parsed = _email_mod.message_from_bytes(raw if isinstance(raw, bytes) else raw.encode())
                    body = ""
                    if parsed.is_multipart():
                        for part in parsed.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                body = payload.decode("utf-8", errors="replace") if payload else ""
                                break
                    else:
                        payload = parsed.get_payload(decode=True)
                        body = payload.decode("utf-8", errors="replace") if payload else ""

                    messages.append(
                        Message(
                            id=uid.decode() if isinstance(uid, bytes) else str(uid),
                            channel=mailbox,
                            sender=parsed.get("From", ""),
                            content=body[:10_000],
                            timestamp=parsed.get("Date", ""),
                        )
                    )
                return messages
            finally:
                conn.logout()

        return await asyncio.to_thread(_fetch)

    async def _list_channels(self) -> list[str]:
        if not self._imap_host:
            raise ConnectorError("EmailTool list_channels requires imap_host")
        if not self._username or not self._password:
            raise ConnectorAuthError("EmailTool requires username and password")

        def _list_mailboxes() -> list[str]:
            conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
            try:
                conn.login(self._username, self._password)
                _, mailboxes = conn.list()
                result = []
                for mb in mailboxes or []:
                    decoded = mb.decode() if isinstance(mb, bytes) else str(mb)
                    # Parse IMAP list response: e.g. '(\\HasNoChildren) "/" "INBOX"'
                    parts = decoded.rsplit('" "', 1)
                    name = parts[-1].strip('"') if len(parts) > 1 else decoded.rsplit(" ", 1)[-1].strip('"')
                    result.append(name)
                return result
            finally:
                conn.logout()

        return await asyncio.to_thread(_list_mailboxes)
