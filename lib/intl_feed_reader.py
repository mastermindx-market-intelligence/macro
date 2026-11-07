"""Bounded, fixed-origin reader for the International feed plane.

The International service publishes its feed plane to the configured R2 public
origin (``config.yml`` -> ``r2_data_plane.public_base``, the ``feeds`` anchor).
This module is the transport primitive UNDER that plane and nothing else:

  - the base origin is TRUSTED deployment configuration, handed to the reader
    at construction time. It is never read from a request body, from the
    environment, or from this module's own config lookup.
  - every read is ONE GET for ONE named feed below ``<base>/feeds/``.
  - the response is returned as exact bytes. Nothing here parses, decodes,
    re-encodes, hashes, or otherwise alters the body.

What this module deliberately does NOT do -- the caller composes it ABOVE a
reader: generation/current-descriptor selection, descriptor and hash
validation, freshness admission, caching, retry, and fallback. Folding those
into the transport would make the transport untestable and would let a
stale-but-well-formed body pass as current.

Security posture (all enforced here, all exercised by
``tests/test_intl_feed_reader.py``):

  - HTTPS only, absolute URL, no userinfo, no query, no fragment, no
    backslash, no whitespace or control characters, and port 443 when a port
    is supplied at all.
  - Names are flat ASCII ``.json`` basenames --
    ``[A-Za-z0-9][A-Za-z0-9_.-]{0,255}`` with no ``..``. The character class
    already excludes ``/``, ``%``, ``?`` and ``#``, so a name can never leave
    the ``feeds/`` prefix.
  - Redirects are REFUSED, never followed. The opener is built with a
    redirect handler that raises instead of re-issuing the request, and any
    3xx that still reaches the reader is rejected. A followed redirect could
    leave the configured origin, and the "exactly one GET" rule, the byte
    cap, and the timeout would then describe the first hop only.
  - Exactly one GET per read, a 10 second timeout, explicit no-cache request
    headers, no retry, no fallback, no cookie state, and no credential of any
    kind on the wire.
  - The body is capped at ``max_bytes``: the reader materialises at most
    ``max_bytes + 1`` bytes and refuses an over-cap body. A declared
    ``Content-Length`` above the cap is refused up front; a declared length
    BELOW the cap is never trusted -- the body is measured, not believed.

The reader sends no authorization header and no cookie. The R2 public base is
a public origin, and the *service* (not this reader) owns authentication for
its own callers.
"""
from __future__ import annotations

import http.client
import re
import urllib.error
import urllib.parse
import urllib.request

__all__ = [
    "FeedConfigError",
    "FeedFetchError",
    "FeedReadError",
    "FixedFeedReader",
]


class FeedReadError(Exception):
    """Base class for every failure this reader raises."""


class FeedConfigError(FeedReadError, ValueError):
    """The base, the name, or the byte cap is unusable -- a configuration defect."""


class FeedFetchError(FeedReadError):
    """The feed could not be read as-is: transport, status, or framing failure."""


#: One GET, one 10 second budget, no retry.
_TIMEOUT_SECONDS = 10.0

#: Ceiling on a caller-supplied byte cap. The reader materialises the body in
#: memory, so an unbounded cap would let a single response decide the
#: process's memory use. Feeds are small JSON documents; a cap above this is
#: a configuration defect, not a real request.
_MAX_BYTES_CEILING = 64 * 1024 * 1024

#: The feed plane sits under this path segment, directly below the base.
_FEEDS_SEGMENT = "feeds"

#: A flat ASCII ``.json`` basename. The character class already excludes
#: ``/``, ``%``, ``?`` and ``#``, so a name cannot leave the feeds prefix.
_NAME_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.-]{0,255}\Z")

#: A plain DNS hostname: dot-separated labels of alphanumerics with inner
#: dashes (so no leading dash, no trailing dash, no empty label).
_HOSTNAME_RE = re.compile(
    r"\A[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\Z"
)

#: A bracketed IPv6 literal.
_IPV6_RE = re.compile(r"\A\[[0-9A-Fa-f:.]+\]\Z")

#: Digits only. ``int()`` is more permissive than HTTP (it accepts ``5_0`` and
#: unicode digits), so the declared length is matched before it is parsed.
_DIGITS_RE = re.compile(r"\A[0-9]+\Z")

_USER_AGENT = "macro-dashboard/intl-feed-reader"

