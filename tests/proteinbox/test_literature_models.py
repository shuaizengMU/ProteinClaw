from proteinbox.api_literature.models import Article, LiteratureSource
from proteinbox.api_literature.literature import deduplicate_articles


def test_article_creation():
    art = Article(
        title="p53 and apoptosis",
        authors=["Smith J", "Lee K"],
        journal="Nature",
        year="2023",
        doi="10.1038/s41586-023-00001-1",
        abstract="A study on p53.",
        identifiers={"pmid": "12345", "doi": "10.1038/s41586-023-00001-1"},
        citation_count=42,
        sources=["pubmed"],
        url="https://pubmed.ncbi.nlm.nih.gov/12345",
    )
    assert art.title == "p53 and apoptosis"
    assert art.citation_count == 42
    assert len(art.authors) == 2


def test_article_defaults():
    art = Article(title="Minimal", sources=["crossref"])
    assert art.authors == []
    assert art.citation_count is None
    assert art.doi is None
    assert art.abstract is None


def test_literature_source_is_abstract():
    class DummySource(LiteratureSource):
        name = "dummy"

        def search(self, query: str, max_results: int) -> list[Article]:
            return []

    src = DummySource()
    assert src.name == "dummy"
    assert src.search("test", 5) == []


def test_dedup_by_doi():
    a1 = Article(
        title="Paper A",
        doi="10.1000/abc",
        sources=["pubmed"],
        citation_count=10,
        abstract="Short.",
        identifiers={"pmid": "111"},
    )
    a2 = Article(
        title="Paper A (variant title)",
        doi="10.1000/ABC",  # same DOI, different case
        sources=["semantic_scholar"],
        citation_count=20,
        abstract="Longer abstract text here.",
        identifiers={"s2id": "222"},
    )
    result = deduplicate_articles([a1, a2])
    assert len(result) == 1
    art = result[0]
    assert set(art.sources) == {"pubmed", "semantic_scholar"}
    assert art.citation_count == 20  # max
    assert art.abstract == "Longer abstract text here."  # longest
    assert art.identifiers["pmid"] == "111"
    assert art.identifiers["s2id"] == "222"


def test_dedup_by_title_year():
    a1 = Article(
        title="A Study on BRCA1!",
        year="2024",
        sources=["europmc"],
        citation_count=5,
    )
    a2 = Article(
        title="a study on brca1",  # same after normalization
        year="2024",
        sources=["crossref"],
        citation_count=8,
    )
    result = deduplicate_articles([a1, a2])
    assert len(result) == 1
    assert set(result[0].sources) == {"europmc", "crossref"}
    assert result[0].citation_count == 8


def test_dedup_no_match():
    a1 = Article(title="Paper X", doi="10.1/x", sources=["pubmed"])
    a2 = Article(title="Paper Y", doi="10.1/y", sources=["arxiv"])
    result = deduplicate_articles([a1, a2])
    assert len(result) == 2


def test_dedup_sort_by_citations():
    a1 = Article(title="Low", doi="10.1/low", sources=["pubmed"], citation_count=2)
    a2 = Article(title="High", doi="10.1/high", sources=["pubmed"], citation_count=50)
    a3 = Article(title="None", doi="10.1/none", sources=["pubmed"])
    result = deduplicate_articles([a1, a2, a3])
    assert result[0].citation_count == 50
    assert result[1].citation_count == 2
    assert result[2].citation_count is None
