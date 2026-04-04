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


from proteinbox.api_literature.sources.crossref import CrossRefSource

CROSSREF_RESPONSE = {
    "status": "ok",
    "message": {
        "items": [
            {
                "DOI": "10.1234/test",
                "title": ["Protein structure prediction"],
                "author": [
                    {"given": "John", "family": "Smith"},
                    {"given": "Jane", "family": "Doe"},
                ],
                "container-title": ["Science"],
                "published-print": {"date-parts": [[2024]]},
                "abstract": "<p>An abstract about proteins.</p>",
                "is-referenced-by-count": 35,
                "URL": "https://doi.org/10.1234/test",
            }
        ]
    },
}


@respx.mock
def test_crossref_source():
    respx.get("https://api.crossref.org/works").mock(
        return_value=httpx.Response(200, json=CROSSREF_RESPONSE)
    )
    src = CrossRefSource()
    articles = src.search("protein structure", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "Protein structure prediction"
    assert art.doi == "10.1234/test"
    assert art.citation_count == 35
    assert art.authors == ["Smith J", "Doe J"]
    assert "crossref" in art.sources


from proteinbox.api_literature.sources.biorxiv import BioRxivSource

BIORXIV_RESPONSE = {
    "collection": [
        {
            "biorxiv_doi": "10.1101/2024.01.01.000001",
            "title": "Novel protein folding method",
            "authors": "Smith, J.; Lee, K.",
            "category": "bioinformatics",
            "date": "2024-01-15",
            "abstract": "We introduce a new method.",
        }
    ]
}


@respx.mock
def test_biorxiv_source():
    respx.get(url__startswith="https://api.biorxiv.org/details/biorxiv").mock(
        return_value=httpx.Response(200, json=BIORXIV_RESPONSE)
    )
    src = BioRxivSource()
    articles = src.search("protein folding", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "Novel protein folding method"
    assert art.doi == "10.1101/2024.01.01.000001"
    assert art.year == "2024"
    assert "biorxiv" in art.sources


from proteinbox.api_literature.sources.arxiv import ArxivSource

ARXIV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>AlphaFold advances</title>
    <summary>New developments in protein structure prediction.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Smith J</name></author>
    <author><name>Lee K</name></author>
    <arxiv:doi>10.1234/arxiv.test</arxiv:doi>
  </entry>
</feed>"""


@respx.mock
def test_arxiv_source():
    respx.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=ARXIV_RESPONSE)
    )
    src = ArxivSource()
    articles = src.search("alphafold protein", max_results=5)
    assert len(articles) == 1
    art = articles[0]
    assert art.title == "AlphaFold advances"
    assert art.identifiers["arxiv_id"] == "2401.00001"
    assert art.year == "2024"
    assert "arxiv" in art.sources
