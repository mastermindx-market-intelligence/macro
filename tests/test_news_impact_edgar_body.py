"""Tests for ``engine.news_impact.edgar_body`` — issuer 8-K body minting.

Every test uses fakes (no network).  The real ``SecFilingArchiveCollector`` is
constructed with a ``FakeSession`` so its bounded-streaming and persistence
behaviour is exercised end to end.  Forensics is a duck-typed fake except in
the dedicated T8 sub-test, which also runs once with the real
``SecForensicsCollector`` over a fake session.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import io
import json
import re
import sys

import pytest

from collectors.edgar_forensics import SecForensicsCollector
from collectors.sec_document_spine import (
    SecFilingArchiveCollector,
    read_archive_document,
)
from collectors.sec_request_pacer import SecRequestPacer
from engine.company_intelligence.documents import (
    DocumentError,
    text_span,
    verify_span,
)
from engine.news_impact import edgar_body as eb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _weekday_sessions(start: date, end: date) -> list[date]:
    out: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            out.append(current)
        current = date.fromordinal(current.toordinal() + 1)
    return out


SESSIONS: list[date] = _weekday_sessions(date(2026, 9, 8), date(2026, 10, 9))


USER_AGENT = "Prophet Test test@example.com"
RETRIEVED_AT = "2026-10-14T00:00:00Z"


@dataclass
class _Counter:
    value: int = 0

    def __call__(self) -> float:
        self.value += 1
        return float(self.value)


def _make_pacer() -> SecRequestPacer:
    return SecRequestPacer(
        min_interval_seconds=0.1,
        sleeper=lambda seconds: None,
        monotonic=_Counter(),
    )


class _Response:
    """One streamed response compatible with both SEC collectors."""

    def __init__(
        self,
        body: bytes = b"",
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers: dict[str, str] = {"Content-Length": str(len(body))}
        if headers:
            self.headers.update(headers)
        self.url = ""
        self.closed = False
        self.iter_chunk_sizes: list[int] = []

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 65536):
        self.iter_chunk_sizes.append(chunk_size)
        body = self._body
        for offset in range(0, len(body), chunk_size):
            yield body[offset : offset + chunk_size]

    def close(self) -> None:
        self.closed = True


class FakeSession:
    """A ``requests.Session``-like fake that records every URL it serves."""

    def __init__(self, routes: dict[str, bytes | BaseException] | None = None) -> None:
        self.routes: dict[str, bytes | BaseException] = dict(routes or {})
        self.calls: list[str] = []
        self.url_counts: dict[str, int] = {}

    def add(self, url: str, body: bytes | BaseException) -> None:
        self.routes[url] = body

    def get(self, url: str, **kwargs):
        self.calls.append(url)
        self.url_counts[url] = self.url_counts.get(url, 0) + 1
        if url not in self.routes:
            raise AssertionError(f"FakeSession: no route for {url!r}")
        route = self.routes[url]
        if isinstance(route, BaseException):
            raise route
        response = _Response(body=route, status_code=200)
        response.url = url
        return response


class FakeForensics:
    """Duck-typed forensics used everywhere except T8's real-collector sub-test."""

    def __init__(
        self,
        current: dict[str, dict | Exception] | None = None,
        shards: dict[str, dict] | None = None,
    ) -> None:
        self.current = dict(current or {})
        self.shards = dict(shards or {})
        self.current_calls = 0
        self.shard_calls: list[str] = []

    def retrieve_current(self, cik10: str, endpoint: str):
        assert endpoint == "submissions", endpoint
        self.current_calls += 1
        value = self.current.get(cik10)
        if isinstance(value, BaseException):
            raise value
        if value is None:
            raise RuntimeError(f"FakeForensics: no current payload for {cik10!r}")
        return json.dumps(value).encode("utf-8"), {
            "url": f"https://data.sec.gov/submissions/CIK{cik10}.json",
            "http_etag": '"fake"',
            "http_last_modified": "Wed, 14 Oct 2026 00:00:00 GMT",
        }

    def retrieve_historical_submissions_file(self, cik10: str, name: str):
        key = (cik10, name)
        self.shard_calls.append(name)
        value = self.shard_calls_indexed(key)
        if isinstance(value, BaseException):
            raise value
        if value is None:
            raise RuntimeError(
                f"FakeForensics: no shard payload for CIK {cik10!r} name {name!r}"
            )
        return json.dumps(value).encode("utf-8"), {
            "url": f"https://data.sec.gov/submissions/{name}",
            "http_etag": '"shard"',
            "http_last_modified": "Wed, 14 Oct 2026 00:00:00 GMT",
        }

    def shard_calls_indexed(self, key: tuple[str, str]):
        name = key[1]
        if name in self.shard_calls_as_exceptions:
            return self.shard_calls_as_exceptions[name]
        return self.shards.get(name)

    shard_calls_as_exceptions: dict[str, BaseException]


FakeForensics.shard_calls_as_exceptions = {}


# ---------------------------------------------------------------------------
# Index/page builders
# ---------------------------------------------------------------------------


def _index_html(rows: list[tuple[str, str, str, str, str]]) -> bytes:
    """Build a synthetic EDGAR filing index page.

    Each row is ``(seq, description, filename_or_href, doc_type, extra)`` where
    ``extra`` is appended verbatim into cell 2 (used to add /ix?doc= prefixes).
    """
    body_rows: list[str] = []
    for seq, description, filename_or_href, doc_type, extra in rows:
        body_rows.append(
            "<tr>"
            f"<td scope=\"row\">{seq}</td>"
            f"<td scope=\"row\">{description}</td>"
            f"<td scope=\"row\"><a href=\"{filename_or_href}\">{filename_or_href.split('/')[-1]}</a>{extra}</td>"
            f"<td scope=\"row\">{doc_type}</td>"
            "<td scope=\"row\">1234</td>"
            "</tr>"
        )
    header = (
        "<tr>"
        "<th scope=\"col\">Seq</th>"
        "<th scope=\"col\">Description</th>"
        "<th scope=\"col\">Document</th>"
        "<th scope=\"col\">Type</th>"
        "<th scope=\"col\">Size</th>"
        "</tr>"
    )
    html = (
        "<html><body>"
        "<table summary=\"Document Format Files\">"
        + header
        + "".join(body_rows)
        + "</table>"
        "</body></html>"
    )
    return html.encode("utf-8")


def _make_archive(
    tmp_path: Path, session: FakeSession, *, pacer: SecRequestPacer,
    utc_now=None,
) -> SecFilingArchiveCollector:
    return SecFilingArchiveCollector(
        tmp_path / "archive",
        user_agent=USER_AGENT,
        session=session,
        sleeper=lambda seconds: None,
        monotonic=_Counter(),
        utc_now=utc_now or (lambda: "2026-10-14T00:00:00Z"),
        pacer=pacer,
    )


