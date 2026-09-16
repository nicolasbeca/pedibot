"""What a tweet is not allowed to say (6-sep-2026).

The operator asked for seven drafts a week to post from his own account. A post is a public
claim, and the site's entire argument is that it does not guess — so the cost of one invented
number in a tweet is higher than the reach the tweet buys.

The model therefore writes from a fact sheet that was counted, not remembered, and every draft is
read back before it can be sent. These are the rules it is read against. Each one is a way the
project has already been wrong somewhere else:

  · a number nobody measured (CLAUDE.md: "NO inventar resultados ni inflar números")
  · a clinician's approval that does not exist — no doctor has reviewed these guides, and that
    is the one claim that would actually hurt somebody
  · a dose or an age threshold, which is not a thing to put in a tweet at all
"""

from __future__ import annotations

import json
import pathlib

import pytest

from pedibot.bot.llm import FakeProvider
from pedibot.ops.tweets import (
    MAX_CHARS,
    allowed_numbers,
    fact_sheet,
    facts,
    load_history,
    problems,
    remember,
    write_batch,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

FACTS = {
    "guides": 483,
    "guides_per_language": {"en": 63, "es": 60},
    "language_names": ["English", "Spanish"],
    "languages": 8,
    "documents": 288,
    "organisations": 18,
    "organisation_names": ["WHO", "NHS", "RKI"],
    "vaccine_countries": 7,
    "vaccine_country_codes": ["BR", "ES"],
    "vaccine_authorities": ["Ministerio de Sanidad", "NHS"],
    "medicines_in_the_dose_calculator": 4,
    "guide_titles_english": ["What should I do if my child has a fever?"],
    # 16-sep-2026: el operador pidió que algunos tuits lleven enlace al tema del que hablan.
    # La lista sale de lo publicado, así que una dirección inventada no puede colarse.
    "links": [
        "https://pedibot.xyz/dose — the weight-based dose calculator",
        "https://pedibot.xyz/guides/fever — What should I do if my child has a fever?",
    ],
}
OK = allowed_numbers(FACTS)


def test_the_measured_numbers_are_the_only_ones_allowed() -> None:
    assert {"483", "63", "60", "8", "288", "18", "7", "4"} <= OK
    assert "1200" not in OK and "39" not in OK


@pytest.mark.parametrize(
    ("draft", "why"),
    [
        ("PediBot answers from 1200 published documents.", "números"),
        ("Every guide is reviewed by a paediatrician before it goes up.", "prohibida"),
        ("Our guides are doctor-approved and free.", "prohibida"),
        ("It can diagnose croup from a description.", "prohibida"),
        ("Give 15 mg per kg every six hours.", "números"),
        ("Read it at https://pedibot.xyz", "enlace"),
        ("Ask @pedibot anything.", "cuenta"),
        ("x" * (MAX_CHARS + 1), "caracteres"),
        ("   ", "vacío"),
    ],
)
def test_a_draft_that_breaks_a_rule_is_not_sent(draft: str, why: str) -> None:
    found = problems(draft, FACTS)
    assert found, f"debería haberse rechazado: {draft[:60]}"
    assert any(why in f for f in found), f"esperaba «{why}», salió {found}"


def test_a_true_and_measured_draft_passes() -> None:
    good = (
        "483 guides in 8 languages, written only from 288 published documents. "
        "Every sentence carries the number of the document it came from."
    )
    assert problems(good, FACTS) == []


def test_the_fact_sheet_carries_no_number_the_verifier_would_reject() -> None:
    """The sheet is what the model copies from. A number in it that the verifier does not know
    would train the model to write drafts that are then thrown away."""
    import re

    assert not [n for n in re.findall(r"\d+", fact_sheet(FACTS)) if n not in OK]


def test_the_sample_facts_carry_every_key_the_sheet_reads() -> None:
    """This is how three tests broke at once: a key was added to facts() and the sample here did
    not have it, so fact_sheet() raised KeyError and nothing said which key."""
    real = facts(ROOT, ROOT / "index" / "pedibot.db")
    assert set(real) == set(FACTS), f"faltan en el ejemplo: {sorted(set(real) - set(FACTS))}"


def test_facts_are_counted_in_this_deployment_not_stored() -> None:
    """A constant in a prompt goes stale in silence and starts being false. These are counted
    from the repository and the index every time the job runs."""
    f = facts(ROOT, ROOT / "index" / "pedibot.db")
    assert f["guides"] > 400 and f["languages"] == 8
    assert f["documents"] > 200 and f["organisations"] > 5
    assert f["vaccine_countries"] == len(f["vaccine_country_codes"])
    assert f["guide_titles_english"], "sin títulos reales no se puede citar una guía de verdad"


def test_the_batch_keeps_the_good_ones_and_says_why_it_dropped_the_rest() -> None:
    reply = "\n".join(
        [
            "1. 483 guides in 8 languages, each statement numbered to its document.",
            "2. Reviewed by paediatricians before publication.",  # a lie
            "3. Built from 9999 documents.",  # a number nobody measured
            "4. It says so when no source covers the question, instead of answering.",
            '5. "What should I do if my child has a fever?" — the answer names its sources.',
        ]
    )
    kept, dropped = write_batch(FakeProvider(reply), FACTS, n=7)
    assert len(kept) == 3, kept
    assert not any("paediatricians" in k for k in kept)
    assert any("prohibida" in d for d in dropped)
    assert any("9999" in d for d in dropped)
    # and the numbering the model reached for is gone from what would be pasted
    assert not any(k[0].isdigit() and k[1] in ".)" for k in kept)


def test_it_does_not_send_the_same_draft_two_weeks_running(tmp_path) -> None:
    line = "483 guides in 8 languages, each statement numbered to its document."
    kept, dropped = write_batch(FakeProvider(line), FACTS, n=7, already_sent=(line,))
    assert kept == []
    assert any("repetido" in d for d in dropped)


def test_what_went_out_is_remembered(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    remember(tmp_path, ["uno de verdad y bastante largo para pasar el filtro"])
    assert load_history(tmp_path) == ["uno de verdad y bastante largo para pasar el filtro"]
    # a corrupt line is skipped, not fatal: this file is appended to weekly for years
    (tmp_path / "data" / "tweets_sent.jsonl").write_text(
        json.dumps({"date": "2026-09-06", "text": "bueno"}) + "\n{roto\n", encoding="utf-8"
    )
    assert load_history(tmp_path) == ["bueno"]


def test_it_will_not_say_that_an_answer_is_numbered() -> None:
    """A guide numbers every statement. A chat answer names its sources and shows no numbers —
    the same confusion the site's own legal page had to be corrected for on 5-sep. The prompt
    forbids it and the model wrote it anyway in two batches out of three, so it is checked here
    rather than asked for there."""
    bad = (
        "Each question gets an answer from a published guideline, and every sentence is "
        "tagged with the number of the document it came from."
    )
    assert any("numeradas" in p for p in problems(bad, FACTS))
    good = "Every statement in a guide carries the number of the document it came from."
    assert problems(good, FACTS) == []


def test_a_quoted_title_keeps_its_opening_quotation_mark() -> None:
    """The unwrapper used to strip quotes from both ends, so a draft that opened with a quoted
    guide title lost the opening mark and went out looking broken."""
    from pedibot.ops.tweets import _split

    assert _split('"What should I do if my child has a fever?" is one of the guides here.') == [
        '"What should I do if my child has a fever?" is one of the guides here.'
    ]
    # a draft the model wrapped whole is still unwrapped
    assert _split('"483 guides, written from published documents only."') == [
        "483 guides, written from published documents only."
    ]


def test_it_will_not_name_a_body_that_does_not_exist() -> None:
    """Fourth batch, first draft: "built from 288 published documents by 18 bodies including WHO,
    RKI, NHS, and Ecuchi". There is no Ecuchi — the corpus has an Ecimed and the model reached
    for something shaped like it. Every number was right, so nothing fired.

    A name is exactly as falsifiable as a number, and inventing a source on a site whose whole
    argument is that it names its sources is the same failure as inventing a count."""
    bad = "Built from 288 documents by 18 bodies including WHO, RKI, NHS and Ecuchi."
    assert any("nombres" in p and "Ecuchi" in p for p in problems(bad, FACTS))
    good = "Built from 288 documents by 18 bodies including WHO, NHS and RKI."
    assert problems(good, FACTS) == []


def test_a_capital_at_the_start_of_a_sentence_proves_nothing() -> None:
    """English capitalises the first word of every sentence, and after an opening quote. Treating
    those as names would reject almost everything."""
    assert (
        problems("Vaccination schedules cover 7 countries. Each cites its own source.", FACTS) == []
    )


def test_it_will_not_quote_a_guide_that_does_not_exist() -> None:
    """Quoting a title is the strongest thing one of these can do — it is checkable in one click.
    So it has to be checkable in one click."""
    real = FACTS["guide_titles_english"][0]
    assert problems(f'"{real}" is one of 483 guides.', FACTS) == []
    made_up = '"What should I do if my child swallowed a magnet?" is one of 483 guides.'
    assert any("título que no existe" in p for p in problems(made_up, FACTS))


@pytest.mark.parametrize(
    "draft",
    [
        "PediBot now has a token, PDBT, live on four chains.",
        "483 guides, 8 languages, and a coin to go with them.",
        "Connect your wallet to support the project.",
    ],
)
def test_the_health_account_never_posts_about_the_token(draft: str) -> None:
    """These go out from @pedibotai, the account of a children's health site. A token launched
    on 6-sep takes 1% of every trade, and one post that mixes the two turns a paediatric feed
    into token promotion — for a parent who came for a fever question, that is the moment the
    site stops being credible.

    The operator already keeps them apart: the token is off the homepage by his own decision.
    This is that separation held by the code instead of by somebody remembering.
    """
    assert any("token" in p for p in problems(draft, FACTS))


def test_the_token_check_does_not_eat_ordinary_english() -> None:
    """ "listed" threw away a good draft on the first real run: the documents of a guide are
    listed at the foot. A guard that rejects true sentences costs drafts every week."""
    fine = (
        "Every sentence in a guide carries the number of its document, and the documents "
        "are listed at the foot."
    )
    assert problems(fine, FACTS) == []


# --- los organismos se ordenaban por grosor, no por número de documentos (7-sep-2026) ---------
#
# La frase que sale del generador es «built from 288 published documents by 18 bodies, including
# ...», pero la lista de nombres venía de contar TROZOS del índice. Un manual de 400 páginas se
# parte en miles de pedazos, así que un solo libro adelantaba a un organismo entero:
#
#   por trozos:      Ecimed 2056, PUC Chile 926, WHO 703, College of the Canyons 658, NHS 361
#   por documentos:  MedlinePlus 74, NHS 56, WHO 54, RKI 30, SEUP 29, CDC 19
#
# Ecimed y el College of the Canyons son UN documento cada uno. El ensayo del 7-sep escribió
# «including Ecimed, PUC Chile, the College of the Canyons and Santé publique France»: cada
# palabra verdad, y a la vez la peor foto posible del proyecto —el NHS, la OMS, los CDC y
# MedlinePlus fuera de la frase— en el único texto que existe para darlo a conocer.


def _indice_de_prueba(tmp_path):
    """Un índice con un libro gordo de un organismo pequeño y muchas hojas de uno grande."""
    import json
    import sqlite3

    db = tmp_path / "i.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE chunks (data TEXT)")
    filas = []
    # un solo documento troceado en 500 pedazos
    filas += [json.dumps({"org": "Editorial Gorda", "doc_id": "libro"}) for _ in range(500)]
    # veinte documentos de tres pedazos cada uno
    for i in range(20):
        filas += [json.dumps({"org": "NHS", "doc_id": f"nhs_{i}"}) for _ in range(3)]
    con.executemany("INSERT INTO chunks VALUES (?)", [(f,) for f in filas])
    con.commit()
    con.close()
    return db


def test_the_bodies_are_ranked_by_documents_not_by_how_fat_their_pdfs_are(tmp_path):
    from pedibot.ops.tweets import facts

    f = facts(ROOT, _indice_de_prueba(tmp_path))
    nombres = f["organisation_names"]
    assert nombres[0] == "NHS", (
        f"se ordena por grosor otra vez: {nombres}. Un libro de 500 trozos no representa al "
        "proyecto mejor que veinte hojas de un organismo de referencia."
    )
    assert f["organisations"] == 2


def test_an_unsigned_document_is_not_a_body_called_none(tmp_path):
    """Al pasar el campo por str(), un documento sin organismo se convertiría en uno llamado
    «None» y subiría el «18 organismos» del tuit sin que nadie hubiera añadido nada."""
    import json
    import sqlite3

    from pedibot.ops.tweets import facts

    db = tmp_path / "i.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE chunks (data TEXT)")
    con.executemany(
        "INSERT INTO chunks VALUES (?)",
        [(json.dumps({"org": "NHS", "doc_id": "a"}),), (json.dumps({"doc_id": "b"}),)],
    )
    con.commit()
    con.close()
    f = facts(ROOT, db)
    assert f["organisations"] == 1
    assert "None" not in f["organisation_names"]


