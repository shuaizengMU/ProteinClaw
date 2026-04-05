# GWAS Catalog & Protein Atlas Bug Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two data-accuracy bugs: GWAS Catalog uses the wrong endpoint (returns unfiltered results), and Protein Atlas drops parsed fields via an over-narrow `columns=` filter.

**Architecture:** Both fixes are one-line changes to existing tool files. Tests are added to `tests/proteinbox/test_api_tools.py` (the existing test file for api_tools). TDD: write failing test → apply fix → verify pass.

**Tech Stack:** Python, httpx, respx (HTTP mock), pytest, uv

---

### Task 1: Fix GWAS Catalog — Restore Gene-Filtered Endpoint

**Files:**
- Modify: `proteinbox/api_tools/gwas_catalog.py:30-32`
- Test: `tests/proteinbox/test_api_tools.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/proteinbox/test_api_tools.py`:

```python
# ── GWAS Catalog ──────────────────────────────────────────────────────────────

from proteinbox.api_tools.gwas_catalog import GWASCatalogTool

GWAS_BASE = "https://www.ebi.ac.uk/gwas/rest/api"

MOCK_GWAS_RESPONSE = {
    "_embedded": {
        "associations": [
            {
                "efoTraits": [{"trait": "Breast cancer"}],
                "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs12345-A"}]}],
                "pvalueMantissa": 1,
                "pvalueExponent": -10,
                "riskFrequency": "0.25",
                "orPerCopyNum": 1.3,
                "studyAccession": "GCST000123",
            }
        ]
    }
}


@respx.mock
def test_gwas_catalog_success():
    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(
        return_value=httpx.Response(200, json=MOCK_GWAS_RESPONSE)
    )
    result = GWASCatalogTool().run(gene="BRCA1")
    assert result.success is True
    assert result.data["total"] == 1
    assert result.data["associations"][0]["traits"] == ["Breast cancer"]
    assert result.data["associations"][0]["snps"] == ["rs12345-A"]
    assert result.data["associations"][0]["p_value"] == "1e-10"


@respx.mock
def test_gwas_catalog_no_results():
    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(
        return_value=httpx.Response(200, json={"_embedded": {"associations": []}})
    )
    result = GWASCatalogTool().run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["total"] == 0
    assert result.data["associations"] == []


@respx.mock
def test_gwas_catalog_uses_geneName_param():
    """Verify the tool sends geneName=, not gene=, so the endpoint actually filters."""
    called_with = {}

    def capture(request):
        called_with["params"] = dict(request.url.params)
        return httpx.Response(200, json={"_embedded": {"associations": []}})

    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(side_effect=capture)
    GWASCatalogTool().run(gene="TP53")
    assert called_with["params"].get("geneName") == "TP53"
    assert "gene" not in called_with["params"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw
uv run pytest tests/proteinbox/test_api_tools.py::test_gwas_catalog_success tests/proteinbox/test_api_tools.py::test_gwas_catalog_no_results tests/proteinbox/test_api_tools.py::test_gwas_catalog_uses_geneName_param -v
```

Expected: all three FAIL (respx raises `httpx.ConnectError` or no match because the tool currently calls `/associations?gene=...`).

- [ ] **Step 3: Apply the fix**

In `proteinbox/api_tools/gwas_catalog.py`, change lines 30-32:

```python
            resp = httpx.get(
                "https://www.ebi.ac.uk/gwas/rest/api/associations/search/findByGene",
                params={"geneName": gene},
                headers={"Accept": "application/json"},
                timeout=30,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/proteinbox/test_api_tools.py::test_gwas_catalog_success tests/proteinbox/test_api_tools.py::test_gwas_catalog_no_results tests/proteinbox/test_api_tools.py::test_gwas_catalog_uses_geneName_param -v
```

Expected: all three PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add proteinbox/api_tools/gwas_catalog.py tests/proteinbox/test_api_tools.py
git commit -m "fix(gwas): restore gene-filtered endpoint (findByGene?geneName=)"
```

---

### Task 2: Fix Protein Atlas — Remove Over-Narrow `columns` Filter

**Files:**
- Modify: `proteinbox/api_tools/protein_atlas.py:34-35`
- Test: `tests/proteinbox/test_api_tools.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/proteinbox/test_api_tools.py`:

```python
# ── Protein Atlas ─────────────────────────────────────────────────────────────

from proteinbox.api_tools.protein_atlas import HumanProteinAtlasTool

