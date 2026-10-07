"""«Head» es palabra entera (7-oct-2026).

Por prefijo, el disparador «head» casaba «headache» y «heads», y «how do I know if my child has
head lice» se ampliaba con «traumatismo craneal, golpe»: tres pasajes de la SEUP sobre el TCE y
ninguno de los tres sobre piojos que hay en inglés. De 3.839 búsquedas cambian seis, todas a mejor.
"""

from __future__ import annotations

from pedibot.bot.retrieval import Synonyms
from pedibot.settings import get_settings

S = get_settings()
SYN = Synonyms(S.config_dir / "synonyms.yaml", S.config_dir / "drugs.yaml")


def test_un_dolor_de_cabeza_no_es_un_golpe() -> None:
    assert "traumatismo craneal" not in SYN.expand("my teenager has a headache every morning", "en")


def test_los_piojos_son_piojos() -> None:
    extra = SYN.expand("how do I know if my child has head lice", "en")
    assert "head lice" in extra and "piojos" in extra


def test_un_golpe_en_la_cabeza_sigue_siendolo() -> None:
    assert "traumatismo craneal" in SYN.expand("my son hit his head on the table", "en")
