# ────────────────────────────────────────────
# ProteinClaw — TUI launcher (Windows)
# Runs the React/Ink TUI via Bun.
# Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Colour helpers ──────────────────────────
function ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg" -ForegroundColor Cyan }

# ── 1. Prerequisite checks ──────────────────
info "Checking prerequisites..."

try { $null = Get-Command bun -ErrorAction Stop }
catch { fail "bun not found. Install: https://bun.sh" }

try { $null = Get-Command python -ErrorAction Stop }
catch {
    try { $null = Get-Command python3 -ErrorAction Stop }
    catch { fail "python / python3 not found. Make sure Python is installed and on PATH." }
}

ok "Prerequisites met"

# ── 2. Launch ────────────────────────────────
info "Starting ProteinClaw TUI..."
Set-Location tui
bun run src/main.tsx
