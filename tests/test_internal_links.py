"""Every internal link and every hreflang points at a page that was built (5-sep-2026).

Written after walking them for the first time: 27.635 links, 74 dead, all of them the language
switcher on a medicine page.

A generic drug is not spelled the same everywhere — ibuprofeno / ibuprofen / ibuprofène — so each
edition builds its page at its own slug, and the switcher derived the other editions by swapping
the prefix on the current path. From /ar/dose/ibuprofen it offered /pt/dose/ibuprofen, which
Portuguese had built as /pt/dose/ibuprofeno.

The hreflang half is the one that mattered more: the same list feeds those tags, so on every one
of those pages Google was being told about translations that return 404. Nothing failed, nothing
logged, and no test looked — the guide templates had four separate locks and the dose pages had
none, which is how the same clone rot lived here after being cleaned out there.

Skipped when there is no build: `npm run build` in web/site makes one.
"""

from __future__ import annotations

import collections
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")

HREF = re.compile(r'href="(/[^"#?]*)')
ALT = re.compile(r'hreflang="[a-z-]+" href="https://pedibot\.xyz(/[^"]*)')


def built() -> set[str]:
    """Everything the build produced, by the URL that reaches it."""
    out: set[str] = set()
    for f in DIST.rglob("*"):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(DIST).as_posix()
        out.add(rel)
        if f.name == "index.html":
            out.add(rel[: -len("index.html")].rstrip("/") or "/")
    return out


def reachable(url: str, have: set[str]) -> bool:
    u = url.rstrip("/") or "/"
    return u in have or f"{u}/" in have or f"{u}/index.html" in have


@pytest.fixture(scope="module")
def have() -> set[str]:
    return built()


def test_no_internal_link_is_dead(have: set[str]) -> None:
    bad: collections.Counter[str] = collections.Counter()
    where: dict[str, str] = {}
    for f in DIST.rglob("*.html"):
        src = "/" + f.relative_to(DIST).parent.as_posix()
        for m in HREF.finditer(f.read_text(encoding="utf-8", errors="replace")):
            if not reachable(m.group(1), have):
                bad[m.group(1)] += 1
                where.setdefault(m.group(1), src)
    assert not bad, "\n".join(
        f"{n}× {u}  (p.ej. desde {where[u]})" for u, n in bad.most_common(10)
    )


def test_no_hreflang_promises_a_page_that_does_not_exist(have: set[str]) -> None:
    """Worse than a dead link in a menu: this is what the search engines are told."""
    bad: collections.Counter[str] = collections.Counter()
    for f in DIST.rglob("*.html"):
        for m in ALT.finditer(f.read_text(encoding="utf-8", errors="replace")):
            if not reachable(m.group(1), have):
                bad[m.group(1)] += 1
    assert not bad, "\n".join(f"{n}× {u}" for u, n in bad.most_common(10))


def test_a_medicine_offers_the_right_name_in_each_language(have: set[str]) -> None:
    """The concrete case, kept by name so a regression is recognisable: the same drug, eight
    editions, three different spellings, and every switch link has to land."""
    page = DIST / "ar" / "dose" / "ibuprofen" / "index.html"
    assert page.exists(), "la página árabe del ibuprofeno cambió de sitio"
    alts = ALT.findall(page.read_text(encoding="utf-8", errors="replace"))
    assert len(alts) >= 8, f"solo {len(alts)} alternativas"
    assert any(a.endswith("/ibuprofeno") for a in alts), "ninguna alternativa usa el slug español"
    for a in alts:
        assert reachable(a, have), a


#: the eight guide templates: one per language, identical apart from their language wiring
_TPLS = sorted((ROOT / "web" / "site" / "src" / "pages").glob("**/guides/[[]...slug[]].astro"))


def _lang_of(tpl: pathlib.Path) -> str:
    """English lives at the root, every other language under its own folder."""
    parts = tpl.relative_to(ROOT / "web" / "site" / "src" / "pages").parts
    return "en" if parts[0] == "guides" else parts[0]


