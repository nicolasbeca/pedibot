"""El filtro de voz: lo que delata un texto escrito por una IA, antes de que salga (3-nov-2026).

Wayan Vota (ICTworks), 1-nov: «This reads as if it was written by AI… It sounds like a copy-paste
from AI». El operador ya lo había visto el 14-oct en una tanda. El perfil de cómo escribe él y lo
que hay que hacer con un texto está en ops/VOZ.md; aquí va sólo lo que se puede contar:

  - «para»: no sale. Rayas largas, listas y negritas, frases de plantilla, comillas curvas, la
    firma con tilde, un enlace a pedibot.xyz sin su `?r=`.
  - «ojo»: sale, pero se mira. Largo, frases muy largas, «no solo… sino», vocabulario de IA.

Sin dependencias: lo usa ops/correo.py con el Python del servidor.

    python ops/voz.py cuerpo.txt [otro.txt …]      # 1 si alguno para
    python ops/voz.py --palabras 800 articulo.txt  # un artículo, no un correo
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

#: un correo que se lee entero en el móvil; más, y suena a carta de presentación
PALABRAS_CORREO = 170
FRASE_LARGA = 35


@dataclass(frozen=True)
class Aviso:
    para: bool
    regla: str
    trozo: str

    def __str__(self) -> str:
        return f"{'PARA' if self.para else 'ojo '} {self.regla}: {self.trozo}"


#: nadie escribe esto en un correo de verdad; el operador las marcó una a una (14-oct) o salen
#: en la guía de Wikipedia de señales de texto de IA
PLANTILLA = re.compile(
    r"I hope (this|my) (message|e-?mail|note) finds you|hope you('re| are) (doing )?well"
    r"|I'?d be (really |truly |so )?grateful|thank you for (all )?the (amazing |incredible )?work you do"
    r"|I(?:'m| am) reaching out|I wanted to reach out|don'?t hesitate to|feel free to reach out"
    r"|looking forward to hearing from you|thank you for your (time and )?consideration"
    r"|I hope this helps|best of luck with|in today'?s (fast-paced |digital )?world"
    r"|espero que (este|mi) (mensaje|correo) (te|le|os) encuentre|no dudes? en (contactar|escribir)"
    r"|quedo a (tu|su|vuestra) (entera )?disposición|en el mundo actual|en la era digital"
    r"|es importante destacar|cabe destacar que|me pongo en contacto (contigo|con usted|con vosotros) para"
    r"|j'esp[èe]re que ce (message|courriel) vous trouve|n'h[ée]sitez pas [àa]"
    r"|ich hoffe, (diese|meine) (nachricht|e-mail) erreicht sie|z[öo]gern sie nicht"
    r"|espero que (esta|esse) (mensagem|e-?mail) (o|a|te) encontre|n[ãa]o hesite em",
    re.IGNORECASE,
)

#: vocabulario que la IA usa mucho más que la gente (Wikipedia, «Signs of AI writing», 2023-2026)
PALABRAS_DE_IA = re.compile(
    r"\b(delve|crucial|pivotal|robust|seamless(ly)?|leverag(e|ing)|foster(s|ing)?|testament"
    r"|tapestry|landscape|showcas(e|es|ing)|underscor(e|es|ing)|vibrant|meticulous(ly)?"
    r"|game-?changer|empower(s|ing)?|holistic|multifaceted|groundbreaking|invaluable"
    r"|navigate the|in the realm of|a myriad of|plays a (key|vital|crucial) role"
    r"|fundamental(es)?|crucial(es)?|clave|sin duda|cabe destacar|en definitiva|en resumen"
    r"|potenciar|fomentar|abordar|herramienta poderosa|panorama|ecosistema|sinergia)\b",
    re.IGNORECASE,
)

#: la estructura de IA más reconocible: corregir algo que nadie ha dicho
NO_SOLO = re.compile(
    r"no (es )?s[óo]lo\b[^.]{0,80}\bsino( también)?|not (just|only|merely)\b[^.]{0,80}\b(but|it'?s|it is)"
    r"|it'?s not (about )?[^.,]{1,40}, it'?s|more than just|non seulement[^.]{0,80}mais"
    r"|nicht nur[^.]{0,80}sondern|n[ãa]o (é )?s[óo][^.]{0,80}mas( também)?",
    re.IGNORECASE,
)

_RAYA = re.compile(r"[—–]")
_LISTA = re.compile(r"^\s*([-*•·]|\d{1,2}[.)])\s+\S", re.MULTILINE)
_MARKDOWN = re.compile(r"\*\*[^*]+\*\*|^#{1,6}\s|__[^_]+__", re.MULTILINE)
_COMILLAS = re.compile(r"[“”‘’]")
_ENLACE = re.compile(r"https?://(?:www\.)?pedibot\.xyz[^\s)>\]\"']*", re.IGNORECASE)
_FRASE = re.compile(r"(?<=[.!?])\s+|\n\s*\n")


def _cerca(texto: str, m: re.Match[str]) -> str:
    a, b = max(0, m.start() - 30), min(len(texto), m.end() + 30)
    return texto[a:b].replace("\n", " ").strip()


def revisa(texto: str, asunto: str = "", palabras: int = PALABRAS_CORREO) -> list[Aviso]:
    """Los avisos de un texto: los de «para» no dejan que salga."""
    todo = f"{asunto}\n{texto}" if asunto else texto
    avisos: list[Aviso] = []
    for regla, patron in (
        ("raya_larga", _RAYA),
        ("lista", _LISTA),
        ("markdown", _MARKDOWN),
        ("comillas", _COMILLAS),
        ("plantilla", PLANTILLA),
    ):
        m = patron.search(todo)
        if m:
            avisos.append(Aviso(True, regla, _cerca(todo, m)))
    if re.search(r"Nicol[áà]s Beca", todo):
        avisos.append(Aviso(True, "firma", "«Nicolás» con tilde: se ve mal en muchos clientes"))
    for m in _ENLACE.finditer(todo):
        if not re.search(r"[?&]r=[A-Za-z0-9._-]+", m.group(0)):
            avisos.append(Aviso(True, "enlace_sin_canal", m.group(0)))
            break

    n = len(texto.split())
    if n > palabras:
        avisos.append(Aviso(False, "largo", f"{n} palabras (máximo {palabras})"))
    for f in _FRASE.split(texto):
        if len(f.split()) > FRASE_LARGA:
            avisos.append(Aviso(False, "frase_larga", f[:90].replace("\n", " ") + "…"))
            break
    for regla, patron in (("no_solo", NO_SOLO), ("palabra_de_ia", PALABRAS_DE_IA)):
        m = patron.search(todo)
        if m:
            avisos.append(Aviso(False, regla, _cerca(todo, m)))
    if texto.count("!") > 1:
        avisos.append(Aviso(False, "exclamaciones", f"{texto.count('!')} signos de exclamación"))
    if _SE_PRESENTA.search(_entrada(texto, 8)):
        avisos.append(
            Aviso(False, "se_presenta_primero", "abre con quién eres: mejor con lo que le traes")
        )
    return avisos


#: «Soy Nicolas Beca y escribo desde Sevilla»: la plantilla de las tandas hasta el 30-oct
_SE_PRESENTA = re.compile(
    r"^(soy|me llamo|i'?m|i am|my name is|je m'appelle|je suis|ich bin|ich heiße|mein name ist"
    r"|chamo-me|meu nome é|sou o)\b",
    re.IGNORECASE,
)


def _entrada(texto: str, n: int = 4) -> str:
    """Las primeras palabras después del saludo, que es donde se nota la plantilla."""
    lineas = [x.strip() for x in texto.strip().splitlines() if x.strip()]
    cuerpo = lineas[1:] if lineas and len(lineas[0].split()) <= 4 else lineas
    return " ".join(" ".join(cuerpo).lower().split()[:n])


def _trozos(texto: str, n: int = 5) -> set[str]:
    w = re.findall(r"[^\W\d_]+", texto.lower())
    return {" ".join(w[i : i + n]) for i in range(len(w) - n + 1)}


def revisa_tanda(textos: list[str]) -> list[Aviso]:
    """Lo que sólo se ve juntando los correos de un día: que todos empiecen igual."""
    avisos: list[Aviso] = []
    if len(textos) < 2:
        return avisos
    entradas: dict[str, int] = {}
    for t in textos:
        e = _entrada(t)
        entradas[e] = entradas.get(e, 0) + 1
    for e, n in entradas.items():
        if n >= 2 and n * 3 > len(textos):
            avisos.append(Aviso(False, "misma_entrada", f"{n} de {len(textos)} empiezan «{e}…»"))
    # la misma frase de cinco palabras en tres correos o más: la plantilla del producto. La firma
    # y el saludo no cuentan (son dos o tres palabras)
    cuenta: dict[str, int] = {}
    for t in textos:
        for k in _trozos(t):
            cuenta[k] = cuenta.get(k, 0) + 1
    repetidas = sorted((k for k, n in cuenta.items() if n >= 3), key=lambda k: -cuenta[k])
    vistas: list[str] = []
    for k in repetidas:
        if not any(set(k.split()) & set(v.split()) for v in vistas):
            vistas.append(k)
    for k in vistas[:5]:
        avisos.append(Aviso(False, "frase_repetida", f"«{k}» en {cuenta[k]} de {len(textos)}"))
    return avisos


def main(argv: list[str]) -> int:
    palabras = PALABRAS_CORREO
    if argv[:1] == ["--palabras"]:
        palabras, argv = int(argv[1]), argv[2:]
    textos, para = [], False
    for ruta in argv:
        t = Path(ruta).read_text(encoding="utf-8")
        textos.append(t)
        avisos = revisa(t, palabras=palabras)
        para = para or any(a.para for a in avisos)
        print(f"== {ruta}: {'limpio' if not avisos else ''}")
        for a in avisos:
            print("  ", a)
    for a in revisa_tanda(textos):
        print("== la tanda:", a)
    return 1 if para else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
