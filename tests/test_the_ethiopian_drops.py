"""Las gotas etíopes de paracetamol, que no estaban y eran las peligrosas (20-sep-2026).

Buscando marcas para los 23 países africanos que no tenían ninguna, el registro del regulador
etíope —la EFDA, lista de medicamentos sin receta— no da marcas, pero da algo mejor: **las
concentraciones que se venden allí**, en una tabla, con nombre y forma farmacéutica.

    5. Paracetamol
       100mg/5ml       Drops       1 bottle
       125mg, 250mg    Suppository 10 suppositories
       120mg/5ml, 250mg/5ml  Syrup 1 bottle

Las dos de jarabe ya estaban. **Las gotas no.** Y ahí está el problema, que no es de cobertura
sino de seguridad:

- en Etiopía las gotas de paracetamol son **100 mg/5 ml**, o sea 20 mg/ml;
- en España, en Portugal o en la India las gotas son **100 mg/ml**, cinco veces más concentradas;
- y hasta hoy la calculadora sólo ofrecía la segunda.

O sea que un padre en Adís Abeba con su bote de gotas en la mano leía «gotas» en el envase,
encontraba «gotas 100 mg/ml» en nuestra lista, y **le daba cinco veces la dosis**. No es un caso
rebuscado: es lo que hace cualquiera que busca en una lista la palabra que pone en su bote.

Es exactamente el fallo que este proyecto existe para no cometer, y llevaba escrito en su propia
cabecera desde el principio: «la concentración es lo que cambia y lo que los padres confunden».
"""

from __future__ import annotations

import pytest

from pedibot.bot.dose import DRUGS, bottles_in_country, calculate


def _etiquetas(key: str) -> list[str]:
    return list(calculate(key, 10.0, 24).ml.keys())


def test_las_gotas_de_100_mg_por_5_ml_existen() -> None:
    etiquetas = _etiquetas("paracetamol")
    assert any("100 mg/5 ml" in e for e in etiquetas), (
        "las gotas etíopes no están: un padre de allí tiene que elegir entre una fila que le "
        f"queda corta y otra que le multiplica por cinco. {etiquetas}"
    )


def test_la_de_cinco_veces_mas_sigue_estando_y_se_distinguen() -> None:
    """Las dos tienen que convivir y no poder confundirse leyendo la etiqueta."""
    etiquetas = _etiquetas("paracetamol")
    floja = next(e for e in etiquetas if "100 mg/5 ml" in e)
    fuerte = next(e for e in etiquetas if "100 mg/ml" in e and "/5" not in e)
    assert floja != fuerte
    r = calculate("paracetamol", 10.0, 24)
    assert r.ml[floja] == pytest.approx(r.ml[fuerte] * 5, rel=0.02), (
        "si una es cinco veces la otra, los mililitros tienen que salir cinco veces mayores"
    )


def test_un_nino_de_10_kg_en_etiopia_no_recibe_la_dosis_de_las_gotas_fuertes() -> None:
    """El caso concreto, con números, que es lo que hace que esto no se rompa sin avisar."""
    r = calculate("paracetamol", 10.0, 24)
    floja = next(e for e in r.ml if "100 mg/5 ml" in e)
    assert 7.0 <= r.ml[floja] <= 8.0, f"a 20 mg/ml, 150 mg salen unos 7,5 ml; salen {r.ml[floja]}"


def test_etiopia_tiene_sus_concentraciones_y_salen_primero() -> None:
    """No lleva marca a propósito: el regulador publica las concentraciones, no los nombres."""
    formas = bottles_in_country(DRUGS, "paracetamol", "ET")
    assert formas, "Etiopía debería traer las concentraciones de la lista de la EFDA"
    assert any("100 mg/5 ml" in f for f in formas)
    assert any("120 mg/5 ml" in f for f in formas)
    assert any("250 mg/5 ml" in f for f in formas)
    assert bottles_in_country(DRUGS, "ibuprofeno", "ET"), "el ibuprofeno etíope también consta"


def test_lo_del_pais_va_delante_en_la_tabla() -> None:
    """Para lo que sirve todo esto: que la fila de su bote sea la primera que ve.

    Se busca por la concentración y no por la etiqueta entera, porque «gotas»/«jarabe» se
    traducen al idioma del lector y la cifra no.
    """
    from pedibot.bot.dose import format_result

    r = calculate("paracetamol", 10.0, 24)
    texto = format_result(r, "en", country_forms=bottles_in_country(DRUGS, "paracetamol", "ET"))
    sitio = {c: texto.find(c) for c in ("100 mg/5 ml", "250 mg/5 ml", "150 mg/5 ml", "160 mg/5 ml")}
    assert all(v >= 0 for v in sitio.values()), sitio
    etiopes = max(sitio["100 mg/5 ml"], sitio["250 mg/5 ml"])
    otras = min(sitio["150 mg/5 ml"], sitio["160 mg/5 ml"])
    assert etiopes < otras, f"en Etiopía, sus botes van delante: {sitio}"