def test_every_guide_offers_the_chat_at_the_top_and_the_bottom() -> None:
    """A guide's way into the chat used to be one button below the whole article. Somebody who
    arrives from a search reads a paragraph and leaves without ever scrolling to it, so the same
    door is offered again under the opening line (6-sep-2026).

    Source-level on purpose: this one runs without a build.
    """
    assert len(_TPLS) == 8, f"esperaba 8 plantillas de guía, hay {len(_TPLS)}"
    for tpl in _TPLS:
        src = tpl.read_text(encoding="utf-8")
        assert src.count('class="ask-top"') == 1, f"{tpl.name} [{_lang_of(tpl)}]: falta el de arriba"
        assert src.count("s.ask_about") == 1, f"{tpl.name} [{_lang_of(tpl)}]: falta el de abajo"


def test_a_guide_never_sends_its_reader_to_another_language_chat() -> None:
    """The clone rot, in the place it would hurt most: a Spanish guide whose button opens the
    English chat. Both links in a file must carry that file's own prefix."""
    bad: list[str] = []
    for tpl in _TPLS:
        lang = _lang_of(tpl)
        want = "/?q=" if lang == "en" else f"/{lang}?q="
        found = re.findall(r"href=\{`(/[a-z]{0,2}\?q=)\$\{encodeURIComponent", tpl.read_text(encoding="utf-8"))
        assert len(found) == 2, f"{tpl.name}: esperaba dos enlaces al chat, hay {len(found)}"
        bad += [f"[{lang}] apunta a {f}, debería ser {want}" for f in found if f != want]
    assert not bad, "\n".join(bad)


def test_the_map_for_language_models_is_not_an_orphan() -> None:
    """/llms.txt is written for the assistants that answer questions from the web, and in thirty
    days not one of them had ever fetched it: it was mentioned only in a robots.txt COMMENT,
    which no crawler reads, and nothing on the site linked to it.

    The law measured on 4-sep is that crawling follows the link graph — 92% of pages one click
    from the homepage, 0% of orphans — so it now hangs off every page, in the head and the foot.
    """
    base = (ROOT / "web" / "site" / "src" / "layouts" / "Base.astro").read_text(encoding="utf-8")
    assert 'href="/llms.txt"' in base, "la cabecera ya no declara llms.txt"
    # 19-sep-2026: el enlace visible se mudó del pie a /sources. Lo pidió el operador leyendo su
    # propio pie —«¿qué es eso de llms.txt?»—, y si lo pregunta él, un padre ni lo pregunta. Lo
    # que esta prueba defiende no es DÓNDE está el enlace sino que exista uno: el rastreo sigue
    # los enlaces y un fichero al que no apunta nada no se visita nunca.
    fuentes = list((ROOT / "web" / "site" / "src" / "pages").glob("**/sources.astro"))
    assert fuentes, "no hay páginas de fuentes donde colgarlo"
    con_enlace = [f for f in fuentes if ">llms.txt</a>" in f.read_text(encoding="utf-8")]
    assert len(con_enlace) == len(fuentes), (
        f"sólo {len(con_enlace)} de {len(fuentes)} páginas de fuentes lo enlazan"
    )


#: las ocho páginas por medicamento: idénticas salvo idioma y prefijo de URL
_DOSE_TPLS = sorted((ROOT / "web" / "site" / "src" / "pages").glob("**/dose/[[]slug[]].astro"))


def test_every_medicine_page_carries_the_calculator() -> None:
    """Search Console, primera lectura real (6-sep): la única demanda no de marca que nos alcanza
    son consultas de dosis por marca, y casi todas llevan la palabra «calculadora» — «calculadora
    apiretal», «apirofeno 40 mg calculadora», «calcular dosis apiretal».

    La página era una tabla de 36 filas. Meter la palabra en el título sin más habría sido una
    afirmación falsa; ahora la página lleva la calculadora de verdad, con su fármaco puesto, y por
    eso el título puede decirlo. El candado impide que se separen otra vez.
    """
    assert len(_DOSE_TPLS) == 8, f"esperaba 8 plantillas de medicamento, hay {len(_DOSE_TPLS)}"
    for tpl in _DOSE_TPLS:
        src = tpl.read_text(encoding="utf-8")
        assert "<DoseCalc" in src, f"{tpl.name}: la página promete calculadora y no la lleva"
        assert "drug={name}" in src, f"{tpl.name}: la calculadora no viene con su fármaco puesto"


