"""La prueba del vaso, en las ocho lenguas y en las dos direcciones (9-sep-2026).

`petechiae_fever` es la regla de la sepsis meningocócica. El padre que acaba de apretar un vaso
contra la piel de su hijo y ve que las manchas siguen ahí es el caso con menos margen de tiempo
de todo el sistema.

Ensanchar el cruce entre las guías y el triaje a los once signos de alarma —hasta entonces sólo
se había barrido la respiración— dio esto en la primera pantalla: de las siete advertencias
alemanas que describen la prueba del vaso, **las siete** salían rutina.

    «Ein Ausschlag, der nicht verblasst, wenn Sie ihn mit einem Glas andrücken»   → rutina

La regla tenía doce patrones alemanes y ninguno llevaba **verblassen**, que es el verbo con el
que lo dicen el NHS, el RKI y las siete guías del proyecto. Los doce decían «verschwinden» o
«weg gehen», que también se dice — y es exactamente lo que yo escribía al probar, por lo que los
barridos anteriores pasaban. Lo mismo en francés («s'estomper», que no estaba) y en hindi, donde
las guías dicen «गायब» y los patrones decían «मिट», con la negación en «न» y no en «नहीं».

La mitad de abajo de este fichero pesa igual: el resultado BUENO de la prueba —las manchas sí
desaparecen— tiene que quedarse en rutina. Un padre que hace la comprobación que le pedimos y
recibe una alarma roja por el resultado tranquilizador aprende a no volver a hacerla.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: Cada lengua, dicha por la guía y dicha por un padre. Las dos formas van juntas a propósito:
#: escribir los patrones leyendo sólo a una de las dos es cómo se llegó al agujero alemán.
NO_DESAPARECEN = [
    ("de", "guía", "Ein Ausschlag, der nicht verblasst, wenn Sie ihn mit einem Glas andrücken"),
    ("de", "padre", "der Ausschlag verblasst nicht"),
    ("de", "padre", "die Flecken gehen nicht weg wenn ich drücke"),
    ("es", "guía", "Una erupción que no desaparece al presionar con un vaso"),
    ("es", "padre", "las manchas no desaparecen cuando aprieto"),
    ("en", "guía", "A rash that does not fade when you press a glass against it"),
    ("en", "padre", "the rash does not fade when I press it"),
    ("fr", "guía", "Une éruption qui ne s'estompe pas quand on appuie un verre dessus"),
    ("fr", "padre", "les taches ne disparaissent pas quand j'appuie"),
    ("pt", "guía", "Manchas que não desaparecem quando você pressiona"),
    ("ru", "guía", "Сыпь, которая не бледнеет при надавливании"),
    ("ar", "guía", "طفح لا يختفي عند الضغط عليه"),
    ("hi", "guía", "ऐसे धब्बे जो दबाने पर गायब न हों"),
    ("hi", "padre", "दबाने पर दाने नहीं मिट रहे"),
]

#: El resultado tranquilizador. Si esto alarma, el padre deja de hacer la prueba.
SI_DESAPARECEN = [
    ("de", "der Ausschlag verblasst wenn ich mit einem Glas drücke"),
    ("de", "die Flecken verblassen beim Drücken"),
    ("de", "der Ausschlag verschwindet wenn ich drücke"),
    ("fr", "l'éruption s'estompe quand j'appuie avec un verre"),
    ("fr", "les taches disparaissent quand j'appuie"),
    ("es", "las manchas desaparecen cuando aprieto"),
    ("en", "the rash fades when I press it"),
    ("hi", "दबाने पर धब्बे गायब हो जाते हैं"),
    ("pt", "as manchas somem quando eu aperto"),
]


@pytest.mark.parametrize(("lang", "quien", "texto"), NO_DESAPARECEN)
def test_las_manchas_que_no_desaparecen_son_emergencia(
    triage: Triage, lang: str, quien: str, texto: str
) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "emergency", f"[{lang}/{quien}] «{texto}» → {resultado.level}"
    assert any(r.id == "petechiae_fever" for r in resultado.matched), (
        f"[{lang}/{quien}] salta, pero por otra regla: "
        f"{[r.id for r in resultado.matched]}"
    )


@pytest.mark.parametrize(("lang", "texto"), SI_DESAPARECEN)
def test_las_manchas_que_si_desaparecen_no_alarman(
    triage: Triage, lang: str, texto: str
) -> None:
    assert triage.assess(texto).level != "emergency", f"[{lang}] «{texto}» alarma"
