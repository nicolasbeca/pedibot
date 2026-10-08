"""Cuando las guías no coinciden, se dice qué dice cada una (8-oct-2026).

Decisión del operador, para siempre: ante una discrepancia entre fuentes no se elige por el padre;
se cuentan las dos posturas, nombrando a cada organización. Este es el registro: cada conflicto
es una entrada con lo que lo dispara y la nota en las ocho lenguas. El vapor (bot/steam.py) fue
el primero; las manos frías con fiebre, el segundo.

Una entrada se dispara por una regla del triaje que haya saltado (`reglas`) o por el texto de la
pregunta o de la respuesta (`texto`). La nota va al final de la respuesta, en la lengua del padre,
y sin números de pasaje: no siempre están entre los pasajes de esa respuesta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pedibot.bot.steam import NOTA_VAPOR, _VAPOR


@dataclass(frozen=True)
class Discrepancia:
    id: str
    nota: dict[str, str]
    reglas: frozenset[str] = frozenset()
    texto: re.Pattern[str] | None = None
    #: si la nota va también cuando la respuesta acabó en un texto fijo (fallback): sí cuando el
    #: conflicto es justo lo que la tumbó (el redactor cita una guía que contradice el aviso)
    tambien_en_fijas: bool = False


MANOS_FRIAS = {
    "en": "On cold hands and feet with a fever, guidelines differ. The SEUP (Spanish Society of "
    "Paediatric Emergency Medicine) says that while a fever is rising it is normal for a child to "
    "feel cold, even to shiver, with mottled skin especially on the hands and feet. The NHS lists "
    "unusually cold hands and feet among the signs to call the emergency number straight away, and "
    "very cold hands and feet among the symptoms of meningitis.",
    "es": "Sobre las manos y los pies fríos con fiebre, las guías no coinciden. La SEUP (Sociedad "
    "Española de Urgencias de Pediatría) dice que, cuando la fiebre está subiendo, es normal que el "
    "niño tenga frío, incluso escalofríos, y la piel moteada, sobre todo en manos y pies. El NHS "
    "británico pone las manos y los pies inusualmente fríos entre los motivos para llamar ya al "
    "número de emergencias, y las manos y los pies muy fríos entre los síntomas de la meningitis.",
    "fr": "Sur les mains et les pieds froids avec de la fièvre, les recommandations divergent. La "
    "SEUP (Société espagnole des urgences pédiatriques) indique que, quand la fièvre monte, il est "
    "normal que l'enfant ait froid, voire des frissons, avec une peau marbrée, surtout aux mains et "
    "aux pieds. Le NHS britannique place des mains et des pieds anormalement froids parmi les signes "
    "qui justifient d'appeler tout de suite le numéro d'urgence, et des mains et des pieds très "
    "froids parmi les symptômes de la méningite.",
    "de": "Bei kalten Händen und Füßen mit Fieber sind sich die Leitlinien nicht einig. Die SEUP "
    "(Spanische Gesellschaft für pädiatrische Notfallmedizin) sagt, dass ein Kind, während das "
    "Fieber steigt, normalerweise friert, sogar Schüttelfrost hat und eine marmorierte Haut, vor "
    "allem an Händen und Füßen. Der britische NHS nennt ungewöhnlich kalte Hände und Füße als Grund, "
    "sofort den Notruf zu wählen, und sehr kalte Hände und Füße als Symptom einer Hirnhautentzündung.",
    "pt": "Sobre mãos e pés frios com febre, as orientações não coincidem. A SEUP (Sociedade "
    "Espanhola de Urgências Pediátricas) diz que, quando a febre está a subir, é normal a criança ter "
    "frio, até calafrios, e a pele marmoreada, sobretudo nas mãos e nos pés. O NHS britânico inclui "
    "mãos e pés invulgarmente frios entre os sinais para ligar já para o número de emergência, e "
    "mãos e pés muito frios entre os sintomas da meningite.",
    "ru": "Насчёт холодных рук и ног при температуре рекомендации расходятся. SEUP (Испанское "
    "общество неотложной педиатрии) пишет, что, пока температура поднимается, ребёнку нормально "
    "мёрзнуть, даже знобить, а кожа может быть мраморной, особенно на руках и ногах. Британская NHS "
    "относит необычно холодные руки и ноги к признакам, при которых нужно сразу звонить в экстренную "
    "службу, а очень холодные руки и ноги — к симптомам менингита.",
    "ar": "بخصوص برودة اليدين والقدمين مع الحمى، تختلف الإرشادات. تقول جمعية SEUP (الجمعية "
    "الإسبانية لطوارئ الأطفال) إنه من الطبيعي أثناء ارتفاع الحرارة أن يشعر الطفل بالبرد، بل "
    "بالقشعريرة، وأن يظهر جلده مبقعا، خاصة في اليدين والقدمين. أما هيئة NHS البريطانية فتعدّ "
    "برودة اليدين والقدمين غير المعتادة من العلامات التي تستدعي الاتصال برقم الطوارئ فورا، "
    "والبرودة الشديدة لليدين والقدمين من أعراض التهاب السحايا.",
    "hi": "बुखार में हाथ-पैर ठंडे होने के बारे में दिशानिर्देश अलग-अलग हैं। SEUP (स्पेन की "
    "बाल आपातकालीन चिकित्सा सोसाइटी) के अनुसार बुखार चढ़ते समय बच्चे को ठंड लगना, कँपकँपी होना "
    "और त्वचा पर, ख़ासकर हाथ-पैरों पर, धब्बेदार रंग आना सामान्य है। ब्रिटेन की NHS असामान्य रूप "
    "से ठंडे हाथ-पैरों को उन संकेतों में गिनती है जिनमें तुरंत आपातकालीन नंबर पर कॉल करना चाहिए, "
    "और बहुत ठंडे हाथ-पैरों को मेनिनजाइटिस के लक्षणों में।",
}

REGISTRO: tuple[Discrepancia, ...] = (
    Discrepancia(id="vapor", nota=NOTA_VAPOR, texto=_VAPOR),
    Discrepancia(
        id="manos_frias_con_fiebre",
        nota=MANOS_FRIAS,
        reglas=frozenset({"cold_extremities_with_fever"}),
        tambien_en_fijas=True,
    ),
)


def notas(
    reglas: list[str], pregunta: str, respuesta: str, lang: str, fija: bool = False
) -> list[str]:
    """Las notas de discrepancia que tocan a esta respuesta, en la lengua del padre."""
    out = []
    for d in REGISTRO:
        if fija and not d.tambien_en_fijas:
            continue
        por_regla = bool(d.reglas & set(reglas))
        por_texto = d.texto is not None and bool(
            d.texto.search(pregunta or "") or d.texto.search(respuesta or "")
        )
        if por_regla or por_texto:
            out.append(d.nota.get(lang, d.nota["en"]))
    return out
