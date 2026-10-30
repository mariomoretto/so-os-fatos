"""Roda o ciclo completo: coleta -> agrupa -> (extrai fatos -> verifica) -> salva.

Sem ANTHROPIC_API_KEY roda no modo grátis: publica cada acontecimento noticiado por 2+ veículos
com a manchete de cada um, sem chamar o Claude. Com a chave, extrai e confere os fatos.

Uso:
    python pipeline.py                      # todas as categorias
    python pipeline.py esportes games       # só algumas
    python pipeline.py --dry-run            # coleta e agrupa, sem salvar
"""
import os
import sys
from datetime import datetime, timezone

import anthropic

from app import db
from app.cluster import cluster, representative
from app.collect import collect
from app.extract import extract_story
from app.models import Story


def free_story(group) -> Story:
    dates = [a.published for a in group if a.published]
    return Story(group[0].category, representative(group).title, [], [], group,
                 max(dates) if dates else datetime.now(timezone.utc))


def main(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    cats = [a for a in argv if not a.startswith("--")] or None
    use_ai = bool(os.getenv("ANTHROPIC_API_KEY"))

    print("Coletando...")
    articles = collect(cats)
    groups = cluster(articles)
    print(f"\n{len(articles)} matérias, {len(groups)} acontecimentos com 2+ fontes.\n")

    if dry:
        for g in groups:
            print(f"[{g[0].category}] " + " | ".join(f"{a.source}: {a.title}" for a in g))
        return

    print("Modo: " + ("com IA (extração de fatos)" if use_ai else "grátis (sem IA)"))
    con = db.connect()
    novos = 0
    for g in groups:
        if not use_ai:
            db.save(con, free_story(g))
            novos += 1
            continue
        if db.exists(con, [a.link for a in g]):
            continue
        try:
            story, dropped = extract_story(g)
        except anthropic.AuthenticationError:
            sys.exit("ERRO: chave da API inválida. Confira ANTHROPIC_API_KEY.")
        except Exception as exc:
            print(f"  erro ao extrair: {exc}")
            continue
        if story:
            db.save(con, story)
            novos += 1
            print(f"  + {story.headline}  ({len(story.facts)} fatos, {dropped} descartados)")
        else:
            print(f"  - nenhum fato confirmado: {g[0].title}")
    db.prune(con)
    print(f"\n{novos} notícias novas ou atualizadas.")


if __name__ == "__main__":
    main(sys.argv[1:])
