import os, requests

BASE = 'https://www.courtlistener.com/api/rest/v4/'
TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')

def _headers():
    h = {'Accept': 'application/json'}
    if TOKEN:
        h['Authorization'] = f'Token {TOKEN}'
    return h

def search_cases(query: str, jurisdiction: str = '', year_min: int | None = None, year_max: int | None = None, limit: int = 10):
    params = {'type': 'o', 'q': query}
    if jurisdiction:
        params['court'] = jurisdiction
    if year_min:
        params['filed_after'] = f'{year_min}-01-01'
    if year_max:
        params['filed_before'] = f'{year_max}-12-31'
    params['page_size'] = min(limit, 100)
    r = requests.get(BASE + 'search/', params=params, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get('results', [])

def analyze_citations(text: str):
    r = requests.post(BASE + 'citation/verify/', json={'text': text}, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()
