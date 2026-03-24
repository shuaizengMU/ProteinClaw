# ProteinClaw MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ProteinClaw MVP — a web-based AI agent that accepts natural language protein research queries, orchestrates ProteinBox tools (UniProt, BLAST), and streams results to a React frontend.

**Architecture:** Custom ReAct agent loop (Thought→Action→Observation) backed by LiteLLM for multi-model routing. ProteinBox is a standalone Python package providing the tool layer. FastAPI serves the backend API with WebSocket streaming. React+Vite provides the frontend.

**Tech Stack:** Python 3.11+, FastAPI, LiteLLM, httpx, Pydantic v2, React 18, TypeScript, Vite, pytest

---

## File Map

```
proteinbox/
├── __init__.py
└── tools/
    ├── __init__.py
    ├── registry.py          # ToolResult, ProteinTool base class, @register_tool, discover_tools()
    ├── uniprot.py           # UniProtTool
    └── blast.py             # BLASTTool

proteinclaw/
├── __init__.py
├── main.py                  # FastAPI app factory
├── config.py                # SUPPORTED_MODELS, settings loaded from env
├── agent/
│   ├── __init__.py
│   ├── llm.py               # LiteLLM wrapper with streaming support
│   ├── prompt.py            # System prompt builder (injects tool descriptions)
│   └── loop.py              # ReAct agent main loop
└── api/
    ├── __init__.py
    ├── chat.py              # POST /chat + WebSocket /ws/chat
    └── tools.py             # GET /tools

tests/
├── proteinbox/
│   ├── test_registry.py
│   ├── test_uniprot.py
│   └── test_blast.py
└── proteinclaw/
    ├── test_config.py
    ├── test_llm.py
    ├── test_loop.py
    └── test_api.py

frontend/
├── package.json
├── vite.config.ts
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── types.ts             # WebSocket event type definitions
    ├── hooks/
    │   └── useChat.ts       # WebSocket connection + message state
    └── components/
        ├── ChatWindow.tsx
        ├── ToolCallCard.tsx
        └── ModelSelector.tsx

pyproject.toml
.env.example
docker-compose.yml
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `proteinbox/__init__.py`
- Create: `proteinbox/tools/__init__.py`
- Create: `proteinclaw/__init__.py`
- Create: `proteinclaw/agent/__init__.py`
- Create: `proteinclaw/api/__init__.py`
- Create: `tests/proteinbox/__init__.py`
- Create: `tests/proteinclaw/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "proteinclaw"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "litellm>=1.40",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "httpx[ws]>=0.27",
    "respx>=0.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
MINIMAX_API_KEY=...
NCBI_API_KEY=        # optional, increases BLAST rate limit
DEFAULT_MODEL=gpt-4o
```

- [ ] **Step 3: Create all `__init__.py` files and test directories**

```bash
mkdir -p proteinbox/tools proteinclaw/agent proteinclaw/api tests/proteinbox tests/proteinclaw
touch proteinbox/__init__.py proteinbox/tools/__init__.py
touch proteinclaw/__init__.py proteinclaw/agent/__init__.py proteinclaw/api/__init__.py
touch tests/__init__.py tests/proteinbox/__init__.py tests/proteinclaw/__init__.py
touch tests/conftest.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: No errors. `pip show proteinclaw` shows version 0.1.0.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example proteinbox/ proteinclaw/ tests/
git commit -m "chore: scaffold project structure"
```

---

## Task 2: ProteinBox — Tool Registry

**Files:**
- Create: `proteinbox/tools/registry.py`
- Create: `tests/proteinbox/test_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinbox/test_registry.py
from proteinbox.tools.registry import (
    ToolResult, ProteinTool, register_tool, discover_tools, TOOL_REGISTRY
)

def test_tool_result_success():
    r = ToolResult(success=True, data={"key": "value"}, display="ok")
    assert r.success is True
    assert r.data == {"key": "value"}
    assert r.error is None

def test_tool_result_failure():
    r = ToolResult(success=False, data=None, error="something went wrong")
    assert r.success is False
    assert r.error == "something went wrong"

def test_register_tool_adds_to_registry():
    from unittest.mock import patch
    with patch.dict(TOOL_REGISTRY, {}, clear=False):
        @register_tool
        class DummyTool(ProteinTool):
            name: str = "dummy_isolated"
            description: str = "A dummy tool"
            parameters: dict = {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            }
            def run(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={"x": kwargs["x"]}, display=kwargs["x"])

        assert "dummy_isolated" in TOOL_REGISTRY
        tool = TOOL_REGISTRY["dummy_isolated"]
        result = tool.run(x="hello")
        assert result.success is True
        assert result.data == {"x": "hello"}
    # After exiting context, dummy_isolated is removed from TOOL_REGISTRY

def test_protein_tool_run_raises_not_implemented():
    class BadTool(ProteinTool):
        name: str = "bad"
        description: str = "bad"
        parameters: dict = {}
    t = BadTool()
    import pytest
    with pytest.raises(NotImplementedError):
        t.run()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinbox/test_registry.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement `proteinbox/tools/registry.py`**

