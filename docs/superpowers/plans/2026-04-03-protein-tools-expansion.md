# Protein Tools Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand ProteinClaw from 2 tools to 9 — add `pdb`, `alphafold`, `sequence_analysis`, `interpro`, `string`, `pubmed`, `kegg`.

**Architecture:** Each tool is a single file in `proteinbox/tools/`, inheriting `ProteinTool` with `@register_tool`. Auto-discovered by `discover_tools()`. No changes to registry or agent loop.

**Tech Stack:** Python 3.11+, httpx, respx (tests)

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `proteinbox/tools/pdb.py` | RCSB PDB structure lookup |
| Create | `proteinbox/tools/alphafold.py` | AlphaFold DB predicted structure metadata |
| Create | `proteinbox/tools/sequence_analysis.py` | Local sequence property calculation |
| Create | `proteinbox/tools/interpro.py` | InterPro domain/family annotation |
| Create | `proteinbox/tools/string_db.py` | STRING protein-protein interactions |
| Create | `proteinbox/tools/pubmed.py` | PubMed literature search |
| Create | `proteinbox/tools/kegg.py` | KEGG pathway lookup |
| Create | `tests/proteinbox/test_pdb.py` | Tests for pdb tool |
| Create | `tests/proteinbox/test_alphafold.py` | Tests for alphafold tool |
| Create | `tests/proteinbox/test_sequence_analysis.py` | Tests for sequence_analysis tool |
| Create | `tests/proteinbox/test_interpro.py` | Tests for interpro tool |
| Create | `tests/proteinbox/test_string_db.py` | Tests for string tool |
| Create | `tests/proteinbox/test_pubmed.py` | Tests for pubmed tool |
| Create | `tests/proteinbox/test_kegg.py` | Tests for kegg tool |

---

## Batch 1 — P0: Core gaps

### Task 1: Create `pdb.py` — RCSB PDB structure lookup

**Files:**
- Create: `proteinbox/tools/pdb.py`

- [ ] **Step 1: Create `proteinbox/tools/pdb.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class PDBTool(ProteinTool):
    name: str = "pdb"
    description: str = (
        "Look up a protein structure in the RCSB Protein Data Bank by PDB ID. "
        "Returns title, experimental method, resolution, organism, deposit date, "
        "number of chains, and ligand names."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "pdb_id": {
                "type": "string",
                "description": "PDB identifier, e.g. 1TUP, 6LU7",
            }
        },
        "required": ["pdb_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        pdb_id = kwargs["pdb_id"].strip().upper()
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        try:
            resp = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"RCSB PDB returned {resp.status_code} for {pdb_id}",
            )

        raw = resp.json()

        title = raw.get("struct", {}).get("title", "Unknown")
        method = ", ".join(raw.get("exptl", [{}])[0].get("method", "Unknown").split())
        resolution = None
        for r in raw.get("rcsb_entry_info", {}).get("resolution_combined", []) or []:
            resolution = r
            break
        deposit_date = raw.get("rcsb_accession_info", {}).get("deposit_date", "Unknown")
        organism_list = [
            src.get("ncbi_scientific_name", "Unknown")
            for src in raw.get("rcsb_entity_source_organism", [])
        ]
        organism = ", ".join(set(organism_list)) if organism_list else "Unknown"
        polymer_count = raw.get("rcsb_entry_info", {}).get("polymer_entity_count", 0)

        # Ligands from nonpolymer entities
        ligands = []
        for ne in raw.get("rcsb_entry_info", {}).get("nonpolymer_bound_components", []) or []:
            ligands.append(ne)

        data = {
            "pdb_id": pdb_id,
            "title": title,
            "method": method,
            "resolution_angstrom": resolution,
            "deposit_date": deposit_date,
            "organism": organism,
            "polymer_chains": polymer_count,
            "ligands": ligands[:10],
        }
        res_str = f"{resolution} Å" if resolution else "N/A"
        display = f"{pdb_id}: {title[:80]} — {method}, {res_str}, {organism}"
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.pdb import PDBTool; print('OK')"
```

---

### Task 2: Create `test_pdb.py`

**Files:**
- Create: `tests/proteinbox/test_pdb.py`

- [ ] **Step 1: Create `tests/proteinbox/test_pdb.py`**

