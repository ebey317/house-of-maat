"""Tests for maat.translate — the Scrivener function."""

from maat import translate
from maat.translate import plain_english_to_legal


def test_boundary_in_docstring():
    doc = (translate.__doc__ or "").lower()
    assert "scrivener, not counsel" in doc
    assert "does not" in doc or "does not advise" in doc


def test_strips_filler():
    out = plain_english_to_legal("Um, basically I was fired on Tuesday, you know.")
    assert "Um" not in out and "um," not in out.lower().replace("sum", "")
    assert "basically" not in out.lower()
    assert "you know" not in out.lower()


def test_first_person_becomes_numbered_allegations():
    out = plain_english_to_legal("I was fired on September 22. My boss never gave me a warning.")
    assert "1. Movant states that" in out
    assert "2. Movant states that" in out
    assert "fired on september 22" in out.lower()
    assert "movant's boss never gave" in out.lower()


def test_contractions_resolved():
    out = plain_english_to_legal("I'm asking the court for help. I've paid the fee.")
    lowered = out.lower()
    assert "movant is asking" in lowered
    assert "movant has paid" in lowered


def test_complaint_shape():
    out = plain_english_to_legal("The defendant owes me five thousand dollars.", doc_type="complaint")
    assert "COMPLAINT" in out
    assert "Plaintiff states that" in out
    assert "IN THE [COURT NAME]" in out


def test_affidavit_shape():
    out = plain_english_to_legal("I saw the accident happen.", doc_type="affidavit")
    assert "AFFIDAVIT" in out
    assert "Affiant states that" in out


def test_signature_block_unsigned():
    out = plain_english_to_legal("Something happened.")
    assert "UNSIGNED" in out
    assert "The tool never signs" in out


def test_empty_text():
    out = plain_english_to_legal("")
    assert "No factual narrative was provided" in out


def test_unknown_doc_type_defaults_to_motion():
    out = plain_english_to_legal("I need help.", doc_type="not-a-type")
    assert "Movant states that" in out


def test_extract_allegations():
    from maat.translate import extract_allegations

    doc = plain_english_to_legal("I was fired. My boss lied.")
    allegations = extract_allegations(doc)
    assert len(allegations) == 2
    assert allegations[0].startswith("1. Movant states that")
    assert "IN THE [COURT NAME]" not in "\n".join(allegations)