```python
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel

TOOL_REGISTRY: dict[str, "ProteinTool"] = {}


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    display: Optional[str] = None
    error: Optional[str] = None


class ProteinTool(BaseModel):
    name: str
    description: str
    parameters: dict  # OpenAI function-calling compatible JSON Schema

    model_config = {"arbitrary_types_allowed": True}

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError


def register_tool(cls: type[ProteinTool]) -> type[ProteinTool]:
    """Class decorator that instantiates and registers a ProteinTool."""
    instance = cls()
    TOOL_REGISTRY[instance.name] = instance
    return cls


def discover_tools() -> dict[str, ProteinTool]:
    """Import all modules in proteinbox/tools/ to trigger @register_tool decorators."""
    import pkgutil
    import importlib
    import proteinbox.tools as pkg
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if module_name != "registry":
            importlib.import_module(f"proteinbox.tools.{module_name}")
    return TOOL_REGISTRY
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinbox/test_registry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/tools/registry.py tests/proteinbox/test_registry.py
git commit -m "feat(proteinbox): add ToolResult, ProteinTool base, and tool registry"
```

---

## Task 3: ProteinBox — UniProtTool

**Files:**
- Create: `proteinbox/tools/uniprot.py`
- Create: `tests/proteinbox/test_uniprot.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinbox/test_uniprot.py
import pytest
import respx
import httpx
from proteinbox.tools.uniprot import UniProtTool

MOCK_RESPONSE = {
    "primaryAccession": "P04637",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "comments": [
        {"commentType": "FUNCTION", "texts": [{"value": "Acts as a tumor suppressor."}]}
    ],
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 393},
    "uniProtKBCrossReferences": [
        {"database": "GO", "id": "GO:0003677", "properties": [
            {"key": "GoTerm", "value": "F:DNA binding"}
        ]}
    ],
}

@respx.mock
def test_uniprot_tool_success():
    respx.get("https://rest.uniprot.org/uniprotkb/P04637.json").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = UniProtTool()
    result = tool.run(accession_id="P04637")
    assert result.success is True
    assert result.data["accession"] == "P04637"
    assert result.data["name"] == "Cellular tumor antigen p53"
    assert result.data["organism"] == "Homo sapiens"
    assert result.data["sequence_length"] == 393
    assert "TP53" in result.data["genes"]
    assert result.display is not None

@respx.mock
def test_uniprot_tool_not_found():
    respx.get("https://rest.uniprot.org/uniprotkb/INVALID.json").mock(
        return_value=httpx.Response(404)
    )
    tool = UniProtTool()
    result = tool.run(accession_id="INVALID")
    assert result.success is False
    assert "404" in result.error or "not found" in result.error.lower()

@respx.mock
def test_uniprot_tool_registered():
    from proteinbox.tools.registry import TOOL_REGISTRY
    import importlib
    import proteinbox.tools.uniprot  # noqa: F401 — triggers registration
    assert "uniprot" in TOOL_REGISTRY
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinbox/test_uniprot.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `proteinbox/tools/uniprot.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class UniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = (
        "Query UniProt for protein information by accession ID. "
        "Returns protein name, function, gene names, organism, sequence length, and GO terms."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["accession_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession_id = kwargs["accession_id"].strip().upper()
        url = f"https://rest.uniprot.org/uniprotkb/{accession_id}.json"
        try:
            response = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, data=None, error=str(e))

        if response.status_code != 200:
            return ToolResult(
                success=False,
                data=None,
                error=f"UniProt returned {response.status_code} for accession {accession_id}",
            )

        raw = response.json()

        # Extract fields
        name = (
            raw.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "Unknown")
        )
        genes = [
            g["geneName"]["value"]
            for g in raw.get("genes", [])
            if "geneName" in g
        ]
        organism = raw.get("organism", {}).get("scientificName", "Unknown")
        seq_length = raw.get("sequence", {}).get("length", 0)
        function_texts = [
            t["value"]
            for c in raw.get("comments", [])
            if c.get("commentType") == "FUNCTION"
            for t in c.get("texts", [])
        ]
        go_terms = [
            next((p["value"] for p in ref.get("properties", []) if p["key"] == "GoTerm"), ref["id"])
            for ref in raw.get("uniProtKBCrossReferences", [])
            if ref.get("database") == "GO"
        ]

        data = {
            "accession": accession_id,
            "name": name,
            "genes": genes,
            "organism": organism,
            "sequence_length": seq_length,
            "function": function_texts,
            "go_terms": go_terms[:10],  # cap at 10 for LLM context
        }
        display = (
            f"{name} ({', '.join(genes) or 'no gene name'}) — {organism}, "
            f"{seq_length} aa. Function: {function_texts[0][:200] if function_texts else 'N/A'}"
        )
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinbox/test_uniprot.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/tools/uniprot.py tests/proteinbox/test_uniprot.py
git commit -m "feat(proteinbox): add UniProtTool"
```

---

## Task 4: ProteinBox — BLASTTool

**Files:**
- Create: `proteinbox/tools/blast.py`
- Create: `tests/proteinbox/test_blast.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinbox/test_blast.py
import pytest
import respx
import httpx
from proteinbox.tools.blast import BLASTTool

