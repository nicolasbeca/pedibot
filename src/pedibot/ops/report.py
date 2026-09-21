"""Metrics shared by the weekly Telegram report and the /admin panel (operator-only)."""

from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import json
import re
import sqlite3
import subprocess
import sys
from typing import Any

from pedibot.ops.store import NOT_REAL, REAL_ONLY
from pedibot.settings import ROOT

_STATIC = re.compile(
    r"\.(xml|svg|png|ico|css|js|txt|woff2?|webmanifest)$|^/_astro/|^/api/|^/a/|^/admin", re.I
)
# Nombres que se identifican solos. Los cuatro últimos salieron de mirar quién pedía más en
# el registro: un raspador y un navegador headless que no llevan «bot» en ninguna parte.
_BOT_UA = re.compile(
    r"bot|crawl|spider|curl|python|monitor|wget|httpx|scraper|domainworkers|lightpanda"
    r"|headless|puppeteer|playwright|phantomjs|go-http|okhttp|node-fetch|axios|java/|slurp",
    re.I,
)

#: Redes de rastreo que Google **publica** como suyas. Su renderizador pide la página entera con
#: un agente de Chrome corriente, sin «bot» por ningún lado: por agente es indistinguible de un
#: padre, y por dirección es evidente. 897 vistas en catorce días venían de aquí.
_CRAWLER_NETS = (ipaddress.ip_network("66.249.64.0/19"),)


def _de_rastreador(ip: object) -> bool:
    try:
        addr = ipaddress.ip_address(str(ip))
    except ValueError:
        return False
    return any(addr in net for net in _CRAWLER_NETS)


def _who(ip: object, ua: str) -> str:
    """A visitor, as the panel has always counted one: address and browser together, hashed. The
    hash is computed to be compared with other hashes and is never written anywhere."""
    return hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:16]


#: Cuánto dura la marca de una IP nuestra, hacia atrás y hacia delante. Las IP domésticas cambian
#: de manos: marcarla para siempre acabaría escondiendo al vecino que la herede. Un día se quedaba
#: corto, medido sobre el registro real (13-sep-2026): 80 páginas del Chrome de casa del operador
#: se colaban el 27-ago y el 2-3-sep, días sin panel abierto cerca. Esa IP fue nuestra dos semanas
#: seguidas; con siete días se tapa, y el riesgo es esconder una semana a quien la herede.
TEAM_WINDOW = 7 * 86_400.0


def _team_marks(lines: list[str]) -> dict[str, list[float]]:
    """Las IP que son nuestras, con los momentos en que lo demostraron (13-sep-2026).

    Dos pruebas, y las dos son de nosotros por construcción:

    - **abrió /admin** con contraseña (200). Sólo abierto, no pedido: 65 navegadores han pedido
      /admin a este servidor y 64 eran escáneres que se llevaron un 401;
    - **mandó tráfico `x-pedibot-client: test`**: mis scripts, el smoke del despliegue y los
      navegadores que abrieron el panel, que desde entonces avisan desde cada página.

    Antes se descartaba el navegador exacto (IP + agente) que abrió el panel. El operador en su
    móvil, en la misma wifi, contaba como visita; ahora cuenta la IP entera.
    """
    out: dict[str, list[float]] = {}
    for line in lines:
        if '"handled request"' not in line or (
            "/admin" not in line and "pedibot-client" not in line.lower()
        ):
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = j.get("request", {})
        headers = {str(k).lower(): v for k, v in (req.get("headers") or {}).items()}
        panel = j.get("status") == 200 and str(req.get("uri", "")).startswith("/admin")
        prueba = "test" in [str(v).lower() for v in headers.get("x-pedibot-client") or []]
        if panel or prueba:
            out.setdefault(str(req.get("remote_ip")), []).append(float(j.get("ts", 0)))
    return out


def _es_nuestra(marks: dict[str, list[float]], ip: object, ts: float) -> bool:
    return any(abs(ts - m) <= TEAM_WINDOW for m in marks.get(str(ip), ()))