```python
import respx
import httpx
from proteinbox.tools.pdb import PDBTool

MOCK_PDB = {
    "struct": {"title": "CRYSTAL STRUCTURE OF P53 CORE DOMAIN"},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_entry_info": {
        "resolution_combined": [2.2],
        "polymer_entity_count": 4,
        "nonpolymer_bound_components": ["ZN"],
    },
    "rcsb_accession_info": {"deposit_date": "1994-08-25"},
    "rcsb_entity_source_organism": [
        {"ncbi_scientific_name": "Homo sapiens"}
    ],
}


@respx.mock
def test_pdb_success():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/1TUP").mock(
        return_value=httpx.Response(200, json=MOCK_PDB)
    )
    result = PDBTool().run(pdb_id="1tup")
    assert result.success is True
    assert result.data["pdb_id"] == "1TUP"
    assert result.data["method"] == "X-RAY DIFFRACTION"
    assert result.data["resolution_angstrom"] == 2.2
    assert result.data["organism"] == "Homo sapiens"


@respx.mock
def test_pdb_not_found():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/ZZZZ").mock(
        return_value=httpx.Response(404)
    )
    result = PDBTool().run(pdb_id="ZZZZ")
    assert result.success is False
    assert "404" in result.error
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_pdb.py -v
```

---

### Task 3: Create `alphafold.py` — AlphaFold DB lookup

**Files:**
- Create: `proteinbox/tools/alphafold.py`

- [ ] **Step 1: Create `proteinbox/tools/alphafold.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class AlphaFoldTool(ProteinTool):
    name: str = "alphafold"
    description: str = (
        "Look up a predicted protein structure from AlphaFold DB by UniProt accession. "
        "Returns model URL, mean pLDDT confidence score, sequence coverage, and version."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uniprot_id = kwargs["uniprot_id"].strip().upper()
        url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
        try:
            resp = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"No AlphaFold prediction found for {uniprot_id}",
            )
        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"AlphaFold DB returned {resp.status_code} for {uniprot_id}",
            )

        entries = resp.json()
        if not entries:
            return ToolResult(success=False, error=f"Empty response for {uniprot_id}")

        entry = entries[0]
        data = {
            "uniprot_id": uniprot_id,
            "model_url": entry.get("pdbUrl", ""),
            "cif_url": entry.get("cifUrl", ""),
            "mean_plddt": entry.get("globalMetricValue"),
            "sequence_length": entry.get("uniprotEnd", 0) - entry.get("uniprotStart", 0) + 1,
            "coverage_start": entry.get("uniprotStart"),
            "coverage_end": entry.get("uniprotEnd"),
            "model_version": entry.get("latestVersion"),
            "gene": entry.get("gene", ""),
            "organism": entry.get("organismScientificName", ""),
        }
        plddt = data["mean_plddt"]
        confidence = (
            "Very High" if plddt and plddt >= 90
            else "High" if plddt and plddt >= 70
            else "Low" if plddt and plddt >= 50
            else "Very Low" if plddt
            else "Unknown"
        )
        display = (
            f"AlphaFold {uniprot_id}: pLDDT={plddt} ({confidence}), "
            f"{data['sequence_length']} residues, v{data['model_version']}"
        )
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.alphafold import AlphaFoldTool; print('OK')"
```

---

### Task 4: Create `test_alphafold.py`

**Files:**
- Create: `tests/proteinbox/test_alphafold.py`

- [ ] **Step 1: Create `tests/proteinbox/test_alphafold.py`**

```python
import respx
import httpx
from proteinbox.tools.alphafold import AlphaFoldTool

MOCK_AF = [
    {
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.cif",
        "globalMetricValue": 75.5,
        "uniprotStart": 1,
        "uniprotEnd": 393,
        "latestVersion": 4,
        "gene": "TP53",
        "organismScientificName": "Homo sapiens",
    }
]


@respx.mock
def test_alphafold_success():
    respx.get("https://alphafold.ebi.ac.uk/api/prediction/P04637").mock(
        return_value=httpx.Response(200, json=MOCK_AF)
    )
    result = AlphaFoldTool().run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["uniprot_id"] == "P04637"
    assert result.data["mean_plddt"] == 75.5
    assert result.data["sequence_length"] == 393
    assert "High" in result.display


@respx.mock
def test_alphafold_not_found():
    respx.get("https://alphafold.ebi.ac.uk/api/prediction/XXXXXX").mock(
        return_value=httpx.Response(404)
    )
    result = AlphaFoldTool().run(uniprot_id="XXXXXX")
    assert result.success is False
    assert "not found" in result.error.lower() or "404" in result.error
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_alphafold.py -v
```

