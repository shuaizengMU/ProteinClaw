# ProteinClaw

The AI agent for protein bioinformatics. Describe your research goal in plain English — ProteinClaw figures out which tools to call, runs them, and streams a synthesized answer back to you.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Why ProteinClaw?

Protein research spans dozens of databases — UniProt, BLAST, ClinVar, gnomAD, GTEx, cBioPortal, and more. Moving data between them manually is slow, error-prone, and hard to reproduce.

ProteinClaw replaces that pipeline with a single conversational interface backed by a ReAct agent loop. You describe what you want; the agent decides which tools to call, calls them in sequence, and synthesizes the results into a coherent answer.

- **No scripting.** Natural language in, structured results out.
- **Multi-tool reasoning.** The agent chains tools automatically when your question requires it.
- **Streaming output.** See tool calls, intermediate observations, and the final answer as they happen.
- **Your LLM.** Works with OpenAI, Anthropic, DeepSeek, MiniMax, or a local Ollama model.

---

## What's Included

### The Agent Core

A ReAct loop (`proteinclaw/core/agent/`) that drives all three interfaces:

| Component | What it does |
|-----------|--------------|
| `loop.py` | Thought → Tool Call → Observation cycle, up to 10 steps |
| `llm.py` | LiteLLM-based multi-model router with async streaming |
| `prompt.py` | System prompt builder — injects available tools at runtime |
| `events.py` | Typed event stream: `ToolCallEvent`, `ObservationEvent`, `TokenEvent`, `DoneEvent`, `ErrorEvent` |

### Three Interfaces

| Interface | How to launch | Best for |
|-----------|--------------|----------|
| **Terminal UI** | `proteinclaw` | Interactive multi-turn research sessions |
| **One-shot CLI** | `proteinclaw query "..."` | Scripting, pipelines, quick lookups |
| **Desktop App** | Tauri `.dmg` / `.exe` | Non-technical users, GUI workflow |

### ProteinBox — the Tool Layer

