"""«Pesa 8 kg, ¿está bien?» tiene que llegar a la tabla de la OMS (20-sep-2026).

Probado contra el sitio vivo, con Kenia elegido:

    my son is 18 months and weighs 8 kg, is that ok?
    → «I can't tell from your son's weight alone whether it's okay…»

Ocho kilos a los dieciocho meses está **por debajo del percentil 3**, y la tabla que lo dice
estaba en el mismo servidor. Lo mismo en hindi con una niña de ocho meses y seis kilos, y en
árabe con una de un año y siete.

El lector de medidas funcionaba: sacaba el sexo y el peso de las tres frases, en sus tres
alfabetos. Lo que no se disparaba era la puerta, que pedía la palabra «percentil» o las dos
medidas en el mismo mensaje. **Un padre no dice «percentil». Dice «¿está bien?»**, y lo dice en
todos los idiomas.

Lo que este fichero protege por el otro lado, que es igual de importante: que una medida a secas
NO abra la curva. «Pesa 13 kg, ¿cuánto paracetamol?» es una dosis, y responderle con un percentil
sería contestar a otra pregunta.
"""

from __future__ import annotations

import pytest

from pedibot.bot.growth import asks_if_a_measure_is_normal, measurements

#: La misma pregunta en los nueve idiomas del motor. Todas traen una medida y todas preguntan si
#: está bien: es la forma en que se pregunta esto cuando no se sabe la palabra «percentil».
PREGUNTAN = [
    ("en", "my son is 18 months and weighs 8 kg, is that ok?"),
    ("en", "she weighs 6 kg at 8 months, is that normal?"),
    ("en", "he is 2 years old and weighs 9 kg, is that too little?"),
    ("es", "mi hijo de 18 meses pesa 8 kg, ¿está bien?"),
    ("es", "mi niña pesa 6 kg con 8 meses, ¿es normal?"),
    ("fr", "mon fils pèse 8 kg à 18 mois, est-ce normal ?"),
    ("de", "er wiegt 8 kg mit 18 monaten, ist das normal?"),
    ("ru", "ему 18 месяцев и он весит 8 кг, это нормально?"),
    ("ar", "ابنتي عمرها سنة ووزنها 7 كيلو، هل هذا طبيعي؟"),
    ("pt", "o meu filho pesa 8 kg aos 18 meses, é normal?"),
    ("hi", "मेरी बेटी 8 महीने की है और उसका वज़न 6 किलो है, क्या यह ठीक है?"),
]

#: Lo que trae un número y NO es esta pregunta.
#: El suajili escribe la unidad delante —«kilo 8»— y el lector de peso todavía espera el número
#: primero. Queda anotado aquí, sin disfrazarlo: la lengua entra por la capa de seguridad y el
#: lector de medidas es lo siguiente que le toca.
PENDIENTE_SUAJILI = "mwanangu ana miezi 18 na uzito wa kilo 8, ni sawa?"

NO_PREGUNTAN = [
    "pesa 13 kg, ¿cuánto paracetamol le doy?",
    "how much ibuprofen for 12 kg?",
    "mi hijo tiene fiebre, ¿está bien?",
    "¿está bien darle ibuprofeno a un bebé de 2 meses?",
    "is it ok to bathe him with a fever?",
    "mide 92 cm",
]


@pytest.mark.parametrize(
    ("lang", "texto"), PREGUNTAN, ids=[f"{lg}-{i}" for i, (lg, _) in enumerate(PREGUNTAN)]
)
def test_la_pregunta_llega_a_la_tabla(lang: str, texto: str) -> None:
    assert asks_if_a_measure_is_normal(texto), f"[{lang}] no se ha reconocido: «{texto}»"


@pytest.mark.parametrize("texto", NO_PREGUNTAN)
def test_un_numero_suelto_no_abre_la_curva(texto: str) -> None:
    """«Pesa 13 kg, ¿cuánto paracetamol?» es una dosis. Contestar un percentil ahí es contestar
    a otra pregunta, y este proyecto no hace eso."""
    assert not asks_if_a_measure_is_normal(texto), f"se ha leído como crecimiento: «{texto}»"


def test_sin_medida_no_hay_nada_que_mirar() -> None:
    """«¿Está bien?» a secas puede ser cualquier cosa: sin número no hay fila en la tabla."""
    assert not asks_if_a_measure_is_normal("¿está bien?")
    assert not asks_if_a_measure_is_normal("is that normal?")


@pytest.mark.parametrize(
    ("lang", "texto"), PREGUNTAN, ids=[f"{lg}-{i}" for i, (lg, _) in enumerate(PREGUNTAN)]
)
def test_y_el_sexo_y_la_medida_se_leen_de_la_misma_frase(lang: str, texto: str) -> None:
    """De nada sirve abrir la puerta si detrás no hay datos: la curva de una niña no es la de un
    niño, y sin sexo no hay curva."""
    sexo, kg, cm = measurements(texto)
    assert kg is not None or cm is not None, f"[{lang}] sin medida: «{texto}»"
    assert sexo in ("m", "f"), f"[{lang}] sin sexo: «{texto}»"


def test_el_suajili_con_la_unidad_delante_sigue_pendiente() -> None:
    """«uzito wa kilo 8» es como se dice en suajili, y el lector espera «8 kilo».

    Esto no es un test que aprueba un fallo: es el fallo escrito, con su frase, para que el día
    que se arregle el lector de peso esta prueba se caiga y alguien venga a quitarla.
    """
    from pedibot.bot.growth import measurements

    _, kg, _ = measurements(PENDIENTE_SUAJILI)
    assert kg is None, "¡arreglado! quita esta prueba y mete la frase en PREGUNTAN"


# ── cómo se escribe el resultado ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (0.3, "0.3rd"),
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (9, "9th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (50, "50th"),
        (91, "91st"),
        (99.6, "99.6th"),
    ],
)
def test_el_ordinal_ingles_se_escribe_como_en_las_curvas(valor: float, esperado: str) -> None:
    """Decía «2th percentile» y «0.3th». Las curvas publicadas escriben «2nd» y «0.4th centile».

    Sale en cada respuesta de crecimiento en inglés, que es la lengua con la que este sitio
    llega a Kenia, Nigeria, Ghana y la India.
    """
    from pedibot.bot.growth import _ordinal_en

    assert _ordinal_en(valor) == esperado


@pytest.mark.parametrize(
    ("lang", "unidad"), [("ar", "كغ"), ("hi", "किग्रा"), ("ru", "кг"), ("es", "kg"), ("en", "kg")]
)
def test_la_unidad_se_escribe_en_el_alfabeto_del_lector(lang: str, unidad: str) -> None:
    """«6 kg» dentro de una frase en hindi dice, en cada línea, que el texto no es para ti.

    El kilogramo es un símbolo del SI y no se traduce en las lenguas latinas; el árabe, el hindi
    y el ruso sí tienen el suyo.
    """
    from pedibot.bot.growth import Growth, explain
    from pedibot.settings import ROOT

    g = Growth(ROOT / "config" / "who_growth.json")
    texto = explain(g.assess("f", 12, weight_kg=7.0), lang, "f", 12)
    assert f"7 {unidad}" in texto, texto[:160]
