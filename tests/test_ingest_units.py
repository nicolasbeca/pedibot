from __future__ import annotations

from pathlib import Path

from pedibot.ingest.catalog import catalog_by_file, load_catalog
from pedibot.ingest.chunk import MAX_WORDS, chunk_section
from pedibot.ingest.clean import clean, join_hyphenated, normalize_line, repeated_lines
from pedibot.ingest.extract import Extracted, Line, PageText
from pedibot.ingest.pipeline import slug
from pedibot.ingest.sections import Section, is_heading, split_sections


def _ex(pages: list[list[tuple[str, float]]], body: float = 10.0) -> Extracted:
    pts = []
    for i, lines in enumerate(pages, start=1):
        pts.append(PageText(number=i, lines=[Line(t, s, page=i) for t, s in lines]))
    return Extracted(path=Path("x.pdf"), sha256="0" * 64, pages=pts, body_size=body)


# ---------- clean ----------
def test_normalize_collapses_whitespace_and_ligatures():
    assert normalize_line("in fec  ﬁebre ") == "in fec fiebre"


def test_join_hyphenated_only_inside_words():
    assert join_hyphenated("infec- ción alta") == "infección alta"
    assert join_hyphenated("4 - 6 h") == "4 - 6 h"


def test_repeated_headers_removed():
    ex = _ex(
        [
            [("SEUP hojas", 8), ("texto uno", 10)],
            [("SEUP hojas", 8), ("texto dos", 10)],
            [("SEUP hojas", 8), ("texto tres", 10)],
            [("3", 8), ("texto cuatro", 10)],
        ]
    )
    assert "seup hojas" in repeated_lines(ex)
    clean(ex)
    texts = [ln.text for p in ex.pages for ln in p.lines]
    assert "SEUP hojas" not in texts and "3" not in texts
    assert len(texts) == 4


# ---------- sections ----------
def test_question_heading_detected():
    assert is_heading(Line("¿QUÉ ES LA FIEBRE?", 10.0), 10.0)
    assert is_heading(Line("¿Cuándo debo consultar?", 10.0), 10.0)


def test_body_sentence_is_not_heading():
    assert not is_heading(
        Line("La fiebre es una elevación de la temperatura corporal.", 10.0), 10.0
    )
    assert not is_heading(Line("Signos:", 10.0), 10.0)


def test_bigger_font_is_heading():
    assert is_heading(Line("Tratamiento en casa", 13.0), 10.0)
    assert not is_heading(Line("Tratamiento en casa", 10.0), 10.0)


def test_split_sections_groups_lines():
    ex = _ex(
        [
            [
                ("FIEBRE", 14),
                ("¿QUÉ ES?", 11),
                ("Es una elevación.", 10),
                ("Más texto.", 10),
                ("¿CUÁNDO CONSULTAR?", 11),
                ("Si dura más de 5 días.", 10),
            ]
        ]
    )
    secs = split_sections(ex)
    assert [s.title for s in secs] == ["FIEBRE ¿QUÉ ES?", "¿CUÁNDO CONSULTAR?"]
    assert secs[0].text == "Es una elevación. Más texto."
    assert secs[1].pages == [1]


# ---------- chunk ----------
def test_short_section_single_chunk_with_flags():
    sec = Section("¿CUÁNDO ACUDIR A URGENCIAS?", [Line("Llame al 112 si no respira.", 10, page=2)])
    out = chunk_section(sec)
    assert len(out) == 1 and out[0].is_red_flag and not out[0].is_dose_table


def test_dose_table_never_split():
    text = ("Paracetamol 10-15 mg/kg/dosis cada 6 h. " * 100).strip()
    sec = Section("DOSIS", [Line(text, 10, page=5)])
    out = chunk_section(sec)
    assert len(out) == 1 and out[0].is_dose_table
    assert len(out[0].text.split()) > MAX_WORDS


def test_long_section_split_with_overlap():
    sents = [f"Frase número {i} sobre la fiebre del niño." for i in range(200)]
    sec = Section("TEXTO LARGO", [Line(" ".join(sents), 10, page=1)])
    out = chunk_section(sec)
    assert len(out) >= 3
    assert all(len(c.text.split()) <= MAX_WORDS for c in out)
    # overlap: the first sentence of chunk 2 appears in chunk 1
    first_sent_c2 = out[1].text.split(". ")[0]
    assert first_sent_c2 in out[0].text