def test_the_real_sheet_leads_with_the_bodies_a_reader_would_recognise():
    """Sobre el corpus de verdad: el candado del arreglo. No se pide un orden exacto —cambiará al
    ingerir— sino que los que aportan más documentos estén, que es lo que dice la frase."""
    from pedibot.ops.tweets import facts

    f = facts(ROOT, ROOT / "index" / "pedibot.db")
    nombres = set(f["organisation_names"])
    for esperado in ("NHS", "WHO", "MedlinePlus", "CDC"):
        assert esperado in nombres, f"{esperado} no llega a la hoja de datos: {sorted(nombres)}"


def test_se_puede_pedir_una_tanda_mayor() -> None:
    """El semanal son siete; el operador pidió diez el 16-sep y la cifra no puede ser un
    constante escondido. Con tope, que veinte mensajes seguidos a Telegram son un castigo."""
    import importlib.util
    import pathlib

    ruta = pathlib.Path(__file__).resolve().parents[1] / "ops" / "weekly_tweets.py"
    spec = importlib.util.spec_from_file_location("weekly_tweets", ruta)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.how_many([]) == 7
    assert m.how_many(["--n", "10"]) == 10
    assert m.how_many(["--n", "0"]) == 1
    assert m.how_many(["--n", "99"]) == 20
    assert m.how_many(["--dry-run"]) == 7


