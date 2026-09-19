"""Una vacuna se llama en el idioma del que pregunta (20-sep-2026).

58 de los 66 calendarios salen del almacén público de la OMS, que los da en inglés. Un padre
marroquí preguntando en árabe leía «Polio, oral (OPV)» y «Vitamin A (a supplement, not a
vaccine)» en mitad de su respuesta, y son justo los países a los que va esto.

Lo que vigila este fichero, de más grave a menos:

1. **que la tabla esté completa en las ocho lenguas**, porque una clave a la que le falta el
   hindi no da error: devuelve el inglés y nadie se entera;
2. **que la sigla sobreviva**, en la forma que ese país imprime en la cartilla: el inglés dice
   IPV, España VPI, Portugal VIP y Rusia ИПВ, y las cuatro son la misma vacuna escrita como la
   ve la madre en el papel. Lo que no puede pasar es que desaparezca, porque entonces el texto
   deja de casar con lo que le van a decir en el centro de salud;
3. **que lo que no está en la tabla salga intacto**, porque los ocho calendarios transcritos a
   mano usan las palabras del propio ministerio y ésas mandan;
4. **que un « or » dentro de un paréntesis no parta el nombre**, que es el fallo que tenía la
   primera versión con «MMRV vaccine (1st or 2nd dose after 1 July 2024)»;
5. **y que la tabla cubra de verdad lo que se publica**, medido contra los 66 calendarios.
"""

from __future__ import annotations

import collections
import re

import pytest
import yaml

from pedibot.bot.vaccine_names import known_names, list_separator, localise
from pedibot.settings import ROOT

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: Sigla en inglés → las formas con las que ese mismo producto aparece impreso en la cartilla
#: de cada país. No es una traducción: es el mismo acrónimo tal y como lo escribe cada sistema
#: de salud, y por eso la lista está cerrada y se amplía a mano, nunca por regla.
SIGLAS: dict[str, tuple[str, ...]] = {
    "BCG": ("BCG", "БЦЖ"),
    "OPV": ("OPV", "VPO", "VOP", "ОПВ"),
    "IPV": ("IPV", "VPI", "VIP", "ИПВ"),
    "MMR": ("MMR", "ROR", "КПК", "Triple vírica", "Tríplice viral"),
    "MR": ("MR", "SR", "RR", "КК"),
    "Hib": ("Hib", "المستدمية"),
    "HPV": ("HPV", "VPH", "ВПЧ", "الورم الحليمي"),
    "Td": ("Td", "dT", "АДС-М"),
    "DT": ("DT", "АДС"),
}


