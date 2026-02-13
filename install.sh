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

# ── Banner + TUI display ────────────────────────────────────────────────────

print_banner() {
    printf "%s" "${BRIGHT_YELLOW}"
    cat <<'BANNER'
    .___                    __
  __| _/_  _  _____________|  | __ ___________  ______
 / __ |\ \/ \/ /  _ \_  __ \  |/ // __ \_  __ \/  ___/
/ /_/ | \     (  <_> )  | \/    <\  ___/|  | \/\___ \
\____ |  \/\_/ \____/|__|  |__|_ \\___  >__|  /____  >
     \/                         \/    \/           \/
BANNER
    printf "%s\n" "${RESET}"
    printf "  %s\n" "${CYAN}        dworkers — Digital Workers as a Service${RESET}"
    printf "  %s\n" "${DIM}              Installer v${DWORKERS_VERSION}${RESET}"
}

print_welcome() {
    print_banner
    echo ""
    printf "  %s\n" "Welcome! This will install dworkers v${DWORKERS_VERSION} on your system."
}

_menu_draw() {
    local current="$1"
    shift
    local options=("$@")
    local i=0
    for opt in "${options[@]}"; do
        if [[ $i -eq $current ]]; then
            printf "  %s %s\n" "${BRIGHT_CYAN}›${RESET}" "${BOLD_WHITE}${opt}${RESET}"
        else
            printf "  %s %s\n" " " "${DIM}${opt}${RESET}"
        fi
        i=$((i + 1))
    done
}

menu_select() {
    local _result_var="$1"
    shift
    local options=("$@")
    local count=${#options[@]}
    local selected=0

    # Non-interactive: return first option immediately
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 0 ]; then
        eval "$_result_var=0"
        return 0
    fi

    # Hide cursor
    printf "\033[?25l"
    # Ensure cursor is restored on exit
    trap 'printf "\033[?25h"' RETURN 2>/dev/null || true

    # Draw initial menu
    _menu_draw "$selected" "${options[@]}"

    while true; do
        # Read a single character
        local key=""
        IFS= read -rsn1 key

        if [[ "$key" == "" ]]; then
            # Enter pressed
            break
        fi

        if [[ "$key" == $'\033' ]]; then
            # Escape sequence — read two more chars
            local seq1="" seq2=""
            IFS= read -rsn1 seq1
            IFS= read -rsn1 seq2
            if [[ "$seq1" == "[" ]]; then
                case "$seq2" in
                    A)  # Up arrow
                        selected=$(( (selected - 1 + count) % count ))
                        ;;
                    B)  # Down arrow
                        selected=$(( (selected + 1) % count ))
                        ;;
                esac
            fi
        fi

        # Redraw: move cursor up by count lines, then redraw
        printf "\033[%dA" "$count"
        _menu_draw "$selected" "${options[@]}"
    done

    # Restore cursor
    printf "\033[?25h"

    eval "$_result_var=$selected"
}