---

### Task 5: Create `sequence_analysis.py` — local sequence properties

**Files:**
- Create: `proteinbox/tools/sequence_analysis.py`

- [ ] **Step 1: Create `proteinbox/tools/sequence_analysis.py`**

```python
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

# Monoisotopic residue masses (Da) — standard 20 amino acids
AA_MW: dict[str, float] = {
    "A": 71.03711, "R": 156.10111, "N": 114.04293, "D": 115.02694,
    "C": 103.00919, "E": 129.04259, "Q": 128.05858, "G": 57.02146,
    "H": 137.05891, "I": 113.08406, "L": 113.08406, "K": 128.09496,
    "M": 131.04049, "F": 147.06841, "P": 97.05276, "S": 87.03203,
    "T": 101.04768, "W": 186.07931, "Y": 163.06333, "V": 99.06841,
}
WATER_MW = 18.01056

# pKa values for isoelectric point calculation (EMBOSS scale)
PKA_SIDE: dict[str, float] = {
    "D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07,
    "H": 6.00, "K": 10.53, "R": 12.48,
}
PKA_N_TERM = 8.60
PKA_C_TERM = 3.60

# Kyte-Doolittle hydropathy scale
KD_HYDROPATHY: dict[str, float] = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "E": -3.5, "Q": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}


def _net_charge(seq: str, ph: float) -> float:
    """Net charge at given pH via Henderson-Hasselbalch."""
    charge = 0.0
    # N-terminus (positive)
    charge += 1.0 / (1.0 + 10 ** (ph - PKA_N_TERM))
    # C-terminus (negative)
    charge -= 1.0 / (1.0 + 10 ** (PKA_C_TERM - ph))
    for aa in seq:
        if aa in ("D", "E", "C", "Y"):
            charge -= 1.0 / (1.0 + 10 ** (PKA_SIDE[aa] - ph))
        elif aa in ("H", "K", "R"):
            charge += 1.0 / (1.0 + 10 ** (ph - PKA_SIDE[aa]))
    return charge


def _isoelectric_point(seq: str) -> float:
    """Bisection method to find pH where net charge ≈ 0."""
    lo, hi = 0.0, 14.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _net_charge(seq, mid) > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


@register_tool
class SequenceAnalysisTool(ProteinTool):
    name: str = "sequence_analysis"
    description: str = (
        "Analyze a protein sequence locally. Returns molecular weight, "
        "isoelectric point (pI), amino acid composition, GRAVY hydropathy score, "
        "and extinction coefficients. No external API call — instant results."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence in single-letter amino acid codes (e.g. MVLSPADKTNVKA). FASTA headers are stripped automatically.",
            }
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        raw_seq = kwargs["sequence"].strip()
        # Strip FASTA header
        if raw_seq.startswith(">"):
            raw_seq = "\n".join(raw_seq.split("\n")[1:])
        seq = "".join(c.upper() for c in raw_seq if c.isalpha())

        if not seq:
            return ToolResult(success=False, error="Empty sequence provided")

        unknown = set(seq) - set(AA_MW)
        if unknown:
            return ToolResult(
                success=False,
                error=f"Unknown amino acid(s): {', '.join(sorted(unknown))}",
            )

        length = len(seq)

        # Molecular weight
        mw = sum(AA_MW[aa] for aa in seq) + WATER_MW

        # Isoelectric point
        pi = _isoelectric_point(seq)

        # Amino acid composition
        composition = {}
        for aa in sorted(set(seq)):
            count = seq.count(aa)
            composition[aa] = {"count": count, "percent": round(count / length * 100, 1)}

        # GRAVY (grand average of hydropathy)
        gravy = round(sum(KD_HYDROPATHY[aa] for aa in seq) / length, 3)

        # Extinction coefficients (Pace et al.)
        n_w = seq.count("W")
        n_y = seq.count("Y")
        n_c = seq.count("C")
        ext_reduced = n_w * 5500 + n_y * 1490
        ext_oxidized = ext_reduced + (n_c // 2) * 125

        data = {
            "length": length,
            "molecular_weight_da": round(mw, 2),
            "isoelectric_point": pi,
            "gravy": gravy,
            "extinction_coefficient_reduced": ext_reduced,
            "extinction_coefficient_oxidized": ext_oxidized,
            "composition": composition,
        }
        display = (
            f"{length} aa, MW={mw:.0f} Da, pI={pi}, GRAVY={gravy}"
        )
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.sequence_analysis import SequenceAnalysisTool; print('OK')"
```

