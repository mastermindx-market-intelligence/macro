"""Catalyst SEC source cycle writer — hermetic unit suite (A3-W-r2).

No network (an autouse fixture refuses socket connects), no R2, no personal
data, no real SEC request.  A scripted FakeSession serves every GET; the
store is a LocalStore under tmp_path through the namespaced wrapper.
"""
from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import engine.marketing.catalyst_source_cycle as csc
import engine.marketing.catalyst_source_store as css
from collectors.edgar_forensics import endpoint_url
from engine.fundamental_forensics.sec_document_spine import (
    archive_document_url,
    build_filing_manifests,
)
from engine.news_impact.edgar_body import index_url
from engine.marketing.catalyst_source_cycle import (
    CycleResult,
    UniverseIssuer,
    load_universe,
    project_release_figures,
    run_cycle,
)
from engine.marketing.catalyst_source_store import (
    INDEX_SCHEMA,
    NAMESPACE_PREFIX,
    CatalystSourceUnavailable,
    NamespacedSourceStore,
    open_local_store,
    open_production_store,
    read_latest_index,
    validate_index,
)

UTC = timezone.utc
UA = "catalyst-test admin@example.invalid"
FIXTURE = Path(__file__).resolve().parent / "fixtures/earnings_release/ex99_1_release.htm"
TAMPERED = Path(__file__).resolve().parent / "fixtures/earnings_release/ex99_1_release_tampered.htm"
PFE = UniverseIssuer(ticker="PFE", cik=78003, name="Pfizer Inc.")
AAPL = UniverseIssuer(ticker="AAPL", cik=320193, name="Apple Inc.")
ACCESSION = "0000078003-26-000094"
ACCEPTED = "2026-08-04T11:02:43Z"
ACCESSION_B = "0000320193-26-000012"
ACCEPTED_B = "2026-08-04T12:15:00Z"
SYNTHETIC_LATEST_KEY = NAMESPACE_PREFIX + "fundamental_forensics/sec-source/v1/latest.json"


