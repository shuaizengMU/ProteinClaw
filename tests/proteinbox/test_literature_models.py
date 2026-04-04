from proteinbox.api_literature.models import Article, LiteratureSource


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
