#!/usr/bin/env bash
set -euo pipefail
set -m

# ────────────────────────────────────────────
# ProteinClaw — Python backend
# Starts the uvicorn server on port 8000.
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
command -v uv >/dev/null 2>&1 || fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
ok "Prerequisites met"

# ── Install dependencies if needed ──────────
info "Syncing Python dependencies..."
uv sync --extra dev
ok "Dependencies ready"

# ── Start backend ────────────────────────────
info "Starting Python backend on http://127.0.0.1:8000 (Ctrl+C to stop)..."
echo ""
exec uv run uvicorn proteinclaw.server.main:app \
    --host 127.0.0.1 --port 8000 --reload
