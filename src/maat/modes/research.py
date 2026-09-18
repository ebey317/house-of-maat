from maat.connectors.courtlistener import search_cases, analyze_citations

def research_mode(topic: str, jurisdiction: str = '', year_min: int | None = None, year_max: int | None = None) -> str:
    cases = search_cases(topic, jurisdiction=jurisdiction, year_min=year_min, year_max=year_max, limit=15)
    # TODO: score and pick 3
    return f"""
Topic: {topic}
Jurisdiction: {jurisdiction or 'all'}
Year range: {year_min or 'any'} - {year_max or 'any'}

Candidates found: {len(cases)}

(Scoring + small-batch selection not yet implemented.)
"""
