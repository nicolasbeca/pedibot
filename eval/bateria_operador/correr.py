"""Las preguntas del operador (21-sep-2026), tal cual, por el motor de la web con el índice local.

Cada una en su conversación, sin país (como un padre que no lo ha elegido) salvo que se pase
--pais. Guarda una línea JSON por pregunta en el fichero de salida.
"""

import json
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.growth import Growth
from pedibot.bot.llm import provider_from_settings
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.bot.vaccines import Vaccines
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

entrada, salida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
#: 5-oct-2026: las baterías escritas con el reparto de las consultas reales traen bloques
#: «# en · US» y continuaciones «↳ …». El país de la cabecera se pasa al motor, como el chat le
#: pasa el del lector; la continuación va con la pregunta y la respuesta anteriores como historia.
PAISES = {
    "us": "US", "uk": "GB", "gb": "GB", "india": "IN", "in": "IN", "nigeria": "NG", "ng": "NG",
    "kenya": "KE", "ke": "KE", "philippines": "PH", "ph": "PH", "pakistan": "PK", "pk": "PK",
    "españa": "ES", "es": "ES", "méxico": "MX", "mexico": "MX", "mx": "MX", "colombia": "CO",
    "co": "CO", "argentina": "AR", "ar": "AR", "chile": "CL", "cl": "CL", "us latino": "US",
    "us (latinos)": "US", "deutschland": "DE", "de": "DE", "france": "FR", "fr": "FR",
    "sénégal": "SN", "brasil": "BR", "br": "BR", "portugal": "PT", "pt": "PT", "россия": "RU",
    "ru": "RU", "eg / gulf": "SA", "sn": "SN", "sa": "SA", "co ": "CO",
}


def _pais(cabecera: str) -> str | None:
    partes = [x.strip().lower() for x in cabecera.lstrip("#").split("·")]
    if len(partes) < 2:
        return None
    sitio = partes[1].split(" (")[0] if partes[1] not in PAISES else partes[1]
    return PAISES.get(partes[1]) or PAISES.get(sitio)


#: Cada unidad es (país, [pregunta, continuación, …]); una sola pregunta en las baterías viejas.
unidades: list[tuple[str | None, list[str]]] = []
pais: str | None = None
for ln in entrada.read_text(encoding="utf-8").splitlines():
    ln = ln.strip()
    if not ln:
        continue
    if ln.startswith("#"):
        pais = _pais(ln)
        continue
    if ln.startswith("↳") and unidades:
        unidades[-1][1].append(ln.lstrip("↳ ").strip())
        continue
    unidades.append((pais, [ln]))

s = get_settings()
llm = provider_from_settings()


#: 5-oct-2026: para medir un prompt o la inyección del «cuándo consultar» con y sin.
PROMPT = os.environ.get("PEDIBOT_PROMPT", "answer_v10")
INYECTA = os.environ.get("PEDIBOT_INYECTA", "1") == "1"


def motor() -> Engine:
    m = _motor()
    m.inyecta_alarma = INYECTA
    m.temperatura = float(os.environ.get("PEDIBOT_TEMP", "0.2"))
    return m


def _motor() -> Engine:
    return Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
            llm=llm,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
        growth=Growth(s.config_dir / "who_growth.json"),
        prompt_version=PROMPT,
    )


def _fila(i: int, q: str, a, pais: str | None, sigue: bool) -> dict:
    return {
        "i": i,
        "q": q,
        "pais": pais,
        "sigue": sigue,
        "lang": a.lang,
        "level": a.level,
        "ver": a.verification,
        "banner": (a.banner or "").replace("\n", " | "),
        "text": a.text,
        "sources": [x[:90] for x in a.sources],
        # 5-oct-2026: los pasajes que tuvo delante el redactor, para que el juez compare con
        # lo que dicen las guías y no con su propio criterio (util.py).
        "chunk_ids": list(a.chunk_ids or []),
    }


def una(par: tuple[int, tuple[str | None, list[str]]]) -> list[dict]:
    i, (pais, qs) = par
    filas: list[dict] = []
    historia: list[dict[str, str]] = []
    m = motor()
    for j, q in enumerate(qs):
        try:
            a = m.ask(q, country=pais, lang=None, history=historia or None)
        except Exception as e:  # noqa: BLE001
            filas.append({"i": i, "q": q, "pais": pais, "sigue": j > 0, "error": repr(e)})
            break
        filas.append(_fila(i, q, a, pais, j > 0))
        historia += [{"role": "user", "text": q}, {"role": "assistant", "text": a.text}]
    return filas


with ThreadPoolExecutor(6) as ex, salida.open("w", encoding="utf-8") as f:
    for filas in ex.map(una, enumerate(unidades)):
        for r in filas:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            # 23-sep-2026: la consola de Windows es cp1252 y la corrida MURIÓ en la pregunta 249
            # —la primera en ruso— al imprimirla. Media tanda perdida por una traza de progreso.
            linea = f"{r['i']} {r.get('pais')} {r.get('level')} {r.get('ver')} {r['q'][:60]}"
            sys.stdout.buffer.write(linea.encode("utf-8", "replace") + b"\n")
            sys.stdout.flush()