---

### Task 6: Create `test_sequence_analysis.py`

**Files:**
- Create: `tests/proteinbox/test_sequence_analysis.py`

- [ ] **Step 1: Create `tests/proteinbox/test_sequence_analysis.py`**

```python
from proteinbox.tools.sequence_analysis import SequenceAnalysisTool

# Human insulin B-chain (30 aa)
INSULIN_B = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"


def test_seq_analysis_basic():
    result = SequenceAnalysisTool().run(sequence=INSULIN_B)
    assert result.success is True
    assert result.data["length"] == 30
    assert 3000 < result.data["molecular_weight_da"] < 4000
    assert 5.0 < result.data["isoelectric_point"] < 8.0
    assert isinstance(result.data["gravy"], float)
    assert "L" in result.data["composition"]


def test_seq_analysis_fasta():
    fasta = ">sp|P01308|INS_HUMAN\nFVNQHLCGSHLVEALYLVCGERGFFYTPKT"
    result = SequenceAnalysisTool().run(sequence=fasta)
    assert result.success is True
    assert result.data["length"] == 30


def test_seq_analysis_empty():
    result = SequenceAnalysisTool().run(sequence="")
    assert result.success is False


def test_seq_analysis_unknown_aa():
    result = SequenceAnalysisTool().run(sequence="MVLXBZ")
    assert result.success is False
    assert "Unknown" in result.error


def test_extinction_coefficients():
    # A sequence with known W, Y, C counts
    seq = "WCYWCC"  # 1W, 1Y, 3C
    result = SequenceAnalysisTool().run(sequence=seq)
    assert result.success is True
    assert result.data["extinction_coefficient_reduced"] == 1 * 5500 + 1 * 1490
    assert result.data["extinction_coefficient_oxidized"] == 1 * 5500 + 1 * 1490 + 1 * 125
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_sequence_analysis.py -v
```

---

### Task 7: Run all Batch 1 tests + verify auto-discovery

- [ ] **Step 1: Run all proteinbox tests**

```bash
python -m pytest tests/proteinbox/ -v
```

All existing + new tests must pass.

- [ ] **Step 2: Verify auto-discovery picks up new tools**

```bash
python -c "
from proteinbox.tools.registry import discover_tools
tools = discover_tools()
print(f'{len(tools)} tools registered: {sorted(tools.keys())}')
assert 'pdb' in tools
assert 'alphafold' in tools
assert 'sequence_analysis' in tools
print('Auto-discovery OK')
"
```

Expected output: `5 tools registered: ['alphafold', 'blast', 'pdb', 'sequence_analysis', 'uniprot']`

- [ ] **Step 3: Commit Batch 1**

```bash
git add proteinbox/tools/pdb.py proteinbox/tools/alphafold.py proteinbox/tools/sequence_analysis.py \
       tests/proteinbox/test_pdb.py tests/proteinbox/test_alphafold.py tests/proteinbox/test_sequence_analysis.py
git commit -m "feat(tools): add pdb, alphafold, and sequence_analysis tools (Batch 1)"
```

---

## Batch 2 — P1: Annotation + interactions + literature

### Task 8: Create `interpro.py` — domain/family annotation

**Files:**
- Create: `proteinbox/tools/interpro.py`

- [ ] **Step 1: Create `proteinbox/tools/interpro.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class InterProTool(ProteinTool):
    name: str = "interpro"
    description: str = (
        "Look up protein domain and family annotations from InterPro by UniProt accession. "
        "Returns domain hits from Pfam, PROSITE, CDD, and other member databases "
        "with coordinates and descriptions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uniprot_id = kwargs["uniprot_id"].strip().upper()
        url = f"https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/{uniprot_id}"
        try:
            resp = httpx.get(url, timeout=30, headers={"Accept": "application/json"})
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"InterPro returned {resp.status_code} for {uniprot_id}",
            )

        raw = resp.json()
        results = raw.get("results", [])

        domains = []
        for entry in results:
            meta = entry.get("metadata", {})
            # Extract coordinates from protein locations
            locations = []
            for protein in entry.get("proteins", []):
                for loc_group in protein.get("entry_protein_locations", []):
                    for frag in loc_group.get("fragments", []):
                        locations.append({
                            "start": frag.get("start"),
                            "end": frag.get("end"),
                        })

            domains.append({
                "accession": meta.get("accession", ""),
                "name": meta.get("name", ""),
                "type": meta.get("type", ""),
                "source_database": meta.get("source_database", ""),
                "locations": locations,
            })

        data = {
            "uniprot_id": uniprot_id,
            "domain_count": len(domains),
            "domains": domains[:20],  # cap for LLM context
        }
        display = f"{uniprot_id}: {len(domains)} InterPro domain(s) found"
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.interpro import InterProTool; print('OK')"
```

