import respx
import httpx
from proteinbox.tools.pubmed import PubMedTool, EUTILS_BASE

MOCK_SEARCH = {
    "esearchresult": {
        "count": "42",
        "idlist": ["12345678"],
    }
}

MOCK_FETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>p53 and apoptosis: a review</ArticleTitle>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Nature Reviews Cancer</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <Abstract><AbstractText>This review covers p53-mediated apoptosis pathways.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


@respx.mock
def test_pubmed_success():
    respx.get(f"{EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=MOCK_SEARCH)
    )
    respx.get(f"{EUTILS_BASE}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text=MOCK_FETCH_XML)
    )
    result = PubMedTool().run(query="p53 apoptosis")
    assert result.success is True
    assert result.data["total_found"] == 42
    assert len(result.data["articles"]) == 1
    art = result.data["articles"][0]
    assert art["pmid"] == "12345678"
    assert "p53" in art["title"]
    assert art["year"] == "2023"


@respx.mock
def test_pubmed_no_results():
    respx.get(f"{EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    result = PubMedTool().run(query="xyznonexistent")
    assert result.success is False
