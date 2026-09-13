"""Las urgencias de una casa de la India o del Golfo, dichas como las dice el padre (13-sep-2026).

Batería de 71 preguntas de padre en árabe e hindi contra el triaje real. Salieron dos fallos del
árabe y tres huecos que no eran de ninguna lengua, sino de todas:

- **«يتنفس بصعوبة والأضلاع تنسحب للداخل»** («respira con dificultad y se le hunden las
  costillas») salía como **rutina**. La regla sabía «صعوبة في التنفس» (el sustantivo) y
  «انسحاب… ضلوع», no el verbo ni el orden en que lo dice un padre. En castellano, la misma frase
  es emergencia.
- **«حرقة عند التبول»** («escozor al orinar») disparaba la regla de **quemaduras** —«حرق» casaba
  como prefijo de «حرقة»— y citaba la ficha de quemaduras del NHS a un niño con una infección de
  orina.
- **Queroseno**: rutina en las ocho lenguas. La regla de envenenamiento tenía lejía y gasolina,
  y ningún combustible de lámpara o de cocina, que es lo que hay en una casa de la India rural o
  del Golfo. En hindi, además, ni pesticida ni veneno de ratas.
- **Golpe de calor**: rutina en las ocho. La ficha del NHS lo dice literal: «Heatstroke is a
  medical emergency». Regla nueva, urgente, y sólo con el verbo de padecerlo: «¿cómo lo
  prevengo?» no es una urgencia, y un aviso que salta de más se deja de leer.
- **Agua hirviendo** en árabe («ماء مغلي») no llegaba a la regla de quemaduras («ماء ساخن» sí).

Queda fuera, anotado: el recién nacido amarillo. Es rutina en las ocho lenguas, y la única fuente
del corpus que lo trata es un manual clínico; hace falta la ficha para padres antes de la regla.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


ALARMAS: dict[str, list[str]] = {
    "respira con dificultad (árabe, como lo dice un padre)": [
        "طفلي يتنفس بصعوبة والأضلاع تنسحب للداخل",
        "ابني يتنفس بصعوبة",
        "ابنتي تتنفس بصعوبة شديدة",
        "أضلاع طفلي تدخل للداخل عندما يتنفس",
    ],
    "queroseno": [
        "my child drank kerosene",
        "my son swallowed some paraffin oil",
        "mi hijo se ha bebido queroseno",
        "mon enfant a bu du pétrole lampant",
        "mon fils a avalé du kérosène",
        "mein Kind hat Petroleum getrunken",
        "ребёнок выпил керосин",
        "شرب طفلي الكاز",
        "ابني شرب الكيروسين",
        "طفلي شرب جاز",
        "o meu filho bebeu querosene",
        "बच्चे ने मिट्टी का तेल पी लिया",
        "मेरे बच्चे ने केरोसिन पी लिया",
    ],
    "pesticida y veneno de ratas": [
        "बच्चे ने कीटनाशक पी लिया",
        "बच्चे ने चूहे मारने की दवा खा ली",
        "طفلي أكل سم الفئران",
        "my child ate rat poison",
    ],
    "golpe de calor": [
        "my child has heatstroke",
        "my son got sunstroke at the beach",
        "a mi hijo le ha dado un golpe de calor",
        "mon fils a fait un coup de chaleur",
        "mein Kind hat einen Hitzschlag",
        "у ребёнка тепловой удар",
        "طفلي أصيب بضربة شمس",
        "ابني عنده ضربة شمس",
        "o meu filho teve uma insolação",
        "बच्चे को लू लग गई है",
    ],
    "agua hirviendo (árabe)": [
        "انسكب ماء مغلي على يد طفلي",
        "طفلي عنده حرق في يده",
    ],
}

#: Lo que se les parece y NO puede disparar
PARECIDOS = [
    "طفلي يشعر بحرقة عند التبول",
    "ابني عنده حرقة في المعدة",
    "¿cómo prevenir un golpe de calor en verano?",
    "how can I protect my child from heatstroke?",
    "كيف أحمي طفلي من ضربة الشمس؟",
    "लू से बच्चे को कैसे बचाएं?",
    "we cook on a kerosene stove at home",
    "نستخدم مدفأة الكاز في البيت",
    "हम घर में मिट्टी के तेल का चूल्हा इस्तेमाल करते हैं",
    "मेरे बच्चे को पेशाब में जलन होती है",
]

CASOS = [(a, t) for a, textos in ALARMAS.items() for t in textos]


@pytest.mark.parametrize(
    ("alarma", "texto"), CASOS, ids=[f"{a[:14]}-{n}" for n, (a, _) in enumerate(CASOS)]
)
def test_la_alarma_salta(triaje: Triage, alarma: str, texto: str):
    r = triaje.assess(texto)
    assert r.level != "routine", f"«{texto}» sale como rutina; es {alarma}"


@pytest.mark.parametrize("texto", PARECIDOS)
def test_lo_que_se_le_parece_no_dispara(triaje: Triage, texto: str):
    r = triaje.assess(texto)
    assert r.level == "routine", (
        f"falso positivo: «{texto}» sale como {r.level} por {[m.id for m in r.matched]}"
    )


def test_el_escozor_al_orinar_no_es_una_quemadura(triaje: Triage):
    r = triaje.assess("طفلي يشعر بحرقة عند التبول")
    assert "burn" not in [m.id for m in r.matched]


def test_el_golpe_de_calor_cita_la_ficha_que_lo_llama_emergencia(triaje: Triage):
    r = triaje.assess("a mi hijo le ha dado un golpe de calor")
    ids = [m.id for m in r.matched]
    assert "heatstroke" in ids, ids
    regla = next(m for m in r.matched if m.id == "heatstroke")
    assert regla.source == "nhs_en_heat_exhaustion_heatstroke"
    motivos = {
        lang: r.reasons(lang)[ids.index("heatstroke")]
        for lang in ("es", "en", "fr", "de", "ru", "ar", "pt", "hi")
    }
    assert len(set(motivos.values())) == 8, "algún idioma cae al motivo inglés"