# ---------------------------------------------------------------------------
# Hermetic ground rules
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Catches: a regression that makes any test reach the real network."""
    def refused(*args, **kwargs):
        raise AssertionError("network access is forbidden in this suite")

    monkeypatch.setattr(socket.socket, "connect", refused)


@pytest.fixture(autouse=True)
def _noop_pacer(monkeypatch):
    """Catches: pacing regressions; keeps the suite from sleeping 0.2s/GET.

    The pacer is neutralized by replacing the writer module's SecRequestPacer
    with a no-op stand-in (recorded choice in the lane record).
    """
    class _NoopPacer:
        def __init__(self, *, min_interval_seconds=0.2, **kwargs):
            self.min_interval_seconds = min_interval_seconds

        def acquire(self):
            return None

    monkeypatch.setattr(csc, "SecRequestPacer", _NoopPacer)


class FakeResponse:
    def __init__(self, *, status_code=200, url, headers=None, chunks=()):
        self.status_code = status_code
        self.url = url
        self.headers = dict(headers or {})
        self._chunks = list(chunks)
        self.closed = False

    def iter_content(self, chunk_size=65536):
        for chunk in self._chunks:
            yield chunk

    def close(self):
        self.closed = True


class FakeSession:
    """Records every get(); serves scripted responses per URL in order."""

    def __init__(self, routes=None):
        self.routes = {url: list(queue) for url, queue in (routes or {}).items()}
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url not in self.routes:
            raise AssertionError(f"unexpected SEC GET: {url}")
        queue = self.routes[url]
        if len(queue) > 1:
            return queue.pop(0)
        return queue[0]

    def urls(self):
        return [url for url, _ in self.calls]

    def calls_for(self, url):
        return sum(1 for called, _ in self.calls if called == url)


def ok(url, body, status_code=200):
    payload = body if isinstance(body, bytes) else body.encode("utf-8")
    return FakeResponse(
        status_code=status_code, url=url,
        headers={"Content-Length": str(len(payload))},
        chunks=[payload],
    )


def make_clock(start=datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC), step=1):
    state = {"n": 0}

    def clock():
        state["n"] += 1
        return start + timedelta(seconds=state["n"] * step)

    return clock


def submissions_json(rows, *, cik="78003", tickers=("PFE",), files=(),
                     name="Synthetic test issuer"):
    recent: dict[str, list] = {}
    for row in rows:
        for field, value in row.items():
            recent.setdefault(field, []).append(value)
    return json.dumps({
        "cik": cik,
        "name": name,
        "tickers": list(tickers),
        "filings": {"recent": recent, "files": list(files)},
    }).encode("utf-8")


def pfe_row(*, accession=ACCESSION, form="8-K", items="2.02,9.01",
            accepted=ACCEPTED, amends=None, filing_date="2026-08-04",
            report_date="2026-06-28", primary="test8k.htm"):
    return {
        "accessionNumber": accession,
        "form": form,
        "filingDate": filing_date,
        "reportDate": report_date,
        "acceptanceDateTime": accepted,
        "amendsAccessionNumber": amends,
        "items": items,
        "primaryDocument": primary,
        "isXBRL": False,
        "isInlineXBRL": False,
    }


def aapl_row(*, accession=ACCESSION_B, form="8-K", items="2.02",
             accepted=ACCEPTED_B, amends=None):
    return {
        "accessionNumber": accession,
        "form": form,
        "filingDate": "2026-08-04",
        "reportDate": "2026-06-28",
        "acceptanceDateTime": accepted,
        "amendsAccessionNumber": amends,
        "items": items,
        "primaryDocument": "a8k.htm",
        "isXBRL": False,
        "isInlineXBRL": False,
    }


def index_html(rows):
    """A synthetic EDGAR filing index (same shape as the edgar_body suite)."""
    body_rows = []
    for seq, description, href, doc_type in rows:
        body_rows.append(
            "<tr>"
            f"<td scope=\"row\">{seq}</td>"
            f"<td scope=\"row\">{description}</td>"
            f"<td scope=\"row\"><a href=\"{href}\">{href.split('/')[-1]}</a></td>"
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
    return (
        "<html><body>"
        "<table summary=\"Document Format Files\">"
        + header
        + "".join(body_rows)
        + "</table></body></html>"
    ).encode("utf-8")


def archive_dir(accession, cik=78003):
    return f"/Archives/edgar/data/{cik}/{accession.replace('-', '')}"


def ex99_index(accession=ACCESSION, filename="ex99-1.htm", cik=78003):
    return index_html([
        ("1", "8-K", f"{archive_dir(accession, cik)}/{accession}-8k.htm", "8-K"),
        ("2", "EX-99.1", f"{archive_dir(accession, cik)}/{filename}", "EX-99.1"),
    ])


def std_routes(*, release_bytes=None, index_bytes=None, submissions_bytes=None,
               accession=ACCESSION, document="ex99-1.htm", cik=78003, ticker="PFE"):
    body = FIXTURE.read_bytes() if release_bytes is None else release_bytes
    sub = submissions_json([pfe_row(accession=accession)]) if submissions_bytes is None \
        else submissions_bytes
    return {
        endpoint_url(cik, "submissions"): [ok(endpoint_url(cik, "submissions"), sub)],
        index_url(f"{cik:010d}", accession): [
            ok(index_url(f"{cik:010d}", accession),
               ex99_index(accession, document, cik) if index_bytes is None else index_bytes)
        ],
        archive_document_url(cik, accession, document): [
            ok(archive_document_url(cik, accession, document), body)
        ],
    }


def aapl_routes(release_bytes=None):
    body = FIXTURE.read_bytes() if release_bytes is None else release_bytes
    return {
        endpoint_url(320193, "submissions"): [
            ok(endpoint_url(320193, "submissions"),
               submissions_json([aapl_row()], cik="320193", tickers=("AAPL",)))],
        index_url("0000320193", ACCESSION_B): [
            ok(index_url("0000320193", ACCESSION_B),
               ex99_index(ACCESSION_B, "ex99-1.htm", 320193))],
        archive_document_url(320193, ACCESSION_B, "ex99-1.htm"): [
            ok(archive_document_url(320193, ACCESSION_B, "ex99-1.htm"), body)],
    }


def run(store, session, *, universe=(PFE,), clock=None, max_requests=150,
        work_root=None, user_agent=UA):
    sleeps: list[float] = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    result = csc.run_cycle(
        store=store, universe=universe, user_agent=user_agent,
        clock=clock or make_clock(), session=session, sleep=fake_sleep,
        max_requests=max_requests, work_root=work_root,
    )
    return result, sleeps


def bootstrap(store, tmp_path, *, routes=None, universe=(PFE,), max_requests=150):
    session = FakeSession(routes or std_routes())
    result, _ = run(store, session, universe=universe, max_requests=max_requests)
    return result, session


AAPL_URLS = frozenset(aapl_routes())


def bootstrap_with_ok_peer(store, tmp_path, *, routes):
    """Bootstrap PFE beside an ok AAPL so a PFE skip still publishes an index.

    A cycle that verifies nothing ends FAILED and publishes nothing; the skip
    tests need the published ``skipped`` rows, so they sweep an ok peer too.
    Returns the result, the session and the non-AAPL URLs it fetched.
    """
    result, session = bootstrap(store, tmp_path, routes={**routes, **aapl_routes()},
                                universe=(PFE, AAPL))
    return result, session, [url for url in session.urls() if url not in AAPL_URLS]


# ---------------------------------------------------------------------------
# 1-3: bootstrap, carried cycle, integrity
# ---------------------------------------------------------------------------

def test_bootstrap_complete_three_gets(tmp_path):
    """Catches: a bootstrap cycle fetching more or fewer than the 3 lawful GETs."""
    store = open_local_store(tmp_path / "store")
    session = FakeSession(std_routes())
    result, _ = run(store, session, work_root=tmp_path / "work")
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert session.urls() == [
        endpoint_url(78003, "submissions"),
        index_url("0000078003", ACCESSION),
        archive_document_url(78003, ACCESSION, "ex99-1.htm"),
    ]
    assert result.requests_used == 3
    published = read_latest_index(store)
    assert published is not None
    index = published.index
    assert index["schema"] == INDEX_SCHEMA
    assert index["outcome"] == "COMPLETE"
    assert index["issuers"] == [{
        "ticker": "PFE", "cik": 78003, "name": "Pfizer Inc.",
        "issuer_id": "cik:0000078003", "status": "ok", "reason": None,
    }]
    assert result.issuers_ok == 1
    [event] = index["events"]
    assert event["filing_key"] == f"0000078003:{ACCESSION}"
    assert event["form"] == "8-K"
    assert "2.02" in event["items"]
    assert event["filing_date"] == "2026-08-04"
    assert event["report_date"] == "2026-06-28"
    assert event["acceptance_datetime"] == ACCEPTED
    assert event["exhibit"]["exhibit_type"] == "EX-99.1"
    assert event["exhibit"]["source_url"].endswith(f"/000007800326000094/ex99-1.htm")
    assert event["exhibit"]["document_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert event["exhibit"]["byte_length"] == len(FIXTURE.read_bytes())
    assert event["retention"]["first_retained_receipt_id"].startswith("catsec-")
    assert event["retention"]["first_retained_at"] == event["retention"]["last_verified_at"]
    assert event["lineage"] == {"amends_filing_key": "", "correction_generation": 0}
    assert event["parse_status"] == "parsed"
    assert event["figure_outcome"] == "figures_projected"
    assert event["figures"], "projection must yield figures for the release fixture"
    assert index["skipped"] == []
    assert index["truncated"] is False
    assert index["request_budget"] == 150
    assert index["requests_used"] == 3


def test_second_cycle_carried_two_gets(tmp_path):
    """Catches: a carried filing re-fetching the index or losing first-retrieval identity."""
    store = open_local_store(tmp_path / "store")
    first, _ = bootstrap(store, tmp_path)
    assert first.exit_code == 0
    first_event = read_latest_index(store).index["events"][0]

    session = FakeSession({
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"),
               submissions_json([pfe_row()]))],
        archive_document_url(78003, ACCESSION, "ex99-1.htm"): [
            ok(archive_document_url(78003, ACCESSION, "ex99-1.htm"), FIXTURE.read_bytes())],
    })
    result, _ = run(store, session, clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert result.requests_used == 2
    assert session.urls() == [
        endpoint_url(78003, "submissions"),
        archive_document_url(78003, ACCESSION, "ex99-1.htm"),
    ]
    assert not any("-index.htm" in url for url in session.urls())
    [event] = read_latest_index(store).index["events"]
    assert event["retention"]["first_retained_at"] == first_event["retention"]["first_retained_at"]
    assert (event["retention"]["first_retained_receipt_id"]
            == first_event["retention"]["first_retained_receipt_id"])
    assert event["retention"]["last_verified_at"] > first_event["retention"]["last_verified_at"]
    assert event["figures"] == first_event["figures"]
    assert event["parse_status"] == "parsed"


def test_carried_sha_mismatch_drops_event(tmp_path):
    """Catches: a silently altered exhibit surviving into the next index."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    session = FakeSession({
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), submissions_json([pfe_row()]))],
        archive_document_url(78003, ACCESSION, "ex99-1.htm"): [
            ok(archive_document_url(78003, ACCESSION, "ex99-1.htm"),
               TAMPERED.read_bytes())],
    })
    result, _ = run(store, session, clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert result.issuers_incomplete == 1
    index = read_latest_index(store).index
    assert index["events"] == []
    assert index["skipped"] == [{"ticker": "PFE", "accession": ACCESSION,
                                 "reason": "integrity_mismatch"}]


# ---------------------------------------------------------------------------
# 4: budget truncation
# ---------------------------------------------------------------------------

def test_budget_exhaustion_truncates_but_publishes(tmp_path):
    """Catches: budget exhaustion aborting publication or over-fetching."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    session = FakeSession(routes)
    # PFE's bootstrap takes 3 GETs; AAPL's submissions GET is the 4th and its
    # index GET would be the 5th, so the budget truncates mid-AAPL.
    result, _ = run(store, session, universe=(PFE, AAPL), max_requests=4)
    assert (result.outcome, result.exit_code) == ("TRUNCATED", 3)
    assert result.requests_used == 4
    assert len(session.calls) == 4
    assert result.issuers_ok == 1
    assert result.issuers_not_checked == 1
    published = read_latest_index(store)
    assert published is not None
    assert published.index["outcome"] == "TRUNCATED"
    assert published.index["truncated"] is True
    assert published.index["requests_used"] == 4
    rows = {row["ticker"]: row for row in published.index["issuers"]}
    assert rows["PFE"]["status"] == "ok"
    assert (rows["AAPL"]["status"], rows["AAPL"]["reason"]) == (
        "not_checked", "budget_exhausted")
    assert [event["ticker"] for event in published.index["events"]] == ["PFE"]


def test_budget_exhausted_before_any_sweep_publishes_nothing(tmp_path):
    """Catches: a cycle that swept nothing replacing the prior pointer."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    result, _ = run(store, FakeSession(routes), universe=(PFE, AAPL), max_requests=2)
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "budget_exhausted"
    assert result.requests_used == 2
    assert result.issuers_not_checked == 2
    assert result.snapshot_id is None
    assert read_latest_index(store) is None


def test_not_checked_issuer_carries_prior_event(tmp_path):
    """Catches: a truncated later issuer losing its first-retrieval receipt."""
    store = open_local_store(tmp_path / "store")
    first, _ = bootstrap(store, tmp_path, universe=(PFE, AAPL),
                         routes={**std_routes(), **aapl_routes()})
    assert first.exit_code == 0
    prior = {event["ticker"]: event for event in read_latest_index(store).index["events"]}
    assert set(prior) == {"PFE", "AAPL"}

    routes = {**std_routes(), **aapl_routes()}
    result, _ = run(store, FakeSession(routes), universe=(PFE, AAPL), max_requests=2,
                    clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("TRUNCATED", 3)
    index = read_latest_index(store).index
    assert index["truncated"] is True
    statuses = {row["ticker"]: row["status"] for row in index["issuers"]}
    # PFE's filing is carried (2 GETs) and completes; the budget then truncates
    # before AAPL, which must be not_checked with its prior event carried.
    assert statuses == {"PFE": "ok", "AAPL": "not_checked"}
    carried = {event["ticker"]: event for event in index["events"]}
    assert carried["AAPL"] == prior["AAPL"]
    assert (carried["AAPL"]["retention"]["first_retained_receipt_id"]
            == prior["AAPL"]["retention"]["first_retained_receipt_id"])


# ---------------------------------------------------------------------------
# 5-7: exhibit selection (F4a/F4b)
# ---------------------------------------------------------------------------

def test_no_ex99_1_row_skips_without_document_get(tmp_path):
    """Catches: an exhibit fetch attempted without an EX-99.1 index row."""
    store = open_local_store(tmp_path / "store")
    only_ex99_2 = index_html([
        ("1", "8-K", f"{archive_dir(ACCESSION)}/{ACCESSION}-8k.htm", "8-K"),
        ("2", "EX-99.2", f"{archive_dir(ACCESSION)}/ex99-2.htm", "EX-99.2"),
    ])
    result, _, pfe_urls = bootstrap_with_ok_peer(
        store, tmp_path, routes=std_routes(index_bytes=only_ex99_2))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert len(pfe_urls) == 2
    assert not any("ex99" in url for url in pfe_urls)
    index = read_latest_index(store).index
    assert [event for event in index["events"] if event["ticker"] == "PFE"] == []
    assert index["skipped"][0]["reason"] == "no_ex99_1"


def test_type_column_selects_exhibit_not_filename(tmp_path):
    """Catches: F4a — choosing the exhibit by file name instead of the Type column."""
    store = open_local_store(tmp_path / "store")
    crossed = index_html([
        ("1", "8-K", f"{archive_dir(ACCESSION)}/ex99-1.htm", "EX-99.2"),
        ("2", "EX-99.1", f"{archive_dir(ACCESSION)}/ex99-2.htm", "EX-99.1"),
    ])
    routes = std_routes(index_bytes=crossed, document="ex99-2.htm")
    result, session = bootstrap(store, tmp_path, routes=routes)
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert archive_document_url(78003, ACCESSION, "ex99-2.htm") in session.urls()
    [event] = read_latest_index(store).index["events"]
    assert event["exhibit"]["source_url"].endswith("/ex99-2.htm")
    assert event["parse_status"] == "parsed"


def test_two_ex99_1_rows_are_ambiguous(tmp_path):
    """Catches: silently guessing between multiple EX-99.1 rows."""
    store = open_local_store(tmp_path / "store")
    doubled = index_html([
        ("1", "EX-99.1", f"{archive_dir(ACCESSION)}/ex99-1.htm", "EX-99.1"),
        ("2", "EX-99.1", f"{archive_dir(ACCESSION)}/ex99-1b.htm", "EX-99.1"),
    ])
    result, _, pfe_urls = bootstrap_with_ok_peer(
        store, tmp_path, routes=std_routes(index_bytes=doubled))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert len(pfe_urls) == 2
    index = read_latest_index(store).index
    assert index["skipped"][0]["reason"] == "ambiguous_ex99_1"


def test_exhibit_href_under_foreign_cik_refused(tmp_path):
    """Catches: F4b — an exhibit served from another issuer's directory."""
    store = open_local_store(tmp_path / "store")
    foreign = index_html([
        ("1", "EX-99.1", "/Archives/edgar/data/9999999/000007800326000094/ex99-1.htm",
         "EX-99.1"),
    ])
    result, _, pfe_urls = bootstrap_with_ok_peer(
        store, tmp_path, routes=std_routes(index_bytes=foreign))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert len(pfe_urls) == 2
    assert not any("ex99-1.htm" in url for url in pfe_urls)
    index = read_latest_index(store).index
    assert index["skipped"][0]["reason"] == "exhibit_cik_mismatch"


# ---------------------------------------------------------------------------
# 8-11: submissions reduction and identity
# ---------------------------------------------------------------------------

def test_non_qualifying_rows_cause_no_further_gets(tmp_path):
    """Catches: index/document GETs for filings that do not qualify."""
    store = open_local_store(tmp_path / "store")
    payload = submissions_json([
        pfe_row(form="10-Q", items=None),
        pfe_row(accession="0000078003-26-000090", items="9.01"),
        pfe_row(accession="0000078003-26-000091", accepted="2026-07-01T11:00:00Z"),
    ])
    result, session = bootstrap(store, tmp_path, routes=std_routes(submissions_bytes=payload))
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert session.urls() == [endpoint_url(78003, "submissions")]
    index = read_latest_index(store).index
    assert index["events"] == [] and index["skipped"] == []


def test_amendment_lineage_attestation(tmp_path):
    """Catches: an unattested 8-K/A admitted as a correction, or vice versa."""
    store = open_local_store(tmp_path / "store")
    unattested = submissions_json([
        pfe_row(accession="0000078003-26-000101", form="8-K/A",
                accepted="2026-08-04T11:30:00Z", amends=None),
    ])
    result, _, pfe_urls = bootstrap_with_ok_peer(store, tmp_path, routes=std_routes(
        submissions_bytes=unattested, accession="0000078003-26-000101"))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert pfe_urls == [endpoint_url(78003, "submissions")]
    index = read_latest_index(store).index
    assert index["skipped"][0]["reason"] == "unattested_amendment"

    store2 = open_local_store(tmp_path / "store2")
    attested = submissions_json([
        pfe_row(accession="0000078003-26-000101", form="8-K/A",
                accepted="2026-08-04T11:30:00Z", amends=ACCESSION),
    ])
    result2, _ = bootstrap(store2, tmp_path, routes=std_routes(
        submissions_bytes=attested, accession="0000078003-26-000101"))
    assert (result2.outcome, result2.exit_code) == ("COMPLETE", 0)
    [event] = read_latest_index(store2).index["events"]
    assert event["form"] == "8-K/A"
    assert event["lineage"] == {
        "amends_filing_key": f"0000078003:{ACCESSION}",
        "correction_generation": 1,
    }


def _pfe_urls(session):
    aapl = set(aapl_routes())
    return [url for url in session.urls() if url not in aapl]


def _issuer_reason(store, ticker):
    rows = {row["ticker"]: row for row in read_latest_index(store).index["issuers"]}
    return rows[ticker]["status"], rows[ticker]["reason"]


def test_identity_mismatch_fails_issuer(tmp_path):
    """Catches: trusting a submissions payload that names a different issuer."""
    wrong_cik = submissions_json([pfe_row()], cik="39044")
    store = open_local_store(tmp_path / "store")
    result, session = bootstrap(
        store, tmp_path, universe=(PFE, AAPL),
        routes={**std_routes(submissions_bytes=wrong_cik), **aapl_routes()})
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert result.issuers_failed == 1
    assert _pfe_urls(session) == [endpoint_url(78003, "submissions")]
    assert _issuer_reason(store, "PFE") == ("failed", "identity_mismatch")
    assert _issuer_reason(store, "AAPL") == ("ok", None)

    wrong_ticker = submissions_json([pfe_row()], tickers=("XYZ",))
    store2 = open_local_store(tmp_path / "store2")
    result2, session2 = bootstrap(
        store2, tmp_path, universe=(PFE, AAPL),
        routes={**std_routes(submissions_bytes=wrong_ticker), **aapl_routes()})
    assert (result2.outcome, result2.exit_code) == ("PARTIAL", 4)
    assert _pfe_urls(session2) == [endpoint_url(78003, "submissions")]
    assert _issuer_reason(store2, "PFE") == ("failed", "identity_mismatch")

    # A single-issuer cycle that sweeps nothing publishes nothing (FAILED).
    store3 = open_local_store(tmp_path / "store3")
    result3, _ = bootstrap(store3, tmp_path, routes=std_routes(submissions_bytes=wrong_cik))
    assert (result3.outcome, result3.exit_code) == ("FAILED", 6)
    assert result3.reason == "no_issuer_swept"
    assert read_latest_index(store3) is None


def test_pagination_unproven_fails_issuer(tmp_path):
    """Catches: trusting a truncated recent list when older shards exist."""
    store = open_local_store(tmp_path / "store")
    sharded = submissions_json(
        [pfe_row()],
        files=[{"name": "CIK0000078003-submissions-001.json"}])
    result, session = bootstrap(
        store, tmp_path, universe=(PFE, AAPL),
        routes={**std_routes(submissions_bytes=sharded), **aapl_routes()})
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert result.issuers_failed == 1
    assert _pfe_urls(session) == [endpoint_url(78003, "submissions")]
    assert _issuer_reason(store, "PFE") == ("failed", "pagination_unproven")


# ---------------------------------------------------------------------------
# 12-13: transport refusal and retries
# ---------------------------------------------------------------------------

def test_redirect_and_url_mismatch_refused(tmp_path):
    """Catches: following a redirect or accepting a rewritten URL."""
    store = open_local_store(tmp_path / "store")
    redirected = std_routes()
    index = index_url("0000078003", ACCESSION)
    redirected[index] = [FakeResponse(status_code=301, url=index, headers={})]
    result, _ = bootstrap(store, tmp_path, routes={**redirected, **aapl_routes()},
                          universe=(PFE, AAPL))
    assert result.exit_code == 4
    index_read = read_latest_index(store).index
    assert [event["ticker"] for event in index_read["events"]] == ["AAPL"]
    assert index_read["skipped"][0]["reason"] == "SecGetRefused"
    assert index_read["issuers"][0]["status"] == "incomplete"

    store2 = open_local_store(tmp_path / "store2")
    document = archive_document_url(78003, ACCESSION, "ex99-1.htm")
    rewritten = std_routes()
    rewritten[document] = [ok(document + "x", FIXTURE.read_bytes())]
    result2, _ = bootstrap(store2, tmp_path, routes={**rewritten, **aapl_routes()},
                           universe=(PFE, AAPL))
    assert result2.exit_code == 4
    index2 = read_latest_index(store2).index
    assert [event["ticker"] for event in index2["events"]] == ["AAPL"]
    assert index2["skipped"][0]["reason"] == "SecGetRefused"
    assert index2["issuers"][0]["status"] == "incomplete"


def test_retry_backoff_and_limit(tmp_path):
    """Catches: unbounded retries or missing backoff sleep."""
    store = open_local_store(tmp_path / "store")
    index = index_url("0000078003", ACCESSION)
    recovering = std_routes()
    recovering[index] = [
        FakeResponse(status_code=503, url=index, headers={}),
        ok(index, ex99_index(ACCESSION)),
    ]
    result, sleeps = run(store, FakeSession(recovering))
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert sleeps == [2]

    store2 = open_local_store(tmp_path / "store2")
    stuck = std_routes()
    stuck[index] = [FakeResponse(status_code=503, url=index, headers={})] * 4
    result2, sleeps2 = run(store2, FakeSession({**stuck, **aapl_routes()}),
                           universe=(PFE, AAPL))
    assert (result2.outcome, result2.exit_code) == ("PARTIAL", 4)
    assert sleeps2 == [2, 4, 8]
    index2 = read_latest_index(store2).index
    assert index2["skipped"][0]["reason"] == "SecGetRefused"


def test_retry_limit_is_four_attempts(tmp_path):
    """Catches: a fifth attempt after four retryable failures."""
    store = open_local_store(tmp_path / "store")
    index = index_url("0000078003", ACCESSION)
    stuck = std_routes()
    stuck[index] = [FakeResponse(status_code=503, url=index, headers={})] * 4
    session = FakeSession(stuck)
    result, _ = run(store, session)
    assert session.calls_for(index) == 4
    assert result.requests_used == 1 + 4
    # A lone issuer whose only filing failed transiently proves nothing new.
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "no_issuer_verified"
    assert read_latest_index(store) is None


# ---------------------------------------------------------------------------
# 14-15: refusals and publish failure
# ---------------------------------------------------------------------------

def test_refusals_make_zero_calls_and_publish_nothing(tmp_path):
    """Catches: a refusal that still touches the network or the store."""
    store = open_local_store(tmp_path / "store")
    session = FakeSession(std_routes())

    bad_ua, _ = run(store, session, user_agent="no-at-sign-here")
    assert (bad_ua.outcome, bad_ua.exit_code) == ("REFUSED", 2)
    assert bad_ua.reason == "user_agent_invalid"
    assert "no-at-sign-here" not in str(bad_ua)
    assert session.calls == []

    empty, _ = run(store, session, universe=())
    assert (empty.outcome, empty.exit_code) == ("REFUSED", 2)
    assert empty.reason == "universe_out_of_range"

    for budget in (0, 151):
        refused, _ = run(store, session, max_requests=budget)
        assert (refused.outcome, refused.exit_code) == ("REFUSED", 2)
        assert refused.reason == "max_requests_invalid"

    assert session.calls == []
    assert read_latest_index(store) is None
    assert store.list_prefix("") == []

    corrupt = open_local_store(tmp_path / "corrupt")
    corrupt.inner.put_bytes(SYNTHETIC_LATEST_KEY, b"garbage-not-json")
    refused_session = FakeSession(std_routes())
    prior, _ = run(corrupt, refused_session)
    assert (prior.outcome, prior.exit_code) == ("REFUSED", 2)
    assert prior.reason == "prior_index_unreadable"
    assert refused_session.calls == []


def test_publish_failure_keeps_prior_pointer(tmp_path, monkeypatch):
    """Catches: a failed publish moving or corrupting the prior latest pointer."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    before = read_latest_index(store)

    def explode(**kwargs):
        raise RuntimeError("sync refused")

    monkeypatch.setattr(csc, "sync_source_roots", explode)
    session = FakeSession({
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), submissions_json([pfe_row()]))],
        archive_document_url(78003, ACCESSION, "ex99-1.htm"): [
            ok(archive_document_url(78003, ACCESSION, "ex99-1.htm"),
               FIXTURE.read_bytes())],
    })
    result, _ = run(store, session, clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("PUBLISH_FAILED", 5)
    after = read_latest_index(store)
    assert after.snapshot_id == before.snapshot_id
    assert after.index == before.index


# ---------------------------------------------------------------------------
# 16: D4 retention
# ---------------------------------------------------------------------------

def test_d4_no_document_bytes_anywhere(tmp_path, monkeypatch):
    """Catches: SEC document bytes persisted to any store, file or side path."""
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden SEC-byte write path called")

    import collectors.sec_document_spine as spine
    import engine.news_impact.edgar_body as edgar_body
    import collectors.edgar_forensics as forensics
    monkeypatch.setattr(spine, "persist_archive_document", forbidden)
    monkeypatch.setattr(spine.SecFilingArchiveCollector, "fetch_document", forbidden)
    monkeypatch.setattr(edgar_body, "_write_text", forbidden)
    monkeypatch.setattr(forensics, "persist_response", forbidden)

    store = open_local_store(tmp_path / "store")
    work_root = tmp_path / "work"
    work_root.mkdir()
    session = FakeSession(std_routes())
    result, _ = run(store, session, work_root=work_root)
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert session.calls, "the cycle must still have run"

    fixture_slice = FIXTURE.read_bytes()[200:264]
    for path in sorted(tmp_path.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            assert fixture_slice not in data, f"document bytes leaked into {path}"
            assert b"Document Format Files" not in data, f"index HTML leaked into {path}"

    raw_store = store.inner
    pointer = json.loads(raw_store.get_bytes(SYNTHETIC_LATEST_KEY))
    manifest = json.loads(raw_store.get_bytes(NAMESPACE_PREFIX + pointer["manifest_key"]))
    raw_entries = [tree["entries"] for tree in manifest["trees"] if tree["kind"] == "raw"][0]
    assert sorted(entry["relative_path"] for entry in raw_entries) == [
        "catalyst/cycle_index.json"]
    index_entry = raw_entries[0]
    stored = raw_store.get_bytes(NAMESPACE_PREFIX + index_entry["object_key"])
    assert index_entry["byte_length"] == len(stored)
    assert work_root.exists() and list(work_root.iterdir()) == []


# ---------------------------------------------------------------------------
# 17: projection parity with the producer
# ---------------------------------------------------------------------------

def test_projection_parity_with_producer(tmp_path):
    """Catches: the writer's figure projection drifting from catalyst_packets."""
    from tests.test_catalyst_packet_public import NOW, _pinned_sec_fixture
    from engine.marketing.catalyst_packets import observation_from_pinned_sec_archive

    raw, authority, key, receipt = _pinned_sec_fixture(tmp_path)
    observation = observation_from_pinned_sec_archive(
        raw, authority=authority, manifest_key=key,
        first_retained_receipt_id=receipt.receipt_id, checked_at_utc=NOW)
    assert observation is not None
    producer = {
        (figure.field, figure.basis, figure.value, figure.span_sha256)
        for figure in observation.verified_figures
    }

    body = FIXTURE.read_bytes()
    source = {"cik": 78003, "name": "Synthetic test issuer",
              "filings": {"recent": {
                  "accessionNumber": [ACCESSION],
                  "form": ["8-K"], "filingDate": ["2026-08-04"],
                  "reportDate": ["2026-06-28"],
                  "acceptanceDateTime": [ACCEPTED],
                  "amendsAccessionNumber": [None],
                  "items": ["2.02,9.01"], "primaryDocument": ["test8k.htm"]}}}
    manifest = build_filing_manifests(
        source, ticker="PFE", recorded_at="2026-08-04T11:03:20Z")[0]
    status, figures, outcome = project_release_figures(
        cik=78003, accession=ACCESSION, body_bytes=body, manifest=manifest,
        exhibit_url=raw["source_url"],
        document_sha256=hashlib.sha256(body).hexdigest())
    mine = {
        (figure["field"], figure["basis"], figure["value"], figure["span_sha256"])
        for figure in figures
    }
    assert (status, outcome) == ("parsed", "figures_projected")
    assert observation.figure_outcome == "figures_projected"
    assert mine == producer
    assert mine, "projection must be non-empty for the release fixture"


PROSE_RELEASE = b"<html><body><p>Acme reports results for the quarter.</p></body></html>"


def _project(body):
    source = {"cik": 78003, "name": "Synthetic test issuer",
              "filings": {"recent": {
                  "accessionNumber": [ACCESSION],
                  "form": ["8-K"], "filingDate": ["2026-08-04"],
                  "reportDate": ["2026-06-28"],
                  "acceptanceDateTime": [ACCEPTED],
                  "amendsAccessionNumber": [None],
                  "items": ["2.02,9.01"], "primaryDocument": ["test8k.htm"]}}}
    manifest = build_filing_manifests(
        source, ticker="PFE", recorded_at="2026-08-04T11:03:20Z")[0]
    return project_release_figures(
        cik=78003, accession=ACCESSION, body_bytes=body, manifest=manifest,
        exhibit_url=archive_document_url(78003, ACCESSION, "ex99-1.htm"),
        document_sha256=hashlib.sha256(body).hexdigest())


def test_projection_names_why_a_release_has_no_figures():
    """Catches: a release without tables reading the same as a binder failure."""
    assert _project(PROSE_RELEASE) == ("no_figures", (), "no_tables")


def test_projection_names_the_failed_step(monkeypatch):
    """Catches: a binder or replay exception publishing as an empty figure list."""
    import engine.earnings_release.binding as binding

    assert _project(b"\xff\xfe not utf-8") == ("parse_failed", (), "document_not_utf8")

    def boom(*args, **kwargs):
        raise RuntimeError("parser broke")

    with monkeypatch.context() as patch:
        patch.setattr(binding, "bind_release_document", boom)
        assert _project(FIXTURE.read_bytes()) == ("parse_failed", (), "binder_exception")
    real_bind = binding.bind_release_document

    def unreplayable(**kwargs):
        bound = real_bind(**kwargs)
        figures = tuple(replace(f, receipt=replace(f.receipt, span_sha256="0" * 64))
                        for f in bound.figures.figures)
        return replace(bound, figures=replace(bound.figures, figures=figures))

    with monkeypatch.context() as patch:
        patch.setattr(binding, "bind_release_document", unreplayable)
        assert _project(FIXTURE.read_bytes()) == ("parse_failed", (), "replay_failed")


def test_cycle_publishes_the_figure_outcome(tmp_path, monkeypatch):
    """Catches: the index dropping the reason a release projected no figures."""
    import engine.earnings_release.binding as binding

    store = open_local_store(tmp_path / "store")
    result, _ = bootstrap(store, tmp_path, routes=std_routes(release_bytes=PROSE_RELEASE))
    assert result.exit_code == 0
    [event] = read_latest_index(store).index["events"]
    assert (event["parse_status"], event["figure_outcome"]) == ("no_figures", "no_tables")
    assert event["figures"] == []

    def boom(*args, **kwargs):
        raise RuntimeError("parser broke")

    monkeypatch.setattr(binding, "bind_release_document", boom)
    store = open_local_store(tmp_path / "store-broken")
    result, _ = bootstrap(store, tmp_path)
    assert result.exit_code == 0
    [event] = read_latest_index(store).index["events"]
    assert (event["parse_status"], event["figure_outcome"]) == (
        "parse_failed", "binder_exception")


def test_index_validates_the_figure_outcome(tmp_path):
    """Catches: an unknown or contradictory figure outcome passing validation."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    index = read_latest_index(store).index
    validate_index(index)
    for bad in ("not_a_code", "no_tables", ["figures_projected"], None):
        broken = json.loads(json.dumps(index))
        broken["events"][0]["figure_outcome"] = bad
        with pytest.raises(ValueError, match="figure_outcome"):
            validate_index(broken)
    legacy = json.loads(json.dumps(index))
    del legacy["events"][0]["figure_outcome"]
    validate_index(legacy)


# ---------------------------------------------------------------------------
# 18-19: namespace isolation and production opener
# ---------------------------------------------------------------------------

def test_namespace_isolation_and_key_refusals(tmp_path):
    """Catches: writes escaping the catalyst namespace or unsafe store keys."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    # .strict-conditional-write.lock is LocalStore's own control-plane file,
    # created at the store root by the capability probe — never SEC data.
    local_control = {".strict-conditional-write.lock"}
    for path in (tmp_path / "store").rglob("*"):
        if path.is_file():
            relative = path.relative_to(tmp_path / "store").as_posix()
            if relative in local_control:
                continue
            assert relative.startswith(NAMESPACE_PREFIX), relative
            assert not relative.startswith("fundamental_forensics/"), relative
    wrapper = NamespacedSourceStore(store.inner)
    assert wrapper.prefix == NAMESPACE_PREFIX
    with pytest.raises(AttributeError):
        wrapper.prefix = "elsewhere/"
    for bad in ("../x", "/x", "a\\b", ""):
        with pytest.raises(ValueError):
            wrapper._k(bad)
    assert isinstance(wrapper.inner, object)


def test_open_production_store_refusals(tmp_path, monkeypatch):
    """Catches: the production opener accepting a local, missing or dead store."""
    from engine.research_vault.r2_store import LocalStore, R2Store

    monkeypatch.setenv("RESEARCH_LOCAL_STORE", str(tmp_path / "local"))
    with pytest.raises(CatalystSourceUnavailable) as caught:
        open_production_store()
    assert str(caught.value) == "research_local_store_set"
    monkeypatch.delenv("RESEARCH_LOCAL_STORE")

    cases = {
        "no_store_available": lambda: None,
        "store_not_r2": lambda: LocalStore(tmp_path / "local"),
    }
    for expected, factory in cases.items():
        monkeypatch.setattr(css, "build_store", factory)
        with pytest.raises(CatalystSourceUnavailable) as caught:
            open_production_store()
        assert str(caught.value) == expected

    def raising_builder():
        raise RuntimeError("builder failed")

    monkeypatch.setattr(css, "build_store", raising_builder)
    with pytest.raises(CatalystSourceUnavailable) as caught:
        open_production_store()
    assert str(caught.value) == "build_store_failed"

    stand_in = object.__new__(R2Store)
    monkeypatch.setattr(R2Store, "available", property(lambda self: False))
    monkeypatch.setattr(css, "build_store", lambda: stand_in)
    with pytest.raises(CatalystSourceUnavailable) as caught:
        open_production_store()
    assert str(caught.value) == "r2_store_unavailable"


# ---------------------------------------------------------------------------
# 20-21: CLI
# ---------------------------------------------------------------------------

def _write_universe(tmp_path, rows):
    path = tmp_path / "universe.json"
    path.write_text(json.dumps({
        "schema": "marketing.catalyst_pilot_universe/v1",
        "issuers": [{"ticker": t, "cik": c, "name": n} for t, c, n in rows],
    }), encoding="utf-8")
    return path


def test_cli_local_store_one_line_no_ua(tmp_path, monkeypatch, capsys):
    """Catches: the CLI printing the user agent or more than one line."""
    universe_path = _write_universe(tmp_path, [("PFE", 78003, "Pfizer Inc.")])
    store_dir = tmp_path / "cli-store"
    monkeypatch.setattr(csc, "new_session", lambda: FakeSession(std_routes()))
    monkeypatch.setattr(csc, "_utc_now", make_clock())
    from scripts.run_catalyst_source_cycle import main
    code = main(["--local-store", str(store_dir), "--universe", str(universe_path),
                 "--user-agent", UA])
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert code == payload["exit_code"] == 0
    assert payload["outcome"] == "COMPLETE"
    assert payload["issuers_ok"] == 1
    assert len(payload["events"]) == 1
    assert payload["snapshot_id"]
    assert UA not in captured.out and UA not in captured.err
    assert read_latest_index(open_local_store(store_dir)) is not None


def test_cli_refuses_local_env_without_session(tmp_path, monkeypatch, capsys):
    """Catches: the CLI reaching a session or leaking values on a store refusal."""
    def forbidden():
        raise AssertionError("no session may be built on refusal")

    monkeypatch.setenv("RESEARCH_LOCAL_STORE", str(tmp_path / "local"))
    monkeypatch.setattr(csc, "new_session", forbidden)
    from scripts.run_catalyst_source_cycle import main
    code = main([])
    captured = capsys.readouterr()
    assert code == 2
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["reason"] == "research_local_store_set"
    assert payload["requests_used"] == 0


# ---------------------------------------------------------------------------
# 22-23: universe config and unit shape
# ---------------------------------------------------------------------------

def test_tracked_universe_loads():
    """Catches: the shipped pilot universe drifting from the 20-issuer contract."""
    issuers = load_universe(Path(__file__).resolve().parents[1]
                            / "config" / "catalyst_pilot_universe.json")
    assert len(issuers) == 20
    assert len({issuer.ticker for issuer in issuers}) == 20
    assert len({issuer.cik for issuer in issuers}) == 20
    assert issuers[0] == UniverseIssuer("AAPL", 320193, "Apple Inc.")
    assert issuers[-1] == UniverseIssuer("UNH", 731766, "UnitedHealth Group Incorporated")


def test_universe_validation(tmp_path):
    """Catches: load_universe accepting shape-invalid universes."""
    base = [{"ticker": "PFE", "cik": 78003, "name": "Pfizer Inc."}]
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, []))
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, [("pfe", 78003, "Pfizer Inc.")]))
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, [("PFE", True, "Pfizer Inc.")]))
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, [("PFE", 78003, "")]))
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, base + [("PFE", 1, "Echo")]))
    with pytest.raises(ValueError):
        load_universe(_write_universe(tmp_path, base + [("OTHER", 78003, "Echo")]))


