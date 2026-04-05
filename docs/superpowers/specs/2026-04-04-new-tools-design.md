# New Bioinformatics Tools — Design Spec

## Summary

Add 8 new tools to ProteinClaw covering variants, expression, disorder, pathways, and cancer mutations. All use free public APIs with no API key required.

## Tools

### 1. dbSNP (`dbsnp`)
- **Package:** `proteinbox/api_tools/dbsnp.py`
- **API:** NCBI E-utilities `esummary.fcgi?db=snp`
- **Parameters:** `rsid` (string, e.g. "rs7412")
- **Returns:** SNP position, alleles, clinical significance, gene, global MAF
- **Note:** Add 0.4s delay like clinvar to avoid NCBI rate limits

### 2. gnomAD (`gnomad`)
- **Package:** `proteinbox/api_tools/gnomad.py`
- **API:** `https://gnomad.broadinstitute.org/api` (GraphQL)
- **Parameters:** `gene` (string, e.g. "TP53"), `reference_genome` (string, default "GRCh38")
- **Returns:** Gene constraints (pLI, LOEUF), top variants with population frequencies

### 3. GTEx (`gtex`)
- **Package:** `proteinbox/api_tools/gtex.py`
- **API:** `https://gtexportal.org/api/v2/`
- **Parameters:** `gene` (string, e.g. "TP53")
- **Flow:** Step 1: resolve gene symbol → gencodeId via `/reference/gene`. Step 2: get expression via `/expression/medianGeneExpression`
- **Returns:** Median TPM per tissue, top expressed tissues

### 4. MobiDB (`mobidb`)
- **Package:** `proteinbox/api_tools/mobidb.py`
- **API:** `https://mobidb.bio.unipd.it/api/download?acc={acc}&format=json`
- **Parameters:** `accession` (string, e.g. "P04637")
- **Returns:** Disorder consensus regions, curated disorder annotations, length, organism

### 5. DisProt (`disprot`)
- **Package:** `proteinbox/api_tools/disprot.py`
- **API:** `https://disprot.org/api/search?query={acc}&field=acc`
- **Parameters:** `accession` (string, e.g. "P04637")
- **Returns:** Experimentally validated disordered regions, evidence types, methods

### 6. WikiPathways (`wikipathways`)
- **Package:** `proteinbox/api_tools/wikipathways.py`
- **API:** `https://www.wikipathways.org/json/findPathwaysByText.json`
- **Parameters:** `query` (string, e.g. "TP53")
- **Returns:** Pathway IDs, names, species, revision dates

### 7. cBioPortal (`cbioportal`)
- **Package:** `proteinbox/api_tools/cbioportal.py`
- **API:** `https://www.cbioportal.org/api/`
- **Parameters:** `gene` (string, e.g. "TP53")
- **Returns:** Gene info (entrezGeneId, type), available across 535+ cancer studies

### 8. UniProt Variants (`uniprot_variants`)
- **Package:** `proteinbox/api_tools/uniprot_variants.py`
- **API:** `https://www.ebi.ac.uk/proteins/api/variation/{accession}`
- **Parameters:** `accession` (string, e.g. "P04637")
- **Returns:** Known variants with clinical significance, consequence type, position, descriptions

## Implementation Pattern

All tools follow the existing `ProteinTool` + `@register_tool` pattern:

```python
@register_tool
class NewTool(ProteinTool):
    name: str = "tool_name"
    description: str = "..."
    parameters: dict = { ... }

    def run(self, **kwargs) -> ToolResult:
        # 1. Parse params
        # 2. HTTP request
        # 3. Parse response
        # 4. Return ToolResult(success=True, data={...}, display="...")
```

## Test Harness

After implementation, add all 8 tools to `harness/runnable/tool_tests.json` and verify with `scripts/test-tools.sh`.
