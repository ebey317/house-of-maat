"""Plain-English -> court-ready legal drafting (the Scrivener function).

BOUNDARY (read before using — this is a hard design line, not flavor text):

    This module writes down what the user SAYS in legal form. It does NOT:
      - advise what to file, when to file, or whether to file at all;
      - advise what claims, defenses, or arguments to make;
      - provide legal strategy, interpret anyone's rights, or predict outcomes.

    It is a scrivener, not counsel. Scrivener = a careful scribe who puts
    your words into the shape courts expect. Counsel = someone who tells
    you what to do about your situation. This module is only the former.
    If you need the latter, consult a licensed attorney.

Transformation is rule/template-driven and runs fully locally — no external
LLM, no network. Steps:

    1. Strip conversational filler (hedges, false starts, verbal tics).
    2. Normalize first-person narrative into third-person factual allegations
       ("I was fired" -> "Movant states that Movant was fired...").
    3. Split the narrative into sentences and emit them as numbered factual
       allegations (courts read numbered paragraphs, not essays).
    4. Wrap the allegations in a formal caption + heading structure chosen by
       doc_type (motion / complaint / answer / affidavit).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Doc-type templates: caption roles and section titles. The scrivener picks
# the shape; the user supplies the substance.
# ---------------------------------------------------------------------------

_DOC_SHAPES = {
    "motion": {
        "title": "MOTION TO [RELIEF SOUGHT]",
        "subject": "Movant",
        "intro_heading": "INTRODUCTION",
        "facts_heading": "STATEMENT OF FACTS",
        "prayer": (
            "WHEREFORE, Movant respectfully requests that this Court grant the "
            "relief described above and grant such other and further relief as "
            "the Court deems just and proper."
        ),
    },
    "complaint": {
        "title": "COMPLAINT",
        "subject": "Plaintiff",
        "intro_heading": "INTRODUCTION",
        "facts_heading": "STATEMENT OF FACTS",
        "prayer": (
            "WHEREFORE, Plaintiff respectfully requests that this Court enter "
            "judgment in Plaintiff's favor and grant such other and further "
            "relief as the Court deems just and proper."
        ),
    },
    "answer": {
        "title": "ANSWER",
        "subject": "Defendant",
        "intro_heading": "INTRODUCTION",
        "facts_heading": "RESPONSES AND FACTUAL STATEMENTS",
        "prayer": (
            "WHEREFORE, Defendant respectfully requests that this Court deny "
            "the relief sought against Defendant and grant such other and "
            "further relief as the Court deems just and proper."
        ),
    },
    "affidavit": {
        "title": "AFFIDAVIT",
        "subject": "Affiant",
        "intro_heading": "INTRODUCTION",
        "facts_heading": "STATEMENTS OF FACT",
        "prayer": (
            "FURTHER AFFIANT SAYETH NAUGHT."
        ),
    },
}

_CAPTION = """IN THE [COURT NAME], [COUNTY], [STATE]

[MOVING PARTY NAME],
    {role_a},
v.
[RESPONDING PARTY NAME],
    {role_b}.

