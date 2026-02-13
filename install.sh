#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# dworkers installer
# Usage:  curl -fsSL .../install.sh | bash
#         bash install.sh [--yes] [--prefix PATH] [--profile PROFILE] [--uninstall]
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────

DWORKERS_VERSION="26.02.01"
DEFAULT_PREFIX="${HOME}/.dworkers"
UV_INSTALL_URL="https://astral.sh/uv/install.sh"
PYTHON_VERSION="3.13"

# ── Color / Formatting ───────────────────────────────────────────────────────
# Respect NO_COLOR (https://no-color.org/) and dumb terminals.

if [[ -n "${NO_COLOR:-}" ]] || [[ "${TERM:-}" == "dumb" ]]; then
    BOLD=""
    RESET=""
    RED=""
    GREEN=""
    YELLOW=""
    CYAN=""
    DIM=""
    BOLD_WHITE=""
    BRIGHT_YELLOW=""
    BRIGHT_CYAN=""
    BRIGHT_GREEN=""
    BRIGHT_RED=""
else
    BOLD=$'\033[1m'
    RESET=$'\033[0m'
    RED=$'\033[0;31m'
    GREEN=$'\033[0;32m'
    YELLOW=$'\033[0;33m'
    CYAN=$'\033[0;36m'
    DIM=$'\033[2m'
    BOLD_WHITE=$'\033[1;37m'
    BRIGHT_YELLOW=$'\033[1;33m'
    BRIGHT_CYAN=$'\033[1;36m'
    BRIGHT_GREEN=$'\033[1;32m'
    BRIGHT_RED=$'\033[1;31m'
fi

# ── Output helpers ────────────────────────────────────────────────────────────

info() {
    printf "  %s\n" "${GREEN}✓${RESET} $*"
}

warn() {
    printf "  %s\n" "${YELLOW}!${RESET} $*"
}

fail() {
    printf "  %s\n" "${RED}✗${RESET} $*"
}

pending() {
    printf "  %s\n" "${DIM}·${RESET} $*"
}

die() {
    printf "  %s\n" "${RED}✗${RESET} $*" >&2
    exit 1
}

section() {
    local title="$1"
    printf "\n  %s\n" "${BOLD}${title}${RESET}"
    printf "  %s\n" "───────────────────────"
}

# ── Argument parsing ─────────────────────────────────────────────────────────

parse_args() {
    OPT_UNINSTALL=0
    OPT_YES=0
    OPT_PREFIX=""
    OPT_PROFILE=""

    # Auto-detect non-interactive (stdin is not a TTY)
    if ! [ -t 0 ]; then
        OPT_YES=1
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --uninstall)
                OPT_UNINSTALL=1
                shift
                ;;
            --yes|-y)
                OPT_YES=1
                shift
                ;;
            --prefix)
                if [[ $# -lt 2 ]]; then
                    die "--prefix requires a path argument"
                fi
                OPT_PREFIX="$2"
                shift 2
                ;;
            --profile)
                if [[ $# -lt 2 ]]; then
                    die "--profile requires a profile name"
                fi
                OPT_PROFILE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done
}

show_help() {
    cat <<'HELPTEXT'

  dworkers installer

  Usage:
    bash install.sh [OPTIONS]

  Options:
    --yes, -y          Skip confirmation prompts
    --prefix PATH      Installation prefix (default: ~/.dworkers)
    --profile PROFILE  Install profile: minimal, analyst, server, full, custom
    --uninstall        Remove dworkers installation
    -h, --help         Show this help message

HELPTEXT
}

# ── Profile mapping ──────────────────────────────────────────────────────────

profile_to_extras() {
    local profile="${1:-analyst}"
    case "$profile" in
        minimal)  echo "cli" ;;
        analyst)  echo "cli,web,data,presentation" ;;
        server)   echo "cli,web,server" ;;
        full)     echo "all" ;;
        custom)   echo "custom" ;;
        *)        die "Unknown profile: $profile" ;;
    esac
}

