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


def test_maat_corpus_not_indexed():
    out = seeds.seed_context("anything at all", "maat")
    assert "not yet indexed" in out


def test_all_sources_combines_blacks_and_maat_note():
    out = seeds.seed_context("negligence", "all")
    assert "NEGLIGENCE" in out
    assert "not yet indexed" in out


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