def test_sin_pais_la_tabla_no_cambia_de_orden() -> None:
    """Que lo de Etiopía no reordene la tabla de quien no ha dicho de dónde es."""
    from pedibot.bot.dose import format_result

    r = calculate("paracetamol", 10.0, 24)
    assert format_result(r, "en") == format_result(r, "en", country_forms=[])


def test_las_concentraciones_de_un_pais_dicen_de_donde_salen() -> None:
    """Una lista de concentraciones sin fuente es una suposición con formato de dato."""
    import yaml

    from pedibot.settings import ROOT

    d = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))
    paises = d.get("country_forms") or {}
    assert paises, "no hay concentraciones por país"
    for code, v in paises.items():
        assert v.get("source"), f"{code} sin fuente"
        assert str(v.get("url", "")).startswith("http"), f"{code} sin enlace comprobable"


# ── el barrido, que es lo que evita que esto vuelva a pasar ────────────────────────────────
#: Las presentaciones pediátricas líquidas de la Lista Modelo de Medicamentos Esenciales de la
#: OMS, 24.ª edición (2025), leída del PDF en IRIS el 20-sep-2026. Es el documento del que
#: derivan las listas nacionales de casi todos los países de renta baja, así que cubrirlo entero
#: es cubrir la estantería de la mayoría de nuestros mercados de una vez.
#:
#: Y trae un aviso de la propia OMS que conviene tener delante, al pie de la fila del
#: paracetamol: «The presence of both 120 mg/5 mL and 125 mg/5 mL strengths on the same market
#: would cause confusion in prescribing and dispensing and should be avoided». Nosotros tenemos
#: las dos a la fuerza —un padre puede tener cualquiera de ellas— y por eso la etiqueta lleva
#: siempre la concentración entera y el texto termina diciendo que mire el bote.
OMS_EMLC = {
    "paracetamol": [24.0, 25.0, 50.0],  # 120, 125 y 250 mg/5 ml
    "ibuprofeno": [20.0, 40.0],  # 100 y 200 mg/5 ml
}
OMS_FUENTE = (
    "WHO — The selection and use of essential medicines, 2025: WHO Model List of Essential "
    "Medicines (24th list) and Model List of Essential Medicines for Children (10th list). "
    "https://iris.who.int/handle/10665/b130c465"
)


@pytest.mark.parametrize(("key", "fuerzas"), OMS_EMLC.items())
def test_estan_todas_las_concentraciones_que_la_oms_recomienda(
    key: str, fuerzas: list[float]
) -> None:
    """Si la OMS la recomienda, un padre puede tenerla en la mano. Tiene que estar en la tabla.

    Esto no es cobertura por gusto: el caso etíope enseñó que una concentración que falta no
    deja al padre sin respuesta, le empuja a la fila de al lado. Y la de al lado puede ser cinco
    veces más fuerte.
    """
    tabla = {p.mg_per_ml for p in DRUGS[key].presentations}
    faltan = [f for f in fuerzas if not any(abs(f - x) < 0.05 for x in tabla)]
    assert not faltan, (
        f"{key}: la OMS recomienda {faltan} mg/ml y no están en la tabla. Fuente: {OMS_FUENTE}"
    )


def test_ninguna_concentracion_esta_dos_veces() -> None:
    """Dos filas con la misma concentración y distinta etiqueta son una trampa, no una opción."""
    for key in ("paracetamol", "ibuprofeno"):
        fuerzas = [p.mg_per_ml for p in DRUGS[key].presentations]
        assert len(fuerzas) == len(set(fuerzas)), f"{key}: {fuerzas}"


def test_las_gotas_van_juntas_y_no_abren_la_tabla() -> None:
    """La corrección de mi propio fallo, media hora después y mirando la web viva.

    Al añadir las gotas etíopes, el orden puramente ascendente las puso LAS PRIMERAS. Y ahí
    aparecía un riesgo nuevo, peor que el que venía a arreglar: un padre en España con Apiretal
    —gotas de 100 mg/**ml**— que no hubiera elegido país veía «gotas» en la primera línea, le
    daba los 7,5 ml de esa fila, y eran 750 mg en vez de 150. Cinco veces de más, y esta vez en
    la dirección mala.

    Agrupadas por forma, las tres presentaciones de gotas quedan seguidas: quien busca «gotas»
    las ve juntas y tiene que leer la concentración para elegir, que es lo que hay que obligarle
    a hacer.
    """
    for key in ("paracetamol", "ibuprofeno"):
        nombres = [p.name for p in DRUGS[key].presentations]
        assert not nombres[0].startswith("gotas"), (
            f"{key}: la tabla no puede abrir con unas gotas; la primera línea es la que se lee "
            f"sin leer. {nombres}"
        )
        indices = [i for i, n in enumerate(nombres) if n.startswith("gotas")]
        if len(indices) > 1:
            assert indices == list(range(indices[0], indices[0] + len(indices))), (
                f"{key}: las gotas tienen que ir seguidas para que se comparen. {nombres}"
            )


