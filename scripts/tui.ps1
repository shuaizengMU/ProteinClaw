# ────────────────────────────────────────────
# ProteinClaw — TUI launcher (Windows)
# Builds and runs the Ratatui terminal UI.
# Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Colour helpers ──────────────────────────
function ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg" -ForegroundColor Cyan }

# ── Prerequisite checks ─────────────────────
info "Checking prerequisites..."

try { $null = Get-Command cargo -ErrorAction Stop }
catch { fail "cargo not found. Install: https://rustup.rs" }

try { $null = Get-Command uv -ErrorAction Stop }
catch { fail "uv not found. Install: winget install astral-sh.uv" }

ok "Prerequisites met"

# ── Build TUI ───────────────────────────────
info "Building proteinclaw-tui..."
cargo build -p proteinclaw-tui --release
ok "Build complete"

# ── Launch ───────────────────────────────────
info "Starting ProteinClaw TUI..."
& .\target\release\proteinclaw-tui.exe
