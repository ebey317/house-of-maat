def seed_context(question: str, sources: str) -> str:
    # TODO: query sqlite-vec index over Maat + Black's 4th
    selected = []
    if sources in ('all', 'maat'):
        selected.append('42 Laws of Maat (seed corpus not yet indexed)')
    if sources in ('all', 'blacks'):
        selected.append("Black's Law Dictionary 4th ed. (seed corpus not yet indexed)")
    return '\n'.join(selected) if selected else '(no seed sources selected)'