def test_unit_and_timer_shape():
    """Catches: the shipped units losing hardening or carrying secrets."""
    deploy = Path(__file__).resolve().parents[1] / "app" / "deploy"
    service = (deploy / "macro-catalyst-source-cycle.service").read_text()
    timer = (deploy / "macro-catalyst-source-cycle.timer").read_text()
    assert "-m scripts.run_catalyst_source_cycle" in service
    for line in ("SuccessExitStatus=3 4", "EnvironmentFile=-/etc/macro-api.env",
                 "NoNewPrivileges=true", "ProtectSystem=strict", "PrivateTmp=true",
                 "DynamicUser=true", "Type=oneshot", "TimeoutStartSec=240"):
        assert line in service, line
    assert "OnUnitActiveSec=5min" in timer
    assert "Unit=macro-catalyst-source-cycle.service" in timer
    assert "OnBootSec=2min" in timer and "AccuracySec=30s" in timer
    assert "WantedBy=timers.target" in timer
    for text in (service, timer):
        for needle in ("@", "SECRET", "KEY=", "TOKEN"):
            assert needle not in text, needle


# ---------------------------------------------------------------------------
# 24: window expiry
# ---------------------------------------------------------------------------

def test_window_expiry_drops_prior_event(tmp_path):
    """Catches: an expired event surviving past its seven-day window."""
    store = open_local_store(tmp_path / "store")
    old = submissions_json([pfe_row(accepted="2026-07-01T11:02:43Z")])
    first, _ = run(store, FakeSession(std_routes(submissions_bytes=old)),
                   clock=make_clock(datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)))
    assert (first.outcome, first.exit_code) == ("COMPLETE", 0)
    assert len(read_latest_index(store).index["events"]) == 1

    session = FakeSession(std_routes(submissions_bytes=old))
    result, _ = run(store, session, clock=make_clock(datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)
    assert session.urls() == [endpoint_url(78003, "submissions")]
    index = read_latest_index(store).index
    assert index["events"] == []
    assert index["issuers"][0]["status"] == "ok"


# ---------------------------------------------------------------------------
# Extra index-contract checks exercised above
# ---------------------------------------------------------------------------

def test_index_validates_and_sorts_events(tmp_path):
    """Catches: a published index that fails its own schema validation."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    result, _ = run(store, FakeSession(routes), universe=(PFE, AAPL))
    assert result.exit_code == 0
    index = read_latest_index(store).index
    validate_index(index)
    order = [(event["acceptance_datetime"], event["filing_key"]) for event in index["events"]]
    by_filing = sorted(index["events"], key=lambda event: event["filing_key"])
    expected = sorted(by_filing, key=lambda event: event["acceptance_datetime"], reverse=True)
    assert order == [(event["acceptance_datetime"], event["filing_key"]) for event in expected]
    assert [event["ticker"] for event in index["events"]] == ["AAPL", "PFE"]


# ---------------------------------------------------------------------------
# Part-2a repairs: halts, carry, deferral, row-bound href, namespace, UA, CLI
# ---------------------------------------------------------------------------

def test_403_halts_cycle_and_publishes_swept_issuers(tmp_path):
    """Catches: retrying or continuing to hit SEC after a 403 access refusal."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    aapl_submissions = endpoint_url(320193, "submissions")
    routes[aapl_submissions] = [FakeResponse(status_code=403, url=aapl_submissions,
                                             headers={})]
    session = FakeSession(routes)
    result, sleeps = run(store, session, universe=(PFE, AAPL))
    assert (result.outcome, result.exit_code) == ("TRUNCATED", 3)
    assert result.reason == "sec_access_refused"
    assert result.snapshot_id is not None
    assert session.calls_for(aapl_submissions) == 1
    assert sleeps == []
    assert result.requests_used == 4
    assert _issuer_reason(store, "PFE") == ("ok", None)
    assert _issuer_reason(store, "AAPL") == ("not_checked", "sec_access_refused")


def test_403_before_any_sweep_stops_all_requests(tmp_path):
    """Catches: a 403 on one issuer letting later issuers still be requested."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    pfe_index = index_url("0000078003", ACCESSION)
    routes[pfe_index] = [FakeResponse(status_code=403, url=pfe_index, headers={})]
    session = FakeSession(routes)
    result, _ = run(store, session, universe=(PFE, AAPL))
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "sec_access_refused"
    assert session.urls() == [endpoint_url(78003, "submissions"), pfe_index]
    assert not any(url in aapl_routes() for url in session.urls())
    assert read_latest_index(store) is None


def test_persistent_429_halts_after_backoff(tmp_path):
    """Catches: a 429 that outlasts the retries not halting the cycle."""
    store = open_local_store(tmp_path / "store")
    routes = {**std_routes(), **aapl_routes()}
    aapl_submissions = endpoint_url(320193, "submissions")
    routes[aapl_submissions] = [FakeResponse(status_code=429, url=aapl_submissions,
                                             headers={})] * 4
    session = FakeSession(routes)
    result, sleeps = run(store, session, universe=(PFE, AAPL))
    assert (result.outcome, result.exit_code) == ("TRUNCATED", 3)
    assert result.reason == "sec_rate_limited"
    assert sleeps == [2, 4, 8]
    assert session.calls_for(aapl_submissions) == 4
    assert _issuer_reason(store, "AAPL") == ("not_checked", "sec_rate_limited")


def test_failed_issuer_carries_prior_event_with_original_receipt(tmp_path):
    """Catches: a failed sweep dropping an issuer's still-valid prior event."""
    store = open_local_store(tmp_path / "store")
    first, _ = bootstrap(store, tmp_path, universe=(PFE, AAPL),
                         routes={**std_routes(), **aapl_routes()})
    assert first.exit_code == 0
    prior = {event["ticker"]: event for event in read_latest_index(store).index["events"]}

    wrong_cik = submissions_json([pfe_row()], cik="39044")
    routes = {
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), wrong_cik)],
        **{url: queue for url, queue in aapl_routes().items()
           if "-index.htm" not in url},
    }
    result, _ = run(store, FakeSession(routes), universe=(PFE, AAPL),
                    clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    index = read_latest_index(store).index
    assert _issuer_reason(store, "PFE") == ("failed", "identity_mismatch")
    carried = {event["ticker"]: event for event in index["events"]}
    assert carried["PFE"] == prior["PFE"]
    assert (carried["PFE"]["retention"]["first_retained_receipt_id"]
            == prior["PFE"]["retention"]["first_retained_receipt_id"])
    assert _issuer_reason(store, "AAPL") == ("ok", None)


def test_transient_reverify_failure_defers_without_dropping(tmp_path):
    """Catches: a transient carried-document failure discarding the receipt."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path, universe=(PFE, AAPL),
              routes={**std_routes(), **aapl_routes()})
    prior = {event["ticker"]: event for event in read_latest_index(store).index["events"]}

    document = archive_document_url(78003, ACCESSION, "ex99-1.htm")
    routes = {
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), submissions_json([pfe_row()]))],
        document: [FakeResponse(status_code=503, url=document, headers={})] * 4,
        **{url: queue for url, queue in aapl_routes().items()
           if "-index.htm" not in url},
    }
    result, sleeps = run(store, FakeSession(routes), universe=(PFE, AAPL),
                         clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("PARTIAL", 4)
    assert sleeps == [2, 4, 8]
    index = read_latest_index(store).index
    assert _issuer_reason(store, "PFE")[0] == "incomplete"
    assert index["skipped"] == [{"ticker": "PFE", "accession": ACCESSION,
                                 "reason": "reverify_deferred"}]
    carried = {event["ticker"]: event for event in index["events"]}
    assert carried["PFE"] == prior["PFE"]
    assert _issuer_reason(store, "AAPL") == ("ok", None)


def test_all_deferred_reverify_keeps_prior_pointer(tmp_path):
    """Catches: a cycle that only deferred re-verifies publishing an index that serves nothing."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    prior = read_latest_index(store)

    document = archive_document_url(78003, ACCESSION, "ex99-1.htm")
    routes = {
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), submissions_json([pfe_row()]))],
        document: [FakeResponse(status_code=503, url=document, headers={})] * 4,
    }
    result, _ = run(store, FakeSession(routes),
                    clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "no_issuer_verified"
    assert (result.issuers_ok, result.issuers_incomplete) == (0, 1)
    assert result.snapshot_id is None
    after = read_latest_index(store)
    assert after.snapshot_id == prior.snapshot_id
    assert after.index == prior.index


def test_deferred_reverify_plus_new_skip_keeps_prior_pointer(tmp_path):
    """Catches: a new filing's no-EX-99.1 skip counting as verified work, so an
    index that serves nothing (issuer incomplete) replaces one that served it."""
    store = open_local_store(tmp_path / "store")
    bootstrap(store, tmp_path)
    prior = read_latest_index(store)

    new_accession = "0000078003-26-000099"
    document = archive_document_url(78003, ACCESSION, "ex99-1.htm")
    routes = {
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"), submissions_json([
                pfe_row(),
                pfe_row(accession=new_accession, accepted="2026-08-05T09:00:00Z"),
            ]))],
        document: [FakeResponse(status_code=503, url=document, headers={})] * 4,
        index_url("0000078003", new_accession): [
            ok(index_url("0000078003", new_accession), index_html([]))],
    }
    result, _ = run(store, FakeSession(routes),
                    clock=make_clock(datetime(2026, 8, 5, 13, 0, 0, tzinfo=UTC)))
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "no_issuer_verified"
    assert result.snapshot_id is None
    after = read_latest_index(store)
    assert after.snapshot_id == prior.snapshot_id
    assert after.index == prior.index