_toggle_draw() {
    local current="$1"
    shift
    # Remaining args: labels array then states array
    # We pass them as: count label1 label2 ... state1 state2 ...
    local count="$1"
    shift
    local labels=()
    local descs=()
    local i=0
    while [[ $i -lt $count ]]; do
        labels+=("$1")
        shift
        i=$((i + 1))
    done
    local states=()
    i=0
    while [[ $i -lt $count ]]; do
        states+=("$1")
        shift
        i=$((i + 1))
    done

    local selected_count=0
    for s in "${states[@]}"; do
        if [[ "$s" == "1" ]]; then
            selected_count=$((selected_count + 1))
        fi
    done

    i=0
    for label in "${labels[@]}"; do
        local desc=""
        if [[ $i -lt ${#descs[@]:-0} ]]; then
            desc=""
        fi
        local marker=""
        local color=""
        if [[ "${states[$i]}" == "1" ]]; then
            marker="${BRIGHT_GREEN}◉${RESET}"
        else
            marker="${DIM}○${RESET}"
        fi
        if [[ $i -eq $current ]]; then
            printf "  %s %s\n" "$marker" "${BOLD_WHITE}${label}${RESET}"
        else
            printf "  %s %s\n" "$marker" "${DIM}${label}${RESET}"
        fi
        i=$((i + 1))
    done
    printf "  %s\n" "${DIM}${selected_count}/${count} selected  |  ↑↓ move  space toggle  a all  n none  enter confirm${RESET}"
}

toggle_picker() {
    local _result_var="$1"
    shift

    # Parse "label:desc" items
    local labels=()
    local descs=()
    local states=()
    local count=0
    for item in "$@"; do
        local label="${item%%:*}"
        local desc=""
        if [[ "$item" == *":"* ]]; then
            desc="${item#*:}"
        fi
        labels+=("$label")
        descs+=("$desc")
        states+=(0)
        count=$((count + 1))
    done

    # Pre-select items via TOGGLE_PRESELECT
    if [[ -n "${TOGGLE_PRESELECT:-}" ]]; then
        for idx in $TOGGLE_PRESELECT; do
            if [[ $idx -ge 0 ]] && [[ $idx -lt $count ]]; then
                states[$idx]=1
            fi
        done
    fi

    # Non-interactive: return pre-selected items
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 0 ]; then
        local result=""
        local i=0
        while [[ $i -lt $count ]]; do
            if [[ "${states[$i]}" == "1" ]]; then
                if [[ -n "$result" ]]; then
                    result="${result},${labels[$i]}"
                else
                    result="${labels[$i]}"
                fi
            fi
            i=$((i + 1))
        done
        eval "$_result_var=\"\$result\""
        return 0
    fi

    local current=0

    # Hide cursor
    printf "\033[?25l"
    trap 'printf "\033[?25h"' RETURN 2>/dev/null || true

    # Initial draw (count lines + 1 for status bar)
    _toggle_draw "$current" "$count" "${labels[@]}" "${states[@]}"

    while true; do
        local key=""
        IFS= read -rsn1 key

        if [[ "$key" == "" ]]; then
            # Enter — confirm
            break
        fi

        case "$key" in
            " ")
                # Toggle current item
                if [[ "${states[$current]}" == "1" ]]; then
                    states[$current]=0
                else
                    states[$current]=1
                fi
                ;;
            a)
                # Select all
                local j=0
                while [[ $j -lt $count ]]; do
                    states[$j]=1
                    j=$((j + 1))
                done
                ;;
            n)
                # Select none
                local j=0
                while [[ $j -lt $count ]]; do
                    states[$j]=0
                    j=$((j + 1))
                done
                ;;
            $'\033')
                # Escape sequence
                local seq1="" seq2=""
                IFS= read -rsn1 seq1
                IFS= read -rsn1 seq2
                if [[ "$seq1" == "[" ]]; then
                    case "$seq2" in
                        A) current=$(( (current - 1 + count) % count )) ;;
                        B) current=$(( (current + 1) % count )) ;;
                    esac
                fi
                ;;
        esac

        # Redraw: move up count+1 lines (options + status bar)
        printf "\033[%dA" "$((count + 1))"
        _toggle_draw "$current" "$count" "${labels[@]}" "${states[@]}"
    done

    # Restore cursor
    printf "\033[?25h"

    # Build comma-separated result of selected labels
    local result=""
    local i=0
    while [[ $i -lt $count ]]; do
        if [[ "${states[$i]}" == "1" ]]; then
            if [[ -n "$result" ]]; then
                result="${result},${labels[$i]}"
            else
                result="${labels[$i]}"
            fi
        fi
        i=$((i + 1))
    done
    eval "$_result_var=\"\$result\""
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"

    # Skip if non-interactive
    if [[ "${OPT_YES:-0}" == "1" ]]; then
        return 0
    fi

    local hint=""
    if [[ "$default" == "y" ]]; then
        hint="(Y/n)"
    else
        hint="(y/N)"
    fi

    printf "  %s %s " "$prompt" "${DIM}${hint}${RESET}"

    local answer=""
    read -r answer

    # Default on empty
    if [[ -z "$answer" ]]; then
        answer="$default"
    fi

    case "$answer" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

