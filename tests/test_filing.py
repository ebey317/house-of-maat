"""Tests for maat.filing: warning, fees, packet, delivery, emailer, credentials."""

import json
import os
import stat
from pathlib import Path

import pytest

from maat.filing.warning import (
    detect_fringe_theories,
    warning_cover_sheet,
    FRAMING,
)
from maat.filing import fees
from maat.filing.fees import lookup_fee, fee_line
from maat.filing.packet import assemble_packet
from maat.filing.delivery import (
    certified_mail_cover_letter,
    email_receipt_headers,
    tracking_log,
    read_tracking_log,
)
from maat.filing.emailer import send_packet, EmailerError
from maat.filing.portals import get_portal, PORTALS
from maat.filing.credentials import CredentialStore, CredentialError


# --------------------------------------------------------------------------
# warning.py
# --------------------------------------------------------------------------


def test_detect_fringe_keywords():
    hits = detect_fringe_theories(
        "I am a sovereign citizen and this is accepted for value, strawman account."
    )
    assert any("sovereign" in h for h in hits)
    assert any("strawman" in h for h in hits)
    assert any("accepted for value" in h for h in hits)


def test_detect_clean_text_no_hits():
    assert detect_fringe_theories("I was fired on September 22 without warning.") == []


def test_detect_all_caps_name_case_sensitive():
    hits = detect_fringe_theories("The account of JOHN HENRY DOE is at issue.")
    assert "all-caps name" in hits
    # Lowercase prose must NOT trip the all-caps heuristic.
    assert "all-caps name" not in detect_fringe_theories("John Henry Doe filed a motion.")


def test_warning_sheet_exact_framing():
    sheet = warning_cover_sheet(["sovereign citizen / sovereign"])
    # Lijah's directed framing — verbatim, neither discouraging nor encouraging.
    assert FRAMING in sheet
    assert "100% failure rate" in sheet
    assert "Signature: ______ Date: ______" in sheet


# --------------------------------------------------------------------------
# fees.py — no invented fees
# --------------------------------------------------------------------------


def test_verified_indiana_small_claims():
    e = lookup_fee("Indiana", "trial courts", "small claims")
    assert e is not None
    assert e["amount_cents"] == 8700
    assert e["verified"] is True
    assert e["source_url"].startswith("http")


def test_verified_indiana_civil():
    e = lookup_fee("Indiana", "trial courts", "civil action")
    assert e["amount_cents"] == 15700
    assert e["verified"] is True


def test_verified_southern_district_indiana():
    e = lookup_fee("Indiana", "Southern District of Indiana", "civil action")
    assert e["amount_cents"] == 40500
    assert e["verified"] is True


def test_all_verified_entries_have_source_and_amount():
    for e in fees.FEE_TABLE:
        assert e["source_url"], e
        if e["verified"]:
            assert isinstance(e["amount_cents"], int) and e["amount_cents"] > 0, e
        else:
            assert e["amount_cents"] is None, e  # never invent


def test_fee_line_verified_format():
    line = fee_line("Indiana", "Indiana trial courts", "Small claims filing fee")
    assert line.startswith("Filing this in Indiana")
    assert "$87.00" in line
    assert "(verified" in line


def test_fee_line_unverified_format():
    line = fee_line("Indiana", "Northern District of Indiana", "Civil action")
    assert "fee unverified" in line
    assert "check http" in line


def test_fee_line_unknown_court():
    line = fee_line("Indiana", "Some Unknown Court", "Filing")
    assert "fee unverified" in line


# --------------------------------------------------------------------------
# packet.py
# --------------------------------------------------------------------------


def _sample_template():
    return "# Motion Skeleton\n\n## Caption\n\nIN THE [COURT NAME]\n\n## Statement of Facts\n\n" + (
        "[Bullet or paragraph form facts, drawn from the user's evidence.]"
    )


def test_packet_writes_core_files(tmp_path):
    result = assemble_packet(
        template_text=_sample_template(),
        translated_evidence="1. Movant states that x happened.",
        output_path=tmp_path,
    )
    names = {Path(f).name for f in result["files"]}
    assert {"draft.md", "rule_check.md", "signature_page.md", "deadline_calendar.md"} <= names
    assert result["fringe"] is False
    assert not (tmp_path / "warning_cover_sheet.md").exists()


def test_packet_attaches_warning_sheet_on_fringe(tmp_path):
    result = assemble_packet(
        template_text=_sample_template(),
        translated_evidence="1. Movant states that x happened.",
        output_path=tmp_path,
        fringe_hits=["sovereign citizen / sovereign"],
    )
    assert result["fringe"] is True
    sheet = (tmp_path / "warning_cover_sheet.md").read_text()
    assert "100% failure rate" in sheet


def test_signature_page_never_signed(tmp_path):
    assemble_packet(
        template_text=_sample_template(),
        translated_evidence="1. Movant states that x.",
        output_path=tmp_path,
    )
    sig = (tmp_path / "signature_page.md").read_text()
    assert "UNSIGNED" in sig
    assert "The tool never signs" in sig