#: a visit ends after half an hour with no page. The usual convention, and a convention.
VISIT_GAP = 1800.0


def _dwell(seen_at: dict[str, list[float]]) -> dict[str, Any]:
    """How long a visit lasted, for the visits where that can be known at all.

    The only clock this site has is the gap between two requests, so a visit of one page has no
    duration — nothing marks its end. Reporting a number for those would be inventing it, so they
    are counted and left out, and the count is shown next to the figure.

    The median, not the average: one machine returning after ten hours pulls the average of these
    to nineteen minutes while the middle visit is nineteen seconds.
    """
    visits: list[list[float]] = []
    for times in seen_at.values():
        times.sort()
        cur = [times[0]]
        for t in times[1:]:
            if t - cur[-1] > VISIT_GAP:
                visits.append(cur)
                cur = [t]
            else:
                cur.append(t)
        visits.append(cur)
    lasted = sorted(v[-1] - v[0] for v in visits if len(v) > 1)
    return {
        "visits": len(visits),
        "timed": len(lasted),
        "median_seconds": lasted[len(lasted) // 2] if lasted else None,
        # how many of the timed ones were more than a glance
        "over_a_minute": sum(1 for x in lasted if x >= 60),
    }


def web_visits(days: int = 7) -> dict[str, Any]:
    """Page views, unique visitors (hash of IP+UA) and top pages from Caddy's JSON access log.

    `days <= 0` means "as much as there is". It is NOT all-time and must never be shown as such:
    the journal rotates, and this one was capped after it grew to 4 GB. The returned `covers`
    says which days were actually seen, so the panel can label the number with its own period.
    A year is the ceiling either way — beyond that the read costs more than the answer is worth.
    """
    since = f"-{days}d" if days > 0 else "-365d"
    try:
        out = subprocess.run(
            ["journalctl", "-u", "caddy", "--since", since, "-o", "cat", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
    except Exception as e:  # noqa: BLE001
        print("journalctl failed:", e, file=sys.stderr)
        return {
            "views": 0,
            "visitors": 0,
            "page_requests": 0,
            "returning": 0,
            "chat_pageviews": 0,
            "visits": 0,
            "timed": 0,
            "median_seconds": None,
            "over_a_minute": 0,
            "top": [],
            "per_day": {},
            "covers": (),
        }
    return count_visits(out.splitlines())


# ── la web, más allá de Google (21-sep-2026) ─────────────────────────────────────────────────
# El operador: «quiero saber más cosas en general de la web». Todo sale del mismo registro que ya
# cuenta las visitas, sin cookies: la cabecera Referer de la primera página, el agente y el
# Accept-Language. Se cuentan personas, cada una una vez.

_BUSCADORES = {
    "Google": ("google.",),
    "Bing": ("bing.com",),
    "otros buscadores": (
        "duckduckgo.",
        "yandex.",
        "baidu.",
        "ecosia.",
        "yahoo.",
        "brave.com",
        "qwant.",
        "naver.",
        "seznam.",
    ),
    "redes sociales": (
        "t.co",
        "x.com",
        "twitter.",
        "facebook.",
        "fb.",
        "instagram.",
        "bsky.",
        "reddit.",
        "linkedin.",
        "whatsapp.",
        "telegram.",
        "t.me",
        "youtube.",
        "tiktok.",
    ),
    "asistentes de IA": (
        "chatgpt.",
        "openai.",
        "perplexity.",
        "claude.ai",
        "gemini.",
        "copilot.",
        "deepseek.",
    ),
}

#: Cada herramienta, por el primer trozo de la dirección después del idioma.
_HERRAMIENTAS = {
    "dose": "calculadora de dosis",
    "growth": "percentiles",
    "emergency": "urgencias",
    "vaccines": "vacunas",
    "muac": "cinta del brazo",
    "guides": "guías",
    "family": "cuenta de familia",
    "diary": "cuenta de familia",
    "kit": "botiquín",
    "sources": "fuentes",
}
_IDIOMAS_WEB = {"es", "en", "fr", "de", "ru", "ar", "pt", "hi"}


def _origen(ref: str) -> str:
    host = re.sub(r"^https?://", "", ref.lower()).split("/")[0]
    if not host or host.endswith("pedibot.xyz"):
        return "directo"
    for nombre, marcas in _BUSCADORES.items():
        if any(host == m or host.startswith(m) or f".{m}" in f".{host}" for m in marcas):
            return nombre
    return "otras webs"


def _herramienta(uri: str) -> str | None:
    trozos = [x for x in uri.split("/") if x]
    if trozos and trozos[0] in _IDIOMAS_WEB:
        trozos = trozos[1:]
    if not trozos:
        return "chat"
    return _HERRAMIENTAS.get(trozos[0])


def _cuenta(valores: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in valores:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _la_web(
    llegada: dict[str, tuple[float, str, str, str, str]],
    reales: dict[str, list[tuple[str, float]]],
) -> dict[str, Any]:
    idiomas, regiones = [], []
    for _ts, _uri, _ref, _ua, al in llegada.values():
        primero = al.split(",")[0].split(";")[0].strip()
        if not primero or primero == "*":
            continue
        partes = primero.replace("_", "-").split("-")
        idiomas.append(partes[0].lower())
        if len(partes) > 1 and len(partes[1]) == 2:
            regiones.append(partes[1].upper())
    herramientas: list[str] = []
    for vistas in reales.values():
        herramientas += sorted({h for uri, _ in vistas if (h := _herramienta(uri))})
    movil = re.compile(r"Mobi|Android|iPhone|iPad", re.I)
    return {
        "sources": _cuenta([_origen(x[2]) for x in llegada.values()]),
        "devices": _cuenta(
            ["móvil" if movil.search(x[3]) else "ordenador" for x in llegada.values()]
        ),
        "browser_langs": _cuenta(idiomas),
        "regions": _cuenta(regiones),
        "tools": _cuenta(herramientas),
        "entries": sorted(
            _cuenta([x[1] for x in llegada.values()]).items(), key=lambda kv: (-kv[1], kv[0])
        )[:10],
    }


def count_visits(lines: list[str]) -> dict[str, Any]:
    """Cuenta visitas de verdad, y dice aparte cuántas peticiones hubo en bruto.

    El operador lo notó antes que nadie: demasiadas visitas para tan pocas consultas. Sobre
    catorce días, esto contaba **6.258 vistas y 3.227 visitantes**, y de esos 3.227 sólo 211
    habían llegado a pedir un fichero de la propia página. La sospecha estaba escrita aquí
    mismo desde el principio —«uno que pide una página y se va es un rastreador, diga lo que
    diga su agente»— y nunca se había aplicado.

    Ahora **una visita exige la prueba del navegador**: haber pedido, además del HTML, alguno de
    los ficheros que la página carga sola (su CSS, su JavaScript, un tipo de letra, el icono).
    Un rastreador que sólo quiere el texto no los pide nunca. Los que se descartan no
    desaparecen: `page_requests` los sigue diciendo, con su nombre.

    No es perfecto y no pretende serlo — un rastreador que renderice de verdad sigue pareciendo
    un navegador. Es defendible, que es lo que se le pide a un número que se mira para decidir.
    """
    # quiénes somos, antes de contar a nadie (ver _team_marks). Cuesta una pasada más y ninguna
    # configuración.
    ours = _team_marks(lines)
    brutas = 0
    paginas: dict[str, list[tuple[str, float]]] = {}
    llegada: dict[str, tuple[float, str, str, str, str]] = {}
    estaticos: set[str] = set()
    for line in lines:
        if '"handled request"' not in line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = j.get("request", {})
        uri, status = req.get("uri", ""), j.get("status", 0)
        if status != 200 or req.get("method") != "GET":
            continue
        ua = (req.get("headers", {}).get("User-Agent") or [""])[0]
        ip = req.get("remote_ip")
        if _BOT_UA.search(ua) or _de_rastreador(ip):
            continue
        who = _who(ip, ua)
        if _es_nuestra(ours, ip, float(j.get("ts", 0))):
            # el operador mirando su propio sitio no es una visita, y con este tráfico una
            # persona abriéndolo dos veces al día sería casi todo el número que está mirando
            continue
        if _STATIC.search(uri):
            estaticos.add(who)
            continue
        brutas += 1
        ts_pag = float(j.get("ts", 0))
        paginas.setdefault(who, []).append((uri.split("?")[0], ts_pag))
        h = req.get("headers", {})
        if who not in llegada or ts_pag < llegada[who][0]:
            llegada[who] = (
                ts_pag,
                uri.split("?")[0],
                (h.get("Referer") or [""])[0],
                ua,
                (h.get("Accept-Language") or [""])[0],
            )

    reales = {w: v for w, v in paginas.items() if w in estaticos}
    views, chat = 0, 0
    top: dict[str, int] = {}
    per_day: dict[str, int] = {}
    people_day: dict[str, set[str]] = {}
    seen_at: dict[str, list[float]] = {}
    for who, vistas in reales.items():
        for uri, ts in vistas:
            views += 1
            if uri in ("/", "/es", "/es/"):
                chat += 1
            top[uri] = top.get(uri, 0) + 1
            day = dt.datetime.fromtimestamp(ts, dt.UTC).date().isoformat()
            per_day[day] = per_day.get(day, 0) + 1
            people_day.setdefault(day, set()).add(who)
            seen_at.setdefault(who, []).append(ts)
    return {
        "views": views,
        "visitors": len(reales),
        # lo que se descarta no se esconde: peticiones de página que no se identificaron como
        # robot pero tampoco probaron ser un navegador
        "page_requests": brutas,
        **_dwell(seen_at),
        "returning": sum(1 for v in reales.values() if len(v) > 1),
        "chat_pageviews": chat,
        "top": sorted(top.items(), key=lambda kv: -kv[1])[:10],
        "per_day": dict(sorted(per_day.items())),
        # personas distintas cada día: la gráfica del panel sumaba páginas y lo llamaba visitas
        "visitors_per_day": {d: len(w) for d, w in sorted(people_day.items())},
        "web": _la_web({w: llegada[w] for w in reales if w in llegada}, reales),
        # lo que el registro tenía de verdad, para que el panel no llame total a un log rotado
        "covers": (min(per_day), max(per_day)) if per_day else (),
    }


def questions(con: sqlite3.Connection, days: int = 7, include_test: bool = False) -> dict[str, Any]:
    """`days <= 0` counts everything: these rows live in the ops database and nothing deletes
    them, so unlike the visits this really is every question ever asked. Every ISO timestamp
    sorts after the empty string, which is why "everything" needs no separate query.

    Readers only, unless `include_test`. Our own test traffic is real work against a real engine
    and it belongs in the database, but it is not somebody asking about their child, and every
    number on this panel is read as if it were. `test` counts them so the operator can see how
    much of the day was us; `cost` is money and always counts every question, ours included.
    """
    since = (
        (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(timespec="seconds")
        if days > 0
        else ""
    )
    only = "" if include_test else REAL_ONLY
    q = con.execute
    total = q("SELECT COUNT(*) FROM answers WHERE ts>=?" + only, (since,)).fetchone()[0]
    tg = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND source='telegram'", (since,)
    ).fetchone()[0]
    ours = q("SELECT COUNT(*) FROM answers WHERE ts>=?" + NOT_REAL, (since,)).fetchone()[0]
    alarms = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND level<>'routine'", (since,)
    ).fetchone()[0]
    nosrc = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?"
        + only
        + " AND verification IN ('no_source','fallback')",
        (since,),
    ).fetchone()[0]
    # Las respuestas dadas SIN modelo, separadas por causa. `degraded` es el tope de gasto, que
    # decidimos nosotros; `no_model` es una avería del proveedor. Antes del 7-sep-2026 la avería
    # ni siquiera llegaba a la base —salía como un 500—, así que era invisible por definición.
    sin_modelo = dict(
        q(
            "SELECT verification, COUNT(*) FROM answers WHERE ts>=?"
            + only
            + " AND verification IN ('degraded','no_model') GROUP BY 1",
            (since,),
        ).fetchall()
    )
    up = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND feedback=1", (since,)
    ).fetchone()[0]
    down = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND feedback=-1", (since,)
    ).fetchone()[0]
    # money is never filtered: a test question is charged exactly like a real one
    cost = q("SELECT COALESCE(SUM(cost_usd),0) FROM answers WHERE ts>=?", (since,)).fetchone()[0]
    langs = dict(
        q(
            "SELECT lang, COUNT(*) FROM answers WHERE ts>=?" + only + " GROUP BY 1", (since,)
        ).fetchall()
    )
    levels = dict(
        q(
            "SELECT level, COUNT(*) FROM answers WHERE ts>=?" + only + " GROUP BY 1", (since,)
        ).fetchall()
    )
    per_day = dict(
        q(
            "SELECT substr(ts,1,10), COUNT(*) FROM answers WHERE ts>=?"
            + only
            + " GROUP BY 1 ORDER BY 1",
            (since,),
        ).fetchall()
    )
    first = q("SELECT MIN(substr(ts,1,10)) FROM answers WHERE ts>=?" + only, (since,)).fetchone()[0]
    return {
        "first_day": first,
        "total": total,
        "telegram": tg,
        "web": total - tg,
        "test": ours,
        "alarms": alarms,
        "no_source": nosrc,
        "no_model": int(sin_modelo.get("no_model", 0)),
        "degraded": int(sin_modelo.get("degraded", 0)),
        "up": up,
        "down": down,
        "cost": float(cost),
        "langs": langs,
        "levels": levels,
        "per_day": per_day,
    }


