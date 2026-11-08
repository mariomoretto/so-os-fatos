"""Extração de fatos com o Claude + verificação determinística das evidências.

O modelo propõe fatos e, para cada um, aponta o trecho literal de cada matéria que o sustenta.
Depois o código confere se esses trechos existem mesmo no texto das matérias. Fato cuja
evidência não bate, ou que não tenha ao menos MIN_SOURCES fontes confirmadas, é descartado.
"""
from __future__ import annotations
import json
import re
import unicodedata
import urllib.request
from difflib import SequenceMatcher

from .config import CROSS_CHECK, LOCAL_MODEL, MIN_SOURCES, MODEL, OLLAMA_URL, QUOTE_MATCH
from .models import Article, Fact, Story

SYSTEM = """Você é um checador de fatos. Recebe várias matérias de veículos diferentes sobre o mesmo acontecimento.
Sua tarefa é extrair SOMENTE fatos verificáveis, sem opinião.

Regras:
- Fato = quem, o quê, quando, onde, quanto (números, datas, decisões, declarações atribuídas).
- Declarações de pessoas só entram como atribuição: "Fulano afirmou que X", nunca "X" como verdade.
- Proibido: adjetivos de juízo (polêmico, histórico, duro, surpreendente...), interpretação, previsão,
  análise de jornalista, "especialistas avaliam", motivações presumidas.
- Escreva cada fato em português, frase curta, com suas próprias palavras.
- Para cada fato, cite como evidência o trecho LITERAL (copiado exatamente, até 25 palavras) de cada
  matéria que o confirma, identificando a matéria pelo id (ex.: A1).
- Cada fato precisa ser confirmado por matérias de PELO MENOS DOIS veículos diferentes (veja "Fonte"):
  cite um trecho de cada um. Se a informação aparece em um veículo só, deixe o fato de fora.
- Se as matérias discordam em algum dado (número, data, nome), registre em divergências, citando quem diz o quê.
- Prefira menos fatos bem sustentados a muitos fatos fracos.
- Responda sempre chamando a ferramenta registrar_fatos."""

