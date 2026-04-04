import re
import xml.etree.ElementTree as ET

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivSource(LiteratureSource):
    name = "arxiv"

    def search(self, query: str, max_results: int) -> list[Article]:
        search_query = f"all:{query} AND cat:q-bio.*"
        try:
            resp = httpx.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": search_query, "start": 0, "max_results": max_results},
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        return self._parse(resp.text)

    def _parse(self, xml_text: str) -> list[Article]:
        root = ET.fromstring(xml_text)
        articles = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title = entry.findtext(f"{{{ATOM_NS}}}title", "").strip()
            if not title:
                continue

            raw_id = entry.findtext(f"{{{ATOM_NS}}}id", "")
            match = re.search(r"abs/(\d+\.\d+)", raw_id)
            arxiv_id = match.group(1) if match else ""

            summary = entry.findtext(f"{{{ATOM_NS}}}summary", "").strip()
            if summary and len(summary) > 500:
                summary = summary[:500] + "..."

            published = entry.findtext(f"{{{ATOM_NS}}}published", "")
            year = published[:4] if published else None

            authors = []
            for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
                name = author_el.findtext(f"{{{ATOM_NS}}}name", "")
                if name:
                    authors.append(name)

            doi = entry.findtext(f"{{{ARXIV_NS}}}doi", "")

            identifiers: dict[str, str] = {}
            if arxiv_id:
                identifiers["arxiv_id"] = arxiv_id
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors[:5],
                journal="arXiv",
                year=year,
                doi=doi or None,
                abstract=summary or None,
                identifiers=identifiers,
                sources=["arxiv"],
                url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
            ))
        return articles
