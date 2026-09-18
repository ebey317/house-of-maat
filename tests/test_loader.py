from maat.templates.loader import load_template
from pathlib import Path

def test_load_template_scaffolds():
    path = load_template('test-motion')
    assert Path(path).exists()
