from pathlib import Path
from maat.templates.loader import load_template
from maat.forms.fillable import fill_form
from maat.connectors.courtlistener import analyze_citations

def file_mode(case_type: str, evidence_path: str, output_path: str) -> str:
    evidence = Path(evidence_path)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    # TODO: load template, intake evidence, draft, verify citations, emit packet
    template = load_template(case_type)
    return f"""
Case type: {case_type}
Evidence folder: {evidence}
Output folder: {output}
Template: {template}

(Filing packet generation not yet implemented — this is the scaffold.)
"""
