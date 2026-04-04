import httpx
import xml.etree.ElementTree as ET
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@register_tool
class PubMedTool(ProteinTool):
    name: str = "pubmed"
    description: str = (
        "Search PubMed for biomedical literature. Returns article titles, authors, "
        "journal, year, and abstract snippets. Useful for finding papers about "
        "specific proteins, pathways, or biological processes."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'p53 apoptosis' or 'BRCA1 DNA repair'",
            },
            "max_results": {
                "type": "integer",
                "description": "Max articles to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        max_results = int(kwargs.get("max_results", 5))

        # Step 1: esearch to get PMIDs
        search_url = f"{EUTILS_BASE}/esearch.fcgi"
        try:
            resp = httpx.get(
                search_url,
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                },
                timeout=30,
            )
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"PubMed search failed: {e}")

        if resp.status_code != 200:
            return ToolResult(success=False, error=f"PubMed returned {resp.status_code}")

        search_data = resp.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return ToolResult(success=False, error=f"No PubMed results for '{query}'")

        # Step 2: efetch to get article details
        fetch_url = f"{EUTILS_BASE}/efetch.fcgi"
        try:
            resp = httpx.get(
                fetch_url,
                params={
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "xml",
                },
                timeout=30,
            )
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"PubMed fetch failed: {e}")

        if resp.status_code != 200:
            return ToolResult(success=False, error=f"PubMed fetch returned {resp.status_code}")

        articles = self._parse_articles(resp.text)

        data = {
            "query": query,
            "total_found": int(
                search_data.get("esearchresult", {}).get("count", 0)
            ),
            "articles": articles,
        }
        display = f"PubMed: {len(articles)} articles for '{query}'"
        return ToolResult(success=True, data=data, display=display)

    def _parse_articles(self, xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        articles = []
        for article_el in root.iter("PubmedArticle"):
            medline = article_el.find(".//MedlineCitation")
            if medline is None:
                continue
            pmid = medline.findtext("PMID", "")
            art = medline.find("Article")
            if art is None:
                continue
            title = art.findtext("ArticleTitle", "")
            journal = art.findtext(".//Journal/Title", "")
            year = art.findtext(".//Journal/JournalIssue/PubDate/Year", "")
            abstract = art.findtext(".//Abstract/AbstractText", "")
            authors = []
            author_list = art.find("AuthorList")
            for au in (author_list if author_list is not None else []):
                last = au.findtext("LastName", "")
                init = au.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {init}".strip())
            articles.append({
                "pmid": pmid,
                "title": title,
                "authors": authors[:5],  # cap for context
                "journal": journal,
                "year": year,
                "abstract": (abstract[:500] + "...") if abstract and len(abstract) > 500 else abstract,
            })
        return articles