---

### Task 9: Create `test_interpro.py`

**Files:**
- Create: `tests/proteinbox/test_interpro.py`

- [ ] **Step 1: Create `tests/proteinbox/test_interpro.py`**

```python
import respx
import httpx
from proteinbox.tools.interpro import InterProTool

MOCK_INTERPRO = {
    "results": [
        {
            "metadata": {
                "accession": "IPR011615",
                "name": "p53-like transcription factor",
                "type": "domain",
                "source_database": "interpro",
            },
            "proteins": [
                {
                    "entry_protein_locations": [
                        {"fragments": [{"start": 94, "end": 292}]}
                    ]
                }
            ],
        }
    ]
}


@respx.mock
def test_interpro_success():
    respx.get(
        "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/P04637"
    ).mock(return_value=httpx.Response(200, json=MOCK_INTERPRO))
    result = InterProTool().run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["domain_count"] == 1
    assert result.data["domains"][0]["name"] == "p53-like transcription factor"
    assert result.data["domains"][0]["locations"][0]["start"] == 94


@respx.mock
def test_interpro_not_found():
    respx.get(
        "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/XXXXXX"
    ).mock(return_value=httpx.Response(404))
    result = InterProTool().run(uniprot_id="XXXXXX")
    assert result.success is False
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_interpro.py -v
```

---

### Task 10: Create `string_db.py` — protein-protein interactions

**Files:**
- Create: `proteinbox/tools/string_db.py`

- [ ] **Step 1: Create `proteinbox/tools/string_db.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class STRINGTool(ProteinTool):
    name: str = "string"
    description: str = (
        "Query the STRING database for protein-protein interaction partners. "
        "Input a protein name (e.g. TP53) and species taxid (default 9606 for human). "
        "Returns top interaction partners with combined scores."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "protein_name": {
                "type": "string",
                "description": "Protein or gene name, e.g. TP53, BRCA1",
            },
            "species": {
                "type": "integer",
                "description": "NCBI taxonomy ID (default: 9606 for Homo sapiens)",
                "default": 9606,
            },
            "limit": {
                "type": "integer",
                "description": "Max number of interaction partners (default: 10)",
                "default": 10,
            },
        },
        "required": ["protein_name"],
    }

    def run(self, **kwargs) -> ToolResult:
        protein = kwargs["protein_name"].strip()
        species = int(kwargs.get("species", 9606))
        limit = int(kwargs.get("limit", 10))

        url = "https://string-db.org/api/json/network"
        params = {
            "identifiers": protein,
            "species": species,
            "limit": limit,
            "caller_identity": "proteinclaw",
        }
        try:
            resp = httpx.get(url, params=params, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"STRING returned {resp.status_code}",
            )

        entries = resp.json()
        if not entries:
            return ToolResult(
                success=False,
                error=f"No interactions found for {protein} (species {species})",
            )

        partners = []
        seen = set()
        for e in entries:
            a = e.get("preferredName_A", "")
            b = e.get("preferredName_B", "")
            partner = b if a.upper() == protein.upper() else a
            if partner in seen:
                continue
            seen.add(partner)
            partners.append({
                "partner": partner,
                "combined_score": e.get("score", 0),
                "nscore": e.get("nscore", 0),
                "fscore": e.get("fscore", 0),
                "pscore": e.get("pscore", 0),
                "ascore": e.get("ascore", 0),
                "escore": e.get("escore", 0),
                "dscore": e.get("dscore", 0),
                "tscore": e.get("tscore", 0),
            })

        partners.sort(key=lambda x: x["combined_score"], reverse=True)

        data = {
            "query": protein,
            "species": species,
            "partner_count": len(partners),
            "partners": partners[:limit],
        }
        top3 = ", ".join(p["partner"] for p in partners[:3])
        display = f"{protein}: {len(partners)} interaction partners. Top: {top3}"
        return ToolResult(success=True, data=data, display=display)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.string_db import STRINGTool; print('OK')"
```