SUBMIT_RESPONSE = "    RID = ABC123\n    RTOE = 10\n"
READY_RESPONSE = "Status=READY\n"
RESULTS_XML = """<?xml version="1.0"?>
<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "">
<BlastOutput>
  <BlastOutput_iterations>
    <Iteration>
      <Iteration_hits>
        <Hit>
          <Hit_def>Tumor suppressor p53 [Homo sapiens]</Hit_def>
          <Hit_accession>NP_000537</Hit_accession>
          <Hit_hsps>
            <Hsp>
              <Hsp_evalue>1e-150</Hsp_evalue>
              <Hsp_identity>393</Hsp_identity>
              <Hsp_align-len>393</Hsp_align-len>
            </Hsp>
          </Hit_hsps>
        </Hit>
      </Iteration_hits>
    </Iteration>
  </BlastOutput_iterations>
</BlastOutput>"""

@respx.mock
def test_blast_tool_success():
    respx.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text=SUBMIT_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", params__contains={"RID": "ABC123", "FORMAT_OBJECT": "SearchInfo"}).mock(
        return_value=httpx.Response(200, text=READY_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", params__contains={"RID": "ABC123", "FORMAT_TYPE": "XML"}).mock(
        return_value=httpx.Response(200, text=RESULTS_XML)
    )
    tool = BLASTTool()
    result = tool.run(sequence="MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDP")
    assert result.success is True
    assert len(result.data["hits"]) >= 1
    assert result.data["hits"][0]["accession"] == "NP_000537"

@respx.mock
def test_blast_tool_timeout():
    respx.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text=SUBMIT_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text="Status=WAITING\n")
    )
    tool = BLASTTool()
    result = tool.run(
        sequence="MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDP",
        timeout=1,
        poll_interval=0.1,
    )
    assert result.success is False
    assert "timed out" in result.error.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinbox/test_blast.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `proteinbox/tools/blast.py`**

```python
import time
import re
import xml.etree.ElementTree as ET
import httpx
from typing import Optional
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

BLAST_URL = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"


@register_tool
class BLASTTool(ProteinTool):
    name: str = "blast"
    description: str = (
        "Run a BLAST search to find homologous proteins for a given sequence. "
        "Input is a protein sequence (plain amino acids or FASTA format). "
        "Returns top hits with descriptions, accessions, E-values, and identity."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence in plain amino acids or FASTA format",
            },
            "max_hits": {
                "type": "integer",
                "description": "Maximum number of hits to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        sequence: str = kwargs["sequence"].strip()
        max_hits: int = int(kwargs.get("max_hits", 5))
        timeout: int = int(kwargs.get("timeout", 120))
        poll_interval: float = float(kwargs.get("poll_interval", 5.0))

        # Strip FASTA header if present
        if sequence.startswith(">"):
            sequence = "\n".join(sequence.split("\n")[1:])

        # Submit job
        try:
            rid, estimated_time = self._submit(sequence)
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"BLAST submit failed: {e}")

        # Poll for results
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(poll_interval)
            status = self._check_status(rid)
            if status == "READY":
                break
            if status == "FAILED":
                return ToolResult(success=False, data=None, error="BLAST search failed on NCBI side")
        else:
            return ToolResult(success=False, data=None, error=f"BLAST search timed out after {timeout}s")

        # Fetch results
        try:
            hits = self._fetch_results(rid, max_hits)
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"BLAST result parse failed: {e}")

        display = f"BLAST found {len(hits)} hits. Top: {hits[0]['description'][:100] if hits else 'none'}"
        return ToolResult(success=True, data={"hits": hits, "rid": rid}, display=display)

    def _submit(self, sequence: str) -> tuple[str, int]:
        resp = httpx.post(
            BLAST_URL,
            data={
                "CMD": "Put",
                "PROGRAM": "blastp",
                "DATABASE": "nr",
                "QUERY": sequence,
                "FORMAT_TYPE": "XML",
            },
            timeout=30,
        )
        resp.raise_for_status()
        rid_match = re.search(r"RID\s*=\s*(\S+)", resp.text)
        rtoe_match = re.search(r"RTOE\s*=\s*(\d+)", resp.text)
        if not rid_match:
            raise ValueError("Could not parse RID from BLAST submit response")
        return rid_match.group(1), int(rtoe_match.group(1)) if rtoe_match else 10

    def _check_status(self, rid: str) -> str:
        resp = httpx.get(
            BLAST_URL,
            params={"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"},
            timeout=15,
        )
        if "Status=READY" in resp.text:
            return "READY"
        if "Status=FAILED" in resp.text or "Status=UNKNOWN" in resp.text:
            return "FAILED"
        return "WAITING"

    def _fetch_results(self, rid: str, max_hits: int) -> list[dict]:
        resp = httpx.get(
            BLAST_URL,
            params={"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML"},
            timeout=60,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        hits = []
        for hit in root.iter("Hit"):
            hsp = hit.find(".//Hsp")
            if hsp is None:
                continue
            align_len = int(hsp.findtext("Hsp_align-len") or 1)
            identity = int(hsp.findtext("Hsp_identity") or 0)
            hits.append({
                "description": hit.findtext("Hit_def", ""),
                "accession": hit.findtext("Hit_accession", ""),
                "evalue": hsp.findtext("Hsp_evalue", ""),
                "identity_pct": round(identity / align_len * 100, 1),
            })
            if len(hits) >= max_hits:
                break
        return hits
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinbox/test_blast.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/tools/blast.py tests/proteinbox/test_blast.py
git commit -m "feat(proteinbox): add BLASTTool with async submit-poll"
```

