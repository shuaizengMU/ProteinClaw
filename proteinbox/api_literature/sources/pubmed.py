import xml.etree.ElementTree as ET

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedSource(LiteratureSource):
    name = "pubmed"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                f"{EUTILS_BASE}/esearch.fcgi",
                params={"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json", "sort": "relevance"},
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        id_list = resp.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        try:
            resp = httpx.get(
                f"{EUTILS_BASE}/efetch.fcgi",
                params={"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"},
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        return self._parse(resp.text)

    def _parse(self, xml_text: str) -> list[Article]:
        root = ET.fromstring(xml_text)
        articles = []
        for pub in root.iter("PubmedArticle"):
            med = pub.find(".//MedlineCitation")
            if med is None:
                continue
            pmid = med.findtext("PMID", "")
            art_el = med.find("Article")
            if art_el is None:
                continue

            title = art_el.findtext("ArticleTitle", "")
            journal = art_el.findtext(".//Journal/Title", "")
            year = art_el.findtext(".//Journal/JournalIssue/PubDate/Year", "")
            abstract_text = art_el.findtext(".//Abstract/AbstractText", "")
            if abstract_text and len(abstract_text) > 500:
                abstract_text = abstract_text[:500] + "..."

            doi = ""
            for eloc in art_el.findall("ELocationID"):
                if eloc.get("EIdType") == "doi":
                    doi = eloc.text or ""
                    break

            authors = []
            author_list = art_el.find("AuthorList")
            for au in (author_list if author_list is not None else []):
                last = au.findtext("LastName", "")
                init = au.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {init}".strip())

            identifiers = {"pmid": pmid}
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors[:5],
                journal=journal,
                year=year,
                doi=doi or None,
                abstract=abstract_text or None,
                identifiers=identifiers,
                sources=["pubmed"],
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
            ))
        return articles
