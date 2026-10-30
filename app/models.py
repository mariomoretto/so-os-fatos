from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib


@dataclass
class Article:
    source: str
    category: str
    title: str
    summary: str
    link: str
    published: datetime | None = None
    image: str = ""

    @property
    def id(self) -> str:
        return hashlib.sha1(self.link.encode()).hexdigest()[:12]

    @property
    def text(self) -> str:
        return f"{self.title}. {self.summary}".strip()


@dataclass
class Fact:
    text: str
    sources: list[str]  # nomes das fontes que confirmam
    links: list[str]


@dataclass
class Story:
    category: str
    headline: str
    facts: list[Fact]
    divergences: list[str]
    articles: list[Article] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
