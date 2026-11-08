from types import SimpleNamespace

from app import db
from app.cluster import cluster, representative
from app.extract import extract_story, quote_in_text, verify, build_prompt
from tests.fixtures import OUTRO, SELIC


def test_cluster_groups_same_event_and_separates_others():
    groups = cluster(SELIC + [OUTRO])
    assert len(groups) == 1
    assert {a.source for a in groups[0]} == {"g1", "Folha", "InfoMoney"}


def test_cluster_ignores_single_source_events():
    assert cluster([SELIC[0], OUTRO]) == []


def test_quote_matching_tolerates_accents_case_and_spacing():
    assert quote_in_text("decisao foi  UNANIME", SELIC[0].text)
    assert not quote_in_text("decisão foi dividida", SELIC[0].text)
    assert not quote_in_text("15%", SELIC[0].text)  # trecho curto demais não vale como prova


def _raw():
    return {
        "manchete": "Copom mantém Selic em 15% ao ano",
        "fatos": [
            {"fato": "O Copom manteve a Selic em 15% ao ano.", "evidencias": [
                {"artigo": "A1", "trecho": "manter a taxa básica de juros em 15% ao ano"},
                {"artigo": "A2", "trecho": "O Copom manteve a Selic em 15% ao ano"},
                {"artigo": "A3", "trecho": "decidiu manter a Selic em 15% ao ano"}]},
            {"fato": "A decisão foi unânime.", "evidencias": [
                {"artigo": "A1", "trecho": "A decisão foi unânime."},
                {"artigo": "A2", "trecho": "em decisão unânime"}]},
            # alucinação: trecho não existe na matéria
            {"fato": "O BC indicou cortes em dezembro.", "evidencias": [
                {"artigo": "A1", "trecho": "o BC indicou cortes em dezembro"},
                {"artigo": "A3", "trecho": "comitê afirmou que seguirá vigilante"}]},
            # só uma fonte
            {"fato": "Foi a quarta manutenção seguida.", "evidencias": [
                {"artigo": "A2", "trecho": "É a quarta manutenção seguida."}]},
        ],
        "divergencias": ["Nenhuma fonte X diz Y", "Folha fala em quarta manutenção seguida; g1 não informa"],
    }


def test_verify_drops_hallucinated_and_single_source_facts():
    _, ids = build_prompt(SELIC)
    facts, dropped = verify(_raw(), ids)
    assert [f.text for f in facts] == ["O Copom manteve a Selic em 15% ao ano.", "A decisão foi unânime."]
    assert facts[0].sources == ["g1", "Folha", "InfoMoney"]
    assert dropped == 2


def test_verify_counts_distinct_outlets_not_articles():
    arts = [SELIC[0], SELIC[0].__class__("g1", "economia", "Outra do g1", SELIC[1].summary, "https://g1.example/2")]
    _, ids = build_prompt(arts)
    raw = {"fatos": [{"fato": "x", "evidencias": [
        {"artigo": "A1", "trecho": "A decisão foi unânime."},
        {"artigo": "A2", "trecho": "em decisão unânime"}]}]}
    facts, _ = verify(raw, ids)
    assert facts == []


class FakeClient:
    def __init__(self, payload):
        self.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", input=payload)]))


def test_end_to_end_with_fake_model(tmp_path):
    story, dropped = extract_story(SELIC, FakeClient(_raw()))
    assert story.headline == "Copom mantém Selic em 15% ao ano"
    assert len(story.facts) == 2 and dropped == 2
    assert story.divergences == ["Folha fala em quarta manutenção seguida; g1 não informa"]

    con = db.connect(str(tmp_path / "t.db"))
    db.save(con, story)
    assert db.exists(con, [a.link for a in SELIC])
    rows = db.list_stories(con, "economia")
    assert rows[0]["facts"][1]["sources"] == ["g1", "Folha"]
    assert db.list_stories(con, "games") == []


def test_new_version_of_event_replaces_old(tmp_path):
    con = db.connect(str(tmp_path / "t.db"))
    old, _ = extract_story(SELIC[:2], FakeClient(_raw()))
    new, _ = extract_story(SELIC, FakeClient(_raw()))
    db.save(con, old)
    db.save(con, new)
    rows = db.list_stories(con)
    assert len(rows) == 1 and len(rows[0]["sources"]) == 3