# ---------- catalog ----------
def test_catalog_loads_and_covers_all_pdfs(config_dir):
    docs = load_catalog(config_dir / "fuentes.yaml")
    pdf_docs = [d for d in docs if d.file.endswith(".pdf") and not d.file.startswith("web/")]
    # 53: the 49 original PDFs (the 2 pitch decks live at the repo root), plus the OCR'd copy of
    # "las 50 principales consultas" — whose scanned original stays catalogued as `excluido` —
    # plus the three Indian documents added on 11-sep-2026 (IMNCI chart booklet, Home-Based
    # Newborn Care guidelines and the ASHA young-child handbook), all under the NHM licence
    assert len(pdf_docs) == 53
    assert len(docs) >= 49 + 150  # + curated web pages (config/fuentes_web.yaml)
    by_file = catalog_by_file(docs)
    assert len(by_file) == len(docs)
    assert by_file["15_Fiebre.pdf"].topic == "fiebre"
    assert by_file["dermatologia_pedi.pdf"].usage == "excluido"
    # the 2008 primary-care manual was measured and left out of the index (see its catalogue note)
    assert by_file["las_50_principales_consultas_ocr.pdf"].usage == "excluido"
    assert {d.usage for d in docs} <= {"publico", "citar_solo", "excluido"}


def test_slug():
    assert slug("¿CUÁNDO DEBO CONSULTAR EN URGENCIAS?") == "cuando_debo_consultar_en_urgencias"
    assert slug("") == "s"


# ---------- merge_small ----------
def test_merge_small_folds_tiny_chunks_into_previous():
    from pedibot.ingest.chunk import RawChunk, merge_small

    big = RawChunk("INTRO", [1], "palabra " * 100, False, False)
    tiny1 = RawChunk("PARACETAMOL", [2], "10-15 mg/kg/dosis", False, True)
    tiny2 = RawChunk("RECUERDA", [2], "hidratación", True, False)
    out = merge_small([big, tiny1, tiny2])
    assert len(out) == 1
    assert out[0].pages == [1, 2] and out[0].is_dose_table and out[0].is_red_flag
    assert "PARACETAMOL: 10-15 mg/kg/dosis" in out[0].text


def test_merge_small_first_tiny_goes_into_next():
    from pedibot.ingest.chunk import RawChunk, merge_small

    tiny = RawChunk("TITULO", [1], "corto", False, False)
    big = RawChunk("CUERPO", [1], "palabra " * 100, False, False)
    out = merge_small([tiny, big])
    assert len(out) == 1 and out[0].section == "TITULO" and "CUERPO:" in out[0].text


def test_merge_small_respects_max():
    from pedibot.ingest.chunk import MAX_WORDS, RawChunk, merge_small

    full = RawChunk("A", [1], "w " * MAX_WORDS, False, False)
    tiny = RawChunk("B", [1], "corto corto", False, False)
    out = merge_small([full, tiny])
    assert len(out) == 2


def test_bibliography_chunks_dropped():
    from pedibot.ingest.chunk import is_bibliography

    refs = " ".join(
        f"{i}. Smith J, et al. Title of paper. J Pediatr 2020;{i}:1-9. doi:10.1000/{i}"
        for i in range(12)
    )
    assert is_bibliography(refs)
    assert not is_bibliography(
        "La fiebre es una elevación de la temperatura corporal por encima de 38ºC. " * 20
    )
    assert chunk_section(Section("REFERENCES", [Line(refs, 10, page=9)])) == []


def test_taxonomy_empty_topic_never_matches(config_dir):
    from pedibot.ingest.classify import Taxonomy

    tax = Taxonomy(config_dir / "taxonomia.yaml")
    assert tax.topic_for("what is the capital of France") is None
    assert tax.topic_for("mi perro puede comer chocolate") is None
    assert tax.topic_for("my baby has a fever and a cough") in ("fiebre", "respiratorio")


def test_extract_html_keeps_main_and_headings(tmp_path: Path):
    from pedibot.ingest.extract_html import extract_html
    from pedibot.ingest.sections import split_sections

    html = """<html><head><title>Fever in children - NHS</title></head><body>
    <header><nav><a>Home</a></nav></header>
    <main><h1>Fever in children</h1><p>A fever is a high temperature.</p>
    <h2>When to get help</h2><ul><li>your child is under 3 months</li><li>has a rash that does not fade</li></ul>
    <div class="nhsuk-feedback">Was this page useful?</div><p>Page last reviewed: 12 May 2024</p></main>
    <footer>© Crown copyright</footer></body></html>"""
    p = tmp_path / "x.html"
    p.write_text(html, encoding="utf-8")
    ex = extract_html(p)
    texts = [ln.text for ln in ex.pages[0].lines]
    assert (
        "Home" not in texts
        and "Was this page useful?" not in texts
        and "© Crown copyright" not in texts
    )
    assert not any(t.startswith("Page last reviewed") for t in texts)
    secs = split_sections(ex)
    assert [s.title for s in secs][-1] == "When to get help"
    assert "under 3 months" in secs[-1].text
