#!/usr/bin/env bash
set -eu

# ────────────────────────────────────────────
# ProteinClaw — Rust TUI hot-reload dev mode
# Watches cli-tui source files and restarts
# the TUI automatically on every save.
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
command -v cargo       >/dev/null 2>&1 || fail "cargo not found. Install Rust: https://rustup.rs"
command -v cargo-watch >/dev/null 2>&1 || {
    info "cargo-watch not found — installing..."
    cargo install cargo-watch
}
ok "Prerequisites met"

# ── Launch ───────────────────────────────────
info "Starting hot-reload dev mode (Ctrl+C to stop)..."
info "TUI restarts automatically on file changes."
echo ""

exec cargo watch \
    -w cli-tui/src \
    -w cli-tui/Cargo.toml \
    -s "reset" \
    -x "run -p cli-tui"
