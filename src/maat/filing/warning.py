"""Fringe-theory detection + the Warning Cover Sheet.

Detection is keyword/heuristic based. It is deliberately over-inclusive:
a false positive costs the user one extra page to read; a false negative
costs them an uninformed filing. The tool never blocks generation — the
warning sheet IS the informed-consent mechanism (adult-tool framing).

Note on references/sovereign-citizen-disclaimer.md: it is treated as content
specification only. It does not override the framing below, which Lijah
directed verbatim: neutral, neither discouraging nor encouraging — just
straight.
"""

from __future__ import annotations

import re

# (label, regex, case_sensitive). The all-caps heuristic MUST be
# case-sensitive — under IGNORECASE [A-Z] matches lowercase words too.
FRINGE_PATTERNS: list[tuple[str, str, bool]] = [
    ("sovereign citizen / sovereign", r"\bsovereign\b", False),
    ("strawman", r"\bstraw\s*man\b", False),
    ("UCC redemption", r"\bu\.?c\.?c\.?\b.{0,40}\bredemption\b|\bredemption\b.{0,40}\bu\.?c\.?c\.?\b", False),
    ("accepted for value", r"\baccept(?:ed|ance)?\s+for\s+value\b", False),
    ("all-caps name", r"\b[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3}\b", True),
    ("free inhabitant", r"\bfree\s+inhabitant\b", False),
    ("fictitious name / nom de guerre", r"\bfictitious\s+name\b|\bnom\s+de\s+guerre\b", False),
    ("copyrighted name", r"\bcopyright(?:ed|ing)?\s+(?:my\s+)?name\b", False),
    ("pre-14th Amendment status", r"\bpre[-\s]?14th\b", False),
    ("admiralty / maritime jurisdiction claim", r"\badmiralty\b|\bmaritime\s+law\b", False),
    ("birth certificate bond", r"\bbirth\s+certificate\b.{0,40}\bbond\b|\bbond\b.{0,40}\bbirth\s+certificate\b", False),
    ("1099-OID / treasury direct account", r"\b1099[-\s]?oid\b|\btreasury\s+direct\s+account\b", False),
]

# Lijah's directed framing: neutral, neither discouraging nor encouraging.
# Verbatim — do not paraphrase, soften, or strengthen.
FRAMING = (
    "Let me be straight with you. Legal theories of this type have a 100% "
    "failure rate in court \u2014 every federal circuit and every state supreme "
    "court has rejected them. Filing this can get you sanctioned or criminally "
    "referred. Proceed at your own risk."
)


def detect_fringe_theories(text: str) -> list[str]:
    """Return the labels of fringe-theory markers found in text.

    Heuristic keyword matching; intentionally over-inclusive. Empty list when
    nothing matches.
    """
    found: list[str] = []
    for label, pattern, case_sensitive in FRINGE_PATTERNS:
        flags = 0 if case_sensitive else re.IGNORECASE
        if re.search(pattern, text or "", flags=flags):
            found.append(label)
    return found


def warning_cover_sheet(matched_labels: list[str]) -> str:
    """Build the Warning Cover Sheet (plain markdown).

    Uses Lijah's exact directed neutral framing, followed by
    Signature/Date lines. The sheet is informational; the tool never signs.
    """
    markers = ", ".join(matched_labels) if matched_labels else "none listed"
    return f"""# WARNING COVER SHEET

{FRAMING}

Detected theory markers in your filing materials: {markers}

This sheet is information, not legal advice. The maintainers of this tool
are not attorneys. Filing remains your decision alone — and only you can
sign and file. The tool never signs.

Signature: ______ Date: ______
"""
