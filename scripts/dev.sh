#!/usr/bin/env bash
set -euo pipefail
set -m  # enable job control so each background job gets its own process group

# ────────────────────────────────────────────
# ProteinClaw — local dev server
# Starts the Python backend (port 8000) and the
# Vite frontend dev server (port 5173) in parallel.
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
command -v uv   >/dev/null 2>&1 || fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v node >/dev/null 2>&1 || fail "node not found. Install: brew install node"
command -v npm  >/dev/null 2>&1 || fail "npm not found. Install: brew install node"
ok "Prerequisites met"

# ── Install dependencies if needed ──────────
info "Syncing Python dependencies..."
uv sync --extra dev
info "Installing frontend dependencies..."
(cd frontend && npm install --silent)
ok "Dependencies ready"

# ── Start servers ────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    info "Shutting down..."
    # Kill the entire process group (covers uv→uvicorn→reload-worker chain)
    [[ -n "$BACKEND_PID"  ]] && kill -- -"$BACKEND_PID"  2>/dev/null || true
    [[ -n "$FRONTEND_PID" ]] && kill -- -"$FRONTEND_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup INT TERM

info "Starting Python backend on http://127.0.0.1:8000 ..."
uv run uvicorn proteinclaw.server.main:app \
    --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

info "Starting Vite frontend on http://localhost:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo -e "${BOLD}Dev servers running. Press Ctrl+C to stop.${RESET}"
echo -e "  Backend:  http://127.0.0.1:8000"
echo -e "  Frontend: http://localhost:5173"
echo ""

wait
