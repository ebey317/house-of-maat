# House of Ma'at

Open-source legal research and filing assistant. Named for Ma'at — truth,
balance, order, law, morality, justice — the oldest attested African
ethical-legal concept.

The House of Ma'at is not a law firm and does not give legal advice. It is a
tool that helps you research primary law, draft court documents, and prepare
filing packets that you sign and file yourself.

## Three modes

| Mode | What it does | Output |
|------|--------------|--------|
| `ask` | Answer legal questions in plain English with inline citations | explanation + primary sources |
| `research` | Find and rank cases on a topic | small batch of verified cases with "why this case" |
| `file` | Draft a motion, complaint, or answer from your evidence | filing packet (draft + rule check + signature page + deadline calendar) |

## Principles

- **Human signs.** The tool never signs a court document under your name.
- **Human files.** The tool preps the packet; you upload it to the court.
- **Cite before ship.** Every draft is checked against CourtListener's
  `analyze_citations` before delivery.
- **Fringe theories get the rejection record.** Sovereign-citizen,
  UCC-redemption, and strawman filings are allowed on your explicit request,
  but the tool inserts the controlling rejections and a Warning Cover Sheet.
- **No IRS content.** Tax-filing content is out of scope.

## Legal data spine

Tier 1 (deep, complete): US federal + Indiana
- CourtListener — case law + RECAP dockets
- GovInfo — U.S. Code, Statutes at Large, Federal Register
- Regulations.gov + eCFR — federal rulemaking
- Indiana — Doxpop, indianajudiciary.gov self-help forms, Indiana Rules of
  Trial Procedure and Small Claims Rules

Tier 2 (coverage via CourtListener): every other US state + their e-filing
portals (Odyssey / Tyler / iiCourt).

Tier 3 (international): EUR-Lex, Curia, HUDOC, legislation.gov.uk, WIPO Lex.

## Connectors

Connectors are optional. The core drafting and form-filling features work
without them; connectors only accelerate case-law lookup and citation
verification.

- CourtListener MCP server: `https://mcp.courtlistener.com/`
- CourtListener REST API: `https://www.courtlistener.com/api/rest/v4/`
- Community CourtListener++ MCP (GovInfo, Regulations.gov):
  `Travis-Prall/court-listener-mcp` (PolyForm Noncommercial)

## Install

```bash
git clone https://github.com/ebey317/house-of-maat.git
cd house-of-maat
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick start

```bash
maat ask "what is adverse possession in Indiana?"
maat research "tenant retaliation security deposit Indiana"

# Filing pipeline: packet -> GATE 1 approval -> e-file ->
# GATE 2 fee confirmation -> emailed copy + tracking log.
maat file --type small-claims-complaint --evidence ./my-case/ --output ./packet
maat file --type small-claims-complaint --evidence ./my-case/ --court in-odyssey \
    --submit --pay --filer-email you@example.com        # dry run by default
maat file --type motion-skeleton --evidence ./my-case/ --court in-odyssey \
    --submit --pay --live                              # real path (gates still required)

# E-file credentials + payment references (secure entry, encrypted storage)
maat creds setup --court in-odyssey
maat creds setup-payment --id main-card
maat creds list
```

## E-file credentials & payment references

Filing portals (Tyler/Odyssey, CM/ECF) need account credentials, and fee
payment needs a payment reference. Both are stored encrypted and loaded
automatically at e-file time:

1.  — username + secret entered via
    (no echo, never displayed, never logged).
2.  — a portal token or masked
   identifier. Full card numbers are REFUSED (no PCI scope in this tool);
   Tyler/Odyssey-style portals collect the fee inside their own checkout.

Storage: the system keyring is tried first (macOS Keychain, Windows
Credential Manager, Linux Secret Service); on headless Linux with no working
keyring backend, the fallback is a Fernet-encrypted file at
 (0600), with the key from
 or a setup-time passphrase (PBKDF2, 600k rounds).
The key is never written next to the file.

Rules: never hardcode credentials (code, tests, docs, examples); tests use
fake credentials in a tmp dir. Credentials load automatically, but nothing
files without your explicit GATE 1 approval and nothing is charged without
your explicit GATE 2 confirmation.

Packet emails are configured env-only and off by default (dry run):

    MAAT_SMTP_HOST / MAAT_SMTP_PORT / MAAT_SMTP_USER / MAAT_SMTP_PASS / MAAT_SMTP_FROM

## E-file credentials & payment references

Filing portals (Tyler/Odyssey, CM/ECF) need account credentials, and fee
payment needs a payment reference. Both are stored encrypted and loaded
automatically at e-file time:

1. `maat creds setup --court in-odyssey` -- username + secret entered via
   `getpass` (no echo, never displayed, never logged).
2. `maat creds setup-payment --id main` -- a portal token or masked
   identifier. Full card numbers are REFUSED (no PCI scope in this tool);
   Tyler/Odyssey-style portals collect the fee inside their own checkout.

Storage: the system keyring is tried first (macOS Keychain, Windows
Credential Manager, Linux Secret Service); on headless Linux with no working
keyring backend, the fallback is a Fernet-encrypted file at
`~/.config/house-of-maat/credentials.enc` (0600), with the key from
`MAAT_CREDENTIALS_KEY` or a setup-time passphrase (PBKDF2, 600k rounds).
The key is never written next to the file.

Rules: never hardcode credentials (code, tests, docs, examples); tests use
fake credentials in a tmp dir. Credentials load automatically, but nothing
files without your explicit GATE 1 approval and nothing is charged without
your explicit GATE 2 confirmation.

Packet emails are configured env-only and off by default (dry run):

    MAAT_SMTP_HOST / MAAT_SMTP_PORT / MAAT_SMTP_USER / MAAT_SMTP_PASS / MAAT_SMTP_FROM

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This software is provided for research and drafting assistance only. It is
not a substitute for a licensed attorney. The maintainers are not responsible
for documents you sign or file.
