# New Tools Round 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 20 new tools to `proteinbox/api_tools/` covering protein evolution, enzyme kinetics, proteomics, complexes, drug binding, and structural features.

**Architecture:** Each tool is a standalone file in `proteinbox/api_tools/` using the `@register_tool` decorator on a class that extends `ProteinTool`. The registry auto-discovers all files in that directory at startup — no other files need to change. Tests mock HTTP calls with `respx`.

**Tech Stack:** Python 3.11+, httpx, respx (tests), pydantic, proteinbox.tools.registry

---

## File Map

**Created (20 tool files):**
- `proteinbox/api_tools/eggnog.py`
- `proteinbox/api_tools/consurf.py`
- `proteinbox/api_tools/phylomedb.py`
- `proteinbox/api_tools/expasy_enzyme.py`
- `proteinbox/api_tools/brenda.py`
- `proteinbox/api_tools/sabio_rk.py`
- `proteinbox/api_tools/paxdb.py`
- `proteinbox/api_tools/proteomicsdb.py`
- `proteinbox/api_tools/pride.py`
- `proteinbox/api_tools/complex_portal.py`
- `proteinbox/api_tools/corum.py`
- `proteinbox/api_tools/bindingdb.py`
- `proteinbox/api_tools/dgidb.py`
- `proteinbox/api_tools/drugbank.py`
- `proteinbox/api_tools/dbptm.py`
- `proteinbox/api_tools/opm.py`
- `proteinbox/api_tools/imgt.py`
- `proteinbox/api_tools/scopedb.py`

**Created (18 test files):**
- `tests/proteinbox/test_eggnog.py`
- `tests/proteinbox/test_consurf.py`
- `tests/proteinbox/test_phylomedb.py`
- `tests/proteinbox/test_expasy_enzyme.py`
- `tests/proteinbox/test_brenda.py`
- `tests/proteinbox/test_sabio_rk.py`
- `tests/proteinbox/test_paxdb.py`
- `tests/proteinbox/test_proteomicsdb.py`
- `tests/proteinbox/test_pride.py`
- `tests/proteinbox/test_complex_portal.py`
- `tests/proteinbox/test_corum.py`
- `tests/proteinbox/test_bindingdb.py`
- `tests/proteinbox/test_dgidb.py`
- `tests/proteinbox/test_drugbank.py`
- `tests/proteinbox/test_dbptm.py`
- `tests/proteinbox/test_opm.py`
- `tests/proteinbox/test_imgt.py`
- `tests/proteinbox/test_scopedb.py`

**Modified (1 file):**
- `README.md` — update Supported Tools table (Task 20)

---

## Task 1: eggNOG — ortholog groups and functional categories

**Files:**
- Create: `proteinbox/api_tools/eggnog.py`
- Create: `tests/proteinbox/test_eggnog.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_eggnog.py
import respx
import httpx
from proteinbox.api_tools.eggnog import EggNOGTool

MOCK_RESPONSE = {
    "hits": [
        {
            "query": "TP53",
            "seed_eggNOG_ortholog": "9606.ENSP00000269305",
            "eggNOG_OGs": "COG0000@1|root,KOG0001@2759|Eukaryota",
            "COG_category": "K",
            "Description": "Tumor suppressor p53",
            "Preferred_name": "TP53",
            "GOs": "GO:0003677,GO:0005634",
            "max_annot_lvl": "Eukaryota",
        }
    ]
}

@respx.mock
def test_eggnog_success():
    respx.get("http://eggnog6.embl.de/api/emapper/annotations").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = EggNOGTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["preferred_name"] == "TP53"
    assert result.data["cog_category"] == "K"
    assert "GO:0003677" in result.data["go_terms"]

@respx.mock
def test_eggnog_not_found():
    respx.get("http://eggnog6.embl.de/api/emapper/annotations").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    tool = EggNOGTool()
    result = tool.run(gene="FAKEGENE999")
    assert result.success is True
    assert result.data["hits"] == 0

@respx.mock
def test_eggnog_api_error():
    respx.get("http://eggnog6.embl.de/api/emapper/annotations").mock(
        return_value=httpx.Response(500)
    )
    tool = EggNOGTool()
    result = tool.run(gene="TP53")
    assert result.success is False
    assert result.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_eggnog.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` — `eggnog.py` does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/eggnog.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class EggNOGTool(ProteinTool):
    name: str = "eggnog"
    description: str = (
        "Query eggNOG v6 for orthologous groups and functional categories. "
        "Returns COG category, orthologous group ID, GO terms, and functional "
        "description for a gene."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "http://eggnog6.embl.de/api/emapper/annotations",
                params={"query": gene, "tax_scope": "auto", "target_orthologs": "all"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"eggNOG returned {resp.status_code} for {gene}")

            hits = resp.json().get("hits", [])
            if not hits:
                return ToolResult(success=True, data={"gene": gene, "hits": 0}, display=f"No eggNOG entry for {gene}")

            hit = hits[0]
            go_terms = [g.strip() for g in hit.get("GOs", "").split(",") if g.strip()]
            ogs = hit.get("eggNOG_OGs", "")

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "hits": len(hits),
                    "preferred_name": hit.get("Preferred_name", gene),
                    "description": hit.get("Description", ""),
                    "cog_category": hit.get("COG_category", ""),
                    "orthologous_groups": ogs,
                    "go_terms": go_terms,
                    "max_annotation_level": hit.get("max_annot_lvl", ""),
                },
                display=f"{gene}: COG={hit.get('COG_category','?')}, {hit.get('Description','')} ({len(go_terms)} GO terms)",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_eggnog.py -v
```
Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/eggnog.py tests/proteinbox/test_eggnog.py
git commit -m "feat(tools): add eggnog tool for orthologous groups and COG categories"
```

---

## Task 2: ConSurf — per-residue evolutionary conservation

**Files:**
- Create: `proteinbox/api_tools/consurf.py`
- Create: `tests/proteinbox/test_consurf.py`

> **Note:** ConSurf DB serves pre-computed results. Verify the endpoint at https://consurf.tau.ac.il before coding. If the REST endpoint is unavailable, fall back to parsing the downloadable grades file via `https://consurf.tau.ac.il/results/{uniprot_id}/consurf.grades`.

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_consurf.py
import respx
import httpx
from proteinbox.api_tools.consurf import ConSurfTool

MOCK_RESPONSE = {
    "uniprot_id": "P04637",
    "pdb_id": "2OCJ",
    "grades": [
        {"position": 1, "residue": "M", "score": 1.234, "grade": 9, "color": "maroon"},
        {"position": 2, "residue": "E", "score": -0.512, "grade": 5, "color": "white"},
        {"position": 3, "residue": "E", "score": -1.123, "grade": 1, "color": "turquoise"},
    ],
    "summary": {"conserved": 150, "average": 100, "variable": 143},
}

@respx.mock
def test_consurf_success():
    respx.get("https://consurf.tau.ac.il/api/grades/P04637").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = ConSurfTool()
    result = tool.run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["uniprot_id"] == "P04637"
    assert result.data["conserved_count"] == 150
    assert result.data["variable_count"] == 143
    assert len(result.data["top_conserved"]) > 0

@respx.mock
def test_consurf_not_found():
    respx.get("https://consurf.tau.ac.il/api/grades/FAKEID").mock(
        return_value=httpx.Response(404)
    )
    tool = ConSurfTool()
    result = tool.run(uniprot_id="FAKEID")
    assert result.success is False
    assert result.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_consurf.py -v