def test_free_mode_headline_is_the_most_shared_title():
    assert representative(SELIC).source in {"g1", "Folha", "InfoMoney"}
    assert "Selic" in representative(SELIC).title or "juros" in representative(SELIC).title


def test_image_skips_logos_and_tracking_pixels():
    from app.collect import image_of
    entry = {"summary": '<img src="https://agenciabrasil.ebc.com.br/ebc.png?id=1&amp;o=rss">'
                        '<img src="https://x.example/logo-agencia.png"><img src="http://x.example/foto.jpg?a=1&amp;b=2">'}
    assert image_of(entry) == "https://x.example/foto.jpg?a=1&b=2"
    assert image_of({"media_content": [{"url": "https://g1.example/f.jpg"}]}) == "https://g1.example/f.jpg"
    assert image_of({"summary": "sem foto"}) == ""


def test_quote_tolerance_is_off_by_default_and_still_blocks_invented_text():
    text = SELIC[0].text
    near = "Comitê de Política Monetária do Banco Central decidiu manter a taxa de juros em 15% ao ano"
    assert not quote_in_text(near, text)              # padrão: só cópia exata
    assert quote_in_text(near, text, 0.85)            # quase igual: passa com tolerância
    invented = "o Banco Central decidiu cortar a taxa básica para 12% ao ano em dezembro"
    assert not quote_in_text(invented, text, 0.85)    # inventado: continua barrado


def test_cross_check_needs_same_numbers_and_names_in_another_outlet():
    _, ids = build_prompt(SELIC)
    one_source = {"fatos": [{"fato": "O Copom manteve a Selic em 15% ao ano.", "evidencias": [
        {"artigo": "A1", "trecho": "manter a taxa básica de juros em 15% ao ano"}]}]}
    assert verify(one_source, ids, cross=False)[0] == []                       # desligado: precisa de 2 trechos
    facts, _ = verify(one_source, ids, cross=True)
    assert facts and facts[0].sources[0] == "g1" and len(facts[0].sources) == 2  # Folha/InfoMoney trazem Copom, Selic e 15
    wrong = {"fatos": [{"fato": "O Copom manteve a Selic em 14% ao ano.", "evidencias": [
        {"artigo": "A1", "trecho": "manter a taxa básica de juros em 15% ao ano"}]}]}
    assert verify(wrong, ids, cross=True)[0] == []                             # número que não está nas matérias


def test_outlet_only_counts_if_its_article_has_the_same_numbers():
    from app.models import Article
    g1 = Article("g1", "mundo", "Ataque", "Ataque deixa seis mortos e pelo menos 15 feridos neste sábado (7).", "https://g1.example/a")
    fo = Article("Folha", "mundo", "Ataque", "Um homem matou seis pessoas e feriu outras 16 neste sábado (7).", "https://fo.example/a")
    _, ids = build_prompt([g1, fo])
    raw = {"fatos": [{"fato": "O ataque deixou 15 feridos.", "evidencias": [
        {"artigo": "A1", "trecho": "deixa seis mortos e pelo menos 15 feridos"},
        {"artigo": "A2", "trecho": "matou seis pessoas e feriu outras 16"}]}]}
    assert verify(raw, ids)[0] == []        # Folha diz 16: não confirma "15 feridos"
    raw["fatos"][0]["fato"] = "O ataque aconteceu no sábado (7)."
    assert len(verify(raw, ids)[0]) == 1    # data igual nos dois: confirma


def test_ai_tried_flag_survives_save_and_restore(tmp_path):
    con = db.connect(str(tmp_path / "t.db"))
    story, _ = extract_story(SELIC, FakeClient({"manchete": "x", "fatos": [], "divergencias": []}))
    assert story is None
    from pipeline import free_story
    base = free_story(SELIC)
    links = [a.link for a in SELIC]
    assert db.needs_summary(con, links)
    base.ai_tried = True
    db.save(con, base)
    assert not db.needs_summary(con, links)           # já tentou: não tenta de novo
    rows = db.list_stories(con)
    con2 = db.connect(str(tmp_path / "t2.db"))
    db.restore(con2, rows)
    assert not db.needs_summary(con2, links)          # a marca volta ao recuperar do site
