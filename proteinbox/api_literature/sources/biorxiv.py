from datetime import date, timedelta

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class BioRxivSource(LiteratureSource):
    name = "biorxiv"

    def search(self, query: str, max_results: int) -> list[Article]:
        # bioRxiv content API uses date ranges; search last 2 years
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=730)).isoformat()

        try:
            resp = httpx.get(
                f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/0/{max_results}",
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        collection = resp.json().get("collection", [])

        # Client-side filter by query terms
        query_terms = query.lower().split()
        articles = []
        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            text = (title + " " + abstract).lower()
            if not all(term in text for term in query_terms):
                continue

            doi = item.get("biorxiv_doi") or None
            date_str = item.get("date", "")
            year = date_str[:4] if date_str else None

            author_str = item.get("authors", "")
            authors = [a.strip() for a in author_str.split(";")][:5] if author_str else []

            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors,
                journal="bioRxiv",
                year=year,
                doi=doi,
                abstract=abstract or None,
                identifiers=identifiers,
                sources=["biorxiv"],
                url=f"https://doi.org/{doi}" if doi else None,
            ))
        return articles