def test_lone_unattested_amendment_bootstrap_publishes_nothing(tmp_path):
    """Catches: a cycle whose only work was a skip publishing an index that serves nothing."""
    store = open_local_store(tmp_path / "store")
    routes = {
        endpoint_url(78003, "submissions"): [
            ok(endpoint_url(78003, "submissions"),
               submissions_json([pfe_row(form="8-K/A", amends=None)]))],
    }
    result, _ = run(store, FakeSession(routes))
    assert (result.outcome, result.exit_code) == ("FAILED", 6)
    assert result.reason == "no_issuer_verified"
    assert read_latest_index(store) is None


def _index_with_exhibit_cell(cell_html):
    return (
        "<html><body><table summary=\"Document Format Files\">"
        "<tr><th scope=\"col\">Seq</th><th scope=\"col\">Description</th>"
        "<th scope=\"col\">Document</th><th scope=\"col\">Type</th>"
        "<th scope=\"col\">Size</th></tr>"
        "<tr><td scope=\"row\">1</td><td scope=\"row\">EX-99.1</td>"
        f"<td scope=\"row\">{cell_html}</td><td scope=\"row\">EX-99.1</td>"
        "<td scope=\"row\">1234</td></tr>"
        "</table></body></html>"
    ).encode("utf-8")