---

### Task 11: Create `test_string_db.py`

**Files:**
- Create: `tests/proteinbox/test_string_db.py`

- [ ] **Step 1: Create `tests/proteinbox/test_string_db.py`**

```python
import respx
import httpx
from proteinbox.tools.string_db import STRINGTool

MOCK_STRING = [
    {
        "preferredName_A": "TP53",
        "preferredName_B": "MDM2",
        "score": 0.999,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.95, "dscore": 0.9, "tscore": 0.95,
    },
    {
        "preferredName_A": "TP53",
        "preferredName_B": "CDKN1A",
        "score": 0.998,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.9, "dscore": 0.85, "tscore": 0.9,
    },
]


@respx.mock
def test_string_success():
    respx.get("https://string-db.org/api/json/network").mock(
        return_value=httpx.Response(200, json=MOCK_STRING)
    )
    result = STRINGTool().run(protein_name="TP53")
    assert result.success is True
    assert result.data["partner_count"] == 2
    names = [p["partner"] for p in result.data["partners"]]
    assert "MDM2" in names
    assert "CDKN1A" in names


@respx.mock
def test_string_no_results():
    respx.get("https://string-db.org/api/json/network").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = STRINGTool().run(protein_name="NOTAPROTEIN")
    assert result.success is False
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_string_db.py -v
```

---

### Task 12: Create `pubmed.py` — literature search

**Files:**
- Create: `proteinbox/tools/pubmed.py`

- [ ] **Step 1: Create `proteinbox/tools/pubmed.py`**

```python
import httpx
import xml.etree.ElementTree as ET
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@register_tool
class PubMedTool(ProteinTool):
    name: str = "pubmed"
    description: str = (
        "Search PubMed for biomedical literature. Returns article titles, authors, "
        "journal, year, and abstract snippets. Useful for finding papers about "
        "specific proteins, pathways, or biological processes."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'p53 apoptosis' or 'BRCA1 DNA repair'",
            },
            "max_results": {
                "type": "integer",
                "description": "Max articles to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        max_results = int(kwargs.get("max_results", 5))

        # Step 1: esearch to get PMIDs
        search_url = f"{EUTILS_BASE}/esearch.fcgi"
        try:
            resp = httpx.get(
                search_url,
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                },
                timeout=30,
            )
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"PubMed search failed: {e}")

        if resp.status_code != 200:
            return ToolResult(success=False, error=f"PubMed returned {resp.status_code}")

        search_data = resp.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return ToolResult(success=False, error=f"No PubMed results for '{query}'")

        # Step 2: efetch to get article details
        fetch_url = f"{EUTILS_BASE}/efetch.fcgi"
        try:
            resp = httpx.get(
                fetch_url,
                params={
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "xml",
                },
                timeout=30,
            )
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"PubMed fetch failed: {e}")

        if resp.status_code != 200:
            return ToolResult(success=False, error=f"PubMed fetch returned {resp.status_code}")

        articles = self._parse_articles(resp.text)

        data = {
            "query": query,
            "total_found": int(
                search_data.get("esearchresult", {}).get("count", 0)
            ),
            "articles": articles,
        }
        display = f"PubMed: {len(articles)} articles for '{query}'"
        return ToolResult(success=True, data=data, display=display)

    def _parse_articles(self, xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        articles = []
        for article_el in root.iter("PubmedArticle"):
            medline = article_el.find(".//MedlineCitation")
            if medline is None:
                continue
            pmid = medline.findtext("PMID", "")
            art = medline.find("Article")
            if art is None:
                continue
            title = art.findtext("ArticleTitle", "")
            journal = art.findtext(".//Journal/Title", "")
            year = art.findtext(".//Journal/JournalIssue/PubDate/Year", "")
            abstract = art.findtext(".//Abstract/AbstractText", "")
            authors = []
            for au in (art.find("AuthorList") or []):
                last = au.findtext("LastName", "")
                init = au.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {init}".strip())
            articles.append({
                "pmid": pmid,
                "title": title,
                "authors": authors[:5],  # cap for context
                "journal": journal,
                "year": year,
                "abstract": (abstract[:500] + "...") if abstract and len(abstract) > 500 else abstract,
            })
        return articles
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.pubmed import PubMedTool; print('OK')"
```