#: Explicit no-cache request headers: this reader must never be answered from
#: a cache, and must never be the reason a cache keeps a stale copy.
#: ``Accept-Encoding: identity`` keeps the body uncompressed -- urllib does
#: not decode content encodings, so a compressed body would arrive as bytes
#: the caller cannot verify against the published descriptor.
_REQUEST_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect instead of following it.

    urllib's default opener answers a 3xx by issuing a SECOND request to the
    ``Location`` target. For a fixed-origin reader that is the wrong shape:
    the second request may leave the configured origin entirely, and the byte
    cap, the timeout, and the "exactly one GET" rule would all describe the
    first hop only. Raising here stops the chain before that second request
    is issued; the raised ``HTTPError`` carries the 3xx status, which the
    reader reports as a refused redirect.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Refuse the redirect instead of returning a replacement request."""
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


#: One shared opener. It carries no cookie handler (so no state survives a
#: read) and the refusing redirect handler above. urllib's default proxy and
#: TLS behaviour is left standing.
_OPENER = urllib.request.build_opener(_NoRedirect())


def _reject_control_and_space(text: str, what: str) -> None:
    """Refuse whitespace and control characters anywhere in ``text``."""
    for char in text:
        code = ord(char)
        if char.isspace() or code < 0x20 or 0x7F <= code <= 0x9F:
            raise FeedConfigError(f"{what} must not contain whitespace or control characters")


def _normalise_base(base: str) -> str:
    """Validate the TRUSTED deployment base and return its normalised form.

    The base is deployment configuration, not request input -- but it is
    still validated, because a mis-set base would otherwise silently aim
    every read at the wrong place. The accepted shape is an absolute HTTPS
    origin, optionally with a path prefix and optionally with port 443.
    """
    if not isinstance(base, str):
        raise FeedConfigError(f"base must be a string, got {type(base).__name__}")
    if not base:
        raise FeedConfigError("base must not be empty")
    if "\\" in base:
        raise FeedConfigError("base must not contain a backslash")
    _reject_control_and_space(base, "base")
    if "?" in base or "#" in base:
        raise FeedConfigError("base must not carry a query string or a fragment")

    try:
        parts = urllib.parse.urlsplit(base)
    except ValueError as exc:
        raise FeedConfigError(f"base is not a parseable URL: {exc}") from exc
    if parts.scheme != "https":
        raise FeedConfigError("base must be an absolute https:// URL")
    if not parts.netloc or not parts.hostname:
        raise FeedConfigError("base must include a host")
    if "@" in parts.netloc:
        raise FeedConfigError("base must not carry userinfo")
    try:
        port = parts.port
    except ValueError as exc:
        raise FeedConfigError(f"base carries an invalid port: {exc}") from exc
    if port is not None and port != 443:
        raise FeedConfigError("base port must be 443 when a port is supplied")
    host = parts.hostname
    if not (_HOSTNAME_RE.match(host) or _IPV6_RE.match(host)):
        raise FeedConfigError(f"base host is not a plain hostname: {host!r}")

    path = parts.path
    if path and not path.startswith("/"):
        raise FeedConfigError("base path must be absolute")
    for segment in path.split("/"):
        if segment in (".", ".."):
            raise FeedConfigError("base path must not contain '.' or '..' segments")
    return f"{parts.scheme}://{parts.netloc}{path.rstrip('/')}"


def _normalise_name(name: str) -> str:
    """Validate a feed name and return it unchanged.

    A name is a flat ASCII ``.json`` basename. The regular expression is the
    whole of the character policy: it admits only ``[A-Za-z0-9]``, ``_``, ``.``
    and ``-``, so a slash, a percent sign, a query, or a fragment cannot be
    spelled at all, and a name can never climb out of the ``feeds/`` prefix.
    """
    if not isinstance(name, str):
        raise FeedConfigError(f"name must be a string, got {type(name).__name__}")
    if not _NAME_RE.match(name):
        raise FeedConfigError(
            "name must match [A-Za-z0-9][A-Za-z0-9_.-]{0,255} "
            "(flat ASCII basename, no path, no percent, no query, no fragment)"
        )
    if not name.endswith(".json"):
        raise FeedConfigError("name must end with '.json'")
    if ".." in name:
        raise FeedConfigError("name must not contain '..'")
    return name


def _validate_cap(max_bytes: int) -> int:
    """Validate the caller's byte cap."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise FeedConfigError(f"max_bytes must be an int, got {type(max_bytes).__name__}")
    if max_bytes <= 0:
        raise FeedConfigError("max_bytes must be a positive integer")
    if max_bytes > _MAX_BYTES_CEILING:
        raise FeedConfigError(f"max_bytes must not exceed {_MAX_BYTES_CEILING} bytes")
    return max_bytes


