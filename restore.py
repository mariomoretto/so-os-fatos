"""Recria o banco a partir do noticias.json publicado.

No GitHub Actions cada execução começa do zero; o próprio site guarda as notícias entre uma e outra.
Uso: python restore.py [--obrigatorio]   (--obrigatorio: falha se não recuperar nada)
"""
import json
import sys
import time
import urllib.request

from app import db

URL = "https://mariomoretto.github.io/so-os-fatos/noticias.json"

if __name__ == "__main__":
    try:
        with urllib.request.urlopen(f"{URL}?t={int(time.time())}", timeout=20) as r:
            stories = json.load(r)["noticias"]
    except Exception as exc:
        print(f"Não deu para baixar as notícias publicadas: {exc}")
        stories = []
    n = db.restore(db.connect(), stories)
    print(f"{n} notícias recuperadas do site.")
    if n == 0 and "--obrigatorio" in sys.argv:
        sys.exit("Nada recuperado; o site não será republicado.")
