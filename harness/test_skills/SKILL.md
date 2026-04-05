---
name: test-tools
description: Use when you need to verify that ProteinClaw bioinformatics tools can reach their external APIs and return valid results. Trigger on "test tools", "check tools", "run harness", "tool connectivity", or after modifying any tool in proteinbox/tools/ or proteinbox/api_tools/.
---

# Test Tools

Run the data-driven tool harness to verify all ProteinClaw tools can call their external APIs.

## How to Run

```bash
# All tools (skip slow ones like blast)
scripts/test-tools.sh --skip-slow

# All tools including slow
scripts/test-tools.sh

# Specific tools only
scripts/test-tools.sh uniprot kegg pdb

# Custom timeout (default 30s)
scripts/test-tools.sh --timeout 60
```

## What It Tests

27 tools across 3 packages — each gets instantiated, called with real parameters, and checked for `result.success`:

| Package | Tools |
|---------|-------|
| `proteinbox/tools/` | uniprot, blast, alphafold, interpro, kegg, pdb, pubmed, sequence_analysis, string |
| `proteinbox/api_tools/` | ncbi_gene, clinvar, reactome, ensembl, disgenet, chembl, omim, phosphosite, expasy_protparam, gene_ontology, panther, opentargets, protein_atlas, intact, cath, gwas_catalog, elm |
| `proteinbox/api_literature/` | literature |

Test parameters are defined in `harness/runnable/tool_tests.json`.

## Reading Results

- Exit code = number of failures (0 = all pass)
- `blast` is marked `_slow` — skipped with `--skip-slow`
- Failures show tool name, elapsed time, and error message
- A failure summary is printed at the end

## When a Tool Fails

1. Check if it's a transient issue (rate limit, network timeout) — re-run that single tool
2. If persistent, read the tool source in `proteinbox/tools/` or `proteinbox/api_tools/`
3. Test the API endpoint directly with `curl` to confirm the issue
4. Common causes: API endpoint changed, field renamed in response, rate limiting