# ── enlaces (petición del operador, 16-sep-2026) ─────────────────────────────
def _hechos_con_enlaces():
    from pedibot.ops.tweets import facts
    from pedibot.settings import ROOT

    return facts(ROOT, ROOT / "index" / "pedibot.db")


def test_un_enlace_de_la_lista_pasa():
    """El operador pidió que algunos tuits lleven enlace al tema del que hablan."""
    from pedibot.ops.tweets import problems

    f = _hechos_con_enlaces()
    assert f["links"], "la hoja de datos no ofrece ninguna página que enlazar"
    url = f["links"][0].split(" — ")[0]
    assert problems(f"Every statement in a guide names the document it came from. {url}", f) == []


def test_un_enlace_inventado_se_tira():
    """Una dirección inventada desde la cuenta de una web sanitaria no se puede retirar después."""
    from pedibot.ops.tweets import problems

    f = _hechos_con_enlaces()
    malos = problems("Read more at https://pedibot.xyz/guides/this-does-not-exist", f)
    assert any("no está en la lista" in x for x in malos), malos


def test_dos_enlaces_no():
    from pedibot.ops.tweets import problems

    f = _hechos_con_enlaces()
    a, b = (x.split(" — ")[0] for x in f["links"][:2])
    assert any("enlaces" in x for x in problems(f"Mira {a} y {b}", f))


def test_el_enlace_va_al_final():
    from pedibot.ops.tweets import problems

    f = _hechos_con_enlaces()
    url = f["links"][0].split(" — ")[0]
    fallos = problems(f"En {url} lo explicamos con sus fuentes.", f)
    assert any("al final" in x for x in fallos), fallos


def test_nombrar_el_sitio_sin_enlace_tampoco():
    from pedibot.ops.tweets import problems

    f = _hechos_con_enlaces()
    assert problems("Everything is on pedibot.xyz", f)
