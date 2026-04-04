# ────────────────────────────────────────────
# ProteinClaw — Rust TUI hot-reload dev mode (Windows)
# Watches cli-tui source files and restarts
# the TUI automatically on every save.
# Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function ok($msg)   { Write-Host "[OK] $msg"   -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg"    -ForegroundColor Cyan }

# ── Prerequisite checks ─────────────────────
info "Checking prerequisites..."

try { $null = Get-Command cargo -ErrorAction Stop }
catch { fail "cargo not found. Install Rust: https://rustup.rs" }

if (-not (Get-Command cargo-watch -ErrorAction SilentlyContinue)) {
    info "cargo-watch not found -- installing..."
    cargo install cargo-watch
}

ok "Prerequisites met"

# ── Launch ───────────────────────────────────
info "Starting hot-reload dev mode (Ctrl+C to stop)..."
info "TUI restarts automatically on file changes."
Write-Host ""

cargo watch -s "cmd /c cls" -x "run -p cli-tui"
