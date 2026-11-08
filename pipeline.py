"""Roda o ciclo: coleta -> agrupa -> salva -> (resume com IA -> verifica).

Toda notícia nova entra na hora com a manchete de cada veículo (grátis, sem IA).
O resumo por IA só roda com um modelo configurado:
  - NF_MODELO_LOCAL (ex.: gemma3:4b via Ollama): grátis, lento; resume até N grupos por execução.
  - ANTHROPIC_API_KEY: Claude, pago; resume todos os grupos novos.

Uso:
    python pipeline.py                      # todas as categorias
    python pipeline.py esportes mundo       # só algumas
    python pipeline.py --resumir 5          # com IA: no máximo 5 resumos nesta execução
    python pipeline.py --dry-run            # coleta e agrupa, sem salvar
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

import anthropic

from app import db
from app.cluster import cluster, representative
from app.collect import collect
from app.config import LOCAL_MODEL
from app.extract import extract_story
from app.models import Story


def free_story(group) -> Story:
    dates = [a.published for a in group if a.published]
    return Story(group[0].category, representative(group).title, [], [], group,
                 max(dates) if dates else datetime.now(timezone.utc))


def summarize(con, groups, limit: int | None, minutes: float) -> None:
    """Resume com IA os grupos ainda sem resumo, dos mais confirmados e recentes para os demais."""
    todo = [g for g in groups if db.needs_summary(con, [a.link for a in g])]
    todo.sort(key=lambda g: (len({a.source for a in g}), free_story(g).created_at), reverse=True)
    todo = todo[:limit] if limit else todo
    print(f"\nResumindo {len(todo)} acontecimento(s) com {LOCAL_MODEL or 'Claude'}...")
    deadline = time.time() + minutes * 60
    for g in todo:
        if time.time() > deadline:
            print("  tempo esgotado; o resto fica para a próxima execução")
            break
        t = time.time()
        try:
            story, dropped = extract_story(g)
        except anthropic.AuthenticationError:
            sys.exit("ERRO: chave da API inválida. Confira ANTHROPIC_API_KEY.")
        except Exception as exc:
            print(f"  erro ao resumir: {exc}")
            continue
        base = free_story(g)
        if story:
            story.created_at = base.created_at  # resumir não faz a notícia "subir" na lista
            story.ai_tried = True
            db.save(con, story)
            print(f"  + {story.headline}  ({len(story.facts)} fatos, {dropped} descartados, {time.time() - t:.0f}s)")
        else:
            base.ai_tried = True  # não tenta de novo o mesmo grupo
            db.save(con, base)
            print(f"  - nenhum fato confirmado ({dropped} descartados, {time.time() - t:.0f}s): {g[0].title}")


def main(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    limit = int(argv[argv.index("--resumir") + 1]) if "--resumir" in argv else None
    cats = [a for a in argv if not a.startswith("--") and not a.isdigit()] or None
    use_ai = bool(LOCAL_MODEL or os.getenv("ANTHROPIC_API_KEY"))

    print("Coletando...")
    articles = collect(cats)
    groups = cluster(articles)
    print(f"\n{len(articles)} matérias, {len(groups)} acontecimentos com 2+ fontes.\n")

    if dry:
        for g in groups:
            print(f"[{g[0].category}] " + " | ".join(f"{a.source}: {a.title}" for a in g))
        return

    con = db.connect()
    novos = 0
    for g in groups:  # notícia nova entra na hora; as já salvas (e seus resumos) ficam como estão
        if not db.exists(con, [a.link for a in g]):
            db.save(con, free_story(g))
            novos += 1
    print(f"{novos} notícias novas.")

    if use_ai:
        minutes = float(os.getenv("NF_IA_MINUTOS", "15")) if LOCAL_MODEL else float("inf")
        summarize(con, groups, limit if LOCAL_MODEL else None, minutes)
    db.prune(con)


if __name__ == "__main__":
    main(sys.argv[1:])
