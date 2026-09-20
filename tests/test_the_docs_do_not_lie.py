"""Ningún documento dice una cifra que ya no es verdad (21-sep-2026).

El operador, repasando el proyecto: «nuestros archivos base, los `.md`, a veces tienen poca
consistencia, hay contradicciones entre ellos». Se midió antes de opinar: **107 cifras escritas
a mano** no cuadraban con los ficheros de datos. APP.md decía 88 países en tres sitios y 61
calendarios en cinco; WEB.md, 44 reglas de alarma cuando son 83 y 419 documentos cuando son 497.

**Ninguna estaba mal el día que se escribió.** Ése es el punto. Una cifra tecleada no discute
con nadie: el dato cambia y la frase se queda, y cuanto más útil es el documento más veces se ha
copiado esa frase. El resultado es un proyecto que se contradice consigo mismo justo en lo que
más presume de comprobar.

Tres piezas, y las tres hacen falta:

1. `DATOS.md`, generado, con todas las cifras contadas de los ficheros de verdad;
2. `scripts/check_docs.py`, que relee la prosa y dice dónde no cuadra;
3. esto, que lo ejecuta en cada suite.

Lo que el candado **no** persigue, que es la mitad de la regla: los diarios —`LESSONS.md`,
`STATE.md`, `IDEAS.md`—, el texto de MetaDAO tal y como se envió, el PRD original, y cualquier
frase que diga que su cifra es de otro momento («390 de las 483 guías **de entonces**»).
Perseguir eso obligaría a borrar frases verdaderas o a mentir cambiándoles el número.
"""

from __future__ import annotations

import sys

from pedibot.settings import ROOT

sys.path.insert(0, str(ROOT))


def test_ninguna_cifra_de_los_documentos_contradice_a_los_datos() -> None:
    from scripts.check_docs import revisa

    problemas = revisa()
    assert not problemas, (
        "cifras escritas a mano que ya no son verdad. Actualiza la frase, enlaza a DATOS.md, o "
        "marca que es histórica («de entonces», «contado el …»):\n\n  " + "\n  ".join(problemas)
    )


def test_datos_md_esta_generado_y_no_escrito_a_mano() -> None:
    """Si alguien lo edita a mano, la siguiente generación se lo lleva por delante sin avisar."""
    texto = (ROOT / "DATOS.md").read_text(encoding="utf-8")
    assert "Este fichero se genera. No se edita a mano." in texto
    assert "scripts/build_datos.py" in texto


def test_las_cifras_de_datos_md_son_las_de_los_ficheros() -> None:
    """El generado tiene que coincidir con lo que hay hoy; si no, está sin regenerar."""
    import re

    from scripts.build_datos import cifras

    texto = (ROOT / "DATOS.md").read_text(encoding="utf-8")
    desfasadas = []
    for nombre, d in cifras().items():
        # las pruebas automáticas se cuentan al generar y cambian con cada fichero nuevo: pedir
        # que cuadren al dígito obligaría a regenerar en cada commit, y eso se acaba ignorando
        if nombre == "pruebas automáticas":
            continue
        fila = re.search(rf"\|\s*{re.escape(nombre)}\s*\|\s*\*\*([\d.]+|—)\*\*", texto)
        assert fila, f"«{nombre}» no aparece en DATOS.md: regenera"
        escrito = fila.group(1).replace(".", "")
        if escrito != str(d["n"]):
            desfasadas.append(f"{nombre}: DATOS.md dice {escrito}, son {d['n']}")
    assert not desfasadas, (
        "DATOS.md está sin regenerar; corre `uv run python scripts/build_datos.py`:\n  "
        + "\n  ".join(desfasadas)
    )


