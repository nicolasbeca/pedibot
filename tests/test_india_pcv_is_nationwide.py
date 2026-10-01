"""El neumococo es nacional en la India desde 2021 (1-oct-2026).

El calendario indio se transcribió del PDF del NHM de 2018, que marca la PCV como «selected
states only». El 29-oct-2021 el ministerio la extendió a todo el país dentro del Programa
Universal de Inmunización (nota de prensa del PIB, PRID 1767478; Gavi: «India completes national
introduction of pneumococcal conjugate vaccine»). La página decía a un padre de Kerala o de
Bengala Occidental que a su hijo no le tocaba una vacuna gratuita que sí le toca. Se vio al
preparar el correo a la Indian Academy of Pediatrics, que lo habría visto a la primera.
"""

from __future__ import annotations

import yaml

from pedibot.settings import ROOT


def _india() -> dict:
    datos = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))

    def busca(d):  # noqa: ANN001, ANN202
        if isinstance(d, dict):
            if "IN" in d and isinstance(d["IN"], dict) and "schedule" in d["IN"]:
                return d["IN"]
            for v in d.values():
                r = busca(v)
                if r:
                    return r
        return None

    pais = busca(datos)
    assert pais, "no encuentro la India en vaccines.yaml"
    return pais


def test_no_dose_says_selected_states() -> None:
    for fila in _india()["schedule"]:
        for v in fila["vaccines"]:
            assert "selected states" not in v, v


def test_the_note_no_longer_limits_pcv_in_any_language() -> None:
    for lang, texto in _india()["note"].items():
        assert "Bihar" not in texto and "बिहार" not in texto, (lang, texto[:120])


def test_the_correction_names_its_source() -> None:
    assert "PIB" in _india()["source"] and "2021" in _india()["source"]
