"""Cada aviso trae el pasaje que lo respalda, o ninguno (7-oct-2026).

Cuando salta una regla de alarma, el redactor recibe delante el pasaje de su fuente para poder
citarlo. Se elegía «el primer pasaje de alarma» del documento, y comprobado regla a regla con el
modelo, en 75 de 97 no decía lo que dice el aviso: al estridor, a la invaginación y al monóxido
de carbono les llegaba la prevención de enfermedades genéticas del manual de pediatría cubano. Las
respuestas cosían entonces listas de alarma de otra cosa (el juez contra las guías lo marcaba
como «wrong»). Ahora cada regla nombra su pasaje (`source_chunk`), elegido por el modelo entre
candidatos de su documento y del corpus y revisado a mano (cinco rechazados por tratar de otra
situación). Sin pasaje comprobado, no se inyecta nada: mejor nada que un pasaje equivocado.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.index.store import Index
from pedibot.settings import get_settings

S = get_settings()
REGLAS = Triage(S.config_dir / "red_flags.yaml").rules


def test_la_mayoria_tiene_su_pasaje() -> None:
    assert sum(1 for r in REGLAS if r.source_chunk) >= 80


@pytest.mark.skipif(not S.index_db_path.exists(), reason="sin índice")
@pytest.mark.parametrize("regla", [r for r in REGLAS if r.source_chunk], ids=lambda r: r.id)
def test_el_pasaje_existe_y_es_de_su_fuente(regla) -> None:  # noqa: ANN001
    c = Index(S.index_db_path).get(regla.source_chunk)
    assert c is not None, f"{regla.id}: {regla.source_chunk} no está en el índice"
    assert c.doc_id == regla.source, f"{regla.id}: el pasaje es de {c.doc_id}, la fuente {regla.source}"


@pytest.mark.parametrize(
    ("regla", "pasaje"),
    [
        ("stridor", "ecimed_pediatria_2016#manifestaciones_clinicas#18"),
        ("cold_extremities_with_fever", "nhs_en_fever_in_children#don_t#1"),
        ("button_battery", "seup_acudir_urgencias#comporta_miento#1"),
    ],
)
def test_algunos_conocidos(regla: str, pasaje: str) -> None:
    assert {r.id: r.source_chunk for r in REGLAS}[regla] == pasaje
