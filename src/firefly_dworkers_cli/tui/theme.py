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
    height: 1fr;
    align: center middle;
    padding: 2 4;
}

#welcome .welcome-text {
    color: #666666;
    text-align: center;
    width: auto;
    max-width: 52;
    content-align: center middle;
}

.connecting-indicator {
    color: #f59e0b;
    text-align: center;
    text-style: bold;
    width: auto;
    height: 1;
    margin: 1 0 0 0;
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
    color: #f59e0b;
    text-style: bold;
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
    max-height: 6;
    min-height: 2;
    border-top: solid #444444;
    padding: 0 1;
}

#input-area #prompt-input {
    width: 1fr;
    min-height: 1;
    max-height: 5;
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

/* ── @mention autocomplete popup ─────────────── */

#mention-popup {
    display: none;
    dock: bottom;
    height: auto;
    max-height: 8;
    width: 1fr;
    padding: 0 1;
    border-top: solid #444444;
    color: #d4d4d4;
    background: transparent;
}

#mention-popup.visible {
    display: block;
}

#mention-popup .mention-item {
    height: 1;
    width: 1fr;
    padding: 0 1;
    color: #999999;
}

#mention-popup .mention-item-selected {
    height: 1;
    width: 1fr;
    padding: 0 1;
    color: #d4d4d4;
    background: #333333;
    text-style: bold;
}

/* ── Slash command autocomplete popup ───────── */

#command-popup {
    display: none;
    dock: bottom;
    height: auto;
    max-height: 10;
    width: 1fr;
    padding: 0 1;
    border-top: solid #444444;
    color: #d4d4d4;
    background: transparent;
}

#command-popup.visible {
    display: block;
}

#command-popup .command-item {
    height: 1;
    width: 1fr;
    padding: 0 1;
    color: #999999;
}

#command-popup .command-item-selected {
    height: 1;
    width: 1fr;
    padding: 0 1;
    color: #d4d4d4;
    background: #333333;
    text-style: bold;
}

/* ── Task progress block ───────────────────── */

.task-progress-block {
    height: auto;
    padding: 0 0 0 1;
}

.activity-line {
    color: #f59e0b;
    text-style: bold;
    height: 1;
}

.task-tree {
    color: #999999;
    height: auto;
    padding: 0 0 0 2;
}

/* ── Interactive question ──────────────────── */

.interactive-question {
    height: auto;
    padding: 0 1;
}

#input-area.question-active {
    max-height: 50%;
}

.question-text {
    color: #d4d4d4;
    height: auto;
    padding: 0 0 1 0;
}

.question-options {
    color: #d4d4d4;
    height: auto;
}

.question-option {
    height: 1;
    width: 1fr;
    padding: 0;
    color: #d4d4d4;
}

.question-option:hover {
    background: #333333;
    color: #ffffff;
}

.question-hint {
    color: #555555;
    height: 1;
    padding: 1 0 0 0;
}

.question-answered {
    color: #10b981;
    height: 1;
}

/* ── Attachment indicator ────────────────────── */

#attachment-bar {
    height: auto;
    padding: 0 1;
    color: #f59e0b;
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

#status-bar .status-remote {
    color: #60a5fa;
}

#status-bar .status-disconnected {
    color: #ef4444;
}

#status-bar .status-model-loc {
    color: #888888;
}

#status-bar .model-loc-local {
    color: #10b981;
}

#status-bar .model-loc-cloud {
    color: #888888;
}

#status-bar .status-mode {
    color: #666666;
}

#status-bar .status-autonomy {
    color: #666666;
}

#status-bar .autonomy-autonomous {
    color: #10b981;
}

#status-bar .autonomy-semi-supervised {
    color: #f59e0b;
}

#status-bar .autonomy-manual {
    color: #ef4444;
}

#status-bar .status-sep {
    color: #555555;
    width: auto;
    padding: 0 0;
}

