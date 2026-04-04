import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class SemanticScholarSource(LiteratureSource):
    name = "semantic_scholar"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,authors,venue,year,externalIds,abstract,citationCount,url",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        data = resp.json().get("data", [])
        articles = []
        for p in data:
            title = p.get("title", "")
            if not title:
                continue

            raw_authors = p.get("authors") or []
            authors = [a["name"] for a in raw_authors if a.get("name")][:5]

            ext = p.get("externalIds") or {}
            doi = ext.get("DOI") or None

            abstract = p.get("abstract") or None
            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {"s2id": p.get("paperId", "")}
            if doi:
                identifiers["doi"] = doi
            if ext.get("PubMed"):
                identifiers["pmid"] = ext["PubMed"]
            if ext.get("ArXiv"):
                identifiers["arxiv_id"] = ext["ArXiv"]

            year = p.get("year")

            articles.append(Article(
                title=title,
                authors=authors,
                journal=p.get("venue") or None,
                year=str(year) if year else None,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=p.get("citationCount"),
                sources=["semantic_scholar"],
                url=p.get("url") or None,
            ))
        return articles
