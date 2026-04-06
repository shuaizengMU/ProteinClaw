#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# ProteinClaw installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/shuaizengMU/ProteinClaw/main/install.sh | bash
#
# What this script does:
#   1. Installs uv (if not already installed)
#   2. Installs the ProteinClaw Python backend via uv tool install
#   3. Downloads the proteinclaw-tui binary for your platform
#   4. Places it in ~/.local/bin and adds it to PATH if needed
# ─────────────────────────────────────────────────────────────────────────────

REPO="shuaizengMU/ProteinClaw"
BIN_NAME="proteinclaw-tui"
INSTALL_DIR="${HOME}/.local/bin"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗ Error:${RESET} $*" >&2; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }

echo ""
echo -e "${BOLD}ProteinClaw Installer${RESET}"
echo "──────────────────────────────────────────"
echo ""

# ── 1. Detect OS and architecture ────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      fail "Unsupported OS: $OS. Windows users: run install.ps1 instead." ;;
esac

case "$ARCH" in
  arm64|aarch64) ARCH_LABEL="arm64" ;;
  x86_64)        ARCH_LABEL="x86_64" ;;
  *)             fail "Unsupported architecture: $ARCH" ;;
esac

ok "Detected platform: ${PLATFORM}-${ARCH_LABEL}"

# ── 2. Install uv (if not present) ───────────────────────────────────────────
if command -v uv >/dev/null 2>&1; then
  ok "uv already installed: $(uv --version)"
else
  info "Installing uv..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
  # Add uv to PATH for the rest of this script
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  command -v uv >/dev/null 2>&1 || fail "uv installation failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
  ok "uv installed: $(uv --version)"
fi

# ── 3. Install Python backend ─────────────────────────────────────────────────
info "Installing ProteinClaw Python backend..."
uv tool install "git+https://github.com/${REPO}.git" --force
ok "Python backend installed"

# ── 4. Download proteinclaw-tui binary ───────────────────────────────────────
ASSET="${BIN_NAME}-${PLATFORM}-${ARCH_LABEL}"
LATEST_URL="https://github.com/${REPO}/releases/download/v0.1.0-beta/${ASSET}"

info "Downloading ${BIN_NAME} (${PLATFORM}-${ARCH_LABEL})..."

mkdir -p "$INSTALL_DIR"
TMP=$(mktemp)
TUI_INSTALLED=false

if curl -fsSL --output "$TMP" "$LATEST_URL" 2>/dev/null; then
  chmod +x "$TMP"
  mv "$TMP" "${INSTALL_DIR}/${BIN_NAME}"
  ok "Downloaded ${BIN_NAME} → ${INSTALL_DIR}/${BIN_NAME}"
  TUI_INSTALLED=true
else
  rm -f "$TMP"
  warn "${BIN_NAME} binary not yet available for ${PLATFORM}-${ARCH_LABEL}."
  warn "To build the TUI from source:"
  warn "  git clone https://github.com/${REPO}.git && cd ProteinClaw && bash scripts/build-tui.sh"
fi

# ── 5. Add ~/.local/bin to PATH if needed ────────────────────────────────────
add_to_path() {
  local shell_rc="$1"
  if [[ -f "$shell_rc" ]] && grep -q 'local/bin' "$shell_rc" 2>/dev/null; then
    return 0  # already present
  fi
  echo '' >> "$shell_rc"
  echo '# Added by ProteinClaw installer' >> "$shell_rc"
  echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "$shell_rc"
}

if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
  warn "${INSTALL_DIR} is not in your PATH. Adding it..."
  SHELL_NAME="$(basename "${SHELL:-}")"
  case "$SHELL_NAME" in
    zsh)  add_to_path "${HOME}/.zshrc";  warn "Run: source ~/.zshrc" ;;
    bash) add_to_path "${HOME}/.bashrc"; warn "Run: source ~/.bashrc" ;;
    fish) fish -c "fish_add_path ${INSTALL_DIR}" 2>/dev/null || true ;;
    *)    warn "Add ${INSTALL_DIR} to your PATH manually." ;;
  esac
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}──────────────────────────────────────────${RESET}"
echo -e "${GREEN}${BOLD}ProteinClaw installed successfully!${RESET}"
echo ""
if [[ "$TUI_INSTALLED" == "true" ]]; then
  echo "  Run:  proteinclaw-tui"
else
  echo "  Run:  proteinclaw server    # start the backend"
  echo "        proteinclaw query \"<question>\""
fi
echo ""
echo "  On first launch, a setup wizard will prompt for your API key."
echo -e "${BOLD}──────────────────────────────────────────${RESET}"
echo ""
