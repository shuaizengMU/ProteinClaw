# GWAS Catalog & Protein Atlas Bug Fix — Design Spec

## Summary

Fix two data-accuracy bugs introduced in recent edits to `gwas_catalog.py` and `protein_atlas.py`.

---

## Bug 1: GWAS Catalog — Wrong Endpoint

**File:** `proteinbox/api_tools/gwas_catalog.py:30-32`

**Problem:** The endpoint was changed from the named Spring Data REST query route to the bare collection endpoint. The collection endpoint ignores the `gene` query parameter and returns unfiltered associations, so every gene query returns the same default page of results.

**Fix:** Revert the URL and parameter name:
- URL: `https://www.ebi.ac.uk/gwas/rest/api/associations/search/findByGene`
- Param: `geneName=<gene>` (was incorrectly changed to `gene=<gene>`)

No other logic changes needed.

---

## Bug 2: Protein Atlas — Narrow `columns` Filter Drops Parsed Fields

**File:** `proteinbox/api_tools/protein_atlas.py:34-35`

**Problem:** The `search_download.php` call specifies `columns=g,eg,up,scl,pc,t_RNA_specificity,t_RNA_distribution`. The parser reads additional fields (`Gene description`, `Protein class`, `Subcellular location`, `Tissue expression cluster`, `RNA cancer specificity`, `Prognostic - favorable`) that are absent from the filter, so they silently return as empty strings/lists.

**Fix (Option A):** Remove the `columns` parameter entirely. The API returns all fields by default; no columns filter means the parser receives every field it reads. The response is slightly larger but the gene-match logic added in the same change is preserved.

---

## Verification

After applying both fixes, run the harness against the two affected tools:

```bash
scripts/test-tools.sh gwas_catalog protein_atlas
```

Both should pass and return non-empty field values (traits for GWAS; localization/class for Protein Atlas).
