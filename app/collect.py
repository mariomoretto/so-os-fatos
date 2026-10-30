"""Coleta de matérias via RSS."""
from __future__ import annotations
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser

from .config import FEEDS, MAX_AGE_HOURS
from .models import Article

_TAG = re.compile(r"<[^>]+>")
_IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
# logos e pixels de rastreamento que alguns feeds colocam no lugar da foto
_NOT_PHOTO = re.compile(r"logo|ebc\.png|pixel|feedburner|gravatar|1x1|spacer", re.I)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text or ""))).strip()


def _published(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def image_of(entry) -> str:
    """Primeira foto da matéria: media:content, anexo de imagem ou <img> no texto."""
    urls = [m.get("url", "") for m in entry.get("media_content", []) + entry.get("media_thumbnail", [])]
    urls += [l.get("href", "") for l in entry.get("links", []) if l.get("type", "").startswith("image")]
    for part in [entry.get("summary", "")] + [c.get("value", "") for c in entry.get("content", [])]:
        urls += _IMG.findall(part or "")
    for url in urls:
        url = html.unescape(url).strip()
        if url.startswith("http") and not _NOT_PHOTO.search(url):
            return url.replace("http://", "https://", 1)
    return ""


def fetch_feed(source: str, url: str, category: str) -> list[Article]:
    parsed = feedparser.parse(url, agent="NoticiasFatos/0.1")
    if not parsed.entries and parsed.get("bozo"):
        raise RuntimeError(parsed.get("bozo_exception") or "feed inválido")
    if parsed.get("status", 200) >= 400:
        raise RuntimeError(f"HTTP {parsed.status}")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    out = []
    for e in parsed.entries:
        pub = _published(e)
        if pub and pub < cutoff:
            continue
        title = clean(e.get("title", ""))
        link = e.get("link", "")
        if not title or not link:
            continue
        out.append(Article(source, category, title, clean(e.get("summary", ""))[:1500], link, pub, image_of(e)))
    return out


def collect(categories: list[str] | None = None) -> list[Article]:
    articles, seen = [], set()
    for cat, feeds in FEEDS.items():
        if categories and cat not in categories:
            continue
        for source, url in feeds:
            try:
                got = [a for a in fetch_feed(source, url, cat) if a.link not in seen]
                seen.update(a.link for a in got)
                print(f"  {cat:<11} {source:<15} {len(got):>3} matérias")
                articles.extend(got)
            except Exception as exc:  # uma fonte fora do ar não derruba as outras
                print(f"  {cat:<11} {source:<15} ERRO: {exc}")
    return articles