prompt_path() {
    local title="$1"
    local default_path="$2"
    local _result_var="$3"

    # Non-interactive: use default
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 0 ]; then
        eval "$_result_var=\"\$default_path\""
        return 0
    fi

    printf "  %s %s: " "$title" "${DIM}[${default_path}]${RESET}"
    local answer=""
    read -r answer

    if [[ -z "$answer" ]]; then
        answer="$default_path"
    fi

    eval "$_result_var=\"\$answer\""
}

# ── Preflight checks ───────────────────────────────────────────────────────

preflight_checks() {
    detect_platform

    section "Preflight"

    # OS + architecture
    local os_label=""
    case "${DETECTED_OS}-${DETECTED_ARCH}" in
        macos-arm64)   os_label="macOS arm64 (Apple Silicon)" ;;
        macos-x86_64)  os_label="macOS x86_64 (Intel)" ;;
        linux-arm64)   os_label="Linux arm64" ;;
        linux-x86_64)  os_label="Linux x86_64" ;;
        *)             os_label="${DETECTED_OS} ${DETECTED_ARCH}" ;;
    esac
    info "OS: ${os_label} [${DETECTED_OS}/${DETECTED_ARCH}]"

    # Bash version
    info "bash ${BASH_VERSION}"

    # curl
    if command -v curl >/dev/null 2>&1; then
        info "curl available"
    else
        die "curl is required but not found. Please install curl and try again."
    fi

    # Existing installation
    local install_prefix="${OPT_PREFIX:-$DEFAULT_PREFIX}"
    if [[ -d "$install_prefix" ]]; then
        warn "Existing installation found at ${install_prefix}"
        if [[ "${OPT_YES:-0}" != "1" ]] && [ -t 0 ]; then
            if ! confirm "Overwrite existing installation?"; then
                die "Installation cancelled."
            fi
        fi
    fi

    # uv
    if command -v uv >/dev/null 2>&1; then
        local uv_ver=""
        uv_ver="$(uv --version 2>/dev/null || echo "unknown")"
        info "uv: ${uv_ver}"
    else
        warn "uv not found — will install automatically"
    fi
}

# ── Install flow ────────────────────────────────────────────────────────────

ensure_uv() {
    if command -v uv &>/dev/null; then
        return 0
    fi

    start_spinner "Installing uv..."
    if curl -LsSf "$UV_INSTALL_URL" | sh >/dev/null 2>&1; then
        export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
        stop_spinner
        info "uv installed"
    else
        stop_spinner
        die "Could not install uv. Please install it manually: https://docs.astral.sh/uv/"
    fi

    if ! command -v uv &>/dev/null; then
        die "uv was installed but not found in PATH. Please restart your shell and try again."
    fi
}

create_venv() {
    local install_dir="$1"

    start_spinner "Creating Python ${PYTHON_VERSION} virtual environment..."
    if uv venv "${install_dir}/venv" --python "$PYTHON_VERSION" --quiet 2>/dev/null; then
        stop_spinner
        info "Python ${PYTHON_VERSION} virtual environment created"
    else
        stop_spinner
        die "Could not create Python ${PYTHON_VERSION} venv. Ensure Python ${PYTHON_VERSION}+ is available.\n    Try: uv python install ${PYTHON_VERSION}"
    fi
}

