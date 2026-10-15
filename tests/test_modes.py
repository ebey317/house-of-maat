"""Live tests for the ask and research modes.

These hit the real CourtListener API, so they verify structure and honest
grounding — not specific case names (search results may shift over time).
"""

from maat.modes.ask import ask_mode, FOOTER as ASK_FOOTER
from maat.modes.research import research_mode, FOOTER as RESEARCH_FOOTER

ASK_Q = "what is adverse possession in Indiana?"
RESEARCH_T = "tenant retaliation security deposit Indiana"


def test_ask_returns_sources_section_and_footer():
    ans = ask_mode(ASK_Q)
    assert "Sources" in ans
    assert "[1]" in ans
    assert ASK_FOOTER in ans


def test_ask_sources_are_verifiable_live_results():
    """Every numbered source must carry a real CourtListener link — provenance,
    not invented citations."""
    ans = ask_mode(ASK_Q)
    src = ans.split("Sources", 1)[1]
    assert "courtlistener.com" in src
    assert "filed" in src  # dates come from live metadata


def test_ask_handles_unreachable_api_honestly():
    """Simulate an unreachable API: answer must say so, not invent content."""
    import maat.modes.ask as ask_mod

    real_search = ask_mod.search_cases

    def boom(*a, **k):
        raise ConnectionError("simulated outage")

    ask_mod.search_cases = boom
    try:
        ans = ask_mode(ASK_Q)
    finally:
        ask_mod.search_cases = real_search
    assert "could not be reached" in ans
    assert ASK_FOOTER in ans


def test_research_returns_three_ranked_with_why():
    out = research_mode(RESEARCH_T)
    assert "Candidates found:" in out
    assert out.count("Why this case:") == 3
    assert "1." in out and "3." in out


def test_research_why_lines_are_metadata_grounded():
    """Why-lines may only cite returned metadata: court level, status,
    filing date, opinion type, score — never invented relevance."""
    out = research_mode(RESEARCH_T)
    why_lines = [l for l in out.splitlines() if l.strip().startswith("Why this case:")]
    assert len(why_lines) == 3
    for line in why_lines:
        assert "score" in line  # transparent scoring shown
        assert "matched the search terms" in line


def test_research_footer():
    out = research_mode(RESEARCH_T)
    assert RESEARCH_FOOTER in out


def test_research_handles_unreachable_api_honestly():
    import maat.modes.research as res_mod

    real_search = res_mod.search_cases

    def boom(*a, **k):
        raise ConnectionError("simulated outage")

    res_mod.search_cases = boom
    try:
        out = research_mode(RESEARCH_T)
    finally:
        res_mod.search_cases = real_search
    assert "Candidates found: 0" in out
    assert RESEARCH_FOOTER in out
