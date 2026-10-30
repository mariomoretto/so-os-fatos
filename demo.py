"""Popula o banco com uma notícia de exemplo, para ver a página sem chave de API nem internet."""
from app import db
from app.extract import extract_story
from tests.fixtures import SELIC
from tests.test_pipeline import FakeClient, _raw

story, _ = extract_story(SELIC, FakeClient(_raw()))
db.save(db.connect(), story)
print("Exemplo salvo. Rode: uvicorn app.main:app --reload  e abra http://localhost:8000")
