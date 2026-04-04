import re

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class CrossRefSource(LiteratureSource):
    name = "crossref"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://api.crossref.org/works",
                params={
                    "query": query,
                    "rows": max_results,
                    "sort": "relevance",
                    "mailto": "proteinclaw@example.com",
                },
                headers={"User-Agent": "ProteinClaw/1.0 (mailto:proteinclaw@example.com)"},
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        items = resp.json().get("message", {}).get("items", [])
        articles = []
        for item in items:
            titles = item.get("title", [])
            title = titles[0] if titles else ""
            if not title:
                continue

            raw_authors = item.get("author", [])
            authors = []
            for a in raw_authors[:5]:
                family = a.get("family", "")
                given = a.get("given", "")
                initial = given[0] if given else ""
                if family:
                    authors.append(f"{family} {initial}".strip())

            doi = item.get("DOI") or None
            container = item.get("container-title", [])
            journal = container[0] if container else None

            date_parts = item.get("published-print", {}).get("date-parts", [[]])
            if not date_parts or not date_parts[0]:
                date_parts = item.get("published-online", {}).get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

            abstract = item.get("abstract") or None
            if abstract:
                abstract = re.sub(r"<[^>]+>", "", abstract)  # strip HTML tags
                if len(abstract) > 500:
                    abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=item.get("is-referenced-by-count"),
                sources=["crossref"],
                url=item.get("URL") or None,
            ))
        return articles
