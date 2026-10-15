"""Per-jurisdiction filing-fee tables.

HARD RULE: never invent a fee. An entry carries an amount ONLY when it was
verified against an official court source (court website, court clerk fee
schedule, or statute) with the source URL returning HTTP 200 at verification
time. Everything else gets amount_cents=None and verified=False.

Contribution pattern (for adding a fee):
    1. Find the fee on an official court source (a .gov / court domain, or
       the controlling statute). County clerk pages on .gov domains count;
       third-party legal blogs do NOT.
    2. Confirm the URL returns HTTP 200 and note the effective date shown on
       the source.
    3. Add the entry with verified=True, amount_cents as an integer, and the
       source_url + a notes string quoting what the source says.
    4. If you cannot verify, add the entry anyway with amount_cents=None and
       verified=False so the gap is visible — a visible gap beats an
       invented number.

Fees change (usually July 1 in Indiana). Re-verify annually; stale verified
entries are worse than unverified ones.
"""

from __future__ import annotations

# Verified 2026-10-15. Official source, HTTP 200 confirmed:
# Indiana State Board of Accounts, "Filing Fees by Case Type Collected by
# the Clerk" (July 1, 2025):
#   http://secure.in.gov/sboa/files/2025-Court-Costs-and-Fees-by-Case-Type.pdf
_SBOA_2025 = "http://secure.in.gov/sboa/files/2025-Court-Costs-and-Fees-by-Case-Type.pdf"

# Verified 2026-10-15. Official source, HTTP 200 confirmed:
# U.S. District Court, Southern District of Indiana — Electronic Civil Case
# Opening page: "The filing of new civil complaints and notices of removal
# via CM/ECF includes electronic payment of the $405 filing fee via Pay.gov."
_INSD_CASE_OPENING = "https://www.insd.uscourts.gov/node/281"

FEE_TABLE: list[dict] = [
    {
        "jurisdiction": "Indiana",
        "court": "Indiana trial courts (circuit / superior / city / town)",
        "filing_type": "Civil action filing fee",
        "amount_cents": 15700,
        "verified": True,
        "source_url": _SBOA_2025,
        "notes": "SBOA schedule (effective July 1, 2025): 'Total Civil Filing Fee $157.00' ($185.00 with $28 sheriff service of process).",
    },
    {
        "jurisdiction": "Indiana",
        "court": "Indiana trial courts (circuit / superior / city / town)",
        "filing_type": "Small claims filing fee",
        "amount_cents": 8700,
        "verified": True,
        "source_url": _SBOA_2025,
        "notes": "SBOA schedule (effective July 1, 2025): 'Total Small Claims Filing Fees $87.00' ($115.00 with $28 sheriff service of process).",
    },
    {
        "jurisdiction": "Indiana",
        "court": "Indiana trial courts (circuit / superior / city / town)",
        "filing_type": "Probate filing fee",
        "amount_cents": 17700,
        "verified": True,
        "source_url": _SBOA_2025,
        "notes": "SBOA schedule (effective July 1, 2025): 'Total Probate Filing Fees $177.00'.",
    },
    {
        "jurisdiction": "Indiana",
        "court": "Indiana trial courts (circuit / superior / city / town)",
        "filing_type": "Infraction / ordinance violation filing fee",
        "amount_cents": 13900,
        "verified": True,
        "source_url": _SBOA_2025,
        "notes": "SBOA schedule (effective July 1, 2025): 'Total Infraction/Ordinance Violations Filing Fees $139.00'.",
    },
    {
        "jurisdiction": "Indiana",
        "court": "U.S. District Court, Southern District of Indiana",
        "filing_type": "Civil action (complaint or notice of removal)",
        "amount_cents": 40500,
        "verified": True,
        "source_url": _INSD_CASE_OPENING,
        "notes": "Court's official electronic case-opening page: $405 filing fee via Pay.gov (28 U.S.C. 1914(a) $350 + $55 administrative fee).",
    },
    # --- Unverified stubs: real gaps, not guesses. amount None + verified False.
    {
        "jurisdiction": "Indiana",
        "court": "Clerk of the Indiana Appellate Courts (Court of Appeals / Supreme Court)",
        "filing_type": "Appeal docketing fee",
        "amount_cents": None,
        "verified": False,
        "source_url": "https://www.in.gov/judiciary/appeals/",
        "notes": "UNVERIFIED — confirm the current docketing fee with the Clerk of the Indiana Appellate Courts before relying on any number.",
    },
    {
        "jurisdiction": "Indiana",
        "court": "U.S. District Court, Northern District of Indiana",
        "filing_type": "Civil action (complaint or notice of removal)",
        "amount_cents": None,
        "verified": False,
        "source_url": "https://www.innd.uscourts.gov/",
        "notes": "UNVERIFIED — confirm the current civil filing fee on the court's official fee schedule before relying on any number.",
    },
    {
        "jurisdiction": "Indiana",
        "court": "U.S. Bankruptcy Court, Southern District of Indiana",
        "filing_type": "Chapter 7 petition filing fee",
        "amount_cents": None,
        "verified": False,
        "source_url": "https://www.insb.uscourts.gov/",
        "notes": "UNVERIFIED — confirm the current petition fee on the bankruptcy court's official fee schedule before relying on any number.",
    },
]


def lookup_fee(jurisdiction: str, court: str = "", filing_type: str = "") -> dict | None:
    """Find the best-matching fee entry (case-insensitive substring match).

    Returns the entry dict or None when nothing matches. Unmatched courts
    are a normal case — callers must handle None as 'fee unverified'.
    """
    j = (jurisdiction or "").lower()
    c = (court or "").lower()
    f = (filing_type or "").lower()
    for entry in FEE_TABLE:
        ej = entry["jurisdiction"].lower()
        if j and j not in ej and ej not in j:
            continue
        if c and c not in entry["court"].lower():
            continue
        if f and f not in entry["filing_type"].lower():
            continue
        return entry
    return None


def format_amount(amount_cents: int) -> str:
    return f"${amount_cents / 100:,.2f}"


def fee_line(jurisdiction: str, court: str = "", filing_type: str = "") -> str:
    """One-line upfront fee disclosure for the packet summary.

    Verified:  'Filing this in <jurisdiction> — <court> (<filing type>): $X (verified — <source>)'
    Unverified: 'Filing this in <jurisdiction> — <court> (<filing type>): fee unverified — check <source>'
    """
    return fee_line_for_entry(
        lookup_fee(jurisdiction, court, filing_type), jurisdiction, court, filing_type
    )


def fee_line_for_entry(
    entry: dict | None, jurisdiction: str, court: str = "", filing_type: str = ""
) -> str:
    """Same as fee_line but for an already-looked-up entry (e.g. found via
    a fallback court alias in the filing pipeline)."""
    label = f"{jurisdiction} — {court or 'unspecified court'}" + (
        f" ({filing_type})" if filing_type else ""
    )
    if entry and entry["verified"] and entry["amount_cents"] is not None:
        return (
            f"Filing this in {label}: {format_amount(entry['amount_cents'])} "
            f"(verified — {entry['source_url']})"
        )
    source = entry["source_url"] if entry else "the clerk of the target court"
    return f"Filing this in {label}: fee unverified — check {source}"
