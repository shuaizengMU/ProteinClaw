# Desktop Build Scripts Design

**Date:** 2026-03-25
**Status:** Approved

## Overview

Two platform-specific build scripts that package ProteinClaw as a Tauri desktop app. Docker is removed. Each script handles prerequisite checking, uv sidecar binary download, frontend build, and Tauri bundling.

## Motivation

The project previously used Docker for development and deployment. With the Tauri desktop app approach, Docker is no longer needed. Users need a simple, reproducible way to produce installable desktop packages on their native platform.

## Files Changed

### Added
- `scripts/build-mac.sh` — macOS build script (bash)
- `scripts/build-windows.ps1` — Windows build script (PowerShell)

### Deleted
- `Dockerfile.backend`
- `Dockerfile.frontend`

Note: there is no `docker-compose.yml` in this repo. The Docker cleanup is limited to the two Dockerfiles listed above. The build scripts themselves do not delete these files — deletion is a separate manual step (or part of this implementation task).

## Script Structure

Both scripts follow the same five-step sequence, run from the project root:

1. **Prerequisite checks** — verify required tools are installed
2. **Download uv sidecar** — fetch the correct uv binary for the current platform/arch into `src-tauri/binaries/`
3. **Build frontend** — `npm install && npm run build` in `frontend/`
4. **Tauri build** — `cargo tauri build` from project root
5. **Print output path** — show the user where the installable artifact lives

## Prerequisite Checks

Each script checks for the following tools before proceeding. Any missing tool causes an immediate exit with an actionable install hint.

Detection commands:
- `rustc`: `command -v rustc` (bash) / `Get-Command rustc` (PowerShell)
- `node` / `npm`: `command -v node` and `command -v npm` (bash) / `Get-Command node` (PowerShell)
- `cargo tauri`: `cargo tauri --version 2>/dev/null` (bash) / `cargo tauri --version` in a try/catch (PowerShell)

| Tool | macOS hint | Windows hint |
|------|-----------|--------------|
| `rustc` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` | Same (rustup.rs) |
| `node` / `npm` | `brew install node` | `winget install OpenJS.NodeJS` |
| `cargo tauri` | `cargo install tauri-cli` | `cargo install tauri-cli` |

If all checks pass, the script prints `✓ All prerequisites met` and continues.

## uv Sidecar Binary

Tauri bundles `uv` as a sidecar (`externalBin: ["binaries/uv"]`). The binary must be present in `src-tauri/binaries/` with a Tauri-style target-triple filename before `cargo tauri build` runs.

**Version:** Pinned via a variable at the top of each script:
- bash: `UV_VERSION="0.6.6"`
- PowerShell: `$UV_VERSION = "0.6.6"`

Update this variable to upgrade. **Important:** when `UV_VERSION` changes, the existing binary must be manually deleted from `src-tauri/binaries/` so the script re-downloads it. The idempotency skip (see below) is keyed on file existence only, not version.

**Download source:** `https://github.com/astral-sh/uv/releases/download/`

**Directory creation:** The script creates `src-tauri/binaries/` with `mkdir -p` (bash) / `New-Item -Force` (PowerShell) before placing files there. This handles clean checkouts where the directory does not exist.

### macOS (`build-mac.sh`)

Detects architecture via `uname -m`:

| `uname -m` | Archive | Target filename |
|-----------|---------|-----------------|
| `arm64` | `uv-aarch64-apple-darwin.tar.gz` | `src-tauri/binaries/uv-aarch64-apple-darwin` |
| `x86_64` | `uv-x86_64-apple-darwin.tar.gz` | `src-tauri/binaries/uv-x86_64-apple-darwin` |

**Archive layout:** The macOS `.tar.gz` contains a subdirectory named after the archive (e.g., `uv-aarch64-apple-darwin/`), and the `uv` binary is inside it. Extraction must account for this:

```bash
tar -xzf "uv-${TRIPLE}.tar.gz" --strip-components=1 -C "$TMPDIR" "uv-${TRIPLE}/uv"
```

After extraction, the binary is moved from `$TMPDIR/uv` to `src-tauri/binaries/uv-${TRIPLE}` and made executable with `chmod +x`.

### Windows (`build-windows.ps1`)

Fixed to x86_64 (ARM Windows not supported):

| Archive | Target filename |
|---------|-----------------|
| `uv-x86_64-pc-windows-msvc.zip` | `src-tauri/binaries/uv-x86_64-pc-windows-msvc.exe` |

**Archive layout:** The Windows `.zip` is flat — `uv.exe` and `uvx.exe` are at the root with no subdirectory. Extract directly:

```powershell
Expand-Archive -Path "uv-x86_64-pc-windows-msvc.zip" -DestinationPath $tmpDir -Force
Copy-Item "$tmpDir\uv.exe" "src-tauri\binaries\uv-x86_64-pc-windows-msvc.exe"
```

**Idempotent:** Both scripts skip the download step if the target file already exists.

## Build Steps

All commands run from the project root.

### Frontend
```
cd frontend
npm install
npm run build
cd ..
```

### Tauri
```
cargo tauri build
```

Must be run from the project root (the directory containing `src-tauri/`). This triggers `beforeBuildCommand: "npm run build"` (already handled above, harmless to run twice) and produces the installable bundle.

## Output Artifacts

| Platform | Location | Format |
|----------|----------|--------|
| macOS | `src-tauri/target/release/bundle/dmg/*.dmg` | DMG disk image |
| Windows | `src-tauri/target/release/bundle/nsis/*.exe` | NSIS installer |

The script prints the full path to the artifact on success.

## Error Handling

- Prerequisite check failure: print hint, `exit 1`
- uv download failure: print error, `exit 1`
- Frontend build failure: npm/node errors surface naturally; script exits via `set -e` (bash) / `$ErrorActionPreference = "Stop"` (PowerShell)
- Tauri build failure: cargo errors surface naturally

## Non-Goals

- Cross-compilation (macOS builds run on Mac, Windows builds run on Windows)
- Auto-installing prerequisites (scripts check and hint, not install)
- ARM Windows support
- Checksum verification of uv downloads
- CI/CD configuration (out of scope for this design)
