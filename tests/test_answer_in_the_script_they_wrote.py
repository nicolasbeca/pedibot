"""Si el padre escribe en letras latinas, la respuesta va en letras latinas (23-sep-2026).

De las 500 de la séptima tanda, siete respuestas salieron en un alfabeto que el padre no había
usado. Las peores:

    «my baby has bukhar and is very sleepy, what do i do?»      → respuesta en urdu, en árabe
    «bachay ko bukhar hai aur doodh kam pee raha hai»           → respuesta en urdu, en árabe
    «bukhar hai lekin thermometer nahi funciona, kya karu?»     → respuesta en devanagari

Media India y medio Pakistán escriben su lengua en teclado latino; eso ya lo sabía este proyecto
—la tabla de sinónimos tiene las formas romanizadas desde agosto— y la respuesta se iba igual en
un alfabeto que quien pregunta a lo mejor no lee. Un padre que escribe «bukhar» en letras
latinas puede no saber leer nastaliq.

La regla es de código y no de modelo: se mira lo que escribió el padre y se le pide al redactor
la misma escritura.
"""

from __future__ import annotations

from pedibot.bot.answer import escritura_latina


def test_it_knows_the_latin_alphabet() -> None:
    assert escritura_latina("bachay ko bukhar hai aur doodh kam pee raha hai")
    assert escritura_latina("my baby has bukhar and is very sleepy")
    assert escritura_latina("mtoto wangu ana homa lakini anakula vizuri")
    assert escritura_latina("mi hijo tiene fiebre")


def test_it_knows_the_others() -> None:
    assert not escritura_latina("بچے کو بخار ہے")
    assert not escritura_latina("मेरे बच्चे को बुखार है")
    assert not escritura_latina("ребёнок кашляет и тяжело дышит")
    assert not escritura_latina("طفلي عنده حرارة")


def test_a_mix_counts_as_the_one_that_weighs_more() -> None:
    # «bukhar hai lekin thermometer nahi funciona» es latino con una palabra prestada
    assert escritura_latina("bukhar hai lekin thermometer nahi funciona, kya karu?")
    # y al revés: una palabra inglesa dentro de una frase en devanagari no la vuelve latina
    assert not escritura_latina("मेरे बच्चे को fever है और वह सुस्त है")


def test_the_writer_is_told_which_script_to_use() -> None:
    """Y el motor se lo dice al redactor, que es donde esto sirve de algo."""
    from test_the_ai_reads_the_question_first import _json, _motor

    motor, visto = _motor(_json(lang="ur", lang_name="Urdu"))
    motor.ask("bachay ko bukhar hai aur doodh kam pee raha hai", lang="en")
    pedido = " ".join(visto["redactor"])
    assert "Latin" in pedido, pedido