PA_BASE = "https://www.proteinatlas.org/api/search_download.php"

MOCK_PA_RESPONSE = [
    {
        "Gene": "TP53",
        "Gene description": "Tumor protein p53",
        "Protein class": ["Cancer-related genes", "Transcription factors"],
        "Subcellular location": ["Nucleus", "Cytoplasm"],
        "RNA tissue specificity": "Low tissue specificity",
        "RNA tissue distribution": "Detected in all",
        "Tissue expression cluster": ["Cluster 1"],
        "RNA cancer specificity": "Not detected",
        "Prognostic - favorable": ["Breast cancer"],
    }
]


@respx.mock
def test_protein_atlas_success():
    respx.get(PA_BASE).mock(return_value=httpx.Response(200, json=MOCK_PA_RESPONSE))
    result = HumanProteinAtlasTool().run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert result.data["description"] == "Tumor protein p53"
    assert "Nucleus" in result.data["subcellular_localization"]
    assert result.data["cancer_specificity"] == "Not detected"
    assert result.data["prognostic_favorable"] == ["Breast cancer"]


@respx.mock
def test_protein_atlas_no_columns_param():
    """Verify the tool does NOT send a columns= parameter."""
    called_with = {}

    def capture(request):
        called_with["params"] = dict(request.url.params)
        return httpx.Response(200, json=MOCK_PA_RESPONSE)

    respx.get(PA_BASE).mock(side_effect=capture)
    HumanProteinAtlasTool().run(gene="TP53")
    assert "columns" not in called_with["params"]


@respx.mock
def test_protein_atlas_exact_gene_match():
    """Returns the TP53 entry even when the response contains multiple genes."""
    multi = [
        {"Gene": "TP53BP1", "Gene description": "TP53 binding protein 1",
         "Protein class": [], "Subcellular location": [], "RNA tissue specificity": "",
         "RNA tissue distribution": "", "Tissue expression cluster": [],
         "RNA cancer specificity": "", "Prognostic - favorable": []},
        {"Gene": "TP53", "Gene description": "Tumor protein p53",
         "Protein class": ["Cancer-related genes"], "Subcellular location": ["Nucleus"],
         "RNA tissue specificity": "Low tissue specificity",
         "RNA tissue distribution": "Detected in all", "Tissue expression cluster": [],
         "RNA cancer specificity": "", "Prognostic - favorable": []},
    ]
    respx.get(PA_BASE).mock(return_value=httpx.Response(200, json=multi))
    result = HumanProteinAtlasTool().run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert result.data["description"] == "Tumor protein p53"


@respx.mock
def test_protein_atlas_not_found():
    respx.get(PA_BASE).mock(return_value=httpx.Response(200, json=[]))
    result = HumanProteinAtlasTool().run(gene="FAKEGENE")
    assert result.success is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/proteinbox/test_api_tools.py::test_protein_atlas_success tests/proteinbox/test_api_tools.py::test_protein_atlas_no_columns_param tests/proteinbox/test_api_tools.py::test_protein_atlas_exact_gene_match tests/proteinbox/test_api_tools.py::test_protein_atlas_not_found -v
```

Expected: `test_protein_atlas_no_columns_param` FAILS (tool currently sends `columns=`); the others may also fail depending on respx strict matching.

- [ ] **Step 3: Apply the fix**

In `proteinbox/api_tools/protein_atlas.py`, change the `params` dict (lines 31-36) to remove `columns`:

```python
            resp = httpx.get(
                "https://www.proteinatlas.org/api/search_download.php",
                params={
                    "search": gene,
                    "format": "json",
                    "compress": "no",
                },
                timeout=30,
                follow_redirects=True,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/proteinbox/test_api_tools.py::test_protein_atlas_success tests/proteinbox/test_api_tools.py::test_protein_atlas_no_columns_param tests/proteinbox/test_api_tools.py::test_protein_atlas_exact_gene_match tests/proteinbox/test_api_tools.py::test_protein_atlas_not_found -v
```

Expected: all four PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: no new failures.

- [ ] **Step 6: Verify with live harness**

```bash
scripts/test-tools.sh gwas_catalog protein_atlas
```

Expected: both `✓`, with non-empty `display` strings (real traits for GWAS, real localization/class for Protein Atlas).

- [ ] **Step 7: Commit**

```bash
git add proteinbox/api_tools/protein_atlas.py tests/proteinbox/test_api_tools.py
git commit -m "fix(protein-atlas): remove columns filter so all parsed fields are returned"
```
