# ────────────────────────────────────────────
# ProteinClaw — local dev server (Windows)
# Starts the Python backend (port 8000) and the
# Vite frontend dev server (port 5173) in parallel.
# Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Colour helpers ──────────────────────────
function ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg" -ForegroundColor Cyan }

# ── Prerequisite checks ──────────────────────
info "Checking prerequisites..."

try { $null = Get-Command uv   -ErrorAction Stop }
catch { fail "uv not found. Install: winget install astral-sh.uv" }

try { $null = Get-Command node -ErrorAction Stop }
catch { fail "node not found. Install: winget install OpenJS.NodeJS" }

try { $null = Get-Command npm  -ErrorAction Stop }
catch { fail "npm not found. Install: winget install OpenJS.NodeJS" }

ok "Prerequisites met"

# ── Install dependencies ─────────────────────
info "Syncing Python dependencies..."
uv sync --extra dev

info "Installing frontend dependencies..."
Push-Location frontend
try { npm install --silent }
finally { Pop-Location }

ok "Dependencies ready"

# ── Start servers ────────────────────────────
info "Starting Python backend on http://127.0.0.1:8000 ..."
$backend = Start-Process -FilePath "cmd" `
    -ArgumentList "/c", "uv run uvicorn proteinclaw.server.main:app --host 127.0.0.1 --port 8000 --reload" `
    -PassThru -NoNewWindow

info "Starting Vite frontend on http://localhost:5173 ..."
$frontend = Start-Process -FilePath "cmd" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory (Join-Path (Get-Location) "frontend") `
    -PassThru -NoNewWindow

Write-Host ""
Write-Host "Dev servers running. Press Ctrl+C to stop." -ForegroundColor White
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""

# ── Wait and handle Ctrl+C ───────────────────
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    info "Shutting down..."
    if ($backend  -and -not $backend.HasExited)  { Stop-Process -Id $backend.Id  -Force -ErrorAction SilentlyContinue }
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
}