Case No. [CASE NUMBER]
"""

# ---------------------------------------------------------------------------
# Step 1: filler stripping
# ---------------------------------------------------------------------------

# Standalone verbal tics and hedges that carry no factual content. Each is
# removed with any trailing comma/space so the sentence still reads cleanly.
_FILLER_RES = [
    r"\b(?:um|uh|er|ah|hmm)\b[,\s]*",
    r"\byou know\b[,\s]*",
    r"\bbasically\b[,\s]*",
    r"\bactually\b[,\s]*",
    r"\bliterally\b[,\s]*",
    r"\bhonestly\b[,\s]*",
    r"\bpretty much\b[,\s]*",
    r"\bkind of\b[,\s]*",
    r"\bsort of\b[,\s]*",
    r"\bwell\b[,\s]*(?=[A-Z])",
    r"\banyway\b[,\s]*",
    r"\bjust\b[,\s]*",
    r"\breally\b[,\s]*",
    r"\bvery\b[,\s]*",
]

# Sentence-initial throat-clearing openers ("So, here's what happened...").
_OPENER_RES = [
    r"^(?:so|okay|ok|alright|listen)[,\s]+",
]


def _strip_filler(text: str) -> str:
    cleaned = text
    for pat in _OPENER_RES:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    for pat in _FILLER_RES:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    # Collapse whitespace, tidy spaces before punctuation.
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Step 2: first-person -> third-person factual voice
# ---------------------------------------------------------------------------

# Handled before the generic "\bI\b" rule so contractions resolve cleanly.
_CONTRACTION_RES = [
    (r"\bI['\u2019]m\b", "SUBJECT is"),
    (r"\bI['\u2019]ve\b", "SUBJECT has"),
    (r"\bI['\u2019]ll\b", "SUBJECT will"),
    (r"\bI['\u2019]d\b", "SUBJECT would"),
]


def _depersonalize(text: str, subject: str) -> str:
    out = text
    for pat, repl in _CONTRACTION_RES:
        out = re.sub(pat, repl.replace("SUBJECT", subject), out, flags=re.IGNORECASE)
    out = re.sub(r"\bmy\b", f"{subject}'s", out, flags=re.IGNORECASE)
    out = re.sub(r"\bmine\b", f"{subject}'s", out, flags=re.IGNORECASE)
    out = re.sub(r"\bme\b", subject, out, flags=re.IGNORECASE)
    # Lone "I" as grammatical subject. Guard against "i.e." style fragments.
    out = re.sub(r"\bI\b(?!['\u2019.])", subject, out)
    # Repair doubled subjects the rule above can create ("Movant Movant was").
    out = re.sub(rf"\b{subject}\s+{subject}\b", subject, out)
    return out


# ---------------------------------------------------------------------------
# Step 3: sentence splitting + numbered allegations
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\u201c])", text)
    sentences = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Drop fragments that are only a leftover opener.
        if len(p.split()) < 2 and p.lower() in {"so", "ok", "okay", "well"}:
            continue
        if p[0].islower():
            p = p[0].upper() + p[1:]
        if p[-1] not in ".!?":
            p += "."
        sentences.append(p)
    return sentences


# ---------------------------------------------------------------------------
# Allegation extraction (for packet assembly: insert just the numbered
# allegations at the template's facts placeholder, not the whole document).
# ---------------------------------------------------------------------------

_FACTS_HEADINGS = {
    "### STATEMENT OF FACTS",
    "### RESPONSES AND FACTUAL STATEMENTS",
    "### STATEMENTS OF FACT",
}


def extract_allegations(rendered_doc: str) -> list[str]:
    """Pull the numbered factual allegations out of a rendered document.

    Returns the allegation lines (e.g. '1. Movant states that ...'). Falls
    back to the whole document when the facts section cannot be found.
    """
    lines = (rendered_doc or "").splitlines()
    collecting = False
    allegations: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in _FACTS_HEADINGS:
            collecting = True
            continue
        if collecting:
            if stripped.startswith("###"):
                break
            if re.match(r"^\d+\.\s", stripped):
                allegations.append(stripped)
    return allegations or [rendered_doc.strip()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plain_english_to_legal(text: str, doc_type: str = "motion") -> str:
    """Convert plain-English narrative into court-ready drafting.

    Scrivener boundary (also in this module's docstring): this function
    restates what the user said in legal form. It does not advise what to
    file, what claims to make, or any strategy.

    Args:
        text: the user's plain-English narrative (one or more sentences).
        doc_type: "motion" (default), "complaint", "answer", or "affidavit".

    Returns:
        A markdown document with a formal caption block, numbered factual
        allegations, and a prayer for relief — bracketed placeholders left
        for the user to fill (names, court, case number).
    """
    shape = _DOC_SHAPES.get(doc_type, _DOC_SHAPES["motion"])
    subject = shape["subject"]

    cleaned = _strip_filler(text or "")
    if not cleaned:
        allegations = ["1. [No factual narrative was provided.]"]
    else:
        voiced = _depersonalize(cleaned, subject)
        sentences = _split_sentences(voiced) or [voiced]
        # Every paragraph reads "N. <Subject> states that <fact>." — the
        # standard factual-allegation frame. Lowercase the sentence start so
        # it reads naturally after "states that".
        allegations = []
        for i, s in enumerate(sentences, start=1):
            body = s[0].lower() + s[1:] if s and s[0].isupper() else s
            allegations.append(f"{i}. {subject} states that {body}")

    role_a, role_b = {
        "motion": ("Movant", "Respondent"),
        "complaint": ("Plaintiff", "Defendant"),
        "answer": ("Defendant", "Plaintiff"),
        "affidavit": ("Affiant", ""),
    }.get(doc_type, ("Movant", "Respondent"))
    caption = _CAPTION.format(role_a=role_a, role_b=role_b).rstrip()
    if doc_type == "affidavit":
        caption = caption.replace("v.\n[RESPONDING PARTY NAME],\n    .\n\n", "")

    facts = "\n\n".join(allegations)

    doc = f"""{caption}

## {shape["title"]}

### {shape["intro_heading"]}

[One-paragraph summary of what this document requests and why.]

### {shape["facts_heading"]}

{facts}

### PRAYER FOR RELIEF

{shape["prayer"]}

### SIGNATURE BLOCK

Respectfully submitted,

_________________________  \\
[PRINTED NAME] — UNSIGNED. The tool never signs. Sign only after your review. \\
[ADDRESS] \\
[PHONE] \\
[EMAIL]
"""
    return doc
