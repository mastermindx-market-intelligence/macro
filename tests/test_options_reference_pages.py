"""Tests for reference_page_validator.validate_reference_next_url."""

import socket
import urllib.parse

import pytest

@pytest.mark.parametrize('url',[
    'https://@api.polygon.io/v3/reference/options/contracts?cursor=abc',
    'https://api.polygon.io:/v3/reference/options/contracts?cursor=abc'])
def test_empty_userinfo_and_empty_port_are_explicitly_refused(url):
    with pytest.raises(ValueError):
        validate_reference_next_url(url,origin='https://api.polygon.io',scope={'limit':1000})

def test_caller_cannot_change_reference_endpoint():
    with pytest.raises(ValueError):
        validate_reference_next_url('https://api.polygon.io/v3/snapshot/options?cursor=abc',
            origin='https://api.polygon.io',scope={'limit':1000},path='/v3/snapshot/options')

from lib.options_reference_pages import (
    DEFAULT_REFERENCE_PATH,
    MAX_CURSOR_CHARS,
    ReferenceNextUrlError,
    validate_reference_next_url,
)


def page_prober(payloads, statuses=None):
    import json
    from types import SimpleNamespace
    from scripts.massive_entitlement_probe import RestProber
    from lib.options_source_receipts import BoundedRequestBudget
    class Pages:
        headers={}
        def __init__(self):self.calls=[]
        def get(self,*a,**kw):
            i=len(self.calls);self.calls.append((a,kw))
            raw=json.dumps(payloads[i]).encode()
            return SimpleNamespace(status_code=(statuses or [200]*len(payloads))[i],
                iter_content=lambda **k:iter([raw]),close=lambda:None)
    session=Pages();budget=BoundedRequestBudget(20,profile='reference_population')
    clock=[0.0]
    prober=RestProber('synthetic-secret',session=session,request_budget=budget,profile='reference_population',
        max_rows=1000,max_bytes=1024*1024,page_clock=lambda:clock[0],page_sleep=lambda n:clock.__setitem__(0,clock[0]+n))
    return prober,session,budget,clock


def test_population_crawl_preserves_actual_queries_and_stops_at_last_page():
    p,s,b,c=page_prober([{'results':[],'next_url':ORIGIN+PATH+'?cursor=next&apiKey=never-retain'}, {'results':[]}])
    updates=[];out=p.reference_population('SPY','2026-10-16',on_update=updates.append)
    assert out['state']=='COMPLETE' and b.attempts==2 and len(out['pages'])==2
    assert out['pages'][0]['params']['as_of']=='2026-10-16'
    assert out['pages'][1]['params']=={'cursor':'next'} and c[0]==15
    assert all(not kw['allow_redirects'] for _,kw in s.calls)
    assert 'apiKey' not in str(out) and 'never-retain' not in str(out)
    assert all(u['state']!='COMPLETE' for u in updates[:-1])
    from lib.options_source_receipts import reference_population_terms
    terms,refs=reference_population_terms(out,'SPY')
    assert terms==[] and len(refs)==2


@pytest.mark.parametrize('mode',['wrong_origin','cycle','page_cap','byte_cap','row_cap','refused','body_refused'])
def test_population_crawl_failure_never_promotes_partial_manifest(mode):
    nxt=ORIGIN+PATH+'?cursor=again'
    payloads=[{'results':[],'next_url':nxt},{'results':[]}];kwargs={};statuses=None
    if mode=='wrong_origin':payloads[0]['next_url']='https://wrong.test'+PATH+'?cursor=x'
    if mode=='cycle':payloads[1]['next_url']=nxt+'&limit=1000'
    if mode=='page_cap':kwargs['max_pages']=1
    if mode=='byte_cap':kwargs['max_total_bytes']=1
    if mode=='row_cap':payloads[0]['results']=[{}]*1001
    if mode=='refused':statuses=[429]
    if mode=='body_refused':payloads[0]['status']='NOT_AUTHORIZED'
    p,s,b,c=page_prober(payloads,statuses);out=p.reference_population('SPY','2026-10-16',**kwargs)
    assert out['state']=='STOPPED' and b.stopped
    assert len(s.calls)==(2 if mode=='cycle' else 1)
    from lib.options_source_receipts import reference_population_terms
    with pytest.raises(ValueError):reference_population_terms(out,'SPY')

