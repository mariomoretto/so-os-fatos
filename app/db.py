"""Persistência simples em SQLite."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import CATEGORY_LABELS, DB_PATH
from .models import Story

SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    key TEXT PRIMARY KEY,          -- links ordenados do grupo, evita reprocessar
    category TEXT NOT NULL,
    headline TEXT NOT NULL,
    facts TEXT NOT NULL,           -- JSON
    divergences TEXT NOT NULL,     -- JSON
    sources TEXT NOT NULL,         -- JSON [{source, title, link}]
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cat_date ON stories(category, created_at DESC);
"""


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def group_key(links: list[str]) -> str:
    return "|".join(sorted(links))


def exists(con, links: list[str]) -> bool:
    return con.execute("SELECT 1 FROM stories WHERE key=?", (group_key(links),)).fetchone() is not None


def save(con, story: Story) -> None:
    """Salva a notícia. Se o acontecimento já existia com menos matérias, a versão antiga sai."""
    links = {a.link for a in story.articles}
    for (key,) in con.execute("SELECT key FROM stories").fetchall():
        if links & set(key.split("|")):
            con.execute("DELETE FROM stories WHERE key=?", (key,))
    con.execute(
        "INSERT OR REPLACE INTO stories VALUES (?,?,?,?,?,?,?)",
        (
            group_key([a.link for a in story.articles]),
            story.category,
            story.headline,
            json.dumps([f.__dict__ for f in story.facts], ensure_ascii=False),
            json.dumps(story.divergences, ensure_ascii=False),
            json.dumps([{"source": a.source, "title": a.title, "link": a.link} for a in story.articles],
                       ensure_ascii=False),
            story.created_at.isoformat(timespec="seconds"),
        ),
    )
    con.commit()


def list_stories(con, category: str | None = None, limit: int = 50) -> list[dict]:
    q, args = "SELECT * FROM stories", []
    if category:
        q += " WHERE category=?"
        args.append(category)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    out = []
    for r in con.execute(q, args):
        out.append({
            "category": r["category"],
            "headline": r["headline"],
            "facts": json.loads(r["facts"]),
            "divergences": json.loads(r["divergences"]),
            "sources": json.loads(r["sources"]),
            "created_at": r["created_at"],
        })
    return out


def prune(con, days: int = 7) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    con.execute("DELETE FROM stories WHERE created_at < ?", (cutoff,))
    con.commit()


def snapshot(con) -> dict:
    """Tudo que a página precisa, num JSON só (usado pelo servidor local e pelo site estático)."""
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categorias": CATEGORY_LABELS,
        "noticias": list_stories(con, limit=300),
    }
