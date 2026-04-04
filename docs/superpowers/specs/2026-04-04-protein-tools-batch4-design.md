# Protein Bioinformatics Tools — Batch 4 Design

**Date:** 2026-04-04
**Scope:** 8 new API tools for `proteinbox/api_tools/`
**Pattern:** Same as existing tools — one file per tool, `@register_tool`, `httpx` for HTTP, no new abstractions.

## Tools

### 1. Gene Ontology (QuickGO) — `gene_ontology.py`

- **Name:** `gene_ontology`
- **Purpose:** Retrieve GO functional annotations for a protein — molecular function, biological process, cellular component.
- **API:** `GET https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId={accession}&limit=100`
- **Input:** `accession` (UniProt ID, e.g. P04637)
- **Output:** GO terms grouped by aspect (`molecular_function`, `biological_process`, `cellular_component`), each with GO ID, term name, evidence code, qualifier, assigned_by.
- **Display:** `"P04637: 12 molecular_function, 34 biological_process, 8 cellular_component GO terms"`
- **Error handling:** 404 → "Protein not found"; timeout → standard error.

### 2. PANTHER — `panther.py`

- **Name:** `panther`
- **Purpose:** Classify a protein into PANTHER families/subfamilies and protein classes.
- **API:** `GET https://pantherdb.org/services/oai/pantherdb/geneinfo?geneInputList={gene_id}&organism=9606`
- **Input:** `gene` (gene symbol, e.g. TP53). Tool constructs the PANTHER gene ID format internally.
- **Output:** PANTHER family name + ID, subfamily name + ID, protein class, GO slim terms (molecular function, biological process).
- **Display:** `"TP53: Transformation/transcription domain-associated protein (PTHR10159), protein class: tumor suppressor"`
- **Note:** PANTHER API expects gene list format. We'll send `HUMAN|HGNC=<id>|UniProtKB=<acc>` or fall back to gene symbol search.

### 3. Open Targets — `opentargets.py`

- **Name:** `opentargets`
- **Purpose:** Get target-disease association evidence scores, known drugs, and tractability info.
- **API:** `POST https://api.platform.opentargets.org/api/v4/graphql`
- **Input:** `gene` (gene symbol, e.g. EGFR). Tool first resolves to Ensembl ID via search query, then fetches associations.
- **Output:** Top 15 associated diseases with `overallScore`, `datatypeScores` (genetic, somatic, drugs, literature, etc.), known drugs with phase and mechanism. Also tractability assessment (small molecule, antibody, other modalities).
- **Display:** `"EGFR: 45 disease associations, top: Lung carcinoma (0.92), 12 known drugs"`
- **GraphQL queries:** Two queries — `search` to resolve gene symbol → Ensembl ID, then `associatedDiseases` for the target.

### 4. Human Protein Atlas — `protein_atlas.py`

- **Name:** `protein_atlas`
- **Purpose:** Get tissue/cell expression levels, subcellular localization, and protein classification.
- **API:** `GET https://www.proteinatlas.org/{gene}.json`
- **Input:** `gene` (gene symbol, e.g. TP53)
- **Output:** RNA tissue expression (top tissues by nTPM), protein expression (detected/not detected per tissue via IHC), subcellular localization(s), protein class(es), RNA cancer specificity, prognostic data if available.
- **Display:** `"TP53: expressed in 45 tissues, localization: Nucleoplasm, class: Transcription factor, Cancer-related gene"`
- **Note:** The JSON response is large. Extract only the relevant summary fields.

### 5. IntAct — `intact.py`

- **Name:** `intact`
- **Purpose:** Retrieve curated molecular interactions with experimental evidence details.
- **API:** `GET https://www.ebi.ac.uk/intact/ws/interaction/findInteractor/{accession}?pageSize=20`
- **Input:** `accession` (UniProt ID, e.g. P04637)
- **Output:** Binary interactions listing: partner protein (accession + name), interaction type (e.g. physical association), detection method (e.g. two hybrid), MI score, publication count.
- **Display:** `"P04637: 156 interactions, top partners: MDM2 (0.95), EP300 (0.87), BRCA1 (0.82)"`
- **Fallback:** If the IntAct REST API format has changed, fall back to the PSICQUIC REST endpoint.