TOOL = {
    "name": "registrar_fatos",
    "description": "Registra a manchete neutra, os fatos com evidências e as divergências.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "manchete": {"type": "string", "description": "Manchete neutra e factual, até 14 palavras."},
            "fatos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fato": {"type": "string"},
                        "evidencias": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "artigo": {"type": "string"},
                                    "trecho": {"type": "string"},
                                },
                                "required": ["artigo", "trecho"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["fato", "evidencias"],
                    "additionalProperties": False,
                },
            },
            "divergencias": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["manchete", "fatos", "divergencias"],
        "additionalProperties": False,
    },
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[“”\"'‘’«»]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_score(quote: str, text: str) -> float:
    """Fração das palavras do trecho que aparecem na matéria, na ordem, em sequências de 2+ palavras."""
    qw, tw = _norm(quote).strip(" .…").split(), _norm(text).split()
    if not qw:
        return 0.0
    blocks = SequenceMatcher(None, qw, tw, autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks if b.size >= 2) / len(qw)


def quote_in_text(quote: str, text: str, min_ratio: float = QUOTE_MATCH) -> bool:
    q = _norm(quote).strip(" .…")
    if len(q) < 8:
        return False
    if q in _norm(text):
        return True
    # tolerância opcional para modelos que reescrevem um pouco o trecho em vez de copiar
    return min_ratio < 1 and len(q.split()) >= 5 and quote_score(quote, text) >= min_ratio


_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_NAME = re.compile(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,}")
_NOT_NAME = {"para", "apos", "segundo", "nesta", "neste", "desde", "como", "entre", "sobre", "durante", "ainda"}


def key_terms(text: str) -> tuple[set[str], set[str]]:
    """Números e nomes próprios de uma frase, já normalizados."""
    nums = set(_NUM.findall(text))
    names = {_norm(w) for w in _NAME.findall(text)} - _NOT_NAME
    return nums, names


def has_terms(text: str, nums: set[str], names: set[str]) -> bool:
    """A matéria traz todos os números e pelo menos 2/3 dos nomes?"""
    t = _norm(text)
    found_names = sum(1 for n in names if re.search(rf"\b{re.escape(n)}\b", t))
    return nums <= set(_NUM.findall(t)) and found_names * 3 >= len(names) * 2


def corroborating_article(fact: str, confirmed: Article, ids: dict[str, Article], sources: list[str]) -> Article | None:
    """Matéria de outro veículo com os mesmos números e nomes do fato (que também precisam estar na já confirmada)."""
    nums, names = key_terms(fact)
    if len(nums) + len(names) < 2 or not has_terms(confirmed.text, nums, names):
        return None
    return next((a for a in ids.values() if a.source not in sources and has_terms(a.text, nums, names)), None)


def build_prompt(articles: list[Article]) -> tuple[str, dict[str, Article]]:
    ids = {f"A{i + 1}": a for i, a in enumerate(articles)}
    parts = [f"[{k}] Fonte: {a.source}\nTítulo: {a.title}\nTexto: {a.summary}" for k, a in ids.items()]
    return "\n\n".join(parts), ids


def verify(raw: dict, ids: dict[str, Article], min_sources: int = MIN_SOURCES,
           min_ratio: float = QUOTE_MATCH, cross: bool = CROSS_CHECK) -> tuple[list[Fact], int]:
    """Mantém só fatos cujas evidências existem literalmente e vêm de fontes distintas suficientes.

    Retorna (fatos aprovados, quantidade descartada).
    """
    kept, dropped = [], 0
    for f in raw.get("fatos", []):
        sources, links, confirmed = [], [], []
        for ev in f.get("evidencias", []):
            art = ids.get(ev.get("artigo", "").strip())
            if art and quote_in_text(ev.get("trecho", ""), art.text, min_ratio) and art.source not in sources:
                sources.append(art.source)
                links.append(art.link)
                confirmed.append(art)
        if cross and len(confirmed) == 1 and min_sources == 2:
            other = corroborating_article(f.get("fato", ""), confirmed[0], ids, sources)
            if other:
                sources.append(other.source)
                links.append(other.link)
        if len(sources) >= min_sources and f.get("fato", "").strip():
            kept.append(Fact(f["fato"].strip(), sources, links))
        else:
            dropped += 1
    return kept, dropped


def call_claude(user_text: str, client=None) -> dict:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        tools=[TOOL],
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": user_text}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Modelo não retornou a ferramenta esperada")


def call_local(user_text: str) -> dict:
    """Modelo pequeno via Ollama. O formato da resposta é forçado pelo mesmo schema da ferramenta."""
    body = {
        "model": LOCAL_MODEL, "stream": False, "format": TOOL["input_schema"],
        "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [
            {"role": "system", "content": SYSTEM.replace("Responda sempre chamando a ferramenta registrar_fatos.",
                                                         "Responda apenas com o JSON pedido.")},
            {"role": "user", "content": user_text},
        ],
    }
    if LOCAL_MODEL.startswith("qwen3"):
        body["think"] = False  # sem "raciocínio" longo: bem mais rápido
    req = urllib.request.Request(OLLAMA_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(json.load(r)["message"]["content"])


def extract_story(articles: list[Article], client=None) -> tuple[Story | None, int]:
    text, ids = build_prompt(articles)
    raw = call_local(text) if LOCAL_MODEL and client is None else call_claude(text, client)
    facts, dropped = verify(raw, ids)
    if not facts:
        return None, dropped
    # Divergência só é útil se mencionar alguma fonte real do grupo.
    names = {a.source.lower() for a in articles}
    div = [d for d in raw.get("divergencias", []) if any(n in d.lower() for n in names)]
    story = Story(articles[0].category, raw.get("manchete", facts[0].text), facts, div, articles)
    return story, dropped
