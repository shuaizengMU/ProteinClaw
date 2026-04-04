# api_literature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an aggregated literature search tool that queries 6 data sources (PubMed, Europe PMC, Semantic Scholar, CrossRef, bioRxiv, arXiv) in parallel, deduplicates by DOI, and returns merged results.

**Architecture:** Single registered tool `literature` dispatches searches to independent source modules via `concurrent.futures.ThreadPoolExecutor`. Results are merged/deduped in `literature.py`. Each source is a separate file implementing a common `LiteratureSource` interface.

**Tech Stack:** Python, httpx, pydantic, respx (testing), concurrent.futures

**Spec:** `docs/superpowers/specs/2026-04-04-api-literature-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `proteinbox/api_literature/__init__.py` | Create | Empty package init |
| `proteinbox/api_literature/models.py` | Create | `Article` dataclass, `LiteratureSource` base class |
| `proteinbox/api_literature/literature.py` | Create | `LiteratureTool` (`@register_tool`), dispatch, dedup, merge |
| `proteinbox/api_literature/sources/__init__.py` | Create | Export `ALL_SOURCES` list |
| `proteinbox/api_literature/sources/pubmed.py` | Create | PubMed E-utilities source |
| `proteinbox/api_literature/sources/europmc.py` | Create | Europe PMC REST source |
| `proteinbox/api_literature/sources/semantic_scholar.py` | Create | Semantic Scholar API source |
| `proteinbox/api_literature/sources/crossref.py` | Create | CrossRef API source |
| `proteinbox/api_literature/sources/biorxiv.py` | Create | bioRxiv API source |
| `proteinbox/api_literature/sources/arxiv.py` | Create | arXiv Atom API source |
| `proteinbox/tools/registry.py` | Modify | Add `api_literature` to `discover_tools()` |
| `tests/proteinbox/test_literature_models.py` | Create | Tests for Article and dedup logic |
| `tests/proteinbox/test_literature_sources.py` | Create | Tests for each source (mocked) |
| `tests/proteinbox/test_literature_tool.py` | Create | Integration tests for LiteratureTool |

---

### Task 1: Models — Article dataclass and LiteratureSource base

**Files:**
- Create: `proteinbox/api_literature/__init__.py`
- Create: `proteinbox/api_literature/models.py`
- Create: `proteinbox/api_literature/sources/__init__.py`
- Test: `tests/proteinbox/test_literature_models.py`

- [ ] **Step 1: Create package structure**

```bash
mkdir -p proteinbox/api_literature/sources
```

- [ ] **Step 2: Create empty `__init__.py` files**

`proteinbox/api_literature/__init__.py`:
```python
```

`proteinbox/api_literature/sources/__init__.py` (will be updated in later tasks):
```python
ALL_SOURCES: list = []
```

- [ ] **Step 3: Write failing test for Article**

`tests/proteinbox/test_literature_models.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'proteinbox.api_literature.models'`

- [ ] **Step 5: Implement models.py**

`proteinbox/api_literature/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class Article:
    title: str
    sources: list[str]
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    year: str | None = None
    doi: str | None = None
    abstract: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    citation_count: int | None = None
    url: str | None = None


class LiteratureSource(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, max_results: int) -> list[Article]:
        ...
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_models.py -v
```
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add proteinbox/api_literature/__init__.py proteinbox/api_literature/models.py proteinbox/api_literature/sources/__init__.py tests/proteinbox/test_literature_models.py
git commit -m "feat(literature): add Article dataclass and LiteratureSource base"
```

---

### Task 2: Dedup & merge logic

**Files:**
- Modify: `proteinbox/api_literature/literature.py` (create)
- Test: `tests/proteinbox/test_literature_models.py` (append)

- [ ] **Step 1: Write failing tests for dedup/merge**

Append to `tests/proteinbox/test_literature_models.py`:
```python
from proteinbox.api_literature.literature import deduplicate_articles


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_models.py::test_dedup_by_doi -v
```
Expected: FAIL — `ImportError: cannot import name 'deduplicate_articles'`