---

## Task 5: ProteinClaw — Config

**Files:**
- Create: `proteinclaw/config.py`
- Create: `tests/proteinclaw/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinclaw/test_config.py
import os
import pytest
from proteinclaw.config import Settings, SUPPORTED_MODELS

def test_supported_models_contains_required_keys():
    required = {"gpt-4o", "claude-opus-4-5", "deepseek-chat", "deepseek-reasoner",
                "minimax-text-01", "ollama/llama3"}
    assert required.issubset(set(SUPPORTED_MODELS.keys()))

def test_supported_models_have_provider():
    for name, cfg in SUPPORTED_MODELS.items():
        assert "provider" in cfg, f"{name} missing 'provider'"

def test_settings_default_model(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-4o")
    s = Settings()
    assert s.default_model == "gpt-4o"

def test_settings_default_model_fallback(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    s = Settings()
    assert s.default_model in SUPPORTED_MODELS
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinclaw/test_config.py -v
```

- [ ] **Step 3: Implement `proteinclaw/config.py`**

```python
from pydantic_settings import BaseSettings
from pydantic import Field


SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":   {"provider": "minimax",   "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
}


class Settings(BaseSettings):
    default_model: str = Field(default="gpt-4o", alias="DEFAULT_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    ncbi_api_key: str = Field(default="", alias="NCBI_API_KEY")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinclaw/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/config.py tests/proteinclaw/test_config.py
git commit -m "feat(proteinclaw): add config with SUPPORTED_MODELS and Settings"
```

---

## Task 6: ProteinClaw — LLM Wrapper

**Files:**
- Create: `proteinclaw/agent/llm.py`
- Create: `tests/proteinclaw/test_llm.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinclaw/test_llm.py
import pytest
from unittest.mock import patch, MagicMock
from proteinclaw.agent.llm import call_llm, call_llm_stream, build_tools_schema
from proteinbox.tools.registry import ProteinTool, ToolResult, TOOL_REGISTRY

class EchoTool(ProteinTool):
    name: str = "echo"
    description: str = "Echo back the input"
    parameters: dict = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }
    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"text": kwargs["text"]}, display=kwargs["text"])

def test_build_tools_schema():
    tools = {"echo": EchoTool()}
    schema = build_tools_schema(tools)
    assert len(schema) == 1
    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "echo"
    assert "parameters" in schema[0]["function"]

def test_call_llm_returns_message():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello"
    mock_response.choices[0].message.tool_calls = None

    with patch("proteinclaw.agent.llm.litellm.completion", return_value=mock_response):
        msg = call_llm(
            model="gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )
    assert msg.content == "Hello"
    assert msg.tool_calls is None

def test_call_llm_with_tool_call():
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "echo"
    mock_tool_call.function.arguments = '{"text": "hello"}'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tool_call]

    with patch("proteinclaw.agent.llm.litellm.completion", return_value=mock_response):
        msg = call_llm(
            model="gpt-4o",
            messages=[{"role": "user", "content": "echo hello"}],
            tools=[],
        )
    assert msg.tool_calls is not None
    assert msg.tool_calls[0].function.name == "echo"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinclaw/test_llm.py -v
```

- [ ] **Step 3: Implement `proteinclaw/agent/llm.py`**

```python
from __future__ import annotations
import json
from typing import Any, Generator
import litellm
from proteinclaw.config import SUPPORTED_MODELS


def build_tools_schema(tools: dict) -> list[dict]:
    """Convert TOOL_REGISTRY entries to OpenAI function-calling schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools.values()
    ]


def _get_litellm_kwargs(model: str) -> dict[str, Any]:
    cfg = SUPPORTED_MODELS.get(model, {})
    kwargs: dict[str, Any] = {"model": model}
    if "api_base" in cfg:
        kwargs["api_base"] = cfg["api_base"]
    return kwargs


def call_llm(model: str, messages: list[dict], tools: list[dict]):
    """Single (non-streaming) LLM call. Returns the response message object."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(
        messages=messages,
        tools=tools or None,
        tool_choice="auto" if tools else None,
        **kwargs,
    )
    return response.choices[0].message


def call_llm_stream(model: str, messages: list[dict]) -> Generator[str, None, None]:
    """Streaming LLM call (no tools). Yields text tokens."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(messages=messages, stream=True, **kwargs)
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinclaw/test_llm.py -v
```

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/agent/llm.py tests/proteinclaw/test_llm.py
git commit -m "feat(proteinclaw): add LiteLLM wrapper with tool schema builder"
```

---

## Task 7: ProteinClaw — System Prompt

**Files:**
- Create: `proteinclaw/agent/prompt.py`
- Create: `tests/proteinclaw/test_prompt.py`

- [ ] **Step 1: Write failing test**

```python
# tests/proteinclaw/test_prompt.py
from proteinbox.tools.registry import ProteinTool, ToolResult
from proteinclaw.agent.prompt import build_system_prompt

