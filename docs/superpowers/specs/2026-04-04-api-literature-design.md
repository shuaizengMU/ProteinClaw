# api_literature - Aggregated Protein Literature Search Tool

## Overview

A unified literature search tool that queries 6 data sources in parallel, deduplicates by DOI, and returns merged results. Registered as a single `literature` tool via `@register_tool`.

## Tool Interface

**Name:** `literature`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | yes | - | Search query, e.g. "p53 apoptosis" |
| `sources` | array of string | no | all 6 | Which sources to search. Enum: `pubmed`, `europmc`, `semantic_scholar`, `crossref`, `biorxiv`, `arxiv` |
| `max_results` | integer | no | 5 | Max articles per source before dedup |

**Return structure:**

```json
{
    "query": "p53 apoptosis",
    "total_found": 12,
    "articles": [
        {
            "title": "...",
            "authors": ["Smith J", "Lee K"],
            "journal": "Nature",
            "year": "2024",
            "doi": "10.1038/...",
            "abstract": "...",
            "identifiers": {"pmid": "123", "pmc": "PMC456", "doi": "...", "arxiv_id": "..."},
            "citation_count": 42,
            "sources": ["pubmed", "semantic_scholar"],
            "url": "https://..."
        }
    ]
}
```

- `authors`: capped at 5
- `abstract`: truncated to 500 characters
- `citation_count`: from Semantic Scholar or CrossRef (whichever is higher)
- `sources`: list of databases where this article was found

## Data Sources

| Source | API Endpoint | Auth | Notes |
|--------|-------------|------|-------|
| PubMed | NCBI E-utilities (`eutils.ncbi.nlm.nih.gov`) | None (optional API key) | Reuse logic from existing pubmed.py |
| Europe PMC | `europepmc.org/rest/search` | None | REST JSON, full-text search, preprints |
| Semantic Scholar | `api.semanticscholar.org/graph/v1` | None (optional API key) | Citation counts, influential citations |
| CrossRef | `api.crossref.org/works` | None | DOI metadata, citation counts, polite pool (mailto) |
| bioRxiv | `api.biorxiv.org/details/biorxiv` | None | Preprints, date-range queries |
| arXiv | `export.arxiv.org/api/query` | None | Atom XML, filter with `cat:q-bio.*` |

All APIs are free and require no authentication.

## Architecture

### Directory Structure

```
proteinbox/api_literature/
├── __init__.py              # Empty, triggers discover_tools scan
├── literature.py            # LiteratureTool (@register_tool), dispatch + dedup
├── models.py                # Article dataclass, LiteratureSource base class
├── sources/
│   ├── __init__.py          # Exports list of all source classes
│   ├── pubmed.py
│   ├── europmc.py
│   ├── semantic_scholar.py
│   ├── crossref.py
│   ├── biorxiv.py
│   └── arxiv.py
```

### Source Interface

Each source implements a unified base class:

```python
class LiteratureSource:
    name: str

    def search(self, query: str, max_results: int) -> list[Article]
```

`Article` is a dataclass in `models.py` with all the fields from the return structure. Each source maps its API response to `Article`.

### Concurrency

Sources are queried in parallel using `concurrent.futures.ThreadPoolExecutor`. Each source has a 30-second timeout; a failing source does not block others. Failed sources are silently omitted from results.

### Deduplication & Merge

**Primary key:** DOI (lowercased, normalized)

**Fuzzy match for DOI-less articles:** title (lowercased, stripped of punctuation) + year must match exactly.

**Merge rules when the same article appears from multiple sources:**
- `sources`: accumulate all matching databases
- `citation_count`: take the maximum value
- `abstract`: take the longest version
- `identifiers`: merge (pmid from PubMed, arxiv_id from arXiv, etc.)
- Other fields: take the first non-empty value

**Sort order:** by `citation_count` descending. Articles without citation counts go to the end.

### Registry Integration

Modify `proteinbox/tools/registry.py` `discover_tools()` to add:

```python
try:
    import proteinbox.api_literature as lit_pkg
    for _, module_name, _ in pkgutil.iter_modules(lit_pkg.__path__):
        importlib.import_module(f"proteinbox.api_literature.{module_name}")
except ImportError:
    pass
```

### Relationship with Existing pubmed.py

`proteinbox/tools/pubmed.py` remains unchanged. `api_literature/sources/pubmed.py` is an independent implementation that reuses the same E-utilities API but returns `Article` instead of `ToolResult`. Both tools coexist: `pubmed` for quick single-source queries, `literature` for aggregated search.
