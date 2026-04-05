# ProteinClaw New Tools — Round 2

**Date:** 2026-04-05
**Status:** Approved

## Background

ProteinClaw currently has 35 tools across 9 categories. This spec adds 20 new tools covering six gaps identified in a full coverage audit:

1. Protein evolution / orthologs — completely absent
2. Enzyme / metabolism — only KEGG pathways, no kinetics
3. Proteomics / protein abundance — only mRNA expression (GTEx, Protein Atlas)
4. Protein complexes — only binary interactions (STRING, IntAct)
5. Drug binding affinity — ChEMBL covers drugs but not measured binding data
6. PTM / structural features — phosphosite covers PTMs partially; membrane proteins and structural classification incomplete

All tools follow the existing `proteinbox/api_tools/` pattern: one file per tool, a class with a `run()` method, auto-registered via the tool registry.

---

## Architecture

No changes to the agent core, server, or CLI. Each new tool is a standalone file in `proteinbox/api_tools/`. The registry discovers tools automatically at startup.

### Authentication

Three tools require credentials:

| Tool | Auth method | Where stored |
|------|-------------|--------------|
| `drugbank` | Bearer token (free registration) | `~/.config/proteinclaw/config.toml` under `[api_keys]` |
| `brenda` | Email + password → SHA256 hash in request | Same config file |
| `pride` | None — read-only public API | — |

All other 17 tools are fully open REST APIs requiring no authentication.

---

## Tools

### Category 1 — Protein Evolution / Orthologs

#### `eggnog` — eggNOG

- **File:** `proteinbox/api_tools/eggnog.py`
- **API:** eggNOG v6 REST (`http://eggnog6.embl.de/api/`)
- **Input:** `gene_name: str` or `uniprot_id: str`, `organism: str = "human"`
- **Output:** COG functional category, orthologous group ID, number of orthologs, species coverage, best OG description
- **Error handling:** Falls back to taxon-level search if exact match fails

#### `consurf` — ConSurf DB

- **File:** `proteinbox/api_tools/consurf.py`
- **API:** ConSurf DB REST (`https://consurf.tau.ac.il/api/`)
- **Input:** `uniprot_id: str`
- **Output:** Per-residue conservation scores (1–9 scale), count of conserved/variable/average positions, functional residue flags
- **Note:** Returns pre-computed results; ConSurf DB covers all reviewed UniProt entries

#### `phylomedb` — PhylomeDB

- **File:** `proteinbox/api_tools/phylomedb.py`
- **API:** PhylomeDB REST (`http://phylomedb.org/api/`)
- **Input:** `uniprot_id: str` or `gene_name: str`
- **Output:** Phylome IDs, ortholog list with species and identity scores, paralog list, tree availability

---

### Category 2 — Enzyme / Metabolism

#### `brenda` — BRENDA Enzyme Database

- **File:** `proteinbox/api_tools/brenda.py`
- **API:** BRENDA SOAP API (free registration required)
- **Input:** `ec_number: str` or `gene_name: str`, `organism: str = "Homo sapiens"`
- **Output:** Km values, Vmax, substrate list, inhibitors, cofactors, optimal pH, optimal temperature, organism-specific entries
- **Auth:** Email + SHA256(password) sent per request per BRENDA spec

#### `expasy_enzyme` — ExPASy ENZYME

- **File:** `proteinbox/api_tools/expasy_enzyme.py`
- **API:** ExPASy ENZYME REST (`https://enzyme.expasy.org/`)
- **Input:** `ec_number: str` or `gene_name: str`
- **Output:** EC number, accepted name, reaction equation, Swiss-Prot cross-references, cofactors, comments

#### `sabio_rk` — SABIO-RK

- **File:** `proteinbox/api_tools/sabio_rk.py`
- **API:** SABIO-RK REST (`http://sabio.h-its.org/sabioRestWebServices/`)
- **Input:** `gene_name: str` or `uniprot_id: str`
- **Output:** Kinetic parameters (kcat, Km, Ki), reaction conditions (pH, temperature, buffer), organism, PubMed reference

---

### Category 3 — Proteomics / Protein Abundance

#### `paxdb` — PaxDb

- **File:** `proteinbox/api_tools/paxdb.py`
- **API:** PaxDb REST v4 (`https://pax-db.org/api/`)
- **Input:** `gene_name: str` or `uniprot_id: str`, `organism: str = "human"`
- **Output:** Protein abundance in ppm per tissue/dataset, integrated whole-organism score, dataset count, species coverage

#### `proteomicsdb` — ProteomicsDB

- **File:** `proteinbox/api_tools/proteomicsdb.py`
- **API:** ProteomicsDB REST (`https://www.proteomicsdb.org/api/`)
- **Input:** `gene_name: str` or `uniprot_id: str`
- **Output:** Expression by tissue and cell line (MS intensity), number of experiments, peptide count, protein detectability

#### `pride` — PRIDE Archive

- **File:** `proteinbox/api_tools/pride.py`
- **API:** PRIDE REST v1 (`https://www.ebi.ac.uk/pride/ws/archive/v2/`)
- **Input:** `gene_name: str` or `keyword: str`
- **Output:** Dataset list with accession, title, species, sample type, instrument, submission date, PubMed ID

---

### Category 4 — Protein Complexes

#### `complex_portal` — Complex Portal (EBI)

