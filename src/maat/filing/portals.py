"""E-filing portal registry.

Each portal declares two honest capabilities:

- efile: "api" — the tool can submit documents non-interactively through a
         documented API (none of the seeded portals qualify today).
         "interactive" — filing happens in the portal's own web UI by the
         human; the tool prepares the packet and prints exact instructions.
- payment: "portal-collects" — the portal takes the filing fee during
         submission (the normal Tyler/Odyssey + CM/ECF shape). The tool
         passes the filer's stored payment reference, shows the exact
         verified fee, and holds at GATE 2 for confirmation.
         "portal-interaction-required" — payment cannot be completed
         non-interactively. The tool MUST say so plainly instead of
         pretending a charge happened.

If a portal cannot do something, the code says so. Faking a submission or a
charge is a worse failure mode than admitting the limit.
"""

from __future__ import annotations

PORTALS: dict[str, dict] = {
    "in-odyssey": {
        "name": "Indiana Odyssey e-filing (Tyler Technologies)",
        "portal_url": "https://www.in.gov/judiciary/e-filing/",
        "efile": "interactive",
        "payment": "portal-interaction-required",
        "notes": (
            "Indiana's statewide e-filing runs on Tyler/Odyssey. Fees are "
            "collected inside the portal during submission; the portal "
            "exposes no non-interactive filing or payment API to filers. "
            "Prepare the packet here, then file and pay in the portal."
        ),
    },
    "insd-cmecf": {
        "name": "U.S. District Court, Southern District of Indiana — CM/ECF",
        "portal_url": "https://www.insd.uscourts.gov/",
        "efile": "interactive",
        "payment": "portal-interaction-required",
        "notes": (
            "CM/ECF case opening collects the $405 civil filing fee via "
            "Pay.gov inside the portal. No non-interactive submission or "
            "payment path is available to filers."
        ),
    },
    "innd-cmecf": {
        "name": "U.S. District Court, Northern District of Indiana — CM/ECF",
        "portal_url": "https://www.innd.uscourts.gov/",
        "efile": "interactive",
        "payment": "portal-interaction-required",
        "notes": (
            "CM/ECF filing with Pay.gov fee collection inside the portal. "
            "No non-interactive submission or payment path is available."
        ),
    },
}


def get_portal(court_id: str | None) -> dict:
    """Return the portal record for a court_id, or a generic interactive
    record when the court is not in the registry."""
    if court_id and court_id in PORTALS:
        return PORTALS[court_id]
    return {
        "name": court_id or "unspecified court",
        "portal_url": "",
        "efile": "interactive",
        "payment": "portal-interaction-required",
        "notes": (
            "This court is not in the portal registry. Filing and fee "
            "payment happen in the court's own portal or at the clerk's "
            "window — the tool prepares the packet; the human files."
        ),
    }


def register_portal(court_id: str, record: dict) -> None:
    """Contribution hook for adding a portal (e.g. a future API-capable one).

    record must include: name, portal_url, efile ("api"|"interactive"),
    payment ("portal-collects"|"portal-interaction-required"), notes.
    """
    required = {"name", "portal_url", "efile", "payment", "notes"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"Portal record missing fields: {sorted(missing)}")
    if record["efile"] not in ("api", "interactive"):
        raise ValueError("efile must be 'api' or 'interactive'")
    if record["payment"] not in ("portal-collects", "portal-interaction-required"):
        raise ValueError("payment must be 'portal-collects' or 'portal-interaction-required'")
    PORTALS[court_id] = record
