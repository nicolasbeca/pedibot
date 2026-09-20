"""La cinta del brazo, que es como se mide la desnutrición donde va esto (20-sep-2026).

El sitio ya calculaba el peso para la talla con las tablas de la OMS. Eso sirve **si hay una
báscula y un tallímetro**. En media África lo que hay es una cinta de papel: el agente de salud
comunitario, y muchas veces la propia madre, mide el brazo y lee un color. Es el método que la
OMS recomienda para cribar en la comunidad y no estaba aquí.

Lo que este fichero fija, de más grave a menos:

1. **Los tres cortes son los de la guía y no se tocan**: 115 y 125 mm. Un número movido aquí es
   un niño grave leído como moderado.
2. **Centímetros y milímetros no se confunden.** Las cintas vienen marcadas en las dos y los
   padres copian lo que ven. «11,5 cm» y «115 mm» son lo mismo; «11,5» y «115» no.
3. **Fuera de 6 a 59 meses no hay respuesta**, porque fuera de ahí esos cortes no existen. Un
   corte llevado a una edad para la que no se calculó es peor que no tener corte.
4. **Un golpe en el brazo no es esto.** «Se dio un golpe y tiene un chichón de 3 cm» trae la
   palabra y trae la medida.
"""

from __future__ import annotations

import pytest

from pedibot.bot.muac import (
    MODERATE_MM,
    SEVERE_MM,
    assess,
    explain,
    is_muac_question,
    read_mm,
)

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi", "sw")


def test_los_cortes_son_los_de_la_guia() -> None:
    """115 y 125 mm, de la guía de la OMS de 2013. Si alguien los mueve, que sea a propósito."""
    assert SEVERE_MM == 115.0
    assert MODERATE_MM == 125.0


@pytest.mark.parametrize(
    ("mm", "franja"),
    [
        (90, "severe"),
        (114, "severe"),
        (114.9, "severe"),
        (115, "moderate"),
        (120, "moderate"),
        (124.9, "moderate"),
        (125, "ok"),
        (140, "ok"),
    ],
)
def test_cada_medida_cae_donde_dice_la_guia(mm: float, franja: str) -> None:
    r = assess(mm, 24)
    assert r is not None and r.band == franja


def test_el_rojo_y_el_amarillo_mandan_ir_hoy() -> None:
    """Las dos franjas necesitan tratamiento; sólo la tercera es rutina."""
    assert assess(100, 24).level == "urgent"
    assert assess(120, 24).level == "urgent"
    assert assess(130, 24).level == "routine"


@pytest.mark.parametrize(
    ("edad", "hay"), [(5, False), (6, True), (24, True), (59, True), (60, False)]
)
def test_fuera_del_rango_de_la_guia_no_hay_respuesta(edad: float, hay: bool) -> None:
    assert (assess(110, edad) is not None) is hay


@pytest.mark.parametrize(
    ("texto", "mm"),
    [
        ("el brazo le mide 11,5 cm", 115.0),
        ("his arm measures 11 cm", 110.0),
        ("MUAC 118 mm", 118.0),
        ("محيط الذراع 10 سم", 100.0),
        ("mkono wake ni sentimita 11", 110.0),
        ("बाजू की माप 11 सेमी है", 110.0),
        ("окружность плеча 11 см", 110.0),
        ("son bras mesure 10,5 cm", 105.0),
    ],
)
def test_la_medida_se_lee_en_su_unidad_y_en_su_alfabeto(texto: str, mm: float) -> None:
    """La diferencia entre centímetros y milímetros es la diferencia entre un niño grave y uno
    sano. La unidad se lee siempre; no se supone nunca."""
    assert is_muac_question(texto)
    assert read_mm(texto) == mm


@pytest.mark.parametrize(
    "texto",
    [
        "se dio un golpe en el brazo y tiene un chichón de 3 cm",
        "he broke his arm, it is swollen 4 cm",
        "le duele el brazo",
        "mi hijo mide 85 cm",
        "pesa 11 kg",
    ],
)
def test_lo_que_no_es_la_cinta_no_lo_parece(texto: str) -> None:
    assert not is_muac_question(texto), f"se ha leído como la cinta: «{texto}»"


def test_un_numero_imposible_no_se_lee() -> None:
    """Un brazo de niño está entre 7 y 25 cm. Fuera de ahí hay un error de unidad o un número
    mal copiado, y adivinar cuál de los dos sería inventar."""
    assert read_mm("el brazo le mide 3 cm") is None
    assert read_mm("MUAC 900 mm") is None


@pytest.mark.parametrize("lang", IDIOMAS)
def test_la_lectura_esta_escrita_en_las_nueve_lenguas(lang: str) -> None:
    texto = explain(assess(100, 24), lang)
    assert texto and "{" not in texto, f"plantilla sin rellenar en {lang}: {texto[:90]}"
    assert "115" in texto, "la lectura tiene que decir el corte del que habla"
    assert "who.int" in texto, "y de dónde sale"


def test_el_verde_no_dice_que_el_nino_este_bien() -> None:
    """La cinta criba, no diagnostica. 125 mm o más dice que esa medida no cae en las dos
    franjas de la guía, que es distinto de decir que está bien alimentado."""
    texto = explain(assess(140, 24), "es")
    assert "no cae" in texto
    assert "hoy a un centro de salud" not in texto


def test_el_motor_la_usa() -> None:
    """De nada sirve la herramienta si la rama no está enchufada."""
    from pedibot.bot.answer import is_muac_question as enchufada

    assert enchufada("el brazo le mide 11 cm")


@pytest.mark.parametrize("lang", IDIOMAS)
def test_el_aviso_rojo_dice_por_que(lang: str) -> None:
    """20-sep-2026, en vivo: la respuesta salía marcada urgente y **sin recuadro rojo**.

    El aviso lo construye el triaje a partir de las reglas que han saltado, y aquí no ha saltado
    ninguna: el mensaje del padre no trae un síntoma, trae una medida. Sin un motivo propio, una
    urgencia se quedaba sin lo primero que se mira.
    """
    from pedibot.bot.muac import reason

    assert reason(assess(100, 24), lang), f"sin motivo en {lang}"
    assert reason(assess(120, 24), lang)
    assert reason(assess(140, 24), lang) == "", "la franja verde no lleva aviso"


@pytest.mark.parametrize(
    ("lang", "unidad"), [("ar", "مم"), ("hi", "मिमी"), ("ru", "мм"), ("es", "mm")]
)
def test_la_unidad_va_en_el_alfabeto_del_lector(lang: str, unidad: str) -> None:
    """«100 mm» dentro de una frase en árabe dice, en cada línea, que el texto no es para ti."""
    texto = explain(assess(100, 24), lang)
    assert f"100 {unidad}" in texto, texto.split("\n")[0]
