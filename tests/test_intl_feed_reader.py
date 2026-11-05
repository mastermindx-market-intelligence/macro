"""lib/intl_feed_reader.py tests — the fixed-origin contract, the byte cap, the
refused redirect, and the one-GET / timeout / closure guarantees.

Fully offline: every request is served by a fake transport installed over the
module's opener, so this file performs NO network I/O of any kind.

Run: python -m pytest tests/test_intl_feed_reader.py -v
"""
from __future__ import annotations

import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure the repo root is on the path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import intl_feed_reader as feed_reader


# The incumbent R2 public base (config.yml -> r2_data_plane.public_base).
BASE = "https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev"


# ---------------------------------------------------------------------------
# helpers: fake transport (no sockets, no network)
# ---------------------------------------------------------------------------

class FakeHeaders:
    """Case-insensitive header mapping, like a real HTTP message."""

    def __init__(self, mapping=None):
        self._items = {str(key).lower(): value for key, value in (mapping or {}).items()}

    def get(self, name, default=None):
        return self._items.get(str(name).lower(), default)

    def __getitem__(self, name):
        return self._items[str(name).lower()]

    def __contains__(self, name):
        return str(name).lower() in self._items


class FakeResponse:
    """Minimal response object. The reader must close it on every path."""

    def __init__(self, body=b"", status=200, headers=None):
        self._body = body
        self.status = status
        self.headers = FakeHeaders(headers)
        self.closed = False
        self.reads = []

    # The urllib response surface the real opener chain uses.
    @property
    def code(self):
        return self.status

    @property
    def msg(self):
        return "OK"

    def info(self):
        return self.headers

    def read(self, amt=None):
        self.reads.append(amt)
        if amt is None:
            chunk, self._body = self._body, b""
        else:
            chunk, self._body = self._body[:amt], self._body[amt:]
        return chunk

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False


class FakeHTTPSHandler(urllib.request.BaseHandler):
    """A urllib handler that answers from a canned response.

    It replaces ONLY the socket layer: the real OpenerDirector, the real
    HTTPErrorProcessor, and the real redirect handler still run, so the
    status handling and the redirect refusal are exercised for real without
    a socket. Its low handler_order makes it win over the stock HTTPS
    handler.
    """

    handler_order = 100

    def __init__(self, response=None):
        self.response = response
        self.requests = []

    def https_open(self, req):
        self.requests.append(req)
        return self.response


class FakeBody:
    """A body for an HTTPError: records whether it was closed."""

    def __init__(self):
        self.closed = False

    def read(self, *args):
        return b""

    def close(self):
        self.closed = True


class FakeOpener:
    """Records every request it is handed; serves a canned response or error."""

    def __init__(self):
        self.response = None
        self.error = None
        self.calls = []

    def open(self, request, timeout=None):
        self.calls.append(SimpleNamespace(request=request, timeout=timeout))
        if self.error is not None:
            raise self.error
        return self.response

    @property
    def urls(self):
        return [call.request.full_url for call in self.calls]


@pytest.fixture
def transport(monkeypatch):
    """Replace the module's opener with a fake transport."""
    fake = FakeOpener()
    monkeypatch.setattr(feed_reader, "_OPENER", fake)
    return fake


def _serve(transport, body=b"", status=200, headers=None):
    """Install a canned response on the fake transport; return it."""
    response = FakeResponse(body=body, status=status, headers=headers)
    transport.response = response
    return response


def _sent_headers(call):
    """The request headers as a lower-cased mapping.

    urllib capitalises header names when a Request is built ("User-Agent"
    becomes "User-agent"), so the assertions must not depend on that case.
    """
    return {key.lower(): value for key, value in call.request.headers.items()}


# ---------------------------------------------------------------------------
# base validation
# ---------------------------------------------------------------------------

def test_the_base_is_normalised_and_exposed():
    assert feed_reader.FixedFeedReader(BASE).base == BASE
    assert feed_reader.FixedFeedReader(BASE + "/").base == BASE
    assert feed_reader.FixedFeedReader(BASE + "/prefix/").base == BASE + "/prefix"
    assert feed_reader.FixedFeedReader(BASE + ":443").base == BASE + ":443"


