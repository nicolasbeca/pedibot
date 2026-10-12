"""A source whose address only changes its encoding has not moved (12-oct-2026).

Every Sunday `sources_check` counted four Vikaspedia pages as "working through a redirect": we
store the Hindi path as letters, the site answers with the same path percent-encoded. Same page,
same words — and the warning came back each week for someone to look at and dismiss.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx

from pedibot.ops import sources_alive


def _fake_get(final: str):
    def get(url, **_kw):
        return SimpleNamespace(url=final, status_code=200)

    return get


def test_the_same_path_percent_encoded_is_ok(monkeypatch) -> None:
    ours = "https://health.vikaspedia.in/viewcontent/health/child-health/तीव्र-श्‍वसन-रोग?lgn=hi"
    theirs = httpx.URL(ours).__str__()
    assert "%E0" in theirs
    monkeypatch.setattr(httpx, "get", _fake_get(theirs))
    assert sources_alive._probe(("vikaspedia_hi_5224", ours))[2] == "ok"


def test_a_real_move_is_still_a_move(monkeypatch) -> None:
    ours = "https://www.nhs.uk/conditions/pelvic-pain/"
    monkeypatch.setattr(httpx, "get", _fake_get("https://www.nhs.uk/symptoms/pelvic-pain/"))
    assert sources_alive._probe(("nhs_en_pelvic_pain", ours))[2] == "movida"
