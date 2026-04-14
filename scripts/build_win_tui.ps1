# ────────────────────────────────────────────
# ProteinClaw — build the Rust TUI (cli-tui)
# Run from the project root in PowerShell.
# Output: target\release\proteinclaw-tui.exe
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Colour helpers ──────────────────────────
function ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg" -ForegroundColor Cyan }

# ── 1. Prerequisite check ───────────────────
try { $null = Get-Command cargo -ErrorAction Stop }
catch { fail "cargo not found. Install Rust: https://rustup.rs" }

ok "cargo found: $(cargo --version)"

# ── 2. Build ────────────────────────────────
info "Building proteinclaw-tui (release)..."
cargo build --release -p cli-tui
if ($LASTEXITCODE -ne 0) { fail "cargo build failed" }
ok "Build complete"

# ── 3. Print artifact path ───────────────────
$BIN = "target\release\proteinclaw-tui.exe"
Write-Host ""
Write-Host "Artifact: $(Resolve-Path $BIN)" -ForegroundColor White
Write-Host ""
Write-Host "To install globally:"
Write-Host "  Copy-Item $BIN `$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\proteinclaw-tui.exe"
