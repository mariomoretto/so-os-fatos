"""Agrupa matérias de fontes diferentes que falam do mesmo acontecimento."""
import unicodedata

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import CLUSTER_THRESHOLD, MIN_SOURCES
from .models import Article

STOPWORDS = set("""
a à ao aos as às até com como da das de del dele deles do dos e é ela elas ele eles em entre era essa esse
esta este eu foi for foram há isso isto já la lhe mais mas me mesmo meu muito na nas nem no nos nós o os
ou para pela pelas pelo pelos por qual quando que quem se sem ser seu sua são só também te tem têm um uma
umas uns vai vão diz disse afirma após sobre contra ser será sido ter teve hoje ontem nesta neste nessa
""".split())


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def cluster(articles: list[Article], threshold: float = CLUSTER_THRESHOLD,
            min_sources: int = MIN_SOURCES) -> list[list[Article]]:
    """Agrupamento por ligação simples sobre similaridade TF-IDF, dentro de cada categoria.

    Retorna só grupos com matérias de pelo menos `min_sources` veículos diferentes.
    """
    groups: list[list[Article]] = []
    by_cat: dict[str, list[Article]] = {}
    for a in articles:
        by_cat.setdefault(a.category, []).append(a)

    for arts in by_cat.values():
        if len(arts) < 2:
            continue
        stop = sorted({_norm(w) for w in STOPWORDS})
        vec = TfidfVectorizer(preprocessor=_norm, stop_words=stop, sublinear_tf=True)
        # título conta em dobro: é onde o fato principal costuma estar
        docs = [f"{a.title}. {a.title}. {a.summary}" for a in arts]
        sim = cosine_similarity(vec.fit_transform(docs))

        # union-find
        parent = list(range(len(arts)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(arts)):
            for j in range(i + 1, len(arts)):
                if arts[i].source != arts[j].source and sim[i, j] >= threshold:
                    parent[find(i)] = find(j)

        buckets: dict[int, list[Article]] = {}
        for i, a in enumerate(arts):
            buckets.setdefault(find(i), []).append(a)
        for g in buckets.values():
            if len({a.source for a in g}) >= min_sources:
                groups.append(g)

    groups.sort(key=lambda g: len({a.source for a in g}), reverse=True)
    return groups
