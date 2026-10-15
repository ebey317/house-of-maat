"""Tests for maat.connectors.seeds (Black's 4th seed-context connector)."""

import sqlite3

from maat.connectors import seeds


def test_blacks_negligence_returns_real_definition():
    out = seeds.seed_context("What is negligence?", "blacks")
    assert "NEGLIGENCE" in out
    # verbatim text from Black's Law Dictionary, 4th ed., rev. 1968
    assert "The omission to do something" in out
    assert "not built" not in out


def test_blacks_multiword_term():
    out = seeds.seed_context("negligence per se", "blacks")
    assert "NEGLIGENCE PER SE" in out


def test_blacks_no_match_is_honest():
    out = seeds.seed_context("qxzylphobic flibbertigibbet", "blacks")
    assert "no Black's 4th definitions matched" in out


def test_blacks_missing_index_degrades_honestly(tmp_path, monkeypatch):
    monkeypatch.setattr(seeds, "INDEX_PATH", tmp_path / "does-not-exist.sqlite")
    out = seeds.seed_context("negligence", "blacks")
    assert "not built" in out
    assert "build_blacks_index.py" in out
    # and it must not contain anything shaped like a definition
    assert "**" not in out


def test_maat_corpus_has_42_declarations():
    laws = seeds._load_maat_laws()
    assert len(laws) == 42, f"expected 42 declarations, got {len(laws)}"
    assert laws[0][0] == 1 and laws[-1][0] == 42
    # verbatim Budge translation spot checks
    assert laws[2] == (3, "I have not stolen. (Hail, Fenti, who comest forth from Khemenu)")
    assert laws[32] == (
        33,
        "I have wronged none, I have done no evil. (Hail, Nefer-Tem, who comest forth from Het-ka-Ptah)",
    )


def test_maat_query_returns_matching_declarations():
    out = seeds.seed_context("what was stolen?", "maat")
    assert "42 Laws of Ma\u2019at" in out
    assert "I have not stolen." in out
    assert "not operative law" in out


def test_maat_no_match_is_honest():
    out = seeds.seed_context("qxzylphobic flibbertigibbet", "maat")
    assert "42 Laws of Ma\u2019at" in out
    assert "No declarations matched" in out
    # and it must not invent a declaration
    assert "  1. " not in out


def test_maat_missing_file_degrades_honestly(tmp_path, monkeypatch):
    monkeypatch.setattr(seeds, "MAAT_PATH", tmp_path / "no-maat.md")
    monkeypatch.setattr(seeds, "_MAAT_LAWS", None)
    out = seeds.seed_context("stealing", "maat")
    assert "not found" in out
    assert "42-laws-of-maat.md" in out


def test_all_sources_combines_blacks_and_maat():
    out = seeds.seed_context("negligence", "all")
    assert "NEGLIGENCE" in out
    assert "42 Laws of Ma\u2019at" in out
    assert "not yet indexed" not in out


def test_unknown_sources():
    assert seeds.seed_context("negligence", "bogus") == "(no seed sources selected)"


def test_index_fts_agrees_with_base_table():
    # the committed build script populates both tables identically
    con = sqlite3.connect(f"file:{seeds.INDEX_PATH}?mode=ro", uri=True)
    try:
        n_base = con.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
        n_fts = con.execute("SELECT COUNT(*) FROM definitions_fts").fetchone()[0]
    finally:
        con.close()
    assert n_base > 10000, f"unexpectedly small index: {n_base}"
    assert n_base == n_fts
