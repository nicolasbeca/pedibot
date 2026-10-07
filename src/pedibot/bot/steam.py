"""El vapor: las guías no coinciden, y se dice (7-oct-2026).

A un padre alemán con un crup de noche se le aconsejó la ducha con vapor. Las guías que tenemos
dicen cosas contrarias:

- CDC (tos y resfriado en niños): «Sit with a young child in a bathroom with steam from a running
  shower» y «Breathe in steam from a bowl of hot water or shower» (cdc_en_treatment).
- NHS, crup: «do not put your child in a steamy room or get them to inhale steam» (nhs_en_croup).
- NHS, infección de pecho: «do not let children breathe in steam from a bowl of hot water because
  of the risk of scalding» (nhs_en_chest_infection).

Elegir una por el padre sería decir más de lo que dicen las guías. Medido a mano, el redactor
seguía la que le llegaba primero (L-v13: una regla en el prompt para que ganase la más específica
se midió y se rechazó). Decisión del operador: cuando se hable del vapor, contar que hay opiniones
distintas y cuáles son. La nota no cita números de pasaje porque no siempre están entre los
pasajes; nombra a cada organización.

El humidificador o el vaporizador de vapor FRÍO no es esto: nadie lo desaconseja.
"""

from __future__ import annotations

import re

_VAPOR = re.compile(
    r"\bsteam(y|ing)?\b|\bhot shower\b"
    r"|\bvapor\b(?!\s+fr[íi]o)|\bvaho\b|\bducha caliente\b"
    r"|\bvapeur\b(?!\s+froide)"
    r"|\bdampf|\bheiße[nr]? dusche\b"
    r"|\bvapore\b"
    # «пару» es también «un par» (пару дней) y «ингаляция» suele ser el nebulizador
    r"|\bпаром\b|горяч\w* пар|над паром"
    r"|بخار|भाप",
    re.IGNORECASE,
)

NOTA_VAPOR = {
    "en": "On steam, guidelines differ. The CDC suggests sitting with a young child in a bathroom "
    "with steam from a running shower to ease a cough. The NHS advises against it: with croup, do "
    "not put your child in a steamy room or get them to inhale steam, and do not let children "
    "breathe in steam from a bowl of hot water, because of the risk of scalding.",
    "es": "Sobre el vapor, las guías no coinciden. Los CDC de EE. UU. proponen sentarse con el "
    "niño pequeño en el baño con el vapor de la ducha para aliviar la tos. El NHS británico lo "
    "desaconseja: con crup, no meta al niño en un cuarto lleno de vapor ni le haga respirar vapor, "
    "y no deje que un niño respire el vapor de un bol de agua caliente, por el riesgo de quemaduras.",
    "fr": "Sur la vapeur, les recommandations divergent. Les CDC américains proposent de s'asseoir "
    "avec le jeune enfant dans une salle de bain remplie de la vapeur de la douche pour soulager la "
    "toux. Le NHS britannique le déconseille : en cas de laryngite (croup), ne mettez pas l'enfant "
    "dans une pièce pleine de vapeur et ne lui faites pas inhaler de vapeur, et ne laissez pas un "
    "enfant respirer la vapeur d'un bol d'eau chaude, à cause du risque de brûlure.",
    "de": "Beim Dampf sind sich die Leitlinien nicht einig. Die US-amerikanischen CDC schlagen vor, "
    "sich mit dem kleinen Kind ins Badezimmer zu setzen, in den Dampf der laufenden Dusche, um den "
    "Husten zu lindern. Der britische NHS rät davon ab: bei Pseudokrupp das Kind nicht in einen "
    "dampfigen Raum bringen und keinen Dampf inhalieren lassen, und Kinder keinen Dampf aus einer "
    "Schüssel mit heißem Wasser einatmen lassen, wegen der Verbrühungsgefahr.",
    "pt": "Sobre o vapor, as orientações não coincidem. Os CDC dos EUA sugerem sentar-se com a "
    "criança pequena na casa de banho com o vapor do chuveiro para aliviar a tosse. O NHS britânico "
    "desaconselha: com crupe, não coloque a criança num quarto cheio de vapor nem a faça inalar "
    "vapor, e não deixe uma criança respirar o vapor de uma tigela de água quente, pelo risco de "
    "queimaduras.",
    "ru": "Насчёт пара рекомендации расходятся. Американские CDC советуют посидеть с маленьким "
    "ребёнком в ванной, наполненной паром от горячего душа, чтобы облегчить кашель. Британская NHS "
    "это не рекомендует: при крупе не помещайте ребёнка в комнату, полную пара, и не давайте ему "
    "дышать паром, и не позволяйте детям дышать паром над миской с горячей водой — есть риск ожога.",
    "ar": "بخصوص البخار، تختلف الإرشادات. تقترح مراكز CDC الأمريكية الجلوس مع الطفل الصغير في "
    "الحمّام مع بخار الدش لتخفيف السعال. أما هيئة NHS البريطانية فلا تنصح بذلك: في حالة الخانوق "
    "(الكروب) لا تضع طفلك في غرفة مليئة بالبخار ولا تجعله يستنشق البخار، ولا تدع الأطفال يستنشقون "
    "البخار من وعاء ماء ساخن بسبب خطر الحروق.",
    "hi": "भाप के बारे में दिशानिर्देश अलग-अलग हैं। अमेरिका की CDC खाँसी में आराम के लिए छोटे "
    "बच्चे के साथ बाथरूम में चलते शावर की भाप में बैठने का सुझाव देती है। ब्रिटेन की NHS इसकी "
    "सलाह नहीं देती: क्रुप में बच्चे को भाप भरे कमरे में न रखें और न ही उसे भाप सुँघाएँ, और गर्म "
    "पानी के कटोरे से बच्चों को भाप न लेने दें, क्योंकि जलने का खतरा है।",
}


def nota_vapor(pregunta: str, respuesta: str, lang: str) -> str | None:
    """La nota si la pregunta o la respuesta hablan del vapor; si no, nada."""
    if not (_VAPOR.search(pregunta or "") or _VAPOR.search(respuesta or "")):
        return None
    return NOTA_VAPOR.get(lang, NOTA_VAPOR["en"])