def test_exhibit_row_href_must_be_the_issuer_direct_link(tmp_path):
    """Catches: binding the CIK check to some other link than the EX-99.1 row's own."""
    direct = f"{archive_dir(ACCESSION)}/ex99-1.htm"
    foreign_accession = f"{archive_dir('0000078003-26-000001')}/ex99-1.htm"
    cases = {
        "two_links": (f"<a href=\"{direct}\">ex99-1.htm</a>"
                      f"<a href=\"/Archives/edgar/data/9999999/x/ex99-1.htm\">x</a>"),
        "foreign_accession": f"<a href=\"{foreign_accession}\">ex99-1.htm</a>",
    }
    for name, cell in cases.items():
        store = open_local_store(tmp_path / name)
        result, _, pfe_urls = bootstrap_with_ok_peer(
            store, tmp_path, routes=std_routes(index_bytes=_index_with_exhibit_cell(cell)))
        assert result.exit_code == 4, name
        assert not any(url.endswith("ex99-1.htm") for url in pfe_urls), name
        assert read_latest_index(store).index["skipped"][0]["reason"] == \
            "exhibit_cik_mismatch", name

    viewer = open_local_store(tmp_path / "viewer")
    cell = f"<a href=\"/ix?doc={direct}\">ex99-1.htm</a>"
    result, _ = bootstrap(viewer, tmp_path,
                          routes=std_routes(index_bytes=_index_with_exhibit_cell(cell)))
    assert (result.outcome, result.exit_code) == ("COMPLETE", 0)


