"""Build and query the SQLite/FTS5 index."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pedibot.ingest.schema import Chunk

THIN_LANG_BOOST = 1.6  # see `thin_lang` in Index.search

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    data TEXT NOT NULL,
    usage TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    topic TEXT NOT NULL,
    is_red_flag INTEGER NOT NULL,
    is_dose_table INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED, text, section, doc_title,
    tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

#: El bloque devanagari va explicito: `\\w` son los caracteres alfanuméricos y las vocales
#: del devanagari (las matras: ा ि ो ै) son marcas combinantes, así que sin esto «बुखार» se
#: parte en «ब»+«ख»+«र» y, con el filtro de tres caracteres de más abajo, una consulta en
#: hindi produce CERO términos (7-sep-2026). Encontraba igual gracias a las tablas cruzadas
#: de sinónimos, pero eso hacía que toda la búsqueda en hindi colgara de esas 176 entradas.
_TOKEN = re.compile(r"[\wáéíóúñü\u0900-\u097f]+", re.I)
STOP = {
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "que",
    "en",
    "a",
    "con",
    "por",
    "para",
    "mi",
    "hijo",
    "hija",
    "tiene",
    "es",
    "se",
    "le",
    "al",
    "del",
    "the",
    "my",
    "is",
    "has",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "with",
    "child",
    "son",
    "daughter",
    "he",
    "she",
    "it",
    "his",
    "her",
    "i",
    "what",
    "should",
    "do",
    "can",
    "qué",
    "cómo",
    "como",
    "hago",
    "doy",
    "puedo",
    "años",
    "año",
    "meses",
    "mes",
    "old",
    "years",
    "year",
    "months",
    "month",
    "weeks",
    "week",
    "days",
    "day",
    "días",
    "dia",
    "día",
    "much",
    "puede",
    "pueden",
    "puedes",
    "comer",
    "hacer",
    "normal",
    "tener",
    "how",
    "many",
    "cuánto",
    "cuanto",
    "cuánta",
    "cuanta",
    "give",
    "dar",
    "darle",
    # ------------------------------------------------------------------------------
    # Las palabras funcionales de las otras seis lenguas (8-sep-2026). La lista estaba
    # escrita en castellano y algo de inglés, así que la MISMA pregunta daba un término
    # en castellano y doce en alemán:
    #
    #   es  «mi hijo tiene fiebre y no sé qué hacer»           -> [fiebre]
    #   de  «mein Kind hat Fieber und ich weiß nicht was...»   -> [mein, kind, hat,
    #        fieber, und, ich, weiß, nicht, was, ich, tun, soll]
    #
    # Y eso no es solo ruido: esos términos entran en la consulta FTS, así que una
    # pregunta alemana sobre fiebre casaba con las fichas del RKI que contienen «ich» y
    # «und» —poliomielitis, estreptococo— por delante de las hojas de la fiebre.
    # Solo palabras funcionales: ni un síntoma, ni una parte del cuerpo, ni un fármaco.
    # en
    "am", "are", "was", "were", "be", "been", "being", "does", "did", "doing", "have", "had",
    "having", "will", "would", "could", "shall", "may", "might", "must", "at", "by", "from",
    "into", "about", "there", "this", "that", "these", "those", "you", "your", "we", "our",
    "us", "me", "him", "them", "they", "their", "it's", "im", "just", "very", "really",
    "please", "help", "know", "think", "tell", "want", "need", "when", "where", "why", "who",
    "which", "if", "so", "but", "not", "no", "yes",
    # fr
    "mon", "ma", "les", "une", "des", "du", "et", "ou", "je",
    "tu", "il", "elle", "nous", "vous", "ils", "elles", "qui", "quoi", "quand",
    "où", "pourquoi", "comment", "est", "sont", "ai", "as", "avons", "avez", "ont", "fait",
    "faire", "dois", "doit", "peut", "peux", "pouvez", "sais", "savoir", "pas", "plus", "très",
    "aussi", "avec", "sans", "pour", "dans", "sur", "au", "aux", "ce", "cette", "ces", "sa", "ses", "lui", "leur", "mais", "donc", "alors", "svp", "aide", "aider", "merci",
    # de
    "mein", "meine", "meinen", "meinem", "der", "die", "das", "den", "dem", "ein", "eine",
    "einen", "einem", "einer", "und", "oder", "ich", "er", "sie", "wir", "ihr",
    "hat", "habe", "haben", "hatte", "ist", "sind", "war", "waren", "bin", "wird", "werden",
    "kann", "können", "soll", "sollen", "muss", "müssen", "darf", "wer", "wo", "wann",
    "warum", "wie", "nicht", "kein", "keine", "auch", "sehr", "aber", "wenn", "dass", "mit",
    "ohne", "für", "von", "zu", "zum", "zur", "auf", "bei", "nach", "tun",
    "machen", "weiß", "denke", "bitte", "hilfe", "danke", "mal", "schon", "noch",
    # pt
    "meu", "minha", "meus", "minhas", "os", "um", "uma", "uns", "umas", "da", "dos", "e", "eu", "ele", "ela", "nós", "você", "vocês", "quem", "quando", "onde", "porque", "é", "são", "está", "estão", "estou", "tem",
    "tenho", "têm", "foi", "ser", "estar", "pode", "posso", "podem", "deve", "devo", "não",
    "sim", "muito", "também", "com", "sem", "em", "na", "nos", "nas",
    "ao", "aos", "à", "às", "mas", "então", "fazer", "faço", "sei", "saber", "ajuda",
    "obrigado", "obrigada",
    # ru
    "мой", "моя", "мои", "моего", "моей", "и", "или", "я", "ты", "он", "она", "оно", "мы",
    "вы", "они", "что", "кто", "где", "когда", "почему", "как", "не", "нет", "да", "очень",
    "тоже", "но", "если", "с", "со", "без", "для", "по", "в", "во", "на", "к", "ко", "от",
    "до", "у", "за", "это", "этот", "эта", "быть", "есть", "был", "была", "было", "были",
    "делать", "делаю", "надо", "нужно", "можно", "могу", "может", "должен", "пожалуйста",
    "помогите", "спасибо",
    # ar
    "ما", "ماذا", "من", "متى", "أين", "لماذا", "كيف", "هل", "في", "على", "إلى", "عن", "مع",
    "بدون", "أن", "أنا", "هو", "هي", "نحن", "هم", "هذا", "هذه", "ذلك", "التي", "الذي", "قد",
    "كان", "كانت", "يكون", "أفعل", "افعل", "عندي", "لدي", "لدى", "جدا", "أيضا", "لكن", "إذا",
    "لا", "نعم", "من فضلك", "أرجو", "شكرا", "أعرف", "يجب",
    # hi
    "मेरा", "मेरी", "मेरे", "मुझे", "मैं", "हम", "आप", "वह", "वे", "यह", "ये", "है", "हैं",
    "था", "थी", "थे", "हो", "होता", "होती", "करना", "करूँ", "करूं", "क्या", "कौन", "कहाँ",
    "कब", "क्यों", "कैसे", "नहीं", "हाँ", "बहुत", "भी", "लेकिन", "अगर", "के", "का", "की", "को",
    "से", "में", "पर", "और", "या", "कृपया", "मदद", "धन्यवाद", "रहा", "रही", "रहे", "गया",
    "गयी", "जाता", "लिए",
}
_DOSE_QUERY = re.compile(
    r"\b(dosis|dose|dosage|mg|ml|kilos?|kg|paracetamol|ibuprofen\w*|acetaminophen|"
    r"cu[aá]nt[oa]|how much)\b"
    # y en las otras tres escrituras, donde `\\b` no sirve: sin esto, una pregunta de dosis
    # en ruso, árabe o hindi no recibía el impulso que sube la tabla de dosificación
    r"|мг|мл|доз|сколько|парацетамол|ибупрофен"
    r"|ملغ|جرعة|كم|باراسيتامول|إيبوبروفين"
    r"|मिग्रा|खुराक|कितना|कितनी|पैरासिटामोल|आइबुप्रोफेन",
    re.I,
)


DOC_TYPE_WEIGHT = {
    "hoja_padres": 1.6,
    "calendario": 1.3,
    "guia_clinica": 1.15,
    "informe": 0.8,
    "manual": 0.75,
    "libro": 0.55,
}


@dataclass
class Hit:
    chunk: Chunk
    score: float  # higher is better (negated bm25)
    matched_terms: int


def build_index(
    chunks: list[Chunk], db_path: Path, include_usage: tuple[str, ...] = ("publico", "citar_solo")
) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)
    n = 0
    for c in chunks:
        if c.usage not in include_usage:
            continue
        con.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
            (
                c.chunk_id,
                c.doc_id,
                c.model_dump_json(),
                c.usage,
                c.doc_type,
                c.topic,
                int(c.is_red_flag),
                int(c.is_dose_table),
            ),
        )
        con.execute(
            "INSERT INTO chunks_fts VALUES (?,?,?,?)",
            (c.chunk_id, c.text, c.section, c.doc_title),
        )
        n += 1
    con.execute("INSERT OR REPLACE INTO meta VALUES ('n_chunks', ?)", (str(n),))
    con.commit()
    con.close()
    return n


def query_terms(query: str, extra: list[str] | None = None) -> list[str]:
    terms = [t.lower() for t in _TOKEN.findall(query)]
    terms = [t for t in terms if len(t) >= 3 and t not in STOP]
    for e in extra or []:
        for t in _TOKEN.findall(e.lower()):
            if len(t) >= 3 and t not in terms:
                terms.append(t)
    return terms


def _fts_expr(terms: list[str]) -> str:
    # prefix match on each term, OR-ed; FTS5 needs quoting
    return " OR ".join(f'"{t}"*' for t in terms)


class Index:
    def __init__(self, db_path: Path):
        if not db_path.exists():
            raise FileNotFoundError(f"index not found: {db_path} (run `pedibot ingest` first)")
        self.con = sqlite3.connect(
            db_path, check_same_thread=False
        )  # read-only use from API threads

    def thin_languages(self, share: float = 0.10) -> frozenset[str]:
        """Languages with less than `share` of the chunks. Computed once, from the data."""
        rows = self.con.execute(
            "SELECT json_extract(data, '$.lang') AS l, COUNT(*) FROM chunks GROUP BY l"
        ).fetchall()
        total = sum(n for _, n in rows) or 1
        return frozenset(lang for lang, n in rows if lang and n / total < share)

    def size(self) -> int:
        row = self.con.execute("SELECT v FROM meta WHERE k='n_chunks'").fetchone()
        return int(row[0]) if row else 0

    def get(self, chunk_id: str) -> Chunk | None:
        row = self.con.execute("SELECT data FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return Chunk.model_validate_json(row[0]) if row else None

    def red_flag_chunk(self, doc_id: str) -> Chunk | None:
        """The warning-signs chunk of a document (for triage rules to cite their own source)."""
        row = self.con.execute(
            "SELECT data FROM chunks WHERE doc_id=? AND is_red_flag=1 ORDER BY chunk_id LIMIT 1",
            (doc_id,),
        ).fetchone()
        if row is None:
            row = self.con.execute(
                "SELECT data FROM chunks WHERE doc_id=? ORDER BY chunk_id LIMIT 1", (doc_id,)
            ).fetchone()
        return Chunk.model_validate_json(row[0]) if row else None

    def search(
        self,
        query: str,
        top_k: int = 6,
        extra_terms: list[str] | None = None,
        prefer_parent_leaflets: bool = True,
        red_flag_boost: bool = False,
        topic: str | None = None,
        boost_topic: str | None = None,
        thin_lang: str | None = None,
    ) -> list[Hit]:
        terms = query_terms(query, extra_terms)
        if not terms:
            return []
        dose_query = bool(_DOSE_QUERY.search(query))
        sql = (
            "SELECT f.chunk_id, bm25(chunks_fts, 0, 1.0, 2.0, 3.0) AS r, c.data "
            "FROM chunks_fts f JOIN chunks c ON c.chunk_id = f.chunk_id "
            "WHERE chunks_fts MATCH ? "
        )
        params: list[object] = [_fts_expr(terms)]
        if topic:
            sql += "AND c.topic = ? "
            params.append(topic)
        sql += "ORDER BY r LIMIT ?"
        params.append(top_k * 5)
        rows = self.con.execute(sql, params).fetchall()
        hits: list[Hit] = []
        for _cid, r, data in rows:
            ch = Chunk.model_validate_json(data)
            score = -float(r)
            low = (ch.text + " " + ch.section).lower()
            # Por PALABRA, no por subcadena. `t in low` contaba «tos» dentro de «esTOS» y de
            # «toDOS», «pis» dentro de «ePISodio», «sed» dentro de «cauSED», «asma» dentro de
            # «plASMA» y de «espASMo». Medido sobre los 6.548 fragmentos del índice el
            # 8-sep-2026: «tos» aparecía en 2.558 como subcadena y en 259 como palabra, diez
            # veces más. Y esta cuenta no es decorativa: es la puerta del «fuente o silencio»
            # —`matched_terms >= min_matched` en retrieval.py— así que estaba abierta de par en
            # par justo para los síntomas que más se preguntan en castellano.
            #
            # Por prefijo, como en el resto del proyecto: «tos» tiene que seguir encontrando
            # «toses» y «fiebre», «fiebres».
            palabras = _TOKEN.findall(low)
            matched = sum(1 for t in terms if any(w.startswith(t) for w in palabras))
            if prefer_parent_leaflets:
                score *= DOC_TYPE_WEIGHT.get(ch.doc_type, 1.0)
            if thin_lang and ch.lang == thin_lang:
                # A language with a handful of documents needs its own material to surface: the
                # cross-lingual bridge is so much bigger that it buries it (French pertussis lost
                # to three English pertussis pages, 3-sep-2026). This is a boost to the thin
                # language, never a penalty to the others — penalising the other side was measured
                # in August and broke the English→Spanish direction the corpus depends on.
                score *= THIN_LANG_BOOST
            if boost_topic and ch.topic == boost_topic:
                score *= 1.5
            elif boost_topic and ch.topic not in (boost_topic, "general"):
                score *= (
                    0.7  # off-topic leaflets (heat stroke vs fever) must not outrank on-topic ones
                )
            if (
                red_flag_boost
                and ch.is_red_flag
                and (boost_topic is None or ch.topic == boost_topic)
            ):
                score *= 1.3
            if dose_query and ch.is_dose_table:
                score *= 1.6
            hits.append(Hit(ch, score, matched))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def dump_index_stats(db_path: Path) -> dict[str, int]:
    con = sqlite3.connect(db_path)
    stats = {
        "chunks": con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "docs": con.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0],
        "red_flag": con.execute("SELECT COUNT(*) FROM chunks WHERE is_red_flag=1").fetchone()[0],
        "dose": con.execute("SELECT COUNT(*) FROM chunks WHERE is_dose_table=1").fetchone()[0],
    }
    con.close()
    return stats


def chunks_to_json(hits: list[Hit]) -> str:
    return json.dumps(
        [
            {"chunk_id": h.chunk.chunk_id, "score": round(h.score, 3), "section": h.chunk.section}
            for h in hits
        ],
        ensure_ascii=False,
        indent=2,
    )