def test_security_txt_has_not_expired() -> None:
    """El RFC 9116 obliga a un campo Expires, y un security.txt caducado se ignora: quien
    encuentre un fallo se queda sin saber a quién avisar. Avisa dos meses antes en vez de
    caducar en silencio."""
    import datetime as dt

    p = ROOT / "web" / "site" / "public" / ".well-known" / "security.txt"
    assert p.exists(), "no hay security.txt"
    m = re.search(r"^Expires:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
    assert m, "security.txt sin campo Expires — el RFC lo exige"
    when = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    quedan = (when - dt.datetime.now(dt.UTC)).days
    assert quedan > 60, f"security.txt caduca en {quedan} días: renueva la fecha"


def test_no_page_loads_anything_from_a_third_party(have: set[str]) -> None:
    """El pie de cada página y /legal prometen «sin rastreadores de terceros». Hasta el 6-sep-2026
    cada carga pedía el CSS a fonts.googleapis.com, que recibía la IP y el navegador del lector
    antes de que la página se pintara, y después los ficheros a fonts.gstatic.com.

    Google Fonts no es un rastreador publicitario. Pero es un tercero que el lector no eligió, la
    frase dice «terceros», y el mayor público de esta web en Google es Alemania, donde un tribunal
    de Múnich declaró en 2022 que incrustarlo sin consentimiento vulnera el RGPD por esa
    transmisión. Ahora las tipografías se sirven desde aquí (licencia SIL OFL).

    Un ENLACE a otro dominio no cuenta: no envía nada hasta que alguien lo pulsa. Lo que se
    comprueba es lo que el navegador se descarga solo.
    """
    carga = re.compile(
        r'<(?:script|img|iframe|source|video|audio|embed)\b[^>]*\bsrc="(https?://[^"]+)"'
        r'|<link\b[^>]*\brel="(?:stylesheet|preconnect|preload|dns-prefetch)"[^>]*\bhref="(https?://[^"]+)"'
        r'|<link\b[^>]*\bhref="(https?://[^"]+)"[^>]*\brel="(?:stylesheet|preconnect|preload|dns-prefetch)"',
        re.I,
    )
    ajenos: list[str] = []
    for f in sorted(DIST.rglob("*.html")):
        for grupos in carga.findall(f.read_text(encoding="utf-8", errors="ignore")):
            url = next((g for g in grupos if g), "")
            host = url.split("/")[2] if url.count("/") >= 2 else ""
            if host and not host.endswith("pedibot.xyz"):
                ajenos.append(f"{f.relative_to(DIST)} carga {host}")
    assert not ajenos, "\n".join(sorted(set(ajenos))[:15])


def test_every_page_family_has_a_door_from_a_well_crawled_page(have: set[str]) -> None:
    """Un grupo de páginas que solo se enlazan entre ellas no se rastrea, por muchos enlaces que
    tenga: vienen de páginas igual de olvidadas.

    Pasó dos veces. El 4-sep con las 120 páginas de marca de dosis, que se enlazaban entre ellas y
    nada del sitio entraba. Y el 7-sep con los calendarios de vacunas: cada uno tenía CATORCE
    enlaces entrantes y **trece venían de otro calendario**. Google no conocía 31 de las 56, siendo
    la categoría que mejor posiciona de toda la web.

    Lo que se comprueba no es el número de enlaces sino la ley medida contra 45 días de Googlebot:
    se rastreó el 100% de lo que está a un clic de una portada, ~50% a dos o tres, y el 0% de lo
    huérfano. Hace falta al menos una puerta desde una página que Google ya visita.
    """
    HREF = re.compile(r'<a\b[^>]*?href="([^"]+)"', re.I)
    EXT = re.compile(r"^(https?:|mailto:|tel:|#|javascript:)", re.I)

    def limpia(p: str) -> str:
        p = p.split("#")[0].split("?")[0]
        return ("/" + p.lstrip("/")).rstrip("/") or "/"

    salidas: dict[str, set[str]] = {}
    for f in DIST.rglob("*.html"):
        rel = "/" + str(f.relative_to(DIST)).replace("\\", "/")
        rel = limpia(
            rel[: -len("index.html")] if rel.endswith("/index.html") else rel[: -len(".html")]
        )
        salidas[rel] = {
            limpia(h)
            for h in HREF.findall(f.read_text(encoding="utf-8", errors="ignore"))
            if not EXT.match(h)
        }

    # anchura primero desde cada portada de idioma, que es como llega un rastreador
    # el inglés vive en la raíz; los otros siete llevan prefijo
    otros = ("es", "fr", "de", "ru", "ar", "pt", "hi")
    raices = [r for r in ["/"] + [f"/{x}" for x in otros] if r in salidas]
    profundidad = {r: 0 for r in raices}
    cola = list(raices)
    while cola:
        cur = cola.pop(0)
        for nxt in salidas.get(cur, ()):
            if nxt in salidas and nxt not in profundidad:
                profundidad[nxt] = profundidad[cur] + 1
                cola.append(nxt)

    entrantes: dict[str, set[str]] = {}
    for src, outs in salidas.items():
        for o in outs:
            if o in salidas and o != src:
                entrantes.setdefault(o, set()).add(src)

    #: familias numerosas que tienden a enlazarse solo entre ellas
    FAMILIAS = {
        "calendarios de vacunas": re.compile(r"^(/[a-z]{2})?/vaccines/[a-z]{2}$"),
        "dosis por medicamento": re.compile(r"^(/[a-z]{2})?/dose/[a-z0-9-]+$"),
    }

    sin_puerta: list[str] = []
    for nombre, patron in FAMILIAS.items():
        miembros = {p for p in salidas if patron.match(p)}
        assert miembros, f"no encuentro ninguna página de «{nombre}»"
        for pagina in sorted(miembros):
            puertas = {
                s
                for s in entrantes.get(pagina, set())
                if not patron.match(s) and profundidad.get(s, 99) <= 1
            }
            if not puertas:
                sin_puerta.append(
                    f"[{nombre}] {pagina}: {len(entrantes.get(pagina, set()))} enlaces entrantes "
                    "y ninguno desde una página a un clic de la portada"
                )
    assert not sin_puerta, "\n".join(sin_puerta[:12])


def test_the_vaccine_calendars_are_linked_from_their_guide(have: set[str]) -> None:
    """El puente que se construyó el 7-sep. La guía de vacunas de cada idioma no enlazaba ningún
    calendario —cero— así que la única puerta de los 56 era la herramienta por edades. Ahora hay
    dos, y la segunda viene de otro grupo temático, que es lo que rompe la isla."""
    HREF = re.compile(r'href="((?:/[a-z]{2})?/vaccines/[a-z]{2})"')
    # se detecta por lo que hace, no por cómo se llama: el nombre del fichero cambia en cada
    # idioma («cuales_son_las_vacunas…», «welche_impfungen…», «bachchon_ke_teeke…»)
    con_enlaces = [
        f
        for f in DIST.rglob("*.html")
        if "/guides/" in str(f).replace("\\", "/")
        and HREF.search(f.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert len(con_enlaces) >= 8, (
        f"solo {len(con_enlaces)} guías enlazan un calendario; debería haber una por idioma"
    )


def test_the_hashed_assets_are_cached_and_the_rest_revalidates() -> None:
    """La regla de caché del Caddyfile, comprobada en el fichero porque es donde se rompe.

    El 6-sep las tipografías pasaron a servirse desde aquí, y cayeron del lado que revalida en
    cada carga: 23 idas y vueltas por página para quien ya las tenía, peor que como estaban en
    gstatic. El nombre que Google les puso ya lleva su hash de contenido, así que se cachean igual
    que /_astro/.

    El HTML tiene que seguir revalidando: sin eso, un despliegue es invisible para quien ya había
    visitado la web (pasó el 1-sep).
    """
    caddy = (ROOT / "ops" / "Caddyfile").read_text(encoding="utf-8")
    m = re.search(r"@hashed path ([^\n]+)", caddy)
    assert m, "no encuentro la regla de assets con hash"
    con_hash = m.group(1).split()
    assert "/_astro/*" in con_hash, "los assets construidos ya no se cachean"
    assert "/fonts/*.woff2" in con_hash, "las tipografías revalidan en cada carga"

    m2 = re.search(r"@revalidate not path ([^\n]+)", caddy)
    assert m2, "no encuentro la regla de revalidación"
    assert sorted(m2.group(1).split()) == sorted(con_hash), (
        "las dos reglas de caché ya no son complementarias: alguna ruta se queda sin regla o con dos"
    )


def test_el_sitemap_no_contradice_al_html_sobre_los_idiomas() -> None:
    """El sitemap no declara hreflang: lo declara el HTML, que es el que acierta (9-sep-2026).

    Este mismo fichero cuenta arriba cómo el conmutador de idiomas ofrecía /pt/dose/ibuprofen
    cuando el portugués había construido /pt/dose/ibuprofeno. Aquello se arregló el 5-sep en el
    HTML, y **el sitemap se quedó con el fallo cuatro días más**, porque nadie miró la segunda
    superficie: `@astrojs/sitemap` con la opción `i18n` empareja las URLs por su prefijo de
    idioma, y en este sitio la rebanada cambia con la lengua.

    Medido antes de quitarlo: el HTML de /dose/ibuprofen declaraba las ocho ediciones más la
    x-default, y el sitemap declaraba **cinco** — ar, de, en, hi, ru, las que casualmente
    comparten rebanada— dejando el castellano y el portugués en un grupo aparte y el francés
    huérfano. Las 483 guías, cuya rebanada también cambia por idioma, se quedaban con cero.

    Google lee las dos fuentes. Una que a veces miente no aporta una señal de más: quita la buena.
    """
    sitemap = (DIST / "sitemap-0.xml").read_text(encoding="utf-8")
    assert "xhtml:link" not in sitemap, (
        "el sitemap ha vuelto a declarar hreflang; si vuelve la opción `i18n` de @astrojs/sitemap, "
        "volverá a agrupar por prefijo de URL y a contradecir al HTML en las páginas cuya "
        "rebanada cambia con el idioma (los fármacos y las 483 guías)"
    )
    # lo que sí tiene que seguir estando
    assert sitemap.count("<loc>") == sitemap.count("<lastmod>") > 700, (
        "el sitemap ha perdido URLs o fechas al quitarle el hreflang"
    )


def test_cada_farmaco_declara_sus_ocho_ediciones_en_el_html() -> None:
    """Y la otra mitad: si el sitemap ya no lo dice, el HTML tiene que decirlo entero.

    Se comprueba justo en las páginas donde la rebanada cambia con la lengua, que son las que
    rompieron las dos veces.
    """
    faltan = []
    for f in sorted((DIST / "dose").glob("*/index.html")):
        html = f.read_text(encoding="utf-8")
        idiomas = set(re.findall(r'rel="alternate" hreflang="([a-z-]+)"', html))
        esperadas = {"en", "es", "fr", "de", "ru", "ar", "pt", "hi", "x-default"}
        if not esperadas <= idiomas:
            faltan.append(f"{f.parent.name}: sin {sorted(esperadas - idiomas)}")
    assert not faltan, "páginas de fármaco con el grupo de idiomas incompleto:\n" + "\n".join(faltan)


def test_ninguna_guia_cuelga_de_un_solo_enlace() -> None:
    """El reparto de enlaces internos, que nadie había contado (9-sep-2026).

    Search Console lo dijo de la guía portuguesa de la meningitis: «Página de referencia: no se
    ha detectado ninguna». Al contarlo salió que **390 de las 483 guías recibían un único enlace
    interno** —el índice de su idioma, que lista sesenta— y 24 recibían más de sesenta.

    La causa estaba en `relatedTo`: agrupaba por `topic` exacto, y cada tema tiene UNA sola guía
    por idioma, así que el grupo salía siempre vacío y el sustituto eran «las tres más recientes»
    —las mismas para las sesenta guías de la lengua—. Para un dominio nuevo, una página que
    cuelga de un solo enlace dentro de un índice de sesenta es una página que el rastreador no
    llega a visitar, y Google decía exactamente eso: «no reconozco esta URL».

    Los hreflang NO cuentan aquí. Son una señal de idioma entre versiones de la misma página, no
    un camino por el que se descubre contenido nuevo, y contarlos escondía el problema: la guía
    de la meningitis parecía tener ocho enlaces y tenía uno.

    Medido después del arreglo: mínimo 3, máximo 13, media 7,1.
    """
    paginas = {}
    for f in DIST.rglob("index.html"):
        rel = "/" + f.relative_to(DIST).as_posix()
        # una redirección no es una guía: es la dirección vieja de una que se volvió a generar
        # con otro título, lleva `noindex` y nadie la enlaza a propósito (16-sep-2026)
        if '<meta http-equiv="refresh"' in f.read_text(encoding="utf-8", errors="ignore")[:600]:
            continue
        paginas[rel[: -len("index.html")].rstrip("/") or "/"] = f

    alterna = re.compile(r'rel="alternate" hreflang="[a-z-]+" href="https://pedibot\.xyz(/[^"]*)"')
    entrantes: dict[str, set[str]] = collections.defaultdict(set)
    for u, f in paginas.items():
        html = f.read_text(encoding="utf-8", errors="ignore")
        idiomas = set(alterna.findall(html))
        for destino in set(HREF.findall(html)):
            d = destino.rstrip("/") or "/"
            if d != u and d not in idiomas and d in paginas:
                entrantes[d].add(u)

    guias = [u for u in paginas if "/guides/" in u]
    pobres = sorted(u for u in guias if len(entrantes[u]) < 3)
    assert not pobres, (
        f"{len(pobres)} guías con menos de 3 enlaces internos entrantes (sin contar hreflang); "
        f"el anillo de `relatedTo` debería garantizar el suelo:\n" + "\n".join(pobres[:15])
    )


def test_cada_tema_publicado_tiene_categoria_en_la_taxonomia() -> None:
    """Un tema sin categoría enlaza mal y, sobre todo, se busca peor.

    Al clasificar los temas para enlazar las guías, diez de los 69 no casaban con ninguna
    categoría: meningitis, infección de orina, conjuntivitis, dentición, piojos, lombrices,
    picaduras, enuresis, dolores de crecimiento y salud mental del adolescente.

    Lo que lo hace importante no son los enlaces: la taxonomía es la que le pone tema a la
    pregunta del padre, y **sin tema la puerta del «fuente o silencio» pasa de exigir un término
    a exigir tres** (L76, escrita por esto mismo con las enfermedades exantemáticas). Había guías
    publicadas de los diez temas y el chat las alcanzaba peor que las de fiebre, sin ninguna
    razón clínica.
    """
    import json

    mapa = json.loads(
        (ROOT / "web" / "site" / "src" / "data" / "topic_category.json").read_text(encoding="utf-8")
    )
    temas = set()
    for md in (ROOT / "web" / "content").rglob("*.md"):
        m = re.search(r"^topic:\s*(.+)$", md.read_text(encoding="utf-8")[:2000], re.M)
        if m:
            temas.add(m.group(1).strip())
    sin = sorted(t for t in temas if t not in mapa)
    assert not sin, (
        "temas publicados que la taxonomía no clasifica (enlazan mal y se buscan peor):\n"
        + "\n".join(sin)
    )
