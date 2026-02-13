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

# ── GitHub source URLs ──────────────────────────────────────────────────────
# These packages are not published on PyPI — install directly from GitHub.
DWORKERS_REPO="https://github.com/fireflyresearch/firefly-dworkers.git"
GENAI_REPO="https://github.com/fireflyframework/fireflyframework-genai.git"
FLYBROWSER_REPO="https://github.com/fireflyresearch/flybrowser.git"

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

CURSOR_HIDDEN=0

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

    # When piped (curl | bash), bash reads the script from stdin (fd 0).
    # We MUST NOT redirect fd 0 or bash loses the script source and hangs.
    # Instead, open /dev/tty on a separate fd (3) for interactive prompts.
    # All interactive read calls use <&3 to read from the terminal.
    if ! [ -t 0 ]; then
        if (exec 3</dev/tty) 2>/dev/null; then
            exec 3</dev/tty
        else
            exec 3<&0
            OPT_YES=1
        fi
    else
        exec 3<&0
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
}

stop_spinner() {
    if [[ -n "${SPINNER_PID:-}" ]]; then
        kill "$SPINNER_PID" 2>/dev/null || true
        wait "$SPINNER_PID" 2>/dev/null || true
        SPINNER_PID=""
        printf "\r\033[2K"
    fi
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
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 3 ]; then
        eval "$_result_var=\"0\""
        return 0
    fi

    # Hide cursor
    CURSOR_HIDDEN=1
    printf "\033[?25l"

    # Draw initial menu
    _menu_draw "$selected" "${options[@]}"

    while true; do
        # Read a single character
        local key=""
        IFS= read -rsn1 key <&3

        if [[ "$key" == "" ]]; then
            # Enter pressed
            break
        fi

        if [[ "$key" == $'\033' ]]; then
            # Escape sequence — read two more chars
            local seq1="" seq2=""
            IFS= read -rsn1 seq1 <&3
            IFS= read -rsn1 seq2 <&3
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
    CURSOR_HIDDEN=0

    eval "$_result_var=\"\$selected\""
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
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 3 ]; then
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
    CURSOR_HIDDEN=1
    printf "\033[?25l"

    # Initial draw (count lines + 1 for status bar)
    _toggle_draw "$current" "$count" "${labels[@]}" "${states[@]}"

    while true; do
        local key=""
        IFS= read -rsn1 key <&3

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
    CURSOR_HIDDEN=0

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
    read -r answer <&3

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
    if [[ "${OPT_YES:-0}" == "1" ]] || ! [ -t 3 ]; then
        eval "$_result_var=\"\$default_path\""
        return 0
    fi

    printf "  %s %s: " "$title" "${DIM}[${default_path}]${RESET}"
    local answer=""
    read -r answer <&3

    if [[ -z "$answer" ]]; then
        answer="$default_path"
    fi

    # Expand leading tilde
    answer="${answer/#\~/$HOME}"

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

    # git (needed to install packages from GitHub)
    if command -v git >/dev/null 2>&1; then
        info "git available"
    else
        die "git is required but not found. Please install git and try again."
    fi

    # Existing installation
    local install_prefix="${OPT_PREFIX:-$DEFAULT_PREFIX}"
    if [[ -d "$install_prefix" ]]; then
        warn "Existing installation found at ${install_prefix}"
        if [[ "${OPT_YES:-0}" != "1" ]] && [ -t 3 ]; then
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

show_install_error() {
    local log_file="$1"
    if [[ -f "$log_file" ]] && [[ -s "$log_file" ]]; then
        printf "\n  %s\n" "${DIM}─── last 10 lines of install log ───${RESET}"
        tail -10 "$log_file" | while IFS= read -r line; do
            printf "  %s\n" "${DIM}${line}${RESET}"
        done
        printf "  %s\n\n" "${DIM}Full log: ${log_file}${RESET}"
    fi
    die "Installation failed. See log above for details."
}

