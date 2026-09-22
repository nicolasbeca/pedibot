"""Deterministic dose calculator. The LLM never computes doses (CLAUDE.md rule 4).

Source of the ranges: AEPap, "Guía rápida de dosificación práctica en pediatría" (3.ª ed.),
table of analgesics/antipyretics:
  PARACETAMOL  40-60 mg/kg/día, 10-15 mg/kg/dosis, cada 4-6-8 h.
  IBUPROFENO   20 mg/kg/día (as listed in the guide; up to 30-40 mg/kg/día in other references),
               cada 6-8 h. Not under 3 months / 5 kg (ficha técnica).
Hard caps follow the Spanish summary of product characteristics (adult maxima) and are
intentionally conservative. Every number here has a unit test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

from pedibot.bot.strings import tool_strings
from pedibot.settings import ROOT

if TYPE_CHECKING:  # sólo para el tipo: en marcha no hace falta y evita el círculo
    from pedibot.bot.drugs import Brand


@dataclass(frozen=True)
class Presentation:
    name: str
    mg_per_ml: float


@dataclass(frozen=True)
class Drug:
    key: str
    #: El nombre genérico en los ocho idiomas. Eran dos campos, `name_es` y `name_en`, y el
    #: formateador elegía con `d.name_es if lang == "es" else d.name_en`: la forma que el
    #: candado del i18n prohíbe en la web —entrega la rama inglesa a los otros seis— viviendo
    #: en el Python, donde ese candado no miraba. Un padre ruso leía «Paracetamol
    #: (acetaminophen) для 12 кг» (7-sep-2026).
    names: dict[str, str]
    mg_per_kg_min: float
    mg_per_kg_max: float
    #: The single figure to act on. The band is what the guide publishes; this is the
    #: dose the published daily maximum is built from (15 × 4 = 60, 10 × 3 = 30) and the
    #: one the sources state outright for fever. A parent cannot measure a range.
    usual_mg_per_kg: float
    interval_hours: tuple[int, int]
    max_mg_per_kg_day: float
    max_single_dose_mg: float
    max_daily_mg: float
    min_age_months: float
    min_weight_kg: float
    presentations: tuple[Presentation, ...]
    source: str
    #: idioma → (organismo, título, enlace) de una ficha que ESE lector puede abrir sobre
    #: esta medicina. No es la fuente de la tabla —ésa es `source` y no cambia—, es la
    #: puerta para quien no lee el idioma de la fuente. Hoy sólo hay del NHS, en inglés.
    read_more: dict[str, tuple[str, str, str]] = field(default_factory=dict)


PARACETAMOL = Drug(
    key="paracetamol",
    names={
        "en": "Paracetamol (acetaminophen)",
        "es": "Paracetamol",
        "fr": "Paracétamol",
        "de": "Paracetamol",
        "ru": "Парацетамол",
        "ar": "باراسيتامول",
        "pt": "Paracetamol",
        "hi": "पैरासिटामोल",
    },
    mg_per_kg_min=10,
    mg_per_kg_max=15,
    usual_mg_per_kg=15,
    interval_hours=(4, 6),
    max_mg_per_kg_day=60,
    max_single_dose_mg=1000,
    max_daily_mg=4000,
    min_age_months=0,
    min_weight_kg=0,
    # Los JARABES primero y las GOTAS después, y dentro de cada grupo de la más diluida a la más
    # concentrada. Hasta el 7-sep-2026 el chat solo conocía tres de las siete: quien tuviera
    # gotas de 200 mg/ml —la presentación brasileña, que está en el catálogo y tiene su página en
    # la web— no veía su bote, y si cogía por error la línea de las de 100 mg/ml se pasaba al
    # doble.
    #
    # **Por qué agrupadas por forma y no sólo por concentración (20-sep-2026).** Al añadir las
    # gotas etíopes de 100 mg/5 ml, el orden puramente ascendente las ponía LAS PRIMERAS de la
    # tabla, y ahí aparecía un riesgo nuevo mirando la web viva: un padre en España con Apiretal
    # —gotas de 100 mg/**ml**— que no hubiera elegido país veía «gotas» en la primera línea, le
    # daba los 7,5 ml de esa fila y eran 750 mg en vez de 150. **Cinco veces de más, y en la
    # dirección mala.** Agrupadas, las tres presentaciones de gotas quedan seguidas: quien busca
    # «gotas» las ve juntas y tiene que leer la concentración para elegir, que es exactamente lo
    # que hay que obligarle a hacer.
    presentations=(
        Presentation("jarabe 120 mg/5 ml", 24.0),
        # 125 mg/5 ml es el jarabe infantil estándar de India (Crocin, Dolo, Metacin,
        # Pyrigesic) y de Egipto (Cetal). Faltaba: un padre indio no podía elegir su bote,
        # y el de al lado —120 mg/5 ml— se le parece lo justo para cogerlo por error.
        Presentation("jarabe 125 mg/5 ml", 25.0),
        Presentation("jarabe 150 mg/5 ml (3 %)", 30.0),
        Presentation("jarabe 160 mg/5 ml", 32.0),
        Presentation("jarabe 200 mg/5 ml (4 %)", 40.0),
        Presentation("jarabe 250 mg/5 ml", 50.0),
        # Y las gotas, las tres seguidas. La primera son las de Etiopía, según la lista de
        # medicamentos sin receta de su regulador (EFDA), y faltaban: sin ellas, un padre de
        # Adís Abeba cogía la de 100 mg/ml y le daba cinco veces la dosis. La etiqueta lleva la
        # concentración entera justo para que las tres no puedan confundirse leyéndolas.
        Presentation("gotas 100 mg/5 ml", 20.0),
        Presentation("gotas 100 mg/ml", 100.0),
        Presentation("gotas 200 mg/ml", 200.0),
    ),
    source="AEPap — Guía rápida de dosificación práctica en pediatría (3.ª ed.), tabla analgésicos/antitérmicos",
    read_more={
        "en": (
            "NHS",
            "Paracetamol for children",
            "https://www.nhs.uk/medicines/paracetamol-for-children/",
        )
    },
)

IBUPROFENO = Drug(
    key="ibuprofeno",
    names={
        "en": "Ibuprofen",
        "es": "Ibuprofeno",
        "fr": "Ibuprofène",
        "de": "Ibuprofen",
        "ru": "Ибупрофен",
        "ar": "إيبوبروفين",
        "pt": "Ibuprofeno",
        "hi": "आइबुप्रोफेन",
    },
    mg_per_kg_min=5,
    mg_per_kg_max=10,
    usual_mg_per_kg=10,
    interval_hours=(6, 8),
    max_mg_per_kg_day=30,
    max_single_dose_mg=400,
    max_daily_mg=1200,
    min_age_months=3,
    min_weight_kg=5,
    presentations=(
        Presentation("jarabe 2 % (100 mg/5 ml)", 20.0),
        Presentation("jarabe 4 % (200 mg/5 ml)", 40.0),
        Presentation("gotas 50 mg/ml", 50.0),
    ),
    source="AEPap — Guía rápida de dosificación práctica en pediatría (3.ª ed.), tabla analgésicos/antitérmicos",
    read_more={
        "en": (
            "NHS",
            "Ibuprofen for children",
            "https://www.nhs.uk/medicines/ibuprofen-for-children/",
        )
    },
)


def leer_mas(d: Drug, lang: str) -> str:
    """«Más sobre el paracetamol en niños: NHS — …», cuando ese lector tiene dónde.

    Vacío cuando no hay ficha en su idioma, que hoy es casi siempre. Un enlace en una lengua
    que no lee no es una puerta: es una puerta pintada en la pared.
    """
    ficha = d.read_more.get(lang)
    if not ficha:
        # La lengua puente que este proyecto ya tiene decidida: un lector de hindi, árabe, ruso,
        # alemán o francés puede abrir una ficha en inglés, y el portugués una en español. No es
        # una suposición mía, es la misma tabla con la que el buscador elige qué subir al tercer
        # puesto cuando la lengua del lector no tiene material propio (L183).
        from pedibot.index.store import READABLE_FALLBACK

        puente = READABLE_FALLBACK.get(lang)
        ficha = d.read_more.get(puente) if puente else None
    if not ficha:
        return ""
    org, titulo, url = ficha
    plantilla = tool_strings(lang).get("dose_read_more")
    if not plantilla:
        return ""
    return plantilla.format(org=org, title=titulo, url=url)


DRUGS: dict[str, Drug] = {
    "paracetamol": PARACETAMOL,
    "acetaminophen": PARACETAMOL,
    "ibuprofeno": IBUPROFENO,
    "ibuprofen": IBUPROFENO,
}


@dataclass(frozen=True)
class DoseResult:
    drug: Drug
    weight_kg: float
    mg_min: float
    mg_max: float
    #: the single figure to act on; mg_min/mg_max stay as the band the guide publishes
    mg: float
    ml: dict[str, float]
    ml_band: dict[str, tuple[float, float]]
    interval_hours: tuple[int, int]
    max_doses_per_day: int
    warnings: list[str]
    refer: bool  # True → do not give: refer to paediatrician / emergency


class DoseError(ValueError):
    pass


#: Las dos palabras con las que nombramos NOSOTROS una presentación genérica, en los ocho
#: idiomas. La concentración no se traduce —«120 mg/5 ml» se lee igual en todas partes— y el
#: nombre de una marca tampoco: «infant», «six plus» o «baby drops» es lo que pone en la caja,
#: y un padre busca en la lista lo que tiene en la mano.
#:
#: Hasta el 8-sep-2026 la lista de botes salía en castellano en los ocho idiomas: un padre
#: alemán leía «jarabe 120 mg/5 ml» y uno hindi «gotas 100 mg/ml», en la herramienta
#: determinista insignia y en la única línea de la respuesta que es una instrucción. El
#: comprobador de fugas de idioma no lo veía porque mira las páginas construidas, y esta lista
#: la pinta el navegador con lo que responde el API.
_FORMA = {
    "jarabe": {
        "en": "syrup",
        "es": "jarabe",
        "fr": "sirop",
        "de": "Saft",
        "ru": "сироп",
        "ar": "شراب",
        "pt": "xarope",
        "hi": "सिरप",
    },
    "gotas": {
        "en": "drops",
        "es": "gotas",
        "fr": "gouttes",
        "de": "Tropfen",
        "ru": "капли",
        "ar": "قطرات",
        "pt": "gotas",
        "hi": "ड्रॉप्स",
    },
}


def _mg_por_ml(texto: str) -> float | None:
    """La concentración que lleva dentro una etiqueta, sea nuestra o de una marca.

    «jarabe 125 mg/5 ml» → 25. «suspensión 2,4 % (120 mg/5 ml)» → 24. «gotas 100 mg/ml» → 100.
    Se compara por número y no por texto porque la misma concentración se escribe de cinco
    formas distintas según quién la imprima.
    """
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*(\d+(?:[.,]\d+)?)?\s*ml", texto, re.I)
    if not m:
        return None
    mg = float(m.group(1).replace(",", "."))
    ml = float(m.group(2).replace(",", ".")) if m.group(2) else 1.0
    return mg / ml if ml else None


def _misma_concentracion(presentacion: str, brand: Brand) -> bool:
    objetivo = _mg_por_ml(presentacion)
    if objetivo is None:
        return False
    return any((c := _mg_por_ml(f)) is not None and abs(c - objetivo) < 0.05 for f in brand.forms)


@lru_cache(maxsize=1)
def _formas_por_pais() -> dict[str, dict[str, list[str]]]:
    """Lo que el regulador de cada país publica, cuando no hay una marca que escribir.

    20-sep-2026. Buscando marcas para los 23 países africanos que no tenían ninguna aparece un
    patrón: en muchos el regulador publica **qué concentraciones se dispensan**, pero ninguna
    marca manda lo bastante como para escribirla. Inventarse una marca sería lo que aquí no se
    hace; tirar la lista del regulador por no traer nombres sería tirar el dato más útil de los
    dos, porque **lo que hace daño no es el nombre del bote, es la concentración**.
    """
    import yaml  # noqa: PLC0415 — sólo si alguien pregunta por un país

    d = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))
    fuera: dict[str, dict[str, list[str]]] = {}
    for code, v in (d.get("country_forms") or {}).items():
        fuera[code.upper()] = {k: list(x) for k, x in v.items() if isinstance(x, list)}
    return fuera


def bottles_in_country(drugs: object, drug_key: str, country: str | None) -> list[str]:
    """Las etiquetas de los botes que se venden en ese país.

    Dos orígenes, y los dos son datos ya escritos en otro sitio: el catálogo de marcas leído del
    revés —cada marca dice en qué países está y con qué formatos—, y las concentraciones que
    publica el regulador del país, para los que tienen registro pero no una marca dominante.
    """
    if not country or drugs is None:
        return []
    cc = country.upper()
    fuera: list[str] = []
    for marca in getattr(drugs, "brands_for", lambda *_: [])(drug_key):
        if cc in getattr(marca, "countries", ()):
            fuera += [f for f in getattr(marca, "forms", ())]
    # La misma molécula entra por dos nombres —«ibuprofen» desde el catálogo y «ibuprofeno» desde
    # el chat— y sin normalizar, media llamada no encontraría nada y nadie se enteraría.
    canonico = DRUGS[k].key if (k := drug_key.lower()) in DRUGS else k
    fuera += _formas_por_pais().get(cc, {}).get(canonico, [])
    return fuera


def _del_pais_primero(ml: dict[str, float], formas_del_pais: list[str]) -> list[tuple[str, float]]:
    """Las presentaciones que allí se venden delante, conservando su orden relativo."""
    filas = list(ml.items())
    if not formas_del_pais:
        return filas
    concentraciones = {c for f in formas_del_pais if (c := _mg_por_ml(f)) is not None}
    if not concentraciones:
        return filas
    aqui = [
        f
        for f in filas
        if (c := _mg_por_ml(f[0])) is not None and any(abs(c - x) < 0.05 for x in concentraciones)
    ]
    return aqui + [f for f in filas if f not in aqui] if aqui else filas


def _cuantas_del_pais(filas: list[tuple[str, float]], formas_del_pais: list[str]) -> int:
    """Cuántas de las primeras filas se venden en su país, con el criterio que las ordenó."""
    concentraciones = {c for f in formas_del_pais if (c := _mg_por_ml(f)) is not None}
    if not concentraciones:
        return 0
    n = 0
    for pname, _ in filas:
        c = _mg_por_ml(pname)
        if c is None or not any(abs(c - x) < 0.05 for x in concentraciones):
            break
        n += 1
    return n


def _suya_primero(ml: dict[str, float], brand: Brand | None) -> list[tuple[str, float]]:
    """Las presentaciones de su marca delante, en el mismo orden relativo que tenían."""
    filas = list(ml.items())
    if not brand:
        return filas
    suyas = [f for f in filas if _misma_concentracion(f[0], brand)]
    return suyas + [f for f in filas if f not in suyas] if suyas else filas


def presentation_label(name: str, lang: str) -> str:
    """La etiqueta de una presentación genérica en el idioma del lector.

    Solo toca la primera palabra, que es la nuestra; la concentración y los porcentajes se
    quedan como están. Una etiqueta que no empiece por una de las nuestras —las de las marcas—
    se devuelve intacta a propósito.
    """
    primera, _, resto = name.partition(" ")
    traducciones = _FORMA.get(primera.lower())
    if not traducciones:
        return name
    return f"{traducciones.get(lang, traducciones['en'])} {resto}".strip()


def _floor_ml(x: float) -> float:
    """Down to the tenth of a millilitre an oral syringe can actually show.

    Down, not nearest: rounding up moves the dose above the milligrams it was computed
    from, and this is the one page where a number is an instruction.
    """
    return int(x * 10) / 10


def calculate(drug_key: str, weight_kg: float, age_months: float | None = None) -> DoseResult:
    drug = DRUGS.get(drug_key.lower())
    if drug is None:
        raise DoseError(f"unknown drug: {drug_key}")
    if not (1.0 <= weight_kg <= 120.0):
        raise DoseError("weight must be between 1 and 120 kg")

    warnings: list[str] = []
    refer = False
    if age_months is not None and age_months < 3:
        warnings.append("under_3_months_refer")
        refer = True
    if age_months is not None and age_months < drug.min_age_months:
        warnings.append("below_min_age")
        refer = True
    if age_months is None and drug.min_age_months > 0:
        # Sin edad no se puede descartar la contraindicación, y el desplegable de la web tiene
        # una opción que dice literalmente «no lo sé». Medido el 9-sep-2026: con esa opción, el
        # ibuprofeno a 5 kg devolvía la dosis entera, sin un solo aviso — y 5 kg es un peso de
        # lactante. El fármaco no se da por debajo de tres meses.
        #
        # Se trata igual que cuando SÍ sabemos que no toca: se dice por qué y no se dice cuánto
        # (decisión del operador del 8-sep). El paracetamol no tiene edad mínima, así que el
        # caso corriente sigue funcionando sin indicar la edad.
        warnings.append("age_unknown")
        refer = True
    if weight_kg < drug.min_weight_kg:
        warnings.append("below_min_weight")
        refer = True

    mg_min = drug.mg_per_kg_min * weight_kg
    mg_max = drug.mg_per_kg_max * weight_kg
    mg = drug.usual_mg_per_kg * weight_kg
    if mg_max > drug.max_single_dose_mg:
        warnings.append("capped_single_dose")
        mg_max = drug.max_single_dose_mg
        mg_min = min(mg_min, mg_max)
    mg = min(mg, drug.max_single_dose_mg)

    # daily cap → max number of doses at the max single dose
    daily_cap = min(drug.max_mg_per_kg_day * weight_kg, drug.max_daily_mg)
    max_doses = int(daily_cap // mg_max) if mg_max > 0 else 0
    max_doses = max(1, min(max_doses, 24 // drug.interval_hours[0]))

    # También hacia abajo, por la misma razón que `ml`: el extremo alto de la banda es un
    # volumen, y un volumen nunca puede quedar por encima de los miligramos que lo justifican.
    # Era el único sitio que quedaba con `round()` después de arreglar la web y el API el
    # 6-sep-2026 — la misma lección aplicada a un lado y no al otro.
    ml_band = {
        p.name: (_floor_ml(mg_min / p.mg_per_ml), _floor_ml(mg_max / p.mg_per_ml))
        for p in drug.presentations
    }
    ml = {p.name: _floor_ml(mg / p.mg_per_ml) for p in drug.presentations}
    return DoseResult(
        drug=drug,
        weight_kg=weight_kg,
        mg_min=round(mg_min, 1),
        mg_max=round(mg_max, 1),
        mg=round(mg, 1),
        ml=ml,
        ml_band=ml_band,
        interval_hours=drug.interval_hours,
        max_doses_per_day=max_doses,
        warnings=warnings,
        refer=refer,
    )


def format_result(
    r: DoseResult,
    lang: str = "en",
    brand: Brand | None = None,
    brand_key: str | None = None,
    country_forms: list[str] | None = None,
    country_name: str | None = None,
) -> str:
    """La dosis para un padre. Cuando `refer` está puesto, SIN los números.

    Decisión del operador (8-sep-2026). Hasta hoy esta función escribía «no dar sin consultar:
    menor de 3 meses» y a renglón seguido los miligramos y los mililitros de cada bote — para el
    ibuprofeno, que su propia ficha dice que no se da por debajo de tres meses ni de cinco kilos.
    A las tres de la madrugada se leen los números, no el renglón de arriba.

    Se conserva todo lo que ayuda a decidir: qué fármaco es, por qué no se le da, y de dónde sale
    la norma. Lo único que desaparece es la cifra que se podría echar en la jeringa.
    """
    d = r.drug
    T = tool_strings(lang)
    name = d.names.get(lang, d.names["en"])
    lines = [T["dose_for"].format(name=name, kg=r.weight_kg)]
    if r.refer:
        lines.append(
            T["dose_refer"] + ", ".join(T["dose_warn"].get(w, w) for w in r.warnings) + "."
        )
        lines.append(T["dose_source"].format(source=d.source))
        mas = leer_mas(d, lang)
        if mas:
            lines.append(mas)
        lines.append(T["dose_check"])
        return "\n".join(lines)
    lines.append(
        T["dose_line"].format(
            mg=r.mg,
            h0=d.interval_hours[0],
            h1=d.interval_hours[1],
            max_doses=r.max_doses_per_day,
        )
    )
    # 20-sep-2026: Dalsy es ibuprofeno a 40 mg/ml y el paracetamol tiene una presentación a
    # 40 mg/ml. Sin esto, preguntar por paracetamol nombrando Dalsy ponía «Dalsy» encima de una
    # fila de paracetamol: decirle a un padre que su bote lleva otra cosa. Lo cazó su prueba.
    if brand is not None and brand_key is not None and brand_key != r.drug.key:
        brand = None
    # Si ha escrito su marca, manda la suya. Si no, mandan los botes que se venden en su país,
    # que es el mismo criterio con menos información: enseñar primero lo que puede tener en la
    # mano (20-sep-2026).
    filas = (
        _suya_primero(r.ml, brand)
        if brand is not None
        else _del_pais_primero(r.ml, country_forms or [])
    )

    def fila(pname: str, millilitres: float) -> str:
        etiqueta = presentation_label(pname, lang)
        if brand and _misma_concentracion(pname, brand):
            # con el nombre de su caja delante: ocho líneas de mililitros parecidos es donde se
            # lee la que no es, y «6,2» y «6» están una encima de otra (20-sep-2026)
            etiqueta = f"{brand.name}, {etiqueta}"
        return f"  – {etiqueta}: {millilitres:g} ml"

    # 22-sep-2026, y esto lo contó el operador en CHIFA con su propio error delante: las gotas
    # de paracetamol son 100 mg/5 ml en Etiopía y 100 mg/ml en España, CINCO VECES más fuertes.
    # Ponerlas primero (20-sep) ayuda y no basta: en la lista siguen saliendo dos líneas que
    # empiezan por «gotas» y nada dice cuál es la suya. Se agrupan bajo el nombre del país.
    del_pais = _cuantas_del_pais(filas, country_forms or [])
    if country_name and del_pais and brand is None and del_pais < len(filas):
        lines.append(T["dose_sold_in"].format(country=country_name))
        lines += [fila(*f) for f in filas[:del_pais]]
        lines.append(T["dose_other_strengths"])
        lines += [fila(*f) for f in filas[del_pais:]]
    else:
        lines += [fila(*f) for f in filas]
    # the band the guide publishes, so a different figure from a paediatrician is
    # visibly inside it rather than looking like a contradiction
    lines.append(T["dose_band"].format(mg_min=r.mg_min, mg_max=r.mg_max))
    lines.append(T["dose_source"].format(source=d.source))
    mas = leer_mas(d, lang)
    if mas:
        lines.append(mas)
    lines.append(T["dose_check"])
    return "\n".join(lines)
