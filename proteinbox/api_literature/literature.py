from __future__ import annotations

import re

from proteinbox.api_literature.models import Article


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
