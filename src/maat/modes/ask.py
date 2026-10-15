"""Ask mode — plain-English answers grounded ONLY in live sources.

Every case name, court, date, and citation in the output comes from a live
CourtListener API response. Nothing is invented: if the APIs are unreachable,
the answer says so honestly instead of answering from nothing.
"""

from __future__ import annotations

from maat.connectors.courtlistener import search_cases
from maat.connectors.seeds import seed_context

FOOTER = "Research aid only — not legal advice. Verify with a licensed attorney."

_ASK_LIMIT = 5


def _case_label(case: dict) -> str:
    """One-line case description built purely from API-returned metadata."""
    name = case.get("caseName") or "Untitled case"
    court = case.get("court") or "court unknown"
    date = case.get("dateFiled") or "date unknown"
    citations = case.get("citation") or []
    cite_str = f" ({', '.join(citations)})" if citations else ""
    return f"{name}{cite_str} — {court}, filed {date}"


def _case_source_line(case: dict) -> str:
    """Numbered Sources entry with a verifiable link back to CourtListener."""
    url = case.get("absolute_url") or ""
    link = f"https://www.courtlistener.com{url}" if url else "URL not returned"
    status = case.get("status") or "status unknown"
    return f"{_case_label(case)} [{status}] — {link}"


def ask_mode(question: str, sources: str = "all") -> str:
    """Answer a legal question in plain English from live sources.

    Structure: short answer, key findings, seed sources, a numbered
    Sources section with inline citations, then the research-aid footer.
    Every citation is drawn from live API results; nothing is invented.
    """
    lines: list[str] = [f"Question: {question}", ""]

    use_courtlistener = sources in ("all", "courtlistener")

    try:
        seed_text = seed_context(question, sources)
    except Exception as exc:  # seeds must never crash the answer
        seed_text = f"(seed sources unavailable: {exc})"

    cases: list[dict] = []
    fetch_error: Exception | None = None
    if use_courtlistener:
        try:
            cases = search_cases(question, limit=_ASK_LIMIT)
        except Exception as exc:
            fetch_error = exc

    if fetch_error is not None:
        lines += [
            "Short answer: I can't answer right now — the live case-law "
            "lookup (CourtListener API) could not be reached, and I won't "
            "answer legal questions from nothing.",
            "",
            f"Lookup error: {type(fetch_error).__name__}: {fetch_error}",
            "",
            "Seed sources:",
            seed_text,
            "",
            FOOTER,
        ]
        return "\n".join(lines)

    if not cases:
        lines += [
            "Short answer: no CourtListener cases were returned for this "
            "question and source selection, so there is nothing verified "
            "to answer from.",
            "",
            "Seed sources:",
            seed_text,
            "",
            FOOTER,
        ]
        return "\n".join(lines)

    # --- Short answer + key findings, grounded in what the API returned ---
    courts = sorted({c.get("court") or "unknown court" for c in cases})
    dates = [c.get("dateFiled") or "" for c in cases if c.get("dateFiled")]
    newest = max(dates) if dates else "unknown date"
    top = cases[0]
    lines += [
        "Short answer (plain English, from live case law):",
        f"  CourtListener returned {len(cases)} opinion(s) matching this "
        f"question, from {', '.join(courts)}, newest filed {newest}. "
        f"CourtListener's top-ranked match is [1] {_case_label(top)}. "
        "Use this as a starting map of the case law — read the full "
        "opinions before relying on any of it.",
        "",
        "Key findings (each grounded in a live API result):",
    ]
    for i, case in enumerate(cases, start=1):
        lines.append(
            f"  [{i}] {_case_label(case)} "
            f"[{case.get('status') or 'status unknown'}]"
        )
    lines.append("")

    lines += ["Seed sources:", seed_text, ""]
    lines += ["Sources (every entry is a live CourtListener result):"]
    for i, case in enumerate(cases, start=1):
        lines.append(f"  [{i}] {_case_source_line(case)}")
    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)
