"""Research mode — scored candidate batches with transparent ranking.

Ranking signals, all derived from returned API metadata and printed with
every batch (no invented relevance claims):

  - court level: U.S. Supreme Court 100 > state supreme 90 > federal
    circuit 70 > state appellate 60 > federal district 40 > trial 30 >
    other/unknown 20
  - recency: filed >= 2020 +30, 2010-2019 +20, 2000-2009 +10
  - opinion type: signed lead opinion +10, multiple opinions +7,
    per curiam +5
  - status: published +10, unpublished -10
"""

from __future__ import annotations

from maat.connectors.courtlistener import search_cases

FOOTER = "Research aid only — not legal advice. Verify with a licensed attorney."

_RESEARCH_LIMIT = 15
_TOP_N = 3


def _court_level_score(court: str) -> tuple[int, str]:
    name = (court or "").lower()
    if "supreme court of the united states" in name or name.strip() in (
        "u.s. supreme court",
        "united states supreme court",
    ):
        return 100, "U.S. Supreme Court"
    if "supreme court" in name:
        return 90, "state supreme court"
    if "court of appeals" in name and "circuit" in name:
        return 70, "federal circuit court"
    if "court of appeals" in name or "appellate" in name:
        return 60, "state appellate court"
    if "district court" in name:
        return 40, "federal district court"
    if "superior" in name or "circuit court" in name or "trial" in name:
        return 30, "trial court"
    return 20, "other/unknown court"


def _recency_score(date_filed: str) -> tuple[int, str]:
    try:
        year = int((date_filed or "")[:4])
    except (ValueError, TypeError):
        return 0, "date unknown"
    if year >= 2020:
        return 30, f"filed {year} (recent)"
    if year >= 2010:
        return 20, f"filed {year}"
    if year >= 2000:
        return 10, f"filed {year}"
    return 0, f"filed {year} (older)"


def _opinion_signal(case: dict) -> tuple[int, str]:
    """Opinion-type proxy from the search result's opinions list."""
    opinions = case.get("opinions") or []
    if not opinions:
        return 0, "opinion type not reported"
    if any(op.get("per_curiam") for op in opinions):
        return 5, "per curiam opinion"
    if len(opinions) > 1:
        return 7, f"{len(opinions)} opinions on file (concurring/dissenting may be present)"
    return 10, "signed lead opinion"


def _status_score(status: str) -> tuple[int, str]:
    s = (status or "").lower()
    if s == "published":
        return 10, "published"
    if s == "unpublished":
        return -10, "unpublished"
    return 0, "status unknown"


def _score_case(case: dict) -> dict:
    court_pts, court_lbl = _court_level_score(case.get("court") or "")
    rec_pts, rec_lbl = _recency_score(case.get("dateFiled") or "")
    op_pts, op_lbl = _opinion_signal(case)
    st_pts, st_lbl = _status_score(case.get("status") or "")
    return {
        "total": court_pts + rec_pts + op_pts + st_pts,
        "court_pts": court_pts,
        "court_lbl": court_lbl,
        "rec_pts": rec_pts,
        "rec_lbl": rec_lbl,
        "op_pts": op_pts,
        "op_lbl": op_lbl,
        "st_pts": st_pts,
        "st_lbl": st_lbl,
    }


def _dedupe(cases: list[dict]) -> list[dict]:
    """Drop duplicate clusters (the search API can repeat the same case)."""
    seen: set = set()
    out: list[dict] = []
    for case in cases:
        key = (
            case.get("cluster_id")
            or case.get("absolute_url")
            or (case.get("caseName"), case.get("court"), case.get("dateFiled"))
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(case)
    return out


def research_mode(
    topic: str,
    jurisdiction: str = "",
    year_min: int | None = None,
    year_max: int | None = None,
) -> str:
    """Return a scored batch of candidates for a research topic.

    Fetches up to 15 candidates, dedupes, scores on transparent signals,
    and prints the top 3 with a one-line "why this case" grounded only in
    returned metadata.
    """
    lines: list[str] = [
        f"Topic: {topic}",
        f"Jurisdiction: {jurisdiction or 'all'}",
        f"Year range: {year_min or 'any'} - {year_max or 'any'}",
        "",
    ]

    try:
        raw = search_cases(
            topic,
            jurisdiction=jurisdiction,
            year_min=year_min,
            year_max=year_max,
            limit=_RESEARCH_LIMIT,
        )
    except Exception as exc:
        return "\n".join(
            lines
            + [
                "Candidates found: 0",
                "",
                "The live case-law lookup (CourtListener API) could not be "
                "reached, so no candidates could be ranked.",
                f"Lookup error: {type(exc).__name__}: {exc}",
                "",
                FOOTER,
            ]
        )

    candidates = _dedupe(raw)
    scored = sorted(
        ((_score_case(c), c) for c in candidates),
        key=lambda pair: (-pair[0]["total"], pair[1].get("caseName") or ""),
    )

    lines += [
        f"Candidates found: {len(candidates)} (from {len(raw)} raw results)",
        "",
        "Scoring signals (transparent, from returned metadata only):",
        "  court level: U.S. Supreme Court 100 > state supreme 90 > federal",
        "    circuit 70 > state appellate 60 > federal district 40 > trial 30",
        "    > other/unknown 20;",
        "  recency: filed >= 2020 +30, 2010-2019 +20, 2000-2009 +10;",
        "  opinion type: signed lead opinion +10, multiple opinions +7,",
        "    per curiam +5;",
        "  status: published +10, unpublished -10.",
        "",
    ]

    if not scored:
        lines += ["No candidates matched — nothing to rank.", "", FOOTER]
        return "\n".join(lines)

    top = scored[:_TOP_N]
    lines.append(f"Top {len(top)} ranked cases:")
    lines.append("")
    for rank, (score, case) in enumerate(top, start=1):
        name = case.get("caseName") or "Untitled case"
        url = case.get("absolute_url") or ""
        link = f"https://www.courtlistener.com{url}" if url else "URL not returned"
        court = case.get("court") or "court unknown"
        date = case.get("dateFiled") or "date unknown"
        why = (
            f"Why this case: {score['court_lbl']}; {score['st_lbl']}; "
            f"{score['rec_lbl']}; {score['op_lbl']} — matched the search "
            f"terms and ranked #{rank} of {len(scored)} on these signals "
            f"(score {score['total']})."
        )
        lines += [
            f"{rank}. {name}",
            f"   {court} — filed {date} [{score['st_lbl']}]",
            f"   score {score['total']} (court {score['court_pts']}, "
            f"recency {score['rec_pts']}, opinion {score['op_pts']}, "
            f"status {score['st_pts']})",
            f"   {why}",
            f"   {link}",
            "",
        ]

    lines.append(FOOTER)
    return "\n".join(lines)