- [ ] **Step 3: Implement deduplicate_articles in literature.py**

`proteinbox/api_literature/literature.py` (initial version, tool class added in Task 9):
```python
from __future__ import annotations

import re

from proteinbox.api_literature.models import Article


def _normalize_title(title: str) -> str:
    """Lowercase and strip punctuation for fuzzy title matching."""
    return re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()


def _merge_article(existing: Article, new: Article) -> None:
    """Merge new article data into existing article in place."""
    for src in new.sources:
        if src not in existing.sources:
            existing.sources.append(src)

    if new.citation_count is not None:
        if existing.citation_count is None or new.citation_count > existing.citation_count:
            existing.citation_count = new.citation_count

    if new.abstract and (not existing.abstract or len(new.abstract) > len(existing.abstract)):
        existing.abstract = new.abstract

    for k, v in new.identifiers.items():
        if k not in existing.identifiers:
            existing.identifiers[k] = v

    if not existing.journal and new.journal:
        existing.journal = new.journal
    if not existing.year and new.year:
        existing.year = new.year
    if not existing.url and new.url:
        existing.url = new.url
    if not existing.authors and new.authors:
        existing.authors = new.authors
    if not existing.doi and new.doi:
        existing.doi = new.doi


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    """Deduplicate articles by DOI then by normalized title+year. Returns sorted by citation count desc."""
    doi_map: dict[str, Article] = {}
    title_map: dict[str, Article] = {}
    unique: list[Article] = []

    for art in articles:
        merged = False

        # Try DOI match
        if art.doi:
            key = art.doi.lower().strip()
            if key in doi_map:
                _merge_article(doi_map[key], art)
                merged = True
            else:
                doi_map[key] = art

        # Try title+year match (only if no DOI match)
        if not merged and art.year:
            tkey = _normalize_title(art.title) + "|" + art.year
            if tkey in title_map:
                _merge_article(title_map[tkey], art)
                merged = True
            else:
                title_map[tkey] = art

        if not merged:
            unique.append(art)

    # Sort: citation_count desc, None goes last
    unique.sort(key=lambda a: (a.citation_count is None, -(a.citation_count or 0)))
    return unique
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/proteinbox/test_literature_models.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/literature.py tests/proteinbox/test_literature_models.py
git commit -m "feat(literature): add dedup and merge logic"
```

---

### Task 3: PubMed source

**Files:**
- Create: `proteinbox/api_literature/sources/pubmed.py`
- Test: `tests/proteinbox/test_literature_sources.py`

- [ ] **Step 1: Write failing test**

`tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_pubmed_source -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement PubMed source**

`proteinbox/api_literature/sources/pubmed.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/pubmed.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add PubMed source"
```

---

### Task 4: Europe PMC source

**Files:**
- Create: `proteinbox/api_literature/sources/europmc.py`
- Test: `tests/proteinbox/test_literature_sources.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_europmc_source -v
```
Expected: FAIL

- [ ] **Step 3: Implement Europe PMC source**

`proteinbox/api_literature/sources/europmc.py`:
```python
import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class EuroPMCSource(LiteratureSource):
    name = "europmc"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={
                    "query": query,
                    "resultType": "core",
                    "pageSize": max_results,
                    "format": "json",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        results = resp.json().get("resultList", {}).get("result", [])
        articles = []
        for r in results:
            title = r.get("title", "")
            if not title:
                continue

            author_str = r.get("authorString", "")
            authors = [a.strip() for a in author_str.split(",")][:5] if author_str else []

            doi = r.get("doi") or None
            abstract = r.get("abstractText") or None
            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if r.get("pmid"):
                identifiers["pmid"] = r["pmid"]
            if r.get("pmcid"):
                identifiers["pmcid"] = r["pmcid"]
            if doi:
                identifiers["doi"] = doi

            pmid = r.get("pmid", "")
            url = f"https://europepmc.org/article/MED/{pmid}" if pmid else ""

            articles.append(Article(
                title=title,
                authors=authors,
                journal=r.get("journalTitle") or None,
                year=r.get("pubYear") or None,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=r.get("citedByCount"),
                sources=["europmc"],
                url=url or None,
            ))
        return articles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/europmc.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add Europe PMC source"
```

---

### Task 5: Semantic Scholar source

**Files:**
- Create: `proteinbox/api_literature/sources/semantic_scholar.py`
- Test: `tests/proteinbox/test_literature_sources.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_semantic_scholar_source -v
```
Expected: FAIL

- [ ] **Step 3: Implement Semantic Scholar source**

`proteinbox/api_literature/sources/semantic_scholar.py`:
```python
import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class SemanticScholarSource(LiteratureSource):
    name = "semantic_scholar"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,authors,venue,year,externalIds,abstract,citationCount,url",
                },
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        data = resp.json().get("data", [])
        articles = []
        for p in data:
            title = p.get("title", "")
            if not title:
                continue

            raw_authors = p.get("authors") or []
            authors = [a["name"] for a in raw_authors if a.get("name")][:5]

            ext = p.get("externalIds") or {}
            doi = ext.get("DOI") or None

            abstract = p.get("abstract") or None
            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {"s2id": p.get("paperId", "")}
            if doi:
                identifiers["doi"] = doi
            if ext.get("PubMed"):
                identifiers["pmid"] = ext["PubMed"]
            if ext.get("ArXiv"):
                identifiers["arxiv_id"] = ext["ArXiv"]

            year = p.get("year")

            articles.append(Article(
                title=title,
                authors=authors,
                journal=p.get("venue") or None,
                year=str(year) if year else None,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=p.get("citationCount"),
                sources=["semantic_scholar"],
                url=p.get("url") or None,
            ))
        return articles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/semantic_scholar.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add Semantic Scholar source"
```

---

### Task 6: CrossRef source

**Files:**
- Create: `proteinbox/api_literature/sources/crossref.py`
- Test: `tests/proteinbox/test_literature_sources.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_crossref_source -v
```
Expected: FAIL

- [ ] **Step 3: Implement CrossRef source**

`proteinbox/api_literature/sources/crossref.py`:
```python
import re

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class CrossRefSource(LiteratureSource):
    name = "crossref"

    def search(self, query: str, max_results: int) -> list[Article]:
        try:
            resp = httpx.get(
                "https://api.crossref.org/works",
                params={
                    "query": query,
                    "rows": max_results,
                    "sort": "relevance",
                    "mailto": "proteinclaw@example.com",
                },
                headers={"User-Agent": "ProteinClaw/1.0 (mailto:proteinclaw@example.com)"},
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        items = resp.json().get("message", {}).get("items", [])
        articles = []
        for item in items:
            titles = item.get("title", [])
            title = titles[0] if titles else ""
            if not title:
                continue

            raw_authors = item.get("author", [])
            authors = []
            for a in raw_authors[:5]:
                family = a.get("family", "")
                given = a.get("given", "")
                initial = given[0] if given else ""
                if family:
                    authors.append(f"{family} {initial}".strip())

            doi = item.get("DOI") or None
            container = item.get("container-title", [])
            journal = container[0] if container else None

            date_parts = item.get("published-print", {}).get("date-parts", [[]])
            if not date_parts or not date_parts[0]:
                date_parts = item.get("published-online", {}).get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

            abstract = item.get("abstract") or None
            if abstract:
                abstract = re.sub(r"<[^>]+>", "", abstract)  # strip HTML tags
                if len(abstract) > 500:
                    abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract,
                identifiers=identifiers,
                citation_count=item.get("is-referenced-by-count"),
                sources=["crossref"],
                url=item.get("URL") or None,
            ))
        return articles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/crossref.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add CrossRef source"
```

---

### Task 7: bioRxiv source

**Files:**
- Create: `proteinbox/api_literature/sources/biorxiv.py`
- Test: `tests/proteinbox/test_literature_sources.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_biorxiv_source -v
```
Expected: FAIL

- [ ] **Step 3: Implement bioRxiv source**

`proteinbox/api_literature/sources/biorxiv.py`:
```python
from datetime import date, timedelta

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource


