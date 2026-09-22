"""Las falsas alarmas de las 854 preguntas del 22-sep-2026.

Pasadas por el triaje en seco, 59 de las 854 daban aviso. Diecisiete estaban mal, y no de una
manera inocente: un bebé de ocho meses que «no responde siempre cuando le llamamos por su
nombre» —la pregunta con la que empieza la sospecha de sordera o de autismo, y que un padre hace
con miedo— recibía **emergencia, llama a una ambulancia**. Un bebé de once meses que vomita a
veces después del huevo recibía el aviso de un trastorno de la conducta alimentaria.

Un aviso que salta donde no toca no es prudencia: es la manera de que el aviso que sí importa no
se lea. Cada línea de aquí es una de ésas, y debajo está la de verdad que tiene que seguir
saltando.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

TRIAJE = Triage(ROOT / "config" / "red_flags.yaml")

#: (pregunta, qué regla saltaba)
FALSAS = [
    ("bebe de 8 meses que no responde siempre cuando le llamamos por su nombre", "not_responding"),
    (
        "mi bebe de 11 meses vomita despues de comer huevo pero solo algunas veces",
        "eating_disorder",
    ),
    ("mi bebe vomita leche cuajada una hora despues de comer", "eating_disorder"),
    ("mi hija vomita solo cuando corre despues de comer", "eating_disorder"),
    (
        "mi bebe tiene 2 meses y medio y no sonrie cuando le hablo pero si cuando ve la lampara",
        "drowsy_irritable",
    ),
    ("mi hijo se despierta con la boca seca todos los dias", "dehydration"),
    ("bebe que rechaza el agua pero toma pecho bien", "dehydration"),
    ("mi hijo tiene miedo al perro de los vecinos aunque nunca le ha mordido", "mammal_bite"),
    ("mi hija hace caca con moco pero sin sangre", "blood_in_stool"),
    ("mi hija toma hierro y sus cacas estan casi negras", "blood_in_stool"),
    ("mi bebe tiene un bulto pequeño detras de la oreja desde hace semanas", "mastoiditis"),
    ("mi hijo tiene una costra amarilla en la nariz que no se quita", "foreign_body_nose_or_ear"),
    ("mi hijo ha estado en la piscina y ahora tiembla pero no tiene fiebre", "heatstroke"),
    ("mi bebe ha tomado un biberon que llevaba dos horas fuera", "poisoning"),
    (
        "mi hijo se tira al suelo y deja de respirar unos segundos cuando llora muchisimo",
        "severe_breathing",
    ),
    ("mi bebe se pone rigido durante unos segundos cuando esta muy excitado", "seizure"),
    ("mi hijo se ha atragantado con pan pero ahora esta normal", "choking"),
    (
        "tiene 6 semanas y cuando le doy el biberon hace como que se atraganta pero luego sigue comiendo normal",
        "choking",
    ),
    ("mi bebe tuvo fiebre hace una semana y ahora tiene granitos por el cuerpo", "infant_fever"),
    ("mi hijo se ha quemado con el sol en los hombros", "burn"),
]

DE_VERDAD = [
    "mi bebe de 3 meses no responde, esta flojo y no reacciona cuando le hablo",
    "mi hijo tiene fiebre y las manos y los pies muy frios",
    "le ha mordido un perro en la cara y sangra",
    "mi hija hace caca con sangre roja desde ayer",
    "mi bebe esta hinchado detras de la oreja, rojo y con fiebre, y la oreja se le despega",
    "mi hijo ha bebido lejia sin querer",
    "mi hijo se esta atragantando ahora con una uva y no puede respirar",
    "mi bebe de 2 meses tiene 38.5 de fiebre",
    "mi hija se ha quemado con agua hirviendo y le ha salido una ampolla grande",
    "mi hijo ha estado al sol todo el dia, vomita y esta confuso",
    "lleva 8 horas sin hacer pis, no tiene lagrimas y esta muy dormido",
    "mi hijo se ha quedado rigido, con sacudidas, y no responde",
]


@pytest.mark.parametrize("q,regla", FALSAS, ids=[r for _, r in FALSAS])
def test_it_does_not_ring(q: str, regla: str) -> None:
    r = TRIAJE.assess(q)
    assert r.level == "routine", f"{regla}: {[x.id for x in r.matched]}"


@pytest.mark.parametrize("q", DE_VERDAD)
def test_the_real_one_still_rings(q: str) -> None:
    assert TRIAJE.assess(q).level != "routine", q