def test_store_outside_catalyst_namespace_refused(tmp_path):
    """Catches: the writer publishing through a store not scoped to its namespace."""
    store = open_local_store(tmp_path / "store")
    session = FakeSession(std_routes())
    result, _ = run(store.inner, session)
    assert (result.outcome, result.exit_code) == ("REFUSED", 2)
    assert result.reason == "store_not_catalyst_namespace"

    class ForeignPrefix(NamespacedSourceStore):
        @property
        def prefix(self):
            return "fundamental_forensics/"

    foreign = ForeignPrefix(store.inner)
    result2, _ = run(foreign, session)
    assert (result2.outcome, result2.exit_code) == ("REFUSED", 2)
    assert result2.reason == "store_not_catalyst_namespace"
    assert session.calls == []
    assert read_latest_index(store) is None


@pytest.mark.parametrize("agent", [
    "catalyst-test admin@example.invalid\r\nX-Injected: y",
    "catalyst-" + "x" * 260 + " admin@example.invalid",
    "admin@example.invalid",
    "catalyst-test",
    "catalyst-test admin@example.invalid\u00e9",
])
def test_user_agent_validator_refuses_unsafe_values(tmp_path, agent):
    """Catches: header injection, unbounded or contactless SEC user agents."""
    store = open_local_store(tmp_path / "store")
    session = FakeSession(std_routes())
    result, _ = run(store, session, user_agent=agent)
    assert (result.outcome, result.exit_code) == ("REFUSED", 2)
    assert result.reason == "user_agent_invalid"
    assert agent not in str(result)
    assert session.calls == []


