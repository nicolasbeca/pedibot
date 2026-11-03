"""La respuesta tiene delante cuándo pedir ayuda y no lo dice (3-nov-2026).

La regla c) del prompt pide la lista entera de «cuándo ir» cuando un pasaje de esta situación la
trae, y casi siempre sale. A veces no: «My 2 year old has had a fever of 39 degrees for two days.
What should I do?» (consulta 1125) citaba el NHS de la fiebre por su primera sección y dejaba
fuera la otra, «Don't», que lleva dentro «Urgent advice: Call 111 if…»; acababa en «Watch their
general condition and colour». Para un padre, lo que más importa de una respuesta sin aviso es
cuándo deja de poder esperar.

Aquí decide el código, con dos condiciones para no rehacer lo que está bien:
  - la lista es de un documento que la respuesta YA usa (misma situación; la de otro documento
    puede ser de otra enfermedad, que es justo lo que la v12 quitó), y
  - ninguna frase de la respuesta manda al médico (las de la dosis no cuentan).
Entonces, un reintento con la nota. Ver tests/test_answer_says_when_to_get_help.py.
"""

from __future__ import annotations

import re

from pedibot.index.store import Hit

#: un pasaje que dice cuándo pedir ayuda, por sus cabeceras: las del NHS van dentro del texto
#: («Urgent advice:», «Immediate action required:»), las demás en el título de la sección. Además
#: de los que la ingesta marca `is_red_flag`, que no son todos (el pañal del NHS no lo lleva).
LISTA_DE_AYUDA = re.compile(
    r"urgent advice:|immediate action required:|non-urgent advice:"
    r"|when (and where )?to (get|seek) (medical )?(help|care|advice)"
    r"|when to (see|call|contact) (a |your )?(gp|doctor|medical professional|health)"
    r"|cu[aá]ndo (debemos |hay que |se debe )?(consultar|acudir|llamar|contactar)"
    r"|situaciones que exigen una consulta|motivos para consultar"
    r"|wann\b[^.?]{0,60}(ärztlich|arzt|ärztin|praxis|hilfe)"
    r"|quand (faut-il )?consulter|quando (procurar|recorrer|consultar)",
    re.IGNORECASE,
)

#: una frase que manda a alguien que atiende, en las lenguas en que se contesta. Si la respuesta
#: tiene una, ya dice cuándo ir aunque no sea con la lista, y no se rehace
MANDA_AL_MEDICO = re.compile(
    r"doctor|\bGP\b|p(a)?ediatrician|nurse|health visitor|midwife|\bA&E\b|emergenc|urgent"
    r"|hospital|ambulance|\b(111|999|911|112)\b|medical (help|advice|attention|care)"
    r"|(get|seek) help|health ?care (provider|professional)|health professional|clinic"
    r"|m[ée]dic|pediatra|urgencias|centro de salud|enfermer|consult|ambulancia|profesional sanitario"
    r"|p[ée]diatre|urgences|h[ôo]pital|samu"
    r"|[äa]rzt|notaufnahme|notruf|klinik|krankenhaus|praxis|hebamme"
    r"|urg[êe]ncia|centro de sa[úu]de|sns 24|profissional de sa[úu]de"
    r"|डॉक्टर|चिकित्सक|अस्पताल|आपातकाल|इमरजेंसी|स्वास्थ्य केंद्र"
    r"|طبيب|مستشفى|طوارئ|إسعاف|مركز صحي"
    r"|врач|педиатр|скор|больниц|неотложн"
    r"|daktari|hospitali|kliniki|dharura|kituo cha afya",
    re.IGNORECASE,
)

#: las frases de la dosis: «a la dosis que indique su pediatra» no dice cuándo ir
DOSIS = re.compile(
    r"\bdos(e|es|age|is|ierung)\b|posolog|dosagem|खुराक|डोज़|جرع|доз|kipimo", re.IGNORECASE
)

_FRASE = re.compile(r"(?<=[.!?।؟])\s+|\n+")
_CIT = re.compile(r"\[(\d{1,2})\]")


def es_lista_de_ayuda(hit: Hit) -> bool:
    c = hit.chunk
    return c.is_red_flag or bool(LISTA_DE_AYUDA.search(f"{c.section}\n{c.text}"))


def manda_al_medico(texto: str) -> bool:
    return any(
        MANDA_AL_MEDICO.search(f) and not DOSIS.search(f) for f in _FRASE.split(texto)
    )


def falta_cuando_pedir_ayuda(texto: str, hits: list[Hit]) -> str | None:
    """La nota para el reintento, o `None` si la respuesta ya dice cuándo ir o no hay de dónde."""
    citados = {int(n) for n in _CIT.findall(texto)}
    usados = {hits[n - 1].chunk.doc_id for n in citados if 0 < n <= len(hits)}
    listas = [n for n, h in enumerate(hits, start=1) if es_lista_de_ayuda(h)]
    if not usados or citados & set(listas) or manda_al_medico(texto):
        return None
    suyas = [n for n in listas if hits[n - 1].chunk.doc_id in usados]
    if not suyas:
        return None
    cuales = ", ".join(f"[{n}]" for n in suyas)
    return (
        f"missing_when_to_get_help: {cuales} says when to get help in this situation, and your"
        " answer never says it. Add when to get help from it, with its citation, keeping every"
        " reason that can apply to this child, as one sentence or a short list"
    )
