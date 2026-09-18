# AGENTS.md — House of Ma'at

This repo is the scaffold for an open-source legal research and filing
assistant.

## Build priorities

1. Make `maat ask` return a real answer from seed corpus + CourtListener.
2. Make `maat research` return a scored 3-case batch with "why this case."
3. Make `maat file` produce a complete filing packet (draft + rule check +
   signature page + deadline calendar).
4. Add fillable PDF support for Indiana forms.
5. Add the Maat + Black's 4th seed corpus and sqlite-vec index.

## Constraints

- Never auto-sign a court document.
- Never auto-file a document under the user's name.
- Always verify citations before delivery.
- Always insert the rejection-record disclaimer for fringe-theory filings.
- No IRS content.
- No Claude/closed-AI lock-in; keep core runnable on local models.

## When changing this repo

- Run `pytest` before committing.
- Keep `references/` as the single source of truth for sources and templates.
- Update README.md if you change CLI commands.