def _wire_routes(
    session: FakeSession,
    cik10: str,
    accession: str,
    primary_filename: str,
    primary_body: bytes,
    exhibit_bodies: dict[str, bytes] | None = None,
) -> dict[str, bytes]:
    """Populate the fake session with index + primary + exhibits; return routes."""
    exhibit_bodies = exhibit_bodies or {}
    index_url = eb.index_url(cik10, accession)
    primary_url = eb.document_url(cik10, accession, primary_filename)
    routes: dict[str, bytes] = {}
    rows: list[tuple[str, str, str, str, str]] = [
        (
            "1",
            "8-K",
            primary_filename,
            "8-K",
            " &nbsp;&nbsp;<span class=\"small\">iXBRL</span>",
        )
    ]
    seq = 2
    for exhibit_name in exhibit_bodies:
        rows.append((str(seq), "EX-99.1", exhibit_name, "EX-99.1", ""))
        seq += 1
    routes[index_url] = _index_html(rows)
    routes[primary_url] = primary_body
    for name, body in exhibit_bodies.items():
        routes[eb.document_url(cik10, accession, name)] = body
    session.routes.update(routes)
    return routes


# ---------------------------------------------------------------------------
# T1 - parse_issuer_cik
# ---------------------------------------------------------------------------


def test_parse_issuer_cik():
    assert eb.parse_issuer_cik("cik:0000320193") == "0000320193"
    assert eb.parse_issuer_cik("unresolved:no_mention") is None
    assert eb.parse_issuer_cik("cik:123") is None
    assert eb.parse_issuer_cik("") is None
    assert eb.parse_issuer_cik("cik:0000320193a") is None
    assert eb.parse_issuer_cik(None) is None


# ---------------------------------------------------------------------------
# T2 - session_window
# ---------------------------------------------------------------------------


def test_session_window_basic():
    # Saturday 2026-09-19 -> (09-18, 09-21, 09-22)
    assert eb.session_window("2026-09-19T15:00:00Z", SESSIONS) == (
        date(2026, 9, 18),
        date(2026, 9, 21),
        date(2026, 9, 22),
    )
    # 2026-09-16T02:00Z is 22:00 ET on 2026-09-15 -> (09-14, 09-15, 09-16)
    assert eb.session_window("2026-09-16T02:00:00Z", SESSIONS) == (
        date(2026, 9, 14),
        date(2026, 9, 15),
        date(2026, 9, 16),
    )


def test_session_window_edges_and_errors():
    # First session, no previous
    assert eb.session_window("2026-09-08T15:00:00Z", SESSIONS) is None
    # After the last session
    assert eb.session_window("2026-12-01T15:00:00Z", SESSIONS) is None
    # Naive datetime
    with pytest.raises(eb.EdgarBodyError):
        eb.session_window("2026-09-10T00:00:00", SESSIONS)
    # Datetime instance without tzinfo
    with pytest.raises(eb.EdgarBodyError):
        eb.session_window(datetime(2026, 9, 10, 12, 0), SESSIONS)


def test_validate_sessions_errors():
    with pytest.raises(eb.EdgarBodyError):
        eb.validate_sessions([date(2026, 9, 8), date(2026, 9, 9)])
    with pytest.raises(eb.EdgarBodyError):
        eb.validate_sessions(
            [date(2026, 9, 8), date(2026, 9, 10), date(2026, 9, 9)]
        )
    with pytest.raises(eb.EdgarBodyError):
        eb.validate_sessions(
            [datetime(2026, 9, 8, 12), date(2026, 9, 9), date(2026, 9, 10)]
        )
    # Too short
    with pytest.raises(eb.EdgarBodyError):
        eb.validate_sessions([date(2026, 9, 8)])


# ---------------------------------------------------------------------------
# T3 - parse_submissions / older_shards
# ---------------------------------------------------------------------------


def _recent_payload(rows: list[dict]) -> dict:
    return {
        "cik": "0000320193",
        "filings": {
            "recent": {
                "accessionNumber": [r["accession"] for r in rows],
                "filingDate": [r["filingDate"] for r in rows],
                "form": [r["form"] for r in rows],
                "items": [r.get("items", "") for r in rows],
                "primaryDocument": [r["primaryDocument"] for r in rows],
            },
            "files": [
                {"name": "CIK0000320193-submissions-001.json", "filingFrom": "2026-07-01", "filingTo": "2026-07-31"}
            ],
        },
    }


def _shard_payload(rows: list[dict]) -> dict:
    return {
        "cik": "0000320193",
        "accessionNumber": [r["accession"] for r in rows],
        "filingDate": [r["filingDate"] for r in rows],
        "form": [r["form"] for r in rows],
        "items": [r.get("items", "") for r in rows],
        "primaryDocument": [r["primaryDocument"] for r in rows],
    }


def test_parse_submissions_recent_and_shard():
    recent = _recent_payload(
        [
            {
                "accession": "0000320193-26-000010",
                "filingDate": "2026-09-15",
                "form": "8-K",
                "items": "2.02,9.01",
                "primaryDocument": "aapl-20260915.htm",
            }
        ]
    )
    rows = eb.parse_submissions(recent)
    assert len(rows) == 1
    assert rows[0].accession == "0000320193-26-000010"
    assert rows[0].form == "8-K"
    assert rows[0].items == ("2.02", "9.01")
    assert rows[0].filing_date == date(2026, 9, 15)

    shard = _shard_payload(
        [
            {
                "accession": "0000320193-25-000005",
                "filingDate": "2025-08-10",
                "form": "8-K",
                "items": "5.02",
                "primaryDocument": "aapl-20250810.htm",
            }
        ]
    )
    rows = eb.parse_submissions(shard)
    assert rows[0].accession == "0000320193-25-000005"

    # older_shards
    shards = eb.older_shards(recent)
    assert shards == [
        (
            "CIK0000320193-submissions-001.json",
            date(2026, 7, 1),
            date(2026, 7, 31),
        )
    ]
    assert eb.older_shards(shard) == []


def test_parse_submissions_errors():
    with pytest.raises(eb.EdgarBodyError):
        eb.parse_submissions(
            {
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-26-000010", "0000320193-26-000011"],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": [""],
                        "primaryDocument": ["a.htm"],
                    }
                }
            }
        )
    with pytest.raises(eb.EdgarBodyError):
        eb.parse_submissions(
            {
                "filings": {
                    "recent": {
                        "accessionNumber": ["bad-accession"],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": [""],
                        "primaryDocument": ["a.htm"],
                    }
                }
            }
        )


# ---------------------------------------------------------------------------
# T4 - qualifying_filings
# ---------------------------------------------------------------------------


def _row(accession, filing_date, form, items, primary="p.htm"):
    return eb.FilingRow(
        accession=accession,
        filing_date=date.fromisoformat(filing_date),
        form=form,
        items=tuple(items.split(",")) if items else (),
        primary_document=primary,
    )


def test_qualifying_filings():
    window = (date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 16))
    rows = [
        _row("0000320193-26-000001", "2026-09-15", "8-K", "2.02,9.01"),
        _row("0000320193-26-000002", "2026-09-15", "8-K", "5.02"),
        _row("0000320193-26-000003", "2026-09-15", "8-K/A", "2.02"),
        _row("0000320193-26-000004", "2026-09-15", "10-Q", "2.02"),
        _row("0000320193-26-000005", "2026-09-10", "8-K", "2.02"),  # out of window
    ]
    kept, truncated = eb.qualifying_filings(rows, window)
    assert truncated == 0
    assert [r.accession for r in kept] == ["0000320193-26-000001"]


