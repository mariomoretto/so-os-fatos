"""Gera o site estático em site/ (publicado no GitHub Pages; é o app do celular)."""
from __future__ import annotations
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app import db

STATIC = Path(__file__).parent / "app" / "static"
OUT = Path("site")


def ibovespa() -> dict | None:
    """Ibovespa pela HG Brasil. Vem daqui porque ela não libera acesso direto do navegador."""
    try:
        with urllib.request.urlopen("https://api.hgbrasil.com/finance?format=json-cors", timeout=15) as r:
            ibov = json.load(r)["results"]["stocks"]["IBOVESPA"]
        return {"pontos": ibov["points"], "variacao": ibov["variation"],
                "em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    except Exception as exc:  # sem Ibovespa o site sai do mesmo jeito
        print(f"Ibovespa indisponível: {exc}")
        return None


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(STATIC, OUT)
    data = db.snapshot(db.connect())
    data["ibovespa"] = ibovespa()
    (OUT / "noticias.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Site gerado em {OUT}/")
