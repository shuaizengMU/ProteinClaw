# ────────────────────────────────────────────
# ProteinClaw — GUI dev launcher (Windows)
# Starts the Tauri desktop app in development mode.
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

try { $null = Get-Command cargo -ErrorAction Stop }
catch { fail "cargo not found. Install Rust: https://rustup.rs" }

try { $null = Get-Command node -ErrorAction Stop }
catch { fail "node not found. Install: winget install OpenJS.NodeJS" }

try { $null = Get-Command uv -ErrorAction Stop }
catch { fail "uv not found. Install: winget install astral-sh.uv" }

$tauriCheck = cargo tauri --version 2>&1
if ($LASTEXITCODE -ne 0) { fail "cargo-tauri not found. Run: cargo install tauri-cli" }

ok "Prerequisites met"

# ── Install dependencies ─────────────────────
info "Syncing Python dependencies..."
uv sync

info "Installing frontend dependencies..."
Push-Location frontend
try { npm install --silent }
finally { Pop-Location }

ok "Dependencies ready"

# ── Launch Tauri dev ─────────────────────────
info "Starting ProteinClaw GUI (Tauri dev mode)..."
cargo tauri dev
