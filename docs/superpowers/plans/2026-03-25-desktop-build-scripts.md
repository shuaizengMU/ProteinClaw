# Desktop Build Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `scripts/build-mac.sh` and `scripts/build-windows.ps1` that package ProteinClaw as a Tauri desktop app, and remove the now-unused Docker files.

**Architecture:** Each script runs from the project root and performs five steps in order: prerequisite check, uv sidecar binary download, frontend build, Tauri build, artifact path print. The macOS and Windows scripts are independent — each runs on its respective native platform.

**Tech Stack:** Bash (macOS), PowerShell (Windows), Tauri v2 (`cargo tauri build`), Node.js/npm, Rust/cargo, uv 0.6.6

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scripts/build-mac.sh` | macOS build script |
| Create | `scripts/build-windows.ps1` | Windows build script |
| Delete | `Dockerfile.backend` | Removed — Docker no longer used |
| Delete | `Dockerfile.frontend` | Removed — Docker no longer used |
| Modify | `.gitignore` | Ignore downloaded uv binaries in `src-tauri/binaries/` |

---

## Task 1: Remove Docker files

**Files:**
- Delete: `Dockerfile.backend`
- Delete: `Dockerfile.frontend`

- [ ] **Step 1: Delete the two Dockerfiles**

```bash
rm Dockerfile.backend Dockerfile.frontend
```

- [ ] **Step 2: Verify they are gone**

```bash
ls Dockerfile* 2>&1
```

Expected output: `ls: cannot access 'Dockerfile*': No such file or directory`

- [ ] **Step 3: Commit**

```bash
git rm Dockerfile.backend Dockerfile.frontend
git commit -m "chore: remove Docker files (replaced by Tauri desktop app)"
```

---

## Task 2: Update .gitignore for downloaded uv binaries

The `src-tauri/binaries/` directory holds downloaded uv binaries that should not be committed (they are large, platform-specific, and fetched by the build scripts). The existing `uv-aarch64-apple-darwin` was previously committed; going forward the directory is gitignored.

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Check current .gitignore state**

```bash
cat .gitignore
grep -n "binaries" .gitignore || echo "no binaries entry yet"
grep -n "binaries" src-tauri/.gitignore 2>/dev/null || echo "no src-tauri/.gitignore entry"
```

- [ ] **Step 2: Add ignore rule for uv binaries**

Add to `src-tauri/.gitignore` (create it if absent):

```
# Downloaded uv sidecar binaries — fetched by build scripts, not committed
binaries/uv-*
```

Note: if `src-tauri/binaries/uv-aarch64-apple-darwin` is currently tracked by git, untrack it:

```bash
git rm --cached src-tauri/binaries/uv-aarch64-apple-darwin 2>/dev/null || true
```

- [ ] **Step 3: Verify the rule works**

```bash
git status src-tauri/binaries/
```

Expected: the existing binary now shows as untracked (not staged), confirming the ignore rule works.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/.gitignore
git commit -m "chore: gitignore downloaded uv sidecar binaries"
```

---

## Task 3: Write build-mac.sh

**Files:**
- Create: `scripts/build-mac.sh`

Note: this is a shell script — there are no unit tests. Verification is done by dry-running the prerequisite check and inspecting the script logic manually. Full end-to-end test requires a macOS machine.

- [ ] **Step 1: Create the scripts/ directory**

```bash
mkdir -p scripts
```

- [ ] **Step 2: Write scripts/build-mac.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────
# ProteinClaw — macOS desktop build script
# Run from the project root.
# ────────────────────────────────────────────

UV_VERSION="0.6.6"

# ── Colour helpers ──────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

# ── 1. Prerequisite checks ──────────────────
info "Checking prerequisites..."

command -v rustc >/dev/null 2>&1 || \
  fail "rustc not found. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

command -v node >/dev/null 2>&1 || \
  fail "node not found. Install Node.js: brew install node  (or https://nodejs.org)"

command -v npm >/dev/null 2>&1 || \
  fail "npm not found. Install Node.js: brew install node  (or https://nodejs.org)"

cargo tauri --version >/dev/null 2>&1 || \
  fail "cargo tauri not found. Install: cargo install tauri-cli"

ok "All prerequisites met"

# ── 2. Download uv sidecar binary ───────────
ARCH=$(uname -m)
case "$ARCH" in
  arm64)  TRIPLE="aarch64-apple-darwin" ;;
  x86_64) TRIPLE="x86_64-apple-darwin" ;;
  *)      fail "Unsupported architecture: $ARCH" ;;
esac

DEST="src-tauri/binaries/uv-${TRIPLE}"
mkdir -p src-tauri/binaries

if [[ -f "$DEST" ]]; then
  ok "uv sidecar already present: $DEST (skipping download)"