@pytest.mark.parametrize("bad_base", [
    "http://pub.example",             # not HTTPS
    "ftp://pub.example",
    "//pub.example",                   # no scheme
    "pub.example/feeds",               # no scheme
    "https:///feeds",                  # no host
    "https://",                        # no host
    "https://user:secret@pub.example",  # userinfo
    "https://user@pub.example",        # userinfo
    "https://pub.example/feeds?a=1",   # query
    "https://pub.example/feeds#frag",  # fragment
    "https://pub.example\\feeds",      # backslash
    "https://pub.example /feeds",      # whitespace
    "https://pub.example/feeds\n",     # control character
    "https://pub.example\tfeeds",      # control character
    "https://pub.example:8443",         # port other than 443
    "https://pub.example:notaport",    # malformed port
    "https://pub.example/a/../b",      # dot segment
    "https://pub.example/a/./b",       # dot segment
    "",                                # empty
])
def test_an_unusable_base_is_refused(bad_base):
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(bad_base)


def test_a_non_string_base_is_refused():
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(None)


def test_a_config_error_is_also_a_value_error():
    """Callers that catch ValueError keep working."""
    with pytest.raises(ValueError):
        feed_reader.FixedFeedReader("http://pub.example")


# ---------------------------------------------------------------------------
# name validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("good_name", [
    "a.json",
    "A.json",
    "0.json",
    "a.b.json",
    "a_b-c.json",
    "x" * 251 + ".json",       # 256 characters: the longest allowed
])
def test_a_well_formed_name_is_accepted(good_name, transport):
    _serve(transport, body=b"{}")
    assert feed_reader.FixedFeedReader(BASE).read(good_name, max_bytes=64) == b"{}"


@pytest.mark.parametrize("bad_name", [
    "",                              # empty
    ".json",                         # no stem
    "../a.json",                     # parent traversal
    "..json",                        # leading dot
    "a..json",                       # doubled dot
    "a/b.json",                      # path separator
    "a%2Fb.json",                    # percent encoding
    "a.json?x=1",                    # query
    "a.json#frag",                   # fragment
    "a.json ",                       # trailing whitespace
    " a.json",                       # leading whitespace
    "a.json\n",                      # control character
    "a\t.json",
    "é.json",                        # non-ASCII
    "a.JSON",                        # not a .json name
    "a.txt",
    "-a.json",                       # first character must be alphanumeric
    "_a.json",
    ".hidden.json",
    "x" * 252 + ".json",             # 257 characters: one too long
])
def test_an_unusable_name_is_refused(bad_name, transport):
    _serve(transport, body=b"{}")
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(BASE).read(bad_name, max_bytes=64)
    assert transport.calls == []


def test_a_non_string_name_is_refused(transport):
    _serve(transport, body=b"{}")
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(BASE).read(None, max_bytes=64)


# ---------------------------------------------------------------------------
# byte cap validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_cap", [0, -1, 1.5, "64", None, True])
def test_an_unusable_cap_is_refused(bad_cap, transport):
    _serve(transport, body=b"{}")
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(BASE).read("a.json", max_bytes=bad_cap)
    assert transport.calls == []


def test_a_cap_above_the_ceiling_is_refused(transport):
    _serve(transport, body=b"{}")
    with pytest.raises(feed_reader.FeedConfigError):
        feed_reader.FixedFeedReader(BASE).read("a.json", max_bytes=feed_reader._MAX_BYTES_CEILING + 1)
    assert transport.calls == []


# ---------------------------------------------------------------------------
# the request itself
# ---------------------------------------------------------------------------

def test_the_request_targets_the_feeds_path_under_the_origin(transport):
    _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert transport.urls == [BASE + "/feeds/daily.json"]


def test_the_request_targets_the_feeds_path_under_a_prefix_base(transport):
    _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE + "/intl").read("daily.json", max_bytes=64)
    assert transport.urls == [BASE + "/intl/feeds/daily.json"]


