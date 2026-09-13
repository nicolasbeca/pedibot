"""El bebé amarillo (13-sep-2026).

Salía como **rutina en las ocho lenguas** —«mi recién nacido está amarillo», «रضيعي لونه أصفر»,
«नवजात को पीलिया है»— y la batería de árabe e hindi lo dejó anotado: no había una ficha para padres
detrás, sólo un manual clínico. Ahora la hay: la página del NHS «Jaundice in babies» dice que un bebé
con la piel o los ojos amarillos después de las 24 horas necesita cita urgente ese día, y que antes de
las 24 horas, o con somnolencia, sin comer, con fiebre o sin pañales mojados, es una emergencia.

La regla sale urgente, y el motivo dice cuándo es emergencia. Y lo que NO puede disparar importa
tanto como lo que sí: la caca amarilla y grumosa es lo normal en un bebé de pecho, y los mocos
amarillos son mocos. Un aviso que salta con el pañal de todos los días se deja de leer.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


AMARILLO = [
    ("en", "my newborn looks yellow"),
    ("en", "the whites of my baby's eyes are yellow"),
    ("en", "I think my baby has jaundice"),
    ("es", "mi recién nacido está amarillo"),
    ("es", "mi bebé tiene la piel amarillenta"),
    ("es", "creo que mi bebé tiene ictericia"),
    ("fr", "mon bébé a la peau jaune"),
    ("fr", "mon nouveau-né a une jaunisse"),
    ("de", "unser Baby hat Gelbsucht"),
    ("de", "die Haut meines Neugeborenen ist gelb"),
    ("ru", "у новорождённого желтуха"),
    ("ru", "у малыша пожелтела кожа"),
    ("ar", "رضيعي حديث الولادة لونه أصفر"),
    ("ar", "عيون طفلي الرضيع صفراء"),
    ("ar", "مولودي عنده يرقان"),
    ("pt", "o meu recém-nascido está amarelo"),
    ("pt", "o bebê está com icterícia"),
    ("hi", "नवजात बच्चे को पीलिया है"),
    ("hi", "मेरे शिशु की त्वचा पीली पड़ गई है"),
]

NO_ES_ICTERICIA = [
    "la caca de mi bebé es amarilla y con grumos",
    "my breastfed baby's poo is yellow and seedy",
    "o cocô do bebê está amarelo",
    "mi bebé tiene mocos amarillos",
    "my baby has yellow snot",
    "ابني عنده مخاط أصفر",
    "बच्चे की पॉटी पीली है",
    "le bébé a vomi du lait jaune",
    "mein Baby hat gelben Stuhl",
    "у малыша жёлтый стул",
]


@pytest.mark.parametrize(("lang", "texto"), AMARILLO)
def test_el_bebe_amarillo_no_es_rutina(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    assert r.level != "routine", f"«{texto}» ({lang}) sale como rutina"
    assert "neonatal_jaundice" in [m.id for m in r.matched], [m.id for m in r.matched]


@pytest.mark.parametrize("texto", NO_ES_ICTERICIA)
def test_la_caca_y_los_mocos_amarillos_no_son_ictericia(triaje: Triage, texto: str):
    r = triaje.assess(texto)
    assert "neonatal_jaundice" not in [m.id for m in r.matched], f"falso positivo: «{texto}»"


def test_cita_la_ficha_del_nhs_y_dice_cuando_es_emergencia(triaje: Triage):
    r = triaje.assess("my newborn looks yellow")
    regla = next(m for m in r.matched if m.id == "neonatal_jaundice")
    assert regla.source == "nhs_en_jaundice_in_babies"
    assert r.level == "urgent"
    for lang in ("es", "en", "fr", "de", "ru", "ar", "pt", "hi"):
        motivo = r.reasons(lang)[[m.id for m in r.matched].index("neonatal_jaundice")]
        assert "24" in motivo, f"{lang}: el motivo no dice lo de las 24 horas: {motivo}"


def test_la_ficha_esta_en_el_catalogo():
    import yaml

    cat = yaml.safe_load((ROOT / "config/fuentes_web.yaml").read_text(encoding="utf-8"))["sources"]
    assert "nhs_en_jaundice_in_babies" in {d["doc_id"] for d in cat}
