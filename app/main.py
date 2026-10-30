"""Servidor local. Rode com: uvicorn app.main:app --reload  (no celular, use o site do GitHub Pages)"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import db

app = FastAPI(title="Só os Fatos")


@app.get("/noticias.json")
def noticias():
    con = db.connect()
    try:
        return db.snapshot(con)
    finally:
        con.close()


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