@pytest.fixture(scope="module")
def tabla() -> dict:
    return yaml.safe_load((ROOT / "config" / "vaccine_names.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def publicados() -> collections.Counter:
    """Cada nombre que aparece en los 66 calendarios, con cuántas veces sale."""
    cal = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    cuenta: collections.Counter = collections.Counter()
    for pais in cal["countries"].values():
        for slot in pais["schedule"]:
            for nombre in slot["vaccines"]:
                cuenta[str(nombre)] += 1
    return cuenta


def test_ninguna_entrada_se_deja_un_idioma(tabla: dict) -> None:
    """A una clave sin hindi no le pasa nada: devuelve el inglés y nadie se entera."""
    incompletas = []
    for seccion in ("names", "suffixes", "units", "units_one"):
        for clave, valores in (tabla.get(seccion) or {}).items():
            faltan = [lg for lg in IDIOMAS if not valores.get(lg)]
            if faltan:
                incompletas.append(f"{seccion}/{clave}: faltan {faltan}")
    for seccion in ("or_word", "second_dose", "list_sep"):
        faltan = [lg for lg in IDIOMAS if not (tabla.get(seccion) or {}).get(lg)]
        if faltan:
            incompletas.append(f"{seccion}: faltan {faltan}")
    assert not incompletas, "\n".join(incompletas)


@pytest.mark.parametrize("lang", IDIOMAS)
def test_la_sigla_sobrevive_en_la_forma_del_pais(tabla: dict, lang: str) -> None:
    """No es que la sigla no cambie: es que no desaparezca.

    España imprime VPI donde el inglés dice IPV, y las dos son la misma vacuna vista desde la
    cartilla de cada uno. Lo que rompería el texto es que no quedara ninguna: entonces deja de
    casar con el papel que la madre tiene en la mano.
    """
    perdidas = []
    for clave, valores in (tabla["names"]).items():
        for sigla, formas in SIGLAS.items():
            # como palabra suelta, para que «DT» no case dentro de «DTaP»
            if not re.search(rf"(?<![A-Za-z]){sigla}(?![A-Za-z])", clave):
                continue
            if not any(f.lower() in valores[lang].lower() for f in formas):
                perdidas.append(
                    f"«{clave}» se queda sin «{sigla}» en {lang}: «{valores[lang]}». "
                    "Si ese país lo imprime de otra forma, añádela a SIGLAS."
                )
    assert not perdidas, chr(10).join(perdidas)


def test_lo_que_no_esta_en_la_tabla_sale_intacto() -> None:
    """Los ocho calendarios transcritos a mano usan las palabras del ministerio, y mandan."""
    for nombre in ("Neumococo (VNC)", "Poliomielite inativada VIP (1.ª dose)", "DTPa"):
        for lang in IDIOMAS:
            assert localise(nombre, lang) == nombre


def test_un_or_dentro_de_un_parentesis_no_parte_el_nombre() -> None:
    """«MMRV vaccine (1st or 2nd dose after 1 July 2024)» es UN nombre, no dos."""
    entero = "MMRV vaccine (1st or 2nd dose after 1 July 2024)"
    assert localise(entero, "es") == entero


def test_dos_alternativas_se_unen_con_la_palabra_de_cada_lengua() -> None:
    """Dos productos en la misma casilla son alternativas para un pinchazo, no dos pinchazos."""
    dos = "DTaP-Hib-HepB-IPV (hexavalent) or DTwP-Hib-HepB (pentavalent)"
    assert " o " in localise(dos, "es")
    assert " oder " in localise(dos, "de")
    assert " ou " in localise(dos, "fr")
    assert " or " in localise(dos, "en")


def test_la_segunda_dosis_respeta_el_singular() -> None:
    """«2.ª dosis 1 meses después» se lee como un error porque lo es."""
    uno = "Td booster (tetanus, diphtheria) — 2nd dose 1 months later"
    seis = "Td booster (tetanus, diphtheria) — 2nd dose 6 months later"
    assert "1 mes después" in localise(uno, "es")
    assert "6 meses después" in localise(seis, "es")
    assert "1 mês" in localise(uno, "pt")


def test_el_arabe_usa_su_propia_coma() -> None:
    """Una coma latina en mitad de un texto de derecha a izquierda dice que no se escribió para ti."""
    assert list_separator("ar") == "، "
    assert list_separator("es") == ", "


def test_la_tabla_cubre_la_mayor_parte_de_lo_publicado(publicados: collections.Counter) -> None:
    """La medida que importa no es cuántas claves hay, es cuántas VECES se lee una traducida.

    El suelo está en el 80 % a propósito: el resto es la cola de los calendarios nacionales
    transcritos a mano, que ya están en su idioma y no deben tocarse. Si esto baja, es que ha
    entrado vocabulario nuevo de la OMS sin traducir.
    """
    sabidas = known_names()
    total = sum(publicados.values())
    cubierto = sum(
        veces
        for nombre, veces in publicados.items()
        if re.sub(r" — .*$", "", nombre).replace(" (some regions only)", "").strip() in sabidas
    )
    assert cubierto / total >= 0.80, (
        f"sólo el {cubierto * 100 // total} % de lo publicado tiene nombre traducido; "
        "mira config/vaccine_names.yaml"
    )


def test_el_calendario_sale_ya_traducido() -> None:
    """La traducción vive en `Vaccines.schedule()`, por donde pasan el chat, la cartilla, el
    `.ics` y el JSON del sitio. Si alguien la sube a una pantalla concreta, esto se cae."""
    from pedibot.bot.vaccines import Vaccines

    v = Vaccines(ROOT / "config" / "vaccines.yaml")
    en_espanol = [n for s in v.schedule("MA", "es") for n in s.vaccines]
    assert any("Vitamina A" in n for n in en_espanol)
    assert not any("a supplement, not a vaccine" in n for n in en_espanol)