else
  info "Downloading uv ${UV_VERSION} for ${TRIPLE}..."
  ARCHIVE="uv-${TRIPLE}.tar.gz"
  URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${ARCHIVE}"
  TMP=$(mktemp -d)
  curl -fsSL "$URL" -o "${TMP}/${ARCHIVE}" || fail "Failed to download uv from ${URL}"
  tar -xzf "${TMP}/${ARCHIVE}" --strip-components=1 -C "${TMP}" "uv-${TRIPLE}/uv" || \
    fail "Failed to extract uv binary from archive"
  mv "${TMP}/uv" "$DEST"
  chmod +x "$DEST"
  rm -rf "$TMP"
  ok "uv sidecar downloaded: $DEST"
fi

# ── 3. Build frontend ────────────────────────
info "Building frontend..."
(cd frontend && npm install && npm run build)
ok "Frontend built"

# ── 4. Tauri build ───────────────────────────
info "Running cargo tauri build (this takes a few minutes)..."
cargo tauri build
ok "Tauri build complete"

# ── 5. Print artifact path ───────────────────
DMG=$(find src-tauri/target/release/bundle/dmg -name "*.dmg" 2>/dev/null | head -1)
if [[ -n "$DMG" ]]; then
  echo ""
  echo -e "${BOLD}Artifact:${RESET} $(realpath "$DMG")"
else
  echo "Build succeeded but no .dmg found in src-tauri/target/release/bundle/dmg/"
fi
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/build-mac.sh
```

- [ ] **Step 4: Verify the script is syntactically valid (no macOS required)**

```bash
bash -n scripts/build-mac.sh && echo "Syntax OK"
```

Expected: `Syntax OK`

- [ ] **Step 5: Dry-run the prerequisite section only (Linux/WSL safe)**

```bash
bash -c '
  command -v rustc >/dev/null 2>&1 && echo "rustc: found" || echo "rustc: MISSING"
  command -v node  >/dev/null 2>&1 && echo "node:  found" || echo "node: MISSING"
  command -v npm   >/dev/null 2>&1 && echo "npm:   found" || echo "npm: MISSING"
  cargo tauri --version >/dev/null 2>&1 && echo "cargo tauri: found" || echo "cargo tauri: MISSING"
'
```

- [ ] **Step 6: Commit**

```bash
git add scripts/build-mac.sh
git commit -m "feat: add macOS desktop build script"
```

---

## Task 4: Write build-windows.ps1

**Files:**
- Create: `scripts/build-windows.ps1`

Note: PowerShell syntax checking can be done with `pwsh -NoProfile -NonInteractive -Command "Get-Command -Syntax"` if `pwsh` is installed (available on WSL2 via `sudo apt install powershell`), but is optional — the script is reviewed manually.

- [ ] **Step 1: Write scripts/build-windows.ps1**

```powershell
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
```

- [ ] **Step 2: Verify PowerShell syntax (if pwsh is available)**

```bash
# Run in WSL2 terminal if pwsh is installed:
pwsh -NoProfile -NonInteractive -File /dev/null 2>/dev/null && \
  pwsh -NoProfile -NonInteractive -Command "
    \$null = [System.Management.Automation.Language.Parser]::ParseFile(
      'scripts/build-windows.ps1', [ref]\$null, [ref]\$errors
    )
    if (\$errors.Count -gt 0) { \$errors; exit 1 } else { Write-Host 'Syntax OK' }
  " || echo "pwsh not available — skipping syntax check"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/build-windows.ps1
git commit -m "feat: add Windows desktop build script"
```

---

## Task 5: Update README.md build instructions

**Files:**
- Modify: `README.md`

The Docker Quick Start was already removed. Now add a "Building the Desktop App" section that points to the two scripts.

- [ ] **Step 1: Add build instructions to README.md**

Find the `## Architecture` section in `README.md` and insert the following section before it:

```markdown
## Building the Desktop App

Run the build script for your platform from the **project root**. The script checks prerequisites, downloads the bundled `uv` binary, builds the frontend, and produces an installable package.

**macOS:**
```bash
bash scripts/build-mac.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\build-windows.ps1
```

Output artifact locations:
- macOS: `src-tauri/target/release/bundle/dmg/*.dmg`
- Windows: `src-tauri/target/release/bundle/nsis/*.exe`

**Prerequisites:** Rust (`rustup`), Node.js 20+, `cargo install tauri-cli`
```

- [ ] **Step 2: Verify README renders correctly**

```bash
# Quick sanity check — look for the new section
grep -n "Building the Desktop App" README.md
```

Expected: one matching line.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add desktop build instructions to README"
```

---

## Verification Checklist (post-implementation)

These steps require running on the actual target platform and cannot be automated in CI without macOS/Windows runners:

- [ ] On macOS (Apple Silicon): run `bash scripts/build-mac.sh` from a clean checkout → produces `.dmg`
- [ ] On macOS (Intel): run `bash scripts/build-mac.sh` → downloads `uv-x86_64-apple-darwin`, produces `.dmg`
- [ ] On Windows: run `.\scripts\build-windows.ps1` → downloads `uv-x86_64-pc-windows-msvc.exe`, produces NSIS `.exe`
- [ ] Re-run either script without deleting the uv binary → confirms idempotency (skip message shown)
