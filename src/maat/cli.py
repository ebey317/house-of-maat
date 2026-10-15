"""House of Ma'at command-line interface.

Commands:
    maat file --type <t> --evidence <dir> [--output <dir>] [--court <id>]
              [--submit] [--pay] [--live] [--filer-email <addr>]
        One seamless flow: packet -> GATE 1 approval -> e-file ->
        GATE 2 fee confirmation -> emailed copy + tracking log.
        Default is --dry-run (full pipeline simulated, nothing real).

    maat creds setup --court <court-id>
        Store e-file credentials for a court (secure entry, encrypted).
    maat creds setup-payment --id <method-id>
        Store a payment method REFERENCE (portal token / masked id — never
        a card number).
    maat creds list
        Show configured courts and payment methods (usernames/labels only).

Principles: human signs, human files. The tool never signs, never files
without explicit GATE 1 approval, never charges without GATE 2 confirmation.
"""

from __future__ import annotations

import click

from maat.modes.file import file_mode
from maat.filing.credentials import CredentialStore, CredentialError


@click.group()
def cli():
    """House of Ma'at — legal research and filing assistant."""


@cli.command("file")
@click.option("--type", "case_type", required=True, help="Template/case type, e.g. motion-skeleton.")
@click.option("--evidence", required=True, help="Folder of .txt/.md evidence files.")
@click.option("--output", default="./packet", help="Packet output folder.")
@click.option("--court", "court_id", default=None, help="Court id, e.g. in-odyssey.")
@click.option("--jurisdiction", default="Indiana", help="Fee-table jurisdiction.")
@click.option("--filing-type", default=None, help="Fee-table filing type.")
@click.option("--filer-email", default=None, help="Email the packet copy here.")
@click.option("--submit", is_flag=True, help="Run the e-file flow after packet generation.")
@click.option("--pay", is_flag=True, help="Include the fee-payment step (needs --submit).")
@click.option("--dry-run/--live", default=True, help="Simulate submit/pay (default) vs real.")
@click.option("--no-citation-check", is_flag=True, help="Skip the CourtListener citation check.")
def file_cmd(case_type, evidence, output, court_id, jurisdiction, filing_type,
             filer_email, submit, pay, dry_run, no_citation_check):
    """Generate a filing packet, optionally e-file it and pay the fee."""
    if pay and not submit:
        raise click.UsageError("--pay requires --submit.")
    if dry_run:
        click.echo("DRY RUN — full pipeline simulated: no real submits, no real charges.")
    summary = file_mode(
        case_type,
        evidence,
        output,
        submit=submit,
        pay=pay,
        court_id=court_id,
        jurisdiction=jurisdiction,
        filing_type=filing_type,
        filer_email=filer_email,
        prompt=lambda text: click.prompt(text, default="", show_default=False),
        dry_run=dry_run,
        check_citations=not no_citation_check,
    )
    click.echo(summary)


@cli.group("creds")
def creds():
    """Manage encrypted e-file credentials and payment references."""


@creds.command("setup")
@click.option("--court", "court_id", required=True, help="Court id, e.g. in-odyssey.")
def creds_setup(court_id):
    """Store e-file credentials for a court (secure entry, encrypted)."""
    store = CredentialStore()
    click.echo(f"Storing e-file credentials for '{court_id}' (backend: {store.backend_name}).")
    click.echo("Values are entered securely (no echo) and never displayed.")
    try:
        store.set_efile(court_id)
    except CredentialError as exc:
        raise click.ClickException(str(exc))
    click.echo(f"Stored. At e-file time the pipeline will load them automatically for '{court_id}'.")


@creds.command("setup-payment")
@click.option("--id", "method_id", required=True, help="Payment method id, e.g. main-card.")
def creds_setup_payment(method_id):
    """Store a payment method REFERENCE (portal token / masked id — never a card number)."""
    store = CredentialStore()
    click.echo(f"Storing payment reference '{method_id}' (backend: {store.backend_name}).")
    click.echo("Enter a portal token or masked identifier. Full card numbers are refused.")
    try:
        store.set_payment(method_id)
    except CredentialError as exc:
        raise click.ClickException(str(exc))
    click.echo("Stored. GATE 2 will always confirm before anything is charged.")


@creds.command("list")
def creds_list():
    """Show configured courts and payment methods (usernames/labels only, no secrets)."""
    store = CredentialStore()
    click.echo(f"Backend: {store.backend_name}")
    click.echo("E-file accounts:")
    for entry in store.list_efile():
        click.echo(f"  - {entry}")
    click.echo("Payment methods:")
    for entry in store.list_payment():
        click.echo(f"  - {entry}")


def main():
    cli()