- **File:** `proteinbox/api_tools/complex_portal.py`
- **API:** Complex Portal REST (`https://www.ebi.ac.uk/intact/complex-ws/`)
- **Input:** `gene_name: str` or `uniprot_id: str`
- **Output:** Complex name, complex AC, subunit list with stoichiometry, biological function, GO annotations, species

#### `corum` — CORUM

- **File:** `proteinbox/api_tools/corum.py`
- **API:** CORUM REST (`https://mips.helmholtz-muenchen.de/corum/api/`)
- **Input:** `gene_name: str` or `uniprot_id: str`
- **Output:** Complex name, subunit gene list, tissue, purification method, disease association, PubMed reference

---

### Category 5 — Drug Binding Affinity

#### `bindingdb` — BindingDB

- **File:** `proteinbox/api_tools/bindingdb.py`
- **API:** BindingDB REST (`https://bindingdb.org/axis2/services/BDBService/`)
- **Input:** `uniprot_id: str` or `gene_name: str`, `affinity_type: str = "all"`
- **Output:** Ligand name, SMILES, Ki/Kd/IC50 values, assay type, organism, PubMed reference; top 10 hits by affinity

#### `drugbank` — DrugBank

- **File:** `proteinbox/api_tools/drugbank.py`
- **API:** DrugBank REST v1 (free tier, requires registration)
- **Input:** `gene_name: str` or `drug_name: str`
- **Output:** Drug name, mechanism of action, pharmacodynamics, ADMET properties, side effects, indication, drug interactions, targets
- **Auth:** Bearer token stored in config

#### `dgidb` — Drug-Gene Interaction Database

- **File:** `proteinbox/api_tools/dgidb.py`
- **API:** DGIdb GraphQL (`https://dgidb.org/api/graphql`)
- **Input:** `gene_name: str`
- **Output:** Drug names, interaction types (inhibitor/activator/etc.), source databases, interaction score, approval status

---

### Category 6 — PTM / Structural Features

#### `dbptm` — dbPTM

- **File:** `proteinbox/api_tools/dbptm.py`
- **API:** dbPTM REST (`https://awi.cuhk.edu.cn/dbPTM/api/`)
- **Input:** `uniprot_id: str` or `gene_name: str`
- **Output:** PTM type, modified residue, position, experimental evidence type, kinase (if phosphorylation), PubMed reference

#### `opm` — Orientations of Proteins in Membranes

- **File:** `proteinbox/api_tools/opm.py`
- **API:** OPM REST (`https://opm-api.protein.bio.uniprot.org/`)
- **Input:** `pdb_id: str` or `uniprot_id: str`
- **Output:** Membrane protein type (TM/monotopic/peripheral), tilt angle, membrane thickness, hydrophobic thickness, transmembrane segments

#### `imgt` — IMGT (Immunogenetics)

- **File:** `proteinbox/api_tools/imgt.py`
- **API:** IMGT/GENE-DB REST (`https://www.imgt.org/genedb/`)
- **Input:** `gene_name: str` (IG/TR/MHC gene, e.g. "IGHV1-2")
- **Output:** Gene classification (IG/TR subgroup), functionality, allele list, species coverage, chromosomal location

#### `scopedb` — SCOPe

- **File:** `proteinbox/api_tools/scopedb.py`
- **API:** SCOPe REST (`https://scop.berkeley.edu/`)
- **Input:** `pdb_id: str` or `uniprot_id: str`
- **Output:** SCOP class, fold, superfamily, family names and IDs; domain count; relationship to other proteins in same fold

---

## Implementation Notes

### Shared patterns across all tools

- All tools return a Pydantic model with `success: bool`, `error: str | None`, and tool-specific fields
- HTTP calls use `httpx` with a 30-second timeout
- Rate-limit-sensitive APIs (BRENDA, eggNOG) add a 0.5s delay between calls
- Each tool includes a `# Example` comment at the top showing a sample call and expected output shape

### Tool registration

No changes needed — `proteinbox/tools/registry.py` already auto-discovers all files in `api_tools/`. Adding a file is sufficient to register the tool.

### Config additions for authenticated tools

`proteinclaw/core/config.py` will add optional fields:
```toml
[api_keys]
drugbank_token = ""
brenda_email = ""
brenda_password = ""
```

The setup wizard in `cli-tui` does not need changes for now; keys can be added manually to config.toml or via environment variables (`DRUGBANK_TOKEN`, `BRENDA_EMAIL`, `BRENDA_PASSWORD`).

---

## Testing

Each tool gets a test in `tests/proteinbox/` that:
1. Mocks the HTTP response with a realistic fixture
2. Asserts the returned Pydantic model fields are populated correctly
3. Asserts `success=False` and a non-empty `error` field when the API returns 404/500

Tests do not make real network calls.

---

## API Verification Required

The following tools have APIs that must be confirmed working during implementation before writing the tool file. Fall back to parsing the download/export endpoint if no REST API exists:

- `consurf` — ConSurf DB may require FTP bulk download rather than per-protein REST calls
- `phylomedb` — REST API exists but versioning needs confirmation
- `corum` — may only provide flat-file downloads; if so, bundle a cached copy and query locally
- `opm` — OPM REST endpoint URL needs verification against current OPM website

---

## Out of Scope

- UI changes to display new tool categories
- Auto-discovery of API keys via OAuth flow
- Local model inference (ESMFold, DeepLoc) — deferred to a separate spec
- Linux-specific proteomics tools (MaxQuant, Perseus)
