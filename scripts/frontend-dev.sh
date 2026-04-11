#!/usr/bin/env bash
set -eu

# ────────────────────────────────────────────
# ProteinClaw — Frontend dev server
# Starts the Vite dev server for the React
# frontend. Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
command -v node >/dev/null 2>&1 || fail "node not found. Install Node.js: https://nodejs.org"
command -v npm  >/dev/null 2>&1 || fail "npm not found. Install Node.js: https://nodejs.org"
ok "Prerequisites met"

# ── Install dependencies if needed ──────────
if [ ! -d "frontend/node_modules" ]; then
    info "node_modules not found — running npm install..."
    npm install --prefix frontend
fi

# ── Launch ───────────────────────────────────
info "Starting frontend dev server (Ctrl+C to stop)..."
info "URL: http://localhost:5173"
echo ""

exec npm run dev --prefix frontend
