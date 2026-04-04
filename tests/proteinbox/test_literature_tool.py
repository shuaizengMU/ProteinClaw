import respx
import httpx
from proteinbox.api_literature.literature import LiteratureTool

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


PUBMED_SEARCH = {"esearchresult": {"count": "1", "idlist": ["11111"]}}
PUBMED_FETCH = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>11111</PMID>
      <Article>
        <ArticleTitle>Test paper</ArticleTitle>
        <AuthorList><Author><LastName>Smith</LastName><Initials>J</Initials></Author></AuthorList>
        <Journal><Title>Nature</Title><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>
        <Abstract><AbstractText>Test abstract.</AbstractText></Abstract>
        <ELocationID EIdType="doi">10.1038/test</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

S2_RESPONSE = {
    "total": 1,
    "data": [
        {
            "paperId": "s2id1",
            "title": "Test paper",
            "authors": [{"name": "Smith J"}],
            "venue": "Nature",
            "year": 2024,
            "externalIds": {"DOI": "10.1038/test"},
            "abstract": "Test abstract with more detail.",
            "citationCount": 50,
            "url": "https://www.semanticscholar.org/paper/s2id1",
        }
    ],
}


@respx.mock
def test_literature_tool_basic():
    # Mock PubMed
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=PUBMED_SEARCH)
    )
    respx.get(f"{EUTILS}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text=PUBMED_FETCH)
    )
    # Mock Semantic Scholar
    respx.get(S2_URL).mock(
        return_value=httpx.Response(200, json=S2_RESPONSE)
    )

    tool = LiteratureTool()
    result = tool.run(query="test paper", sources=["pubmed", "semantic_scholar"], max_results=5)
    assert result.success is True
    # Same DOI -> should dedup to 1 article
    assert len(result.data["articles"]) == 1
    art = result.data["articles"][0]
    assert set(art["sources"]) == {"pubmed", "semantic_scholar"}
    assert art["citation_count"] == 50


@respx.mock
def test_literature_tool_default_sources():
    # Mock all sources to return empty/error so we test dispatch works
    respx.route().mock(return_value=httpx.Response(200, json={}))
    tool = LiteratureTool()
    result = tool.run(query="nonexistent xyz")
    assert result.success is False or result.data["total_found"] == 0


@respx.mock
def test_literature_tool_source_failure_is_graceful():
    """A failing source should not break the whole search."""
    # PubMed returns valid data
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=PUBMED_SEARCH)
    )
    respx.get(f"{EUTILS}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text=PUBMED_FETCH)
    )
    # Semantic Scholar times out
    respx.get(S2_URL).mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )

    tool = LiteratureTool()
    result = tool.run(query="test", sources=["pubmed", "semantic_scholar"])
    assert result.success is True
    assert len(result.data["articles"]) == 1
    assert "pubmed" in result.data["articles"][0]["sources"]