def test_dentro_de_cada_forma_van_de_menos_a_mas_concentrada() -> None:
    """Agrupar no puede servir de excusa para desordenar: dentro del grupo, ascendente."""
    for key in ("paracetamol", "ibuprofeno"):
        grupos: dict[str, list[float]] = {}
        for p in DRUGS[key].presentations:
            grupos.setdefault(p.name.split(" ")[0], []).append(p.mg_per_ml)
        for forma, fuerzas in grupos.items():
            assert fuerzas == sorted(fuerzas), f"{key} / {forma}: {fuerzas}"


# ── los países leídos a ojo, uno por uno ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("pais", "espera"),
    [
        # Etiopía espera «120» y no sus gotas de «100 mg/5 ml»: tiene las tres, y desde que la
        # tabla agrupa por forma (L216) los jarabes van antes que las gotas. Que sus gotas estén
        # promocionadas por delante de las otras gotas se comprueba aparte, más abajo.
        ("ET", "120 mg/5 ml"),
        ("RW", "125 mg/5 ml"),  # Ruanda: 125, no 120, que es el par que la OMS avisa de no mezclar
        ("MZ", "125 mg/5 ml"),
        ("CD", "125 mg/5 ml"),
    ],
)
def test_cada_pais_leido_ve_su_bote_primero(pais: str, espera: str) -> None:
    """Para esto sirve todo el trabajo de leer PDF: que su fila sea la primera que ve."""
    from pedibot.bot.dose import format_result
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.settings import ROOT

    cat = DrugCatalog(ROOT / "config" / "drugs.yaml")
    r = calculate("paracetamol", 10.0, 24)
    texto = format_result(r, "en", country_forms=bottles_in_country(cat, "paracetamol", pais))
    primera = next(x.strip() for x in texto.split("\n") if x.strip().startswith("–"))
    assert espera in primera, f"{pais}: la primera fila es «{primera}» y debería llevar {espera}"


def test_las_gotas_etiopes_van_por_delante_de_las_otras_gotas() -> None:
    """La otra mitad de lo de Etiopía: entre las tres presentaciones de gotas, la suya primero."""
    from pedibot.bot.dose import format_result
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.settings import ROOT

    cat = DrugCatalog(ROOT / "config" / "drugs.yaml")
    r = calculate("paracetamol", 10.0, 24)
    texto = format_result(r, "en", country_forms=bottles_in_country(cat, "paracetamol", "ET"))
    suyas = texto.find("100 mg/5 ml")
    otras = min(texto.find("100 mg/ml"), texto.find("200 mg/ml"))
    assert 0 <= suyas < otras, f"suyas en {suyas}, las otras gotas en {otras}"


def test_en_el_congo_el_ibuprofeno_fuerte_va_primero() -> None:
    """Su lista infantil dice 200 mg/5 ml, el DOBLE de lo habitual.

    Un padre congoleño que cogiera la fila de 100 mg/5 ml le daría la mitad de lo que necesita.
    No es el error peligroso —quedarse corto no hace daño— pero es el error, y se evita.
    """
    from pedibot.bot.dose import format_result
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.settings import ROOT

    cat = DrugCatalog(ROOT / "config" / "drugs.yaml")
    r = calculate("ibuprofeno", 10.0, 24)
    texto = format_result(r, "en", country_forms=bottles_in_country(cat, "ibuprofeno", "CD"))
    primera = next(x.strip() for x in texto.split("\n") if x.strip().startswith("–"))
    assert "200 mg/5 ml" in primera, primera


def test_madagascar_no_trae_paracetamol_y_eso_es_deliberado() -> None:
    """Su lista dice «125 mg/ml», que serían 625 mg por cada 5 ml.

    No se puede saber desde aquí si es un producto real o una errata del documento, y las dos
    posibilidades piden lo contrario: si es real falta la fila, y si es errata añadirla crea una
    confundible con «125 mg/5 ml» que llevaría a multiplicar por cinco. Se queda fuera hasta
    tener una segunda fuente — y mientras tanto un padre de allí puede escribir su concentración
    en la calculadora, que para eso está.
    """
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.settings import ROOT

    cat = DrugCatalog(ROOT / "config" / "drugs.yaml")
    assert bottles_in_country(cat, "ibuprofeno", "MG"), "el ibuprofeno de Madagascar sí es claro"
    assert bottles_in_country(cat, "paracetamol", "MG") == [], (
        "el paracetamol de Madagascar no entra sin una segunda fuente"
    )
