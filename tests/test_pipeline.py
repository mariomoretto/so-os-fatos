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