ORIGIN = "https://api.polygon.io"
OTHER_ORIGIN = "https://api.massive.com"
PATH = DEFAULT_REFERENCE_PATH
CURSOR = "b2Zmc2V0PTAmc29ydD10aWNrZXI"
SECRET = "sk_supersecret_12345"

SCOPE = {
    "underlying_ticker": "SPY",
    "as_of": "2026-10-19",
    "expired": "false",
    "order": "asc",
    "sort": "ticker",
    "limit": 1000,
}


def build(query="cursor=" + CURSOR, scheme="https", host="api.polygon.io",
          port=None, userinfo="", path=PATH, fragment=""):
    netloc = host
    if port is not None:
        netloc += ":%d" % port
    url = scheme + "://" + userinfo + netloc + path
    if query is not None:
        url += "?" + query
    return url + fragment


def validate(next_url, origin=ORIGIN, scope=None, path=None):
    kwargs = {"origin": origin, "scope": dict(SCOPE) if scope is None else scope}
    if path is not None:
        kwargs["path"] = path
    return validate_reference_next_url(next_url, **kwargs)


def reject(next_url, **kwargs):
    with pytest.raises(ReferenceNextUrlError) as excinfo:
        validate(next_url, **kwargs)
    assert SECRET not in str(excinfo.value)  # secrets never leak through error text
    return excinfo


def test_valid_minimal_cursor_only():
    path, query = validate(build())
    assert path == PATH
    assert query == {"cursor": CURSOR}


def test_valid_full_link_strips_api_key():
    query_text = (
        "underlying_ticker=SPY&as_of=2026-10-19&expired=false&order=asc"
        "&sort=ticker&limit=1000&apiKey=" + SECRET + "&cursor=" + CURSOR
    )
    path, query = validate(build(query=query_text))
    assert path == PATH
    assert query == {
        "underlying_ticker": "SPY",
        "as_of": "2026-10-19",
        "expired": "false",
        "order": "asc",
        "sort": "ticker",
        "limit": "1000",
        "cursor": CURSOR,
    }
    assert SECRET not in repr(query)
    assert "apiKey" not in urllib.parse.urlencode(query)


def test_valid_massive_origin():
    path, query = validate(build(host="api.massive.com"), origin=OTHER_ORIGIN)
    assert (path, query) == (PATH, {"cursor": CURSOR})


def test_valid_origin_with_trailing_slash():
    path, _ = validate(build(), origin=ORIGIN + "/")
    assert path == PATH


def test_valid_optional_gte_matches_scope():
    scope = dict(SCOPE)
    scope["expiration_date.gte"] = "2026-10-19"
    _, query = validate(build(query="expiration_date.gte=2026-10-19&cursor=" + CURSOR), scope=scope)
    assert query["expiration_date.gte"] == "2026-10-19"


def test_cursor_at_bound_is_accepted():
    _, query = validate(build(query="cursor=" + "a" * MAX_CURSOR_CHARS))
    assert len(query["cursor"]) == MAX_CURSOR_CHARS


def test_api_key_in_scope_is_still_not_echoed():
    scope = dict(SCOPE)
    scope["apiKey"] = SECRET
    _, query = validate(build(query="cursor=" + CURSOR), scope=scope)
    assert "apiKey" not in query
    assert SECRET not in repr(query)


