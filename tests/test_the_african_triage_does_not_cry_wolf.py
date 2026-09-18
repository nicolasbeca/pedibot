"""Y la otra mitad de la fase 2 de África: lo corriente sigue siendo corriente (18-sep-2026).

Nueve reglas nuevas en una tarde. L175 dice que después de ensanchar hay que medir por dónde se
sale, y al medirlo **catorce de estas treinta y cuatro frases saltaban de más**. Casi todas son
cosas que un padre dice de verdad:

· «le di agua de arroz para la diarrea» — el agua de arroz es un líquido casero que la propia OMS
  admite. Disparaba una emergencia de cólera, o sea: mandábamos a urgencias a quien lo estaba
  haciendo bien.
· «se pone rígido cuando hace fuerza para hacer caca» — el recién nacido que puja. Daba tétanos
  neonatal, y en realidad lo cazaba una regla vieja, la de la convulsión.
· «no puede mamar porque tengo mastitis» — quien no puede es la madre.
· «¿el sarampión puede dar úlceras en la boca?» — una pregunta, no un niño enfermo.
· «tiene las palmas manchadas de pintura blanca» — «blanco» no es «pálido».

Un aviso que salta de más hace dos daños: manda a urgencias a quien no lo necesita, y enseña al
padre a ignorar el rojo, que es el que algún día será de verdad.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: (idioma, qué trampa es, frase). Todas tienen que salir «routine».
TRAMPAS: list[tuple[str, str, str]] = [
    # ── el agua de arroz es un remedio, no sólo un síntoma
    ("es", "remedio casero", "le di agua de arroz para la diarrea, como me dijeron"),
    ("en", "remedio casero", "i gave him rice water to drink for the diarrhoea"),
    ("fr", "remedio casero", "je lui ai donné de l'eau de riz"),
    ("es", "pregunta", "se puede dar agua de arroz a un bebé con diarrea"),
    # ── «cólera» es también un enfado, en castellano y en portugués
    ("es", "cólera de enfado", "mi hijo tuvo un ataque de cólera y rompió un juguete"),
    ("pt", "cólera de enfado", "ele ficou com muita cólera quando tirei o tablet"),
    # ── el recién nacido que puja no tiene tétanos
    ("es", "pujos", "mi recién nacido se pone rígido cuando hace fuerza para hacer caca"),
    ("en", "pujos", "my newborn goes stiff when he strains to poo"),
    ("pt", "se despereza", "o recém-nascido fica rígido quando se espreguiça"),
    ("fr", "pujos", "le nouveau-né se raidit quand il fait ses selles"),
    # ── la respiración: información y normalidad
    ("es", "lo dijo el médico", "el médico dijo que 40 por minuto es normal a su edad"),
    ("en", "pregunta de normalidad", "is 50 breaths per minute normal for a newborn?"),
    ("es", "pregunta", "¿cuántas respiraciones por minuto debe hacer un bebé?"),
    ("es", "al correr", "cuando corre respira muy deprisa pero se le pasa enseguida"),
    # ── el paludismo: antecedente, prevención, vacuna, condicional
    ("es", "antecedente", "tuvo malaria el año pasado y se curó bien"),
    ("en", "antecedente", "my son had malaria two years ago and was very sleepy then"),
    ("en", "prevención", "how can I prevent malaria in my children"),
    ("es", "efecto de la vacuna", "¿la vacuna de la malaria da sueño?"),
    ("en", "viaje futuro", "what should we take if we travel to a malaria area next month"),
    ("es", "condicional", "si le da malaria, ¿cómo sé que es grave?"),
    # ── la palidez palmar: pintura, frío, rojo
    ("es", "pintura", "tiene las palmas de las manos manchadas de pintura blanca"),
    ("en", "frío", "his palms go white when he is cold"),
    ("es", "rojas", "las palmas se le ponen rojas cuando juega"),
    # ── el sarampión: la vacuna, y el sarampión sin complicación
    ("es", "vacuna", "le pusieron la vacuna del sarampión y tiene pus en el pinchazo"),
    ("es", "sin complicación", "tiene sarampión y los ojos los tiene bien"),
    ("es", "pregunta", "¿el sarampión puede dar úlceras en la boca?"),
    # ── no puede beber: la madre, no el niño
    ("es", "problema de la madre", "no puede mamar bien porque tengo una mastitis"),
    ("es", "preferencia", "no quiere beber agua, sólo zumo"),
    ("es", "condicional", "¿qué hago si no puede beber nada?"),
    # ── la deshidratación explicada, no vista
    ("es", "información", "me han dicho que si pellizco la piel y tarda en volver es deshidratación"),
    ("en", "información", "how do I check if the skin goes back slowly?"),
    # ── corrientes
    ("es", "catarro", "mi hijo de 3 años tiene mocos y está comiendo bien"),
    ("en", "corriente", "he has a rash after the vaccine, no fever"),
    ("es", "corriente", "está estreñido desde hace dos días"),
]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "lang,trampa,texto", TRAMPAS, ids=lambda x: str(x)[:34] if isinstance(x, str) else str(x)
)
def test_an_ordinary_sentence_about_africa_is_still_ordinary(
    triaje: Triage, lang: str, trampa: str, texto: str
) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", (
        f"[{lang}] {trampa}: «{texto}» → {r.level} por {[m.id for m in r.matched]}"
    )
