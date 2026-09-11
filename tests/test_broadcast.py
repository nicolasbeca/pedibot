"""Las dos publicaciones periódicas de Bluesky (11-sep-2026).

Encargo del operador: una del proyecto cada dos días, y una guía por idioma una vez a la semana.
Hasta hoy sólo se publicaba al generar una guía nueva, y como la generación se paró el 5-sep
—no había ningún timer que la lanzara— Bluesky llevaba una semana en silencio.

Lo que se vigila aquí es lo que puede salir mal sin que nadie lo vea:

- **Ninguna cifra inventada.** Las de los mensajes del proyecto se leen del índice y de los
  ficheros de configuración en el momento de publicar. `CLAUDE.md` lo prohíbe explícitamente
  desde el primer día por el dossier de 2025, y una publicación es «hacia fuera».
- **No repetir.** Ni el mismo mensaje dos veces seguidas, ni la misma guía hasta agotar las suyas.
- **Una por idioma**, con el enlace del idioma que dice ser.
- **Cabe en Bluesky**, que corta a 300.
"""

from __future__ import annotations

import json

import pytest

from pedibot.publish import broadcast


def test_los_numeros_salen_de_los_ficheros_y_no_del_texto():
    f = broadcast.facts()
    assert f["documents"] > 100, "se leen del índice de verdad"
    assert f["languages"] == 8
    assert f["guides"] > 100
    assert f["schedules"] >= 5
    # ninguna plantilla puede llevar un número escrito a mano: todos van por sustitución
    for plantillas in broadcast.PROJECT_POSTS.values():
        for t in plantillas:
            assert not any(c.isdigit() for c in t["text"].replace("{", "").replace("}", "")), t


def test_no_repite_mensaje_dos_veces_seguidas(tmp_path):
    estado = tmp_path / "s.json"
    vistos = [broadcast.project_post(state_path=estado).text() for _ in range(4)]
    assert len(set(vistos)) == 4, "cuatro publicaciones seguidas, cuatro mensajes distintos"


def test_da_la_vuelta_cuando_se_acaban_las_plantillas(tmp_path):
    estado = tmp_path / "s.json"
    n = sum(len(v) for v in broadcast.PROJECT_POSTS.values())
    textos = [broadcast.project_post(state_path=estado).text() for _ in range(n + 1)]
    assert textos[n] == textos[0], "al agotarlas vuelve a empezar, no se queda callado"


def test_una_guia_por_idioma_y_con_su_enlace(tmp_path):
    posts = broadcast.weekly_guides(state_path=tmp_path / "g.json")
    assert {p.lang for p in posts} == set(broadcast.LANGS)
    for p in posts:
        trozo = "/guides/" if p.lang == "en" else f"/{p.lang}/guides/"
        assert trozo in p.url, f"{p.lang} enlaza a {p.url}"
        assert p.title and p.summary


def test_no_repite_guia_hasta_agotar_las_de_su_idioma(tmp_path):
    estado = tmp_path / "g.json"
    primera = {p.lang: p.url for p in broadcast.weekly_guides(state_path=estado)}
    segunda = {p.lang: p.url for p in broadcast.weekly_guides(state_path=estado)}
    repetidas = [idioma for idioma in primera if primera[idioma] == segunda[idioma]]
    assert not repetidas, f"repite la misma guía la semana siguiente en {repetidas}"


@pytest.mark.parametrize("lang", ["en", "es"])
def test_todo_cabe_en_bluesky(lang, tmp_path):
    p = broadcast.project_post(lang=lang, state_path=tmp_path / f"{lang}.json")
    assert len(p.text()) <= 300
    for g in broadcast.weekly_guides(state_path=tmp_path / "g2.json"):
        assert len(g.text()) <= 300, g.lang


def test_el_estado_se_puede_leer_despues(tmp_path):
    estado = tmp_path / "s.json"
    broadcast.project_post(state_path=estado)
    assert json.loads(estado.read_text(encoding="utf-8")), "deja escrito qué publicó"


def test_sin_resumen_no_quedan_lineas_en_blanco_de_mas(tmp_path):
    """Los mensajes del proyecto no llevan resumen, y el formato de siempre dejaba tres saltos."""
    p = broadcast.project_post(state_path=tmp_path / "x.json")
    assert "\n\n\n" not in p.text()
    assert p.text().endswith(p.url)


def test_un_ensayo_no_gasta_el_turno(tmp_path):
    """`--dry-run` enseña lo siguiente; si además lo consumiera, mirar cambiaría lo publicado."""
    estado = tmp_path / "d.json"
    a = broadcast.project_post(state_path=estado, advance=False).text()
    b2 = broadcast.project_post(state_path=estado, advance=False).text()
    assert a == b2
    assert not estado.exists(), "un ensayo no deja estado escrito"