install_packages() {
    local install_dir="$1" extras="$2" profile_name="$3"

    section "Installing dworkers · ${profile_name} profile"

    local spec
    if [[ "$extras" == "all" ]]; then
        spec="firefly-dworkers[all]"
    else
        spec="firefly-dworkers[${extras}]"
    fi

    start_spinner "Installing ${spec}..."
    if uv pip install "$spec" --python "${install_dir}/venv/bin/python" --quiet 2>/dev/null; then
        stop_spinner
        info "Packages installed"
    else
        stop_spinner
        die "Failed to install ${spec}. Check your network connection and try again."
    fi
}

# ── Post-install ────────────────────────────────────────────────────────────

setup_path() {
    local install_dir="$1"
    local shell_rc="${DETECTED_SHELL_RC}"

    # Create directories
    mkdir -p "${install_dir}/bin"
    mkdir -p "${HOME}/.local/bin"

    # Symlink dworkers binary
    ln -sf "${install_dir}/venv/bin/dworkers" "${HOME}/.local/bin/dworkers"

    # Write and chmod uninstall script
    write_uninstall_script "${install_dir}"
    chmod +x "${install_dir}/bin/dworkers-uninstall"

    # Symlink uninstall script
    ln -sf "${install_dir}/bin/dworkers-uninstall" "${HOME}/.local/bin/dworkers-uninstall"

    # Determine sed in-place flag for platform
    local sed_inplace
    if [[ "${DETECTED_OS}" == "macos" ]]; then
        sed_inplace=(-i '')
    else
        sed_inplace=(-i)
    fi

    # Remove existing PATH block if present, then add fresh one
    if [[ -f "$shell_rc" ]] && grep -q '# >>> dworkers >>>' "$shell_rc" 2>/dev/null; then
        sed "${sed_inplace[@]}" '/# >>> dworkers >>>/,/# <<< dworkers <<</d' "$shell_rc"
        # Clean up .bak file if created
        rm -f "${shell_rc}.bak"
    fi

    # Ensure file exists
    touch "$shell_rc"

    # Append PATH block
    {
        echo ""
        echo "# >>> dworkers >>>"
        echo "export PATH=\"${install_dir}/venv/bin:${install_dir}/bin:\${PATH}\""
        echo "# <<< dworkers <<<"
    } >> "$shell_rc"

    info "PATH configured in ${shell_rc}"
}

write_metadata() {
    local install_dir="$1" version="$2" profile="$3" extras="$4" shell_rc="$5"

    # Write version file
    printf "%s\n" "$version" > "${install_dir}/version"

    # Write env metadata file
    cat > "${install_dir}/env" <<ENVFILE
DWORKERS_VERSION=${version}
DWORKERS_PREFIX=${install_dir}
DWORKERS_PROFILE=${profile}
DWORKERS_EXTRAS=${extras}
DWORKERS_INSTALLED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DWORKERS_SHELL_RC=${shell_rc}
ENVFILE

    info "Metadata written to ${install_dir}/env"
}