def test_draft_merges_template_and_evidence(tmp_path):
    assemble_packet(
        template_text=_sample_template(),
        translated_evidence="1. Movant states that x.",
        output_path=tmp_path,
    )
    draft = (tmp_path / "draft.md").read_text()
    assert "Movant states that x" in draft
    assert "[Bullet or paragraph form facts" not in draft  # placeholder replaced


def test_draft_inserts_allegations_not_duplicate_caption(tmp_path):
    from maat.translate import plain_english_to_legal

    translated = plain_english_to_legal("I was fired on September 22.")
    assemble_packet(
        template_text=_sample_template(),
        translated_evidence=translated,
        output_path=tmp_path,
    )
    draft = (tmp_path / "draft.md").read_text()
    # The scrivener's full document (with its own caption) must not be
    # pasted inside the template — only the numbered allegations.
    assert draft.count("IN THE [COURT NAME]") == 1
    assert "1. Movant states that" in draft


# --------------------------------------------------------------------------
# delivery.py
# --------------------------------------------------------------------------


def test_certified_mail_letter_has_usps_references():
    letter = certified_mail_cover_letter(
        sender_name="Jane Doe",
        sender_address="1 Main St, Indianapolis, IN 46218",
        recipient_name="Clerk",
        recipient_address="200 W Washington St, Indianapolis, IN 46204",
        document_title="Motion",
    )
    assert "USPS" in letter
    assert "Certified Mail" in letter
    assert "Return Receipt" in letter
    assert "green card" in letter


def test_email_receipt_headers():
    headers = email_receipt_headers()
    assert "Disposition-Notification-To" in headers


def test_tracking_log_jsonl(tmp_path):
    log = tmp_path / "tracking.jsonl"
    tracking_log(log, "packet_generated", output=str(tmp_path))
    tracking_log(log, "gate1_approved")
    records = read_tracking_log(log)
    assert [r["event"] for r in records] == ["packet_generated", "gate1_approved"]
    assert all("ts" in r for r in records)
    # File is valid JSONL.
    for line in log.read_text().splitlines():
        json.loads(line)


# --------------------------------------------------------------------------
# emailer.py — dry run only in tests
# --------------------------------------------------------------------------


def test_emailer_dry_run_sends_nothing(tmp_path):
    (tmp_path / "draft.md").write_text("draft")
    result = send_packet("filer@example.com", tmp_path, dry_run=True)
    assert result["sent"] is False
    assert result["dry_run"] is True
    assert result["attachments"] == ["draft.md"]
    assert "DRY RUN" in result["note"]


def test_emailer_live_without_config_raises(tmp_path, monkeypatch):
    (tmp_path / "draft.md").write_text("draft")
    for var in ["MAAT_SMTP_HOST", "MAAT_SMTP_PORT", "MAAT_SMTP_USER",
                "MAAT_SMTP_PASS", "MAAT_SMTP_FROM"]:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(EmailerError):
        send_packet("filer@example.com", tmp_path, dry_run=False)


# --------------------------------------------------------------------------
# portals.py — honest capability declarations
# --------------------------------------------------------------------------


def test_portals_mark_payment_honestly():
    for court_id, portal in PORTALS.items():
        assert portal["payment"] in ("portal-collects", "portal-interaction-required"), court_id
        assert portal["efile"] in ("api", "interactive"), court_id
    # The seeded Indiana portals require portal interaction — no faked charges.
    assert PORTALS["in-odyssey"]["payment"] == "portal-interaction-required"


def test_unknown_court_gets_honest_default():
    portal = get_portal("no-such-court")
    assert portal["payment"] == "portal-interaction-required"
    assert portal["efile"] == "interactive"


# --------------------------------------------------------------------------
# file_mode — the seamless flow
# --------------------------------------------------------------------------

from maat.modes.file import file_mode  # noqa: E402


def _evidence_dir(tmp_path, files):
    d = tmp_path / "evidence"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text)
    return d


def _isolate_store(monkeypatch, tmp_path):
    """Point the credential store at a tmp dir so tests never touch the real one."""
    from cryptography.fernet import Fernet

    monkeypatch.setenv("MAAT_CREDENTIALS_BACKEND", "file")
    monkeypatch.setenv("MAAT_CREDENTIALS_DIR", str(tmp_path / "credstore"))
    monkeypatch.setenv("MAAT_CREDENTIALS_KEY", Fernet.generate_key().decode())


def test_file_mode_packet_only(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "Um, I was fired on September 22, basically without warning."})
    out = tmp_path / "packet"
    summary = file_mode(
        "motion-skeleton", str(ev), str(out),
        check_citations=False, dry_run=True,
    )
    assert (out / "draft.md").exists()
    assert (out / "rule_check.md").exists()
    assert (out / "signature_page.md").exists()
    assert (out / "deadline_calendar.md").exists()
    assert "Filing this in Indiana" in summary
    assert "Movant states that" in (out / "draft.md").read_text()