class FakeTool(ProteinTool):
    name: str = "fake_tool"
    description: str = "Does something fake"
    parameters: dict = {}
    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=None)

def test_build_system_prompt_contains_tool_name():
    prompt = build_system_prompt({"fake_tool": FakeTool()})
    assert "fake_tool" in prompt

def test_build_system_prompt_contains_tool_description():
    prompt = build_system_prompt({"fake_tool": FakeTool()})
    assert "Does something fake" in prompt

def test_build_system_prompt_empty_tools():
    prompt = build_system_prompt({})
    assert isinstance(prompt, str)
    assert len(prompt) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinclaw/test_prompt.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `proteinclaw/agent/prompt.py`**

```python
from proteinbox.tools.registry import ProteinTool

SYSTEM_TEMPLATE = """\
You are ProteinClaw, an expert AI assistant for protein bioinformatics research.

You have access to the following tools:
{tool_descriptions}

When answering questions:
1. Identify which tools are needed to answer the question.
2. Call tools in a logical order, using previous results to inform next steps.
3. Synthesize all tool results into a clear, concise answer for the researcher.
4. If a tool fails, explain what went wrong and suggest alternatives.

Always cite the data source (e.g., UniProt, NCBI BLAST) when reporting results.
"""


def build_system_prompt(tools: dict[str, ProteinTool]) -> str:
    tool_descriptions = "\n".join(
        f"- **{tool.name}**: {tool.description}" for tool in tools.values()
    )
    return SYSTEM_TEMPLATE.format(tool_descriptions=tool_descriptions)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinclaw/test_prompt.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/agent/prompt.py tests/proteinclaw/test_prompt.py
git commit -m "feat(proteinclaw): add system prompt builder"
```

---

## Task 8: ProteinClaw — ReAct Agent Loop

**Files:**
- Create: `proteinclaw/agent/loop.py`
- Create: `tests/proteinclaw/test_loop.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinclaw/test_loop.py
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from proteinclaw.agent.loop import run_agent
from proteinbox.tools.registry import ProteinTool, ToolResult, TOOL_REGISTRY

class FakeUniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = "Fake UniProt"
    parameters: dict = {"type": "object", "properties": {"accession_id": {"type": "string"}}, "required": ["accession_id"]}
    def run(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"name": "TP53", "organism": "Homo sapiens"}, display="TP53 — Homo sapiens")

@pytest.fixture(autouse=True)
def patch_registry():
    with patch.dict(TOOL_REGISTRY, {"uniprot": FakeUniProtTool()}, clear=True):
        yield

def _make_tool_call_msg(tool_name: str, args: dict):
    tc = MagicMock()
    tc.id = "call_123"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    return msg

def _make_final_msg(content: str):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    return msg

@pytest.mark.asyncio
async def test_agent_calls_tool_then_answers():
    events = []

    call_sequence = [
        _make_tool_call_msg("uniprot", {"accession_id": "P04637"}),
        _make_final_msg("P04637 is TP53 from Homo sapiens."),
    ]
    call_iter = iter(call_sequence)

    with patch("proteinclaw.agent.loop.call_llm", side_effect=lambda **kw: next(call_iter)):
        async for event in run_agent(
            message="What is P04637?",
            model="gpt-4o",
            history=[],
        ):
            events.append(event)

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    final_tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert "TP53" in final_tokens

@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    # Always returns a tool call — should stop after max_steps
    def always_tool(**kw):
        return _make_tool_call_msg("uniprot", {"accession_id": "P04637"})

    events = []
    with patch("proteinclaw.agent.loop.call_llm", side_effect=always_tool):
        async for event in run_agent(
            message="loop forever",
            model="gpt-4o",
            history=[],
            max_steps=3,
        ):
            events.append(event)

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "max" in error_events[0]["message"].lower() or "step" in error_events[0]["message"].lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinclaw/test_loop.py -v
```

- [ ] **Step 3: Implement `proteinclaw/agent/loop.py`**

