"""File mode: the seamless filing pipeline.

One flow, no separate steps:

    maat file --type <t> --evidence <dir> [--output <dir>] [--court <id>]
              [--submit] [--pay] [--live]

    1. Generate the filing packet (draft + rule check + signature page +
       deadline calendar + warning sheet when fringe keywords are found).
    2. GATE 1 — the user reviews the packet and explicitly approves
       ("approve"/"yes"). Nothing files without this.
    3. E-file using the stored e-file credentials for the target court.
       (All currently registered portals are interactive-only, so the tool
       prepares the packet and hands the human exact portal instructions —
       it never pretends to have submitted.)
    4. --pay: show the EXACT fee, then GATE 2 — explicit confirmation before
       any money moves. Tyler/Odyssey-style portals collect the fee
       themselves during submission; the tool passes the filer's stored
       payment reference and never runs a direct card charge (no PCI scope).
       Portals that cannot complete payment non-interactively are marked
       "payment requires portal interaction" — honestly, not faked.
    5. Return the e-file confirmation (or honest status), payment receipt
       (or honest status), and an emailed copy of the packet. Everything is
       logged to the JSONL tracking log.

    --live runs the real (non-simulated) path; the default is --dry-run,
    which exercises the entire pipeline including both gates with fake
    credentials/payment — no real submits, no real charges.

Human-signs / human-files: the tool never signs and never files without
the user's explicit GATE 1 approval.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from maat.templates.loader import load_template
from maat.translate import plain_english_to_legal
from maat.filing.warning import detect_fringe_theories
from maat.filing.packet import assemble_packet
from maat.filing.fees import lookup_fee, fee_line_for_entry, format_amount
from maat.filing.credentials import CredentialStore, CredentialError
from maat.filing.portals import get_portal
from maat.filing.delivery import tracking_log
from maat.filing.emailer import send_packet, EmailerError

try:
    from maat.connectors.courtlistener import analyze_citations
except Exception:  # connector missing or requests unavailable
    analyze_citations = None

try:
    from maat.forms.fillable import fill_form  # noqa: F401  (kept for compat)
except Exception:
    fill_form = None

_APPROVALS = {"approve", "approved", "yes", "y"}


def _doc_type_for(case_type: str) -> str:
    ct = (case_type or "").lower()
    if "complaint" in ct:
        return "complaint"
    if "answer" in ct:
        return "answer"
    if "affidavit" in ct:
        return "affidavit"
    return "motion"


def _read_evidence(evidence_path: str | Path) -> tuple[str, list[str]]:
    """Read text evidence files (sorted). Returns (combined text, filenames)."""
    ev = Path(evidence_path)
    if not ev.exists():
        return "", []
    files = sorted(
        p for p in ev.iterdir()
        if p.is_file() and p.suffix.lower() in {".txt", ".md", ".text"}
    )
    parts, names = [], []
    for p in files:
        try:
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
            names.append(p.name)
        except OSError:
            continue
    return "\n\n".join(parts).strip(), names


def _court_label(court_id: str | None) -> str:
    if not court_id:
        return ""
    return get_portal(court_id)["name"]


def _filing_type_for(case_type: str) -> str:
    """Map a case_type/template name onto fee-table filing-type language."""
    ct = (case_type or "").lower()
    if "small" in ct and "claim" in ct:
        return "Small claims"
    if "probate" in ct:
        return "Probate"
    if "infraction" in ct or "ordinance" in ct:
        return "Infraction"
    return "Civil action"


def _find_fee(jurisdiction: str, court_id: str | None, filing_type: str | None):
    """Best-effort fee lookup: portal name, then generic trial-court match,
    then jurisdiction-only; each tried with the filing type and then without
    it. Returns the entry or None (unverified)."""
    candidates = [_court_label(court_id), "trial", ""]
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        for f in (filing_type or "", ""):
            entry = lookup_fee(jurisdiction, c, f)
            if entry:
                return entry
    return None


def _ask(prompt_fn, text: str) -> str:
    fn = prompt_fn or (lambda t: input(t + " "))
    try:
        return (fn(text) or "").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return ""


def file_mode(
    case_type: str,
    evidence_path: str,
    output_path: str,
    *,
    submit: bool = False,
    pay: bool = False,
    court_id: str | None = None,
    jurisdiction: str = "Indiana",
    filing_type: str | None = None,
    filer_email: str | None = None,
    prompt=None,
    dry_run: bool = True,
    check_citations: bool = True,
    log_path: str | Path | None = None,
) -> str:
    """Run the filing pipeline. Returns a human-readable summary.

    Args:
        case_type: template name (e.g. "motion-skeleton", "small-claims-complaint").
        evidence_path: folder of .txt/.md evidence files.
        output_path: folder the packet is written to.
        submit: run the e-file flow (default False — packet only).
        pay: include the fee-payment step (requires submit).
        court_id: portal/court identifier (e.g. "in-odyssey").
        jurisdiction: fee-table jurisdiction (default "Indiana").
        filing_type: fee-table filing type (defaults to case_type).
        filer_email: where to email the packet copy (None = skip email).
        prompt: callable(text) -> str for GATE 1 / GATE 2 (default: input()).
        dry_run: True (default) simulates submit/pay with fake confirmations.
        check_citations: run analyze_citations best-effort (default True).
        log_path: tracking-log path (default: <output_path>/tracking.jsonl).
    """
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)
    log = Path(log_path) if log_path else out / "tracking.jsonl"

    # 1. Packet generation -------------------------------------------------
    template_file = Path(load_template(case_type))
    template_text = template_file.read_text(encoding="utf-8", errors="replace")

    evidence_text, evidence_files = _read_evidence(evidence_path)
    doc_type = _doc_type_for(case_type)
    translated = plain_english_to_legal(evidence_text, doc_type=doc_type)

    # Fringe detection runs on the user's RAW evidence only — never on the
    # generated draft, whose own caption block ("IN THE [COURT NAME]") would
    # otherwise trip the all-caps heuristic.
    fringe_hits = detect_fringe_theories(evidence_text)

    if check_citations and analyze_citations is not None:
        try:
            report = analyze_citations(translated)
            if isinstance(report, dict) and report.get("errors") is False:
                citation_note = "CourtListener citation check ran; review any flagged citations."
            else:
                citation_note = f"CourtListener returned: {report}. Verify citations yourself."
        except Exception as exc:
            citation_note = (
                "Citation check unreachable "
                f"({type(exc).__name__}: {exc}). Verify every citation yourself before filing."
            )
    elif check_citations:
        citation_note = "Citation-check connector unavailable. Verify every citation yourself before filing."
    else:
        citation_note = "Citation check skipped by caller. Verify every citation yourself before filing."

    packet = assemble_packet(
        template_text=template_text,
        translated_evidence=translated,
        output_path=out,
        doc_type=doc_type,
        fringe_hits=fringe_hits,
        citation_note=citation_note,
    )
    tracking_log(log, "packet_generated",
                 case_type=case_type, output=str(out),
                 evidence_files=evidence_files,
                 fringe_detected=packet["fringe"],
                 fringe_markers=fringe_hits)

    # Fee line (upfront, always shown) --------------------------------------
    fee_ft = filing_type or _filing_type_for(case_type)
    fee_entry = _find_fee(jurisdiction, court_id, fee_ft)
    fee_court = _court_label(court_id) or court_id or ""
    line = fee_line_for_entry(fee_entry, jurisdiction, fee_court, fee_ft)
    if fee_entry and fee_entry["verified"]:
        fee_display = format_amount(fee_entry["amount_cents"])
        fee_status = f"verified ({fee_entry['source_url']})"
    else:
        fee_display = "UNVERIFIED"
        src = fee_entry["source_url"] if fee_entry else "the clerk of the target court"
        fee_status = f"unverified — check {src}"

    # Credentials note ------------------------------------------------------
    try:
        store = CredentialStore()
        store_backend = store.backend_name
        if court_id and store.has_efile(court_id):
            cred = store.get_efile(court_id)
            cred_note = (
                f"E-file account on file for '{court_id}' "
                f"(username: {cred['username']}) — loaded automatically at e-file time."
            )
            creds_ready = True
        elif court_id:
            cred_note = (
                f"No e-file credentials configured for '{court_id}'. "
                f"Run: maat creds setup --court {court_id}"
            )
            creds_ready = False
        else:
            cred_note = "No target court given — no e-file credentials looked up."
            creds_ready = False
    except CredentialError as exc:
        cred_note = f"Credential store unavailable: {exc}"
        creds_ready = False
        store_backend = "unavailable"

    portal = get_portal(court_id)

    summary = [
        f"Case type: {case_type}  |  Evidence files: {len(evidence_files)}",
        f"Packet written to: {out}",
        *[f"  - {Path(f).name}" for f in packet["files"]],
        f"Fringe-theory markers: {', '.join(fringe_hits) if fringe_hits else 'none'}"
        + (" — warning_cover_sheet.md attached" if packet["fringe"] else ""),
        line,
        cred_note,
    ]

    if not submit:
        summary.append("Submit not requested — packet only. Review, sign, and file yourself.")
        tracking_log(log, "flow_complete", mode="packet-only", submitted=False)
        return "\n".join(summary)

    # 2. GATE 1 — explicit approval ----------------------------------------
    tracking_log(log, "gate1_prompted", court=court_id)
    answer = _ask(prompt, "GATE 1 — Review the packet above. Type 'approve' to authorize e-filing (anything else aborts):")
    if answer not in _APPROVALS:
        tracking_log(log, "gate1_denied", submitted=False)
        summary.append("GATE 1: not approved — nothing was filed, nothing was charged.")
        return "\n".join(summary)
    tracking_log(log, "gate1_approved", court=court_id)

    # 3. E-file --------------------------------------------------------------
    efile_status, confirmation = _efile_step(
        packet_files=packet["files"],
        court_id=court_id,
        portal=portal,
        creds_ready=creds_ready,
        dry_run=dry_run,
        log=log,
    )
    summary.append(f"E-file: {efile_status}")
    if confirmation:
        summary.append(f"Confirmation number: {confirmation}")

    # 4. Fee payment (same flow) ----------------------------------------------
    payment_status, receipt = None, None
    if pay:
        payment_status, receipt = _payment_step(
            fee_display=fee_display,
            fee_status=fee_status,
            portal=portal,
            court_id=court_id,
            dry_run=dry_run,
            prompt=prompt,
            log=log,
        )
        summary.append(f"Payment: {payment_status}")
        if receipt:
            summary.append(f"Payment receipt: {receipt}")
    else:
        tracking_log(log, "payment_skipped", reason="--pay not given")

    # 5. Emailed copy + log ----------------------------------------------------
    if filer_email:
        try:
            email_result = send_packet(filer_email, out, dry_run=dry_run)
            tracking_log(log, "packet_emailed",
                         to=filer_email, dry_run=dry_run,
                         sent=email_result["sent"],
                         attachments=email_result["attachments"])
            summary.append(
                f"Emailed packet copy to {filer_email} "
                f"({'DRY RUN — not actually sent' if dry_run else 'sent'})."
            )
        except EmailerError as exc:
            tracking_log(log, "packet_email_failed", error=str(exc))
            summary.append(f"Email failed: {exc}")
    else:
        summary.append("No filer email given — packet copy not emailed.")
        tracking_log(log, "packet_email_skipped", reason="no filer_email")

    tracking_log(log, "flow_complete", mode="submit", dry_run=dry_run,
                 efile_status=efile_status, payment_status=payment_status,
                 confirmation=confirmation, receipt=receipt)
    return "\n".join(summary)


def _efile_step(*, packet_files, court_id, portal, creds_ready, dry_run, log) -> tuple[str, str | None]:
    """E-file via the portal. Never fakes a submission."""
    name = portal["name"]
    if dry_run:
        confirmation = f"DRYRUN-EFILE-{uuid.uuid4().hex[:8].upper()}"
        status = (
            f"DRY RUN — simulated submission to {name} "
            f"(portal mode: {portal['efile']}). No documents were transmitted."
        )
        if not creds_ready and court_id:
            status += f" NOTE: no e-file credentials are stored for '{court_id}' — configure before a live run."
        tracking_log(log, "efile_simulated", court=court_id,
                     confirmation=confirmation, creds_ready=creds_ready)
        return status, confirmation

    # Live path. All registered portals are interactive-only: be honest.
    if portal["efile"] == "interactive":
        status = (
            f"{name} accepts filings through its own portal only "
            f"({portal['portal_url'] or 'see court website'}). The packet is ready "
            f"in the output folder — file it there yourself. "
            f"Nothing was submitted by the tool. {portal['notes']}"
        )
        tracking_log(log, "efile_interactive_only", court=court_id, submitted=False)
        return status, None

    # Future: a portal with a real non-interactive API would submit here,
    # using the stored credentials automatically. None are registered today.
    tracking_log(log, "efile_not_implemented", court=court_id)
    return (f"API submission for {name} is not implemented. Nothing was submitted.", None)


def _payment_step(*, fee_display, fee_status, portal, court_id, dry_run, prompt, log) -> tuple[str, str | None]:
    """GATE 2 + fee handling. Never fakes a charge."""
    name = portal["name"]
    tracking_log(log, "gate2_prompted", fee=fee_display, fee_status=fee_status)
    answer = _ask(
        prompt,
        f"GATE 2 — Filing fee: {fee_display} ({fee_status}). "
        f"Type 'yes' to confirm payment via {name} (anything else aborts):",
    )
    if answer not in _APPROVALS:
        tracking_log(log, "gate2_denied", charged=False)
        return "GATE 2: not confirmed — no payment made.", None
    tracking_log(log, "gate2_confirmed")

    if portal["payment"] == "portal-interaction-required":
        # Honest path: Tyler/Odyssey and CM/ECF collect the fee inside the
        # portal during submission. The tool never charges directly (no PCI
        # scope) and must not pretend it did.
        status = (
            f"Payment requires portal interaction — {name} collects the "
            f"{fee_display} fee inside its own portal during submission. "
            "Nothing was charged by this tool."
            + (" (Dry run: the fee display and confirmation above were simulated.)" if dry_run else "")
        )
        tracking_log(log, "payment_portal_interaction_required",
                     fee=fee_display, charged=False, dry_run=dry_run)
        return status, None

    # portal-collects via API (no registered portal qualifies today):
    if dry_run:
        receipt = f"DRYRUN-RCPT-{uuid.uuid4().hex[:8].upper()}"
        tracking_log(log, "payment_simulated", fee=fee_display, receipt=receipt)
        return (f"DRY RUN — simulated charge of {fee_display} via {name}. No money moved.", receipt)
    tracking_log(log, "payment_not_implemented", court=court_id)
    return (f"Non-interactive payment for {name} is not implemented. No money moved.", None)
