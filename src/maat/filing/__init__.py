"""Filing pipeline: packet assembly, fees, warnings, credentials, delivery, email.

Human-signs / human-files principles are enforced across this package:

- The tool NEVER signs a document (signature pages are generated UNSIGNED).
- The tool NEVER files without the user's explicit approval (GATE 1).
- The tool NEVER moves money without a second explicit confirmation (GATE 2).
- The tool NEVER invents a fee or citation.

Modules:
    warning      — fringe-theory keyword detection + Warning Cover Sheet.
    fees         — per-jurisdiction filing-fee tables (verified-only seeding).
    credentials  — encrypted e-file + payment-method credential storage.
    portals      — e-filing portal registry (interactive vs. API, payment mode).
    packet       — filing-packet assembly (draft + rule check + signature page
                   + deadline calendar + warning sheet).
    delivery     — delivery-confirmation options + JSONL tracking log.
    emailer      — email the finished packet to the filer (dry-run by default).
"""
