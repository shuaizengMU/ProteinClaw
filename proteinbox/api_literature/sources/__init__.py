from proteinbox.api_literature.sources.pubmed import PubMedSource
from proteinbox.api_literature.sources.europmc import EuroPMCSource
from proteinbox.api_literature.sources.semantic_scholar import SemanticScholarSource
from proteinbox.api_literature.sources.crossref import CrossRefSource
from proteinbox.api_literature.sources.biorxiv import BioRxivSource
from proteinbox.api_literature.sources.arxiv import ArxivSource

ALL_SOURCES = [
    PubMedSource(),
    EuroPMCSource(),
    SemanticScholarSource(),
    CrossRefSource(),
    BioRxivSource(),
    ArxivSource(),
]

SOURCE_MAP = {s.name: s for s in ALL_SOURCES}
