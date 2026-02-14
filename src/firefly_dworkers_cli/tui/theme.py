"""Theme constants and Textual CSS for the dworkers TUI.

Designed to match Claude Code's terminal aesthetic: dark background,
minimal chrome, bordered message boxes, and a persistent status bar.
"""

# Color tokens — terminal-native dark palette
BG = "#1a1a2e"
BG_HEADER = "#16213e"
BG_INPUT = "#0f0f23"
BG_MESSAGE = "#1a1a2e"
BORDER = "#2a2a4a"
BORDER_USER = "#6366f1"
BORDER_AI = "#10b981"
BORDER_SYSTEM = "#64748b"
BORDER_TOOL = "#f59e0b"
TEXT = "#e2e8f0"
TEXT_DIM = "#64748b"
TEXT_MUTED = "#475569"
ACCENT = "#6366f1"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#ef4444"

APP_CSS = """
Screen {
    background: #1a1a2e;
    color: #e2e8f0;
}

/* ── Welcome banner ──────────────────────────── */

#welcome {
    width: 1fr;
    height: auto;
    content-align: center middle;
    padding: 4 8;
    color: #64748b;
}

#welcome .welcome-title {
    text-style: bold;
    color: #e2e8f0;
    text-align: center;
    width: 1fr;
    padding: 1 0;
}

#welcome .welcome-hint {
    color: #475569;
    text-align: center;
    width: 1fr;
}

/* ── Message list ────────────────────────────── */

#message-list {
    height: 1fr;
    padding: 0 1;
    scrollbar-size: 1 1;
}

/* ── Message bubbles ─────────────────────────── */

.msg-box {
    margin: 0 0 1 0;
    padding: 0 1;
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
    text-style: bold;
    padding: 0 1 0 0;
}

.msg-sender-human {
    color: #6366f1;
}

.msg-sender-ai {
    color: #10b981;
}

.msg-sender-system {
    color: #64748b;
}

.msg-timestamp {
    width: auto;
    color: #475569;
    dock: right;
}

.msg-content {
    padding: 0;
    width: 1fr;
    height: auto;
}

.msg-divider {
    height: 1;
    color: #2a2a4a;
    width: 1fr;
    text-align: center;
    margin: 1 0;
}

/* ── Tool call boxes ─────────────────────────── */

.tool-call {
    border: round #f59e0b;
    margin: 0 2 1 2;
    padding: 0 1;
    height: auto;
}

.tool-call-header {
    color: #f59e0b;
    text-style: bold;
    height: 1;
}

.tool-call-content {
    color: #94a3b8;
    height: auto;
    max-height: 8;
}

/* ── Streaming indicator ─────────────────────── */

.streaming-indicator {
    color: #10b981;
    text-style: italic;
    padding: 0 0 0 2;
}

/* ── Input area ──────────────────────────────── */

#input-area {
    dock: bottom;
    height: auto;
    max-height: 10;
    min-height: 3;
    background: #0f0f23;
    border-top: solid #2a2a4a;
    padding: 0 1;
}

#input-area #prompt-input {
    width: 1fr;
    min-height: 1;
    max-height: 8;
    background: #0f0f23;
    border: none;
    color: #e2e8f0;
}

#input-area #prompt-input:focus {
    border: none;
}

#input-area .input-hint {
    color: #475569;
    height: 1;
    padding: 0 1;
    text-align: right;
}

/* ── Status bar ──────────────────────────────── */

#status-bar {
    dock: bottom;
    height: 1;
    background: #16213e;
    color: #64748b;
    padding: 0 2;
}

#status-bar .status-item {
    width: auto;
    padding: 0 1;
}

#status-bar .status-model {
    color: #6366f1;
    text-style: bold;
}

#status-bar .status-tokens {
    color: #64748b;
}

#status-bar .status-connection {
    dock: right;
    width: auto;
    padding: 0 1;
}

#status-bar .status-connected {
    color: #10b981;
}

#status-bar .status-disconnected {
    color: #ef4444;
}

#status-bar .status-mode {
    color: #10b981;
}

#status-bar .status-autonomy {
    color: #f59e0b;
}

#status-bar .status-sep {
    color: #475569;
    width: auto;
    padding: 0 0;
}

/* ── Header ──────────────────────────────────── */

#header-bar {
    dock: top;
    height: 1;
    background: #16213e;
    padding: 0 2;
}

#header-bar .header-title {
    text-style: bold;
    width: 1fr;
}

#header-bar .header-hint {
    dock: right;
    width: auto;
    color: #475569;
}

/* ── Slash command output ────────────────────── */

.cmd-output {
    border: round #64748b;
    margin: 0 2 1 2;
    padding: 0 1;
    height: auto;
}

.cmd-output-header {
    color: #64748b;
    text-style: bold;
    height: 1;
}

.cmd-output-content {
    height: auto;
}
"""
