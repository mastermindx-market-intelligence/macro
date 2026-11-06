"""M2 EDGAR access: rate-limited fetch, integrity-checked cache, index headers.

Network layer for the relationship harvester only.  The cache lives outside the
repo (``$GMI_EDGAR_CACHE``, default ``~/.cache/gmi_edgar``); a cached body is
used only when it still hashes to its own meta record.  Hashes are always taken
over the DECODED body (the bytes ``replay.replay_fetch`` sees).  The rate
limiter's clock and sleep are injectable so tests never really wait.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "MastermindX GMI-REL data@mastermind-x.com"

RETRY_STATUSES = {429, 500, 502, 503, 504}
NO_RETRY_STATUSES = {404, 403, 410}
RETRY_BACKOFF_SECONDS = (2.0, 4.0, 8.0)
DEFAULT_RPS = 3.0
MAX_RPS = 8.0

_EDGAR_BASE = "https://www.sec.gov/Archives/edgar/data"


class HttpError(Exception):
    """A terminal HTTP status (no retry is permitted)."""

    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url


class NetworkError(Exception):
    """Retries exhausted on a transient failure."""

    def __init__(self, url: str, cause: str):
        super().__init__(f"network failed for {url}: {cause}")
        self.url = url
        self.cause = cause


class NetworkDisabled(Exception):
    """GMI_EDGAR_OFFLINE is set and the body is not cached."""

    def __init__(self, url: str):
        super().__init__(f"network disabled and not cached: {url}")
        self.url = url


class FetchResult:
    """Decoded body plus its cache meta record."""

    __slots__ = ("body", "state", "meta")

    def __init__(self, body: bytes, state: str, meta: dict):
        self.body = body
        self.state = state  # fetched | cached
        self.meta = meta


class RateLimiter:
    """One process-wide limiter: at most ``rps`` requests per second."""

    def __init__(self, rps: float = DEFAULT_RPS, clock=time.monotonic,
                 sleep=time.sleep):
        self.min_interval = 1.0 / min(max(rps, 0.1), MAX_RPS)
        self._clock = clock
        self._sleep = sleep
        self._next_ok = 0.0

    def wait(self) -> None:
        now = self._clock()
        delay = self._next_ok - now
        if delay > 0:
            self._sleep(delay)
            now = self._clock()
        self._next_ok = now + self.min_interval


class EdgarCache:
    """<root>/<cik>/<accession_nodash>/<filename> plus .meta.json records."""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)

    def path_for(self, cik: int, accession_nodash: str, filename: str) -> Path:
        return self.root / str(int(cik)) / accession_nodash / filename

    def load(self, cik: int, accession_nodash: str, filename: str):
        """(body, meta, integrity_ok); (None, None, True) on a miss."""
        path = self.path_for(cik, accession_nodash, filename)
        meta_path = Path(str(path) + ".meta.json")
        if not path.exists() or not meta_path.exists():
            return None, None, True
        try:
            body = path.read_bytes()
            meta = json_loads(meta_path.read_bytes())
        except (OSError, ValueError):
            return None, None, True
        integrity_ok = hashlib.sha256(body).hexdigest() == meta.get("sha256")
        return body, meta, integrity_ok

    def store(self, cik: int, accession_nodash: str, filename: str, body: bytes,
              url: str, http_status: int, fetched_at: str) -> dict:
        path = self.path_for(cik, accession_nodash, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        meta = {
            "url": url,
            "sha256": hashlib.sha256(body).hexdigest(),
            "byte_length": len(body),
            "http_status": http_status,
            "fetched_at": fetched_at,
        }
        Path(str(path) + ".meta.json").write_bytes(json_dumps(meta))
        return meta


def json_dumps(obj) -> bytes:
    import json

    return (json.dumps(obj, sort_keys=True) + "\n").encode("utf-8")


def json_loads(raw: bytes):
    import json

    return json.loads(raw.decode("utf-8"))


def index_headers_url(cik: int, accession: str) -> str:
    nodash = accession.replace("-", "")
    return f"{_EDGAR_BASE}/{int(cik)}/{nodash}/{accession}-index-headers.html"


def document_url(cik: int, accession: str, filename: str) -> str:
    nodash = accession.replace("-", "")
    return f"{_EDGAR_BASE}/{int(cik)}/{nodash}/{filename}"


def _default_opener(url: str, headers: dict):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return (
            response.status if hasattr(response, "status") else 200,
            dict(response.headers.items()) if hasattr(response, "headers") else {},
            response.read(),
        )


class EdgarClient:
    """Fetch + cache with retries; every dependency is injectable."""

    def __init__(self, cache_root: str | None = None, rps: float = DEFAULT_RPS,
                 clock=time.monotonic, sleep=time.sleep, opener=None,
                 offline: bool | None = None, now_utc=None):
        if cache_root is None:
            cache_root = os.environ.get("GMI_EDGAR_CACHE") or os.path.expanduser(
                "~/.cache/gmi_edgar"
            )
        self.cache = EdgarCache(cache_root)
        self.limiter = RateLimiter(rps=rps, clock=clock, sleep=sleep)
        self._clock = clock
        self._sleep = sleep
        self._opener = opener or _default_opener
        self._now_utc = now_utc or (lambda: time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        ))
        if offline is None:
            offline = os.environ.get("GMI_EDGAR_OFFLINE") == "1"
        self.offline = bool(offline)
        self.counters = {"cache_integrity_refetch": 0}

    def _fetch_network(self, url: str) -> tuple:
        """(body, status) with the retry/backoff contract; raises otherwise."""
        attempt = 0
        while True:
            self.limiter.wait()
            try:
                status, headers, raw = self._opener(
                    url, {"User-Agent": USER_AGENT}
                )
            except urllib.error.HTTPError as error:
                status, headers, raw = error.code, {}, error.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt < len(RETRY_BACKOFF_SECONDS):
                    self._sleep(RETRY_BACKOFF_SECONDS[attempt])
                    attempt += 1
                    continue
                raise NetworkError(url, str(error)) from error
            if status == 200:
                body = raw
                if "gzip" in str(headers.get("Content-Encoding", "")).lower():
                    body = gzip.decompress(raw)
                return body, status
            if status in NO_RETRY_STATUSES:
                raise HttpError(status, url)
            if (
                status == 429 or 500 <= status < 600
            ) and attempt < len(RETRY_BACKOFF_SECONDS):
                self._sleep(RETRY_BACKOFF_SECONDS[attempt])
                attempt += 1
                continue
            raise HttpError(status, url)

    def fetch(self, cik: int, accession_nodash: str, filename: str,
              cache_filename: str | None = None) -> FetchResult:
        """Cached-when-valid, else network; offline misses fail disabled."""
        store_name = cache_filename or filename
        body, meta, integrity_ok = self.cache.load(
            cik, accession_nodash, store_name
        )
        if body is not None and integrity_ok:
            return FetchResult(body, "cached", meta)
        url = (
            index_headers_url(int(cik), _redash(accession_nodash))
            if store_name.endswith("-index-headers.html")
            else document_url(int(cik), accession_nodash, filename)
        )
        if self.offline:
            raise NetworkDisabled(url)
        if body is not None and not integrity_ok:
            self.counters["cache_integrity_refetch"] += 1
        fresh, status = self._fetch_network(url)
        fetched_at = self._now_utc()
        new_meta = self.cache.store(
            int(cik), accession_nodash, store_name, fresh, url, status, fetched_at
        )
        return FetchResult(fresh, "fetched", new_meta)


def _redash(accession_nodash: str) -> str:
    if "-" in accession_nodash:
        return accession_nodash
    return f"{accession_nodash[:10]}-{accession_nodash[10:12]}-{accession_nodash[12:]}"


_ACCEPTANCE_RE = re.compile(r"<ACCEPTANCE-DATETIME>\s*(\d{14})")
_SUBMISSION_TYPE_RE = re.compile(r"CONFORMED SUBMISSION TYPE:\s*(\S+)")
_PERIOD_RE = re.compile(r"CONFORMED PERIOD OF REPORT:\s*(\d{8})")
_FILED_RE = re.compile(r"FILED AS OF DATE:\s*(\d{8})")
_PRE_RE = re.compile(r"<pre>(.*?)</pre>", re.S | re.I)
_DOC_BLOCK_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
_DOC_TYPE_RE = re.compile(r"<TYPE>\s*(\S+)")
_DOC_SEQ_RE = re.compile(r"<SEQUENCE>\s*(\d+)")
_DOC_FILENAME_RE = re.compile(r"<FILENAME>\s*(\S+)")


def _date(text: str) -> str:
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def parse_index_headers(raw: bytes) -> dict:
    """Parse one <accession>-index-headers.html body (H1).

    The readable header is re-parsed from its ``<pre>`` region after entity
    unescaping, so the SGML comment copy can never double the document list.
    """
    text = html.unescape(raw.decode("utf-8", errors="replace"))
    pre = _PRE_RE.search(text)
    segment = pre.group(1) if pre else text
    acceptance = _ACCEPTANCE_RE.search(segment)
    submission = _SUBMISSION_TYPE_RE.search(segment)
    period = _PERIOD_RE.search(segment)
    filed = _FILED_RE.search(segment)
    documents = []
    for block in _DOC_BLOCK_RE.finditer(segment):
        doc_type = _DOC_TYPE_RE.search(block.group(1))
        filename = _DOC_FILENAME_RE.search(block.group(1))
        sequence = _DOC_SEQ_RE.search(block.group(1))
        if doc_type is None or filename is None:
            continue
        documents.append(
            {
                "type": doc_type.group(1),
                "filename": filename.group(1),
                "sequence": sequence.group(1) if sequence else None,
            }
        )
    return {
        "acceptance_et": acceptance.group(1) if acceptance else None,
        "submission_type": submission.group(1) if submission else None,
        "period_of_report": _date(period.group(1)) if period else None,
        "filed_as_of_date": _date(filed.group(1)) if filed else None,
        "documents": documents,
    }