```
Expected: `ImportError` — `consurf.py` does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/consurf.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class ConSurfTool(ProteinTool):
    name: str = "consurf"
    description: str = (
        "Query ConSurf DB for per-residue evolutionary conservation scores. "
        "Returns conservation grades (1=variable to 9=conserved), counts of "
        "conserved/variable positions, and top conserved residues."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {"type": "string", "description": "UniProt accession (e.g. P04637)"},
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uid = kwargs["uniprot_id"].strip().upper()
        try:
            resp = httpx.get(
                f"https://consurf.tau.ac.il/api/grades/{uid}",
                timeout=30,
            )
            if resp.status_code == 404:
                return ToolResult(success=False, error=f"No ConSurf entry for {uid}")
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"ConSurf returned {resp.status_code} for {uid}")

            data = resp.json()
            grades = data.get("grades", [])
            summary = data.get("summary", {})

            # Top 5 most conserved residues (grade 9)
            top_conserved = [
                {"position": g["position"], "residue": g["residue"], "grade": g["grade"]}
                for g in grades if g.get("grade", 0) == 9
            ][:5]

            return ToolResult(
                success=True,
                data={
                    "uniprot_id": uid,
                    "pdb_id": data.get("pdb_id"),
                    "total_residues": len(grades),
                    "conserved_count": summary.get("conserved", 0),
                    "average_count": summary.get("average", 0),
                    "variable_count": summary.get("variable", 0),
                    "top_conserved": top_conserved,
                },
                display=(
                    f"{uid}: {summary.get('conserved', 0)} conserved, "
                    f"{summary.get('variable', 0)} variable residues out of {len(grades)}"
                ),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_consurf.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/consurf.py tests/proteinbox/test_consurf.py
git commit -m "feat(tools): add consurf tool for per-residue evolutionary conservation"
```

---

## Task 3: PhylomeDB — phylogenetic trees and orthologs

**Files:**
- Create: `proteinbox/api_tools/phylomedb.py`
- Create: `tests/proteinbox/test_phylomedb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_phylomedb.py
import respx
import httpx
from proteinbox.api_tools.phylomedb import PhylomeDBTool

SEARCH_RESPONSE = {"proteins": [{"protid": "Hs_TP53", "phylomes": ["1", "14"]}]}
ORTHOLOGS_RESPONSE = {
    "orthologs": [
        {"protid": "Mm_Trp53", "species": "Mus musculus", "type": "1:1", "identity": 0.77},
        {"protid": "Dr_tp53", "species": "Danio rerio", "type": "1:1", "identity": 0.56},
    ]
}

@respx.mock
def test_phylomedb_success():
    respx.get("http://phylomedb.org/api/search/protein/TP53").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    respx.get("http://phylomedb.org/api/orthologs/Hs_TP53").mock(
        return_value=httpx.Response(200, json=ORTHOLOGS_RESPONSE)
    )
    tool = PhylomeDBTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["protein_id"] == "Hs_TP53"
    assert result.data["ortholog_count"] == 2
    assert result.data["orthologs"][0]["species"] == "Mus musculus"

@respx.mock
def test_phylomedb_not_found():
    respx.get("http://phylomedb.org/api/search/protein/FAKEGENE").mock(
        return_value=httpx.Response(200, json={"proteins": []})
    )
    tool = PhylomeDBTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["ortholog_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_phylomedb.py -v
```
Expected: `ImportError` — `phylomedb.py` does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/phylomedb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class PhylomeDBTool(ProteinTool):
    name: str = "phylomedb"
    description: str = (
        "Query PhylomeDB for protein phylogenetic trees and orthologs. "
        "Returns ortholog list with species, orthology type (1:1, 1:many), "
        "and sequence identity."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            search = httpx.get(
                f"http://phylomedb.org/api/search/protein/{gene}",
                timeout=30,
            )
            if search.status_code != 200:
                return ToolResult(success=False, error=f"PhylomeDB search returned {search.status_code}")

            proteins = search.json().get("proteins", [])
            if not proteins:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "ortholog_count": 0},
                    display=f"No PhylomeDB entry for {gene}",
                )

            prot_id = proteins[0]["protid"]
            orth_resp = httpx.get(
                f"http://phylomedb.org/api/orthologs/{prot_id}",
                timeout=30,
            )
            if orth_resp.status_code != 200:
                return ToolResult(success=False, error=f"PhylomeDB orthologs returned {orth_resp.status_code}")

            orthologs = orth_resp.json().get("orthologs", [])
            top = [
                {
                    "protein_id": o["protid"],
                    "species": o["species"],
                    "type": o.get("type", ""),
                    "identity": round(o.get("identity", 0), 3),
                }
                for o in orthologs[:10]
            ]

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "protein_id": prot_id,
                    "phylome_ids": proteins[0].get("phylomes", []),
                    "ortholog_count": len(orthologs),
                    "orthologs": top,
                },
                display=f"{gene} ({prot_id}): {len(orthologs)} orthologs across species",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_phylomedb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/phylomedb.py tests/proteinbox/test_phylomedb.py
git commit -m "feat(tools): add phylomedb tool for phylogenetic orthologs"
```

---

## Task 4: ExPASy ENZYME — EC number and reaction lookup

**Files:**
- Create: `proteinbox/api_tools/expasy_enzyme.py`
- Create: `tests/proteinbox/test_expasy_enzyme.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_expasy_enzyme.py
import respx
import httpx
from proteinbox.api_tools.expasy_enzyme import ExPASyEnzymeTool

MOCK_JSON = {
    "results": [
        {
            "ec": "2.7.11.1",
            "name": "non-specific serine/threonine protein kinase",
            "reaction": "ATP + a protein = ADP + a phosphoprotein",
            "cofactor": ["Mg(2+)"],
            "comments": "Wide specificity.",
            "uniprot_count": 1234,
        }
    ]
}

@respx.mock
def test_expasy_enzyme_by_ec():
    respx.get("https://enzyme.expasy.org/api/enzyme/2.7.11.1").mock(
        return_value=httpx.Response(200, json=MOCK_JSON)
    )
    tool = ExPASyEnzymeTool()
    result = tool.run(ec_number="2.7.11.1")
    assert result.success is True
    assert result.data["ec"] == "2.7.11.1"
    assert "ATP" in result.data["reaction"]
    assert result.data["cofactors"] == ["Mg(2+)"]

