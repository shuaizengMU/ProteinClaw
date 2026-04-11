#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — build the Rust TUI (cli-tui)
# Run from the project root.
# Output: target/release/proteinclaw-tui
# ────────────────────────────────────────────

# ── Colour helpers ──────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── 1. Prerequisite check ───────────────────
command -v cargo >/dev/null 2>&1 || \
  fail "cargo not found. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

ok "cargo found: $(cargo --version)"

# ── 2. Build ────────────────────────────────
info "Building proteinclaw-tui (release)..."
cargo build --release -p cli-tui
ok "Build complete"

# ── 3. Print artifact path ───────────────────
BIN="target/release/proteinclaw-tui"
echo ""
echo -e "${BOLD}Artifact:${RESET} $(realpath "$BIN")"
echo ""
echo "To install globally:"
echo "  cp $BIN ~/.local/bin/proteinclaw-tui"
