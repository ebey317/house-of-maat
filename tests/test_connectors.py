import pytest
import requests

from maat.connectors import courtlistener, govinfo
from maat.connectors.states import get_state_source
from maat.connectors.states.indiana import IndianaSource

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}


def _skip_on_rate_limit(exc):
    resp = getattr(exc, 'response', None)
    if resp is not None and resp.status_code == 429:
        pytest.skip('API rate limit hit (429); retry with a key or later')
    raise


def test_courtlistener_search_live():
    results = courtlistener.search_cases('adverse possession', limit=2)
    assert len(results) >= 1, 'expected live CourtListener results'
    first = results[0]
    assert first.get('caseName'), 'result should have a caseName'


def test_govinfo_search_uscode_live():
    try:
        results = govinfo.search_uscode('adverse possession', limit=3)
    except requests.HTTPError as e:
        _skip_on_rate_limit(e)
    assert len(results) >= 1, 'expected live GovInfo U.S. Code results'
    for r in results:
        assert set(r) == {'title', 'section', 'heading', 'url'}
        assert r['title'] and r['heading']
        assert r['url'].startswith('https://www.govinfo.gov/')


def test_govinfo_collection_info_live():
    try:
        info = govinfo.get_collection_info('USCODE')
    except requests.HTTPError as e:
        _skip_on_rate_limit(e)
    assert info.get('collectionCode') == 'USCODE'


def test_indiana_state_code_and_registry():
    src = get_state_source('IN')
    assert isinstance(src, IndianaSource)
    assert src.state_code() == 'IN'
    with pytest.raises(ValueError):
        get_state_source('ZZ')


def _assert_resolves(entries):
    for e in entries:
        url = e['url']
        try:
            r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
        except requests.RequestException as exc:
            pytest.fail(f'URL did not resolve: {url} ({exc})')
        assert r.status_code == 200, f'expected 200 for {url}, got {r.status_code}'


def test_indiana_forms_index_urls_resolve():
    src = IndianaSource()
    forms = src.forms_index()
    assert len(forms) >= 3
    for f in forms:
        assert f['name'] and f['url'] and f['description']
    _assert_resolves(forms)


def test_indiana_court_rules_urls_resolve():
    rules = IndianaSource().court_rules()
    assert len(rules) >= 2
    for r_ in rules:
        assert r_['name'] and r_['url']
    _assert_resolves(rules)


def test_indiana_self_help_links_resolve():
    links = IndianaSource().self_help_links()
    assert len(links) >= 1
    for link in links:
        assert link['name'] and link['url'] and link['description']
    _assert_resolves(links)


def test_indiana_fees_verified_or_marked_unverified():
    fees = IndianaSource().fee_schedule()
    assert len(fees) >= 1
    verified = [f for f in fees if f.get('verified')]
    assert len(verified) >= 1, 'expected at least one verified fee'
    for f in fees:
        assert f['court'] and f['filing_type'] and f['description']
        if f.get('verified'):
            assert isinstance(f['amount_cents'], int) and f['amount_cents'] > 0, \
                f"verified fee must have a positive amount_cents: {f['filing_type']}"
            assert f.get('source_url'), \
                f"verified fee must cite its source: {f['filing_type']}"
        else:
            assert f['amount_cents'] is None, \
                f"unverified fee must use amount_cents=None: {f['filing_type']}"
