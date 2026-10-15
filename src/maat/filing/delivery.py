"""Delivery-confirmation options.

Three mechanisms, all honest about what they prove:

1. Email send-receipt request — headers the filer can attach to the
   packet email asking the recipient's mail server/client for a delivery
   or read receipt (the recipient can decline; a receipt is evidence of
   delivery, not of the recipient's agreement).
2. Certified-mail / return-receipt cover letter — printable instructions
   for USPS Certified Mail with Return Receipt (green card), the paper
   trail courts recognize for proof of mailing/delivery.
3. JSONL tracking log — append-only record of what was sent, when, and
   how. One line per event; machine-readable for later audit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def email_receipt_headers() -> dict:
    """Headers requesting delivery + read receipts on the packet email.

    Add these to the outgoing message. Note: compliance is voluntary on the
    recipient's side — a missing receipt proves nothing by itself.
    """
    return {
        "Disposition-Notification-To": "filer",  # read receipt request (RFC 3798)
        "Return-Receipt-To": "filer",  # delivery receipt request (RFC 2298)
        "X-Confirm-Reading-To": "filer",
    }


def certified_mail_cover_letter(
    *,
    sender_name: str,
    sender_address: str,
    recipient_name: str,
    recipient_address: str,
    document_title: str,
    tracking_number: str = "",
) -> str:
    """Printable USPS Certified Mail + Return Receipt cover letter.

    Instructions reference real USPS products: Certified Mail (proof of
    mailing), Return Receipt / "green card" (proof of delivery). The filer
    buys postage at the post office or via USPS.com Click-N-Ship; the tool
    never buys postage.
    """
    track_line = tracking_number or "[TRACKING NUMBER — fill in from USPS receipt]"
    return f"""CERTIFIED MAIL — RETURN RECEIPT REQUESTED
Tracking: {track_line}

FROM:
{sender_name}
{sender_address}

TO:
{recipient_name}
{recipient_address}

RE: {document_title}

Enclosed please find the above-referenced document(s).

MAILING INSTRUCTIONS (USPS):
1. Bring this letter and its enclosures to any U.S. Post Office, or prepare
   the label at usps.com (Click-N-Ship) and schedule a pickup.
2. Send via USPS Certified Mail (provides proof of mailing and a tracking
   number). Add USPS Return Receipt service — the "green card" (PS Form 3811)
   — for proof of delivery with the recipient's signature.
3. Keep the USPS mailing receipt and the tracking number with your case file.
   Track delivery at usps.com or by texting the tracking number to 28777.
4. When the green Return Receipt card comes back, staple it to your copy of
   what you mailed and file it with your proof of service.

The tool does not buy postage and does not mail anything. Mailing is a
human step — this letter just makes the paper trail easy to do right.
"""


def tracking_log(log_path: str | Path, event: str, **details) -> dict:
    """Append one event to the JSONL tracking log. Returns the record."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def read_tracking_log(log_path: str | Path) -> list[dict]:
    """Read back the tracking log as a list of records."""
    path = Path(log_path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records
