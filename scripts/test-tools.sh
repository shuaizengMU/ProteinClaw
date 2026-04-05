#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — run tool connectivity harness
#
# Usage:
#   scripts/test-tools.sh                  # test all tools
#   scripts/test-tools.sh uniprot kegg     # test specific tools
#   scripts/test-tools.sh --skip-slow      # skip blast etc.
#   scripts/test-tools.sh --timeout 60     # custom timeout
# ────────────────────────────────────────────

cd "$(dirname "$0")/.."
exec uv run python -m harness.runner "$@"
