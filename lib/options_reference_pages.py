"""Safe validation of provider-returned pagination next_url links.

The Massive (Polygon-compatible) reference-contract pagination adapter
receives an opaque next_url from the provider.  That string is untrusted: it
must be pinned to an allowed HTTPS origin and the exact reference path before
the adapter may rebuild a request with its own requests.Session.

validate_reference_next_url returns (path, query_dict) so the caller can issue
session.get(origin + path, params=query_dict):

* only absolute same-origin HTTPS links on the exact reference path are
  accepted: no userinfo, fragment, explicit port or path-encoding tricks;
* the query may carry only cursor, limit, apiKey and the original scope keys,
  each at most once and nothing else;
* exactly one nonempty bounded cursor is required; the opaque cursor is passed
  through untouched, never decoded or invented;
* any apiKey is dropped and is never returned, logged or embedded in an error
  message;
* scope keys echoed by the provider must equal the original request values,
  and an explicit limit must equal the original limit or be absent.

This module is pure standard library: it performs no I/O, no network calls,
no retries and activates no endpoints, and it grants no entitlement.
"""

import urllib.parse

__all__ = [
    "ALLOWED_ORIGINS",
    "DEFAULT_REFERENCE_PATH",
    "MAX_CURSOR_CHARS",
    "ReferenceNextUrlError",
    "validate_reference_next_url",
]

#: The only origins a provider next link may ever point at.
ALLOWED_ORIGINS = ("https://api.polygon.io", "https://api.massive.com")

#: The exact reference-contracts path a next link must reuse.
DEFAULT_REFERENCE_PATH = "/v3/reference/options/contracts"

#: Upper bound, in decoded characters, for the opaque cursor token.
MAX_CURSOR_CHARS = 8192

_ALLOWED_EXTRA_KEYS = ("cursor", "limit", "apiKey")
_SECRET_KEYS = frozenset({"apiKey"})


class ReferenceNextUrlError(ValueError):
    """A provider next link failed the same-origin/reference-contract checks."""


def _origin_parts(origin):
    """Return (scheme, hostname) for a bare origin string."""
    if not isinstance(origin, str) or not origin:
        raise ReferenceNextUrlError("origin must be a nonempty string")
    parts = urllib.parse.urlsplit(origin)
    if parts.scheme != "https" or not parts.netloc:
        raise ReferenceNextUrlError("origin must be an absolute https origin")
    if "@" in parts.netloc:
        raise ReferenceNextUrlError("origin must not carry userinfo")
    try:
        port = parts.port
    except ValueError:
        raise ReferenceNextUrlError("origin carries a malformed port") from None
    if port is not None or ":" in parts.netloc:
        raise ReferenceNextUrlError("origin must not carry an explicit port")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ReferenceNextUrlError("origin must not carry a path, query or fragment")
    return parts.scheme, parts.hostname


def _assert_allowed_origin(scheme, hostname):
    for allowed in ALLOWED_ORIGINS:
        if _origin_parts(allowed) == (scheme, hostname):
            return
    raise ReferenceNextUrlError(
        "origin %s://%s is not an allowed reference origin" % (scheme, hostname)
    )


def _check_cursor(cursor):
    if not cursor:
        raise ReferenceNextUrlError("next_url must carry exactly one nonempty cursor")
    if len(cursor) > MAX_CURSOR_CHARS:
        raise ReferenceNextUrlError("cursor exceeds the bounded cursor length")
    for char in cursor:
        if char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F:
            raise ReferenceNextUrlError("cursor carries whitespace or control characters")


def _check_limit(value, original):
    if not (value.isascii() and value.isdigit()):
        raise ReferenceNextUrlError("limit must be a plain decimal number")
    if original is None or value != str(original):
        raise ReferenceNextUrlError("limit does not equal the original request limit")


def validate_reference_next_url(next_url, *, origin, path=DEFAULT_REFERENCE_PATH, scope):
    """Validate an untrusted provider next_url and rebuild a safe request.

    origin is the origin the adapter is about to call (one of
    ALLOWED_ORIGINS); path is the exact reference path to pin; scope is the
    original nonsecret query mapping (underlying_ticker, as_of, expired,
    optional expiration_date.gte, order, sort and limit).

    Returns (path, query_dict): the pinned path and the validated nonsecret
    query values actually present on the next link, ready for
    requests.Session.get(origin + path, params=query_dict).

    Raises ReferenceNextUrlError (a ValueError subclass) on any deviation.
    The cursor is treated as opaque: it is never decoded or invented, and no
    retry is ever attempted here.
    """
    if not isinstance(next_url, str) or not next_url:
        raise ReferenceNextUrlError("next_url must be a nonempty string")
    if any(ord(char) <= 0x20 or ord(char) == 0x7F for char in next_url):
        raise ReferenceNextUrlError("next_url carries whitespace or control characters")
    if not isinstance(scope, dict) or not scope:
        raise ReferenceNextUrlError("scope must be a nonempty mapping of the original query")
    if path != DEFAULT_REFERENCE_PATH:
        raise ReferenceNextUrlError("path must be an absolute URL path string")

    origin_scheme, origin_host = _origin_parts(origin)
    _assert_allowed_origin(origin_scheme, origin_host)

    try:
        parts = urllib.parse.urlsplit(next_url)
    except ValueError:
        raise ReferenceNextUrlError("next_url is unparseable") from None

    if parts.scheme != "https" or not parts.netloc:
        raise ReferenceNextUrlError("next_url must be an absolute https URL")
    if "@" in parts.netloc:
        raise ReferenceNextUrlError("next_url must not carry userinfo")
    try:
        port = parts.port
    except ValueError:
        raise ReferenceNextUrlError("next_url carries a malformed port") from None
    if port is not None or ":" in parts.netloc:
        raise ReferenceNextUrlError("next_url must not carry an explicit port")
    if parts.fragment:
        raise ReferenceNextUrlError("next_url must not carry a fragment")
    if (parts.scheme, parts.hostname) != (origin_scheme, origin_host):
        raise ReferenceNextUrlError("next_url is not same-origin")
    if parts.path != path:
        raise ReferenceNextUrlError("next_url path is not the exact reference path")

    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    values = {}
    for key, value in pairs:
        if key in values:
            raise ReferenceNextUrlError("duplicate query key %r" % key)
        values[key] = value

    unknown = sorted(set(values) - set(_ALLOWED_EXTRA_KEYS) - set(scope))
    if unknown:
        raise ReferenceNextUrlError("unknown query key(s): %s" % ", ".join(unknown))

    query_dict = {}
    for key, value in values.items():
        if key in _SECRET_KEYS:
            continue  # dropped here: never returned, logged or put in errors
        if key == "cursor":
            continue  # validated below
        if key == "limit":
            _check_limit(value, scope.get("limit"))
        elif value != str(scope[key]):
            raise ReferenceNextUrlError("query key %r does not match the original scope" % key)
        query_dict[key] = value

    _check_cursor(values.get("cursor"))
    query_dict["cursor"] = values["cursor"]
    return path, query_dict