#status-bar .status-participants {
    color: #888888;
    width: auto;
    padding: 0 0;
}

#status-bar .status-private {
    color: #f59e0b;
    width: auto;
    padding: 0 0;
}

#project-indicator {
    width: auto;
    height: 1;
    color: #555555;
    padding: 0 0;
}

#project-indicator.status-has-project {
    color: #10b981;
}

/* ── Header ──────────────────────────────────── */

#header-bar {
    dock: top;
    height: 1;
    padding: 0 2;
    background: #1a1a1a;
}

#header-bar .header-title {
    color: #e5e5e5;
    text-style: bold;
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
    padding: 0;
}

.cmd-output-content MarkdownH2 {
    text-style: bold;
    color: #d4d4d4;
    margin: 0;
    padding: 0 0 1 0;
}

.cmd-output-content MarkdownTable {
    padding: 0;
    margin: 0;
}

/* ── Avatar colors ──────────────────────────── */

.avatar-green { color: #10b981; }
.avatar-blue { color: #60a5fa; }
.avatar-cyan { color: #22d3ee; }
.avatar-yellow { color: #fbbf24; }
.avatar-magenta { color: #c084fc; }

/* ── Status bar hints ──────────────────────── */

#status-bar .status-spacer {
    width: 1fr;
}

#status-bar .status-hints {
    width: auto;
    color: #555555;
}

#status-bar .status-agent {
    color: #60a5fa;
}

/* ── Rich response rendering ──────────────── */

.msg-content MarkdownFence {
    margin: 1 0;
    padding: 0 1;
    background: #1a1a1a;
    border: solid #333333;
    color: #d4d4d4;
    overflow-x: auto;
}

.msg-content Markdown > MarkdownBlockQuote {
    border-left: thick #444444;
    padding: 0 1;
    color: #999999;
    margin: 0 0 1 0;
}

.msg-content MarkdownH1 {
    text-style: bold;
    color: #e5e5e5;
    margin: 1 0 0 0;
    padding: 0;
}

.msg-content MarkdownH2 {
    text-style: bold;
    color: #d4d4d4;
    margin: 1 0 0 0;
    padding: 0;
}

.msg-content MarkdownH3 {
    text-style: bold;
    color: #d4d4d4;
    margin: 1 0 0 0;
    padding: 0;
}

.msg-content MarkdownBulletList {
    margin: 0 0 0 2;
    padding: 0;
}

.msg-content MarkdownOrderedList {
    margin: 0 0 0 2;
    padding: 0;
}

/* -- Contextual toolbar --------------------- */

#toolbar {
    dock: top;
    height: 1;
    background: #1e1e1e;
    color: #888888;
    padding: 0 1;
}

#toolbar.toolbar-plan {
    color: #4ec9b0;
}

#toolbar.toolbar-streaming {
    color: #e5c07b;
}

/* -- Conversation tab bar ------------------- */

#tab-bar {
    dock: top;
    height: 1;
    width: 1fr;
    padding: 0 1;
    background: transparent;
    color: #666666;
}

.conv-tab {
    width: auto;
    padding: 0 1;
    color: #666666;
}

.conv-tab-active {
    width: auto;
    padding: 0 1;
    color: #d4d4d4;
    text-style: bold;
}

.conv-tab-new {
    width: auto;
    padding: 0 1;
    color: #555555;
}

/* -- Plan approval ----------------------- */

.plan-approval {
    border-left: thick #f59e0b;
    margin: 0 2 1 2;
    padding: 0 1;
    height: auto;
}

.plan-steps {
    height: auto;
    padding: 0;
}

.plan-buttons {
    height: 1;
    padding: 0;
}

.plan-btn-approve {
    color: #10b981;
    width: auto;
    text-style: bold;
}

.plan-btn-modify {
    color: #f59e0b;
    width: auto;
}

.plan-btn-reject {
    color: #666666;
    width: auto;
}
"""