def test_exactly_one_get_is_issued_with_a_ten_second_timeout(transport):
    _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call.request.get_method() == "GET"
    assert call.timeout == 10.0
    assert call.timeout == feed_reader._TIMEOUT_SECONDS


def test_the_request_carries_explicit_no_cache_headers_and_a_user_agent(transport):
    _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    headers = _sent_headers(transport.calls[0])
    assert headers["user-agent"]
    assert "no-cache" in headers["cache-control"]
    assert "no-store" in headers["cache-control"]
    assert headers["pragma"] == "no-cache"
    assert headers["expires"] == "0"


def test_the_request_carries_no_credential(transport):
    _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    headers = _sent_headers(transport.calls[0])
    for forbidden in ("authorization", "cookie", "x-api-key", "x-amz-security-token"):
        assert forbidden not in headers


# ---------------------------------------------------------------------------
# the body
# ---------------------------------------------------------------------------

def test_the_exact_bytes_come_back_unaltered(transport):
    body = b'{"generation": "2026-11-04", "rows": [1, 2, 3]}\n'
    _serve(transport, body=body)
    assert feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=1024) == body


def test_binary_bytes_come_back_unaltered(transport):
    body = bytes(range(256))
    _serve(transport, body=body)
    assert feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=1024) == body


def test_a_body_exactly_at_the_cap_is_returned(transport):
    _serve(transport, body=b"12345")
    assert feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=5) == b"12345"


def test_a_body_one_byte_over_the_cap_is_refused(transport):
    response = _serve(transport, body=b"123456")
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=5)
    assert response.closed


def test_the_reader_never_materialises_more_than_the_cap_plus_one(transport):
    response = _serve(transport, body=b"x" * 4096)
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=5)
    assert sum(amt for amt in response.reads) <= 6


def test_a_non_bytes_body_is_refused(transport):
    _serve(transport, body="not bytes at all")
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)


# ---------------------------------------------------------------------------
# Content-Length framing
# ---------------------------------------------------------------------------

def test_a_declared_length_above_the_cap_is_refused_before_the_body_is_read(transport):
    response = _serve(transport, body=b"x" * 100, headers={"Content-Length": "100"})
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=10)
    assert response.reads == []


def test_a_declared_length_at_the_cap_is_accepted(transport):
    _serve(transport, body=b"12345", headers={"Content-Length": "5"})
    assert feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=5) == b"12345"


def test_a_declared_length_below_the_cap_is_not_trusted(transport):
    """A lying short Content-Length must not smuggle an over-cap body through."""
    response = _serve(transport, body=b"x" * 100, headers={"Content-Length": "5"})
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=10)
    assert response.closed


@pytest.mark.parametrize("declared", ["abc", "5, 5", "5.0", "0x10", "5_0", "", "  "])
def test_a_malformed_declared_length_is_refused(declared, transport):
    _serve(transport, body=b"{}", headers={"Content-Length": declared})
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)


def test_a_negative_declared_length_is_refused(transport):
    _serve(transport, body=b"{}", headers={"Content-Length": "-1"})
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)


def test_an_absent_declared_length_is_fine(transport):
    _serve(transport, body=b"{}")
    assert feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64) == b"{}"


# ---------------------------------------------------------------------------
# status handling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [201, 204, 206, 400, 403, 404, 410, 500, 503])
def test_only_200_is_accepted(status, transport):
    response = _serve(transport, body=b"{}", status=status)
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert response.closed
    assert len(transport.calls) == 1


def test_a_redirect_response_is_refused_without_a_second_request(transport):
    response = _serve(
        transport,
        body=b"",
        status=302,
        headers={"Location": "https://elsewhere.example/steal"},
    )
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1
    assert all("elsewhere.example" not in url for url in transport.urls)
    assert response.closed


@pytest.mark.parametrize("status", [300, 301, 302, 303, 307, 308])
def test_a_redirect_raised_as_an_http_error_is_refused_without_a_second_request(status, transport):
    body = FakeBody()
    transport.error = urllib.error.HTTPError(f"{BASE}/feeds/daily.json", status, "Found", {}, body)
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1
    assert body.closed


