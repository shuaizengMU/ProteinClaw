#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — run test suite
# Usage: scripts/test.sh [pytest args...]
# Examples:
#   scripts/test.sh
#   scripts/test.sh -x -v
#   scripts/test.sh tests/proteinclaw/test_api.py
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

command -v uv >/dev/null 2>&1 || fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

info "Syncing dev dependencies..."
uv sync --extra dev

info "Running tests..."
uv run pytest "$@"
ok "All tests passed"