write_uninstall_script() {
    local install_dir="$1"

    cat > "${install_dir}/bin/dworkers-uninstall" <<'UNINSTALL_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source metadata
if [[ -f "${SCRIPT_DIR}/../env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/../env"
else
    echo "Error: Cannot find dworkers metadata. Is dworkers installed?" >&2
    exit 1
fi

# Colors
if [[ -n "${NO_COLOR:-}" ]] || [[ "${TERM:-}" == "dumb" ]]; then
    BOLD="" RESET="" RED="" GREEN="" YELLOW="" CYAN="" DIM=""
    BOLD_WHITE="" BRIGHT_YELLOW="" BRIGHT_CYAN=""
else
    BOLD=$'\033[1m' RESET=$'\033[0m' RED=$'\033[0;31m'
    GREEN=$'\033[0;32m' YELLOW=$'\033[0;33m' CYAN=$'\033[0;36m'
    DIM=$'\033[2m' BOLD_WHITE=$'\033[1;37m'
    BRIGHT_YELLOW=$'\033[1;33m' BRIGHT_CYAN=$'\033[1;36m'
fi

# Banner
printf "%s" "${BRIGHT_YELLOW}"
cat <<'BANNER'
    .___                    __
  __| _/_  _  _____________|  | __ ___________  ______
 / __ |\ \/ \/ /  _ \_  __ \  |/ // __ \_  __ \/  ___/
/ /_/ | \     (  <_> )  | \/    <\  ___/|  | \/\___ \
\____ |  \/\_/ \____/|__|  |__|_ \\___  >__|  /____  >
     \/                         \/    \/           \/
BANNER
printf "%s\n" "${RESET}"

printf "\n  %s\n" "${BOLD}Uninstall dworkers${RESET}"
printf "  %s\n\n" "───────────────────────"

printf "  %s\n" "The following will be removed:"
printf "  %s %s\n" "${DIM}•${RESET}" "${DWORKERS_PREFIX}"
printf "  %s %s\n" "${DIM}•${RESET}" "${HOME}/.local/bin/dworkers"
printf "  %s %s\n" "${DIM}•${RESET}" "${HOME}/.local/bin/dworkers-uninstall"
printf "  %s %s\n" "${DIM}•${RESET}" "PATH entries from ${DWORKERS_SHELL_RC}"
echo ""

# Check for --yes/-y flag
AUTO_YES=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y) AUTO_YES=1 ;;
    esac
done

if [[ "$AUTO_YES" != "1" ]]; then
    printf "  %s %s " "Proceed with uninstall?" "${DIM}(y/N)${RESET}"
    read -r answer
    case "$answer" in
        [yY]|[yY][eE][sS]) ;;
        *) echo "  Cancelled."; exit 0 ;;
    esac
fi

# Remove symlinks
rm -f "${HOME}/.local/bin/dworkers"
rm -f "${HOME}/.local/bin/dworkers-uninstall"
printf "  %s %s\n" "${GREEN}✓${RESET}" "Symlinks removed"

# Remove PATH block from shell rc
if [[ -n "${DWORKERS_SHELL_RC:-}" ]] && [[ -f "${DWORKERS_SHELL_RC}" ]]; then
    # Detect platform for sed -i
    case "$(uname -s)" in
        Darwin*) sed -i '' '/# >>> dworkers >>>/,/# <<< dworkers <<</d' "${DWORKERS_SHELL_RC}" ;;
        *)       sed -i '/# >>> dworkers >>>/,/# <<< dworkers <<</d' "${DWORKERS_SHELL_RC}" ;;
    esac
    printf "  %s %s\n" "${GREEN}✓${RESET}" "PATH entries removed from ${DWORKERS_SHELL_RC}"
fi

# Remove install directory
rm -rf "${DWORKERS_PREFIX}"
printf "  %s %s\n" "${GREEN}✓${RESET}" "Installation removed"

echo ""
printf "  %s\n" "${DIM}dworkers has been uninstalled. Goodbye!${RESET}"
echo ""
UNINSTALL_SCRIPT
}

print_success() {
    local install_dir="$1" version="$2" profile="$3" extras="$4"

    echo ""
    print_banner
    echo ""

    printf "  %s\n\n" "${GREEN}✓ dworkers v${version} installed successfully!${RESET}"

    printf "  %s  %s\n" "${DIM}Location${RESET}" "${install_dir}"
    printf "  %s   %s\n" "${DIM}Profile${RESET}" "${profile}"
    printf "  %s    %s\n" "${DIM}Extras${RESET}" "${extras}"

    section "Get started"
    printf "  %s\n" "${CYAN}dworkers init${RESET}       Create a new worker project"
    printf "  %s\n" "${CYAN}dworkers serve${RESET}      Start the worker server"
    printf "  %s\n" "${CYAN}dworkers check${RESET}      Validate configuration"

    section "To uninstall"
    printf "  %s\n" "${CYAN}dworkers-uninstall${RESET}"

    echo ""
    printf "  %s\n\n" "${DIM}Docs: https://docs.fireflyresearch.com/dworkers${RESET}"
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
