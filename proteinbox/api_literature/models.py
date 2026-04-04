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
