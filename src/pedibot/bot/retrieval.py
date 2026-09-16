"""Retrieval with cross-lingual expansion: synonyms (offline) + optional LLM translation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from pedibot.bot.llm import LLMProvider

# El MISMO conversor de guiones que usa el triaje, no una copia: son los dos sitios
# que leen lo que escribe el padre, y la L65 salió justo de arreglarlo en uno solo.
from pedibot.bot.triage import _GUIONES
from pedibot.index.store import READABLE_FALLBACK, Hit, Index, fold, query_terms
from pedibot.ingest.classify import Taxonomy

# The Devanagari range is spelled out because Python's `\w` excludes combining vowel signs:
# without it "बुखार" tokenises as ब, ख, र and every single-word Hindi trigger below is
# unmatchable. Same property of `\w` that made a word boundary useless in the triage
# patterns (see NOT_AFTER in bot/triage.py): the third thing it broke quietly today.
#: La vocal larga del hindi transliterado se escribe doblada o no, según quien teclee:
#: «kaan»/«kan», «daant»/«dant», «bukhaar»/«bukhar», «ultee»/«ulti». Se pliega para comparar.
_VOCAL_DOBLE = re.compile(r"([aeiou])\1+", re.I)
#: La hamza del árabe se escribe o no según el teclado y las prisas: «إسهال» en la ficha de la
#: OMS, «اسهال» en el móvil del padre. Y la ة final se teclea «ه», y la ى se teclea «ي». Esto
#: no cambia el significado de ninguna palabra del vocabulario médico: sólo su ortografía.
_ARABE = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "\u064b": "",
        "\u064c": "",
        "\u064d": "",
        "\u064e": "",
        "\u064f": "",
        "\u0650": "",
        "\u0651": "",
        "\u0652": "",
        "\u0640": "",
    }
)


def _pliega_vocales(s: str) -> str:
    """kaan → kan, daant → dant: la vocal larga del hindi transliterado."""
    return _VOCAL_DOBLE.sub(r"\1", s)


def _normaliza_arabe(s: str) -> str:
    return s.translate(_ARABE)


#: El «franco-árabe»: el móvil está en inglés y las letras que el alfabeto latino no tiene se
#: escriben con cifras — 3 es ع, 7 es ح, 5 es خ, 2 es la hamza. Y lo demás lo escribe cada uno
#: como le suena: «sokhouna» / «sukhuna» / «sokhona». Se pliega todo a una forma: fuera las
#: cifras, las letras repetidas a una, y o→u, e→i, que es donde está la mitad de la variación.
_CIFRAS_ARABIZI = str.maketrans(
    {
        "2": "",
        "3": "",
        "'": "",
        "`": "",
        "7": "h",
        "5": "kh",
        "8": "gh",
        "9": "s",
        "6": "t",
        "4": "th",
    }
)
_REPETIDA = re.compile(r"([a-z])\1+")
_VOCAL_ARABIZI = str.maketrans({"o": "u", "e": "i"})


def _normaliza_arabizi(s: str) -> str:
    # las repeticiones se pliegan AL FINAL: «sokhouna» sólo dobla la u después de o→u
    return _REPETIDA.sub(r"\1", s.translate(_CIFRAS_ARABIZI).translate(_VOCAL_ARABIZI))


def _normaliza_ar(s: str) -> str:
    """El árabe, se escriba en su alfabeto o en el latino. No se mezclan: si hay una sola letra
    árabe, el texto es árabe y las cifras son cifras (los números de emergencia, las edades)."""
    if any("\u0600" <= c <= "\u06ff" for c in s):
        return _normaliza_arabe(s)
    return _normaliza_arabizi(s)


#: Qué se normaliza en cada lengua antes de comparar. Las demás, nada: en castellano «masa» y
#: «maasa» no son la misma palabra, y plegar de más rompió en agosto la dirección inglés→castellano.
_NORMALIZA = {"hi": _pliega_vocales, "ar": _normaliza_ar}


_TOKEN = re.compile(r"[\wáéíóúñüऀ-ॿ]+", re.I)
TRANSLATE_SYSTEM = (
    "You translate a parent's question about a child's health into 5-10 Spanish medical search "
    "keywords (nouns, symptoms, condition names). Output only the keywords separated by commas. "
    "No explanations."
)


#: Palabras que acompañan a una marca y no son la marca. Sin esto, una casilla futura del
#: tipo «Children's Panadol» convertiría «children» en disparador de paracetamol.
_COLETILLAS = frozenset(
    {
        "children",
        "children's",
        "infant",
        "infants",
        "infants'",
        "junior",
        "baby",
        "kids",
        "for",
        "pediátrico",
        "pediatrico",
        "pédiatrique",
    }
)


def _brand_terms(drugs_path: Path) -> dict[str, dict[str, str]]:
    """marca o alias → {idioma: nombre genérico}, sacado del catálogo.

    Derivado, no copiado. La lista de marcas ya existe en `config/drugs.yaml` para la calculadora;
    tenerla otra vez a mano en `synonyms.yaml` es el patrón del clon podrido — se añade una marca
    en un sitio, el otro no se entera y nada falla. Medido el 7-sep-2026: de 44 nombres, 39 no
    estaban en los sinónimos.
    """
    raw = yaml.safe_load(drugs_path.read_text(encoding="utf-8")) or {}
    fuera: dict[str, dict[str, str]] = {}
    for ficha in (raw.get("drugs") or {}).values():
        genericos = {k: str(v).lower() for k, v in (ficha.get("generic") or {}).items()}
        nombres = [
            str(b.get("name", "")) for b in (ficha.get("brands") or []) if isinstance(b, dict)
        ]
        nombres += [str(a) for a in (ficha.get("aliases") or [])]
        for n in nombres:
            # «Tempra / Tylenol» y «Advil Children's / Infants'» son dos marcas en una casilla
            for parte in str(n).split("/"):
                clave = parte.strip().lower()
                if len(clave) >= 3:
                    fuera.setdefault(clave, genericos)
                # Y la primera palabra a secas, que es como se escribe. En el catálogo la
                # marca lleva su coletilla —«Panadol Children», «Nurofen for Children»— y el
                # emparejador trata un nombre con espacios como una frase, así que tenía que
                # aparecer entera: nadie escribe eso. Resultado medido el 11-sep-2026: el
                # sitio publicaba /dose/panadol y el asistente no sabía qué era «panadol»,
                # que es EL antitérmico infantil del Golfo. Mismo corte que hace
                # `export_catalog.py` para la URL, para que las dos cosas no se separen.
                cabeza = clave.split(" ")[0]
                if cabeza != clave and len(cabeza) >= 4 and cabeza not in _COLETILLAS:
                    fuera.setdefault(cabeza, genericos)
    return fuera


class Synonyms:
    def __init__(self, path: Path, drugs: Path | None = None):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        # Todo se fuerza a texto al cargar. Un «112» sin comillas en el YAML lo lee el cargador
        # como entero, y `" ".join(...)` revienta con un TypeError que le llega al padre como un
        # 500: estaba vivo en producción para cualquier pregunta en inglés con la palabra
        # «emergency», que es de las más naturales que hay en el idioma principal del producto
        # (8-sep-2026). El dato está arreglado; esto es para que el siguiente descuido de
        # comillas cueste una recuperación peor y no una respuesta perdida.
        self._maps: dict[str, dict[str, list[str]]] = {
            str(k): {str(t): [str(x) for x in (terms or [])] for t, terms in (v or {}).items()}
            for k, v in raw.items()
        }
        self._marcas = _brand_terms(drugs) if drugs and drugs.exists() else {}

    def knows(self, lang: str) -> bool:
        """Whether this language has any local table, so retrieval works without a model."""
        return any(self._tables(lang))

    def _tables(self, lang: str) -> list[dict[str, list[str]]]:
        """`es` (colloquial → leaflet) plus any cross-lingual table such as `es_en`."""
        return [v for k, v in self._maps.items() if k == lang or k.startswith(f"{lang}_")]

    @staticmethod
    def _candidates(token: str) -> list[str]:
        """The token, plus the Arabic forms with a leading clitic removed.

        Arabic writes «and», «with», «the» joined to the next word: "and his temperature" is one
        token, «وحرارته». A prefix match against «حرارة» finds nothing, and listing every
        combination would be four entries per trigger and still miss the fifth.
        """
        if not ("\u0600" <= token[0] <= "\u06ff"):
            return [token, fold(token)] if fold(token) != token else [token]
        out = [token]
        for clitic in ("ال", "و", "ف", "ب", "ك", "ل"):
            if token.startswith(clitic) and len(token) > len(clitic) + 1:
                rest = token[len(clitic) :]
                out.append(rest)
                if rest.startswith("ال") and len(rest) > 3:
                    out.append(rest[2:])
        return out

    def expand(self, query: str, lang: str = "en") -> list[str]:
        # Los guiones se vuelven espacios antes de mirar, aquí también. Un disparador con guion
        # dentro —«nouveau-né», «recém-nascido», «pronto-socorro», «magen-darm»— no es una frase
        # (no lleva espacio) y se busca por prefijo contra los tokens… que el tokenizador parte
        # justo por el guion. Eran doce disparadores que NO PODÍAN casar nunca, y entre ellos el
        # recién nacido en francés y en portugués (8-sep-2026).
        low = fold(_GUIONES.sub(" ", query.lower()))
        tokens = [c for t in _TOKEN.findall(low) for c in self._candidates(t)]
        extra: list[str] = []
        # Las marcas, antes que nada. Un padre escribe lo que pone en el
        # bote —«Dalsy», «Apiretal», «Alivium»— y el corpus habla de «ibuprofeno» y
        # «paracetamol». Hasta el 7-sep-2026 el buscador no sabía que eran lo mismo y una
        # consulta real por Dalsy recibió «no tengo información fiable sobre esto».
        for marca, genericos in self._marcas.items():
            hit = marca in low if " " in marca else any(t == marca for t in tokens)
            if not hit:
                continue
            # solo el genérico del idioma de la pregunta y el inglés: meter los ocho
            # añadiría cirílico y árabe a una consulta española, términos que no casan
            # con nada y que le quitan peso a los que sí
            for g in (genericos.get(lang), genericos.get("en")):
                if g and g not in extra:
                    extra.append(g)
        # El hindi se teclea mucho en letras latinas, y ahí la ortografía la pone cada uno: la
        # vocal larga se dobla o no («kaan» / «kan», «daant» / «dant», «daane» / «dane»), y entre
        # las dos palabras de una frase se cuela «me», «par» o «ka». Medido el 16-sep-2026 sobre
        # quince preguntas corrientes: SEIS no encontraban nada, y las claves romanizadas
        # estaban puestas desde agosto. Sólo para el hindi: en castellano «masa» y «maasa» no
        # son la misma palabra (23-ago: plegar de más rompió la dirección inglés→castellano).
        #
        # Y el árabe tiene lo suyo: la hamza se escribe o no —«إسهال» en la ficha, «اسهال» en el
        # teclado— y con eso «عيالي عندهم اسهال» no encontraba NADA. Misma solución: se comparan
        # las formas normalizadas, y la normalización es de la lengua, no general.
        romanizado = lang == "hi"
        norm = _NORMALIZA.get(lang)
        low_n = norm(low) if norm else low
        tokens_n = [norm(t) for t in tokens] if norm else tokens
        for table in self._tables(lang):
            for trigger, terms in table.items():
                # a trigger with a space is a phrase ("stomach bug"), matched on the whole query;
                # a single word is matched by prefix on each token ("vomit" → "vomiting")
                # el disparador se normaliza igual que la consulta: con eso, uno que
                # llevaba guion pasa a ser una frase de varias palabras y se busca entera
                disp = fold(_GUIONES.sub(" ", trigger))
                if " " in disp:
                    hit = disp in low
                    if not hit and norm:
                        hit = norm(disp) in low_n
                    if not hit and romanizado:
                        partes = norm(disp).split(" ") if norm else disp.split(" ")
                        # una palabra corta en medio —«kaan me dard»— no rompe la frase
                        hueco = r"\s+(?:\w{1,3}\s+)?".join(re.escape(p) for p in partes)
                        hit = re.search(hueco, low_n) is not None
                elif disp.endswith("$"):
                    # palabra entera: «tablet$» es el aparato y «tableta» es de chocolate — o una
                    # pastilla, que es peor. Por prefijo, «se ha tomado una tableta de
                    # paracetamol» expandía a «screen time» y le daba tema de pantallas a una
                    # pregunta de dosis (10-sep-2026). Misma marca que en la taxonomía.
                    entera = disp[:-1]
                    hit = any(t == entera for t in tokens)
                    if not hit and norm:
                        plegada = norm(entera)
                        hit = any(t == plegada for t in tokens_n)
                else:
                    hit = any(t.startswith(disp) for t in tokens)
                    if not hit and norm:
                        plegado = norm(disp)
                        hit = any(t.startswith(plegado) for t in tokens_n)
                if hit:
                    for t in terms:
                        if t not in extra:
                            extra.append(t)
        return extra


def detect_lang(text: str) -> str:
    """Tiny heuristic over the seven languages — enough to pick the synonym direction, the
    answer language and the triage wording. A language only joins here once it has its own triage
    patterns: guessing the language of a message the safety layer cannot read is worse than
    defaulting to English.

    Languages in their own script are decided by the script and never reach the word counting:
    counting Latin-alphabet markers in a Cyrillic sentence compares it against vocabularies it
    has no letters in common with."""
    # A different script is not a hint, it is the answer. Measured over the letters only, so a
    # Cyrillic question with a Latin brand name in it ("Нурофен 200 mg") still counts as Russian.
    letters = [c for c in text if c.isalpha()]
    if letters:
        # Devanagari joins Cyrillic and Arabic: a different alphabet is not a hint,
        # it is the answer. Hindi typed in Latin letters is very common in India and
        # falls through to the word markers below, which is why it also has those.
        for script, code in (
            ("\u0400\u04ff", "ru"),
            ("\u0600\u06ff", "ar"),
            ("\u0900\u097f", "hi"),
        ):
            # not lo/hi:  is also the Hindi score further down, and mypy caught the clash
            first, last = script[:1], script[1:]
            if sum(first <= c <= last for c in letters) / len(letters) > 0.5:
                return code
    low = " " + re.sub(r"[¿¡?!.,;:]", " ", text.lower()) + " "
    es_markers = [
        " mi ",
        " hijo",
        " hija",
        " tiene ",
        " fiebre",
        " años",
        " meses",
        " le ",
        " qué ",
        " puedo",
        " está ",
        " bebé",
        " niño",
        " niña",
        " puede",
        " tomar",
        " cuánto",
        " cuanto",
        " perro",
        " se ",
        " ha ",
        " una ",
        " con ",
        " del ",
        " los ",
        " las ",
        " quiere",
        " hago",
        " ayer",
        " muy ",
        " tengo",
        " duele",
        " cabeza",
        " noche",
        " mucho",
        " ahora",
        " cuando ",
        " cuándo",
        " debo",
        " dale",
        " darle",
        " llora",
        " comiendo",
        " nada ",
    ]
    en_markers = [
        " my ",
        " has ",
        " fever",
        " old ",
        " should ",
        " the ",
        " is ",
        " can ",
        " what ",
        " baby",
        " son ",
        " daughter",
        " he ",
        " she ",
    ]
    fr_markers = [
        " mon ",
        " ma ",
        " mes ",
        " fils",
        " fille",
        " bébé",
        " enfant",
        " il a ",
        " elle a ",
        " que faire",
        " est ",
        " des ",
        " du ",
        " avec ",
        " pas ",
        " pour ",
        " dois",
        " puis",
        " nuit",
        " ans",
        " mois",
        " fièvre",
        " toux",
        " ventre",
        " tête",
        # French-only words that carry a short question on their own. Added when the
        # cedilla stopped counting for French — it is shared with Portuguese — and
        # «Ça fait mal quand il avale» was left scoring zero in every language.
        " ça ",
        " quand ",
        " fait ",
        " avale",
        # Medido el 8-sep-2026: 6 de 11 preguntas francesas corrientes se leían como inglés o
        # como castellano, y «Qu'est-ce que la rougeole ?» se contestaba EN CASTELLANO. Casi
        # todo lo que faltaba es o bien una palabra sin acento —un padre teclea «fievre»,
        # «cogne», «tete»— o bien una interrogativa que el francés no comparte con nadie.
        " combien",
        " comment",
        " pourquoi",
        " qu'est",
        " est-ce",
        " s'est",
        " depuis",
        " hier",
        " rien",
        " beaucoup",
        " tousse",
        " boutons",
        " pleure",
        " soigner",
        " donner",
        " puis-je",
        " dure ",
        " fievre",
        " tete",
        " cogne",
        " bebe pleure",
        " le ventre",
    ]
    de_markers = [
        " mein ",
        " meine ",
        " sohn",
        " tochter",
        " kind",
        " baby",
        " hat ",
        " ist ",
        " nicht ",
        " und ",
        " der ",
        " die ",
        " das ",
        " ich ",
        " was ",
        " soll ",
        " kann ",
        " wie ",
        " fieber",
        " husten",
        " bauch",
        " kopf",
        " monate",
        " jahre",
        " jahren",
        " wochen",
        # las formas verbales corrientes, que son las que traen la frase entera
        " isst",
        " hustet",
        " weint",
        " erbricht",
        " nachts",
        " seit ",
        " gestern",
        " nichts",
        " darf ",
        " wann ",
        " lange",
        " dauern",
        " geben",
        " gestoßen",
        " gestossen",
    ]
    pt_markers = [
        " você",
        " não ",
        " nao ",
        " criança",
        " crianca",
        " filho",
        " filha",
        " meu ",
        " minha ",
        " tem ",
        " pode ",
        " febre",
        " com ",
        " uma ",
        " são ",
        " é ",
        " está com",
        " vômito",
        " vomito ",
        " remédio",
        # Solo 3 de 10 preguntas portuguesas corrientes se detectaban bien, y las siete que
        # fallaban estaban escritas SIN acentos, que es como se teclea en un móvil. Las de aquí
        # abajo son, además, distintivas frente al castellano, que es con quien se confunde:
        # «quanto» (es: cuanto), «tosse» (tos), «noite» (noche), «ontem» (ayer), «cabeca»
        # (cabeza), «faco» (hago), «posso» (puedo), «ele/ela» (él/ella).
        " quanto",
        " tosse",
        " noite",
        " ontem",
        " cabeça",
        " cabeca",
        " faço",
        " faco",
        " fazer",
        " posso",
        " ele ",
        " ela ",
        " dele",
        " dela",
        " tem ",
        " muito",
        " esta com",
        " dar ibuprofeno",
        " bebe chora",
        " chora",
        " na ",
        " nas ",
        " barriga",
    ]
    hi_markers = [
        " bukhar",
        " bacche",
        " bachche",
        " bachcha",
        " mera beta",
        " meri beti",
        " saans",
        " sans nahi",
        " ulti",
        " dast ",
        " kya karu",
        " kya karoon",
        " mahine ka",
        " saal ka",
        " dawa ",
        " doodh",
        " behosh",
        " nahi le raha",
    ]
    es = sum(m in low for m in es_markers) + sum(ch in "ñ¿¡" for ch in text.lower())
    en = sum(m in low for m in en_markers)
    # French shares most accents with Spanish, so only the ones Spanish never uses count. NOT ç:
    # Portuguese writes it too (criança, cabeça), so it separates neither and it used to hand
    # "A criança bateu a cabeça" to French on two cedillas alone.
    fr = sum(m in low for m in fr_markers) + sum(ch in "èêôûà" for ch in text.lower())
    # ä ö ü ß are German alone among the four; "das/der/die" carry most of the rest
    de = sum(m in low for m in de_markers) + sum(ch in "äöüß" for ch in text.lower())
    # ã and õ belong to Portuguese alone here; Spanish has ñ, which is counted for Spanish
    pt = sum(m in low for m in pt_markers) + sum(ch in "ãõ" for ch in text.lower())
    # Latin-script Hindi only; anything in Devanagari was decided by script above
    hi = sum(m in low for m in hi_markers)
    best = max(es, en, fr, de, pt, hi)
    if best == 0:
        return "en"
    # Portuguese first among the Latin ones when it wins outright: its markers are disjoint
    # from Spanish's, so a tie means the text is not really Portuguese and Spanish should win.
    if hi == best and hi > es and hi > en:
        return "hi"
    if pt == best and pt > es:
        return "pt"
    # ties go to the more conservative side: es before fr, because "mi/ma" and "hijo/fils" overlap
    if es == best:
        return "es"
    if fr == best:
        return "fr"
    if de == best:
        return "de"
    return "en"


def _one_readable_up_front(hits: list[Hit], lang: str) -> list[Hit]:
    """Entre las TRES primeras tiene que haber una que el padre pueda abrir, si existe alguna.

    16-sep-2026, batería de cuarenta preguntas de casa en hindi y árabe. «बच्चा उल्टी कर रहा
    है» y «طفلي يتقيأ» devolvían tres hojas de la SEUP, en castellano, y la página del NHS sobre
    vómitos justo detrás, a seis puntos. El padre recibe una respuesta con fuentes que no puede
    abrir, y comprobar es lo único que este producto ofrece por encima de un buscador.

    No se toca la puntuación —subir el empujón de la lengua puente movería las ocho lenguas por
    un caso de tres—: se sube UNA sola ficha legible al tercer puesto, y el orden de las demás
    se queda como estaba. Si no hay ninguna legible, no se inventa: se devuelve lo que hay.
    """
    legibles = {lang, READABLE_FALLBACK.get(lang, "")}
    if len(hits) < 4 or any(h.chunk.lang in legibles for h in hits[:3]):
        return hits
    for i, h in enumerate(hits[3:], start=3):
        if h.chunk.lang in legibles:
            return [*hits[:2], h, *hits[2:i], *hits[i + 1 :]]
    return hits


class Retriever:
    def __init__(
        self,
        index: Index,
        synonyms: Synonyms,
        llm: LLMProvider | None = None,
        top_k: int = 6,
        taxonomy: Taxonomy | None = None,
    ):
        self.index = index
        self.synonyms = synonyms
        self.llm = llm
        self.top_k = top_k
        self.taxonomy = taxonomy
        # Languages holding less than a tenth of the corpus: measured from the index itself, so a
        # language stops being "thin" on its own once it has enough material.
        self.thin_langs = index.thin_languages()

    def expand(self, query: str, lang: str) -> list[str]:
        extra = self.synonyms.expand(query, lang)
        if self.llm is not None and lang != "es" and len(extra) < 3:
            try:
                out = self.llm.complete(
                    TRANSLATE_SYSTEM, query, temperature=0.0, max_tokens=60
                ).text
                for kw in out.split(","):
                    kw = kw.strip().lower()
                    if kw and kw not in extra:
                        extra.append(kw)
            except Exception:  # noqa: BLE001 — expansion is best-effort
                pass
        return extra

    def search(
        self, query: str, lang: str, red_flag_boost: bool = False
    ) -> tuple[list[Hit], list[str]]:
        extra = self.expand(query, lang)
        topic = self.taxonomy.topic_for(query + " " + " ".join(extra)) if self.taxonomy else None
        hits = self.index.search(
            query,
            top_k=self.top_k,
            extra_terms=extra,
            red_flag_boost=red_flag_boost,
            boost_topic=topic,
            thin_lang=lang if lang in self.thin_langs else None,
            # Y la lengua que ese lector puede abrir si la suya no tiene el documento: un
            # padre indio lee inglés y no lee castellano (ver READABLE_FALLBACK).
            fallback_lang=READABLE_FALLBACK.get(lang),
        )
        # "source or silence": a hit must match a query term in its own text, and the question must
        # look paediatric (a taxonomy topic) unless it matches >= 3 terms; "my dog ate chocolate"
        # would otherwise match "perro" in the croup leaflet (one term, no topic).
        terms = query_terms(query, extra)
        if not terms:
            return [], extra
        min_matched = 1 if topic else 3
        good = [h for h in hits if h.matched_terms >= min_matched]
        # NOTE (26-ago-2026): a relevance floor was measured here and REJECTED. Neither an absolute
        # bm25 threshold nor a term-coverage ratio separates "the corpus covers this" from "it does
        # not": legitimate questions match as little as 1 term of 7 (g23) and score 20, while
        # "se hace pis en la cama" — covered by nothing — scores 10 and matches 1 of 3. The ranges
        # overlap, and an absolute score is not even comparable between corpora (it silenced every
        # test fixture). Separating them needs semantic similarity, not another threshold.
        return _one_readable_up_front(good, lang), extra