def test_qualifying_filings_cap_and_ordering():
    window = (date(2026, 9, 12), date(2026, 9, 15), date(2026, 9, 16))
    rows = [
        _row("0000320193-26-000010", "2026-09-14", "8-K", "2.02"),  # d=-1
        _row("0000320193-26-000011", "2026-09-15", "8-K", "2.02"),  # d=0
        _row("0000320193-26-000012", "2026-09-16", "8-K", "2.02"),  # d=+1
        _row("0000320193-26-000013", "2026-09-12", "8-K", "2.02"),  # d=-3
    ]
    kept, truncated = eb.qualifying_filings(rows, window)
    assert len(kept) == 3
    assert truncated == 1
    # Closest to window[1] is 09-15 (d=0); then 09-14 and 09-16 (d=1); 09-12 is dropped (d=3).
    accessions = [r.accession for r in kept]
    assert accessions[0] == "0000320193-26-000011"
    assert sorted(accessions[1:]) == [
        "0000320193-26-000010",
        "0000320193-26-000012",
    ]


# ---------------------------------------------------------------------------
# T5 - parse_filing_index
# ---------------------------------------------------------------------------


def test_parse_filing_index_basic():
    html = (
        "<html><body>"
        "<table summary=\"Document Format Files\">"
        "<tr><th scope=\"col\">Seq</th><th scope=\"col\">Desc</th><th scope=\"col\">Doc</th><th scope=\"col\">Type</th><th scope=\"col\">Size</th></tr>"
        "<tr><td scope=\"row\">1</td><td scope=\"row\">8-K</td><td scope=\"row\"><a href=\"/ix?doc=/Archives/edgar/data/320193/000032019326000005/aapl-20260130.htm\">aapl-20260130.htm</a> &nbsp;&nbsp;<span class=\"small\">iXBRL</span></td><td scope=\"row\">8-K</td><td scope=\"row\">39741</td></tr>"
        "<tr><td scope=\"row\">2</td><td scope=\"row\">EX-99.1</td><td scope=\"row\"><a href=\"/Archives/edgar/data/320193/000032019326000005/ex99-1.htm\">ex99-1.htm</a></td><td scope=\"row\">EX-99.1</td><td scope=\"row\">1024</td></tr>"
        "<tr><td scope=\"row\">3</td><td scope=\"row\">GRAPHIC</td><td scope=\"row\"><a href=\"/Archives/edgar/data/320193/000032019326000005/g1.jpg\">g1.jpg</a></td><td scope=\"row\">GRAPHIC</td><td scope=\"row\">1234</td></tr>"
        "<tr><td scope=\"row\">4</td><td scope=\"row\">EX-101.SCH</td><td scope=\"row\"><a href=\"/Archives/edgar/data/320193/000032019326000005/sch.xsd\">sch.xsd</a></td><td scope=\"row\">EX-101.SCH</td><td scope=\"row\">42</td></tr>"
        "</table>"
        "</body></html>"
    )
    docs = eb.parse_filing_index(html)
    assert [d.filename for d in docs] == ["aapl-20260130.htm", "ex99-1.htm", "g1.jpg", "sch.xsd"]
    assert [d.doc_type for d in docs] == ["8-K", "EX-99.1", "GRAPHIC", "EX-101.SCH"]


def test_parse_filing_index_no_matching_table():
    assert eb.parse_filing_index("<html><body><p>nothing</p></body></html>") == []


# ---------------------------------------------------------------------------
# T6 - select_body_documents
# ---------------------------------------------------------------------------


def test_select_body_documents_ordering_and_cap():
    primary = eb.IndexDocument(seq="1", description="8-K", filename="p.htm", doc_type="8-K")
    ex991 = eb.IndexDocument(seq="2", description="EX-99.1", filename="e1.htm", doc_type="EX-99.1")
    ex992 = eb.IndexDocument(seq="3", description="EX-99.2", filename="e2.htm", doc_type="EX-99.2")
    ex993 = eb.IndexDocument(seq="4", description="EX-99.3", filename="e3.htm", doc_type="EX-99.3")
    ex994 = eb.IndexDocument(seq="5", description="EX-99.4", filename="e4.htm", doc_type="EX-99.4")
    graphic = eb.IndexDocument(seq="6", description="GRAPHIC", filename="g.jpg", doc_type="GRAPHIC")
    sch = eb.IndexDocument(seq="7", description="SCH", filename="s.xsd", doc_type="EX-101.SCH")
    out = eb.select_body_documents(
        [primary, ex991, ex992, graphic, sch, ex993, ex994], "p.htm"
    )
    assert [d.filename for d in out] == ["p.htm", "e1.htm", "e2.htm", "e3.htm"]


def test_select_body_documents_primary_fallback():
    primary_missing = eb.IndexDocument(seq="1", description="WRAP", filename="w.htm", doc_type="COVER")
    first_8k = eb.IndexDocument(seq="2", description="8-K", filename="x.htm", doc_type="8-K")
    out = eb.select_body_documents([primary_missing, first_8k], "missing.htm")
    assert [d.filename for d in out] == ["x.htm"]


def test_select_body_documents_nothing_usable():
    out = eb.select_body_documents(
        [eb.IndexDocument(seq="1", description="G", filename="g.jpg", doc_type="GRAPHIC")],
        "missing.htm",
    )
    assert out == []


# ---------------------------------------------------------------------------
# T7 - html_to_text
# ---------------------------------------------------------------------------


def test_html_to_text_spec_example():
    raw = (
        b"<html><head><style>p{}</style></head>"
        b"<body><p>Revenue&nbsp;rose&amp;fell</p>"
        b"<script>x()</script><div>Q3   2026</div></body></html>"
    )
    assert eb.html_to_text(raw) == "Revenue rose&fell\nQ3 2026"


def test_html_to_text_ix_header_and_comment():
    raw = (
        b"<html><body><!-- hidden -->"
        b"<ix:header>nope</ix:header>"
        b"<p>Hello&nbsp;World</p></body></html>"
    )
    assert eb.html_to_text(raw) == "Hello World"


def test_html_to_text_cp1252():
    # 0x93 / 0x94 are curly quotes in cp1252
    assert eb.html_to_text(b"\x93Hi\x94") == "“Hi”"


def test_html_to_text_empty():
    assert eb.html_to_text(b"<html><script>x</script></html>") == ""


# ---------------------------------------------------------------------------
# T8 - end to end
# ---------------------------------------------------------------------------


