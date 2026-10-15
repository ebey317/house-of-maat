"""Email the finished packet to the filer.

Configuration is env-only (never hardcoded):

    MAAT_SMTP_HOST   SMTP server hostname
    MAAT_SMTP_PORT   SMTP port (default 587)
    MAAT_SMTP_USER   SMTP username
    MAAT_SMTP_PASS   SMTP password / app password
    MAAT_SMTP_FROM   From: address

dry_run=True is the default: the function logs exactly what WOULD be sent
(recipients, subject, attachments) and sends nothing. Tests must use the
dry run — no real sends in tests, ever.
"""

from __future__ import annotations

import os
from email.message import EmailMessage
from pathlib import Path

from .delivery import email_receipt_headers


class EmailerError(Exception):
    """Raised when email cannot be sent (missing config, SMTP failure)."""


def _smtp_config() -> dict:
    host = os.environ.get("MAAT_SMTP_HOST")
    if not host:
        raise EmailerError(
            "MAAT_SMTP_HOST is not set. Set MAAT_SMTP_HOST/PORT/USER/PASS/FROM "
            "to enable sending, or keep dry_run=True."
        )
    return {
        "host": host,
        "port": int(os.environ.get("MAAT_SMTP_PORT", "587")),
        "user": os.environ.get("MAAT_SMTP_USER", ""),
        "password": os.environ.get("MAAT_SMTP_PASS", ""),
        "from": os.environ.get("MAAT_SMTP_FROM", os.environ.get("MAAT_SMTP_USER", "")),
    }


def _packet_files(packet_dir: str | Path) -> list[Path]:
    d = Path(packet_dir)
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix == ".md")


def send_packet(
    to_address: str,
    packet_dir: str | Path,
    *,
    subject: str | None = None,
    dry_run: bool = True,
    cc: list[str] | None = None,
) -> dict:
    """Email the packet files to the filer.

    Returns a summary dict. With dry_run=True nothing is sent; the summary
    describes what would have been sent.
    """
    files = _packet_files(packet_dir)
    subject = subject or "Your House of Ma'at filing packet (review before signing)"
    body = (
        "Attached is your filing packet.\n\n"
        "HUMAN STEPS — the tool does not do these:\n"
        "1. Review draft.md against rule_check.md.\n"
        "2. Fill every [BRACKETED PLACEHOLDER].\n"
        "3. Sign the signature page yourself.\n"
        "4. File in the court's portal (or at the clerk's window) and pay the fee.\n\n"
        "This email is a copy for your records. Nothing has been filed."
    )

    summary = {
        "sent": False,
        "dry_run": dry_run,
        "to": to_address,
        "cc": cc or [],
        "subject": subject,
        "attachments": [p.name for p in files],
        "receipt_headers": email_receipt_headers(),
    }

    if dry_run:
        summary["note"] = (
            f"DRY RUN — would email {len(files)} file(s) to {to_address}; "
            "no message was sent."
        )
        return summary

    cfg = _smtp_config()
    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to_address
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    for header, value in email_receipt_headers().items():
        # Address the receipt requests to the sender, not the literal "filer".
        msg[header] = cfg["from"] if value == "filer" else value
    msg.set_content(body)
    for p in files:
        msg.add_attachment(
            p.read_bytes(),
            maintype="text",
            subtype="markdown",
            filename=p.name,
        )

    import smtplib

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
            smtp.starttls()
            if cfg["user"]:
                smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailerError(f"SMTP send failed: {exc}") from exc

    summary["sent"] = True
    summary["note"] = f"Emailed {len(files)} file(s) to {to_address}."
    return summary