@respx.mock
def test_expasy_enzyme_not_found():
    respx.get("https://enzyme.expasy.org/api/enzyme/9.9.9.9").mock(
        return_value=httpx.Response(404)
    )
    tool = ExPASyEnzymeTool()
    result = tool.run(ec_number="9.9.9.9")
    assert result.success is False
    assert "9.9.9.9" in result.error
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_expasy_enzyme.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/expasy_enzyme.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class ExPASyEnzymeTool(ProteinTool):
    name: str = "expasy_enzyme"
    description: str = (
        "Query ExPASy ENZYME for enzyme classification and reaction details. "
        "Returns EC number, accepted name, reaction equation, cofactors, and "
        "number of characterized UniProt entries."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "ec_number": {"type": "string", "description": "EC number (e.g. 2.7.11.1)"},
        },
        "required": ["ec_number"],
    }

    def run(self, **kwargs) -> ToolResult:
        ec = kwargs["ec_number"].strip()
        try:
            resp = httpx.get(
                f"https://enzyme.expasy.org/api/enzyme/{ec}",
                timeout=30,
            )
            if resp.status_code == 404:
                return ToolResult(success=False, error=f"EC {ec} not found in ExPASy ENZYME")
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"ExPASy ENZYME returned {resp.status_code}")

            results = resp.json().get("results", [])
            if not results:
                return ToolResult(success=False, error=f"No results for EC {ec}")

            r = results[0]
            return ToolResult(
                success=True,
                data={
                    "ec": r.get("ec", ec),
                    "name": r.get("name", ""),
                    "reaction": r.get("reaction", ""),
                    "cofactors": r.get("cofactor", []),
                    "comments": r.get("comments", ""),
                    "uniprot_count": r.get("uniprot_count", 0),
                },
                display=f"EC {ec}: {r.get('name','')} — {r.get('reaction','')}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_expasy_enzyme.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/expasy_enzyme.py tests/proteinbox/test_expasy_enzyme.py
git commit -m "feat(tools): add expasy_enzyme tool for EC number and reaction lookup"
```

---

## Task 5: BRENDA — enzyme kinetics database

**Files:**
- Create: `proteinbox/api_tools/brenda.py`
- Create: `tests/proteinbox/test_brenda.py`

> **Note:** BRENDA uses a SOAP API. This implementation makes raw XML/SOAP POST requests via httpx. Register for free at https://www.brenda-enzymes.org to get credentials. Credentials are read from environment variables `BRENDA_EMAIL` and `BRENDA_PASSWORD`, or from `~/.config/proteinclaw/config.toml`.

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_brenda.py
import respx
import httpx
from proteinbox.api_tools.brenda import BRENDATool

SOAP_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
  <SOAP-ENV:Body>
    <ns1:getKmValueResponse>
      <return>
        2.7.11.1#Km value#0.05#mM#ATP#Homo sapiens#PubMed:12345678!
        2.7.11.1#Km value#0.12#mM#substrate#Homo sapiens#PubMed:87654321
      </return>
    </ns1:getKmValueResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

@respx.mock
def test_brenda_success():
    respx.post("https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl").mock(
        return_value=httpx.Response(200, content=SOAP_RESPONSE)
    )
    tool = BRENDATool()
    result = tool.run(ec_number="2.7.11.1", organism="Homo sapiens")
    assert result.success is True
    assert result.data["ec_number"] == "2.7.11.1"
    assert len(result.data["km_values"]) >= 1

@respx.mock
def test_brenda_api_error():
    respx.post("https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl").mock(
        return_value=httpx.Response(500)
    )
    tool = BRENDATool()
    result = tool.run(ec_number="2.7.11.1", organism="Homo sapiens")
    assert result.success is False
    assert result.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_brenda.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/brenda.py
import hashlib
import os
import httpx
from xml.etree import ElementTree as ET
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

BRENDA_URL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"

def _get_credentials() -> tuple[str, str]:
    email = os.environ.get("BRENDA_EMAIL", "")
    password = os.environ.get("BRENDA_PASSWORD", "")
    if not email or not password:
        try:
            from proteinclaw.core.config import load_user_config
            import os as _os
            load_user_config()
            email = _os.environ.get("BRENDA_EMAIL", email)
            password = _os.environ.get("BRENDA_PASSWORD", password)
        except Exception:
            pass
    password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
    return email, password_hash

def _soap_request(method: str, params: str) -> httpx.Response:
    email, pwd_hash = _get_credentials()
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:ns1="https://www.brenda-enzymes.org">
  <SOAP-ENV:Body>
    <ns1:{method}>
      <parameters>{email},{pwd_hash},{params}</parameters>
    </ns1:{method}>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""
    return httpx.post(
        BRENDA_URL,
        content=body.encode(),
        headers={"Content-Type": "text/xml; charset=utf-8"},
        timeout=30,
    )

def _parse_soap_return(resp: httpx.Response) -> list[str]:
    root = ET.fromstring(resp.content)
    ns = {"s": "http://schemas.xmlsoap.org/soap/envelope/"}
    body = root.find(".//return")
    if body is None or not body.text:
        return []
    return [line.strip() for line in body.text.strip().split("!") if line.strip()]

@register_tool
class BRENDATool(ProteinTool):
    name: str = "brenda"
    description: str = (
        "Query BRENDA for enzyme kinetics data. Returns Km values, substrates, "
        "inhibitors, cofactors, and optimal pH/temperature for an EC number. "
        "Requires BRENDA_EMAIL and BRENDA_PASSWORD environment variables."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "ec_number": {"type": "string", "description": "EC number (e.g. 2.7.11.1)"},
            "organism": {"type": "string", "description": "Organism name", "default": "Homo sapiens"},
        },
        "required": ["ec_number"],
    }

    def run(self, **kwargs) -> ToolResult:
        ec = kwargs["ec_number"].strip()
        organism = kwargs.get("organism", "Homo sapiens").strip()
        try:
            resp = _soap_request("getKmValue", f"{ec}#kmValue*{organism}#")
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"BRENDA returned {resp.status_code}")

            lines = _parse_soap_return(resp)
            km_values = []
            for line in lines:
                parts = line.split("#")
                if len(parts) >= 5:
                    km_values.append({
                        "value": parts[2] if len(parts) > 2 else "",
                        "unit": parts[3] if len(parts) > 3 else "",
                        "substrate": parts[4] if len(parts) > 4 else "",
                        "organism": parts[5] if len(parts) > 5 else "",
                        "reference": parts[6] if len(parts) > 6 else "",
                    })

            return ToolResult(
                success=True,
                data={
                    "ec_number": ec,
                    "organism": organism,
                    "km_values": km_values[:10],
                },
                display=f"EC {ec} ({organism}): {len(km_values)} Km values found",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_brenda.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/brenda.py tests/proteinbox/test_brenda.py
git commit -m "feat(tools): add brenda tool for enzyme kinetics data"
```

---

## Task 6: SABIO-RK — biochemical reaction kinetics

**Files:**
- Create: `proteinbox/api_tools/sabio_rk.py`
- Create: `tests/proteinbox/test_sabio_rk.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_sabio_rk.py
import respx
import httpx
from proteinbox.api_tools.sabio_rk import SABIORKTool

MOCK_TSV = """EntryID\tReactionID\tEnzymeName\tParameter.type\tParameter.startValue\tParameter.unit\tOrganismName\tpH\tTemperature\tPubMedID
12345\t678\tp53\tKm\t0.05\tmM\tHomo sapiens\t7.4\t37\t12345678
12346\t678\tp53\tkcat\t1.2\ts^-1\tHomo sapiens\t7.4\t37\t12345678"""

@respx.mock
def test_sabio_rk_success():
    respx.get("http://sabiork.h-its.org/sabioRestWebServices/kineticlawsExportTsv").mock(
        return_value=httpx.Response(200, text=MOCK_TSV)
    )
    tool = SABIORKTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert result.data["entry_count"] == 2
    assert any(p["type"] == "Km" for p in result.data["parameters"])

@respx.mock
def test_sabio_rk_no_results():
    respx.get("http://sabiork.h-its.org/sabioRestWebServices/kineticlawsExportTsv").mock(
        return_value=httpx.Response(200, text="EntryID\tReactionID\n")
    )
    tool = SABIORKTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["entry_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_sabio_rk.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/sabio_rk.py
import io
import csv
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class SABIORKTool(ProteinTool):
    name: str = "sabio_rk"
    description: str = (
        "Query SABIO-RK for experimentally measured biochemical kinetic parameters. "
        "Returns Km, kcat, Vmax values with organism, pH, temperature, and reference."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene/enzyme name (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "http://sabiork.h-its.org/sabioRestWebServices/kineticlawsExportTsv",
                params={"EnzymeName": gene, "format": "tsv"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"SABIO-RK returned {resp.status_code}")

            reader = csv.DictReader(io.StringIO(resp.text), delimiter="\t")
            rows = list(reader)
            if not rows:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "entry_count": 0},
                    display=f"No kinetic data in SABIO-RK for {gene}",
                )

            params = [
                {
                    "type": r.get("Parameter.type", ""),
                    "value": r.get("Parameter.startValue", ""),
                    "unit": r.get("Parameter.unit", ""),
                    "organism": r.get("OrganismName", ""),
                    "pH": r.get("pH", ""),
                    "temperature": r.get("Temperature", ""),
                    "pubmed_id": r.get("PubMedID", ""),
                }
                for r in rows[:10]
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "entry_count": len(rows), "parameters": params},
                display=f"{gene}: {len(rows)} kinetic parameter entries in SABIO-RK",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_sabio_rk.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/sabio_rk.py tests/proteinbox/test_sabio_rk.py
git commit -m "feat(tools): add sabio_rk tool for biochemical reaction kinetics"
```

---

## Task 7: PaxDb — protein abundance across species

**Files:**
- Create: `proteinbox/api_tools/paxdb.py`
- Create: `tests/proteinbox/test_paxdb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_paxdb.py
import respx
import httpx
from proteinbox.api_tools.paxdb import PaxDbTool

SEARCH_RESPONSE = [{"uniprotAc": "P04637", "name": "TP53_HUMAN"}]
ABUNDANCE_RESPONSE = {
    "abundances": [
        {"dataset": {"organ": "liver"}, "abundance": 12.5},
        {"dataset": {"organ": "brain"}, "abundance": 8.3},
    ],
    "integrated": 10.2,
}

@respx.mock
def test_paxdb_success():
    respx.get("https://pax-db.org/api/v1/search/protein/TP53").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    respx.get("https://pax-db.org/api/v1/proteins/P04637/abundances").mock(
        return_value=httpx.Response(200, json=ABUNDANCE_RESPONSE)
    )
    tool = PaxDbTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["uniprot_id"] == "P04637"
    assert result.data["integrated_score"] == 10.2
    assert len(result.data["tissues"]) == 2

@respx.mock
def test_paxdb_not_found():
    respx.get("https://pax-db.org/api/v1/search/protein/FAKEGENE").mock(
        return_value=httpx.Response(200, json=[])
    )
    tool = PaxDbTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["tissues"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_paxdb.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/paxdb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class PaxDbTool(ProteinTool):
    name: str = "paxdb"
    description: str = (
        "Query PaxDb for protein abundance across tissues and species. "
        "Returns abundance in ppm (parts per million) per tissue, integrated "
        "whole-organism score, and dataset count."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            search = httpx.get(
                f"https://pax-db.org/api/v1/search/protein/{gene}",
                timeout=30,
            )
            if search.status_code != 200:
                return ToolResult(success=False, error=f"PaxDb search returned {search.status_code}")

            results = search.json()
            if not results:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "tissues": [], "integrated_score": None},
                    display=f"No PaxDb entry for {gene}",
                )

            uid = results[0]["uniprotAc"]
            abund = httpx.get(
                f"https://pax-db.org/api/v1/proteins/{uid}/abundances",
                timeout=30,
            )
            if abund.status_code != 200:
                return ToolResult(success=False, error=f"PaxDb abundance returned {abund.status_code}")

            data = abund.json()
            tissues = [
                {
                    "tissue": a["dataset"].get("organ", "unknown"),
                    "abundance_ppm": a.get("abundance"),
                }
                for a in data.get("abundances", [])
            ]
            tissues_sorted = sorted(tissues, key=lambda x: x["abundance_ppm"] or 0, reverse=True)

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "uniprot_id": uid,
                    "integrated_score": data.get("integrated"),
                    "tissue_count": len(tissues),
                    "tissues": tissues_sorted[:10],
                },
                display=f"{gene} ({uid}): integrated score {data.get('integrated')} ppm across {len(tissues)} tissues",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_paxdb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/paxdb.py tests/proteinbox/test_paxdb.py
git commit -m "feat(tools): add paxdb tool for protein abundance across tissues"
```

---

## Task 8: ProteomicsDB — human proteome expression

**Files:**
- Create: `proteinbox/api_tools/proteomicsdb.py`
- Create: `tests/proteinbox/test_proteomicsdb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_proteomicsdb.py
import respx
import httpx
from proteinbox.api_tools.proteomicsdb import ProteomicsDBTool

MOCK_RESPONSE = {
    "queries": {
        "rows": [
            {"TISSUE_NAME": "Liver", "MS_INTENSITY": 1234567.89, "EXPERIMENT_COUNT": 5},
            {"TISSUE_NAME": "Brain", "MS_INTENSITY": 987654.32, "EXPERIMENT_COUNT": 3},
        ]
    }
}

@respx.mock
def test_proteomicsdb_success():
    respx.get("https://www.proteomicsdb.org/proteomicsdb/logic/api/proteinexpression.xsodata/InputParams").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = ProteomicsDBTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert len(result.data["tissues"]) == 2
    assert result.data["tissues"][0]["tissue"] == "Liver"

@respx.mock
def test_proteomicsdb_error():
    respx.get("https://www.proteomicsdb.org/proteomicsdb/logic/api/proteinexpression.xsodata/InputParams").mock(
        return_value=httpx.Response(500)
    )
    tool = ProteomicsDBTool()
    result = tool.run(gene="TP53")
    assert result.success is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_proteomicsdb.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/proteomicsdb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class ProteomicsDBTool(ProteinTool):
    name: str = "proteomicsdb"
    description: str = (
        "Query ProteomicsDB for human protein expression at the proteome level. "
        "Returns MS intensity by tissue and cell line, experiment count, and "
        "peptide detectability."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "https://www.proteomicsdb.org/proteomicsdb/logic/api/proteinexpression.xsodata/InputParams",
                params={"PROTEINFILTER": gene, "$format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"ProteomicsDB returned {resp.status_code}")

            rows = resp.json().get("queries", {}).get("rows", [])
            if not rows:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "tissues": []},
                    display=f"No ProteomicsDB data for {gene}",
                )

            tissues = [
                {
                    "tissue": r.get("TISSUE_NAME", ""),
                    "ms_intensity": r.get("MS_INTENSITY"),
                    "experiment_count": r.get("EXPERIMENT_COUNT", 0),
                }
                for r in rows
            ]
            tissues_sorted = sorted(tissues, key=lambda x: x["ms_intensity"] or 0, reverse=True)

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "tissue_count": len(tissues),
                    "tissues": tissues_sorted[:10],
                },
                display=f"{gene}: detected in {len(tissues)} tissues/cell lines in ProteomicsDB",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_proteomicsdb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/proteomicsdb.py tests/proteinbox/test_proteomicsdb.py
git commit -m "feat(tools): add proteomicsdb tool for human proteome expression"
```

---

## Task 9: PRIDE — proteomics datasets

**Files:**
- Create: `proteinbox/api_tools/pride.py`
- Create: `tests/proteinbox/test_pride.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_pride.py
import respx
import httpx
from proteinbox.api_tools.pride import PRIDETool

MOCK_RESPONSE = {
    "_embedded": {
        "projects": [
            {
                "accession": "PXD012345",
                "title": "TP53 phosphoproteomics in cancer cell lines",
                "organisms": [{"name": "Homo sapiens"}],
                "sampleProcessingProtocol": "LC-MS/MS",
                "submissionDate": "2023-06-15",
                "publicationDate": "2023-08-01",
                "references": [{"pubmedId": "37654321"}],
            }
        ]
    },
    "page": {"totalElements": 1},
}

@respx.mock
def test_pride_success():
    respx.get("https://www.ebi.ac.uk/pride/ws/archive/v2/projects").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = PRIDETool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["total"] == 1
    assert result.data["datasets"][0]["accession"] == "PXD012345"

@respx.mock
def test_pride_no_results():
    respx.get("https://www.ebi.ac.uk/pride/ws/archive/v2/projects").mock(
        return_value=httpx.Response(200, json={"_embedded": {"projects": []}, "page": {"totalElements": 0}})
    )
    tool = PRIDETool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["total"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_pride.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/pride.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class PRIDETool(ProteinTool):
    name: str = "pride"
    description: str = (
        "Query PRIDE Archive for public proteomics datasets. "
        "Returns dataset accessions, titles, species, instruments, submission "
        "dates, and linked PubMed IDs for a gene or keyword."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol or keyword (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/pride/ws/archive/v2/projects",
                params={"keyword": gene, "pageSize": 10, "page": 0},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"PRIDE returned {resp.status_code}")

            body = resp.json()
            projects = body.get("_embedded", {}).get("projects", [])
            total = body.get("page", {}).get("totalElements", 0)

            datasets = [
                {
                    "accession": p.get("accession", ""),
                    "title": p.get("title", ""),
                    "organism": p.get("organisms", [{}])[0].get("name", "") if p.get("organisms") else "",
                    "submission_date": p.get("submissionDate", ""),
                    "pubmed_ids": [r.get("pubmedId") for r in p.get("references", []) if r.get("pubmedId")],
                }
                for p in projects
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "total": total, "datasets": datasets},
                display=f"{gene}: {total} public proteomics datasets in PRIDE Archive",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_pride.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/pride.py tests/proteinbox/test_pride.py
git commit -m "feat(tools): add pride tool for public proteomics datasets"
```

---

## Task 10: Complex Portal — macromolecular complexes

**Files:**
- Create: `proteinbox/api_tools/complex_portal.py`
- Create: `tests/proteinbox/test_complex_portal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_complex_portal.py
import respx
import httpx
from proteinbox.api_tools.complex_portal import ComplexPortalTool

MOCK_RESPONSE = {
    "elements": [
        {
            "complexAC": "CPX-1234",
            "recommendedName": "p53-MDM2 complex",
            "organism": {"scientificName": "Homo sapiens"},
            "participants": [
                {"identifier": "P04637", "name": "TP53", "stoichiometry": "1"},
                {"identifier": "Q00987", "name": "MDM2", "stoichiometry": "1"},
            ],
            "function": "Negative regulation of p53 activity by MDM2.",
            "goTerms": [{"identifier": "GO:0043065", "name": "positive regulation of apoptotic process"}],
        }
    ]
}

@respx.mock
def test_complex_portal_success():
    respx.get("https://www.ebi.ac.uk/intact/complex-ws/search").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = ComplexPortalTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["complex_count"] == 1
    assert result.data["complexes"][0]["ac"] == "CPX-1234"
    assert len(result.data["complexes"][0]["subunits"]) == 2

@respx.mock
def test_complex_portal_not_found():
    respx.get("https://www.ebi.ac.uk/intact/complex-ws/search").mock(
        return_value=httpx.Response(200, json={"elements": []})
    )
    tool = ComplexPortalTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["complex_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_complex_portal.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/complex_portal.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class ComplexPortalTool(ProteinTool):
    name: str = "complex_portal"
    description: str = (
        "Query the Complex Portal (EBI) for experimentally validated macromolecular "
        "complexes. Returns complex name, subunit list with stoichiometry, biological "
        "function, and GO annotations."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/intact/complex-ws/search",
                params={"query": gene, "facets": "species_f", "format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"Complex Portal returned {resp.status_code}")

            elements = resp.json().get("elements", [])
            if not elements:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "complex_count": 0},
                    display=f"No Complex Portal entries for {gene}",
                )

            complexes = [
                {
                    "ac": e.get("complexAC", ""),
                    "name": e.get("recommendedName", ""),
                    "organism": e.get("organism", {}).get("scientificName", ""),
                    "function": e.get("function", ""),
                    "subunits": [
                        {"id": p.get("identifier"), "name": p.get("name"), "stoichiometry": p.get("stoichiometry")}
                        for p in e.get("participants", [])
                    ],
                    "go_terms": [g.get("name") for g in e.get("goTerms", [])],
                }
                for e in elements[:5]
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "complex_count": len(elements), "complexes": complexes},
                display=f"{gene}: found in {len(elements)} complexes in Complex Portal",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_complex_portal.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/complex_portal.py tests/proteinbox/test_complex_portal.py
git commit -m "feat(tools): add complex_portal tool for macromolecular complexes"
```

---

## Task 11: CORUM — mammalian protein complexes

**Files:**
- Create: `proteinbox/api_tools/corum.py`
- Create: `tests/proteinbox/test_corum.py`

> **Note:** CORUM may only provide flat-file downloads. Check https://mips.helmholtz-muenchen.de/corum/api/ before implementing. If no REST API is available, use the search endpoint at `https://mips.helmholtz-muenchen.de/corum/search` with query params and parse the JSON response.

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_corum.py
import respx
import httpx
from proteinbox.api_tools.corum import CORUMTool

MOCK_RESPONSE = {
    "results": [
        {
            "complex_id": "1",
            "complex_name": "p53 complex",
            "subunits_gene_name": "TP53;MDM2;MDM4",
            "subunits_uniprot_id": "P04637;Q00987;O15151",
            "organism": "Human",
            "cell_line": "HeLa",
            "purification_method": "co-immunoprecipitation",
            "disease_comment": "mutated in 50% of cancers",
            "pubmed_id": "12345678",
        }
    ]
}

@respx.mock
def test_corum_success():
    respx.get("https://mips.helmholtz-muenchen.de/corum/api/search").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = CORUMTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["complex_count"] == 1
    assert result.data["complexes"][0]["name"] == "p53 complex"
    assert "TP53" in result.data["complexes"][0]["subunit_genes"]

@respx.mock
def test_corum_not_found():
    respx.get("https://mips.helmholtz-muenchen.de/corum/api/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    tool = CORUMTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["complex_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_corum.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/corum.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class CORUMTool(ProteinTool):
    name: str = "corum"
    description: str = (
        "Query CORUM for curated mammalian protein complexes. Returns complex name, "
        "subunit gene list, purification method, tissue/cell line, disease association, "
        "and PubMed reference."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                "https://mips.helmholtz-muenchen.de/corum/api/search",
                params={"term": gene, "format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"CORUM returned {resp.status_code}")

            results = resp.json().get("results", [])
            if not results:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "complex_count": 0},
                    display=f"No CORUM entries for {gene}",
                )

            complexes = [
                {
                    "id": r.get("complex_id", ""),
                    "name": r.get("complex_name", ""),
                    "subunit_genes": [g.strip() for g in r.get("subunits_gene_name", "").split(";") if g.strip()],
                    "subunit_uniprot": [u.strip() for u in r.get("subunits_uniprot_id", "").split(";") if u.strip()],
                    "organism": r.get("organism", ""),
                    "cell_line": r.get("cell_line", ""),
                    "purification_method": r.get("purification_method", ""),
                    "disease_comment": r.get("disease_comment", ""),
                    "pubmed_id": r.get("pubmed_id", ""),
                }
                for r in results[:5]
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "complex_count": len(results), "complexes": complexes},
                display=f"{gene}: {len(results)} complexes in CORUM",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_corum.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/corum.py tests/proteinbox/test_corum.py
git commit -m "feat(tools): add corum tool for mammalian protein complexes"
```

---

## Task 12: BindingDB — protein-ligand binding affinity

**Files:**
- Create: `proteinbox/api_tools/bindingdb.py`
- Create: `tests/proteinbox/test_bindingdb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_bindingdb.py
import respx
import httpx
from proteinbox.api_tools.bindingdb import BindingDBTool

MOCK_RESPONSE = {
    "affinities": [
        {
            "ligand_name": "Nutlin-3a",
            "smiles": "CC(C)(C)c1ccc(CC2=NC(=O)N(C2=O)Cc2ccc(Cl)cc2Cl)cc1",
            "ki_nm": "90",
            "kd_nm": None,
            "ic50_nm": None,
            "assay_type": "Biochemical",
            "organism": "Homo sapiens",
            "pubmed_id": "14569205",
        },
        {
            "ligand_name": "PRIMA-1",
            "smiles": "CC1(CO)CN(C=O)C1=O",
            "ki_nm": None,
            "kd_nm": None,
            "ic50_nm": "2500",
            "assay_type": "Cell-based",
            "organism": "Homo sapiens",
            "pubmed_id": "12526800",
        },
    ]
}

@respx.mock
def test_bindingdb_success():
    respx.get("https://bindingdb.org/axis2/services/BDBService/getLigandsByUniprots").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = BindingDBTool()
    result = tool.run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["ligand_count"] == 2
    assert result.data["ligands"][0]["name"] == "Nutlin-3a"
    assert result.data["ligands"][0]["ki_nm"] == "90"

@respx.mock
def test_bindingdb_no_results():
    respx.get("https://bindingdb.org/axis2/services/BDBService/getLigandsByUniprots").mock(
        return_value=httpx.Response(200, json={"affinities": []})
    )
    tool = BindingDBTool()
    result = tool.run(uniprot_id="P99999")
    assert result.success is True
    assert result.data["ligand_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_bindingdb.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/bindingdb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class BindingDBTool(ProteinTool):
    name: str = "bindingdb"
    description: str = (
        "Query BindingDB for protein-ligand binding affinity data. "
        "Returns top ligands with Ki, Kd, and IC50 values, assay type, "
        "organism, and PubMed reference."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {"type": "string", "description": "UniProt accession (e.g. P04637)"},
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uid = kwargs["uniprot_id"].strip().upper()
        try:
            resp = httpx.get(
                "https://bindingdb.org/axis2/services/BDBService/getLigandsByUniprots",
                params={"uniprot": uid, "cutoff": 10000, "format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"BindingDB returned {resp.status_code}")

            affinities = resp.json().get("affinities", [])
            if not affinities:
                return ToolResult(
                    success=True,
                    data={"uniprot_id": uid, "ligand_count": 0},
                    display=f"No BindingDB ligands for {uid}",
                )

            ligands = [
                {
                    "name": a.get("ligand_name", ""),
                    "smiles": a.get("smiles", ""),
                    "ki_nm": a.get("ki_nm"),
                    "kd_nm": a.get("kd_nm"),
                    "ic50_nm": a.get("ic50_nm"),
                    "assay_type": a.get("assay_type", ""),
                    "organism": a.get("organism", ""),
                    "pubmed_id": a.get("pubmed_id", ""),
                }
                for a in affinities[:10]
            ]

            return ToolResult(
                success=True,
                data={"uniprot_id": uid, "ligand_count": len(affinities), "ligands": ligands},
                display=f"{uid}: {len(affinities)} binding ligands in BindingDB (top: {ligands[0]['name']})",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_bindingdb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/bindingdb.py tests/proteinbox/test_bindingdb.py
git commit -m "feat(tools): add bindingdb tool for protein-ligand binding affinity"
```

---

## Task 13: DGIdb — drug-gene interactions

**Files:**
- Create: `proteinbox/api_tools/dgidb.py`
- Create: `tests/proteinbox/test_dgidb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_dgidb.py
import respx
import httpx
from proteinbox.api_tools.dgidb import DGIdbTool

MOCK_RESPONSE = {
    "data": {
        "genes": {
            "nodes": [
                {
                    "name": "TP53",
                    "interactions": {
                        "nodes": [
                            {
                                "drug": {"name": "PRIMA-1MET", "approved": False},
                                "interactionTypes": [{"type": "activator"}],
                                "sources": [{"sourceDbName": "TdgClinicalTrial"}],
                                "score": 0.9,
                            },
                            {
                                "drug": {"name": "APR-246", "approved": False},
                                "interactionTypes": [{"type": "activator"}],
                                "sources": [{"sourceDbName": "ChEMBL"}],
                                "score": 0.8,
                            },
                        ]
                    },
                }
            ]
        }
    }
}

@respx.mock
def test_dgidb_success():
    respx.post("https://dgidb.org/api/graphql").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = DGIdbTool()
    result = tool.run(gene="TP53")
    assert result.success is True
    assert result.data["interaction_count"] == 2
    assert result.data["interactions"][0]["drug"] == "PRIMA-1MET"

@respx.mock
def test_dgidb_not_found():
    respx.post("https://dgidb.org/api/graphql").mock(
        return_value=httpx.Response(200, json={"data": {"genes": {"nodes": []}}})
    )
    tool = DGIdbTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["interaction_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_dgidb.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/dgidb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

QUERY = """
query($gene: [String!]!) {
  genes(names: $gene) {
    nodes {
      name
      interactions {
        nodes {
          drug { name approved }
          interactionTypes { type }
          sources { sourceDbName }
          score
        }
      }
    }
  }
}
"""

@register_tool
class DGIdbTool(ProteinTool):
    name: str = "dgidb"
    description: str = (
        "Query DGIdb for drug-gene interactions. Returns drug names, interaction "
        "types (inhibitor/activator/etc.), source databases, approval status, "
        "and interaction scores."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol (e.g. TP53)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()
        try:
            resp = httpx.post(
                "https://dgidb.org/api/graphql",
                json={"query": QUERY, "variables": {"gene": [gene]}},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"DGIdb returned {resp.status_code}")

            nodes = resp.json().get("data", {}).get("genes", {}).get("nodes", [])
            if not nodes:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "interaction_count": 0},
                    display=f"No DGIdb interactions for {gene}",
                )

            raw = nodes[0].get("interactions", {}).get("nodes", [])
            interactions = [
                {
                    "drug": i["drug"]["name"],
                    "approved": i["drug"].get("approved", False),
                    "types": [t["type"] for t in i.get("interactionTypes", [])],
                    "sources": [s["sourceDbName"] for s in i.get("sources", [])],
                    "score": i.get("score"),
                }
                for i in raw[:10]
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "interaction_count": len(raw), "interactions": interactions},
                display=f"{gene}: {len(raw)} drug interactions in DGIdb",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_dgidb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/dgidb.py tests/proteinbox/test_dgidb.py
git commit -m "feat(tools): add dgidb tool for drug-gene interactions"
```

---

## Task 14: DrugBank — detailed drug information

**Files:**
- Create: `proteinbox/api_tools/drugbank.py`
- Create: `tests/proteinbox/test_drugbank.py`

> **Note:** DrugBank requires a free API token from https://go.drugbank.com/releases/latest. Set the `DRUGBANK_TOKEN` environment variable before using this tool.

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_drugbank.py
import os
import respx
import httpx
import pytest
from proteinbox.api_tools.drugbank import DrugBankTool

MOCK_RESPONSE = {
    "products": [
        {
            "name": "Nutlin-3",
            "drugbank_id": "DB12345",
            "indication": "Investigational: cancer",
            "mechanism_of_action": "MDM2 inhibitor that stabilizes p53",
            "pharmacodynamics": "Restores p53 function in tumors",
            "toxicity": "Not established",
            "targets": [{"gene": "MDM2", "action": "inhibitor"}],
            "categories": [{"category": "Antineoplastic Agents"}],
        }
    ]
}

@respx.mock
def test_drugbank_success(monkeypatch):
    monkeypatch.setenv("DRUGBANK_TOKEN", "test-token-123")
    respx.get("https://api.drugbankplus.com/v1/us/drug_targets").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = DrugBankTool()
    result = tool.run(gene="MDM2")
    assert result.success is True
    assert result.data["drug_count"] == 1
    assert result.data["drugs"][0]["name"] == "Nutlin-3"

def test_drugbank_no_token(monkeypatch):
    monkeypatch.delenv("DRUGBANK_TOKEN", raising=False)
    tool = DrugBankTool()
    result = tool.run(gene="TP53")
    assert result.success is False
    assert "DRUGBANK_TOKEN" in result.error
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_drugbank.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/drugbank.py
import os
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class DrugBankTool(ProteinTool):
    name: str = "drugbank"
    description: str = (
        "Query DrugBank for detailed drug information. Returns mechanism of action, "
        "pharmacodynamics, ADMET properties, indications, side effects, and targets. "
        "Requires DRUGBANK_TOKEN environment variable (free registration at drugbank.com)."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "Gene symbol of the drug target (e.g. MDM2)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()
        token = os.environ.get("DRUGBANK_TOKEN", "")
        if not token:
            return ToolResult(success=False, error="DRUGBANK_TOKEN environment variable not set. Get a free token at https://go.drugbank.com/releases/latest")
        try:
            resp = httpx.get(
                "https://api.drugbankplus.com/v1/us/drug_targets",
                params={"gene_name": gene, "per_page": 10},
                headers={"Authorization": token},
                timeout=30,
            )
            if resp.status_code == 401:
                return ToolResult(success=False, error="DrugBank API token invalid or expired")
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"DrugBank returned {resp.status_code}")

            products = resp.json().get("products", [])
            if not products:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "drug_count": 0},
                    display=f"No DrugBank entries for target {gene}",
                )

            drugs = [
                {
                    "name": d.get("name", ""),
                    "drugbank_id": d.get("drugbank_id", ""),
                    "indication": d.get("indication", ""),
                    "mechanism_of_action": d.get("mechanism_of_action", ""),
                    "pharmacodynamics": d.get("pharmacodynamics", ""),
                    "targets": [{"gene": t.get("gene"), "action": t.get("action")} for t in d.get("targets", [])],
                    "categories": [c.get("category") for c in d.get("categories", [])],
                }
                for d in products
            ]

            return ToolResult(
                success=True,
                data={"gene": gene, "drug_count": len(products), "drugs": drugs},
                display=f"{gene}: {len(products)} drugs in DrugBank",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_drugbank.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/drugbank.py tests/proteinbox/test_drugbank.py
git commit -m "feat(tools): add drugbank tool for detailed drug information"
```

---

## Task 15: dbPTM — comprehensive PTM database

**Files:**
- Create: `proteinbox/api_tools/dbptm.py`
- Create: `tests/proteinbox/test_dbptm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_dbptm.py
import respx
import httpx
from proteinbox.api_tools.dbptm import DbPTMTool

MOCK_RESPONSE = {
    "result": [
        {
            "uniprot_id": "P04637",
            "position": 15,
            "residue": "S",
            "ptm_type": "Phosphoserine",
            "kinase": "ATM",
            "evidence": "Experimental",
            "pmid": "11054552",
        },
        {
            "uniprot_id": "P04637",
            "position": 20,
            "residue": "K",
            "ptm_type": "Acetyllysine",
            "kinase": "",
            "evidence": "Experimental",
            "pmid": "12556884",
        },
    ]
}

@respx.mock
def test_dbptm_success():
    respx.get("https://awi.cuhk.edu.cn/dbPTM/api/search").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = DbPTMTool()
    result = tool.run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["ptm_count"] == 2
    assert result.data["ptms"][0]["position"] == 15
    assert result.data["ptm_types"] == {"Phosphoserine": 1, "Acetyllysine": 1}

@respx.mock
def test_dbptm_not_found():
    respx.get("https://awi.cuhk.edu.cn/dbPTM/api/search").mock(
        return_value=httpx.Response(200, json={"result": []})
    )
    tool = DbPTMTool()
    result = tool.run(uniprot_id="P99999")
    assert result.success is True
    assert result.data["ptm_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_dbptm.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/dbptm.py
from collections import Counter
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class DbPTMTool(ProteinTool):
    name: str = "dbptm"
    description: str = (
        "Query dbPTM for experimentally verified post-translational modifications. "
        "Returns PTM type, modified residue position, kinase (if phosphorylation), "
        "experimental evidence type, and PubMed reference."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {"type": "string", "description": "UniProt accession (e.g. P04637)"},
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uid = kwargs["uniprot_id"].strip().upper()
        try:
            resp = httpx.get(
                "https://awi.cuhk.edu.cn/dbPTM/api/search",
                params={"UniProtAC": uid, "format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"dbPTM returned {resp.status_code}")

            results = resp.json().get("result", [])
            if not results:
                return ToolResult(
                    success=True,
                    data={"uniprot_id": uid, "ptm_count": 0},
                    display=f"No PTM entries in dbPTM for {uid}",
                )

            ptms = [
                {
                    "position": r.get("position"),
                    "residue": r.get("residue", ""),
                    "type": r.get("ptm_type", ""),
                    "kinase": r.get("kinase", ""),
                    "evidence": r.get("evidence", ""),
                    "pmid": r.get("pmid", ""),
                }
                for r in results[:20]
            ]

            type_counts = dict(Counter(r.get("ptm_type", "") for r in results))

            return ToolResult(
                success=True,
                data={
                    "uniprot_id": uid,
                    "ptm_count": len(results),
                    "ptm_types": type_counts,
                    "ptms": ptms,
                },
                display=f"{uid}: {len(results)} PTMs — {', '.join(f'{v}x {k}' for k, v in sorted(type_counts.items(), key=lambda x: -x[1])[:3])}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_dbptm.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/dbptm.py tests/proteinbox/test_dbptm.py
git commit -m "feat(tools): add dbptm tool for post-translational modifications"
```

---

## Task 16: OPM — membrane protein orientation

**Files:**
- Create: `proteinbox/api_tools/opm.py`
- Create: `tests/proteinbox/test_opm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_opm.py
import respx
import httpx
from proteinbox.api_tools.opm import OPMTool

MOCK_RESPONSE = {
    "objects": [
        {
            "pdbid": "1IYT",
            "name": "Potassium channel KcsA",
            "type": {"name": "Transmembrane protein (alpha-helical)"},
            "tilt_angle": 5.2,
            "thickness": 27.8,
            "hydrophobic_thickness": 25.1,
            "subunit_segments": [{"start": 22, "end": 62}],
            "families": [{"name": "Potassium channels"}],
        }
    ]
}

@respx.mock
def test_opm_by_pdb():
    respx.get("https://lomize-group-opm.herokuapp.com/primary_structures").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = OPMTool()
    result = tool.run(pdb_id="1IYT")
    assert result.success is True
    assert result.data["pdb_id"] == "1IYT"
    assert result.data["membrane_type"] == "Transmembrane protein (alpha-helical)"
    assert result.data["tilt_angle"] == 5.2

@respx.mock
def test_opm_not_found():
    respx.get("https://lomize-group-opm.herokuapp.com/primary_structures").mock(
        return_value=httpx.Response(200, json={"objects": []})
    )
    tool = OPMTool()
    result = tool.run(pdb_id="XXXX")
    assert result.success is True
    assert result.data.get("pdb_id") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_opm.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/opm.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class OPMTool(ProteinTool):
    name: str = "opm"
    description: str = (
        "Query OPM (Orientations of Proteins in Membranes) for membrane protein "
        "geometry. Returns membrane protein type, tilt angle, hydrophobic thickness, "
        "and transmembrane segment positions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "pdb_id": {"type": "string", "description": "PDB ID (e.g. 1IYT)"},
        },
        "required": ["pdb_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        pdb_id = kwargs["pdb_id"].strip().upper()
        try:
            resp = httpx.get(
                "https://lomize-group-opm.herokuapp.com/primary_structures",
                params={"pdbid": pdb_id.lower()},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"OPM returned {resp.status_code}")

            objects = resp.json().get("objects", [])
            if not objects:
                return ToolResult(
                    success=True,
                    data={"message": f"No OPM entry for PDB {pdb_id}"},
                    display=f"PDB {pdb_id} not found in OPM (may not be a membrane protein)",
                )

            obj = objects[0]
            segments = obj.get("subunit_segments", [])

            return ToolResult(
                success=True,
                data={
                    "pdb_id": pdb_id,
                    "name": obj.get("name", ""),
                    "membrane_type": obj.get("type", {}).get("name", ""),
                    "tilt_angle": obj.get("tilt_angle"),
                    "thickness": obj.get("thickness"),
                    "hydrophobic_thickness": obj.get("hydrophobic_thickness"),
                    "tm_segments": [{"start": s.get("start"), "end": s.get("end")} for s in segments],
                    "families": [f.get("name") for f in obj.get("families", [])],
                },
                display=f"PDB {pdb_id}: {obj.get('type', {}).get('name', 'membrane protein')}, tilt={obj.get('tilt_angle')}°, thickness={obj.get('hydrophobic_thickness')} Å",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_opm.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/opm.py tests/proteinbox/test_opm.py
git commit -m "feat(tools): add opm tool for membrane protein orientation"
```

---

## Task 17: IMGT — immunogenetics database

**Files:**
- Create: `proteinbox/api_tools/imgt.py`
- Create: `tests/proteinbox/test_imgt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_imgt.py
import respx
import httpx
from proteinbox.api_tools.imgt import IMGTTool

MOCK_RESPONSE = {
    "results": [
        {
            "gene": "IGHV1-2",
            "species": "Homo sapiens",
            "group": "IGHV",
            "subgroup": "IGHV1",
            "functionality": "F",
            "chromosomal_location": "14q32.33",
            "alleles": ["IGHV1-2*01", "IGHV1-2*02", "IGHV1-2*05"],
            "sequence_length": 296,
        }
    ]
}

@respx.mock
def test_imgt_success():
    respx.get("https://www.imgt.org/genedb/api/gene/IGHV1-2").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = IMGTTool()
    result = tool.run(gene="IGHV1-2")
    assert result.success is True
    assert result.data["gene"] == "IGHV1-2"
    assert result.data["allele_count"] == 3
    assert result.data["functionality"] == "F"

@respx.mock
def test_imgt_not_found():
    respx.get("https://www.imgt.org/genedb/api/gene/FAKEGENE").mock(
        return_value=httpx.Response(404)
    )
    tool = IMGTTool()
    result = tool.run(gene="FAKEGENE")
    assert result.success is False
    assert result.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_imgt.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/imgt.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class IMGTTool(ProteinTool):
    name: str = "imgt"
    description: str = (
        "Query IMGT for immunoglobulin, T-cell receptor, and MHC gene data. "
        "Returns gene classification, functionality, allele list, chromosomal "
        "location, and species coverage. Use for IG/TR/MHC gene names (e.g. IGHV1-2)."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {"type": "string", "description": "IMGT gene name (e.g. IGHV1-2, TRAV1-1, HLA-A)"},
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        try:
            resp = httpx.get(
                f"https://www.imgt.org/genedb/api/gene/{gene}",
                timeout=30,
            )
            if resp.status_code == 404:
                return ToolResult(success=False, error=f"IMGT gene '{gene}' not found")
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"IMGT returned {resp.status_code}")

            results = resp.json().get("results", [])
            if not results:
                return ToolResult(success=False, error=f"No IMGT results for {gene}")

            r = results[0]
            alleles = r.get("alleles", [])

            return ToolResult(
                success=True,
                data={
                    "gene": r.get("gene", gene),
                    "species": r.get("species", ""),
                    "group": r.get("group", ""),
                    "subgroup": r.get("subgroup", ""),
                    "functionality": r.get("functionality", ""),
                    "chromosomal_location": r.get("chromosomal_location", ""),
                    "allele_count": len(alleles),
                    "alleles": alleles,
                    "sequence_length": r.get("sequence_length"),
                },
                display=f"{gene}: {r.get('group','')} gene, functionality={r.get('functionality','')}, {len(alleles)} alleles, {r.get('species','')}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_imgt.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/imgt.py tests/proteinbox/test_imgt.py
git commit -m "feat(tools): add imgt tool for immunoglobulin and T-cell receptor genes"
```

---

## Task 18: SCOPe — structural classification of proteins

**Files:**
- Create: `proteinbox/api_tools/scopedb.py`
- Create: `tests/proteinbox/test_scopedb.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/proteinbox/test_scopedb.py
import respx
import httpx
from proteinbox.api_tools.scopedb import SCOPeDBTool

MOCK_RESPONSE = {
    "domains": [
        {
            "sccs": "a.1.1.1",
            "domain_id": "d1dlwa_",
            "pdb_id": "1DLW",
            "chain": "A",
            "class": {"id": "a", "description": "All alpha proteins"},
            "fold": {"id": "a.1", "description": "Globin-like"},
            "superfamily": {"id": "a.1.1", "description": "Globin-like"},
            "family": {"id": "a.1.1.1", "description": "Truncated hemoglobin"},
        }
    ]
}

@respx.mock
def test_scopedb_by_pdb():
    respx.get("https://scop.berkeley.edu/api/search").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = SCOPeDBTool()
    result = tool.run(pdb_id="1DLW")
    assert result.success is True
    assert result.data["domain_count"] == 1
    assert result.data["domains"][0]["sccs"] == "a.1.1.1"
    assert result.data["domains"][0]["class"] == "All alpha proteins"

@respx.mock
def test_scopedb_not_found():
    respx.get("https://scop.berkeley.edu/api/search").mock(
        return_value=httpx.Response(200, json={"domains": []})
    )
    tool = SCOPeDBTool()
    result = tool.run(pdb_id="XXXX")
    assert result.success is True
    assert result.data["domain_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/proteinbox/test_scopedb.py -v
```
Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
# proteinbox/api_tools/scopedb.py
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

@register_tool
class SCOPeDBTool(ProteinTool):
    name: str = "scopedb"
    description: str = (
        "Query SCOPe for structural classification of proteins. Returns SCOP "
        "class, fold, superfamily, and family for each domain in a PDB structure. "
        "Complements CATH with an independent classification hierarchy."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "pdb_id": {"type": "string", "description": "PDB ID (e.g. 1TUP)"},
        },
        "required": ["pdb_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        pdb_id = kwargs["pdb_id"].strip().upper()
        try:
            resp = httpx.get(
                "https://scop.berkeley.edu/api/search",
                params={"pdbid": pdb_id.lower(), "format": "json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"SCOPe returned {resp.status_code}")

            domains_raw = resp.json().get("domains", [])
            if not domains_raw:
                return ToolResult(
                    success=True,
                    data={"pdb_id": pdb_id, "domain_count": 0},
                    display=f"No SCOPe classification for PDB {pdb_id}",
                )

            domains = [
                {
                    "sccs": d.get("sccs", ""),
                    "domain_id": d.get("domain_id", ""),
                    "chain": d.get("chain", ""),
                    "class": d.get("class", {}).get("description", ""),
                    "fold": d.get("fold", {}).get("description", ""),
                    "superfamily": d.get("superfamily", {}).get("description", ""),
                    "family": d.get("family", {}).get("description", ""),
                }
                for d in domains_raw
            ]

            return ToolResult(
                success=True,
                data={"pdb_id": pdb_id, "domain_count": len(domains), "domains": domains},
                display=f"PDB {pdb_id}: {len(domains)} SCOPe domain(s) — {domains[0]['class']} / {domains[0]['fold']}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/proteinbox/test_scopedb.py -v
```
Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_tools/scopedb.py tests/proteinbox/test_scopedb.py
git commit -m "feat(tools): add scopedb tool for SCOP structural classification"
```

---

## Task 19: Update README Supported Tools table

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add new tools to the Supported Tools table in README.md**

Add the following rows to the existing Supported Tools table in `README.md`. Insert them into the appropriate categories:

**Protein Evolution (new category):**
```
| **Protein Evolution** | `eggnog` | API | eggNOG v6 | Orthologous groups, COG category, GO terms, functional description |
| | `consurf` | API | ConSurf DB | Per-residue conservation scores (1–9), conserved/variable residue counts |
| | `phylomedb` | API | PhylomeDB | Phylogenetic orthologs, paralog list, sequence identity, species coverage |
```

**Enzyme / Metabolism (new category):**
```
| **Enzyme / Metabolism** | `expasy_enzyme` | API | ExPASy ENZYME | EC number, reaction equation, cofactors, UniProt cross-references |
| | `brenda` | API* | BRENDA | Km, Vmax, substrates, inhibitors, optimal pH/temperature (requires free registration) |
| | `sabio_rk` | API | SABIO-RK | Experimental kinetic parameters (kcat, Km, Ki) with reaction conditions |
```

**Proteomics / Abundance (new category):**
```
| **Proteomics / Abundance** | `paxdb` | API | PaxDb | Protein abundance (ppm) across tissues and species, integrated score |
| | `proteomicsdb` | API | ProteomicsDB | Human protein expression by tissue and cell line (MS intensity) |
| | `pride` | API | PRIDE Archive | Public proteomics datasets: accession, species, instrument, PubMed ID |
```

**Protein Complexes (new category):**
```
| **Protein Complexes** | `complex_portal` | API | Complex Portal (EBI) | Macromolecular complexes, subunit stoichiometry, GO annotations |
| | `corum` | API | CORUM | Mammalian protein complexes, subunits, purification method, disease association |
```

**Drug Binding (new rows under Disease & Drug):**
```
| | `bindingdb` | API | BindingDB | Protein-ligand binding affinity: Ki, Kd, IC50 with assay type and reference |
| | `drugbank` | API* | DrugBank | Drug mechanism, ADMET, indications, side effects (requires free token) |
| | `dgidb` | API | DGIdb | Drug-gene interactions from 30+ sources, interaction types and scores |
```

**PTM / Structural Features (new rows):**
```
| | `dbptm` | API | dbPTM | Comprehensive PTM database: 20+ modification types with kinase and evidence |
| | `opm` | API | OPM | Membrane protein orientation: tilt angle, hydrophobic thickness, TM segments |
| | `imgt` | API | IMGT | Immunoglobulin, T-cell receptor, MHC genes: alleles, functionality, location |
| | `scopedb` | API | SCOPe | Structural classification: Class/Fold/Superfamily/Family hierarchy |
```

Update the count at the top of the Supported Tools section from `35 tools` to `55 tools`.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update Supported Tools table with 20 new tools (55 total)"
```

---

## Task 20: Run full test suite

- [ ] **Step 1: Run all new tool tests together**

```bash
uv run pytest tests/proteinbox/test_eggnog.py tests/proteinbox/test_consurf.py \
  tests/proteinbox/test_phylomedb.py tests/proteinbox/test_expasy_enzyme.py \
  tests/proteinbox/test_brenda.py tests/proteinbox/test_sabio_rk.py \
  tests/proteinbox/test_paxdb.py tests/proteinbox/test_proteomicsdb.py \
  tests/proteinbox/test_pride.py tests/proteinbox/test_complex_portal.py \
  tests/proteinbox/test_corum.py tests/proteinbox/test_bindingdb.py \
  tests/proteinbox/test_dgidb.py tests/proteinbox/test_drugbank.py \
  tests/proteinbox/test_dbptm.py tests/proteinbox/test_opm.py \
  tests/proteinbox/test_imgt.py tests/proteinbox/test_scopedb.py -v
```

Expected: All tests PASSED.

- [ ] **Step 2: Run the full existing test suite to confirm no regressions**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASSED (no regressions in existing tools).

- [ ] **Step 3: Verify all 20 tools register correctly**

```bash
uv run python -c "
from proteinbox.tools.registry import discover_tools
tools = discover_tools()
new = ['eggnog','consurf','phylomedb','expasy_enzyme','brenda','sabio_rk',
       'paxdb','proteomicsdb','pride','complex_portal','corum',
       'bindingdb','dgidb','drugbank','dbptm','opm','imgt','scopedb']
missing = [t for t in new if t not in tools]
print(f'Total tools: {len(tools)}')
print(f'Missing: {missing}' if missing else 'All 20 new tools registered OK')
"
```

Expected output:
```
Total tools: 55
All 20 new tools registered OK
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(tools): complete round 2 — 20 new tools, 55 total"
```
