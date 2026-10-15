import os, re, requests

BASE = 'https://api.govinfo.gov/'
KEY = os.environ.get('GOVINFO_API_KEY', 'DEMO_KEY')

# GovInfo's /search endpoint is POST-only and ignores the `collections`
# body field; restricting to one collection is done with the
# `collection:<CODE>` query prefix (verified against the live API).


def _post_search(query: str, limit: int):
    body = {'query': query, 'pageSize': min(limit, 100),
            'offsetMark': '*', 'historical': True}
    r = requests.post(BASE + 'search', params={'api_key': KEY}, json=body, timeout=30)
    r.raise_for_status()
    return r.json().get('results', [])


def _parse_uscode_ids(item: dict):
    title, section = None, None
    m = re.search(r'-title(\d+)', item.get('packageId') or '')
    if m:
        title = m.group(1)
    m = re.search(r'-sec([0-9A-Za-z.]+)', item.get('granuleId') or '')
    if m:
        section = m.group(1)
    return title, section


def search_uscode(query: str, limit: int = 10):
    """Search the U.S. Code. Returns [{title, section, heading, url}]."""
    out = []
    for item in _post_search(f'collection:USCODE {query}', limit):
        title_num, section = _parse_uscode_ids(item)
        if title_num and section:
            title = f'{title_num} U.S.C. \u00a7 {section}'
        else:
            title = (item.get('title') or '').strip()
        out.append({
            'title': title,
            'section': section,
            'heading': (item.get('title') or '').strip(),
            'url': f"https://www.govinfo.gov/app/details/{item.get('packageId')}/{item.get('granuleId')}",
        })
    return out


def search_statutes(query: str, limit: int = 10):
    """Search the Statutes at Large (collection STATUTE)."""
    out = []
    for item in _post_search(f'collection:STATUTE {query}', limit):
        out.append({
            'title': (item.get('title') or '').strip(),
            'package_id': item.get('packageId'),
            'granule_id': item.get('granuleId'),
            'url': f"https://www.govinfo.gov/app/details/{item.get('packageId')}/{item.get('granuleId')}",
        })
    return out


def get_collection_info(collection: str = 'USCODE'):
    r = requests.get(BASE + 'collections/' + collection, params={'api_key': KEY}, timeout=30)
    r.raise_for_status()
    return r.json()