---

### Task 13: Create `test_pubmed.py`

**Files:**
- Create: `tests/proteinbox/test_pubmed.py`

- [ ] **Step 1: Create `tests/proteinbox/test_pubmed.py`**

```python
import respx
import httpx
from proteinbox.tools.pubmed import PubMedTool, EUTILS_BASE

MOCK_SEARCH = {
    "esearchresult": {
        "count": "42",
        "idlist": ["12345678"],
    }
}

MOCK_FETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>p53 and apoptosis: a review</ArticleTitle>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Nature Reviews Cancer</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <Abstract><AbstractText>This review covers p53-mediated apoptosis pathways.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


@respx.mock
def test_pubmed_success():
    respx.get(f"{EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=MOCK_SEARCH)
    )
    respx.get(f"{EUTILS_BASE}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text=MOCK_FETCH_XML)
    )
    result = PubMedTool().run(query="p53 apoptosis")
    assert result.success is True
    assert result.data["total_found"] == 42
    assert len(result.data["articles"]) == 1
    art = result.data["articles"][0]
    assert art["pmid"] == "12345678"
    assert "p53" in art["title"]
    assert art["year"] == "2023"


@respx.mock
def test_pubmed_no_results():
    respx.get(f"{EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    result = PubMedTool().run(query="xyznonexistent")
    assert result.success is False
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_pubmed.py -v
```

---

### Task 14: Run all Batch 2 tests + verify auto-discovery

- [ ] **Step 1: Run all proteinbox tests**

```bash
python -m pytest tests/proteinbox/ -v
```

- [ ] **Step 2: Verify all 8 tools are discovered**

```bash
python -c "
from proteinbox.tools.registry import discover_tools
tools = discover_tools()
print(f'{len(tools)} tools registered: {sorted(tools.keys())}')
expected = {'alphafold','blast','interpro','pdb','pubmed','sequence_analysis','string','uniprot'}
assert set(tools.keys()) == expected, f'Missing: {expected - set(tools.keys())}'
print('Auto-discovery OK')
"
```

- [ ] **Step 3: Commit Batch 2**

```bash
git add proteinbox/tools/interpro.py proteinbox/tools/string_db.py proteinbox/tools/pubmed.py \
       tests/proteinbox/test_interpro.py tests/proteinbox/test_string_db.py tests/proteinbox/test_pubmed.py
git commit -m "feat(tools): add interpro, string, and pubmed tools (Batch 2)"
```

---

## Batch 3 — P2: Pathways

### Task 15: Create `kegg.py` — KEGG pathway lookup

**Files:**
- Create: `proteinbox/tools/kegg.py`

- [ ] **Step 1: Create `proteinbox/tools/kegg.py`**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

KEGG_BASE = "https://rest.kegg.jp"


@register_tool
class KEGGTool(ProteinTool):
    name: str = "kegg"
    description: str = (
        "Look up KEGG pathway information for a gene. "
        "Input a KEGG gene ID (e.g. hsa:7157 for human TP53) or search by gene name. "
        "Returns pathways the gene participates in."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "KEGG gene ID (e.g. hsa:7157) or search term (e.g. 'TP53 human')",
            }
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()

        # If it looks like a KEGG gene ID (org:id), use it directly
        if ":" in query and len(query.split(":")[0]) <= 4:
            gene_id = query
        else:
            # Search for the gene
            gene_id = self._find_gene(query)
            if gene_id is None:
                return ToolResult(
                    success=False,
                    error=f"No KEGG gene found for '{query}'",
                )

        # Get pathway links for this gene
        try:
            resp = httpx.get(f"{KEGG_BASE}/link/pathway/{gene_id}", timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200 or not resp.text.strip():
            return ToolResult(
                success=False,
                error=f"No pathways found for {gene_id}",
            )

        pathway_ids = []
        for line in resp.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) == 2:
                pathway_ids.append(parts[1].replace("path:", ""))

        if not pathway_ids:
            return ToolResult(success=False, error=f"No pathways for {gene_id}")

        # Get pathway names
        pathways = []
        for pid in pathway_ids[:15]:  # cap
            name = self._get_pathway_name(pid)
            pathways.append({
                "pathway_id": pid,
                "name": name,
                "url": f"https://www.kegg.jp/pathway/{pid}",
            })

        data = {
            "gene_id": gene_id,
            "pathway_count": len(pathways),
            "pathways": pathways,
        }
        top = pathways[0]["name"] if pathways else "none"
        display = f"{gene_id}: {len(pathways)} KEGG pathways. Top: {top}"
        return ToolResult(success=True, data=data, display=display)

    def _find_gene(self, query: str) -> str | None:
        try:
            resp = httpx.get(f"{KEGG_BASE}/find/genes/{query}", timeout=30)
        except httpx.RequestError:
            return None
        if resp.status_code != 200 or not resp.text.strip():
            return None
        first_line = resp.text.strip().split("\n")[0]
        return first_line.split("\t")[0] if "\t" in first_line else None

    def _get_pathway_name(self, pathway_id: str) -> str:
        try:
            resp = httpx.get(f"{KEGG_BASE}/get/{pathway_id}", timeout=15)
        except httpx.RequestError:
            return pathway_id
        for line in resp.text.split("\n"):
            if line.startswith("NAME"):
                return line.replace("NAME", "").strip().rstrip(" - Homo sapiens (human)")
        return pathway_id