def _run_e2e(
    tmp_path: Path,
    *,
    use_real_forensics: bool,
    cik10: str = "0000320193",
    seendate: str = "2026-09-15T15:00:00Z",
    primary_body: bytes = b"<html><body><p>Revenue rose 12% in Q3 2026.</p></body></html>",
    exhibit_body: bytes = b"<html><body><p>Exhibit details follow.</p></body></html>",
    primary_filename: str = "aapl-20260915.htm",
    exhibit_filename: str = "ex99-1.htm",
    case_index_recent: dict | None = None,
    forensics: FakeForensics | None = None,
) -> tuple[dict, list[dict], dict, FakeSession]:
    if case_index_recent is None:
        case_index_recent = {
            "accessionNumber": ["0000320193-26-000010"],
            "filingDate": ["2026-09-15"],
            "form": ["8-K"],
            "items": ["2.02"],
            "primaryDocument": [primary_filename],
        }
    accession = case_index_recent["accessionNumber"][0]
    session = FakeSession()
    routes = _wire_routes(
        session,
        cik10,
        accession,
        primary_filename,
        primary_body,
        exhibit_bodies={exhibit_filename: exhibit_body},
    )
    pacer = _make_pacer()
    archive = _make_archive(tmp_path, session, pacer=pacer)
    if use_real_forensics:
        # Real collector over a fake session: route the current submissions URL
        current_url = "https://data.sec.gov/submissions/CIK0000320193.json"
        session.add(current_url, json.dumps(case_index_recent).encode("utf-8"))
        forensics_collector = SecForensicsCollector(
            tmp_path / "forensics",
            user_agent=USER_AGENT,
            session=session,
            pacer=pacer,
        )
    else:
        assert forensics is not None
        forensics_collector = forensics
    case = {
        "item_id": "case-001",
        "issuer": f"cik:{cik10}",
        "template": "t",
        "proxy_cell": "c",
        "group_id": "g",
        "fold": "0",
        "source_sha256": "a" * 64,
        "seendate": seendate,
        "tags": [],
    }
    status_map, records, report = eb.fetch_bodies(
        [case],
        forensics=forensics_collector,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    return status_map, records, report, session


def test_end_to_end_available_with_fake_forensics(tmp_path):
    forensics = FakeForensics(
        current={
            "0000320193": {
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-26-000010"],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": ["aapl-20260915.htm"],
                    }
                }
            }
        }
    )
    status_map, records, report, _ = _run_e2e(
        tmp_path, use_real_forensics=False, forensics=forensics
    )
    assert status_map == {"case-001": "available"}
    assert len(records) == 1
    record = records[0]
    assert record["status"] == "available"
    assert len(record["filings"]) == 1
    filing = record["filings"][0]
    assert filing["accession"] == "0000320193-26-000010"
    assert len(filing["documents"]) == 2
    assert all(doc["status"] == "available" for doc in filing["documents"])

    # Texts directory: one file per document, hashes match
    texts_dir = tmp_path / "out" / "texts"
    assert texts_dir.is_dir()
    for doc in filing["documents"]:
        target = texts_dir / f"{doc['text_sha256']}.txt"
        assert target.is_file()
        body = target.read_bytes()
        import hashlib
        assert hashlib.sha256(body).hexdigest() == doc["text_sha256"]
        assert int(doc["text_bytes"]) == len(body)

    # source_document fields
    src = filing["documents"][0]["source_document"]
    assert src["source_class"] == "primary_filing"
    assert src["rights_state"] == "internal_only"
    assert src["filing_key"] == {"cik": "0000320193", "accession": "0000320193-26-000010"}

    # Re-running verify_span against the text file passes
    doc_entry = filing["documents"][0]
    text_bytes = (texts_dir / f"{doc_entry['text_sha256']}.txt").read_bytes()
    text = text_bytes.decode("utf-8")
    span = text_span(
        document_id=doc_entry["document_id"],
        document_version=1,
        body_sha256=doc_entry["text_sha256"],
        segment_index=0,
        segment_text=text,
        start_byte=0,
        end_byte=len(text_bytes),
        text=text,
        display_excerpt="",
    )
    assert span.span_id == doc_entry["span_id"]
    verify_span(span, segment_text=text, body_sha256=doc_entry["text_sha256"])
    # One byte changed -> DocumentError
    modified = bytearray(text_bytes)
    modified[0] = (modified[0] + 1) & 0xFF
    with pytest.raises(DocumentError):
        verify_span(
            span,
            segment_text=bytes(modified).decode("utf-8"),
            body_sha256=doc_entry["text_sha256"],
        )


def test_end_to_end_available_with_real_forensics(tmp_path):
    status_map, records, report, _ = _run_e2e(tmp_path, use_real_forensics=True)
    assert status_map == {"case-001": "available"}
    assert records[0]["status"] == "available"
    assert records[0]["filings"][0]["documents"][0]["status"] == "available"


# ---------------------------------------------------------------------------
# T9 - reasons
# ---------------------------------------------------------------------------


def _case(item_id: str, issuer: str, seendate: str) -> dict:
    return {
        "item_id": item_id,
        "issuer": issuer,
        "template": "t",
        "proxy_cell": "c",
        "group_id": "g",
        "fold": "0",
        "source_sha256": "a" * 64,
        "seendate": seendate,
        "tags": [],
    }


def _fetch_one(
    tmp_path: Path,
    case: dict,
    *,
    forensics,
    session_routes: dict[str, bytes] | None = None,
    max_document_bytes: int | None = None,
) -> tuple[dict, list[dict], dict]:
    session = FakeSession(session_routes or {})
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    return eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
        max_document_bytes=max_document_bytes,
    )


def test_reason_no_cik(tmp_path):
    forensics = FakeForensics()
    case = _case("no-cik", "unresolved:no_mention", "2026-09-15T15:00:00Z")
    status_map, records, _ = _fetch_one(tmp_path, case, forensics=forensics)
    assert status_map == {"no-cik": "body_unavailable:no_cik"}


def test_reason_calendar_gap(tmp_path):
    forensics = FakeForensics()
    # Before the first session
    case = _case("gap", "cik:0000320193", "2026-09-01T15:00:00Z")
    status_map, records, _ = _fetch_one(tmp_path, case, forensics=forensics)
    assert status_map == {"gap": "body_unavailable:calendar_gap"}


def test_reason_submissions_failed(tmp_path):
    forensics = FakeForensics(
        current={"0000320193": RuntimeError("network down")}
    )
    case = _case("sub-fail", "cik:0000320193", "2026-09-15T15:00:00Z")
    status_map, records, _ = _fetch_one(tmp_path, case, forensics=forensics)
    assert status_map == {"sub-fail": "body_unavailable:submissions_failed"}


def test_reason_no_qualifying_8k(tmp_path):
    forensics = FakeForensics(
        current={
            "0000320193": {
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-26-000099"],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["5.02"],
                        "primaryDocument": ["a.htm"],
                    }
                }
            }
        }
    )
    case = _case("no-8k", "cik:0000320193", "2026-09-15T15:00:00Z")
    status_map, records, _ = _fetch_one(tmp_path, case, forensics=forensics)
    assert status_map == {"no-8k": "body_unavailable:no_qualifying_8k"}