def test_el_candado_perdona_lo_que_dice_ser_historico() -> None:
    """«390 de las 483 guías de entonces» es verdad y tiene que pasar."""
    from scripts.check_docs import HISTORICA

    assert HISTORICA.search("390 de las 483 guías de entonces colgaban de un solo enlace")
    assert HISTORICA.search("20 marcas con su concentración (contado el 7-sep-2026)")
    assert not HISTORICA.search("el proyecto tiene 61 calendarios de vacunas")


def test_los_diarios_estan_fuera_y_se_dice_por_que() -> None:
    """Un diario con cifras corregidas a posteriori es un historial falsificado."""
    from scripts.check_docs import DIARIOS

    for fichero in ("LESSONS.md", "STATE.md", "IDEAS.md", "METADAO.md"):
        assert fichero in DIARIOS, f"{fichero} debería estar exento"
        assert len(DIARIOS[fichero]) > 20, f"{fichero} está exento sin explicar por qué"


def test_el_candado_no_grita_cuando_la_cifra_es_de_africa() -> None:
    """«los 54 países del continente» es verdad y no es la cifra mundial.

    Salto el 21-sep-2026 con una frase correcta del borrador de Emergent Ventures. El descarte
    miraba sólo lo que iba **después** del número, y ahí «For Africa» iba delante. Un candado que
    grita cuando la frase es correcta se acaba ignorando, y entonces deja de servir.
    """
    from scripts.check_docs import revisa

    verdades = {"países con número de emergencia": 90, "marcas de medicamento": 35}
    frases = [
        "For Africa that means all 54 countries have their emergency number.",
        "En África son 54 países con número, y 31 países con alguna marca.",
        "Las marcas llegan a 31 países de África.",
    ]
    for frase in frases:
        assert not _revisa_texto(revisa, verdades, frase), f"no debería señalar: {frase}"


def test_el_candado_sigue_cogiendo_una_cifra_mundial_mal() -> None:
    """Y la otra mitad: que el arreglo de arriba no lo haya dejado ciego."""
    from scripts.check_docs import revisa

    verdades = {"países con número de emergencia": 90}
    problemas = _revisa_texto(revisa, verdades, "El proyecto cubre 88 países con su número.")
    assert problemas, "una cifra mundial equivocada tiene que seguir saltando"


def _revisa_texto(revisa, verdades: dict[str, int], frase: str) -> list[str]:
    """Escribe la frase en un `.md` de verdad, porque el candado lee del disco."""
    prueba = ROOT / "ops" / "_candado_de_prueba.md"
    prueba.write_text(frase + "\n", encoding="utf-8")
    try:
        return [p for p in revisa(verdades) if "_candado_de_prueba" in p]
    finally:
        prueba.unlink()


def test_el_candado_ve_la_cifra_aunque_haya_un_adjetivo_en_medio() -> None:
    """«288 published documents» era mentira y el candado no la veía.

    El fallo contrario al de arriba y peor: un candado silencioso da confianza. El texto del
    Show HN llevaba desde el 6-sep-2026 diciendo 288 documentos de 18 organismos —son 497 y 21—
    y el patrón no casaba porque entre el número y el sustantivo había un adjetivo.
    """
    from scripts.check_docs import revisa

    verdades = {"documentos del catálogo público": 497, "calendarios de vacunas": 66}
    mentiras = [
        "a corpus of 288 published documents from 18 bodies",
        "un corpus de 288 documentos publicados",
        "Plus vaccination schedules for 7 countries.",
    ]
    for frase in mentiras:
        assert _revisa_texto(revisa, verdades, frase), f"debería señalar: {frase}"


def test_el_candado_perdona_la_nota_que_explica_un_fallo() -> None:
    """«decía 288 documentos cuando son 497» es la frase más honesta del fichero.

    Si el detector del error obliga a borrar la explicación del error, sobra el detector.
    """
    from scripts.check_docs import revisa

    verdades = {"documentos del catálogo público": 497}
    frase = "Se recontaron el 21-sep-2026: decía 288 documentos cuando son 497"
    assert not _revisa_texto(revisa, verdades, frase)