class BioRxivSource(LiteratureSource):
    name = "biorxiv"

    def search(self, query: str, max_results: int) -> list[Article]:
        # bioRxiv content API uses date ranges; search last 2 years
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=730)).isoformat()

        try:
            resp = httpx.get(
                f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/0/{max_results}",
                timeout=30,
            )
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        collection = resp.json().get("collection", [])

        # Client-side filter by query terms
        query_terms = query.lower().split()
        articles = []
        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            text = (title + " " + abstract).lower()
            if not all(term in text for term in query_terms):
                continue

            doi = item.get("biorxiv_doi") or None
            date_str = item.get("date", "")
            year = date_str[:4] if date_str else None

            author_str = item.get("authors", "")
            authors = [a.strip() for a in author_str.split(";")][:5] if author_str else []

            if abstract and len(abstract) > 500:
                abstract = abstract[:500] + "..."

            identifiers: dict[str, str] = {}
            if doi:
                identifiers["doi"] = doi

            articles.append(Article(
                title=title,
                authors=authors,
                journal="bioRxiv",
                year=year,
                doi=doi,
                abstract=abstract or None,
                identifiers=identifiers,
                sources=["biorxiv"],
                url=f"https://doi.org/{doi}" if doi else None,
            ))
        return articles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/biorxiv.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add bioRxiv source"
```

---

### Task 8: arXiv source

**Files:**
- Create: `proteinbox/api_literature/sources/arxiv.py`
- Test: `tests/proteinbox/test_literature_sources.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_sources.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_sources.py::test_arxiv_source -v
```
Expected: FAIL

- [ ] **Step 3: Implement arXiv source**

`proteinbox/api_literature/sources/arxiv.py`:
```python
import re
import xml.etree.ElementTree as ET

import httpx