```python
from __future__ import annotations
import json
from typing import AsyncIterator
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
from proteinclaw.agent.llm import call_llm, call_llm_stream, build_tools_schema
from proteinclaw.agent.prompt import build_system_prompt


async def run_agent(
    message: str,
    model: str,
    history: list[dict],
    max_steps: int = 10,
) -> AsyncIterator[dict]:
    """
    Run the ReAct agent loop. Yields WebSocket event dicts:
      {"type": "thinking",    "content": str}
      {"type": "tool_call",   "tool": str, "args": dict}
      {"type": "observation", "tool": str, "result": dict}
      {"type": "token",       "content": str}
      {"type": "done"}
      {"type": "error",       "message": str}
    """
    tools = discover_tools()
    tools_schema = build_tools_schema(tools)
    system_prompt = build_system_prompt(tools)

    messages: list[dict] = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": message}]
    )

    for step in range(max_steps):
        response_msg = call_llm(model=model, messages=messages, tools=tools_schema)

        # Tool call branch
        if response_msg.tool_calls:
            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in response_msg.tool_calls
                ],
            })

            for tc in response_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "tool": tool_name, "args": args}

                tool = tools.get(tool_name)
                if tool is None:
                    tool_result_dict = {"success": False, "error": f"Tool '{tool_name}' not found"}
                else:
                    result = tool.run(**args)
                    tool_result_dict = result.model_dump()

                yield {"type": "observation", "tool": tool_name, "result": tool_result_dict}

                # Append tool result as tool message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result_dict),
                })

        # Final answer branch — stream the response
        else:
            final_content = response_msg.content or ""
            # Yield content as tokens (split by word for streaming feel if not using stream=True)
            for token in final_content.split(" "):
                yield {"type": "token", "content": token + " "}
            yield {"type": "done"}
            return

    # Exceeded max_steps
    yield {"type": "error", "message": f"Reached max_steps ({max_steps}) without a final answer."}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/proteinclaw/test_loop.py -v
```

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/agent/loop.py tests/proteinclaw/test_loop.py
git commit -m "feat(proteinclaw): add ReAct agent loop"
```

---

## Task 9: ProteinClaw — FastAPI App + REST Endpoints

**Files:**
- Create: `proteinclaw/main.py`
- Create: `proteinclaw/api/tools.py`
- Create: `proteinclaw/api/chat.py`
- Create: `tests/proteinclaw/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/proteinclaw/test_api.py
import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from proteinclaw.main import app

@pytest.mark.asyncio
async def test_get_tools():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)

@pytest.mark.asyncio
async def test_post_chat():
    async def mock_agent(**kwargs):
        yield {"type": "token", "content": "Hello "}
        yield {"type": "token", "content": "world"}
        yield {"type": "done"}

    with patch("proteinclaw.api.chat.run_agent", side_effect=mock_agent):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={
                "message": "What is P04637?",
                "model": "gpt-4o",
                "history": [],
            })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Hello" in data["reply"]
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/proteinclaw/test_api.py -v
```

- [ ] **Step 3: Implement `proteinclaw/api/tools.py`**

```python
from fastapi import APIRouter
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY

router = APIRouter()

# Discover all tools once at import time (populates TOOL_REGISTRY)
discover_tools()

@router.get("/tools")
def list_tools():
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in TOOL_REGISTRY.values()
        ]
    }
```

- [ ] **Step 4: Implement `proteinclaw/api/chat.py`**

```python
from fastapi import APIRouter
from pydantic import BaseModel
from proteinclaw.agent.loop import run_agent
from proteinclaw.config import SUPPORTED_MODELS, settings

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str = settings.default_model
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    model = request.model if request.model in SUPPORTED_MODELS else settings.default_model
    reply_parts = []
    tool_calls_log = []

    async for event in run_agent(
        message=request.message,
        model=model,
        history=request.history,
    ):
        if event["type"] == "token":
            reply_parts.append(event["content"])
        elif event["type"] == "tool_call":
            tool_calls_log.append(event)
        elif event["type"] == "error":
            reply_parts.append(f"\n[Error: {event['message']}]")

    return ChatResponse(reply="".join(reply_parts).strip(), tool_calls=tool_calls_log)
```

- [ ] **Step 5: Implement `proteinclaw/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.api.tools import router as tools_router
from proteinclaw.api.chat import router as chat_router