def _status_of(response) -> int | None:
    """Return the response status, or None when the response carries none."""
    status = getattr(response, "status", None)
    if status is None:
        getter = getattr(response, "getcode", None)
        if callable(getter):
            status = getter()
    if status is None:
        return None
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def _declared_length(response) -> int | None:
    """Return the declared ``Content-Length``, or None when the header is absent.

    A declared length that is malformed or negative is refused rather than
    ignored: a header the server got wrong is a framing failure, and treating
    it as "absent" would let a broken response through as a good one.
    """
    headers = getattr(response, "headers", None)
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    raw = getter("Content-Length")
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise FeedFetchError("Content-Length is not ASCII") from exc
    text = str(raw).strip()
    if not text:
        raise FeedFetchError("Content-Length is empty")
    if text.startswith("-"):
        raise FeedFetchError(f"Content-Length is negative: {text!r}")
    if not _DIGITS_RE.match(text):
        raise FeedFetchError(f"Content-Length is malformed: {text!r}")
    return int(text)


def _read_bounded(response, cap: int) -> bytes:
    """Read at most ``cap + 1`` bytes and return them if they fit the cap.

    The extra byte is the probe: if it materialises, the body is over the cap
    and the read is refused. Reading one byte past the cap is enough to know
    the body is too large, and it bounds what a hostile response can pull
    into memory.
    """
    limit = cap + 1
    buffer = bytearray()
    while len(buffer) < limit:
        chunk = response.read(limit - len(buffer))
        if not chunk:
            break
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise FeedFetchError(f"feed body was not bytes, got {type(chunk).__name__}")
        buffer += chunk
    if len(buffer) > cap:
        raise FeedFetchError(f"feed body exceeds the {cap}-byte cap")
    return bytes(buffer)


class FixedFeedReader:
    """One request-local reader bound to a single configured feed origin.

    ``base`` is the TRUSTED deployment base -- the value of ``config.yml``'s
    ``r2_data_plane.public_base`` -- supplied by the caller. The reader never
    reads the environment, the config file, or a request body to find it.

    The base contract is fixed and is not guessed at read time: ``base`` is
    the bucket origin (or a prefix root), and the reader ALWAYS appends
    ``/feeds/`` plus the feed name below it. A base that already ends in
    ``/feeds`` therefore reads ``.../feeds/feeds/<name>``: the base is the
    caller's value and the reader does not silently rewrite it.
    """

    __slots__ = ("_base",)

    def __init__(self, base: str) -> None:
        self._base = _normalise_base(base)

    @property
    def base(self) -> str:
        """The validated, normalised base this reader is bound to."""
        return self._base

    def read(self, name: str, *, max_bytes: int) -> bytes:
        """Fetch one named feed and return its exact bytes.

        The body is returned verbatim: not parsed, not re-encoded, not
        hashed. Raises :class:`FeedConfigError` when the name or the cap is
        unusable, and :class:`FeedFetchError` when the fetch itself fails --
        transport error, timeout, non-200 status, refused redirect, malformed
        framing, or a body over the cap.
        """
        cap = _validate_cap(max_bytes)
        safe_name = _normalise_name(name)
        url = f"{self._base}/{_FEEDS_SEGMENT}/{safe_name}"
        request = urllib.request.Request(url, method="GET", headers=dict(_REQUEST_HEADERS))

        opener = _OPENER
        try:
            response = opener.open(request, timeout=_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            # The refusing redirect handler raises here for every 3xx, and
            # urllib raises for every other non-2xx status. The error object
            # is itself a response: close it so its body cannot leak.
            with exc:
                if 300 <= exc.code < 400:
                    raise FeedFetchError(
                        f"refusing redirect ({exc.code}) for feed {safe_name!r}"
                    ) from exc
                raise FeedFetchError(
                    f"feed {safe_name!r} returned HTTP {exc.code}"
                ) from exc
        except (OSError, http.client.HTTPException) as exc:
            # URLError (DNS, connection, TLS) and socket timeouts are OSError
            # subclasses; http.client carries the protocol-level failures.
            raise FeedFetchError(
                f"feed {safe_name!r} could not be fetched: {exc}"
            ) from exc

        with response:
            status = _status_of(response)
            if status is None:
                raise FeedFetchError(f"feed {safe_name!r} response carried no status")
            if 300 <= status < 400:
                raise FeedFetchError(f"refusing redirect ({status}) for feed {safe_name!r}")
            if status != 200:
                raise FeedFetchError(f"feed {safe_name!r} returned HTTP {status}")
            declared = _declared_length(response)
            if declared is not None and declared > cap:
                raise FeedFetchError(
                    f"feed {safe_name!r} declares {declared} bytes, above the {cap}-byte cap"
                )
            # A declared length at or below the cap is never trusted: the body
            # is measured against the cap, not believed.
            return _read_bounded(response, cap)
