from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from proteinbox.api_literature.models import Article
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool
from proteinbox.api_literature.sources import SOURCE_MAP


def _normalize_title(title: str) -> str:
    """Lowercase and strip punctuation for fuzzy title matching."""
    return re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()


def _merge_article(existing: Article, new: Article) -> None:
    """Merge new article data into existing article in place."""
    for src in new.sources:
        if src not in existing.sources:
            existing.sources.append(src)

    if new.citation_count is not None:
        if existing.citation_count is None or new.citation_count > existing.citation_count:
            existing.citation_count = new.citation_count

    if new.abstract and (not existing.abstract or len(new.abstract) > len(existing.abstract)):
        existing.abstract = new.abstract

    for k, v in new.identifiers.items():
        if k not in existing.identifiers:
            existing.identifiers[k] = v

    if not existing.journal and new.journal:
        existing.journal = new.journal
    if not existing.year and new.year:
        existing.year = new.year
    if not existing.url and new.url:
        existing.url = new.url
    if not existing.authors and new.authors:
        existing.authors = new.authors
    if not existing.doi and new.doi:
        existing.doi = new.doi


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    """Deduplicate articles by DOI then by normalized title+year. Returns sorted by citation count desc."""
    doi_map: dict[str, Article] = {}
    title_map: dict[str, Article] = {}
    unique: list[Article] = []

    for art in articles:
        merged = False

        # Try DOI match
        if art.doi:
            key = art.doi.lower().strip()
            if key in doi_map:
                _merge_article(doi_map[key], art)
                merged = True
            else:
                doi_map[key] = art

        # Try title+year match (only if no DOI match)
        if not merged and art.year:
            tkey = _normalize_title(art.title) + "|" + art.year
            if tkey in title_map:
                _merge_article(title_map[tkey], art)
                merged = True
            else:
                title_map[tkey] = art

        if not merged:
            unique.append(art)

    # Sort: citation_count desc, None goes last
    unique.sort(key=lambda a: (a.citation_count is None, -(a.citation_count or 0)))
    return unique


ALL_SOURCE_NAMES = ["pubmed", "europmc", "semantic_scholar", "crossref", "biorxiv", "arxiv"]


@register_tool
class LiteratureTool(ProteinTool):
    name: str = "literature"
    description: str = (
        "Search multiple literature databases for protein-related publications. "
        "Queries PubMed, Europe PMC, Semantic Scholar, CrossRef, bioRxiv, and arXiv in parallel, "
        "deduplicates by DOI, and returns merged results with citation counts. "
        "Useful for comprehensive literature review on proteins, pathways, and biological processes."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'p53 apoptosis' or 'BRCA1 DNA repair'",
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ALL_SOURCE_NAMES,
                },
                "description": "Data sources to search (default: all)",
            },
            "max_results": {
                "type": "integer",
                "description": "Max articles per source (default: 5)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        max_results = int(kwargs.get("max_results", 5))
        requested = kwargs.get("sources") or ALL_SOURCE_NAMES

        sources = [SOURCE_MAP[name] for name in requested if name in SOURCE_MAP]
        if not sources:
            return ToolResult(success=False, error=f"No valid sources in {requested}")

        all_articles: list[Article] = []

        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            futures = {pool.submit(src.search, query, max_results): src.name for src in sources}
            for future in as_completed(futures, timeout=60):
                try:
                    articles = future.result(timeout=35)
                    all_articles.extend(articles)
                except Exception:
                    pass  # source failure is graceful

        if not all_articles:
            return ToolResult(
                success=False,
                error=f"No literature results for '{query}'",
                data={"query": query, "total_found": 0, "articles": []},
            )

        merged = deduplicate_articles(all_articles)
        articles_dicts = [asdict(a) for a in merged]

        display = f"Literature: {len(articles_dicts)} articles for '{query}' (from {', '.join(requested)})"
        return ToolResult(
            success=True,
            data={"query": query, "total_found": len(articles_dicts), "articles": articles_dicts},
            display=display,
        )
