# ────────────────────────────────────────────
# ProteinClaw — Frontend dev server (Windows)
# Starts the Vite dev server for the React
# frontend. Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function ok($msg)   { Write-Host "[OK] $msg"   -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg"    -ForegroundColor Cyan }

# ── Prerequisite checks ─────────────────────
info "Checking prerequisites..."

try { $null = Get-Command node -ErrorAction Stop }
catch { fail "node not found. Install Node.js: https://nodejs.org" }

try { $null = Get-Command npm -ErrorAction Stop }
catch { fail "npm not found. Install Node.js: https://nodejs.org" }

ok "Prerequisites met"

# ── Install dependencies if needed ──────────
if (-not (Test-Path "frontend\node_modules")) {
    info "node_modules not found -- running npm install..."
    npm install --prefix frontend
}

# ── Launch ───────────────────────────────────
info "Starting frontend dev server (Ctrl+C to stop)..."
info "URL: http://localhost:5173"
Write-Host ""

npm run dev --prefix frontend
