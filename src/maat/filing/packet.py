"""Filing-packet assembly.

A complete packet, written into output_path:

    draft.md               — template + translated user evidence (unsigned draft)
    rule_check.md          — checklist the USER must verify before filing
    signature_page.md      — UNSIGNED. The tool never signs.
    deadline_calendar.md   — response/service deadlines (verify with local rules)
    warning_cover_sheet.md — only when fringe-theory keywords are detected

Every page of draft.md carries bracketed placeholders the user must fill
(names, court, case number). Nothing here is filed anywhere by the tool.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .warning import warning_cover_sheet
from maat.translate import extract_allegations

FACTS_PLACEHOLDER = "[Bullet or paragraph form facts, drawn from the user's evidence.]"


def build_draft(template_text: str, translated_evidence: str) -> str:
    """Merge the template with the translated evidence.

    The numbered allegations are inserted at the template's facts
    placeholder when present (just the allegations — not the scrivener's
    full document, which would duplicate the caption); otherwise the full
    translated document is appended as a Statement of Facts section.
    """
    if FACTS_PLACEHOLDER in template_text:
        allegations = "\n\n".join(extract_allegations(translated_evidence))
        return template_text.replace(FACTS_PLACEHOLDER, allegations)
    facts_section = (
        "### Statement of Facts (from user evidence)\n\n" + translated_evidence.strip()
    )
    return template_text.rstrip() + "\n\n" + facts_section + "\n"


def build_rule_checklist(doc_type: str = "motion") -> str:
    return f"""# Rule Check — VERIFY EACH ITEM YOURSELF BEFORE FILING

Document type: {doc_type}

- [ ] Caption is correct: court name, county, parties, case number.
- [ ] Every [BRACKETED PLACEHOLDER] in draft.md is filled in — none left blank.
- [ ] Facts match your evidence files exactly (no facts the tool invented).
- [ ] Every citation was verified (see citation note in the packet summary).
- [ ] Exhibits referenced in the draft are attached, labeled, and paginated.
- [ ] Service: copies prepared for every other party per the rules of procedure.
- [ ] Filing fee amount confirmed with the clerk (or fee-waiver petition attached).
- [ ] Page/word limits and formatting rules of the target court are met.
- [ ] Signature page is SIGNED BY YOU (the tool never signs).
- [ ] Deadline calendar dates checked against the court's local rules.

This checklist is not legal advice. When in doubt, ask the clerk's office
(procedural questions) or a licensed attorney (substantive questions).
"""


def build_signature_page() -> str:
    # UNSIGNED by design. Human signs, human files.
    return """# Signature Page — UNSIGNED

DO NOT FILE THIS PAGE UNSIGNED. The tool never signs a court document.

By signing below you declare under penalty of perjury that the foregoing
is true and correct to the best of your knowledge.

Respectfully submitted,

_________________________  \\
[PRINTED NAME]

[ADDRESS] \\
[PHONE] \\
[EMAIL]

Date: _______________

---
Generated as part of a House of Ma'at filing packet. Review the rule check
before signing.
"""


def build_deadline_calendar(today: date | None = None) -> str:
    today = today or date.today()
    return f"""# Deadline Calendar (generated {today.isoformat()})

VERIFY every date against the target court's local rules — deadlines vary
by court, case type, and method of service. This calendar is a starting
checklist, not a computation of your deadlines.

- [ ] Filing deadline / statute of limitations for your claim: ________
- [ ] Service of process deadline after filing: ________
- [ ] Response deadline if you are answering a complaint/motion: ________
- [ ] Discovery cutoffs (if applicable): ________
- [ ] Hearing / trial date: ________
- [ ] Fee payment or fee-waiver petition deadline: ________

Common federal reference points (VERIFY — local rules control):
- Answer to a complaint: 21 days after service (FRCP 12(a)(1)(A)(i)).
- Response to a motion: check the district's local rule (often 14–28 days).

If any deadline is unclear, call the clerk's office — procedural deadline
questions are exactly what clerks answer.
"""


def assemble_packet(
    *,
    template_text: str,
    translated_evidence: str,
    output_path: str | Path,
    doc_type: str = "motion",
    fringe_hits: tuple[str, ...] | list[str] = (),
    citation_note: str = "",
) -> dict:
    """Write the full packet into output_path. Returns {'files': [...], 'fringe': bool}."""
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)

    files: list[str] = []

    def _write(name: str, content: str) -> None:
        p = out / name
        p.write_text(content, encoding="utf-8")
        files.append(str(p))

    draft = build_draft(template_text, translated_evidence)
    if citation_note:
        draft += f"\n\n---\n\n**Citation check note:** {citation_note}\n"
    _write("draft.md", draft)
    _write("rule_check.md", build_rule_checklist(doc_type))
    _write("signature_page.md", build_signature_page())
    _write("deadline_calendar.md", build_deadline_calendar())

    fringe = bool(fringe_hits)
    if fringe:
        _write("warning_cover_sheet.md", warning_cover_sheet(list(fringe_hits)))

    return {"files": files, "fringe": fringe}