def test_reason_index_failed(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000020"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": ["p.htm"],
                    }
                }
            }
        }
    )
    # 404 on the index URL
    session_routes = {eb.index_url(cik10, accession): b""}
    session = FakeSession()
    session.add(eb.index_url(cik10, accession), _Response)  # placeholder, replaced
    # Use a 404 by overriding the session: provide only the index URL with a 404
    class _OneRouteSession:
        def __init__(self, url: str) -> None:
            self.url = url
            self.calls: list[str] = []

        def get(self, url, **kwargs):
            self.calls.append(url)
            if url == self.url:
                return _Response(b"", status_code=404)
            raise AssertionError(f"unexpected URL {url!r}")

    archive = SecFilingArchiveCollector(
        tmp_path / "archive",
        user_agent=USER_AGENT,
        session=_OneRouteSession(eb.index_url(cik10, accession)),
        sleeper=lambda s: None,
        monotonic=_Counter(),
        pacer=_make_pacer(),
    )
    case = _case("idx-fail", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"idx-fail": "body_unavailable:index_failed"}


def test_reason_no_body_document(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000021"
    primary_filename = "p.htm"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": [primary_filename],
                    }
                }
            }
        }
    )
    # Index that lists only a GRAPHIC row (no primary matching, no exhibits)
    rows = [
        (
            "1",
            "GRAPHIC",
            "g.jpg",
            "GRAPHIC",
            "",
        )
    ]
    routes = {eb.index_url(cik10, accession): _index_html(rows)}
    case = _case("no-body", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, _ = _fetch_one(tmp_path, case, forensics=forensics, session_routes=routes)
    assert status_map == {"no-body": "body_unavailable:no_body_document"}


def test_reason_document_missing(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000022"
    primary_filename = "p.htm"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": [primary_filename],
                    }
                }
            }
        }
    )
    # Session: index returns a proper EDGAR table; primary URL returns 404
    index_url = eb.index_url(cik10, accession)
    primary_url = eb.document_url(cik10, accession, primary_filename)
    index_html = _index_html(
        [
            (
                "1",
                "8-K",
                primary_filename,
                "8-K",
                " &nbsp;&nbsp;<span class=\"small\">iXBRL</span>",
            )
        ]
    )

    class _SelectiveSession:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def get(self, url, **kwargs):
            self.calls.append(url)
            if url == index_url:
                response = _Response(index_html, status_code=200)
                response.url = url
                return response
            if url == primary_url:
                response = _Response(b"", status_code=404)
                response.url = url
                return response
            raise AssertionError(f"unexpected URL {url!r}")

    archive = SecFilingArchiveCollector(
        tmp_path / "archive",
        user_agent=USER_AGENT,
        session=_SelectiveSession(),
        sleeper=lambda s: None,
        monotonic=_Counter(),
        pacer=_make_pacer(),
    )
    case = _case("doc-miss", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"doc-miss": "body_unavailable:document_missing"}


def test_reason_too_large(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000023"
    primary_filename = "p.htm"
    # Document body deliberately larger than the per-document cap.
    primary_body = b"<html><body><p>" + b"X" * 600 + b"</p></body></html>"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": [primary_filename],
                    }
                }
            }
        }
    )
    session = FakeSession()
    _wire_routes(session, cik10, accession, primary_filename, primary_body)
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    case = _case("too-large", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    # The synthetic index page is ~370 bytes; the document body is ~620 bytes.
    # A cap of 500 admits the index and refuses the document.
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
        max_document_bytes=500,
    )
    assert status_map == {"too-large": "body_unavailable:too_large"}


def test_reason_empty_text(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000024"
    primary_filename = "p.htm"
    primary_body = b"<html><script>x</script></html>"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": [primary_filename],
                    }
                }
            }
        }
    )
    helper_session = FakeSession()
    routes = _wire_routes(helper_session, cik10, accession, primary_filename, primary_body)
    case = _case("empty", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, _ = _fetch_one(
        tmp_path,
        case,
        forensics=forensics,
        session_routes=routes,
    )
    assert status_map == {"empty": "body_unavailable:empty_text"}


def test_reason_furthest_stage_among_filings(tmp_path):
    """Two filings, one document_missing and one empty_text -> empty_text wins."""
    cik10 = "0000320193"
    a1 = "0000320193-26-000030"
    a2 = "0000320193-26-000031"
    p1 = "p1.htm"
    p2 = "p2.htm"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [a1, a2],
                        "filingDate": ["2026-09-15", "2026-09-15"],
                        "form": ["8-K", "8-K"],
                        "items": ["2.02", "2.02"],
                        "primaryDocument": [p1, p2],
                    }
                }
            }
        }
    )
    # Two-route session: index1 -> real index, index2 -> real index, doc1 -> 404, doc2 -> empty
    session = FakeSession()
    _wire_routes(
        session,
        cik10,
        a1,
        p1,
        b"<html><body><p>Document one.</p></body></html>",
    )
    # Override: doc1 URL returns 404
    session.routes.pop(eb.document_url(cik10, a1, p1))

    class _SelectiveSession:
        def __init__(self, real: FakeSession, overrides: dict[str, int]) -> None:
            self.real = real
            self.overrides = overrides
            self.calls: list[str] = []

        def get(self, url, **kwargs):
            self.calls.append(url)
            if url in self.overrides:
                return _Response(b"", status_code=self.overrides[url])
            return self.real.get(url, **kwargs)

    selective = _SelectiveSession(session, {eb.document_url(cik10, a1, p1): 404})
    _wire_routes(
        selective.real,
        cik10,
        a2,
        p2,
        b"<html><script>x</script></html>",
    )
    archive = SecFilingArchiveCollector(
        tmp_path / "archive",
        user_agent=USER_AGENT,
        session=selective,
        sleeper=lambda s: None,
        monotonic=_Counter(),
        pacer=_make_pacer(),
    )
    case = _case("furthest", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"furthest": "body_unavailable:empty_text"}


# ---------------------------------------------------------------------------
# T10 - memoisation
# ---------------------------------------------------------------------------


