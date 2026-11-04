"""Teste do modelo local: resume os N acontecimentos mais confirmados e mostra cada trecho citado.

Para cada evidência: ✓ cópia exata, ≈ passaria com tolerância, ✗ rejeitada (com o pedaço mais
parecido da matéria, para comparar a olho).
Uso: NF_MODELO_LOCAL=qwen3:4b python testar_ia.py 6
"""
import sys
import time

from app.cluster import cluster
from app.collect import collect
from app.config import LOCAL_MODEL
from app.extract import _norm, build_prompt, call_local, quote_in_text, quote_score, verify

TOL = 0.85


def closest(quote: str, text: str) -> str:
    qw, tw = _norm(quote).split(), _norm(text).split()
    n = max(len(qw), 1)
    best = max(range(max(len(tw) - n + 1, 1)), key=lambda i: quote_score(quote, " ".join(tw[i:i + n])))
    return " ".join(tw[best:best + n])


n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
groups = cluster(collect())[:n]
print(f"\nModelo: {LOCAL_MODEL} | {len(groups)} acontecimentos | tolerância {TOL}\n")
start, with_exact, with_tol = time.time(), 0, 0
for g in groups:
    t = time.time()
    text, ids = build_prompt(g)
    print(f"### {g[0].category} | {len({a.source for a in g})} veículos")
    for k, a in ids.items():
        print(f"    {k} [{a.source}] {a.title}")
    try:
        raw = call_local(text)
    except Exception as exc:
        print(f"  ERRO: {exc}\n")
        continue
    print(f"  MANCHETE: {raw.get('manchete')}")
    for f in raw.get("fatos", []):
        print(f"   • {f.get('fato')}")
        for ev in f.get("evidencias", []):
            art, quote = ids.get(ev.get("artigo", "").strip()), ev.get("trecho", "")
            if not art:
                print(f"       ✗ {ev.get('artigo')}: artigo inexistente")
                continue
            mark = "✓" if quote_in_text(quote, art.text, 1) else "≈" if quote_in_text(quote, art.text, TOL) else "✗"
            print(f"       {mark} {ev['artigo']} ({art.source}) nota {quote_score(quote, art.text):.2f}: \"{quote}\"")
            if mark != "✓":
                print(f"           matéria: \"{closest(quote, art.text)}\"")
    exact, _ = verify(raw, ids, min_ratio=1)
    tol, _ = verify(raw, ids, min_ratio=TOL)
    with_exact += bool(exact)
    with_tol += bool(tol)
    print(f"  => fatos aprovados: {len(exact)} exatos | {len(tol)} com tolerância | {time.time() - t:.0f}s\n")
print(f"RESUMO: acontecimentos com resumo: {with_exact}/{len(groups)} só exato | {with_tol}/{len(groups)} com tolerância")
print(f"Tempo total: {time.time() - start:.0f}s")
