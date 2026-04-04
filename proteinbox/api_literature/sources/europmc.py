import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class EuroPMCSource(LiteratureSource):
    name = "europmc"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={
                    "query": query,
                    "resultType": "core",
                    "pageSize": max_results,
                    "format": "json",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        results = resp.json().get("resultList", {}).get("result", [])
        articles = []
        for r in results:
            title = r.get("title", "")
            if not title:
                continue

            author_str = r.get("authorString", "")
            authors = [a.strip() for a in author_str.split(",")][:5] if author_str else []

            doi = r.get("doi") or None
            abstract = r.get("abstractText") or None
            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if r.get("pmid"):
                identifiers["pmid"] = r["pmid"]
            if r.get("pmcid"):
                identifiers["pmcid"] = r["pmcid"]
            if doi:
                identifiers["doi"] = doi

            pmid = r.get("pmid", "")
            url = f"https://europepmc.org/article/MED/{pmid}" if pmid else ""

            articles.append(Article(
                title=title,
                authors=authors,
                journal=r.get("journalTitle") or None,
                year=r.get("pubYear") or None,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=r.get("citedByCount"),
                sources=["europmc"],
                url=url or None,
            ))
        return articles
