import respx
import httpx
from proteinbox.api_literature.sources.pubmed import PubMedSource

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

MOCK_SEARCH = {
    "esearchresult": {"count": "1", "idlist": ["12345678"]},
}

MOCK_FETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>p53 and apoptosis</ArticleTitle>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Nature</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <Abstract><AbstractText>A review of p53.</AbstractText></Abstract>
        <ELocationID EIdType="doi">10.1038/test</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


@respx.mock
def test_pubmed_source():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=MOCK_SEARCH)
    )
    respx.get(f"{EUTILS}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text=MOCK_FETCH_XML)
    )
    src = PubMedSource()
    articles = src.search("p53 apoptosis", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "p53 and apoptosis"
    assert art.identifiers["pmid"] == "12345678"
    assert art.year == "2023"
    assert "pubmed" in art.sources


@respx.mock
def test_pubmed_source_no_results():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    src = PubMedSource()
    assert src.search("xyznonexistent", 5) == []


from proteinbox.api_literature.sources.europmc import EuroPMCSource

EUROPMC_RESPONSE = {
    "resultList": {
        "result": [
            {
                "id": "12345678",
                "title": "Protein folding review",
                "authorString": "Smith J, Lee K, Wang L",
                "journalTitle": "Cell",
                "pubYear": "2024",
                "doi": "10.1016/j.cell.2024.01.001",
                "abstractText": "A comprehensive review.",
                "pmid": "12345678",
                "pmcid": "PMC9999999",
                "citedByCount": 15,
                "source": "MED",
            }
        ]
    }
}


@respx.mock
def test_europmc_source():
    respx.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search").mock(
        return_value=httpx.Response(200, json=EUROPMC_RESPONSE)
    )
    src = EuroPMCSource()
    articles = src.search("protein folding", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "Protein folding review"
    assert art.doi == "10.1016/j.cell.2024.01.001"
    assert art.identifiers["pmcid"] == "PMC9999999"
    assert art.citation_count == 15
    assert "europmc" in art.sources


from proteinbox.api_literature.sources.semantic_scholar import SemanticScholarSource

S2_RESPONSE = {
    "total": 1,
    "data": [
        {
            "paperId": "abc123",
            "title": "Deep learning for proteins",
            "authors": [{"name": "Smith J"}, {"name": "Lee K"}],
            "venue": "NeurIPS",
            "year": 2024,
            "externalIds": {"DOI": "10.5555/test", "PubMed": "99999", "ArXiv": "2401.00001"},
            "abstract": "We present a deep learning approach.",
            "citationCount": 100,
            "url": "https://www.semanticscholar.org/paper/abc123",
        }
    ],
}


@respx.mock
def test_semantic_scholar_source():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=S2_RESPONSE)
    )
    src = SemanticScholarSource()
    articles = src.search("deep learning proteins", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "Deep learning for proteins"
    assert art.citation_count == 100
    assert art.identifiers["s2id"] == "abc123"
    assert art.identifiers["arxiv_id"] == "2401.00001"
    assert "semantic_scholar" in art.sources
