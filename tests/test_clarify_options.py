"""Los botones que ofrecemos nosotros tienen que llevar a alguna parte (9-sep-2026).

Cuando la primera pregunta es demasiado vaga, el bot ofrece siete opciones —«Fiebre», «Tos o
respiración», «Golpe o caída»…— para que el padre concrete. Nadie había pulsado esos botones.

De las 56 combinaciones de opción × idioma, **once acababan en «no tengo información fiable
sobre esto»**, que es lo peor que se puede contestar a alguien que acaba de pulsar exactamente
lo que le ofreciste:

  · «Golpe o caída» en ruso, árabe y portugués — las tablas de sinónimos tenían el VERBO
    («упал», «سقط», «caiu») y el botón dice el SUSTANTIVO («Падение», «سقوط», «queda»). El
    buscador casa por prefijo, y «падение» no empieza por «упал». La familia de la L64, ahora
    en los sinónimos en vez de en el triaje.
  · «Otra cosa», en los ocho. Y ésa no es un fallo de vocabulario: es una meta-opción, el botón
    que dice «nada de lo de arriba». Buscarla en el corpus no puede devolver nada. Lo que toca
    es preguntar, y eso es lo que hace ahora.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import CLARIFY_OPTIONS, DESCRIBE_IT
from pedibot.eval import fake_engine_from_settings

IDIOMAS = tuple(CLARIFY_OPTIONS)


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


@pytest.mark.parametrize(
    ("lang", "opcion"),
    [(lg, op) for lg, ops in CLARIFY_OPTIONS.items() for op in ops],
)
def test_every_button_leads_somewhere(engine, lang: str, opcion: str) -> None:
    """Ofrecer un botón y contestar «no sé» a quien lo pulsa es peor que no ofrecerlo."""
    a = engine.ask(opcion, lang=lang)
    assert a.verification != "no_source", (
        f"[{lang}] «{opcion}» acaba en «no tengo información fiable»"
    )


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_last_button_asks_instead_of_searching(engine, lang: str) -> None:
    """«Otra cosa» no es un síntoma: no se busca, se pregunta."""
    a = engine.ask(CLARIFY_OPTIONS[lang][-1], lang=lang)
    assert a.text == DESCRIBE_IT[lang]
    assert a.verification == "clarify"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_invitation_is_written_in_every_language(lang: str) -> None:
    assert DESCRIBE_IT[lang].strip(), f"[{lang}] sin texto"
    assert DESCRIBE_IT[lang] != DESCRIBE_IT["en"] or lang == "en", (
        f"[{lang}] se quedó con la versión inglesa"
    )


@pytest.mark.parametrize("lang", IDIOMAS)
def test_a_real_question_is_not_mistaken_for_the_button(engine, lang: str) -> None:
    """La comparación es exacta y con la lista de SU idioma: una pregunta de verdad que empiece
    parecido no puede acabar convertida en la invitación a contarlo."""
    a = engine.ask(CLARIFY_OPTIONS[lang][0], lang=lang)  # «Fiebre», el primero
    assert a.text != DESCRIBE_IT[lang]
