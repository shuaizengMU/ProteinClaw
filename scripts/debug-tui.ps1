# ────────────────────────────────────────────────────────────────
# ProteinClaw — build and run the TUI in debug mode (Windows)
#
# Stderr from the TUI (panics, backtraces) → debug.log
# Stderr from the Python server              → server.log
# Both logs are shown after the TUI exits.
#
# Options (env vars):
#   $env:PROTEINCLAW_NO_SPAWN = "1"   Skip auto-spawning the server.
#                                     Run the server yourself first:
#                                       uv run proteinclaw server --host 127.0.0.1 --port 8765
#                                     Then launch this script with the env var set.
#   $env:PROTEINCLAW_SERVER_CMD = "x" Override the server binary.
#
# Run from the project root in PowerShell.
# ────────────────────────────────────────────────────────────────
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function ok($msg)   { Write-Host "[OK] $msg"   -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "--> $msg"    -ForegroundColor Cyan }

$TUI_LOG = "debug.log"
$SRV_LOG = "server.log"

# ── Prerequisite check ──────────────────────────────────────────
try { $null = Get-Command cargo -ErrorAction Stop }
catch { fail "cargo not found. Install Rust: https://rustup.rs" }
ok "cargo found: $(cargo --version)"

# ── Build (debug profile) ───────────────────────────────────────
info "Building proteinclaw-tui (debug)..."
cargo build -p cli-tui
if ($LASTEXITCODE -ne 0) { fail "cargo build failed" }
ok "Build complete -> target\debug\proteinclaw-tui.exe"

# ── Pre-flight note ─────────────────────────────────────────────
if ($env:PROTEINCLAW_NO_SPAWN -eq "1") {
    info "PROTEINCLAW_NO_SPAWN=1 -- expecting server already on port 8765"
} else {
    info "Server stderr -> $SRV_LOG"
}

# ── Run ─────────────────────────────────────────────────────────
$BIN = "target\debug\proteinclaw-tui.exe"
"" | Set-Content $TUI_LOG

$env:RUST_BACKTRACE = "1"
$env:RUST_LOG       = "debug"

info "Launching TUI (debug). TUI stderr -> $TUI_LOG  |  Ctrl+C to stop"
Write-Host ""

& $BIN 2>>$TUI_LOG
$exitCode = $LASTEXITCODE

Remove-Item Env:\RUST_BACKTRACE -ErrorAction SilentlyContinue
Remove-Item Env:\RUST_LOG       -ErrorAction SilentlyContinue

# ── Post-exit: show logs ─────────────────────────────────────────
Write-Host ""
foreach ($log in @($TUI_LOG, $SRV_LOG)) {
    $content = Get-Content $log -ErrorAction SilentlyContinue
    if ($content) {
        Write-Host "-- $log ($($content.Count) lines) --" -ForegroundColor Red
        $content | Write-Host
        Write-Host ""
    }
}

$tuiEmpty = -not (Get-Content $TUI_LOG -ErrorAction SilentlyContinue)
$srvEmpty = -not (Get-Content $SRV_LOG -ErrorAction SilentlyContinue)
if ($tuiEmpty -and $srvEmpty) { ok "No errors logged. Clean exit." }
