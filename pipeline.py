"""Roda o ciclo completo: coleta -> agrupa -> extrai fatos -> verifica -> salva.

Uso:
    python pipeline.py                      # todas as categorias
    python pipeline.py esportes games       # só algumas
    python pipeline.py --dry-run            # coleta e agrupa, sem chamar o Claude
"""
import sys

import anthropic

from app import db
from app.cluster import cluster
from app.collect import collect
from app.extract import extract_story


def main(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    cats = [a for a in argv if not a.startswith("--")] or None

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
    for g in groups:
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
    print(f"\n{novos} novas notícias salvas.")


if __name__ == "__main__":
    main(sys.argv[1:])
