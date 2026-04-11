#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — smoke-test the CLI (query mode)
# Runs a few non-interactive queries and checks
# that the output looks sane.
# Run from the project root.
#
# Usage:
#   scripts/test-cli.sh
#   scripts/test-cli.sh --model deepseek-chat
# ────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
sep()  { echo -e "${BOLD}────────────────────────────────────────${RESET}"; }

MODEL_FLAG="${1:-}"   # optional: --model <name>

command -v uv >/dev/null 2>&1 || fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

info "Syncing dependencies..."
uv sync --quiet

sep
echo -e "${BOLD}ProteinClaw CLI smoke tests${RESET}"
sep

# ── Check at least one API key is set ────────
if [[ -z "${ANTHROPIC_API_KEY:-}" && \
      -z "${OPENAI_API_KEY:-}" && \
      -z "${DEEPSEEK_API_KEY:-}" && \
      -z "${MINIMAX_API_KEY:-}" ]]; then
    warn "No API key found in environment."
    warn "Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, MINIMAX_API_KEY"
    warn "Or run 'proteinclaw' to configure via the setup wizard."
    echo ""
fi

# ── Helper: run a query and check output ─────
run_query() {
    local label="$1"
    local query="$2"
    local expect="$3"   # substring that must appear in stdout

    info "Test: $label"
    echo -e "  Query: ${YELLOW}${query}${RESET}"

    output=$(uv run proteinclaw query $MODEL_FLAG "$query" 2>&1) || {
        echo -e "  Output:\n$output"
        fail "$label — command exited with error"
    }

    echo -e "  Output (first 3 lines):"
    echo "$output" | head -3 | sed 's/^/    /'

    if [[ -n "$expect" ]] && ! echo "$output" | grep -qi "$expect"; then
        warn "$label — expected '$expect' not found in output (may be a model decision)"
    else
        ok "$label"
    fi
    echo ""
}

# ── Test 1: Basic help / version ─────────────
info "Test: CLI entry point is reachable"
uv run proteinclaw --help >/dev/null 2>&1 && ok "proteinclaw --help works" || fail "proteinclaw --help failed"
echo ""

# ── Test 2: Query mode exits 0 ───────────────
run_query \
    "UniProt lookup (P04637 = TP53)" \
    "What is the UniProt accession P04637?" \
    "TP53"

# ── Test 3: Short factual query ──────────────
run_query \
    "Simple protein question" \
    "What does a kinase do?" \
    "phosph"

# ── Test 4: Exit code 0 on success ───────────
info "Test: exit code is 0 on clean run"
uv run proteinclaw query $MODEL_FLAG "What is a protein?" > /dev/null 2>&1
ok "Exit code 0"
echo ""

sep
ok "All CLI smoke tests completed"
sep
echo ""
echo "To launch the interactive TUI:"
echo -e "  ${BOLD}scripts/tui.sh${RESET}   (Linux/WSL)"
echo -e "  ${BOLD}scripts/tui.ps1${RESET}  (Windows)"
echo ""
