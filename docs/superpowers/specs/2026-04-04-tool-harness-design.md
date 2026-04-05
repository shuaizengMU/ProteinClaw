# Tool Harness Design

## Goal

Data-driven test harness that verifies each ProteinClaw tool can call its external API and return a valid result. Each tool has a test case defined in a JSON config; a single runner script executes them all.

## File Structure

```
harness/
├── runnable/
│   └── tool_tests.json   # test case config (tool name -> run() kwargs)
└── runner.py              # generic runner: discover tools, run each, report
scripts/
└── test-tools.sh          # convenience shell wrapper
```

## Config Format (`tool_tests.json`)

Key = tool registry name, value = kwargs passed to `tool.run(**kwargs)`:

```json
{
  "uniprot": { "accession_id": "P04637" },
  "blast":   { "sequence": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS", "max_hits": 2 }
}
```

## Runner (`harness/runner.py`)

- Uses `discover_tools()` to populate `TOOL_REGISTRY`
- Loads `tool_tests.json`, iterates entries
- For each tool: instantiate from registry, call `run(**params)`, check `result.success`
- Prints colored pass/fail per tool with timing and first line of `result.display` or `result.error`
- CLI args:
  - Positional tool names to filter (default: all)
  - `--skip-slow`: skip tools marked slow in config (blast)
  - `--timeout N`: per-tool timeout in seconds (default: 30)
- Exit code = number of failures (0 = all pass)

## Slow Tools

`blast` uses NCBI BLAST polling and can take 60s+. The config marks it with `"_slow": true` so `--skip-slow` can skip it.

## Shell Wrapper (`scripts/test-tools.sh`)

```bash
#!/usr/bin/env bash
uv run python -m harness.runner "$@"
```

## Tools Covered (27)

**proteinbox/tools/** (9): uniprot, blast, alphafold, interpro, kegg, pdb, pubmed, sequence_analysis, string

**proteinbox/api_tools/** (17): ncbi_gene, clinvar, reactome, ensembl, disgenet, chembl, omim, phosphosite, expasy_protparam, gene_ontology, panther, opentargets, protein_atlas, intact, cath, gwas_catalog, elm

**proteinbox/api_literature/** (1): literature