def test_cli_without_user_agent_refuses_and_never_reads_config(tmp_path, monkeypatch,
                                                               capsys):
    """Catches: the CLI inheriting another collector's tracked SEC contact."""
    def forbidden():
        raise AssertionError("no session may be built without a user agent")

    universe_path = _write_universe(tmp_path, [("PFE", 78003, "Pfizer Inc.")])
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.setattr(csc, "new_session", forbidden)
    from scripts.run_catalyst_source_cycle import main
    code = main(["--local-store", str(tmp_path / "cli-store"),
                 "--universe", str(universe_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert code == payload["exit_code"] == 2
    assert payload["reason"] == "user_agent_unresolved"
    assert payload["requests_used"] == 0
    assert read_latest_index(open_local_store(tmp_path / "cli-store")) is None


def test_cli_max_requests_reaches_the_cycle(tmp_path, monkeypatch, capsys):
    """Catches: the CLI parsing --max-requests but running on the default budget."""
    universe_path = _write_universe(tmp_path, [("PFE", 78003, "Pfizer Inc.")])
    session = FakeSession(std_routes())
    monkeypatch.setattr(csc, "new_session", lambda: session)
    monkeypatch.setattr(csc, "_utc_now", make_clock())
    from scripts.run_catalyst_source_cycle import main
    code = main(["--local-store", str(tmp_path / "cli-store"), "--universe", str(universe_path),
                 "--user-agent", UA, "--max-requests", "1"])
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == payload["exit_code"] == 6
    assert payload["reason"] == "budget_exhausted"
    assert payload["requests_used"] == 1
    assert len(session.calls) == 1
    assert read_latest_index(open_local_store(tmp_path / "cli-store")) is None

    code = main(["--local-store", str(tmp_path / "cli-store"), "--universe", str(universe_path),
                 "--user-agent", UA, "--max-requests", "0"])
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == payload["exit_code"] == 2
    assert payload["reason"] == "max_requests_invalid"
