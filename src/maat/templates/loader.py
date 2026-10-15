from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / 'templates'

def load_template(name: str) -> str:
    """Return path to a template by case type."""
    # Try motions first, then complaints, then forms
    for sub in ['motions', 'complaints', 'forms']:
        p = TEMPLATE_DIR / sub / f'{name}.md'
        if p.exists():
            return str(p)
    # Fallback: scaffold file in motions
    p = TEMPLATE_DIR / 'motions' / f'{name}.md'
    p.write_text(f'# {name}\n\n(Auto-scaffolded template.)\n')
    return str(p)
