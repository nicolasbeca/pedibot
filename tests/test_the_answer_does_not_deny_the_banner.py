"""El texto no puede negar el número que el aviso está dando (20-sep-2026).

Probado contra el sitio vivo, con país Nigeria y un niño atragantado. Lo que llegó a la pantalla,
entero, en este orden:

    🚨 Call 112 now or go to the emergency department.
       Reason: Choking with breathing difficulty

    I can't give you an emergency number — that depends on the country you are in, and my
    sources only mention the number for Spain.

El aviso es nuestro y es determinista: sale de la tabla de 90 países y va en el idioma del
lector. El texto es del modelo, que estaba obedeciendo la regla de no mandar a nadie a un
servicio que sólo existe donde se escribió la fuente… y **explicándola en voz alta**.

Las dos cosas juntas son peores que cualquiera por separado. En la peor noche posible, el padre
lee un número y, debajo, que no hay número. Y de paso se entera de cómo está hecho esto por
dentro en vez de leer sobre su hijo.

El prompt lo prohíbe desde hoy. Esto es el candado, que es lo que de verdad lo impide: si el
texto niega tener un número, la respuesta se rechaza y se vuelve a escribir.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import denies_the_number_problem

#: La frase de producción, y su forma en cada lengua del sitio.
NIEGAN = [
    "I can't give you an emergency number — that depends on the country you are in, and my "
    "sources only mention the number for Spain.",
    "I cannot provide an emergency number for your country.",
    "I am not able to give you a number, sorry.",
    "My sources only mention the number for Spain.",
    "No puedo darte un número de urgencias: depende del país en el que estés.",
    "Mis fuentes sólo mencionan el número de España.",
    "Je ne peux pas donner un numéro d'urgence, cela dépend de votre pays.",
    "Ich kann Ihnen keine Notrufnummer nennen.",
    "Я не могу дать номер экстренной службы.",
    "لا أستطيع إعطاء رقم الطوارئ في بلدك.",
    "Não posso dar um número de emergência.",
]

#: Lo que sí puede escribir, y que no debe confundirse con lo anterior.
VALEN = [
    "Call your local emergency number now.",
    "Lay the child on their side and do not put anything in their mouth, according to the SEUP.",
    "Llama ahora a tu número de urgencias.",
    "Si el niño no respira, hay que actuar de inmediato, según la SEUP.",
    "There is no national emergency number in your country; go to the nearest health centre.",
    "I cannot tell you whether this is serious; a paediatrician can.",
]


@pytest.mark.parametrize("texto", NIEGAN)
def test_negar_el_numero_tumba_la_respuesta(texto: str) -> None:
    problema = denies_the_number_problem(texto)
    assert problema, f"esto contradice al aviso y ha pasado: «{texto}»"
    assert "denies_the_number" in problema


@pytest.mark.parametrize("texto", VALEN)
def test_lo_que_si_puede_decir_pasa(texto: str) -> None:
    """Dos de éstas están a un pelo de la frase prohibida y tienen que pasar.

    «No hay número nacional en tu país» es verdad en siete países y es exactamente lo que hay que
    decir allí. «No puedo decirte si esto es grave» es la honestidad del proyecto, no una
    contradicción. Un candado que también las tumbara haría callar lo que sí hay que decir.
    """
    assert denies_the_number_problem(texto) is None, (
        f"esto es correcto y se ha rechazado: «{texto}»"
    )


def test_el_guardian_esta_enchufado_a_la_verificacion() -> None:
    """De nada sirve el candado si nadie lo llama: aquí se comprueba que `verify_answer` lo usa."""
    from pedibot.bot.answer import verify_answer

    problemas = verify_answer(NIEGAN[0], [])
    assert any(p.startswith("denies_the_number") for p in problemas), problemas
