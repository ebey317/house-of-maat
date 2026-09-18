from maat.connectors.courtlistener import search_cases
from maat.connectors.seeds import seed_context

def ask_mode(question: str, sources: str = 'all') -> str:
    # TODO: implement RAG over seeds + CourtListener
    context = seed_context(question, sources)
    cases = search_cases(question, limit=3) if 'courtlistener' in sources or sources == 'all' else []
    return f"""
Question: {question}

Seeds:
{context}

Cases:
{cases}

(Answer generation not yet implemented — this is the scaffold.)
"""
