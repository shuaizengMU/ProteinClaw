#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — TUI launcher (Linux / WSL)
# Runs the React/Ink terminal UI via Bun.
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
info "Checking prerequisites..."

command -v bun    >/dev/null 2>&1 || fail "bun not found. Install: curl -fsSL https://bun.sh/install | bash"
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 \
    || fail "python not found. Make sure Python is installed and on PATH."

ok "Prerequisites met"

# ── Install TUI dependencies if needed ──────
if [[ ! -d tui/node_modules ]]; then
    info "Installing TUI dependencies..."
    (cd tui && bun install --silent)
    ok "Dependencies ready"
fi

# ── Launch ───────────────────────────────────
info "Starting ProteinClaw TUI..."
exec bun run tui/src/main.tsx
