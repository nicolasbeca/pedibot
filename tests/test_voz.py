"""El filtro de voz antes de que salga un correo o un texto (3-nov-2026, ops/voz.py y ops/VOZ.md).

Wayan Vota (ICTworks), 1-nov, sobre el borrador del artículo: «This reads as if it was written by
AI… It sounds like a copy-paste from AI. Please add your own color to the words». No era la
primera vez: el 14-oct el operador ya leyó «a veces parece muy IA» en la tercera tanda (la lista de
idiomas entre paréntesis, la misma estructura en los cinco, «I'd be really grateful», «Thank you for
the work you do»). Lo que se puede contar, lo cuenta el código: si un texto trae una raya larga,
una lista, una frase de plantilla o un enlace sin su canal, no sale.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _voz():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location("voz", ROOT / "ops" / "voz.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["voz"] = m  # la dataclass lo busca ahí
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


voz = _voz()


def _paran(texto: str, **kw) -> set[str]:  # noqa: ANN003
    return {a.regla for a in voz.revisa(texto, **kw) if a.para}


def _ojos(texto: str, **kw) -> set[str]:  # noqa: ANN003
    return {a.regla for a in voz.revisa(texto, **kw) if not a.para}


LIMPIO = """Hola, Laura:

El Gelocatil para niños se vende en gotas de 100 mg por ml y en jarabe de 120 mg por 5 ml. Misma
marca, y las gotas son unas cuatro veces más fuertes. Me lo encontré haciendo la calculadora de
PediBot, una web gratis que contesta con guías oficiales.

Por eso la calculadora pregunta primero qué frasco tienes: https://pedibot.xyz/es/dose?r=maldita

Si te interesa, te mando las fuentes.

Un saludo,
Nicolas Beca
"""


def test_a_plain_short_email_goes_out():
    assert _paran(LIMPIO) == set()


def test_long_dashes_stop_it():
    assert "raya_larga" in _paran(LIMPIO.replace("Misma\nmarca,", "Misma marca —"))
    assert "raya_larga" in _paran(LIMPIO.replace("Misma\nmarca,", "Misma marca –"))


def test_lists_and_numbered_headings_stop_it():
    """«1. Local is a safety feature», en el borrador de ICTworks."""
    assert "lista" in _paran("Hello,\n\n1. Local is a safety feature\n\nThe word...")
    assert "lista" in _paran("Hello,\n\n- keep breastfeeding\n- no paracetamol\n")
    assert "lista" in _paran("Hello,\n\n• one thing\n")
    assert "markdown" in _paran("Hello, this is **important**.")


def test_template_phrases_stop_it():
    for frase in [
        "I hope this message finds you well.",
        "I'd be really grateful if you could share it.",
        "Thank you for the work you do.",
        "I'm reaching out because",
        "Espero que este correo te encuentre bien.",
        "No dudes en contactarme.",
    ]:
        assert "plantilla" in _paran(LIMPIO + "\n" + frase), frase


def test_the_signature_has_no_accent_and_every_link_its_channel():
    assert "firma" in _paran(LIMPIO.replace("Nicolas Beca", "Nicolás Beca"))
    assert "enlace_sin_canal" in _paran(LIMPIO.replace("?r=maldita", ""))
    assert "enlace_sin_canal" not in _paran("Mira https://pedibot.xyz/fr/vaccines/ml?r=muso.")


def test_curly_quotes_stop_it():
    assert "comillas" in _paran("He said “drops” and it’s fine.")
    # las españolas y las francesas son de verdad
    assert "comillas" not in _paran("Dice «gotas» y « gouttes ».")


def test_warnings_that_do_not_stop_it():
    largo = " ".join(["palabra"] * 200)
    assert "largo" in _ojos(largo)
    assert "largo" not in _ojos(largo, palabras=800)
    assert "no_solo" in _ojos("No solo calcula la dosis, sino también el frasco.")
    assert "no_solo" in _ojos("It's not just a calculator, it's a safety net.")
    assert "palabra_de_ia" in _ojos("A crucial and robust tool that fosters trust.")
    assert "palabra_de_ia" in _ojos("Es fundamental y cabe destacar que es clave.")


def test_the_ictworks_draft_would_not_have_gone_out():
    borrador = (ROOT / "tests" / "textos" / "voz_ictworks_29oct.txt").read_text(encoding="utf-8")
    assert "lista" in _paran(borrador, palabras=800)


def test_a_batch_that_opens_the_same_way_is_flagged():
    a = "Hello,\n\nI'm Nicolas Beca, writing from Seville. One thing.\n\nNicolas Beca"
    b = "Hello,\n\nI'm Nicolas Beca, writing from Seville. Other thing.\n\nNicolas Beca"
    c = "Hi Ana,\n\nYour crèches in Colaba gave me the idea.\n\nNicolas Beca"
    assert "misma_entrada" in {x.regla for x in voz.revisa_tanda([a, b, c])}
    assert "misma_entrada" not in {x.regla for x in voz.revisa_tanda([a, c])}


def test_the_same_product_line_in_every_email_is_flagged():
    """La tanda del 30-oct pasaba limpia correo a correo, y los diez abrían «Soy Nicolas Beca y
    escribo desde Sevilla. Hago PediBot, una web gratuita que…», con «con la fuente debajo de cada
    respuesta» en cuatro. Eso es la plantilla, y sólo se ve juntándolos."""
    base = "Hola:\n\n{} Hago PediBot, una web que contesta con la fuente debajo de cada respuesta.\n"
    tanda = [base.format(x) for x in ("Una cosa.", "Otra cosa.", "La tercera.", "Y la cuarta.")]
    avisos = {x.regla for x in voz.revisa_tanda(tanda)}
    assert "frase_repetida" in avisos


def test_opening_with_who_you_are_is_flagged():
    assert "se_presenta_primero" in _ojos("Hola:\n\nSoy Nicolas Beca y escribo desde Sevilla.")
    assert "se_presenta_primero" in _ojos("Hello,\n\nI'm Nicolas Beca, writing from Seville.")
    assert "se_presenta_primero" not in _ojos("Hola, Laura:\n\nEl Gelocatil para niños se vende…")


def _correo():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location("correo", ROOT / "ops" / "correo.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["correo"] = m
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


def test_correo_does_not_send_what_the_filter_stops(tmp_path, monkeypatch):
    correo = _correo()
    enviados = []
    monkeypatch.setattr(correo, "enviar", lambda *a, **k: enviados.append(a) or "<id>")
    malo = tmp_path / "malo.txt"
    malo.write_text("Hello,\n\nI hope this message finds you well — here it is.\n", encoding="utf-8")
    try:
        correo.main(["--to", "x@y.org", "--subject", "s", "--body", str(malo)])
    except SystemExit as e:
        assert e.code == 2
    assert enviados == []
    # a sabiendas, sí
    correo.main(["--to", "x@y.org", "--subject", "s", "--body", str(malo), "--sin-filtro"])
    assert len(enviados) == 1
    bueno = tmp_path / "bueno.txt"
    bueno.write_text(LIMPIO, encoding="utf-8")
    correo.main(["--to", "x@y.org", "--subject", "s", "--body", str(bueno)])
    assert len(enviados) == 2
