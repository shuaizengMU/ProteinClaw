#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — TUI launcher (Linux / WSL)
# Builds and runs the Ratatui terminal UI.
# Run from the project root.
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── Prerequisite checks ─────────────────────
info "Checking prerequisites..."

command -v cargo >/dev/null 2>&1 || fail "cargo not found. Install: https://rustup.rs"
command -v uv    >/dev/null 2>&1 || fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

ok "Prerequisites met"

# ── Build TUI ───────────────────────────────
info "Building proteinclaw-tui..."
cargo build -p proteinclaw-tui --release
ok "Build complete"

# ── Launch ───────────────────────────────────
info "Starting ProteinClaw TUI..."
exec ./target/release/proteinclaw-tui