All database integrations live in `proteinbox/api_tools/`. Each tool is independently testable and auto-discovered by the agent at startup. See [Supported Tools](#supported-tools) for the full list.

---

## Usage Examples

**Interactive TUI — multi-turn session:**
```
proteinclaw

> What is P04637?
  [tool: uniprot] P04637
  TP53_HUMAN is a tumor suppressor protein (393 aa) involved in cell cycle
  regulation, apoptosis, and DNA repair. It is mutated in ~50% of human cancers.

> Find proteins similar to its DNA-binding domain
  [tool: blast] VVRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGQMNRRPILTIITLEDSSGKLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPVHGQWLDSPRGQSTK
  Top hits: TP63_HUMAN (92% identity), TP73_HUMAN (88% identity), ...
```

**One-shot mode:**
```bash
proteinclaw query "What clinical variants are reported for BRCA1?"
proteinclaw query --model gpt-4o "Summarize the GTEx expression profile of TP53"
proteinclaw query "Is rs1801133 a pathogenic variant?"
```

**Example queries and what happens:**

| Query | Tools invoked |
|-------|--------------|
| `What is P04637?` | UniProt → returns annotation, GO terms, sequence length |
| `Find homologs of this sequence: <FASTA>` | BLAST → top hits with E-values and identity |
| `What variants are reported for BRCA1?` | ClinVar + gnomAD → clinical significance, allele frequencies |
| `Where is TP53 expressed?` | GTEx → tissue expression profile |
| `What pathways does EGFR participate in?` | WikiPathways → pathway list with descriptions |
| `Tell me about TP53 mutations in lung cancer` | cBioPortal + UniProt → mutation landscape + protein context |

**TUI slash commands:**

| Command | Effect |
|---------|--------|
| `/model <name>` | Switch LLM model for this session |
| `/tools` | List all registered tools |
| `/clear` | Clear conversation history |
| `/quit` | Exit |

---

## Installation

### Option 1 — Install with uv (Recommended)

**Prerequisite:** [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python 3.11+ is bundled automatically.

```bash
uv tool install git+https://github.com/shuaizengMU/ProteinClaw.git
proteinclaw
```

On first launch, a setup wizard prompts for your API key and default model. Settings are saved to `~/.config/proteinclaw/config.toml`.

You can also set keys via environment variables instead:

```bash
# macOS / Linux
export DEEPSEEK_API_KEY=sk-...
proteinclaw

# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-..."
proteinclaw
```

### Option 2 — Run from source

```bash
git clone https://github.com/shuaizengMU/ProteinClaw.git
cd ProteinClaw
uv sync
uv run proteinclaw
```

### Option 3 — Desktop App

Download the installer for your platform from the [Releases](https://github.com/shuaizengMU/ProteinClaw/releases) page.

| Platform | Format |
|----------|--------|
| macOS | `.dmg` (~20 MB download; ~500 MB installed) |
| Windows | `.exe` NSIS installer (~15 MB download) |

Python and all dependencies are downloaded automatically on first launch. No Python installation required.

### API Keys

You only need one key to get started.

| Variable | Provider | Required |
|----------|----------|----------|
| `OPENAI_API_KEY` | OpenAI | If using GPT-4o |
| `ANTHROPIC_API_KEY` | Anthropic | If using Claude |
| `DEEPSEEK_API_KEY` | DeepSeek | If using DeepSeek |
| `MINIMAX_API_KEY` | MiniMax | If using MiniMax |
| `NCBI_API_KEY` | NCBI | Optional — raises BLAST rate limit |

---

## Supported Tools

35 tools across 9 categories. **API** = calls an external database. **Local** = runs entirely on-device, no network required.

| Category | Tool | Type | Database / Source | What it fetches |
|----------|------|------|-------------------|-----------------|
| **Protein Annotation** | `uniprot` | API | UniProt | Name, function, genes, organism, sequence length, GO terms |
| | `interpro` | API | InterPro (EBI) | Domain/family annotations from Pfam, PROSITE, CDD with coordinates |
| | `panther` | API | PANTHER | Family/subfamily classification, protein class, GO slim |
| | `gene_ontology` | API | QuickGO (EBI) | GO annotations by molecular function, biological process, cellular component |
| | `phosphosite` | API | UniProt PTM | Post-translational modifications (phosphorylation, ubiquitination, acetylation) with positions |
| | `expasy_protparam` | Local | — | MW, pI, GRAVY, instability index, signal peptide and TM helix prediction |
| | `sequence_analysis` | Local | — | MW, isoelectric point, GRAVY, amino acid composition, extinction coefficients |
| **Protein Structure** | `alphafold` | API | AlphaFold DB (EBI) | Predicted structure, pLDDT confidence score, sequence coverage, model version |
| | `pdb` | API | RCSB Protein Data Bank | Structure metadata: method, resolution, organism, deposit date, chains, ligands |
| | `cath` | API | CATH Structural DB | Domain classification: Class, Architecture, Topology, Homology hierarchy |
| **Sequence & Motifs** | `blast` | API | NCBI BLAST | Sequence similarity against NR database; E-values, percent identity |
| | `elm` | Local | — | Short linear motif predictions: binding sites, modification sites, degradation signals |
| | `disprot` | API | DisProt | Experimentally validated intrinsically disordered regions with coordinates and evidence |
| | `mobidb` | API | MobiDB | Disorder consensus regions, curated disorder annotations |
| **Variants & Clinical** | `clinvar` | API | ClinVar (NCBI) | Clinical significance by gene; pathogenic/benign calls, associated conditions |
| | `dbsnp` | API | dbSNP (NCBI) | SNP details by rsID: position, alleles, clinical significance, minor allele frequency |
| | `gnomad` | API | gnomAD (Broad) | Gene constraint metrics: pLI, LOEUF, missense constraint |
| | `uniprot_variants` | API | EBI Proteins API | Known protein variants with clinical significance, consequence type, position |
| | `gwas_catalog` | API | GWAS Catalog (EBI) | GWAS associations by gene: traits, SNP rsIDs, p-values, risk alleles |
| **Gene & Genomics** | `ensembl` | API | Ensembl REST API | Gene/transcript IDs, genomic coordinates, biotype, orthologs, cross-references |
| | `ncbi_gene` | API | NCBI Gene (Entrez) | Gene ID, aliases, organism, chromosome location, summary |
| | `kegg` | API | KEGG REST API | KEGG pathway IDs and names for a gene |
| **Pathways & Interactions** | `reactome` | API | Reactome | Biological pathways with names, species, diagram availability, sub-pathways |
| | `wikipathways` | API | WikiPathways | Pathways by gene/term: IDs, names, species, revision dates |
| | `string` | API | STRING Database | Protein-protein interactions: top partners with combined and interaction scores |
| | `intact` | API | IntAct (EBI) | Curated binary protein interactions with detection methods, MI scores |
| **Disease & Drug** | `opentargets` | API | Open Targets Platform | Target-disease associations with evidence scores, known drugs, tractability |
| | `chembl` | API | ChEMBL (EBI) | Drug-target interactions: approved drugs and clinical candidates with mechanisms |
| | `disgenet` | API | DisGeNET + NCBI | Disease-gene associations with scores; NCBI fallback for Mendelian disease entries |
| | `omim` | API | OMIM (via NCBI) | Genetic disease associations via NCBI Gene → OMIM linkage |
| | `cbioportal` | API | cBioPortal | Cancer genomics: gene type, cytoband, mutation landscape across 535+ cancer studies |
| **Expression** | `gtex` | API | GTEx Portal | Tissue-specific gene expression (median TPM) across human tissues |
| | `protein_atlas` | API | Human Protein Atlas | Tissue expression, IHC detection, subcellular localization, cancer specificity |
| **Literature** | `pubmed` | API | PubMed (NCBI eUtils) | Article titles, authors, journal, year, abstract snippets |
| | `literature` | API | PubMed · Europe PMC · Semantic Scholar · CrossRef · bioRxiv · arXiv | Searches 6 sources in parallel, deduplicates by DOI, merges results with citation counts |

---

## License

MIT