```

- [ ] **Step 2: Verify import**

```bash
python -c "from proteinbox.tools.kegg import KEGGTool; print('OK')"
```

---

### Task 16: Create `test_kegg.py`

**Files:**
- Create: `tests/proteinbox/test_kegg.py`

- [ ] **Step 1: Create `tests/proteinbox/test_kegg.py`**

```python
import respx
import httpx
from proteinbox.tools.kegg import KEGGTool, KEGG_BASE


@respx.mock
def test_kegg_direct_id():
    respx.get(f"{KEGG_BASE}/link/pathway/hsa:7157").mock(
        return_value=httpx.Response(
            200,
            text="hsa:7157\tpath:hsa04115\nhsa:7157\tpath:hsa05200\n",
        )
    )
    respx.get(f"{KEGG_BASE}/get/hsa04115").mock(
        return_value=httpx.Response(200, text="NAME        p53 signaling pathway\nDESCRIPTION ...\n")
    )
    respx.get(f"{KEGG_BASE}/get/hsa05200").mock(
        return_value=httpx.Response(200, text="NAME        Pathways in cancer\nDESCRIPTION ...\n")
    )
    result = KEGGTool().run(query="hsa:7157")
    assert result.success is True
    assert result.data["pathway_count"] == 2
    assert any("p53" in p["name"].lower() for p in result.data["pathways"])


@respx.mock
def test_kegg_search():
    respx.get(f"{KEGG_BASE}/find/genes/TP53 human").mock(
        return_value=httpx.Response(200, text="hsa:7157\tTP53; tumor protein p53\n")
    )
    respx.get(f"{KEGG_BASE}/link/pathway/hsa:7157").mock(
        return_value=httpx.Response(200, text="hsa:7157\tpath:hsa04115\n")
    )
    respx.get(f"{KEGG_BASE}/get/hsa04115").mock(
        return_value=httpx.Response(200, text="NAME        p53 signaling pathway\n")
    )
    result = KEGGTool().run(query="TP53 human")
    assert result.success is True
    assert result.data["gene_id"] == "hsa:7157"


@respx.mock
def test_kegg_not_found():
    respx.get(f"{KEGG_BASE}/find/genes/NOTAREALGENE").mock(
        return_value=httpx.Response(200, text="")
    )
    result = KEGGTool().run(query="NOTAREALGENE")
    assert result.success is False
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/proteinbox/test_kegg.py -v
```

---

### Task 17: Final verification — all 9 tools

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/proteinbox/ -v
```

- [ ] **Step 2: Verify all 9 tools discovered**

```bash
python -c "
from proteinbox.tools.registry import discover_tools
tools = discover_tools()
print(f'{len(tools)} tools registered: {sorted(tools.keys())}')
expected = {'alphafold','blast','interpro','kegg','pdb','pubmed','sequence_analysis','string','uniprot'}
assert set(tools.keys()) == expected, f'Missing: {expected - set(tools.keys())}'
print('All 9 tools OK')
"
```

- [ ] **Step 3: Commit Batch 3**

```bash
git add proteinbox/tools/kegg.py tests/proteinbox/test_kegg.py
git commit -m "feat(tools): add kegg pathway tool (Batch 3)"
```
