"""Los calendarios vacunales, por dentro (9-sep-2026).

Ya dieron un susto: se publicó el calendario de Portugal derogado desde octubre de 2025. Un
calendario equivocado no se nota —parece un calendario— y decide cuándo lleva un padre a su hijo
a que le pinchen.

Lo que se comprueba aquí es la forma del dato, que es lo que sí se puede comprobar sola: que cada
cita tenga vacunas y etiqueta en los ocho idiomas, que no haya edades repetidas ni imposibles, y
que la herramienta conteste a cualquier edad sin romperse.

Lo que NO se puede comprobar aquí es si el calendario es el vigente: para eso está el vigilante de
enlaces (`ops/sources_alive.py`), que ya incluye estas siete direcciones y avisa cuando una se
rompe, redirige o cambia de tema. Su punto ciego, y conviene tenerlo escrito: **una edición nueva
publicada en la misma dirección**, que es exactamente lo que pasó con Portugal.
"""

from __future__ import annotations

import pathlib
from collections import Counter

import pytest
import yaml

from pedibot.bot.vaccines import Vaccines, format_answer

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FICHERO = RAIZ / "config" / "vaccines.yaml"
CRUDO = yaml.safe_load(FICHERO.read_text(encoding="utf-8"))["countries"]
PAISES = sorted(CRUDO)
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def vac() -> Vaccines:
    return Vaccines(FICHERO)


def test_there_are_schedules_to_check() -> None:
    assert len(PAISES) >= 7, f"solo hay {len(PAISES)} calendarios"


@pytest.mark.parametrize("pais", PAISES)
def test_no_appointment_is_empty_or_unlabelled(pais: str) -> None:
    for s in CRUDO[pais]["schedule"]:
        assert s.get("vaccines"), f"{pais}: la cita de {s['age']} meses no tiene vacunas"
        etiqueta = s.get("label")
        assert isinstance(etiqueta, dict), f"{pais}: cita de {s['age']} m sin etiquetas"
        faltan = [lg for lg in IDIOMAS if not str(etiqueta.get(lg, "")).strip()]
        assert not faltan, f"{pais}: cita de {s['age']} m sin etiqueta en {faltan}"


@pytest.mark.parametrize("pais", PAISES)
def test_no_age_is_repeated_or_impossible(pais: str) -> None:
    """Una edad repetida es casi siempre un error: la misma visita escrita dos veces.

    Casi siempre, no siempre. Una CAMPAÑA anual —la gripe— puede empezar justo a la edad de una
    cita fija: en el Golfo, a los 6 meses tocan la hexavalente y empieza la gripe de temporada.
    Son cosas distintas y la herramienta las trata distinto (`every_year` se arrastra a todas las
    edades posteriores, y la cita fija no), así que la comprobación se hace dentro de cada grupo
    y no sobre la mezcla, que es lo que hacía hasta el 17-sep-2026 (L169).
    """
    edades = [float(s["age"]) for s in CRUDO[pais]["schedule"]]
    for anual in (False, True):
        # Lo que se compara es la edad CON SU ETIQUETA, y no la edad sola (18-sep-2026, con los
        # calendarios africanos). Somalia pone el sarampión «a los 15 meses» y la vitamina A «de
        # 15 a 18»: empiezan el mismo día y son dos citas distintas, con dos etiquetas distintas.
        # La avería que esta regla busca —la misma visita escrita dos veces— tiene las dos cosas
        # iguales; una edad que arranca dos rangos no la tiene.
        grupo = [
            (float(s["age"]), s["label"]["en"])
            for s in CRUDO[pais]["schedule"]
            if bool(s.get("every_year")) is anual
        ]
        repes = [e for e, n in Counter(grupo).items() if n > 1]
        cual = "campañas anuales" if anual else "citas fijas"
        assert not repes, f"{pais}: citas repetidas entre las {cual}: {repes}"
    fuera = [e for e in edades if e < 0 or e > 216]
    assert not fuera, f"{pais}: edades fuera de la infancia {fuera}"


@pytest.mark.parametrize("pais", PAISES)
def test_the_fixed_appointments_are_in_order(pais: str) -> None:
    """`schedule()` ordena, así que esto no protege al código: protege la lectura del fichero,
    que es donde alguien comprueba a mano si el calendario es el que dice el ministerio."""
    fijas = [float(s["age"]) for s in CRUDO[pais]["schedule"] if not s.get("every_year")]
    assert fijas == sorted(fijas), f"{pais}: las citas fijas no están en orden: {fijas}"


@pytest.mark.parametrize("pais", PAISES)
def test_the_schedule_says_where_it_comes_from(pais: str) -> None:
    """Sin fuente y sin enlace, un calendario es una lista de fechas que hay que creerse."""
    d = CRUDO[pais]
    assert str(d.get("source", "")).strip(), f"{pais}: sin fuente"
    assert str(d.get("source_url", "")).startswith("http"), f"{pais}: sin enlace a la fuente"


@pytest.mark.parametrize("pais", PAISES)
def test_the_tool_answers_at_any_age_without_breaking(vac: Vaccines, pais: str) -> None:
    for edad in (0, 2, 4, 6, 12, 18, 48, 144, 216):
        debidas, siguiente = vac.at_age(pais, edad, "es")
        assert isinstance(debidas, list)
        if siguiente is not None:
            assert siguiente.age_months > edad, (
                f"{pais}: a los {edad} m la «próxima» cita es de {siguiente.age_months} m"
            )


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_text_a_parent_reads_has_content_in_every_language(vac: Vaccines, lang: str) -> None:
    for pais in PAISES:
        texto = format_answer(vac, pais, 4, lang)
        assert texto and len(texto) > 40, f"{pais}/{lang}: texto vacío o mínimo"


@pytest.mark.parametrize("pais", PAISES)
def test_the_link_to_the_source_is_an_address_and_not_a_display_name(pais: str) -> None:
    """18-sep-2026. El enlace a la página de la OMS se armaba con el nombre del CLDR, que es el
    que sirve para escribir en una interfaz y no para una dirección: salieron
    «congo---kinshasa», «côte-d'ivoire» con comilla tipográfica y «são-tomé-&-príncipe», que
    devolvía 400 Bad Request. Ahora sale del nombre que usa la propia OMS en REF_COUNTRIES.

    Esta prueba no puede comprobar que la página exista —el sitio de la OMS devuelve los mismos
    23.555 bytes para «kenya» que para «atlantis», así que el 200 no distingue nada (L132)— pero
    sí comprueba lo que hace que una dirección no sea una dirección: un carácter que no es ASCII,
    un ampersand, una comilla o un guion doble de un nombre partido.
    """
    url = CRUDO[pais]["source_url"]
    assert url.isascii(), f"{pais}: el enlace lleva caracteres que no son ASCII — {url}"
    if "immunizationdata.who.int" not in url:
        # Los trece primeros citan a su propio ministerio y ahí manda el ministerio: el PDF de
        # la India lleva un «%20» de verdad, que es un espacio escrito como se escribe.
        return
    trozo = url.rsplit("/", 1)[-1]
    for malo in ("&", "'", "’", "--", " ", "%"):
        assert malo not in trozo, f"{pais}: «{malo}» dentro de la dirección — {url}"