def test_file_mode_fringe_attaches_warning(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I am a sovereign citizen, this is accepted for value."})
    out = tmp_path / "packet"
    summary = file_mode("motion-skeleton", str(ev), str(out), check_citations=False)
    assert (out / "warning_cover_sheet.md").exists()
    assert "warning_cover_sheet.md" in summary


def test_file_mode_no_fringe_false_positive_from_caption(tmp_path, monkeypatch):
    # The draft's own caption ("IN THE [COURT NAME]") must not trip the
    # all-caps heuristic — detection runs on raw evidence only.
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired on September 22 without warning."})
    out = tmp_path / "packet"
    summary = file_mode("motion-skeleton", str(ev), str(out),
                        court_id="in-odyssey", check_citations=False)
    assert not (out / "warning_cover_sheet.md").exists()
    assert "Fringe-theory markers: none" in summary
    # motion-skeleton maps to the verified Indiana civil-action fee.
    assert "$157.00" in summary and "(verified" in summary


def _approver(prompt_text):
    if "GATE 1" in prompt_text:
        return "approve"
    if "GATE 2" in prompt_text:
        return "yes"
    return ""


def test_file_mode_full_flow_dry_run(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired on September 22 without warning."})
    out = tmp_path / "packet"
    summary = file_mode(
        "motion-skeleton", str(ev), str(out),
        submit=True, pay=True, court_id="in-odyssey",
        filer_email="filer@example.com",
        prompt=_approver, dry_run=True, check_citations=False,
    )
    assert "DRYRUN-EFILE-" in summary          # simulated e-file, never faked as real
    assert "Confirmation number" in summary
    assert "GATE 2" in summary or "Payment:" in summary
    assert "Nothing was charged by this tool" in summary  # honest payment handling
    assert "DRY RUN — not actually sent" in summary
    assert "Filing this in Indiana" in summary  # upfront fee line
    assert "maat creds setup" in summary
    log_records = read_tracking_log(out / "tracking.jsonl")
    events = [r["event"] for r in log_records]
    for expected in ["packet_generated", "gate1_prompted", "gate1_approved",
                     "efile_simulated", "gate2_prompted", "gate2_confirmed",
                     "payment_portal_interaction_required", "packet_emailed",
                     "flow_complete"]:
        assert expected in events, events


def test_file_mode_gate1_denied_aborts(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired."})
    out = tmp_path / "packet"
    summary = file_mode(
        "motion-skeleton", str(ev), str(out),
        submit=True, pay=True, court_id="in-odyssey",
        prompt=lambda t: "no", dry_run=True, check_citations=False,
    )
    assert "not approved" in summary
    assert "DRYRUN-EFILE-" not in summary
    events = [r["event"] for r in read_tracking_log(out / "tracking.jsonl")]
    assert "gate1_denied" in events


def test_file_mode_gate2_denied_no_charge(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired."})
    out = tmp_path / "packet"

    def picky(prompt_text):
        return "approve" if "GATE 1" in prompt_text else "no"

    summary = file_mode(
        "motion-skeleton", str(ev), str(out),
        submit=True, pay=True, court_id="in-odyssey",
        prompt=picky, dry_run=True, check_citations=False,
    )
    assert "no payment made" in summary
    events = [r["event"] for r in read_tracking_log(out / "tracking.jsonl")]
    assert "gate2_denied" in events


def test_file_mode_live_interactive_portal_is_honest(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired."})
    out = tmp_path / "packet"
    summary = file_mode(
        "motion-skeleton", str(ev), str(out),
        submit=True, pay=False, court_id="in-odyssey",
        prompt=lambda t: "approve", dry_run=False, check_citations=False,
    )
    # Live + interactive-only portal: honest "file it yourself", no fake confirmation.
    assert "Nothing was submitted by the tool" in summary
    assert "Confirmation number" not in summary


def test_file_mode_credentials_note_names_court(tmp_path, monkeypatch):
    _isolate_store(monkeypatch, tmp_path)
    store = CredentialStore(store_dir=tmp_path / "credstore", backend="file")
    store.set_efile("in-odyssey", username="testuser", secret="fakepass")
    # Point file_mode at the same tmp store via env.
    monkeypatch.setenv("MAAT_CREDENTIALS_DIR", str(tmp_path / "credstore"))
    monkeypatch.setenv("MAAT_CREDENTIALS_BACKEND", "file")
    ev = _evidence_dir(tmp_path, {"notes.txt": "I was fired."})
    out = tmp_path / "packet"
    summary = file_mode("motion-skeleton", str(ev), str(out), court_id="in-odyssey",
                        check_citations=False)
    assert "E-file account on file for 'in-odyssey' (username: testuser)" in summary