def test_memoisation_two_cases_same_filing(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000040"
    primary_filename = "p.htm"
    primary_body = b"<html><body><p>Memo body.</p></body></html>"
    exhibit_body = b"<html><body><p>Memo exhibit.</p></body></html>"
    session = FakeSession()
    _wire_routes(
        session,
        cik10,
        accession,
        primary_filename,
        primary_body,
        exhibit_bodies={"ex1.htm": exhibit_body},
    )
    pacer = _make_pacer()
    archive = _make_archive(tmp_path, session, pacer=pacer)
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": [primary_filename],
                    }
                }
            }
        }
    )
    case1 = _case("memo-1", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    case2 = _case("memo-2", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    status_map, records, report = eb.fetch_bodies(
        [case1, case2],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"memo-1": "available", "memo-2": "available"}
    assert forensics.current_calls == 1
    # Each unique URL was requested exactly once
    index_url = eb.index_url(cik10, accession)
    primary_url = eb.document_url(cik10, accession, primary_filename)
    exhibit_url = eb.document_url(cik10, accession, "ex1.htm")
    assert session.url_counts[index_url] == 1
    assert session.url_counts[primary_url] == 1
    assert session.url_counts[exhibit_url] == 1


# ---------------------------------------------------------------------------
# T11 - shards
# ---------------------------------------------------------------------------


def test_shards_overlap_and_skip(tmp_path):
    cik10 = "0000320193"
    cik_natural = "320193"
    a1 = "0000320193-26-000050"  # in shard1, in window
    shard1_name = "CIK0000320193-submissions-001.json"
    shard2_name = "CIK0000320193-submissions-002.json"
    recent_payload = {
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000099"],
                "filingDate": ["2026-10-05"],  # after the window
                "form": ["8-K"],
                "items": ["2.02"],
                "primaryDocument": ["late.htm"],
            },
            "files": [
                {"name": shard1_name, "filingFrom": "2026-08-25", "filingTo": "2026-09-15"},
                {"name": shard2_name, "filingFrom": "2026-07-01", "filingTo": "2026-07-31"},
            ],
        }
    }
    shard1_payload = {
        "accessionNumber": [a1],
        "filingDate": ["2026-09-09"],
        "form": ["8-K"],
        "items": ["2.02"],
        "primaryDocument": ["p.htm"],
    }
    forensics = FakeForensics(
        current={cik10: recent_payload},
        shards={shard1_name: shard1_payload},
    )
    session = FakeSession()
    _wire_routes(
        session,
        cik10,
        a1,
        "p.htm",
        b"<html><body><p>From shard1.</p></body></html>",
    )
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    case = _case("shard-ok", f"cik:{cik10}", "2026-09-10T15:00:00Z")
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"shard-ok": "available"}
    # shard1 fetched, shard2 never fetched
    assert forensics.shard_calls == [shard1_name]
    # reports the index + document fetches
    assert records[0]["filings"][0]["accession"] == a1


def test_shard_fetch_failure_is_submissions_failed(tmp_path):
    cik10 = "0000320193"
    shard1_name = "CIK0000320193-submissions-001.json"
    recent_payload = {
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000099"],
                "filingDate": ["2026-10-05"],
                "form": ["8-K"],
                "items": ["2.02"],
                "primaryDocument": ["late.htm"],
            },
            "files": [
                {"name": shard1_name, "filingFrom": "2026-08-25", "filingTo": "2026-09-15"},
            ],
        }
    }
    forensics = FakeForensics(current={cik10: recent_payload})
    forensics.shard_calls_as_exceptions[shard1_name] = RuntimeError("shard boom")
    session = FakeSession()
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    case = _case("shard-fail", f"cik:{cik10}", "2026-09-10T15:00:00Z")
    status_map, records, _ = eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert status_map == {"shard-fail": "body_unavailable:submissions_failed"}


# ---------------------------------------------------------------------------
# T12 - contract
# ---------------------------------------------------------------------------


def test_contract_status_map_and_reasons(tmp_path):
    cik10 = "0000320193"
    a1 = "0000320193-26-000060"
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [a1],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["5.02"],  # no qualifying items -> no_qualifying_8k
                        "primaryDocument": ["p.htm"],
                    }
                }
            }
        }
    )
    case_ok = _case("ok", f"unresolved:nope", "2026-09-15T15:00:00Z")
    case_no_8k = _case("no8k", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    session = FakeSession()
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    status_map, records, report = eb.fetch_bodies(
        [case_ok, case_no_8k],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
    )
    assert set(status_map.keys()) == {"ok", "no8k"}
    pattern = re.compile(r"^(available|body_unavailable:[a-z0-9_]+)$")
    for value in status_map.values():
        assert pattern.fullmatch(value), value
    for reason in eb.REASON_ORDER:
        assert reason in report["reasons"]
    # Duplicate item_id raises
    with pytest.raises(eb.EdgarBodyError):
        eb.fetch_bodies(
            [case_ok, case_ok],
            forensics=forensics,
            archive=archive,
            session_dates=SESSIONS,
            out_dir=tmp_path / "out",
            retrieved_at=RETRIEVED_AT,
        )


# ---------------------------------------------------------------------------
# T13 - determinism
# ---------------------------------------------------------------------------


def test_determinism_two_runs(tmp_path):
    cik10 = "0000320193"
    a1 = "0000320193-26-000070"
    primary_body = b"<html><body><p>Deterministic body.</p></body></html>"

    def _run_once(target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        session = FakeSession()
        _wire_routes(session, cik10, a1, "p.htm", primary_body)
        pacer = _make_pacer()
        archive = _make_archive(target, session, pacer=pacer)
        forensics = FakeForensics(
            current={
                cik10: {
                    "filings": {
                        "recent": {
                            "accessionNumber": [a1],
                            "filingDate": ["2026-09-15"],
                            "form": ["8-K"],
                            "items": ["2.02"],
                            "primaryDocument": ["p.htm"],
                        }
                    }
                }
            }
        )
        cases_path = target / "cases.jsonl"
        sessions_path = target / "sessions.json"
        out_dir = target / "out"
        cases_path.write_text(
            json.dumps(
                _case("det", f"cik:{cik10}", "2026-09-15T15:00:00Z")
            )
            + "\n",
            encoding="utf-8",
        )
        sessions_path.write_text(
            json.dumps({"sessions": [d.isoformat() for d in SESSIONS]}),
            encoding="utf-8",
        )
        rc = eb.main(
            [
                "--cases",
                str(cases_path),
                "--sessions",
                str(sessions_path),
                "--cache",
                str(target / "cache"),
                "--out",
                str(out_dir),
                "--user-agent",
                USER_AGENT,
            ],
            forensics=forensics,
            archive=archive,
        )
        assert rc == 0

    one = tmp_path / "run1"
    two = tmp_path / "run2"
    _run_once(one)
    _run_once(two)

    bodies1 = (one / "out" / "bodies.jsonl").read_bytes()
    bodies2 = (two / "out" / "bodies.jsonl").read_bytes()
    assert bodies1 == bodies2
    assert (one / "out" / "status_map.json").read_bytes() == (
        two / "out" / "status_map.json"
    ).read_bytes()
    assert (one / "out" / "body_report.json").read_bytes() == (
        two / "out" / "body_report.json"
    ).read_bytes()


# ---------------------------------------------------------------------------
# T14 - source hygiene
# ---------------------------------------------------------------------------


def test_source_hygiene():
    text = Path(eb.__file__).read_text(encoding="utf-8")
    forbidden = [
        "datetime.now",
        "utcnow",
        "date.today",
        "time.time(",
        "time.sleep",
        "monotonic",
        "import requests",
        "urllib",
        "http.client",
    ]
    for token in forbidden:
        assert token not in text, f"forbidden token {token!r} present in source"


# ---------------------------------------------------------------------------
# T15 - CLI
# ---------------------------------------------------------------------------


def test_cli_main_runs_and_writes_outputs(tmp_path, capsys):
    cik10 = "0000320193"
    a1 = "0000320193-26-000080"
    cases_path = tmp_path / "cases.jsonl"
    sessions_path = tmp_path / "sessions.json"
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"

    case = _case("cli-1", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    sessions_path.write_text(
        json.dumps({"sessions": [d.isoformat() for d in SESSIONS]}),
        encoding="utf-8",
    )

    session = FakeSession()
    _wire_routes(
        session,
        cik10,
        a1,
        "p.htm",
        b"<html><body><p>CLI body.</p></body></html>",
    )
    pacer = _make_pacer()
    archive = _make_archive(tmp_path, session, pacer=pacer)
    forensics = FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [a1],
                        "filingDate": ["2026-09-15"],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": ["p.htm"],
                    }
                }
            }
        }
    )

    rc = eb.main(
        [
            "--cases",
            str(cases_path),
            "--sessions",
            str(sessions_path),
            "--cache",
            str(cache_dir),
            "--out",
            str(out_dir),
            "--user-agent",
            USER_AGENT,
        ],
        forensics=forensics,
        archive=archive,
    )
    assert rc == 0
    assert (out_dir / "bodies.jsonl").is_file()
    assert (out_dir / "status_map.json").is_file()
    assert (out_dir / "body_report.json").is_file()
    assert (out_dir / "texts").is_dir()
    captured = capsys.readouterr()
    parsed = json.loads(captured.out.strip())
    assert parsed["cases"] == 1
    assert parsed["available"] == 1
    assert parsed["out"] == str(out_dir)