from proteinbox.api_literature.models import Article, LiteratureSource

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivSource(LiteratureSource):
    name = "arxiv"

    def search(self, query: str, max_results: int) -> list[Article]:
        # Prefix with cat:q-bio.* to focus on biology-related papers
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

            # Extract arXiv ID from the <id> URL
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_sources.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add proteinbox/api_literature/sources/arxiv.py tests/proteinbox/test_literature_sources.py
git commit -m "feat(literature): add arXiv source"
```

---

### Task 9: LiteratureTool — main tool class + registry integration

**Files:**
- Modify: `proteinbox/api_literature/literature.py`
- Modify: `proteinbox/api_literature/sources/__init__.py`
- Modify: `proteinbox/tools/registry.py`
- Test: `tests/proteinbox/test_literature_tool.py`

- [ ] **Step 1: Update sources/__init__.py to export all sources**

`proteinbox/api_literature/sources/__init__.py`:
```python
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
```

- [ ] **Step 2: Write failing test for LiteratureTool**

`tests/proteinbox/test_literature_tool.py`:
```python
import respx
import httpx
from proteinbox.api_literature.literature import LiteratureTool


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
    respx.get(url__contains="esearch.fcgi").mock(
        return_value=httpx.Response(200, json=PUBMED_SEARCH)
    )
    respx.get(url__contains="efetch.fcgi").mock(
        return_value=httpx.Response(200, text=PUBMED_FETCH)
    )
    # Mock Semantic Scholar
    respx.get(url__contains="semanticscholar.org").mock(
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
    respx.get(url__contains="esearch.fcgi").mock(
        return_value=httpx.Response(200, json=PUBMED_SEARCH)
    )
    respx.get(url__contains="efetch.fcgi").mock(
        return_value=httpx.Response(200, text=PUBMED_FETCH)
    )
    # Semantic Scholar times out
    respx.get(url__contains="semanticscholar.org").mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )

    tool = LiteratureTool()
    result = tool.run(query="test", sources=["pubmed", "semantic_scholar"])
    assert result.success is True
    assert len(result.data["articles"]) == 1
    assert "pubmed" in result.data["articles"][0]["sources"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_tool.py::test_literature_tool_basic -v
```
Expected: FAIL — `ImportError: cannot import name 'LiteratureTool'`

- [ ] **Step 4: Add LiteratureTool class to literature.py**

Add to the top of `proteinbox/api_literature/literature.py` (after existing imports):
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool
from proteinbox.api_literature.sources import SOURCE_MAP
```

Add at the bottom of `proteinbox/api_literature/literature.py`:
```python
ALL_SOURCE_NAMES = ["pubmed", "europmc", "semantic_scholar", "crossref", "biorxiv", "arxiv"]


@register_tool
class LiteratureTool(ProteinTool):
    name: str = "literature"
    description: str = (
        "Search multiple literature databases for protein-related publications. "
        "Queries PubMed, Europe PMC, Semantic Scholar, CrossRef, bioRxiv, and arXiv in parallel, "
        "deduplicates by DOI, and returns merged results with citation counts. "
        "Useful for comprehensive literature review on proteins, pathways, and biological processes."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'p53 apoptosis' or 'BRCA1 DNA repair'",
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ALL_SOURCE_NAMES,
                },
                "description": "Data sources to search (default: all)",
            },
            "max_results": {
                "type": "integer",
                "description": "Max articles per source (default: 5)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        max_results = int(kwargs.get("max_results", 5))
        requested = kwargs.get("sources") or ALL_SOURCE_NAMES

        sources = [SOURCE_MAP[name] for name in requested if name in SOURCE_MAP]
        if not sources:
            return ToolResult(success=False, error=f"No valid sources in {requested}")

        all_articles: list[Article] = []

        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            futures = {pool.submit(src.search, query, max_results): src.name for src in sources}
            for future in as_completed(futures, timeout=60):
                try:
                    articles = future.result(timeout=35)
                    all_articles.extend(articles)
                except Exception:
                    pass  # source failure is graceful

        if not all_articles:
            return ToolResult(
                success=False,
                error=f"No literature results for '{query}'",
                data={"query": query, "total_found": 0, "articles": []},
            )

        merged = deduplicate_articles(all_articles)
        articles_dicts = [asdict(a) for a in merged]

        display = f"Literature: {len(articles_dicts)} articles for '{query}' (from {', '.join(requested)})"
        return ToolResult(
            success=True,
            data={"query": query, "total_found": len(articles_dicts), "articles": articles_dicts},
            display=display,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/proteinbox/test_literature_tool.py -v
```
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add proteinbox/api_literature/literature.py proteinbox/api_literature/sources/__init__.py tests/proteinbox/test_literature_tool.py
git commit -m "feat(literature): add LiteratureTool with parallel dispatch and dedup"
```

---

### Task 10: Registry integration + final wiring

**Files:**
- Modify: `proteinbox/tools/registry.py:33-49`

- [ ] **Step 1: Write failing test**

Append to `tests/proteinbox/test_literature_tool.py`:
```python
def test_literature_tool_in_registry():
    from proteinbox.tools.registry import discover_tools
    tools = discover_tools()
    assert "literature" in tools
    assert tools["literature"].name == "literature"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/proteinbox/test_literature_tool.py::test_literature_tool_in_registry -v
```
Expected: FAIL — `literature` not in registry because `discover_tools` doesn't scan `api_literature`

- [ ] **Step 3: Modify registry.py**

In `proteinbox/tools/registry.py`, add after the `api_tools` scanning block (after line 47):

```python
    try:
        import proteinbox.api_literature as lit_pkg
        for _, module_name, _ in pkgutil.iter_modules(lit_pkg.__path__):
            importlib.import_module(f"proteinbox.api_literature.{module_name}")
    except ImportError:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/proteinbox/test_literature_tool.py -v
```
Expected: 4 passed

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add proteinbox/tools/registry.py tests/proteinbox/test_literature_tool.py
git commit -m "feat(literature): integrate literature tool into registry discovery"
```
