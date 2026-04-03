# ────────────────────────────────────────────
# ProteinClaw — CLI smoke test (Windows)
# Run from the project root in PowerShell.
#
# Usage:
#   scripts\test-cli.ps1
#   scripts\test-cli.ps1 -Model deepseek-chat
# ────────────────────────────────────────────
#Requires -Version 5.1

param(
    [string]$Model = ""
)

$ErrorActionPreference = "Stop"

# ── Colour helpers ───────────────────────────
function ok($msg)   { Write-Host "[OK]   $msg" -ForegroundColor Green }
function fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
function info($msg) { Write-Host "-->    $msg" -ForegroundColor Cyan }
function warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function sep()      { Write-Host ("-" * 44) -ForegroundColor DarkGray }

# ── Prerequisite check ───────────────────────
try { $null = Get-Command uv -ErrorAction Stop }
catch { fail "uv not found. Install: winget install astral-sh.uv" }

info "Syncing dependencies..."
uv sync --quiet

sep
Write-Host "ProteinClaw CLI smoke tests" -ForegroundColor White
sep

# ── API key warning ──────────────────────────
$hasKey = ($env:ANTHROPIC_API_KEY -or $env:OPENAI_API_KEY -or
           $env:DEEPSEEK_API_KEY  -or $env:MINIMAX_API_KEY)
if (-not $hasKey) {
    warn "No API key found in environment."
    warn "Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, MINIMAX_API_KEY"
    warn "Or run 'proteinclaw' to configure via the setup wizard."
    Write-Host ""
}

# Build model args array
$modelArgs = @()
if ($Model) { $modelArgs = @("--model", $Model) }

# ── Helper: run a query ───────────────────────
function Run-Query {
    param(
        [string]$Label,
        [string]$Query,
        [string]$Expect = ""
    )

    info "Test: $Label"
    Write-Host "  Query: $Query" -ForegroundColor Yellow

    $output = uv run proteinclaw query @modelArgs $Query 2>&1
    $exitCode = $LASTEXITCODE

    # Print first 3 lines of output
    $lines = ($output -split "`n") | Select-Object -First 3
    Write-Host "  Output (first 3 lines):"
    foreach ($line in $lines) { Write-Host "    $line" }

    if ($exitCode -ne 0) {
        Write-Host "  Full output: $output"
        fail "$Label — command exited with code $exitCode"
    }

    if ($Expect -and ($output -notmatch $Expect)) {
        warn "$Label — expected '$Expect' not found in output (may be a model decision)"
    } else {
        ok $Label
    }
    Write-Host ""
}

# ── Test 1: --help ───────────────────────────
info "Test: CLI entry point is reachable"
uv run proteinclaw --help | Out-Null
if ($LASTEXITCODE -eq 0) { ok "proteinclaw --help works" }
else { fail "proteinclaw --help failed" }
Write-Host ""

# ── Test 2: UniProt lookup ───────────────────
Run-Query `
    -Label "UniProt lookup (P04637 = TP53)" `
    -Query "What is the UniProt accession P04637?" `
    -Expect "TP53"

# ── Test 3: Simple factual query ─────────────
Run-Query `
    -Label "Simple protein question" `
    -Query "What does a kinase do?" `
    -Expect "phosph"

# ── Test 4: Exit code 0 ──────────────────────
info "Test: exit code is 0 on clean run"
uv run proteinclaw query @modelArgs "What is a protein?" | Out-Null
if ($LASTEXITCODE -eq 0) { ok "Exit code 0" }
else { fail "Unexpected non-zero exit code: $LASTEXITCODE" }
Write-Host ""

sep
ok "All CLI smoke tests completed"
sep
Write-Host ""
Write-Host "To launch the interactive TUI:"
Write-Host "  uv run proteinclaw" -ForegroundColor White
Write-Host ""
