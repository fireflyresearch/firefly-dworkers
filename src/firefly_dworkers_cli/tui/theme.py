"""Theme constants and Textual CSS for the dworkers TUI."""

# Color tokens
PRIMARY = "#6C5CE7"
ACCENT = "#00B894"
WARNING = "#FDCB6E"
ERROR = "#E17055"
SURFACE = "#1E1E2E"
SURFACE_ALT = "#2A2A3E"
TEXT = "#CDD6F4"
TEXT_DIM = "#6C7086"
AI_BADGE = "#00B894"
USER_BADGE = "#6C5CE7"

APP_CSS = """
Screen {
    background: #1E1E2E;
    color: #CDD6F4;
}

#sidebar {
    width: 32;
    background: #181825;
    border-right: solid #313244;
    padding: 1 0;
}

#sidebar .section-label {
    color: #6C7086;
    text-style: bold;
    padding: 1 2 0 2;
}

#sidebar .nav-item {
    padding: 0 2;
    height: 3;
    content-align-vertical: middle;
}

#sidebar .nav-item:hover {
    background: #2A2A3E;
}

#sidebar .nav-item.--active {
    background: #2A2A3E;
    color: #CDD6F4;
    border-left: thick #6C5CE7;
}

#content {
    background: #1E1E2E;
}

.badge {
    background: #00B894;
    color: #1E1E2E;
    text-style: bold;
    padding: 0 1;
}

.badge-warning {
    background: #FDCB6E;
    color: #1E1E2E;
}

.badge-error {
    background: #E17055;
    color: #1E1E2E;
}

.message-bubble {
    background: #2A2A3E;
    margin: 1 2;
    padding: 1 2;
    border: round #313244;
}

.message-bubble-user {
    border: round #6C5CE7;
}

.message-bubble-agent {
    border: round #00B894;
}

.input-bar {
    dock: bottom;
    height: auto;
    max-height: 8;
    background: #181825;
    border-top: solid #313244;
    padding: 1 2;
}

.stats-card {
    background: #2A2A3E;
    border: round #313244;
    padding: 1 2;
    height: auto;
}

.panel-title {
    text-style: bold;
    color: #CDD6F4;
    padding: 1 0;
}

Button {
    background: #6C5CE7;
    color: #CDD6F4;
    border: none;
    min-width: 12;
}

Button:hover {
    background: #7C6DF7;
}

Button.success {
    background: #00B894;
}

Button.warning {
    background: #FDCB6E;
    color: #1E1E2E;
}

Button.error {
    background: #E17055;
}

DataTable {
    background: #1E1E2E;
}

DataTable > .datatable--header {
    background: #181825;
    color: #6C7086;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #2A2A3E;
}

Input {
    background: #2A2A3E;
    border: round #313244;
    color: #CDD6F4;
}

Input:focus {
    border: round #6C5CE7;
}

TextArea {
    background: #2A2A3E;
    border: round #313244;
    color: #CDD6F4;
}

TextArea:focus {
    border: round #6C5CE7;
}

ListView {
    background: #1E1E2E;
}

ListView > ListItem {
    padding: 1 2;
}

ListView > ListItem.--highlight {
    background: #2A2A3E;
}

Tree {
    background: #1E1E2E;
}

#user-panel {
    dock: bottom;
    height: 4;
    padding: 0 2;
    border-top: solid #313244;
    color: #6C7086;
}
"""
