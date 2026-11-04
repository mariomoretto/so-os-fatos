"""Teste do modelo local: resume os N acontecimentos mais confirmados e mostra resultado e tempo.

Uso: NF_MODELO_LOCAL=qwen3:4b python testar_ia.py 6
"""
import sys
import time

from app.cluster import cluster
from app.collect import collect
from app.config import LOCAL_MODEL
from app.extract import extract_story

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
groups = cluster(collect())[:n]
print(f"\nModelo: {LOCAL_MODEL} | {len(groups)} acontecimentos\n")
total = time.time()
for g in groups:
    t = time.time()
    print(f"### {g[0].category} | {len({a.source for a in g})} veículos")
    for a in g:
        print(f"    [{a.source}] {a.title}")
    try:
        story, dropped = extract_story(g)
    except Exception as exc:
        print(f"  ERRO: {exc}\n")
        continue
    if story:
        print(f"  MANCHETE: {story.headline}")
        for f in story.facts:
            print(f"   • {f.text}  ({', '.join(f.sources)})")
        print(f"  {dropped} fato(s) descartado(s) pela verificação | {time.time() - t:.0f}s\n")
    else:
        print(f"  nenhum fato confirmado ({dropped} descartados) | {time.time() - t:.0f}s\n")
print(f"Tempo total: {time.time() - total:.0f}s")