def test_no_network_is_used(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("validator must not touch the network")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    validate(build())


REJECTIONS = [
    ("wrong scheme http", build(scheme="http")),
    ("ftp scheme", build(scheme="ftp")),
    ("wrong host", build(host="evil.example")),
    ("other allowed origin is not same-origin", build(host="api.massive.com")),
    ("userinfo with password", build(userinfo="user:pass@")),
    ("userinfo on allowed host", build(userinfo="user@")),
    ("explicit port 443", build(port=443)),
    ("explicit port 8443", build(port=8443)),
    ("fragment", build(fragment="#page2")),
    ("wrong path", build(path="/v3/reference/tickers")),
    ("trailing slash path", build(path=PATH + "/")),
    ("encoded slash in path", build(path="/v3/reference/options%2Fcontracts")),
    ("encoded chars in path", build(path="/%763/reference/options/contracts")),
    ("double slash in path", build(path="/v3//reference/options/contracts")),
    ("dot segment in path", build(path="/v3/reference/options/contracts/../contracts")),
    ("dot segment in middle", build(path="/v3/./reference/options/contracts")),
    ("semicolon path parameter", build(path=PATH + ";x=1")),
    ("relative url", PATH + "?cursor=" + CURSOR),
    ("scheme relative url", "//api.polygon.io" + PATH + "?cursor=" + CURSOR),
    ("empty netloc", "https://" + PATH + "?cursor=" + CURSOR),
    ("bare origin without path", "https://api.polygon.io"),
    ("raw whitespace in url", "https://api.polygon.io" + PATH + "?cursor=" + CURSOR + " "),
    ("blank cursor", build(query="cursor=")),
    ("missing cursor", build(query="limit=1000")),
    ("oversize cursor", build(query="cursor=" + "a" * (MAX_CURSOR_CHARS + 1))),
    ("space in cursor", build(query="cursor=a+b")),
    ("duplicate cursor", build(query="cursor=a&cursor=b")),
    ("encoded duplicate cursor", build(query="cursor=a&c%75rsor=b")),
    ("duplicate apiKey", build(query="apiKey=" + SECRET + "&apiKey=" + SECRET)),
    ("duplicate scope key", build(query="underlying_ticker=SPY&underlying_ticker=SPY&cursor=" + CURSOR)),
    ("duplicate limit", build(query="limit=1000&limit=1000&cursor=" + CURSOR)),
    ("unknown query field", build(query="cursor=" + CURSOR + "&foo=bar")),
    ("encoded unknown query field", build(query="cursor=" + CURSOR + "&f%6Fo=bar")),
    ("lookalike key is unknown", build(query="cursor=" + CURSOR + "&Cursor=" + CURSOR)),
    ("widened ticker", build(query="underlying_ticker=QQQ&cursor=" + CURSOR)),
    ("widened as_of", build(query="as_of=2026-12-31&cursor=" + CURSOR)),
    ("widened expiry flag", build(query="expired=true&cursor=" + CURSOR)),
    ("widened expiration_date.gte", build(query="expiration_date.gte=2020-01-01&cursor=" + CURSOR)),
    ("widened limit", build(query="limit=5000&cursor=" + CURSOR)),
    ("non decimal limit", build(query="limit=1e3&cursor=" + CURSOR)),
    ("signed limit", build(query="limit=%2B1000&cursor=" + CURSOR)),
    ("float limit", build(query="limit=1000.0&cursor=" + CURSOR)),
    ("empty next_url", ""),
    ("none next_url", None),
    ("bytes next_url", b"https://api.polygon.io/v3/reference/options/contracts"),
    ("garbage next_url", "not a url at all"),
]


@pytest.mark.parametrize("name,next_url", REJECTIONS, ids=[r[0] for r in REJECTIONS])
def test_rejected(name, next_url):
    reject(next_url)


def test_encoded_credentials_are_rejected():
    reject(build(userinfo="user%3Apass@"))


def test_malformed_port_is_rejected():
    reject("https://api.polygon.io:bad" + PATH + "?cursor=" + CURSOR)


def test_empty_scope_is_rejected():
    reject(build(), scope={})


def test_non_mapping_scope_is_rejected():
    with pytest.raises(ReferenceNextUrlError):
        validate_reference_next_url(build(), origin=ORIGIN, scope=None)


def test_disallowed_origin_argument_is_rejected():
    reject(build(), origin="https://example.com")
    reject(build(), origin="http://api.polygon.io")
    reject(build(), origin="https://api.polygon.io:443")
    reject(build(), origin="https://user@api.polygon.io")


def test_reconstruction_is_requests_ready():
    _, query = validate(build())
    rebuilt = ORIGIN + PATH + "?" + urllib.parse.urlencode(query)
    parts = urllib.parse.urlsplit(rebuilt)
    assert parts.path == PATH
    assert urllib.parse.parse_qsl(parts.query) == [("cursor", CURSOR)]
    assert "apiKey" not in rebuilt


@pytest.mark.parametrize('nxt',[False,0,[], ''])
def test_population_malformed_terminal_link_is_not_completion(nxt):
 p,s,b,c=page_prober([{'results':[],'next_url':nxt}])
 out=p.reference_population('SPY','2026-10-16')
 assert out['state']=='STOPPED' and b.attempts==1