### 6. CATH — `cath.py`

- **Name:** `cath`
- **Purpose:** Get structural domain classification (Class → Architecture → Topology → Homologous superfamily).
- **API:** `GET https://www.cathdb.info/version/current/api/rest/uniprot/{accession}`
- **Input:** `accession` (UniProt ID, e.g. P04637)
- **Output:** List of CATH domain assignments, each with: CATH ID (e.g. 1.10.510.10), domain boundaries (start-end), class name, architecture name, topology name, superfamily name + description.
- **Display:** `"P04637: 2 CATH domains — 1.10.510.10 (Mainly Alpha, Orthogonal Bundle), 2.60.40.720 (Mainly Beta, Sandwich)"`
- **Error handling:** No CATH domains → return empty list with note "No structural domain assignments found".

### 7. GWAS Catalog — `gwas_catalog.py`

- **Name:** `gwas_catalog`
- **Purpose:** Find genome-wide association study results linking a gene to traits/diseases.
- **API:** `GET https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/search/findByGene?geneName={gene}`
- **Input:** `gene` (gene symbol, e.g. BRCA1)
- **Output:** SNPs with rsID, associated trait, p-value, risk allele, effect size (OR/beta), mapped gene, study accession, publication.
- **Display:** `"BRCA1: 23 GWAS associations — breast cancer (p=1.2e-45), ovarian cancer (p=3.4e-20), ..."`
- **Note:** The GWAS API can return large results. Limit to top 20 SNPs sorted by p-value.

### 8. ELM — `elm.py`

- **Name:** `elm`
- **Purpose:** Predict short linear motifs (SLiMs) — small functional sites in protein sequences, especially in disordered regions.
- **API:** `GET http://elm.eu.org/api/search/{sequence}.json` or by UniProt accession.
- **Input:** `sequence` (amino acid sequence) or `accession` (UniProt ID). Accepts either.
- **Output:** Predicted ELM instances with: motif name, ELM class/identifier, regex pattern, start-end positions, functional description, whether it overlaps a known domain (filtered vs unfiltered).
- **Display:** `"Found 15 ELM motifs: 3 LIG (ligand binding), 5 MOD (modification), 4 DOC (docking), 3 DEG (degradation)"`
- **Note:** ELM API may require User-Agent header. If API is unavailable, return a note directing users to the web interface.

## File Structure

All files go in `proteinbox/api_tools/`. No changes needed to `registry.py` — it already scans `api_tools/`.

```
proteinbox/api_tools/
├── __init__.py          (existing)
├── gene_ontology.py     (new)
├── panther.py           (new)
├── opentargets.py       (new)
├── protein_atlas.py     (new)
├── intact.py            (new)
├── cath.py              (new)
├── gwas_catalog.py      (new)
└── elm.py               (new)
```

## Update `/demo` Command

Add new demo examples in `cli-tui/src/app.rs` under `CommandDemo`:

- **Function Classification:** `"What are the GO annotations for P04637?"`, `"Classify TP53 into PANTHER families"`
- **Target Validation:** `"What diseases are associated with EGFR? (Open Targets)"`, `"Find GWAS associations for BRCA1"`
- **Expression:** `"Where is TP53 expressed? (Human Protein Atlas)"`
- **Interactions:** `"Find curated molecular interactions for P04637 (IntAct)"`
- **Structure Classification:** `"What CATH structural domains does P04637 have?"`
- **Sequence Motifs:** `"Predict short linear motifs in this sequence (ELM)"`

## Non-Goals

- No async refactor of the tool interface.
- No shared HTTP client or base class.
- No unit tests in this batch (manual verification via `discover_tools()`).
