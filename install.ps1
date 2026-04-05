# ─────────────────────────────────────────────────────────────────────────────
# ProteinClaw installer for Windows
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/shuaizengMU/ProteinClaw/main/install.ps1 | iex
#
# What this script does:
#   1. Installs uv (if not already installed)
#   2. Installs the ProteinClaw Python backend via uv tool install
#   3. Downloads the proteinclaw-tui binary for Windows x86_64
#   4. Places it in %USERPROFILE%\.local\bin and adds it to PATH if needed
# ─────────────────────────────────────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$REPO       = "shuaizengMU/ProteinClaw"
$BIN_NAME   = "proteinclaw-tui"
$INSTALL_DIR = Join-Path $env:USERPROFILE ".local\bin"

function ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg" -ForegroundColor Cyan }
function warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "ProteinClaw Installer" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "──────────────────────────────────────────"
Write-Host ""

# ── 1. Install uv (if not present) ───────────────────────────────────────────
try { $null = Get-Command uv -ErrorAction Stop; ok "uv already installed: $(uv --version)" }
catch {
  info "Installing uv..."
  try {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
    ok "uv installed: $(uv --version)"
  } catch {
    fail "uv installation failed. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
  }
}

# ── 2. Install Python backend ─────────────────────────────────────────────────
info "Installing ProteinClaw Python backend..."
uv tool install "git+https://github.com/$REPO.git" --force
if ($LASTEXITCODE -ne 0) { fail "uv tool install failed" }
ok "Python backend installed"

# ── 3. Download proteinclaw-tui binary ───────────────────────────────────────
$ASSET   = "$BIN_NAME-windows-x86_64.exe"
$URL     = "https://github.com/$REPO/releases/latest/download/$ASSET"
$DEST    = Join-Path $INSTALL_DIR "$BIN_NAME.exe"

info "Downloading $BIN_NAME (windows-x86_64)..."
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null

try {
  Invoke-WebRequest -Uri $URL -OutFile $DEST -UseBasicParsing
  ok "Downloaded $BIN_NAME -> $DEST"
} catch {
  fail "Could not download $BIN_NAME for windows-x86_64.

  Check that a release exists at:
    https://github.com/$REPO/releases/latest

  Or build from source:
    git clone https://github.com/$REPO.git
    cd ProteinClaw
    .\scripts\build-tui.ps1"
}

# ── 4. Add to PATH if needed ──────────────────────────────────────────────────
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$INSTALL_DIR*") {
  warn "$INSTALL_DIR is not in your PATH. Adding it..."
  [Environment]::SetEnvironmentVariable("PATH", "$INSTALL_DIR;$currentPath", "User")
  $env:PATH = "$INSTALL_DIR;$env:PATH"
  warn "Restart your terminal for PATH changes to take effect."
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "──────────────────────────────────────────"
Write-Host "ProteinClaw installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Run:  proteinclaw-tui"
Write-Host ""
Write-Host "  On first launch, a setup wizard will prompt for your API key."
Write-Host "──────────────────────────────────────────"
Write-Host ""
