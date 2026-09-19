"""Quién es Laura (19-sep-2026).

La pieza que convierte «¿qué vacunas le tocan a Laura?» en una respuesta por su edad. Es
deliberadamente pequeña y vive en el borde: **no cambia nada de lo que ya funciona**. Si quien
pregunta tiene cuenta y en su frase aparece el nombre de uno de sus hijos, a la pregunta se le
pone delante la misma línea de contexto que hoy escribe el desplegable del chat —«Edad: 18
meses. Peso: 11,2 kg.»— y de ahí para adentro el triaje, la dosis, el calendario vacunal y el
percentil hacen exactamente lo de siempre.

Dos cuidados, y los dos salen de averías que este proyecto ya pagó:

1. **El nombre no se busca dentro de otra palabra.** «Catar» vive dentro de «catarro» y nos
   costó un día; una niña llamada Laura no puede aparecer porque alguien escriba «laurel». Se
   busca con frontera de palabra y sobre el texto aplanado, que es como se teclea de noche: en
   minúsculas y sin tildes.
2. **Si hay dos nombres en la frase, no se elige.** Contestar por la edad equivocada es peor
   que no contestar por ninguna, y en dosis es peligroso de verdad.

Y una advertencia honesta sobre el método: hay nombres que también son palabras corrientes —Sol,
Ángel, Rocío—. Por eso la respuesta dice SIEMPRE con qué hijo contestó y con qué edad; una edad
que el lector no ve es una edad que no puede corregir, y esa lección es de esta misma mañana.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _aplana(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def child_in_question(texto: str, children: list[dict[str, Any]]) -> dict[str, Any] | None:
    """El hijo nombrado en la frase, o None si no hay ninguno o hay más de uno."""
    if not children:
        return None
    llano = _aplana(texto)
    encontrados = [
        hijo
        for hijo in children
        if (nombre := _aplana(str(hijo.get("name", "")).strip()))
        and re.search(rf"(?<![\w]){re.escape(nombre)}(?![\w])", llano)
    ]
    return encontrados[0] if len(encontrados) == 1 else None


#: Cómo se dice «edad» y «peso» en las nueve lenguas que el aviso sabe hablar. Es una línea de
#: contexto, no prosa: va delante de la pregunta y el modelo la lee como la leería un pediatra.
_ETIQUETAS = {
    "es": ("Edad", "Peso", "meses", "años"),
    "en": ("Age", "Weight", "months", "years"),
    "fr": ("Âge", "Poids", "mois", "ans"),
    "de": ("Alter", "Gewicht", "Monate", "Jahre"),
    "ru": ("Возраст", "Вес", "мес.", "лет"),
    "ar": ("العمر", "الوزن", "شهرا", "سنوات"),
    "pt": ("Idade", "Peso", "meses", "anos"),
    "hi": ("उम्र", "वज़न", "महीने", "साल"),
    "sw": ("Umri", "Uzito", "miezi", "miaka"),
}


def _edad_texto(meses: float, lang: str) -> str:
    _, _, mes, anio = _ETIQUETAS.get(lang, _ETIQUETAS["en"])
    if meses < 24:
        # por debajo de dos años la edad se dice en meses, en las nueve lenguas, y además es
        # el tramo donde un mes de más o de menos cambia la dosis y la vacuna que toca
        return f"{round(meses)} {mes}"
    anios = f"{round(meses / 12, 1):g}"
    # la coma decimal es lo normal en ocho de las nueve; el inglés es la excepción
    return f"{anios if lang == 'en' else anios.replace('.', ',')} {anio}"


def context_line(child: dict[str, Any], lang: str) -> str:
    """«Edad: 18 meses. Peso: 11,2 kg.» — lo mismo que hoy pone el desplegable del chat."""
    etiqueta_edad, etiqueta_peso, _, _ = _ETIQUETAS.get(lang, _ETIQUETAS["en"])
    meses = float(child.get("age_months") or 0)
    trozos = [f"{etiqueta_edad}: {_edad_texto(meses, lang)}"]
    peso = child.get("weight_kg")
    if peso:
        kg = f"{float(peso):g}"
        trozos.append(f"{etiqueta_peso}: {kg if lang == 'en' else kg.replace('.', ',')} kg")
    return ". ".join(trozos) + "."


def with_child_context(texto: str, child: dict[str, Any], lang: str) -> str:
    """La pregunta del padre, con su línea de contexto delante. Sus palabras no se tocan."""
    return f"{context_line(child, lang)}\n{texto}"


#: Cuánto puede envejecer un peso antes de dejar de servir para calcular una dosis, por edad.
#: Un lactante de dos meses gana casi dos kilos en noventa días: usar su peso de hace tres meses
#: para calcular un jarabe sería infradosificarlo con toda la confianza del mundo. Cuanto más
#: pequeño, más corta la caducidad.
_CADUCIDAD_PESO_DIAS = ((12.0, 30), (60.0, 90), (float("inf"), 180))


def fresh_weight(
    child: dict[str, Any], measurements: list[dict[str, Any]], today: Any = None
) -> float | None:
    """El último peso apuntado, **sólo si todavía vale**.

    Un peso viejo no es un dato viejo inofensivo: es una dosis mal calculada. Así que si la
    última vez que se pesó al niño queda fuera de la ventana de su edad, esto devuelve None y la
    pregunta sigue su camino sin peso, como cualquier otra.
    """
    import datetime as _dt

    hoy = today or _dt.date.today()
    meses = float(child.get("age_months") or 0)
    ventana = next(dias for tope, dias in _CADUCIDAD_PESO_DIAS if meses < tope)
    for m in reversed(measurements):
        if m.get("weight_kg") is None:
            continue
        try:
            cuando = _dt.date.fromisoformat(str(m["date"]))
        except ValueError:
            continue
        return float(m["weight_kg"]) if (hoy - cuando).days <= ventana else None
    return None
