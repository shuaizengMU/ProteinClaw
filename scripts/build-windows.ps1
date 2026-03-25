# ────────────────────────────────────────────
# ProteinClaw — Windows desktop build script
# Run from the project root in PowerShell.
# ────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$UV_VERSION = "0.6.6"

# ── Colour helpers ──────────────────────────
function ok($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "✗ $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "→ $msg" -ForegroundColor Cyan }

# ── 1. Prerequisite checks ──────────────────
info "Checking prerequisites..."

try { $null = Get-Command rustc -ErrorAction Stop }
catch { fail "rustc not found. Install Rust: https://rustup.rs" }

try { $null = Get-Command node -ErrorAction Stop }
catch { fail "node not found. Install Node.js: winget install OpenJS.NodeJS" }

try { $null = Get-Command npm -ErrorAction Stop }
catch { fail "npm not found. Install Node.js: winget install OpenJS.NodeJS" }

try { cargo tauri --version | Out-Null }
catch { fail "cargo tauri not found. Install: cargo install tauri-cli" }

ok "All prerequisites met"

# ── 2. Download uv sidecar binary ───────────
$TRIPLE  = "x86_64-pc-windows-msvc"
$DEST    = "src-tauri\binaries\uv-$TRIPLE.exe"

New-Item -ItemType Directory -Force -Path "src-tauri\binaries" | Out-Null

if (Test-Path $DEST) {
    ok "uv sidecar already present: $DEST (skipping download)"
} else {
    info "Downloading uv $UV_VERSION for $TRIPLE..."
    $ARCHIVE = "uv-$TRIPLE.zip"
    $URL     = "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$ARCHIVE"
    $TMP     = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
    $ZIPPATH = Join-Path $TMP $ARCHIVE

    try {
        Invoke-WebRequest -Uri $URL -OutFile $ZIPPATH -UseBasicParsing
    } catch {
        fail "Failed to download uv from $URL : $_"
    }

    Expand-Archive -Path $ZIPPATH -DestinationPath $TMP -Force
    $UVExe = Join-Path $TMP "uv.exe"
    if (-not (Test-Path $UVExe)) { fail "uv.exe not found in extracted archive" }
    Copy-Item $UVExe $DEST
    Remove-Item -Recurse -Force $TMP
    ok "uv sidecar downloaded: $DEST"
}

# ── 3. Build frontend ────────────────────────
info "Building frontend..."
Push-Location frontend
try {
    npm install
    npm run build
} finally {
    Pop-Location
}
ok "Frontend built"

# ── 4. Tauri build ───────────────────────────
info "Running cargo tauri build (this takes a few minutes)..."
cargo tauri build
ok "Tauri build complete"

# ── 5. Print artifact path ───────────────────
$NSIS = Get-ChildItem -Path "src-tauri\target\release\bundle\nsis" -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($NSIS) {
    Write-Host ""
    Write-Host "Artifact: $($NSIS.FullName)" -ForegroundColor White -BackgroundColor DarkGreen
} else {
    Write-Host "Build succeeded but no .exe found in src-tauri\target\release\bundle\nsis\"
}
