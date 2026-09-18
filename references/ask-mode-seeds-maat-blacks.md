# Ask-mode seed corpus — 42 Laws of Maat + Black's 4th edition

These are the two primary sources for the conversational explainer ("ask"
mode) when the user is African-American and wants law explained with depth,
not just statutes.

## 42 Laws of Maat

**Source:** ancient Egyptian (c. 2700 BCE, Old Kingdom, 3rd Dynasty).
Afro-Asiatic language family — the same family as Berber, Amharic, Hausa,
Somali. **Concept:** Maat (mꜣꜥt) = truth, balance, order, law, morality,
justice all in one. Both a goddess and the cosmic order she embodies.

**Why it matters for an African-American-facing legal tool:**
- Oldest attested ethical-legal code in any African language.
- Predates Hammurabi by ~500 years and the Ten Commandments by ~1,000.
- Pre-Western, pre-colonial, pre-Roman — the deepest historical root of
  "law as cosmic order" thinking in Africa.
- The 42 Laws are concrete and quotable, not abstract — perfect seed
  content for "tell me about law" queries.

**Use as seed corpus for:**
- "What is law?"
- "What does justice mean?"
- "Tell me about African legal traditions"
- "What did Black people contribute to law before colonization?"
- Any explainer query where the user wants a non-Eurocentric framing.

**Ingest from:**
- Public translations of the 42 Laws of Maat (multiple versions exist;
  use the most-cited scholarly translation, e.g. Maulana Karenga's
  reconstruction).
- Encyclopedia entries on ancient Egyptian law (Wikipedia, Britannica).
- Academic papers on Maat as legal concept (Bond University research
  paper; Cairo University legal history).

## Black's Law Dictionary, 4th edition (1968)

**Why the 4th edition specifically:**
- The user may prefer the 4th edition over newer ones because newer
  editions redefine terms to fit changing legal fashion (the user's own
  framing).
- Older editions reflect the legal lexicon the user was taught, and may
  include etymologies or definitions that newer editions dropped.

**How the ask mode serves it:**
- Surface the 4th-edition entry verbatim, with attribution.
- Add a sidebar showing how later editions changed it (8th, 10th, current).
- When the user claims an etymology entry exists that the 4th edition
  does NOT contain (e.g. "Black = death in 4th edition" — Black's is a
  law dictionary, not an etymological one; standard etymology is
  Proto-Germanic *blakaz* / Old English *blæc*), serve both side by
  side: the user's preferred source + the standard reference, clearly
  labeled. Let the user decide what to trust.
- DO NOT encode contested etymologies as tool facts. The tool serves
  the source. The user interprets.

**Ingest from:**
- Public-domain scans of the 4th edition (Internet Archive, HathiTrust,
  the user's own digital copy if provided).
- If the user provides a digital file: ingest that file as the canonical
  source. The user has confirmed a 4th-edition file exists in their
  workspace.

## Indexing rules for these sources

- Maat corpus: ~50–80 short documents (one per Law + introductory
  context). Embed all.
- Black's 4th: full-text index. The book is ~2,000 pages; chunk at
  ~512 tokens / 64 overlap like the rest of the index. Surface
  verbatim when the entry is short enough; summarize with the
  original wording quoted when it isn't.
- Cross-link: when an ask-mode query hits Maat AND Black's (e.g.
  "what is justice"), surface both side by side — Maat's framing
  first (cultural depth), Black's framing second (modern legal
  lexicon).

## Naming implications

If the tool is named after Maat (e.g. "house of ma'at"), the Maat
corpus is the obvious primary seed. The user has chosen this direction.