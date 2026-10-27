"""Bajo el aviso, en suajili, nada en inglés (27-oct-2026).

Visto en vivo el 26-oct: «Mtoto wangu wa wiki 6 ana homa ya 38.2» daba el aviso en suajili y,
debajo, «First, do what the warning above says.» en inglés, porque las frases fijas bajo el aviso
no tenían suajili y caían al inglés. Y el texto no se leía como prisa aunque dijera «leo».
"""

from pedibot.bot.answer import SIGUE_EL_AVISO
from pedibot.bot.banner_lead import PRIMERO_EL_AVISO, con_el_aviso_delante


def test_la_frase_delante_del_texto_va_en_suajili():
    texto = "Endelea kumnyonyesha kama kawaida, na mpe maji mengi."
    out = con_el_aviso_delante(texto, "urgent", "sw")
    assert out.startswith(PRIMERO_EL_AVISO["sw"])
    assert "warning" not in out


def test_si_el_texto_ya_dice_prisa_en_suajili_no_se_toca():
    texto = "Mpeleke mtoto hospitali leo, bila kusubiri."
    assert con_el_aviso_delante(texto, "urgent", "sw") == texto
    texto = "Piga simu sasa hivi kwa huduma ya dharura."
    assert con_el_aviso_delante(texto, "emergency", "sw") == texto


def test_la_frase_sale_en_la_lengua_escrita_no_en_la_de_busqueda():
    """El suajili se busca en inglés: a.lang es «en». Desplegado con a.lang, seguía en inglés."""
    import inspect

    from pedibot.bot import answer
    from pedibot.bot.answer import Answer

    a = Answer(
        text="x", level="urgent", banner=None, sources=[], lang="en", prompt_version=None,
        llm=None, chunk_ids=[], verification="ok", wrote_in="Swahili",
    )
    assert a.written_lang in PRIMERO_EL_AVISO
    assert "con_el_aviso_delante(a.text, a.level, a.written_lang)" in inspect.getsource(answer)


def test_sin_fuente_bajo_el_aviso_tambien_en_suajili():
    assert "sw" in SIGUE_EL_AVISO
    assert "warning" not in SIGUE_EL_AVISO["sw"]
