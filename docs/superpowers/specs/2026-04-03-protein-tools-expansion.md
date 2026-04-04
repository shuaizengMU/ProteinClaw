# Protein Tools Expansion — Design Spec

**Date:** 2026-04-03
**Goal:** Expand ProteinClaw's tool suite from 2 tools (uniprot, blast) to 9, covering structure, domains, sequence analysis, interactions, pathways, and literature search.

---

## Current State

| Tool | Source | Capability |
|------|--------|-----------|
| `uniprot` | UniProt REST API | Protein info by accession ID |
| `blast` | NCBI BLAST API | Homology search by sequence |

Gap: no structure lookup, no domain annotation, no local sequence analysis, no interaction network, no pathway context, no literature search.

---

## Proposed Tools

### Batch 1 — P0 (Core gaps, low complexity)

#### 1. `pdb` — Protein Structure Lookup

- **Source:** RCSB PDB REST API (`https://data.rcsb.org/rest/v1/core/entry/{pdb_id}`)
- **Input:** `pdb_id` (string, e.g. "1TUP")
- **Output:** title, experimental method, resolution, organism, deposit date, chains summary, ligands
- **Complexity:** Low — single GET, JSON parse

#### 2. `alphafold` — Predicted Structure Metadata

- **Source:** AlphaFold DB API (`https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}`)
- **Input:** `uniprot_id` (string, e.g. "P04637")
- **Output:** model URL, pLDDT confidence (mean + per-residue summary), coverage, version
- **Complexity:** Low — single GET, JSON parse

#### 3. `sequence_analysis` — Local Sequence Properties

- **Source:** Local computation, no API
- **Input:** `sequence` (string, amino acid sequence)
- **Output:** length, molecular weight, isoelectric point (pI), amino acid composition, GRAVY score, extinction coefficients
- **Complexity:** Low — pure math, no dependencies beyond stdlib
- **Note:** No `biopython` dependency. Hand-rolled using standard amino acid property tables (MW, pKa values). Keeps the dependency tree lean.

### Batch 2 — P1 (Annotation + interactions)

#### 4. `interpro` — Domain & Family Annotation

- **Source:** InterPro REST API (`https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/{uniprot_id}`)
- **Input:** `uniprot_id` (string)
- **Output:** list of domain/family hits with source DB (Pfam, PROSITE, CDD, etc.), coordinates, description
- **Complexity:** Low — single GET, JSON parse

#### 5. `string` — Protein-Protein Interactions

- **Source:** STRING API (`https://string-db.org/api/json/network`)
- **Input:** `protein_name` (string), `species` (int, NCBI taxid, default 9606 for human)
- **Output:** top interaction partners with combined_score, experiment/database/textmining subscores
- **Complexity:** Medium — need to resolve identifier first, then query network

#### 6. `pubmed` — Literature Search

- **Source:** NCBI E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`)
- **Input:** `query` (string, e.g. "p53 tumor suppressor"), `max_results` (int, default 5)
- **Output:** list of articles with PMID, title, authors, journal, year, abstract snippet
- **Complexity:** Medium — two-step: esearch → efetch

### Batch 3 — P2 (Pathways + alignment)

#### 7. `kegg` — Pathway Lookup

- **Source:** KEGG REST API (`https://rest.kegg.jp/`)
- **Input:** `gene_id` (string, e.g. "hsa:7157") or `query` (search term)
- **Output:** pathways the gene participates in, pathway name, ID, link
- **Complexity:** Medium — text parsing (KEGG returns flat text, not JSON)

---

## Architecture

### File structure

```
proteinbox/tools/
├── registry.py          # existing — unchanged
├── uniprot.py           # existing
├── blast.py             # existing
├── pdb.py               # new — Batch 1
├── alphafold.py         # new — Batch 1
├── sequence_analysis.py # new — Batch 1
├── interpro.py          # new — Batch 2
├── string_db.py         # new — Batch 2 (avoid shadowing `string` stdlib)
├── pubmed.py            # new — Batch 2
└── kegg.py              # new — Batch 3
```

### Design principles

1. **One file, one tool** — each tool is a single `@register_tool` class inheriting `ProteinTool`
2. **Auto-discovery** — `discover_tools()` already walks `proteinbox/tools/` with `pkgutil`, so new files are registered automatically
3. **`httpx` for all HTTP** — consistent with existing tools, `timeout=30`
4. **`ToolResult` contract** — `data` (structured dict for LLM), `display` (one-line human summary), `error` (on failure)
5. **No new dependencies** for Batch 1. `sequence_analysis` uses hand-rolled amino acid tables
6. **Idempotent & stateless** — every tool call is a pure function of its inputs

### `sequence_analysis` design detail

Since we avoid `biopython`, the tool includes:

```python
# Amino acid monoisotopic weights (daltons), pKa values for Henderson-Hasselbalch pI calc
AA_MW = {"A": 71.03711, "R": 156.10111, ...}  # 20 standard AAs
AA_PKA = {"D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07, "H": 6.00, "K": 10.53, "R": 12.48}
N_TERM_PKA = 9.69
C_TERM_PKA = 2.34
```

- **Molecular weight:** sum of residue weights + water (18.01524)
- **pI:** bisection method on net charge function using Henderson-Hasselbalch
- **GRAVY:** mean of Kyte-Doolittle hydropathy values
- **Extinction coefficient:** `nW * 5500 + nY * 1490 + nC * 125` (assumes all Cys reduced)

---

## Testing Strategy

Each tool gets a test file `tests/proteinbox/test_<tool>.py`:

- **Unit test:** mock `httpx.get`/`httpx.post`, verify parse logic and `ToolResult` structure
- **`sequence_analysis`:** no mocking needed, test with known sequences (e.g. insulin B chain)
- **Integration test (optional, not in CI):** real API calls with `@pytest.mark.integration`

---

## Change Summary

| Batch | Files Created | Files Modified | New Dependencies |
|-------|--------------|----------------|-----------------|
| 1 (P0) | `pdb.py`, `alphafold.py`, `sequence_analysis.py` + 3 test files | None | None |
| 2 (P1) | `string_db.py`, `interpro.py`, `pubmed.py` + 3 test files | None | None |
| 3 (P2) | `kegg.py` + 1 test file | None | None |