install_packages() {
    local install_dir="$1" extras="$2" profile_name="$3"
    local python="${install_dir}/venv/bin/python"
    local log_file="${install_dir}/install.log"
    local build_dir="${install_dir}/.build"

    section "Installing dworkers · ${profile_name} profile"

    # Truncate log file and create build directory
    : > "$log_file"
    mkdir -p "$build_dir"

    # ── Step 1: Install fireflyframework-genai (not on PyPI) ──
    start_spinner "Installing fireflyframework-genai..."
    if uv pip install "fireflyframework-genai[all] @ git+${GENAI_REPO}" \
        --python "$python" --quiet 2>>"$log_file"; then
        stop_spinner
        info "fireflyframework-genai installed"
    else
        stop_spinner
        fail "Failed to install fireflyframework-genai"
        show_install_error "$log_file"
    fi

    # ── Step 2: Install flybrowser if browser extra is selected (not on PyPI) ──
    if [[ "$extras" == "all" ]] || [[ "$extras" == *"browser"* ]]; then
        start_spinner "Installing flybrowser..."
        if uv pip install "flybrowser @ git+${FLYBROWSER_REPO}" \
            --python "$python" --quiet 2>>"$log_file"; then
            stop_spinner
            info "flybrowser installed"
        else
            stop_spinner
            fail "Failed to install flybrowser"
            show_install_error "$log_file"
        fi
    fi

    # ── Step 3: Download and install firefly-dworkers from source ──
    # We download the source tarball instead of using git+URL because
    # pyproject.toml contains [tool.uv.sources] with local dev paths
    # that uv_build tries to resolve during build — causing failures.
    # Stripping that section lets uv resolve deps from what's already
    # installed (steps 1-2) or from PyPI.
    start_spinner "Downloading firefly-dworkers source..."
    local tarball_url="${DWORKERS_REPO%.git}/archive/refs/heads/main.tar.gz"
    if curl -fsSL "$tarball_url" | tar -xz -C "$build_dir" 2>>"$log_file"; then
        stop_spinner
        info "Source downloaded"
    else
        stop_spinner
        fail "Failed to download firefly-dworkers source"
        show_install_error "$log_file"
    fi

    local src_dir="${build_dir}/firefly-dworkers-main"

    # Patch pyproject.toml for clean install:
    # 1. Strip [tool.uv.sources] — local dev paths that break remote builds
    # 2. Ensure [tool.uv.build-backend] lists all source packages so the
    #    wheel includes firefly_dworkers_cli and firefly_dworkers_server
    "$python" -c "
import re, sys
p = sys.argv[1]
with open(p) as f:
    text = f.read()
# Strip [tool.uv.sources] section
text = re.sub(r'\n*\[tool\.uv\.sources\][^\[]*', '\n\n', text)
# Ensure build-backend config exists
if '[tool.uv.build-backend]' not in text:
    build_backend_cfg = '''
[tool.uv.build-backend]
module-name = [\"firefly_dworkers\", \"firefly_dworkers_cli\", \"firefly_dworkers_server\"]
module-root = \"src\"
'''
    text = text.replace('[build-system]', build_backend_cfg + '\n[build-system]')
with open(p, 'w') as f:
    f.write(text)
" "${src_dir}/pyproject.toml"

    local spec
    if [[ "$extras" == "all" ]]; then
        spec="${src_dir}[all]"
    else
        spec="${src_dir}[${extras}]"
    fi

    start_spinner "Installing firefly-dworkers[${extras}]..."
    if uv pip install "$spec" \
        --python "$python" --quiet 2>>"$log_file"; then
        stop_spinner
        info "Packages installed"
    else
        stop_spinner
        fail "Failed to install firefly-dworkers[${extras}]"
        show_install_error "$log_file"
    fi

    # Clean up build artifacts
    rm -rf "$build_dir"
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

# Resolve symlinks to find the real script location (not the symlink in ~/.local/bin)
SCRIPT_PATH="${BASH_SOURCE[0]}"
while [[ -L "$SCRIPT_PATH" ]]; do
    LINK_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    # Handle relative symlink targets
    [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="${LINK_DIR}/${SCRIPT_PATH}"
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

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
    printf "  %s\n\n" "${DIM}Docs: https://github.com/fireflyresearch/firefly-dworkers/tree/main/docs${RESET}"
}

# ── Uninstall flow ──────────────────────────────────────────────────────────

run_uninstall() {
    detect_platform
    print_banner

    # Find existing installation
    local install_dir=""
    if [[ -n "${OPT_PREFIX:-}" ]]; then
        install_dir="$OPT_PREFIX"
    elif [[ -d "$DEFAULT_PREFIX" ]]; then
        install_dir="$DEFAULT_PREFIX"
    elif [[ -L "${HOME}/.local/bin/dworkers" ]]; then
        # Resolve from symlink: ~/.local/bin/dworkers -> <prefix>/venv/bin/dworkers
        local link_target=""
        link_target="$(readlink "${HOME}/.local/bin/dworkers" 2>/dev/null || true)"
        if [[ -n "$link_target" ]]; then
            # Strip /venv/bin/dworkers to get prefix
            install_dir="${link_target%/venv/bin/dworkers}"
        fi
    fi

    if [[ -z "$install_dir" ]] || [[ ! -d "$install_dir" ]]; then
        die "No dworkers installation found. Nothing to uninstall."
    fi

    # Load metadata
    local dw_version="" dw_profile="" dw_extras="" dw_shell_rc=""
    if [[ -f "${install_dir}/env" ]]; then
        # shellcheck disable=SC1090
        source "${install_dir}/env"
        dw_version="${DWORKERS_VERSION:-unknown}"
        dw_profile="${DWORKERS_PROFILE:-unknown}"
        dw_extras="${DWORKERS_EXTRAS:-unknown}"
        dw_shell_rc="${DWORKERS_SHELL_RC:-}"
    else
        dw_version="unknown"
        dw_profile="unknown"
        dw_extras="unknown"
        dw_shell_rc="${DETECTED_SHELL_RC:-}"
    fi

    section "Uninstall dworkers"
    printf "\n  %s\n" "The following will be removed:"
    printf "  %s %s\n" "${DIM}•${RESET}" "${install_dir}"
    printf "  %s %s\n" "${DIM}•${RESET}" "${HOME}/.local/bin/dworkers"
    printf "  %s %s\n" "${DIM}•${RESET}" "${HOME}/.local/bin/dworkers-uninstall"
    if [[ -n "$dw_shell_rc" ]]; then
        printf "  %s %s\n" "${DIM}•${RESET}" "PATH entries from ${dw_shell_rc}"
    fi
    echo ""

    if ! confirm "Proceed with uninstall?"; then
        printf "\n  Cancelled.\n\n"
        exit 0
    fi

    # Remove symlinks
    rm -f "${HOME}/.local/bin/dworkers"
    rm -f "${HOME}/.local/bin/dworkers-uninstall"
    info "Symlinks removed"

    # Remove PATH block from shell rc
    if [[ -n "$dw_shell_rc" ]] && [[ -f "$dw_shell_rc" ]]; then
        local sed_inplace
        if [[ "${DETECTED_OS}" == "macos" ]]; then
            sed_inplace=(-i '')
        else
            sed_inplace=(-i)
        fi
        sed "${sed_inplace[@]}" '/# >>> dworkers >>>/,/# <<< dworkers <<</d' "$dw_shell_rc"
        rm -f "${dw_shell_rc}.bak"
        info "PATH entries removed from ${dw_shell_rc}"
    fi

    # Remove install directory
    rm -rf "$install_dir"
    info "Installation removed from ${install_dir}"

    echo ""
    printf "  %s\n" "${DIM}dworkers has been uninstalled. Goodbye!${RESET}"
    echo ""
}

# ── Test mode guard ──────────────────────────────────────────────────────────
# When sourced with DWORKERS_TEST_MODE=1, stop here so tests can call
# individual functions without triggering the main installer flow.

if [[ "${DWORKERS_TEST_MODE:-}" == "1" ]]; then
    return 0 2>/dev/null || true
fi

# ── Data arrays ──────────────────────────────────────────────────────────────

EXTRAS_LIST=(
    "web:Web search & scraping"
    "sharepoint:SharePoint integration"
    "google:Google Drive / Docs / Sheets"
    "confluence:Confluence wiki"
    "jira:Jira task management"
    "slack:Slack messaging"
    "teams:Microsoft Teams"
    "email:Email via SMTP"
    "data:openpyxl + pandas"
    "server:FastAPI REST server"
    "browser:FlyBrowser (Playwright)"
    "presentation:PowerPoint generation"
    "pdf:PDF from Markdown/HTML"
    "cli:Typer + Rich CLI"
)

PROFILE_OPTIONS=(
    "Minimal        Core library + CLI only"
    "Analyst        + web, data, presentation — for research workflows"
    "Server         + FastAPI server, CLI, web — for API deployments"
    "Full           All 14 extras — everything included"
    "Custom         Pick individual extras"
)

PROFILE_NAMES=(minimal analyst server full custom)

# ── Profile selection ────────────────────────────────────────────────────────

select_profile() {
    # $1 = profile result var, $2 = extras result var
    local _sp_profile_var=$1
    local _sp_extras_var=$2

    # If profile was passed via flag
    if [[ -n "$OPT_PROFILE" ]]; then
        eval "$_sp_profile_var=\"\$OPT_PROFILE\""
        if [[ "$OPT_PROFILE" == "custom" ]] && [[ "$OPT_YES" == "1" ]]; then
            eval "$_sp_extras_var=\"all\""
        elif [[ "$OPT_PROFILE" != "custom" ]]; then
            local _sp_e
            _sp_e="$(profile_to_extras "$OPT_PROFILE")"
            eval "$_sp_extras_var=\"\$_sp_e\""
        fi
        return
    fi

    section "Choose a profile"
    printf "\n"

    local choice=0
    menu_select choice "${PROFILE_OPTIONS[@]}"

    local _sp_name="${PROFILE_NAMES[$choice]}"
    eval "$_sp_profile_var=\"\$_sp_name\""

    if [[ "$_sp_name" == "custom" ]]; then
        printf "\n"
        section "Select extras"
        printf "  ${DIM}Space to toggle, Enter to confirm, 'a' to select all${RESET}\n\n"

        local selected_extras=""
        toggle_picker selected_extras "${EXTRAS_LIST[@]}"
        eval "$_sp_extras_var=\"\$selected_extras\""
    else
        local _sp_mapped
        _sp_mapped="$(profile_to_extras "$_sp_name")"
        eval "$_sp_extras_var=\"\$_sp_mapped\""
    fi
}

# ── Cleanup trap ─────────────────────────────────────────────────────────────

cleanup() {
    stop_spinner 2>/dev/null || true
    if [[ "$CURSOR_HIDDEN" == "1" ]]; then
        printf "\033[?25h" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Main install flow ────────────────────────────────────────────────────────

run_install() {
    local install_dir profile extras

    # 1. Welcome
    print_welcome

    # 2-3. Preflight
    preflight_checks

    # 4. Install location
    local install_dir=""
    prompt_path "Install location" "$DEFAULT_PREFIX" install_dir

    # Override with flag if provided
    if [[ -n "$OPT_PREFIX" ]]; then
        install_dir="$OPT_PREFIX"
    fi

    # 5. Bootstrap uv
    ensure_uv

    # 6. Create venv
    create_venv "$install_dir"

    # 7. Profile selection
    local profile="" extras=""
    select_profile profile extras

    if [[ -z "$extras" ]]; then
        die "No extras selected. At minimum, the 'cli' extra is required."
    fi

    # Ensure cli is always included
    if [[ "$extras" != "all" ]] && [[ "$extras" != *"cli"* ]]; then
        extras="cli,${extras}"
    fi

    # 8. Install packages
    install_packages "$install_dir" "$extras" "$profile"

    # 9-10. PATH + symlinks
    setup_path "$install_dir"

    # 11. Metadata
    write_metadata "$install_dir" "$DWORKERS_VERSION" "$profile" "$extras" "$DETECTED_SHELL_RC"

    # 12. Success
    print_success "$install_dir" "$DWORKERS_VERSION" "$profile" "$extras"
}

# ── Entry point ──────────────────────────────────────────────────────────────

# Detect interactive mode
INTERACTIVE=1
if [[ ! -t 0 ]] || [[ ! -t 1 ]]; then
    INTERACTIVE=0
fi

parse_args "$@"

if [[ "$OPT_UNINSTALL" == "1" ]]; then
    run_uninstall
else
    run_install
fi
