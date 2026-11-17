"""Bajo un aviso, el texto empieza por el aviso (7-oct-2026).

Con el juez que mide contra las guías, 29 de 107 respuestas con aviso urgente o de emergencia no
tenían ni una palabra de prisa: «Fewer wet nappies than usual is one of the signs of
dehydration…», «El asma se debe a una obstrucción de los bronquios…», debajo de un cartel rojo que
dice «urgencias hoy». El cartel está, pero el texto se lee como si no estuviera, y un padre que
lee sólo el texto se queda en casa. Dos intentos en el prompt y uno en el revisor no lo
arreglaron (L-v13, v11): aquí no decide el modelo.

Si el texto ya dice prisa en su lengua (ahora, hoy, urgencias, el número…), no se toca.
"""

from __future__ import annotations

import re

_PRISA = re.compile(
    r"emergenc|urgen|right away|immediately|\bnow\b|\btoday\b|ambulance|hospital|\bA&E\b"
    r"|\bahora\b|\bhoy\b|inmediat|enseguida|ya mismo"
    r"|maintenant|aujourd|tout de suite|imm[ée]diat|\bsamu\b"
    r"|sofort|\bjetzt\b|\bheute\b|notaufnahme|notruf|notarzt|krankenhaus|unverz[üu]glich"
    r"|\bagora\b|\bhoje\b|imediat|pronto[- ]socorro"
    r"|сейчас|срочно|немедленно|сегодня|скор(ую|ой)|больниц"
    r"|الآن|فور|الطوارئ|اليوم|الإسعاف|مستشفى"
    r"|तुरंत|अभी|आज|आपात|एम्बुलेंस|अस्पताल"
    r"|\bsasa\b|\bleo\b|haraka|mara moja|dharura"
    # 17-nov-2026: un número seguido de una unidad no es un teléfono. «entre 7 e 15 dias» contaba
    # como el 15 del SAMU y el texto del ombligo infectado salía sin la frase del aviso.
    r"|\b(911|112|999|111|061|107|123|115|15|103|108)\b(?![.,]\d)"
    r"(?!\s*(?:d[ií]as?|days?|jours?|tage?n?|semanas?|weeks?|semaines?|wochen|meses|months?"
    r"|mois|monate?n?|anos|años|years?|ans|jahren?|horas?|hours?|heures?|stunden?|minut\w*"
    r"|min\b|ml\b|mg\b|kg\b|g\b|°|%|cm\b|mm\b|veces|times|fois|mal\b|vezes"
    r"|дн|недел|месяц|лет|год|час|минут|мл|кг|يوم|أيام|أسبوع|شهر|ساع|دقيق|मिली|किलो|दिन|हफ़्त|महीन|घंट|मिनट"
    r"|siku|wiki|miezi|saa|dakika))",
    re.IGNORECASE,
)

PRIMERO_EL_AVISO = {
    "en": "First, do what the warning above says.",
    "es": "Lo primero, haz lo que dice el aviso de arriba.",
    "fr": "D'abord, faites ce que dit l'avertissement ci-dessus.",
    "de": "Tun Sie zuerst, was im Hinweis oben steht.",
    "pt": "Primeiro, faça o que diz o aviso acima.",
    "ru": "Сначала сделайте то, что сказано в предупреждении выше.",
    "ar": "أولاً، افعل ما يقوله التنبيه في الأعلى.",
    "hi": "सबसे पहले, ऊपर की चेतावनी में जो लिखा है वह कीजिए।",
    "sw": "Kwanza, fanya kile ambacho onyo lililo hapo juu linasema.",
}


def con_el_aviso_delante(texto: str, level: str, lang: str) -> str:
    """El texto, con la frase del aviso delante si hay aviso y el texto no dice prisa."""
    if level not in ("urgent", "emergency") or not texto or _PRISA.search(texto):
        return texto
    frase = PRIMERO_EL_AVISO.get(lang, PRIMERO_EL_AVISO["en"])
    return texto if texto.startswith(frase) else f"{frase}\n\n{texto}"
