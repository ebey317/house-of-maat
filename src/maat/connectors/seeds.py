"""Seed-context connector: pull definitions from local seed corpora.

Sources:
    'blacks' -- Black's Law Dictionary, 4th ed. (local FTS5 index at
                data/blacks4.sqlite, built by scripts/build_blacks_index.py)
    'maat'   -- the 42 Laws of Maat corpus (not indexed yet)
    'all'    -- both of the above

If an index is absent the function says so honestly; it never invents
definitions.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

INDEX_PATH = Path(__file__).resolve().parents[3] / "data" / "blacks4.sqlite"

BLACKS_MISSING = "(Black's 4th index not built \u2014 run scripts/build_blacks_index.py)"
MAAT_MISSING = "(42 Laws of Maat corpus not yet indexed \u2014 no seed definitions available)"
NO_SOURCES = "(no seed sources selected)"

_STOPWORDS = frozenset(
    """
    a an the and or of to in on for with what what is are was were be been being
    by as at from that this these those it its it s he she they we you i me my
    do does did done have has had having will would should could can may might
    must shall not no yes if then than so such very just about into over under
    when where which who whom whose why how all any both each few more most
    other some there their them his her our your mean means meaning define
    definition legal law laws court case
    """.split()
)

_DEF_CHAR_LIMIT = 1200
_MAX_RESULTS = 5


def _key_terms(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", question.lower())
    terms: list[str] = []
    for w in words:
        w = w.strip("'")
        if len(w) > 2 and w not in _STOPWORDS and w not in terms:
            terms.append(w)
    return terms[:12]


def _open_index() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{INDEX_PATH}?mode=ro", uri=True)


def _query_blacks(question: str) -> str:
    if not INDEX_PATH.exists():
        return BLACKS_MISSING
    terms = _key_terms(question)
    if not terms:
        return "(no searchable terms found in question)"
    try:
        con = _open_index()
        try:
            rows: list[tuple[str, str]] = []
            seen: set[str] = set()

            def add(term: str, definition: str) -> None:
                if term not in seen and len(rows) < _MAX_RESULTS:
                    rows.append((term, definition))
                    seen.add(term)

            # 1. multiword questions: try the key terms as an exact phrase
            #    ("negligence per se" should surface NEGLIGENCE PER SE)
            if len(terms) >= 2:
                phrase = " ".join(terms)
                for term, definition in con.execute(
                    "SELECT term, definition FROM definitions_fts "
                    "WHERE definitions_fts MATCH ? ORDER BY rank LIMIT 3",
                    (f'"{phrase}"',),
                ):
                    add(term, definition)

            # 2. exact headword matches (case-insensitive)
            placeholders = ",".join("?" for _ in terms)
            for term, definition in con.execute(
                f"SELECT term, definition FROM definitions "
                f"WHERE lower(term) IN ({placeholders})",
                [t for t in terms],
            ):
                add(term, definition)

            # 3. full-text matches for the rest, best rank first
            match_q = " OR ".join(f'"{t}"' for t in terms)
            for term, definition in con.execute(
                "SELECT term, definition FROM definitions_fts "
                "WHERE definitions_fts MATCH ? ORDER BY rank LIMIT ?",
                (match_q, _MAX_RESULTS * 3),
            ):
                add(term, definition)
                if len(rows) >= _MAX_RESULTS:
                    break
        finally:
            con.close()
    except sqlite3.Error as exc:
        return f"(Black's 4th index unreadable: {exc})"

    if not rows:
        return "(no Black's 4th definitions matched the question)"
    parts = ["Black's Law Dictionary (4th ed.) \u2014 seed definitions:"]
    for term, definition in rows[:_MAX_RESULTS]:
        if len(definition) > _DEF_CHAR_LIMIT:
            definition = definition[:_DEF_CHAR_LIMIT].rstrip() + " \u2026"
        parts.append(f"\n**{term}.** {definition}")
    return "\n".join(parts)


def seed_context(question: str, sources: str) -> str:
    """Return seed-corpus context text relevant to *question*.

    *sources* is 'blacks', 'maat', or 'all'. Missing corpora are reported
    honestly; definitions are never invented.
    """
    sections: list[str] = []
    if sources in ("all", "blacks"):
        sections.append(_query_blacks(question))
    if sources in ("all", "maat"):
        sections.append(MAAT_MISSING)
    return "\n\n".join(sections) if sections else NO_SOURCES
