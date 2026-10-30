"""Gera o site estático em site/ (publicado no GitHub Pages; é o app do celular)."""
import json
import shutil
from pathlib import Path

from app import db

STATIC = Path(__file__).parent / "app" / "static"
OUT = Path("site")

if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(STATIC, OUT)
    con = db.connect()
    (OUT / "noticias.json").write_text(json.dumps(db.snapshot(con), ensure_ascii=False), encoding="utf-8")
    print(f"Site gerado em {OUT}/")
