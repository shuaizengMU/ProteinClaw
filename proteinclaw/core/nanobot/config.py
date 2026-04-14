"""Nanobot workspace initialisation and config.json generation.

Reads ProteinClaw's env vars / settings and produces a nanobot-compatible
config dict that is written to <workspace>/nanobot-config.json at startup.

The nanobot Config schema (nanobot.config.schema) uses pydantic with
``alias_generator=to_camel``, so JSON keys are camelCase (e.g. ``apiKey``,
``maxToolIterations``).  The dict returned by ``build_nanobot_config`` already
uses those camelCase keys so it round-trips cleanly through
``Config.model_validate(data)``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from proteinclaw.core.config import SUPPORTED_MODELS, _PROVIDER_KEY_MAP

# Maps ProteinClaw provider name → nanobot provider name
_NANOBOT_PROVIDER_MAP: dict[str, str] = {
    "anthropic": "anthropic",
    "openai":    "openai",
    "deepseek":  "deepseek",
    "google":    "gemini",
    "ollama":    "ollama",
}

_SOUL_MD = """\
You are ProteinClaw, an expert AI agent for protein bioinformatics research.
You have access to 35 specialized tools covering protein annotation, structure,
variants, disease, pathways, expression, genomics, and literature databases
including UniProt, BLAST, AlphaFold, PDB, ClinVar, GTEx, and more.
Always chain tools intelligently to answer complex research questions thoroughly.
Respond in the same language the user writes in.
"""


def init_nanobot_workspace(workspace: Path) -> None:
    """Create workspace directory and write SOUL.md if it does not yet exist."""
    workspace.mkdir(parents=True, exist_ok=True)
    soul_path = workspace / "SOUL.md"
    if not soul_path.exists():
        soul_path.write_text(_SOUL_MD, encoding="utf-8")


def build_nanobot_config(
    model: str,
    workspace: Path,
    api_key: str = "",
) -> dict[str, Any]:
    """Build a nanobot config dict for the given model.

    The returned dict uses camelCase keys matching nanobot's JSON schema so it
    can be passed directly to ``Config.model_validate()`` or written to
    ``config.json``.
    """
    model_info = SUPPORTED_MODELS.get(model, {})
    pc_provider = model_info.get("provider", "openai")
    nanobot_provider = _NANOBOT_PROVIDER_MAP.get(pc_provider, "openai")
    api_base = model_info.get("api_base")

    if not api_key:
        env_var = _PROVIDER_KEY_MAP.get(pc_provider, "")
        api_key = os.environ.get(env_var, "")

    # ProviderConfig fields: api_key → apiKey, api_base → apiBase (camelCase aliases)
    provider_entry: dict[str, Any] = {"apiKey": api_key}
    if api_base:
        provider_entry["apiBase"] = api_base

    return {
        "agents": {
            "defaults": {
                "model": model,
                "provider": nanobot_provider,
                "workspace": str(workspace),
                "maxToolIterations": 20,
            }
        },
        "providers": {
            nanobot_provider: provider_entry,
        },
        "tools": {
            "web":  {"enable": False},
            "exec": {"enable": False},
        },
    }


def write_nanobot_config(config: dict[str, Any], config_path: Path) -> None:
    """Write the config dict to a JSON file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