# ── Platform detection ───────────────────────────────────────────────────────

detect_platform() {
    DETECTED_OS=""
    DETECTED_ARCH=""
    DETECTED_SHELL_RC=""

    # OS
    case "$(uname -s)" in
        Darwin*)  DETECTED_OS="macos" ;;
        Linux*)   DETECTED_OS="linux" ;;
        *)        die "Unsupported OS: $(uname -s)" ;;
    esac

    # Architecture
    case "$(uname -m)" in
        x86_64|amd64)   DETECTED_ARCH="x86_64" ;;
        arm64|aarch64)  DETECTED_ARCH="arm64" ;;
        *)              die "Unsupported architecture: $(uname -m)" ;;
    esac

    # Shell RC file
    local current_shell
    current_shell="$(basename "${SHELL:-/bin/sh}")"
    case "$current_shell" in
        zsh)
            DETECTED_SHELL_RC="${HOME}/.zshrc"
            ;;
        bash)
            if [[ "$DETECTED_OS" == "macos" ]]; then
                DETECTED_SHELL_RC="${HOME}/.bash_profile"
            else
                DETECTED_SHELL_RC="${HOME}/.bashrc"
            fi
            ;;
        *)
            DETECTED_SHELL_RC="${HOME}/.profile"
            ;;
    esac
}

# ── Spinner ──────────────────────────────────────────────────────────────────

SPINNER_PID=""
SPINNER_FRAMES="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_spin() {
    local msg="$1"
    local i=0
    local len=${#SPINNER_FRAMES}
    while true; do
        # Each braille character is 3 bytes in UTF-8; extract one frame
        local frame="${SPINNER_FRAMES:$i:1}"
        printf "\r  %s %s" "${CYAN}${frame}${RESET}" "$msg"
        i=$(( (i + 1) % len ))
        sleep 0.08
    done
}

start_spinner() {
    local msg="${1:-}"
    # Non-interactive: just print a static line
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 1 ]; then
        pending "$msg"
        return
    fi
    _spin "$msg" &
    SPINNER_PID=$!
    # Ensure spinner is cleaned up on unexpected exit
    trap 'stop_spinner 2>/dev/null' EXIT
}

stop_spinner() {
    if [[ -n "${SPINNER_PID:-}" ]]; then
        kill "$SPINNER_PID" 2>/dev/null || true
        wait "$SPINNER_PID" 2>/dev/null || true
        SPINNER_PID=""
        printf "\r\033[2K"
    fi
}

# ── Command runner ───────────────────────────────────────────────────────────

try_cmd() {
    local max_attempts=3
    local attempt=1
    local backoff=1

    while [[ $attempt -le $max_attempts ]]; do
        if "$@"; then
            return 0
        fi
        if [[ $attempt -lt $max_attempts ]]; then
            warn "Attempt $attempt failed, retrying in ${backoff}s..."
            sleep "$backoff"
            backoff=$((backoff * 2))
        fi
        attempt=$((attempt + 1))
    done

    fail "Command failed after $max_attempts attempts: $*"
    return 1
}

# ── Test mode guard ──────────────────────────────────────────────────────────
# When sourced with DWORKERS_TEST_MODE=1, stop here so tests can call
# individual functions without triggering the main installer flow.

if [[ "${DWORKERS_TEST_MODE:-}" == "1" ]]; then
    return 0 2>/dev/null || true
fi

# ── Main (placeholder) ───────────────────────────────────────────────────────

parse_args "$@"
detect_platform

section "dworkers installer v${DWORKERS_VERSION}"
info "OS: ${DETECTED_OS}, Arch: ${DETECTED_ARCH}"
info "Prefix: ${OPT_PREFIX:-$DEFAULT_PREFIX}"
info "Profile: ${OPT_PROFILE:-<interactive>}"
info "Shell RC: ${DETECTED_SHELL_RC}"
echo ""
pending "Installer scaffold ready. Nothing to install yet."