def test_the_refusing_handler_raises_instead_of_following_a_location():
    """The real opener's redirect handler must not produce a second request."""
    handler = feed_reader._NoRedirect()
    request = urllib.request.Request(f"{BASE}/feeds/daily.json")
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        handler.redirect_request(
            request, None, 302, "Found", {}, "https://elsewhere.example/steal"
        )
    assert excinfo.value.code == 302


def test_the_redirect_chain_never_opens_a_second_request():
    """urllib's own redirect chain must raise before it would re-open the URL."""
    handler = feed_reader._NoRedirect()
    opened = []
    handler.parent = SimpleNamespace(open=lambda *args, **kwargs: opened.append(args))
    request = urllib.request.Request(f"{BASE}/feeds/daily.json")
    with pytest.raises(urllib.error.HTTPError):
        handler.http_error_302(
            request,
            FakeBody(),
            302,
            "Found",
            FakeHeaders({"Location": "https://elsewhere.example/steal"}),
        )
    assert opened == []


# ---------------------------------------------------------------------------
# the real urllib chain, with only the socket layer replaced
# ---------------------------------------------------------------------------

def test_the_real_urllib_chain_serves_a_200(monkeypatch):
    """The genuine OpenerDirector, error processor and redirect handler run."""
    response = FakeResponse(body=b'{"ok": true}')
    handler = FakeHTTPSHandler(response=response)
    monkeypatch.setattr(
        feed_reader, "_OPENER",
        urllib.request.build_opener(feed_reader._NoRedirect(), handler),
    )
    body = feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert body == b'{"ok": true}'
    assert [req.full_url for req in handler.requests] == [BASE + "/feeds/daily.json"]
    assert response.closed


def test_the_real_urllib_chain_refuses_a_302_without_a_second_request(monkeypatch):
    """A redirect must not become a second HTTPS request to the Location."""
    response = FakeResponse(
        body=b"",
        status=302,
        headers={"Location": "https://elsewhere.example/steal"},
    )
    handler = FakeHTTPSHandler(response=response)
    monkeypatch.setattr(
        feed_reader, "_OPENER",
        urllib.request.build_opener(feed_reader._NoRedirect(), handler),
    )
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(handler.requests) == 1
    assert response.closed


def test_the_real_urllib_chain_raises_on_a_404(monkeypatch):
    response = FakeResponse(body=b"", status=404)
    handler = FakeHTTPSHandler(response=response)
    monkeypatch.setattr(
        feed_reader, "_OPENER",
        urllib.request.build_opener(feed_reader._NoRedirect(), handler),
    )
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(handler.requests) == 1
    assert response.closed


def test_the_shared_opener_carries_the_refusing_handler():
    """The default redirect handler is replaced, not merely supplemented."""
    handlers = feed_reader._OPENER.handlers
    assert any(isinstance(handler, feed_reader._NoRedirect) for handler in handlers)
    assert not any(type(handler) is urllib.request.HTTPRedirectHandler for handler in handlers)


# ---------------------------------------------------------------------------
# transport failures
# ---------------------------------------------------------------------------

def test_a_network_failure_is_reported_without_a_retry(transport):
    transport.error = urllib.error.URLError("name resolution failed")
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1


def test_a_timeout_is_reported(transport):
    transport.error = socket.timeout("timed out")
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1


def test_a_wrapped_timeout_is_reported(transport):
    transport.error = urllib.error.URLError(socket.timeout("timed out"))
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1


def test_a_protocol_failure_is_reported(transport):
    import http.client
    transport.error = http.client.IncompleteRead(b"partial")
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert len(transport.calls) == 1


# ---------------------------------------------------------------------------
# closure
# ---------------------------------------------------------------------------

def test_the_response_is_closed_on_success(transport):
    response = _serve(transport, body=b"{}")
    feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert response.closed


def test_the_response_is_closed_on_a_framing_failure(transport):
    response = _serve(transport, body=b"{}", headers={"Content-Length": "nonsense"})
    with pytest.raises(feed_reader.FeedFetchError):
        feed_reader.FixedFeedReader(BASE).read("daily.json", max_bytes=64)
    assert response.closed
