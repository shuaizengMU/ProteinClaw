#!/usr/bin/env bash
set -eu

# ────────────────────────────────────────────
# ProteinClaw — macOS desktop build script
# Run from the project root.
# ────────────────────────────────────────────

UV_VERSION="0.6.6"

# ── Colour helpers ──────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── 1. Prerequisite checks ──────────────────
info "Checking prerequisites..."

command -v rustc >/dev/null 2>&1 || \
  fail "rustc not found. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

command -v node >/dev/null 2>&1 || \
  fail "node not found. Install Node.js: brew install node  (or https://nodejs.org)"

command -v npm >/dev/null 2>&1 || \
  fail "npm not found. Install Node.js: brew install node  (or https://nodejs.org)"

cargo tauri --version >/dev/null 2>&1 || \
  fail "cargo tauri not found. Install: cargo install tauri-cli"

ok "All prerequisites met"

# ── 2. Download uv sidecar binary ───────────
ARCH=$(uname -m)
case "$ARCH" in
  arm64)  TRIPLE="aarch64-apple-darwin" ;;
  x86_64) TRIPLE="x86_64-apple-darwin" ;;
  *)      fail "Unsupported architecture: $ARCH" ;;
esac

DEST="src-tauri/binaries/uv-${TRIPLE}"
mkdir -p src-tauri/binaries

if [[ -f "$DEST" ]]; then
  ok "uv sidecar already present: $DEST (skipping download)"
else
  info "Downloading uv ${UV_VERSION} for ${TRIPLE}..."
  ARCHIVE="uv-${TRIPLE}.tar.gz"
  URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${ARCHIVE}"
  TMP=$(mktemp -d)
  curl -fsSL "$URL" -o "${TMP}/${ARCHIVE}" || fail "Failed to download uv from ${URL}"
  tar -xzf "${TMP}/${ARCHIVE}" --strip-components=1 -C "${TMP}" "uv-${TRIPLE}/uv" || \
    fail "Failed to extract uv binary from archive"
  mv "${TMP}/uv" "$DEST"
  chmod +x "$DEST"
  rm -rf "$TMP"
  ok "uv sidecar downloaded: $DEST"
fi

# ── 3. Build frontend ────────────────────────
info "Building frontend..."
(cd frontend && npm install && npm run build)
ok "Frontend built"

# ── 4. Tauri build ───────────────────────────
info "Running cargo tauri build (this takes a few minutes)..."
cargo tauri build
ok "Tauri build complete"

# ── 5. Print artifact path ───────────────────
DMG=$(find src-tauri/target/release/bundle/dmg -name "*.dmg" 2>/dev/null | head -1)
if [[ -n "$DMG" ]]; then
  echo ""
  echo -e "${BOLD}Artifact:${RESET} $(realpath "$DMG")"
else
  echo "Build succeeded but no .dmg found in src-tauri/target/release/bundle/dmg/"
fi
