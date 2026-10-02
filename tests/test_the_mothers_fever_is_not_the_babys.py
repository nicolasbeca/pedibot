"""La fiebre de la madre no es la del bebé (2-oct-2026).

Comprobado en vivo: «tengo fiebre y estoy dando el pecho a mi bebé de 2 meses, ¿puedo seguir?»
sacaba el aviso rojo «acudir a urgencias hoy — bebé menor de 3 meses con fiebre». La regla
juntaba «bebé de 2 meses» y «fiebre» sin mirar de quién era la fiebre. El 30-sep se quitó la
frase de cabecera para este caso (`fiebre_del_adulto`), pero no el aviso del triaje, que es lo
que más asusta. Una falsa alarma enseña a no hacer caso de las verdaderas.

La otra mitad importa igual: si el bebé TAMBIÉN tiene fiebre, el aviso sale.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


def _infant_rule(a) -> bool:
    return bool(a.banner) and a.level == "urgent"


@pytest.mark.parametrize(
    "q,lang",
    [
        ("tengo fiebre y estoy dando el pecho a mi bebé de 2 meses, ¿puedo seguir?", "es"),
        ("I have a fever and I'm breastfeeding my 6 week old baby, can I carry on?", "en"),
        ("estoy con fiebre, ¿puedo dar el pecho a mi bebé de un mes?", "es"),
        ("j'ai de la fièvre et j'allaite mon bébé de 2 mois", "fr"),
    ],
)
def test_the_mothers_fever_does_not_raise_the_infant_alarm(engine, q, lang):
    a = engine.ask(q, country="ES", lang=lang)
    assert not _infant_rule(a), a.banner


@pytest.mark.parametrize(
    "q,lang",
    [
        ("mi bebé de 2 meses tiene fiebre", "es"),
        ("tengo un bebé de 2 meses con fiebre", "es"),
        ("tengo fiebre y mi bebé de 2 meses también tiene fiebre", "es"),
        ("I have a fever and my 6 week old baby has a fever too", "en"),
    ],
)
def test_the_babys_fever_still_raises_it(engine, q, lang):
    a = engine.ask(q, country="ES", lang=lang)
    assert _infant_rule(a), a.text[:200]
