"""Las preguntas del operador (21-sep-2026), tal cual, por el motor de la web con el índice local.

Cada una en su conversación, sin país (como un padre que no lo ha elegido) salvo que se pase
--pais. Guarda una línea JSON por pregunta en el fichero de salida.
"""

import json
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
preguntas = [ln.strip() for ln in entrada.read_text(encoding="utf-8").splitlines() if ln.strip()]

s = get_settings()
llm = provider_from_settings()


def motor() -> Engine:
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
    )


def una(par: tuple[int, str]) -> dict:
    i, q = par
    try:
        a = motor().ask(q, country=None, lang=None)
        return {
            "i": i,
            "q": q,
            "lang": a.lang,
            "level": a.level,
            "ver": a.verification,
            "banner": (a.banner or "").replace("\n", " | "),
            "text": a.text,
            "sources": [x[:90] for x in a.sources],
        }
    except Exception as e:  # noqa: BLE001
        return {"i": i, "q": q, "error": repr(e)}


with ThreadPoolExecutor(6) as ex, salida.open("w", encoding="utf-8") as f:
    for r in ex.map(una, enumerate(preguntas)):
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        print(r["i"], r.get("level"), r.get("ver"), r["q"][:60], flush=True)