def test_cli_main_bad_sessions_returns_2(tmp_path, capsys):
    cik10 = "0000320193"
    cases_path = tmp_path / "cases.jsonl"
    sessions_path = tmp_path / "sessions.json"
    case = _case("bad", f"cik:{cik10}", "2026-09-15T15:00:00Z")
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    sessions_path.write_text(json.dumps({"not_sessions": []}), encoding="utf-8")

    rc = eb.main(
        [
            "--cases",
            str(cases_path),
            "--sessions",
            str(sessions_path),
            "--cache",
            str(tmp_path / "cache"),
            "--out",
            str(tmp_path / "out"),
            "--user-agent",
            USER_AGENT,
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "sessions" in captured.err


# ---------------------------------------------------------------------------
# T15 - ni-edgar-body-2: (1, 4) band, open-window guard, filing tags
# ---------------------------------------------------------------------------


def _v2_forensics(cik10: str, accession: str, filing_date: str) -> FakeForensics:
    return FakeForensics(
        current={
            cik10: {
                "filings": {
                    "recent": {
                        "accessionNumber": [accession],
                        "filingDate": [filing_date],
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "primaryDocument": ["p.htm"],
                    }
                }
            }
        }
    )


def _fetch_versioned(
    tmp_path: Path,
    case: dict,
    *,
    forensics,
    session: FakeSession | None = None,
    **kwargs,
) -> tuple[dict, list[dict], dict]:
    archive = _make_archive(tmp_path, session or FakeSession(), pacer=_make_pacer())
    return eb.fetch_bodies(
        [case],
        forensics=forensics,
        archive=archive,
        session_dates=SESSIONS,
        out_dir=tmp_path / "out",
        retrieved_at=RETRIEVED_AT,
        **kwargs,
    )


def test_body_versions_and_bands():
    assert eb.EDGAR_BODY_VERSIONS == ("ni-edgar-body-1", "ni-edgar-body-2")
    assert eb.BODY_BANDS == {"ni-edgar-body-1": (1, 1), "ni-edgar-body-2": (1, 4)}
    assert "window_open" not in eb.REASON_ORDER
    assert eb.REASON_ORDER_V2 == (
        eb.REASON_ORDER[:2] + ("window_open",) + eb.REASON_ORDER[2:]
    )


def test_session_window_band_1_4():
    # Tuesday 2026-09-15: one session before, four after (Mon 09-21).
    assert eb.session_window("2026-09-15T15:00:00Z", SESSIONS, (1, 4)) == (
        date(2026, 9, 14),
        date(2026, 9, 15),
        date(2026, 9, 21),
    )
    # The default band is the version-1 window.
    assert eb.session_window("2026-09-15T15:00:00Z", SESSIONS) == eb.session_window(
        "2026-09-15T15:00:00Z", SESSIONS, (1, 1)
    )
    # Last full band: Monday 2026-10-05 ends on the final session (Fri 10-09).
    assert eb.session_window("2026-10-05T15:00:00Z", SESSIONS, (1, 4)) == (
        date(2026, 10, 2),
        date(2026, 10, 5),
        date(2026, 10, 9),
    )
    # One session later the band runs off the calendar.
    assert eb.session_window("2026-10-06T15:00:00Z", SESSIONS, (1, 4)) is None
    # v1 still covers the same seen date.
    assert eb.session_window("2026-10-06T15:00:00Z", SESSIONS) is not None


@pytest.mark.parametrize(
    "band", [(0, 4), (1, 0), (1,), (1, 4, 1), [1, 4], (True, 4), (1, 4.0), None]
)
def test_session_window_bad_band_raises(band):
    with pytest.raises(eb.EdgarBodyError):
        eb.session_window("2026-09-15T15:00:00Z", SESSIONS, band)


def test_filing_session_offset_and_relation():
    seen = "2026-09-15T15:00:00Z"
    assert eb.filing_session_offset(date(2026, 9, 14), seen, SESSIONS) == -1
    assert eb.filing_session_offset(date(2026, 9, 15), seen, SESSIONS) == 0
    assert eb.filing_session_offset(date(2026, 9, 18), seen, SESSIONS) == 3
    # A non-session filing date rolls forward to the next session (Sat -> Mon).
    assert eb.filing_session_offset(date(2026, 9, 19), seen, SESSIONS) == 4
    # Late-evening UTC seen date maps to its New York market date.
    assert eb.filing_session_offset(
        date(2026, 9, 15), "2026-09-16T02:00:00Z", SESSIONS
    ) == 0
    assert eb.filing_relation(-1) == "filed_before_seen"
    assert eb.filing_relation(0) == "filed_same_session"
    assert eb.filing_relation(3) == "filed_after_seen"


def test_v2_reaches_a_filing_v1_misses(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000150"
    case = _case("late", f"cik:{cik10}", "2026-09-15T15:00:00Z")

    v1_map, v1_records, v1_report = _fetch_versioned(
        tmp_path / "v1", case, forensics=_v2_forensics(cik10, accession, "2026-09-18")
    )
    assert v1_map == {"late": "body_unavailable:no_qualifying_8k"}
    assert v1_report["version"] == "ni-edgar-body-1"
    assert v1_records[0]["window"] == ["2026-09-14", "2026-09-15", "2026-09-16"]

    session = FakeSession()
    _wire_routes(
        session, cik10, accession, "p.htm",
        b"<html><body><p>Results for the quarter.</p></body></html>",
    )
    v2_map, v2_records, v2_report = _fetch_versioned(
        tmp_path / "v2",
        case,
        forensics=_v2_forensics(cik10, accession, "2026-09-18"),
        session=session,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 10, 14),
    )
    assert v2_map == {"late": "available"}
    assert v2_report["version"] == "ni-edgar-body-2"
    record = v2_records[0]
    assert record["window"] == ["2026-09-14", "2026-09-15", "2026-09-21"]
    filing = record["filings"][0]
    assert filing["accession"] == accession
    assert filing["session_offset"] == 3
    assert filing["relation"] == "filed_after_seen"


def test_v2_tags_a_filing_before_the_seen_session(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000151"
    session = FakeSession()
    _wire_routes(
        session, cik10, accession, "p.htm",
        b"<html><body><p>Agreement entered.</p></body></html>",
    )
    _, records, _ = _fetch_versioned(
        tmp_path,
        _case("early", f"cik:{cik10}", "2026-09-15T15:00:00Z"),
        forensics=_v2_forensics(cik10, accession, "2026-09-14"),
        session=session,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 10, 14),
    )
    filing = records[0]["filings"][0]
    assert filing["session_offset"] == -1
    assert filing["relation"] == "filed_before_seen"


def test_v1_records_carry_no_v2_keys(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000152"
    session = FakeSession()
    _wire_routes(
        session, cik10, accession, "p.htm",
        b"<html><body><p>Same-day filing.</p></body></html>",
    )
    status_map, records, report = _fetch_versioned(
        tmp_path,
        _case("same", f"cik:{cik10}", "2026-09-15T15:00:00Z"),
        forensics=_v2_forensics(cik10, accession, "2026-09-15"),
        session=session,
    )
    assert status_map == {"same": "available"}
    filing = records[0]["filings"][0]
    assert "session_offset" not in filing
    assert "relation" not in filing
    assert report["version"] == "ni-edgar-body-1"
    assert list(report["reasons"]) == list(eb.REASON_ORDER)


def test_v2_window_open_fetches_no_submissions(tmp_path):
    cik10 = "0000320193"
    forensics = _v2_forensics(cik10, "0000320193-26-000153", "2026-09-18")
    # Window for 09-15 ends Mon 09-21; as_of on that day leaves it open.
    status_map, records, report = _fetch_versioned(
        tmp_path,
        _case("open", f"cik:{cik10}", "2026-09-15T15:00:00Z"),
        forensics=forensics,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 9, 21),
    )
    assert status_map == {"open": "body_unavailable:window_open"}
    assert records[0]["window"] == ["2026-09-14", "2026-09-15", "2026-09-21"]
    assert records[0]["filings"] == []
    assert forensics.current_calls == 0
    assert report["reasons"]["window_open"] == 1
    assert list(report["reasons"]) == list(eb.REASON_ORDER_V2)


def test_v2_window_closed_the_day_after_its_end(tmp_path):
    cik10 = "0000320193"
    accession = "0000320193-26-000154"
    session = FakeSession()
    _wire_routes(
        session, cik10, accession, "p.htm",
        b"<html><body><p>Filed on the last day.</p></body></html>",
    )
    forensics = _v2_forensics(cik10, accession, "2026-09-21")
    status_map, records, _ = _fetch_versioned(
        tmp_path,
        _case("closed", f"cik:{cik10}", "2026-09-15T15:00:00Z"),
        forensics=forensics,
        session=session,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 9, 22),
    )
    assert status_map == {"closed": "available"}
    assert forensics.current_calls == 1
    assert records[0]["filings"][0]["session_offset"] == 4


def test_v2_no_cik_and_calendar_gap_precede_window_open(tmp_path):
    forensics = FakeForensics()
    no_cik_map, _, _ = _fetch_versioned(
        tmp_path / "a",
        _case("nocik", "unresolved:no_mention", "2026-09-15T15:00:00Z"),
        forensics=forensics,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 9, 1),
    )
    assert no_cik_map == {"nocik": "body_unavailable:no_cik"}
    gap_map, _, _ = _fetch_versioned(
        tmp_path / "b",
        _case("gap", "cik:0000320193", "2026-10-07T15:00:00Z"),
        forensics=forensics,
        version=eb.EDGAR_BODY_VERSION_2,
        as_of=date(2026, 9, 1),
    )
    assert gap_map == {"gap": "body_unavailable:calendar_gap"}
    assert forensics.current_calls == 0