app = FastAPI(title="ProteinClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools_router)
app.include_router(chat_router)
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/proteinclaw/test_api.py -v
```

- [ ] **Step 7: Commit**

```bash
git add proteinclaw/main.py proteinclaw/api/tools.py proteinclaw/api/chat.py tests/proteinclaw/test_api.py
git commit -m "feat(proteinclaw): add FastAPI app with GET /tools and POST /chat"
```

---

## Task 10: ProteinClaw — WebSocket Streaming Endpoint

**Files:**
- Modify: `proteinclaw/api/chat.py` (add WebSocket route)
- Modify: `tests/proteinclaw/test_api.py` (add WebSocket test)

- [ ] **Step 1: Write failing WebSocket test** (add to `tests/proteinclaw/test_api.py`)

```python
@pytest.mark.asyncio
async def test_websocket_chat():
    async def mock_agent(**kwargs):
        yield {"type": "tool_call", "tool": "uniprot", "args": {"accession_id": "P04637"}}
        yield {"type": "observation", "tool": "uniprot", "result": {"success": True, "data": {"name": "TP53"}}}
        yield {"type": "token", "content": "TP53 is "}
        yield {"type": "token", "content": "a tumor suppressor."}
        yield {"type": "done"}

    with patch("proteinclaw.api.chat.run_agent", side_effect=mock_agent):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.websocket_connect("/ws/chat") as ws:
                await ws.send_json({
                    "message": "What is P04637?",
                    "model": "gpt-4o",
                    "history": [],
                })
                events = []
                while True:
                    event = await ws.receive_json()
                    events.append(event)
                    if event["type"] in ("done", "error"):
                        break

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    assert "done" in types
```

Note: `httpx` WebSocket support requires `httpx>=0.27` and `anyio`. Add `httpx[ws]` to `pyproject.toml` dev dependencies.

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinclaw/test_api.py::test_websocket_chat -v
```

Expected: `ImportError` or missing route.

- [ ] **Step 3: Add WebSocket route to `proteinclaw/api/chat.py`**

Add after the `POST /chat` route:

```python
import json
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            message = payload.get("message", "")
            model = payload.get("model", settings.default_model)
            history = payload.get("history", [])

            if model not in SUPPORTED_MODELS:
                model = settings.default_model

            async for event in run_agent(message=message, model=model, history=history):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Run WebSocket test to verify it passes**

```bash
pytest tests/proteinclaw/test_api.py::test_websocket_chat -v
```

Expected: 1 passed.

- [ ] **Step 5: Manual smoke test (requires a real LLM key)**

```bash
# Start the server
uvicorn proteinclaw.main:app --reload --port 8000

# In another terminal, use websocat:
# echo '{"message":"What is P04637?","model":"gpt-4o","history":[]}' | websocat ws://localhost:8000/ws/chat
```

Expected: stream of JSON events ending with `{"type":"done"}`.

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/api/chat.py tests/proteinclaw/test_api.py
git commit -m "feat(proteinclaw): add WebSocket /ws/chat streaming endpoint"
```

---

## Task 11: Frontend — Vite Scaffold + Types

**Files:**
- Create: `frontend/` (Vite + React + TypeScript project)
- Create: `frontend/src/types.ts`

- [ ] **Step 1: Scaffold the frontend**

```bash
cd frontend && npm create vite@latest . -- --template react-ts
npm install
```

- [ ] **Step 2: Create `frontend/src/types.ts`**

```typescript
export type WsEventType =
  | "thinking"
  | "tool_call"
  | "observation"
  | "token"
  | "done"
  | "error";

export interface WsEvent {
  type: WsEventType;
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  message?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: WsEvent[];
}

export interface SendPayload {
  message: string;
  model: string;
  history: Array<{ role: string; content: string }>;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "chore(frontend): scaffold Vite + React + TypeScript project"
```

---

## Task 12: Frontend — ModelSelector

**Files:**
- Create: `frontend/src/components/ModelSelector.tsx`

- [ ] **Step 1: Implement `ModelSelector.tsx`**

```typescript
import { useEffect, useState } from "react";

const MODELS = [
  "gpt-4o",
  "claude-opus-4-5",
  "deepseek-chat",
  "deepseek-reasoner",
  "minimax-text-01",
  "ollama/llama3",
];

const STORAGE_KEY = "proteinclaw_model";

interface Props {
  value: string;
  onChange: (model: string) => void;
}

export function ModelSelector({ value, onChange }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => {
        localStorage.setItem(STORAGE_KEY, e.target.value);
        onChange(e.target.value);
      }}
      style={{ marginLeft: "auto", padding: "4px 8px" }}
    >
      {MODELS.map((m) => (
        <option key={m} value={m}>
          {m}
        </option>
      ))}
    </select>
  );
}

export function useStoredModel(): [string, (m: string) => void] {
  const [model, setModel] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? "gpt-4o"
  );
  return [model, setModel];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ModelSelector.tsx
git commit -m "feat(frontend): add ModelSelector component"
```

---

## Task 13: Frontend — ToolCallCard

**Files:**
- Create: `frontend/src/components/ToolCallCard.tsx`

- [ ] **Step 1: Implement `ToolCallCard.tsx`**

```typescript
import { useState } from "react";
import { WsEvent } from "../types";

interface Props {
  toolCall: WsEvent;
  observation?: WsEvent;
}

export function ToolCallCard({ toolCall, observation }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: 6,
        margin: "4px 0",
        fontSize: 13,
        background: "#f9f9f9",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "6px 10px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontWeight: 500,
        }}
      >
        {open ? "▼" : "▶"} Tool: <code>{toolCall.tool}</code>
        {observation && (observation.result as any)?.success === false && (
          <span style={{ color: "red", marginLeft: 8 }}>✗ failed</span>
        )}
        {observation && (observation.result as any)?.success === true && (
          <span style={{ color: "green", marginLeft: 8 }}>✓</span>
        )}
      </button>
      {open && (
        <div style={{ padding: "0 10px 8px", borderTop: "1px solid #eee" }}>
          <div style={{ marginTop: 6 }}>
            <strong>Args:</strong>
            <pre style={{ margin: "4px 0", overflowX: "auto" }}>
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {observation && (
            <div style={{ marginTop: 6 }}>
              <strong>Result:</strong>
              <pre style={{ margin: "4px 0", overflowX: "auto" }}>
                {JSON.stringify(observation.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ToolCallCard.tsx
git commit -m "feat(frontend): add ToolCallCard component"
```

---

## Task 14: Frontend — ChatWindow + useChat Hook

**Files:**
- Create: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/components/ChatWindow.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Implement `frontend/src/hooks/useChat.ts`**

```typescript
import { useState, useCallback, useRef } from "react";
import { ChatMessage, WsEvent, SendPayload } from "../types";

const WS_URL = "ws://localhost:8000/ws/chat";

// Stable unique ID for tracking the assistant message being built
let msgIdCounter = 0;

interface TrackedMessage extends ChatMessage {
  id: number;
}

export function useChat() {
  const [messages, setMessages] = useState<TrackedMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const send = useCallback((text: string, model: string) => {
    setLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    const userMsg: TrackedMessage = { id: msgIdCounter++, role: "user", content: text };
    const assistantId = msgIdCounter++;
    const assistantMsg: TrackedMessage = { id: assistantId, role: "assistant", content: "", toolCalls: [] };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    const payload: SendPayload = { message: text, model, history };
    ws.onopen = () => ws.send(JSON.stringify(payload));

    ws.onmessage = (e) => {
      const event: WsEvent = JSON.parse(e.data);

      // Update the assistant message by stable ID (not array index)
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== assistantId) return msg;
          const updated = { ...msg };
          if (event.type === "thinking") {
            updated.content += `\n_${event.content}_`;
          } else if (event.type === "tool_call" || event.type === "observation") {
            updated.toolCalls = [...(updated.toolCalls ?? []), event];
          } else if (event.type === "token") {
            updated.content += event.content ?? "";
          } else if (event.type === "error") {
            updated.content += `\n[Error: ${event.message}]`;
          }
          return updated;
        })
      );

      if (event.type === "done" || event.type === "error") {
        setLoading(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      setLoading(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: "[WebSocket connection error]" }
            : msg
        )
      );
    };
  }, [messages]);

  return { messages, loading, send };
}
```

- [ ] **Step 2: Implement `frontend/src/components/ChatWindow.tsx`**

```typescript
import { useState, useRef, useEffect } from "react";
import { ChatMessage, WsEvent } from "../types";
import { ToolCallCard } from "./ToolCallCard";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (text: string) => void;
}

export function ChatWindow({ messages, loading, onSend }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", maxWidth: 800, margin: "0 auto" }}>
      {/* Message list */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {msg.role === "user" ? "You" : "ProteinClaw"}
            </div>

            {/* Tool call cards */}
            {msg.toolCalls && (() => {
              const calls = msg.toolCalls.filter((e) => e.type === "tool_call");
              const obs = msg.toolCalls.filter((e) => e.type === "observation");
              return calls.map((tc, j) => (
                <ToolCallCard key={j} toolCall={tc} observation={obs[j]} />
              ));
            })()}

            {/* Message content */}
            <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
          </div>
        ))}
        {loading && <div style={{ color: "#888", fontStyle: "italic" }}>ProteinClaw is thinking...</div>}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ display: "flex", padding: 16, borderTop: "1px solid #ddd" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a protein, e.g. 'What is P04637?'"
          disabled={loading}
          style={{ flex: 1, padding: "8px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #ccc" }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{ marginLeft: 8, padding: "8px 16px", borderRadius: 4, cursor: "pointer" }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Wire up `frontend/src/App.tsx`**

```typescript
import { ChatWindow } from "./components/ChatWindow";
import { ModelSelector, useStoredModel } from "./components/ModelSelector";
import { useChat } from "./hooks/useChat";

export default function App() {
  const [model, setModel] = useStoredModel();
  const { messages, loading, send } = useChat();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "sans-serif" }}>
      <header style={{ display: "flex", alignItems: "center", padding: "8px 16px", borderBottom: "1px solid #ddd" }}>
        <h2 style={{ margin: 0 }}>ProteinClaw</h2>
        <ModelSelector value={model} onChange={setModel} />
      </header>
      <main style={{ flex: 1, overflow: "hidden" }}>
        <ChatWindow messages={messages} loading={loading} onSend={(text) => send(text, model)} />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: No TypeScript errors, `dist/` created.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add ChatWindow, useChat hook, and App layout"
```

---

## Task 15: Docker Compose

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - .:/app
    command: uvicorn proteinclaw.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host

  ollama:
    image: ollama/ollama
    profiles: ["ollama"]
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

- [ ] **Step 2: Create `Dockerfile.backend`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --upgrade pip setuptools
COPY pyproject.toml .
COPY proteinbox/ ./proteinbox/
COPY proteinclaw/ ./proteinclaw/
RUN pip install .
```

- [ ] **Step 3: Create `Dockerfile.frontend`**

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml Dockerfile.backend Dockerfile.frontend
git commit -m "chore: add Docker Compose with backend, frontend, and optional ollama"
```

---

## Task 16: Run Full Test Suite

- [ ] **Step 1: Run all backend tests**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Start backend and verify smoke test**

```bash
uvicorn proteinclaw.main:app --reload --port 8000
curl http://localhost:8000/tools
```

Expected: JSON with `uniprot` and `blast` tools listed.

- [ ] **Step 3: Start frontend dev server**

```bash
cd frontend && npm run dev
```

Expected: Vite reports `http://localhost:5173` ready.

- [ ] **Step 4: Push to GitHub**

```bash
git push origin main
```
