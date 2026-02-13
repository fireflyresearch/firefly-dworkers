#!/usr/bin/env bash
# Verification harness for install.sh
# Usage: bash tests/test_install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        printf "  \033[0;32m✓\033[0m %s\n" "$desc"
        ((PASS++)) || true
    else
        printf "  \033[0;31m✗\033[0m %s\n    expected: %s\n    actual:   %s\n" "$desc" "$expected" "$actual"
        ((FAIL++)) || true
    fi
}

assert_contains() {
    local desc="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        printf "  \033[0;32m✓\033[0m %s\n" "$desc"
        ((PASS++)) || true
    else
        printf "  \033[0;31m✗\033[0m %s\n    expected to contain: %s\n    actual: %s\n" "$desc" "$needle" "$haystack"
        ((FAIL++)) || true
    fi
}

assert_nonzero() {
    local desc="$1" value="$2"
    if [[ -n "$value" ]]; then
        printf "  \033[0;32m✓\033[0m %s\n" "$desc"
        ((PASS++)) || true
    else
        printf "  \033[0;31m✗\033[0m %s (was empty)\n" "$desc"
        ((FAIL++)) || true
    fi
}

# Source install.sh in test mode (no execution)
export DWORKERS_TEST_MODE=1
source "${SCRIPT_DIR}/install.sh"

echo ""
echo "  install.sh verification"
echo "  ───────────────────────"
echo ""

# --- Argument parsing ---
echo "  Argument parsing"
echo "  ────────────────"

parse_args --yes --prefix /tmp/dw --profile analyst
assert_eq "parse --yes" "1" "$OPT_YES"
assert_eq "parse --prefix" "/tmp/dw" "$OPT_PREFIX"
assert_eq "parse --profile" "analyst" "$OPT_PROFILE"
assert_eq "parse --uninstall default" "0" "$OPT_UNINSTALL"

parse_args --uninstall --yes
assert_eq "parse --uninstall" "1" "$OPT_UNINSTALL"
assert_eq "parse --yes with uninstall" "1" "$OPT_YES"

echo ""

# --- Profile mapping ---
echo "  Profile mapping"
echo "  ───────────────"

assert_eq "minimal profile" "cli" "$(profile_to_extras minimal)"
assert_eq "analyst profile" "cli,web,data,presentation" "$(profile_to_extras analyst)"
assert_eq "server profile" "cli,web,server" "$(profile_to_extras server)"
assert_eq "full profile" "all" "$(profile_to_extras full)"

echo ""

# --- Platform detection ---
echo "  Platform detection"
echo "  ──────────────────"

detect_platform
assert_nonzero "OS detected" "$DETECTED_OS"
assert_nonzero "Arch detected" "$DETECTED_ARCH"

echo ""

# --- Summary ---
echo "  ───────────────────────"
printf "  %d passed, %d failed\n\n" "$PASS" "$FAIL"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