@pytest.mark.parametrize(
    "version, as_of",
    [
        (eb.EDGAR_BODY_VERSION_2, None),
        (eb.EDGAR_BODY_VERSION_2, "2026-10-14"),
        (eb.EDGAR_BODY_VERSION_2, datetime(2026, 10, 14, tzinfo=timezone.utc)),
        (eb.EDGAR_BODY_VERSION, date(2026, 10, 14)),
        ("ni-edgar-body-3", date(2026, 10, 14)),
        ("ni-edgar-body-3", None),
    ],
)
def test_fetch_bodies_version_and_as_of_errors(tmp_path, version, as_of):
    with pytest.raises(eb.EdgarBodyError):
        _fetch_versioned(
            tmp_path,
            _case("x", "cik:0000320193", "2026-09-15T15:00:00Z"),
            forensics=FakeForensics(),
            version=version,
            as_of=as_of,
        )


def _cli_inputs(tmp_path: Path, case: dict) -> list[str]:
    cases_path = tmp_path / "cases.jsonl"
    sessions_path = tmp_path / "sessions.json"
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    sessions_path.write_text(
        json.dumps({"sessions": [d.isoformat() for d in SESSIONS]}),
        encoding="utf-8",
    )
    return [
        "--cases",
        str(cases_path),
        "--sessions",
        str(sessions_path),
        "--cache",
        str(tmp_path / "cache"),
        "--out",
        str(tmp_path / "out"),
        "--user-agent",
        USER_AGENT,
    ]


def test_cli_main_v2_with_as_of(tmp_path, capsys):
    cik10 = "0000320193"
    accession = "0000320193-26-000155"
    session = FakeSession()
    _wire_routes(
        session, cik10, accession, "p.htm",
        b"<html><body><p>CLI v2 body.</p></body></html>",
    )
    archive = _make_archive(tmp_path, session, pacer=_make_pacer())
    argv = _cli_inputs(tmp_path, _case("cli-v2", f"cik:{cik10}", "2026-09-15T15:00:00Z"))
    rc = eb.main(
        argv + ["--version", eb.EDGAR_BODY_VERSION_2, "--as-of", "2026-10-14"],
        forensics=_v2_forensics(cik10, accession, "2026-09-18"),
        archive=archive,
    )
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out.strip())
    assert parsed["available"] == 1
    report = json.loads((tmp_path / "out" / "body_report.json").read_text("utf-8"))
    assert report["version"] == "ni-edgar-body-2"
    assert "window_open" in report["reasons"]


@pytest.mark.parametrize(
    "extra",
    [
        ["--version", "ni-edgar-body-2"],
        ["--version", "ni-edgar-body-2", "--as-of", "2026-13-01"],
        ["--as-of", "2026-10-14"],
        ["--version", "ni-edgar-body-1", "--as-of", "2026-10-14"],
    ],
)
def test_cli_main_version_as_of_errors_return_2(tmp_path, capsys, extra):
    argv = _cli_inputs(tmp_path, _case("cli-bad", "cik:0000320193", "2026-09-15T15:00:00Z"))
    rc = eb.main(argv + extra, forensics=FakeForensics(), archive=None)
    assert rc == 2
    assert "as-of" in capsys.readouterr().err
