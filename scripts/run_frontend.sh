#!/usr/bin/env bash
set -euo pipefail
set -m  # enable job control so each background job gets its own process group

# ────────────────────────────────────────────
# ProteinClaw — Desktop app dev mode
# Launches the Tauri app window (auto-starts Vite internally).
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
command -v cargo >/dev/null 2>&1 || fail "cargo not found. Install: https://rustup.rs"
command -v npm   >/dev/null 2>&1 || fail "npm not found. Install: brew install node"
cargo tauri --version >/dev/null 2>&1 || fail "tauri-cli not found. Run: cargo install tauri-cli"
ok "Prerequisites met"

# ── Install dependencies if needed ──────────
info "Installing frontend dependencies..."
(cd frontend && npm install --silent)
ok "Dependencies ready"

# ── Launch Tauri app window ───────────────────
info "Launching ProteinClaw desktop app..."
echo ""
cargo tauri dev
