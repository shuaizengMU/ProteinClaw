"""Per-model Nanobot singleton cache.

Creates and caches one Nanobot instance per model string. Tool injection
(registering all 35 proteinbox tools) and disabling nanobot built-in tools
happens once per instance creation.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from nanobot import Nanobot

from proteinclaw.core.nanobot.config import (
    build_nanobot_config,
    init_nanobot_workspace,
    write_nanobot_config,
)
from proteinclaw.core.nanobot.tools import build_tool_registry

# Built-in nanobot tool names to remove so only proteinbox tools are exposed.
# Confirmed actual built-in names (with web/exec disabled in config):
#   read_file, write_file, edit_file, list_dir, glob, grep,
#   notebook_edit, message, spawn
_BUILTIN_TOOLS_TO_REMOVE = [
    "read_file",
    "write_file",
    "edit_file",
    "list_dir",
    "glob",
    "grep",
    "notebook_edit",
    "message",
    "spawn",
    # Listed below in case web/exec tools are enabled in other configs:
    "web_search",
    "web_fetch",
    "exec",
]

_instances: dict[str, Nanobot] = {}
_workspace: Path | None = None


def set_workspace(workspace: Path) -> None:
    """Set the workspace root. Call once at app startup."""
    global _workspace
    _workspace = workspace
    init_nanobot_workspace(workspace)


def get_nanobot(model: str) -> Nanobot:
    """Return a cached Nanobot instance for the given model, creating if needed."""
    if model not in _instances:
        _instances[model] = _create_nanobot(model)
    return _instances[model]


def invalidate_nanobot(model: str) -> None:
    """Remove a cached instance so the next get_nanobot() rebuilds with fresh config.

    Call this after updating an API key in os.environ so the new key is picked up.
    """
    _instances.pop(model, None)


def _create_nanobot(model: str) -> Nanobot:
    workspace = _workspace or Path(tempfile.mkdtemp()) / "nanobot-workspace"
    config_path = workspace / f"config-{model.replace('/', '_')}.json"
    config = build_nanobot_config(model=model, workspace=workspace)
    write_nanobot_config(config, config_path)

    bot = Nanobot.from_config(config_path=config_path, workspace=workspace)

    # Remove built-in tools — only proteinbox tools should be available.
    # ToolRegistry.unregister uses dict.pop(..., None) so missing names are safe.
    for name in _BUILTIN_TOOLS_TO_REMOVE:
        bot._loop.tools.unregister(name)

    # Register all proteinbox tools
    proteinbox_registry = build_tool_registry()
    for tool_name in proteinbox_registry.tool_names:
        tool = proteinbox_registry.get(tool_name)
        if tool is not None:
            bot._loop.tools.register(tool)

    return bot
