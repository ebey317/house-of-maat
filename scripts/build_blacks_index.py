#!/usr/bin/env python3
"""Build the Black's Law Dictionary (4th ed., rev. 1968) SQLite FTS5 index.

Reads the dictionary pages of a Black's 4th PDF, parses headword entries
(term + definition), and writes a SQLite database containing:

    definitions(term TEXT PRIMARY KEY, definition TEXT)
    definitions_fts   -- FTS5 index over (term, definition)
    build_meta        -- provenance: pdf sha256, page range, entry count

Usage:
    python3 scripts/build_blacks_index.py [--pdf PATH] [--db PATH]

Defaults are repo-relative: --pdf data/blacks4.pdf, --db data/blacks4.sqlite.
Run from the repo root, or pass absolute paths.

Deterministic: the same PDF bytes always produce the same rows in the same
order. The script is the source of truth; the .sqlite file is a local build
artifact (gitignored).

Requires: pymupdf  (pip install pymupdf)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

# --- entry detection -------------------------------------------------------
# Normal headword: ALL-CAPS term (letters, digits, spaces, ' & / - ( ) ),
# no internal periods (those are handled by ABBREV_RE), followed by ". "
# and a definition that starts with a letter, quote, or paren.
NORMAL_RE = re.compile(r"^([A-Z][A-Z0-9'&/\-() ]{0,60}?)\.\s+(?=[A-Za-z\"'(])")
# Abbreviation headword: 2-3 dotted capital groups, e.g. "A.D.",
# "F.O.B.", "CA. SA.". Requires a letter after the final period so
# citation fragments like "L.R. 1479" or "S. Ct. 308" (digit follows)
# are not treated as entries.
ABBREV_RE = re.compile(r"^((?:[A-Z]{1,4}\.\s*){2,3})(?=[A-Za-z])")
# Small Roman numerals are never real headwords; they appear only as
# wrapped regnal-year citations ("9 Hen. / VI. c. 65") or numbered list
# items ("II. / Villeinage") inside other entries. Restricted to I/V/X
# so real two-letter entries like "CI" (Law French) and "DI" survive.
_ROMAN_RE = re.compile(r"^[IVX]{2,}$")

# Page geometry (Black's 4th PDF: 514 x 696 pt pages, two text columns).
COL_SPLIT_X = 160.0   # left column blocks have x0 < this
HEADER_Y = 34.0       # guide-word header sits above this
FOOTER_Y = 644.0      # footer page-number sits below this

# Markers used to locate the dictionary page range inside the PDF.
START_MARKER = "The first letter in the English"  # from the "A." entry
END_MARKER = "ZYTHUM"  # last headword of the Z section


def page_column_lines(page):
    """Return (left_lines, right_lines) for one page, in reading order.

    Built from pymupdf's word boxes: words are grouped into lines and
    blocks, blocks are split into the two columns by x position and
    ordered top to bottom. Joining explicit word boxes (rather than raw
    span text) keeps inter-word spaces intact.
    """
    blocks: dict[int, dict] = {}
    for x0, y0, x1, y1, word, bno, lno, _wno in page.get_text("words"):
        b = blocks.setdefault(bno, {"x0": x0, "y0": y0, "lines": {}})
        b["x0"] = min(b["x0"], x0)
        b["y0"] = min(b["y0"], y0)
        b["lines"].setdefault(lno, []).append((x0, word))
    columns: list[list[tuple[float, list[str]]]] = [[], []]
    for b in blocks.values():
        if b["y0"] < HEADER_Y or b["y0"] > FOOTER_Y:  # header / footer
            continue
        lines = [
            " ".join(w for _, w in sorted(b["lines"][lno], key=lambda t: t[0]))
            for lno in sorted(b["lines"])
        ]
        columns[0 if b["x0"] < COL_SPLIT_X else 1].append((b["y0"], lines))
    result = []
    for col in columns:
        col.sort(key=lambda t: t[0])
        result.append([ln for _, lines in col for ln in lines])
    return result[0], result[1]


def clean_entry_text(raw: str) -> str:
    """De-hyphenate line breaks and collapse whitespace.

    A line-end hyphen followed by a lowercase continuation is a
    hyphenation break ("para-\\nmount" -> "paramount"); otherwise the
    hyphen is real ("well-\\nknown" keeps its hyphen).
    """
    text = raw.replace("\xad", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = text.replace("-\n", "-")
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_entries(column_text: str):
    """Yield (term, definition) pairs from one column of dictionary text."""
    current_term = None
    current_lines: list[str] = []

    def flush():
        if current_term is not None:
            definition = clean_entry_text("\n".join(current_lines))
            # single letters are citation fragments ("E. I. Ry. Co."),
            # not entries -- the only real one-letter headword is "A";
            # lettered subdivision markers ("A. general acceptance...")
            # start their text lowercase, the real "A." entry does not
            if len(current_term) == 1 and current_term != "A":
                return
            if current_term == "A" and definition[:1].islower():
                return
            # Roman numerals are wrapped citations / list items, not entries
            if _ROMAN_RE.match(current_term):
                return
            # abbreviation entries need a real definition, not a wrapped
            # citation fragment ("C.J.S." / "p. 1059.")
            if "." in current_term and len(definition) < 10:
                return
            if definition and len(definition) >= 3:
                yield current_term, definition

    for line in column_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = ABBREV_RE.match(stripped) or NORMAL_RE.match(stripped)
        if m:
            yield from flush()
            # NOTE: the PDF's text layer mis-encodes some glyphs (the ae
            # ligature and a few others surface as 1/2/4/7/0/). The mapping
            # is ambiguous, so terms are kept verbatim rather than guessed.
            current_term = re.sub(r"\s+", " ", m.group(1)).strip()
            current_lines = [stripped[m.end():]]
        elif current_term is not None:
            current_lines.append(stripped)
        # text before the first headword on the page is ignored
    yield from flush()


def find_dict_range(doc):
    """Locate the dictionary pages: first page with START_MARKER to the
    last page with END_MARKER (0-based, inclusive)."""
    start = end = None
    for i in range(doc.page_count):
        text = doc[i].get_text()
        if start is None and START_MARKER in text:
            start = i
        if END_MARKER in text:
            end = i
    if start is None or end is None or end < start:
        raise SystemExit("could not locate dictionary page range in PDF")
    return start, end


def build(pdf_path: Path, db_path: Path) -> int:
    import pymupdf

    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    doc = pymupdf.open(str(pdf_path))
    start, end = find_dict_range(doc)
    print(f"PDF pages: {doc.page_count}, dictionary pages: {start + 1}-{end + 1} "
          f"(1-based), sha256: {sha[:16]}...", flush=True)

    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    page_count = doc.page_count
    # One continuous line stream in reading order (left column, then right,
    # page after page) so entries that span a column or page break parse
    # whole instead of being truncated.
    all_lines: list[str] = []
    for pi in range(start, end + 1):
        page = doc[pi]
        left, right = page_column_lines(page)
        all_lines.extend(left)
        all_lines.append("")
        all_lines.extend(right)
        all_lines.append("")
        if (pi - start) % 300 == 0:
            print(f"  ... page {pi + 1}", flush=True)
    doc.close()
    for term, definition in parse_entries("\n".join(all_lines)):
        if len(term) > 80 or term in seen:
            continue
        seen.add(term)
        entries.append((term, definition))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("CREATE TABLE definitions(term TEXT PRIMARY KEY, definition TEXT)")
    cur.execute("CREATE VIRTUAL TABLE definitions_fts USING fts5(term, definition)")
    cur.executemany("INSERT INTO definitions(term, definition) VALUES (?, ?)", entries)
    cur.executemany("INSERT INTO definitions_fts(term, definition) VALUES (?, ?)", entries)
    cur.execute("CREATE TABLE build_meta(key TEXT PRIMARY KEY, value TEXT)")
    cur.executemany(
        "INSERT INTO build_meta(key, value) VALUES (?, ?)",
        [
            ("source", "Black's Law Dictionary, Revised Fourth Edition (West, 1968)"),
            ("pdf_sha256", sha),
            ("pdf_pages", str(page_count)),
            ("dict_pages", f"{start + 1}-{end + 1}"),
            ("entries", str(len(entries))),
            ("built_utc", datetime.datetime.now(datetime.timezone.utc).isoformat()),
        ],
    )
    con.commit()
    # integrity check: FTS must see the same rows as the base table
    n_base = cur.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
    n_fts = cur.execute("SELECT COUNT(*) FROM definitions_fts").fetchone()[0]
    con.close()
    assert n_base == n_fts == len(entries), (n_base, n_fts, len(entries))
    print(f"wrote {db_path}: {len(entries)} entries")
    return len(entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the Black's 4th FTS5 index.")
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--pdf", default=str(here / "data" / "blacks4.pdf"))
    ap.add_argument("--db", default=str(here / "data" / "blacks4.sqlite"))
    args = ap.parse_args(argv)
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 1
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        print("pymupdf is required: pip install pymupdf", file=sys.stderr)
        return 1
    build(pdf_path, Path(args.db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
