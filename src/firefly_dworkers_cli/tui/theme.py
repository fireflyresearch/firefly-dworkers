"""Theme constants and Textual CSS for the dworkers TUI.

Transparent backgrounds let the terminal's native colors show through.
Monochrome text with minimal color — only green for success and red for errors.
"""

# Color tokens — monochrome palette (text only, no backgrounds)
BG = "transparent"
BG_HEADER = "transparent"
BG_INPUT = "transparent"
BG_MESSAGE = "transparent"
BORDER = "#444444"
BORDER_USER = "#444444"
BORDER_AI = "#444444"
BORDER_SYSTEM = "#444444"
BORDER_TOOL = "#444444"
TEXT = "#d4d4d4"
TEXT_DIM = "#666666"
TEXT_MUTED = "#555555"
ACCENT = "#d4d4d4"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#ef4444"

APP_CSS = """
Screen {
    background: transparent;
    color: #d4d4d4;
}

/* ── Welcome banner ──────────────────────────── */

#welcome {
    width: 1fr;
    height: auto;
    content-align: center middle;
    padding: 4 8;
    color: #666666;
}

#welcome .welcome-title {
    text-style: bold;
    color: #d4d4d4;
    text-align: center;
    width: 1fr;
    padding: 1 0;
}

#welcome .welcome-hint {
    color: #666666;
    text-align: center;
    width: 1fr;
}

/* ── Message list ────────────────────────────── */

#message-list {
    height: 1fr;
    padding: 0 1;
    scrollbar-size: 1 1;
    scrollbar-background: transparent;
    scrollbar-color: #444444;
    display: none;
}

/* ── Message boxes ───────────────────────────── */

.msg-box {
    margin: 0 0 1 0;
    padding: 0 1;
    width: 1fr;
    height: auto;
}

.msg-box-ai {
    border-left: thick #444444;
    padding: 0 1 0 1;
    margin: 0 0 1 0;
    width: 1fr;
    height: auto;
}

.msg-header {
    height: 1;
    padding: 0 0;
    width: 1fr;
}

.msg-sender {
    width: auto;
    padding: 0 1 0 0;
}

.msg-sender-human {
    color: #666666;
}

.msg-sender-ai {
    color: #d4d4d4;
    text-style: bold;
}

.msg-sender-system {
    color: #666666;
    text-style: italic;
}

.msg-timestamp {
    width: auto;
    color: #555555;
    dock: right;
}

.msg-content {
    padding: 0;
    width: 1fr;
    height: auto;
}

.msg-content-user {
    padding: 0;
    width: 1fr;
    height: auto;
    color: #e5e5e5;
}

.msg-divider {
    height: 1;
    color: #444444;
    width: 1fr;
    text-align: center;
    margin: 1 0;
}

/* ── Tool call boxes ─────────────────────────── */

.tool-call {
    border-left: thick #444444;
    margin: 0 2 1 2;
    padding: 0 1;
    height: auto;
}

.tool-call-header {
    color: #666666;
    height: 1;
}

.tool-call-content {
    color: #d4d4d4;
    height: auto;
    max-height: 8;
}

/* ── Streaming indicator ─────────────────────── */

.streaming-indicator {
    color: #666666;
    text-style: italic;
    padding: 0 0 0 1;
}

.response-summary {
    color: #555555;
    text-style: italic;
    padding: 0 0 0 1;
    height: 1;
}

/* ── Input area ──────────────────────────────── */

#input-area {
    dock: bottom;
    height: auto;
    max-height: 10;
    min-height: 3;
    border-top: solid #444444;
    padding: 0 1;
}

#input-area #prompt-input {
    width: 1fr;
    min-height: 1;
    max-height: 8;
    background: transparent;
    border: none;
    color: #d4d4d4;
}

#input-area #prompt-input:focus {
    border: none;
}

.prompt-prefix {
    color: #666666;
    width: 2;
    padding: 0;
}

#input-row {
    height: auto;
    width: 1fr;
}

#input-area .input-hint {
    color: #555555;
    height: 1;
    padding: 0 1;
    text-align: right;
}

/* ── Status bar ──────────────────────────────── */

#status-bar {
    dock: bottom;
    height: 1;
    color: #666666;
    padding: 0 2;
}

#status-bar .status-item {
    width: auto;
    padding: 0 0;
}

#status-bar .status-model {
    color: #d4d4d4;
}

#status-bar .status-tokens {
    color: #666666;
}

#status-bar .status-connection {
    dock: right;
    width: auto;
    padding: 0 0;
}

#status-bar .status-connected {
    color: #10b981;
}

#status-bar .status-disconnected {
    color: #ef4444;
}

#status-bar .status-mode {
    color: #666666;
}

#status-bar .status-autonomy {
    color: #666666;
}

#status-bar .status-sep {
    color: #555555;
    width: auto;
    padding: 0 0;
}

/* ── Header ──────────────────────────────────── */

#header-bar {
    dock: top;
    height: 1;
    padding: 0 2;
}

#header-bar .header-title {
    color: #d4d4d4;
    width: 1fr;
}

#header-bar .header-hint {
    dock: right;
    width: auto;
    color: #555555;
}

/* ── Slash command output ────────────────────── */

.cmd-output {
    border-left: thick #444444;
    margin: 0 2 1 2;
    padding: 0 1;
    height: auto;
}

.cmd-output-header {
    color: #666666;
    height: 1;
}

.cmd-output-content {
    height: auto;
}
"""