def token(con: sqlite3.Connection, days: int = 7) -> dict[str, Any] | None:
    try:
        rows = con.execute(
            "SELECT day, price_usd, fdv_usd, volume_24h_usd, buys_24h, sells_24h, liquidity_usd FROM token_daily ORDER BY day DESC LIMIT ?",
            (days,),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    return {
        "days": len(rows),
        "price": rows[0][1],
        "fdv": rows[0][2],
        "liquidity": rows[0][6],
        "volume": sum(r[3] for r in rows),
        "buys": sum(r[4] for r in rows),
        "sells": sum(r[5] for r in rows),
        "price_change_pct": (rows[0][1] / rows[-1][1] - 1) * 100 if rows[-1][1] else 0.0,
        "series": [(r[0], r[1], r[4], r[5]) for r in reversed(rows)],
    }


def guides(days: int = 7) -> int:
    """`days <= 0` counts every published guide, which is the number the operator asks for."""
    n = 0
    since = dt.date.today() - dt.timedelta(days=days) if days > 0 else dt.date.min
    for f in (ROOT / "web" / "content").rglob("*.md"):
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", f.read_text(encoding="utf-8"), re.M)
        if m and dt.date.fromisoformat(m.group(1)) >= since:
            n += 1
    return n


def balance() -> float | None:
    try:
        from pedibot.bot.llm import deepseek_balance
        from pedibot.settings import get_settings

        s = get_settings()
        b = deepseek_balance(s.deepseek_api_key, s.deepseek_base_url)
        t = b.get("total_usd")
        return float(t) if isinstance(t, (int, float)) else None
    except Exception:  # noqa: BLE001
        return None


def unanswered(
    con: sqlite3.Connection, days: int = 0, include_test: bool = False, limit: int = 25
) -> list[dict[str, Any]]:
    """Las preguntas que se quedaron sin respuesta, una por una.

    El panel llevaba desde el principio un contador —«sin fuente: 6»— y nada más, así que para
    saber cuáles eran había que abrir la base a mano. Se hizo el 11-sep-2026 y de las seis, tres
    eran **fallos arreglables**: «le duele el oido desde ayer» con cinco fichas de oído en el
    corpus, «le sangro la nariz un momento y ya ha parado» con la del NHS indexada, y una de
    marca. Las otras tres eran negativas correctas.

    O sea que cada línea de esta lista es una de dos cosas, y las dos valen: un hueco del corpus
    que llenar o un fallo del buscador que arreglar. Un número no dice cuál de las dos.
    """
    since = (
        (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(timespec="seconds")
        if days > 0
        else ""
    )
    rows = con.execute(
        "SELECT id, ts, lang, source, verification, question FROM answers WHERE ts>=?"
        + ("" if include_test else REAL_ONLY)
        + " AND verification IN ('no_source','fallback')"
        " ORDER BY id DESC LIMIT ?",
        (since, limit),
    ).fetchall()
    keys = ("id", "ts", "lang", "source", "verification", "question")
    return [dict(zip(keys, r, strict=True)) for r in rows]


def recent_answers(
    con: sqlite3.Connection, limit: int = 50, include_test: bool = False
) -> list[dict[str, Any]]:
    """The cards under the numbers. Same rule: ours are not shown unless asked for, and when they
    are, the card says so — a test answer read as a parent's is how a fake problem gets chased."""
    rows = con.execute(
        "SELECT id, ts, lang, country, level, verification, feedback, cost_usd, latency_ms, question, answer, source"
        " FROM answers WHERE 1=1"
        + ("" if include_test else REAL_ONLY)
        + " ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    keys = (
        "id",
        "ts",
        "lang",
        "country",
        "level",
        "verification",
        "feedback",
        "cost_usd",
        "latency_ms",
        "question",
        "answer",
        "source",
    )
    out = []
    for r in rows:
        d = dict(zip(keys, r, strict=True))
        d["channel"] = _CHANNEL.get(str(d["source"]), str(d["source"]))
        out.append(d)
    return out


#: for the little tag on each card
_CHANNEL = {
    "web": "web",
    "telegram": "telegram",
    "agent": "agente",
    "test": "prueba nuestra",
    "unknown": "sin identificar",
}


def weekly_text(con: sqlite3.Connection) -> str:
    w, qn, tk, g, bal = web_visits(), questions(con), token(con), guides(), balance()
    end = dt.date.today()
    start = end - dt.timedelta(days=7)
    lines = [f"📊 PediBot · semana {start.strftime('%d %b')} – {end.strftime('%d %b')}", ""]
    lines.append(
        f"🌐 Web: {w['views']} páginas vistas · {w['visitors']} visitantes · {w['chat_pageviews']} en el chat"
    )
    fb = f" · 👍 {qn['up']} / 👎 {qn['down']}" if (qn["up"] or qn["down"]) else ""
    langs = " · ".join(f"{k} {v}" for k, v in sorted(qn["langs"].items())) if qn["langs"] else ""
    lines.append(f"💬 Consultas: {qn['total']} (web {qn['web']}, Telegram {qn['telegram']}){fb}")
    if langs:
        lines.append(
            f"   idiomas: {langs} · alarmas: {qn['alarms']} · sin fuente: {qn['no_source']}"
        )
    lines.append(
        f"🤖 Coste IA: {qn['cost']:.3f} $"
        + (f" · saldo DeepSeek {bal:.2f} $" if bal is not None else "")
    )
    if tk:
        lines.append(
            f"🪙 PDBT ({tk['days']} d): {tk['buys']} compras / {tk['sells']} ventas · volumen {tk['volume']:.0f} $ · precio {tk['price']:.7f} $ ({tk['price_change_pct']:+.1f} %) · FDV {tk['fdv']:.0f} $"
        )
    else:
        lines.append("🪙 PDBT: sin datos aún")
    lines.append(f"📝 Guías publicadas: {g}")
    if bal is None:
        # No decir nada es peor que decir que no se sabe: un informe semanal sin la línea del
        # saldo se lee como un informe normal, y si la consulta lleva meses fallando nadie se
        # entera hasta que el bot deja de contestar. Es la L31 —el silencio que no se distingue
        # de la ausencia— en el único aviso que anticipa quedarse sin servicio.
        lines.append("⚠️ No se ha podido leer el saldo de DeepSeek esta semana")
    elif bal < 2:
        lines.append("⚠️ Saldo DeepSeek bajo: recarga en platform.deepseek.com")
    return "\n".join(lines)
