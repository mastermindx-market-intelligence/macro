"""A3-R reader/wiring tests: loader-injected indexes, writer end-to-end, HTTP.

No network, no R2, no real SEC request. Every test fails admission closed and
clears the rights cache afterwards via the autouse fixture.
"""
import builtins
import io
import json
import logging
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import catalyst_integration as ci
from app import catalyst_source_wiring as wiring
from engine.marketing import catalyst_admission
from engine.marketing import catalyst_scan
from engine.marketing import catalyst_source_store as css
from engine.marketing.catalyst_packets import (
    STAGE_A_PACKET_SCHEMA, VerifiedDocumentObservation, VerifiedEarningsFigure)
from engine.marketing.catalyst_source_adapter import build_admitted_source
from engine.marketing.catalyst_source_store import (
    LatestIndex, open_local_store, read_latest_index)
from engine.research_vault import r2_store as r2_store_module
from engine.theme_graph import rights
from tests.test_catalyst_source_cycle import (
    AAPL, ACCESSION, FakeSession, FIXTURE, PFE, archive_document_url, make_clock,
    pfe_row, run, std_routes, submissions_json)

UTC = timezone.utc
import hashlib

EXHIBIT_URL = archive_document_url(78003, ACCESSION, "ex99-1.htm")
DOC_SHA = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
EPS_SPAN = hashlib.sha256(b"eps_actual:gaap").hexdigest()
REV_SPAN = hashlib.sha256(b"rev_actual:reported").hexdigest()
SNAPSHOT_ID = "snap-a3r2-0001"
FK = "%010d:%s" % (78003, ACCESSION)
SOURCE_ID = "sec:" + FK
UNIVERSE = (PFE, AAPL)
RECEIPT = "catsec-" + "a" * 36
TARGET_FAMILY_YAML = (
    "families:\n"
    "  sec_issuer_earnings_release_facts:\n"
    "    rights_class: derived_display_ok\n"
    "    auth_class: keyless_public\n"
)
_ADMISSION_FILE = Path(__file__).resolve().parents[1] / \
    "engine/marketing/catalyst_admission.py"


@pytest.fixture(autouse=True)
def _fail_closed_after():
    # Every test leaves admission unconfigured and the rights cache cleared.
    yield
    catalyst_admission.configure(None)
    rights._load.cache_clear()


@pytest.fixture
def target_registry(tmp_path, monkeypatch):
    """A TEMP registry carrying only the production target family row."""
    path = tmp_path / "rights.yml"
    path.write_text(TARGET_FAMILY_YAML, encoding="utf-8")
    monkeypatch.setattr(rights, "registry_path", lambda: path)
    rights._load.cache_clear()
    yield path
    rights._load.cache_clear()


def install_registry(monkeypatch, tmp_path, yaml_text):
    path = tmp_path / "rights_adhoc.yml"
    path.write_text(yaml_text, encoding="utf-8")
    monkeypatch.setattr(rights, "registry_path", lambda: path)
    rights._load.cache_clear()


def _fmt(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _universe_file(tmp_path, rows=None):
    if rows is None:
        rows = [{"ticker": "PFE", "cik": 78003, "name": "Pfizer Inc."},
                {"ticker": "AAPL", "cik": 320193, "name": "Apple Inc."}]
    path = tmp_path / "universe.json"
    path.write_text(json.dumps(
        {"schema": "marketing.catalyst_pilot_universe/v1", "issuers": rows}),
        encoding="utf-8")
    return str(path)


_ISSUER_FACTS = {"PFE": (78003, "Pfizer Inc."), "AAPL": (320193, "Apple Inc.")}


def _issuer_row(ticker, *, status="ok", reason=None, cik=None, issuer_id=None):
    base_cik, name = _ISSUER_FACTS[ticker]
    cik = base_cik if cik is None else cik
    row = {"ticker": ticker, "cik": cik, "name": name,
           "issuer_id": issuer_id or "cik:%010d" % cik,
           "status": status, "reason": reason}
    return row


def _record(now, *, cycle=None, ticker="PFE", cik=78003, accession=ACCESSION,
            form="8-K", items=("2.02",), exhibit_type="EX-99.1", url=None,
            sha=None, accepted=None, first=None, last=None, figures=None,
            amends="", generation=0, parse_status="parsed", filing_key=None,
            filing_date="2026-10-28"):
    t_start, t_complete = cycle or (now - timedelta(minutes=5),
                                    now - timedelta(minutes=4))
    url = url or ("https://www.sec.gov/Archives/edgar/data/%d/%s/ex99-1.htm"
                  % (cik, accession.replace("-", "")))
    sha = sha or DOC_SHA
    accepted = now - timedelta(hours=2) if accepted is None else accepted
    first = t_complete if first is None else first
    last = t_complete if last is None else last
    figures = figures if figures is not None else [
        {"field": "eps_actual", "basis": "gaap", "value": 2.18,
         "span_sha256": EPS_SPAN},
        {"field": "rev_actual", "basis": "reported", "value": 8412000000.0,
         "span_sha256": REV_SPAN},
    ]
    return {
        "ticker": ticker, "cik": cik, "accession": accession,
        "filing_key": filing_key or "%010d:%s" % (cik, accession),
        "form": form, "items": list(items), "filing_date": filing_date,
        "report_date": "2026-09-30",
        "acceptance_datetime": _fmt(accepted),
        "exhibit": {"exhibit_type": exhibit_type, "source_url": url,
                    "document_sha256": sha, "byte_length": 43007},
        "retention": {"first_retained_at": _fmt(first),
                      "first_retained_receipt_id": RECEIPT,
                      "last_verified_at": _fmt(last)},
        "figures": [dict(figure) for figure in figures],
        "lineage": {"amends_filing_key": amends,
                    "correction_generation": generation},
        "parse_status": parse_status,
    }


def _index(now, *, events=None, issuers=None, cycle=None, **top):
    t_start, t_complete = cycle or (now - timedelta(minutes=5),
                                    now - timedelta(minutes=4))
    if events is None:
        events = [_record(now, cycle=(t_start, t_complete))]
    if issuers is None:
        issuers = [_issuer_row(ticker)
                   for ticker in sorted({event["ticker"] for event in events})]
    index = {
        "schema": "marketing.catalyst_sec_cycle_index/v1",
        "cycle_started_at": _fmt(t_start),
        "cycle_completed_at": _fmt(t_complete),
        "window_start": _fmt(t_start - timedelta(days=7)),
        "window_end": _fmt(t_start),
        "requests_used": 3, "request_budget": 150,
        "outcome": "COMPLETE", "truncated": False,
        "issuers": issuers, "events": events, "skipped": [],
    }
    index.update(top)
    return index


def _loader_for(index, snapshot_id=SNAPSHOT_ID):
    calls = {"n": 0}

    def loader(store):
        calls["n"] += 1
        return LatestIndex(index=index, snapshot_id=snapshot_id,
                           snapshot_at=datetime.now(UTC), manifest_key="m")
    loader.calls = calls
    return loader


def _configure(index, now, *, universe=UNIVERSE, snapshot_id=SNAPSHOT_ID):
    loader = _loader_for(index, snapshot_id)
    source = build_admitted_source(object(), universe=universe,
                                   clock=lambda: now, loader=loader)
    catalyst_admission.configure(source)
    return source, loader


def _scan(tickers, now):
    # The raw producer read: sanitize_public_scan deliberately refuses an
    # unavailable source with a 503, so negative assertions go through the
    # unsanitized compose path.
    return catalyst_scan.scan_tickers(list(tickers), now_utc=now)


def _row(scan, ticker):
    return next(result for result in scan["results"]
                if result["ticker"] == ticker)


def _texts(result):
    return json.dumps(result.get("what_changed") or [])


NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 1-10: freshness, store failures, record validation
# ---------------------------------------------------------------------------

def test_01_happy_path_loader_to_supported_scan(tmp_path, target_registry):
    # Catches: an adapter that cannot turn a fresh valid index into a SUPPORTED Stage-A v2 scan.
    now = NOW
    _configure(_index(now), now)
    scan = ci.scan_with_reader(["PFE"], now_utc=now)
    assert scan["schema"] == "catalyst.scan/v2"
    assert scan["schema_version"] == 2
    pfe = _row(scan, "PFE")
    assert pfe["status"] == "SUPPORTED"
    assert pfe["sources"][0]["rights_receipt_id"] == RECEIPT
    assert "2.18" in _texts(pfe)
    assert "8,412,000,000" in _texts(pfe)


def test_02_stale_snapshot_fails_closed(tmp_path, target_registry):
    # Catches: a snapshot older than the 10-minute MAX_SNAPSHOT_AGE being served.
    now = NOW
    cycle = (now - timedelta(minutes=12), now - timedelta(minutes=11))
    source, _ = _configure(_index(now, cycle=cycle), now)
    assert source.issuer_universe(now) == {}
    assert source.source_coverage(now - timedelta(days=7), now, now) is None
    assert source.public_grant(SOURCE_ID, now) is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_03_future_snapshot_fails_closed(tmp_path, target_registry):
    # Catches: a cycle started or completed in the future being served.
    now = NOW
    for cycle in ((now + timedelta(minutes=2), now + timedelta(minutes=3)),
                  (now - timedelta(minutes=5), now + timedelta(minutes=2))):
        source, _ = _configure(_index(now, cycle=cycle), now)
        assert source.issuer_universe(now) == {}
        assert source.source_coverage(now - timedelta(days=7), now, now) is None
        assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_04_missing_pointer_reads_empty(tmp_path, target_registry):
    # Catches: an empty store being read as coverage instead of failing closed.
    now = NOW
    store = open_local_store(tmp_path / "store")
    source = build_admitted_source(store, universe=UNIVERSE, clock=lambda: now)
    catalyst_admission.configure(source)
    assert source.issuer_universe(now) == {}
    assert source.recent_events(now - timedelta(days=7), now, 20) == []
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_05_invalid_pointer_reads_empty(tmp_path, target_registry):
    # Catches: garbage bytes at the namespaced latest pointer being served as an index.
    now = NOW
    store = open_local_store(tmp_path / "store")
    store.put_bytes("fundamental_forensics/sec-source/v1/latest.json",
                    b"\xff\xfe not-json-at-all")
    source = build_admitted_source(store, universe=UNIVERSE, clock=lambda: now)
    catalyst_admission.configure(source)
    assert source.issuer_universe(now) == {}
    assert source.source_coverage(now - timedelta(days=7), now, now) is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_06_accession_mismatch_fails_issuer(tmp_path, target_registry):
    # Catches: a filing_key that is not cik:accession being admitted.
    now = NOW
    bad = _record(now, filing_key="0000078003:0000078003-26-000099")
    source, _ = _configure(_index(now, events=[bad]), now)
    assert source.issuer_universe(now)["PFE"]["supported"] is False
    assert source.public_grant("sec:0000078003:0000078003-26-000099", now) is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] == "NOT_COVERED"


def test_07_universe_cik_mismatch_fails_issuer(tmp_path, target_registry):
    # Catches: an index issuer whose (ticker, cik) matches no universe row being admitted.
    now = NOW
    issuers = [_issuer_row("PFE", cik=320193)]
    event = _record(now, ticker="PFE", cik=320193)
    source, _ = _configure(_index(now, events=[event], issuers=issuers), now)
    assert source.issuer_universe(now)["PFE"]["supported"] is False
    assert source.public_grant("sec:%010d:%s" % (320193, ACCESSION), now) is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] == "NOT_COVERED"


def test_08_retention_clock_mismatch_fails_issuer(tmp_path, target_registry):
    # Catches: retention clocks outside acceptance..cycle being admitted.
    now = NOW
    for kwargs in ({"first": now - timedelta(hours=3)},
                   {"last": now - timedelta(minutes=6)}):
        event = _record(now, **kwargs)
        source, _ = _configure(_index(now, events=[event]), now)
        assert source.issuer_universe(now)["PFE"]["supported"] is False, kwargs
        assert source.public_grant(SOURCE_ID, now) is None, kwargs
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_09_non_sec_urls_never_granted(tmp_path, target_registry):
    # Catches: a grant minted from a non-SEC or third-party lookalike URL.
    now = NOW
    for url in ("https://example.com/ex99_1_release.htm",
                "https://sec.gov.example.net/Archives/edgar/data/78003/"
                "000007800326000094/ex99-1.htm",
                "http://www.sec.gov/Archives/edgar/data/78003/"
                "000007800326000094/ex99-1.htm"):
        event = _record(now, url=url)
        source, _ = _configure(_index(now, events=[event]), now)
        assert source.public_grant(SOURCE_ID, now) is None, url
        scan = _scan(["PFE"], now)
        assert _row(scan, "PFE")["status"] != "SUPPORTED", url
        assert url not in json.dumps(scan)


def test_10_figure_sha_mismatch_blocks_packet(tmp_path, target_registry):
    # Catches: figure evidence whose document_sha256 differs from the observed record sha.
    now = NOW
    source, _ = _configure(_index(now), now)
    real_observation = source.document_observation

    def tampered(event, at):
        observation = real_observation(event, at)
        figures = tuple(
            VerifiedEarningsFigure(
                field=figure.field, value=figure.value, basis=figure.basis,
                document_sha256="0" * 64, span_sha256=figure.span_sha256)
            for figure in observation.verified_figures)
        return replace(observation, verified_figures=figures)

    catalyst_admission.configure(catalyst_admission.AdmittedEdgarSource(
        issuer_universe=source.issuer_universe,
        recent_events=source.recent_events,
        public_grant=source.public_grant,
        document_observation=tampered,
        source_coverage=source.source_coverage))
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


# ---------------------------------------------------------------------------
# 11-15: F4 identity, truthful truncation, partial cycles
# ---------------------------------------------------------------------------

def test_11_f4_exhibit_type_gate(tmp_path, target_registry):
    # Catches: F4(a) — exhibits other than the issuer's own EX-99.1 being granted.
    now = NOW
    cases = ({"exhibit_type": "EX-99.2"},
             {"exhibit_type": "8-K",
              "url": ("https://www.sec.gov/Archives/edgar/data/78003/"
                      "000007800326000094/0000078003-26-000094-8k.htm")})
    for kwargs in cases:
        event = _record(now, **kwargs)
        source, _ = _configure(_index(now, events=[event]), now)
        assert source.public_grant(SOURCE_ID, now) is None, kwargs
        scan = _scan(["PFE"], now)
        assert _row(scan, "PFE")["status"] != "SUPPORTED", kwargs
        assert event["exhibit"]["source_url"] not in json.dumps(scan)


def test_12_f4_url_cik_gate(tmp_path, target_registry):
    # Catches: F4(b) — an archive URL under another issuer's CIK directory being granted.
    now = NOW
    foreign = _record(now, url=("https://www.sec.gov/Archives/edgar/data/320193/"
                                "000007800326000094/ex99-1.htm"))
    source, _ = _configure(_index(now, events=[foreign]), now)
    assert source.public_grant(SOURCE_ID, now) is None
    scan = _scan(["PFE"], now)
    assert _row(scan, "PFE")["status"] != "SUPPORTED"
    assert foreign["exhibit"]["source_url"] not in json.dumps(scan)
    # Second case: index cik differs from the universe cik for the ticker.
    issuers = [_issuer_row("PFE", cik=78004)]
    event = _record(now, ticker="PFE", cik=78004)
    source2, _ = _configure(_index(now, events=[event], issuers=issuers), now)
    assert source2.public_grant("sec:%010d:%s" % (78004, ACCESSION), now) is None
    scan2 = _scan(["PFE"], now)
    assert _row(scan2, "PFE")["status"] != "SUPPORTED"
    assert event["exhibit"]["source_url"] not in json.dumps(scan2)


def test_13_f4_form_and_item_gate(tmp_path, target_registry):
    # Catches: F4(c) — non-8-K forms or filings without Item 2.02 being granted.
    now = NOW
    for kwargs in ({"form": "10-Q"}, {"items": ("8.01",)}):
        event = _record(now, **kwargs)
        source, _ = _configure(_index(now, events=[event]), now)
        assert source.public_grant(SOURCE_ID, now) is None, kwargs
        scan = _scan(["PFE"], now)
        assert _row(scan, "PFE")["status"] != "SUPPORTED", kwargs
        assert EXHIBIT_URL not in json.dumps(scan)


def test_14_truncated_cycle_is_truthful(tmp_path, target_registry):
    # Catches: a truncated or over-limit cycle being reported COMPLETE.
    now = NOW
    source, _ = _configure(_index(now, truncated=True, outcome="TRUNCATED"), now)
    coverage = source.source_coverage(now - timedelta(days=7), now, now)
    assert coverage.outcome == "TRUNCATED"
    assert coverage.truncated is True
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"
    # 21 OK in-window events exceed EVENT_LIMIT and must read TRUNCATED.
    events = []
    for i in range(1, 22):
        accession = "0000078003-26-%06d" % i
        events.append(_record(now, accession=accession,
                              accepted=now - timedelta(hours=2, minutes=i)))
    source2, _ = _configure(_index(now, events=events), now)
    coverage2 = source2.source_coverage(now - timedelta(days=7), now, now)
    assert coverage2.outcome == "TRUNCATED"
    assert coverage2.truncated is True
    assert len(source2.recent_events(now - timedelta(days=7), now, 20)) == 20
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_15_partial_failed_issuer_isolated(tmp_path, target_registry):
    # Catches: one failed issuer hiding or poisoning the other issuers' coverage.
    now = NOW
    issuers = [_issuer_row("PFE"),
               _issuer_row("AAPL", status="failed", reason="http_error")]
    source, _ = _configure(_index(now, events=[_record(now)], issuers=issuers,
                                  outcome="PARTIAL"), now)
    coverage = source.source_coverage(now - timedelta(days=7), now, now)
    assert coverage.outcome == "COMPLETE"
    assert coverage.issuer_tickers == frozenset({"PFE"})
    universe = source.issuer_universe(now)
    assert universe["PFE"]["supported"] is True
    assert universe["AAPL"]["supported"] is False
    scan = ci.scan_with_reader(["PFE", "AAPL"], now_utc=now)
    assert _row(scan, "PFE")["status"] == "SUPPORTED"
    assert _row(scan, "AAPL")["status"] == "NOT_COVERED"


# ---------------------------------------------------------------------------
# 16-18: F1 rights family
# ---------------------------------------------------------------------------

def test_16_f1_no_legacy_family_fallback(tmp_path, monkeypatch, target_registry):
    # Catches: F1 — the family name falling back to the legacy sec_edgar row.
    now = NOW
    install_registry(monkeypatch, tmp_path, (
        "families:\n"
        "  sec_edgar:\n"
        "    rights_class: direct_display_ok\n"
        "    auth_class: keyless_public\n"))
    _configure(_index(now), now)
    packets, issuers, coverage = catalyst_admission.read_qualified_event_context(now)
    assert packets == () and issuers == {} and coverage is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_17_f1_class_gate_refuses_internal_only(tmp_path, monkeypatch):
    # Catches: an internal_only rights class being emitted publicly.
    now = NOW
    install_registry(monkeypatch, tmp_path, (
        "families:\n"
        "  sec_issuer_earnings_release_facts:\n"
        "    rights_class: internal_only\n"
        "    auth_class: keyless_public\n"))
    _configure(_index(now), now)
    packets, issuers, coverage = catalyst_admission.read_qualified_event_context(now)
    assert packets == () and issuers == {} and coverage is None
    assert _row(_scan(["PFE"], now), "PFE")["status"] != "SUPPORTED"


def test_18_f1_rights_family_constant():
    # Catches: the admission seam drifting back to the legacy family name.
    assert catalyst_admission.RIGHTS_FAMILY == "sec_issuer_earnings_release_facts"
    assert "sec_edgar" not in _ADMISSION_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 19-24: wiring
# ---------------------------------------------------------------------------

def _forbid_production_store(monkeypatch):
    def boom():
        raise AssertionError("open_production_store must not be called")
    monkeypatch.setattr(css, "open_production_store", boom)


def test_19_wiring_flag_off(tmp_path, monkeypatch):
    # Catches: wiring touching the store or admission when the flag is off.
    for value in (None, "true"):
        monkeypatch.delenv("CATALYST_PUBLIC_ENABLED", raising=False)
        if value is not None:
            monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", value)
        _forbid_production_store(monkeypatch)
        assert wiring.configure_from_environment() is False
        assert catalyst_admission._current is None


def test_20_wiring_local_store_refused(tmp_path, monkeypatch):
    # Catches: wiring configuring over a local research store.
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("RESEARCH_LOCAL_STORE", str(tmp_path))
    _forbid_production_store(monkeypatch)
    assert wiring.configure_from_environment() is False
    assert catalyst_admission._current is None


def test_21_wiring_non_r2_store_refused(tmp_path, monkeypatch):
    # Catches: wiring accepting a store whose inner store is not an R2Store.
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)
    store = open_local_store(tmp_path / "store")
    monkeypatch.setattr(css, "open_production_store", lambda: store)
    assert wiring.configure_from_environment() is False
    assert catalyst_admission._current is None


def test_22_wiring_exception_logs_type_only(tmp_path, monkeypatch, caplog):
    # Catches: wiring leaking exception detail (values) into logs.
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)

    def boom():
        raise RuntimeError("secret-looking-text")
    monkeypatch.setattr(css, "open_production_store", boom)
    with caplog.at_level(logging.WARNING, logger="macro.api"):
        assert wiring.configure_from_environment() is False
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in joined
    assert "secret-looking-text" not in joined
    assert catalyst_admission._current is None


def test_23_wiring_success_configures_admission(tmp_path, monkeypatch):
    # Catches: wiring refusing a real production store.
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)

    class _FakeR2Store:
        def __init__(self):
            self.available = True

    monkeypatch.setattr(r2_store_module, "R2Store", _FakeR2Store)
    store = css.NamespacedSourceStore(_FakeR2Store())
    monkeypatch.setattr(css, "open_production_store", lambda: store)
    assert wiring.configure_from_environment() is True
    assert catalyst_admission._current is not None
    now = NOW
    packets, issuers, coverage = catalyst_admission.read_qualified_event_context(now)
    assert issuers == {}  # empty store fails closed, never raises


def test_24_state_cache_ttl_and_failing_loader(tmp_path, target_registry):
    # Catches: per-request store reads (no TTL cache) or a down store being retried per request.
    now = NOW
    mono = {"t": 1000.0}
    loader = _loader_for(_index(now))
    source = build_admitted_source(object(), universe=UNIVERSE,
                                   clock=lambda: now,
                                   monotonic=lambda: mono["t"], loader=loader)
    source.issuer_universe(now)
    source.recent_events(now - timedelta(days=7), now, 20)
    source.public_grant(SOURCE_ID, now)
    assert loader.calls["n"] == 1
    mono["t"] += 30.0
    source.issuer_universe(now)
    assert loader.calls["n"] == 1
    mono["t"] += 31.0  # 61 s after the load
    source.issuer_universe(now)
    assert loader.calls["n"] == 2
    calls = {"n": 0}

    def broken(store):
        calls["n"] += 1
        raise RuntimeError("store down")
    source2 = build_admitted_source(object(), universe=UNIVERSE,
                                    clock=lambda: now,
                                    monotonic=lambda: mono["t"], loader=broken)
    assert source2.issuer_universe(now) == {}
    assert source2.recent_events(now - timedelta(days=7), now, 20) == []
    assert source2.public_grant(SOURCE_ID, now) is None
    assert source2.source_coverage(now - timedelta(days=7), now, now) is None
    assert calls["n"] == 1
    mono["t"] += 5.0
    source2.issuer_universe(now)
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# 25-28: end to end through the writer, HTTP and D4
# ---------------------------------------------------------------------------

def test_25_e1_end_to_end_writer_reader_scan(tmp_path, target_registry):
    # Catches: a writer->reader->scan chain that cannot produce a real SUPPORTED Stage-A v2 packet.
    store = open_local_store(tmp_path / "store")
    work = tmp_path / "work"
    work.mkdir()
    result, _ = run(store, FakeSession(std_routes()), work_root=work)
    assert result.outcome == "COMPLETE"
    now = datetime(2026, 8, 5, 12, 5, 0, tzinfo=UTC)
    source = build_admitted_source(store, universe=(PFE,), clock=lambda: now)
    catalyst_admission.configure(source)
    scan = ci.scan_with_reader(["PFE"], now_utc=now)
    pfe = _row(scan, "PFE")
    assert scan["schema"] == "catalyst.scan/v2"
    assert pfe["status"] == "SUPPORTED"
    assert "2.18" in _texts(pfe)
    assert "8,412,000,000" in _texts(pfe)
    packets, issuers, coverage = catalyst_admission.read_qualified_event_context(now)
    assert len(packets) == 1
    packet = packets[0]
    assert packet["schema"] == STAGE_A_PACKET_SCHEMA
    assert packet["schema_version"] == 2
    latest = read_latest_index(store)
    index_spans = {figure["span_sha256"]
                   for event in latest.index["events"]
                   for figure in event["figures"]}
    evidence_rows = [row for row in packet["evidence"]
                     if row.get("replayed_span_sha256")]
    kinds = {row.get("kind") for row in evidence_rows}
    assert {"eps_actual", "rev_actual"} <= kinds
    # Every replayed span in the packet evidence must be a span the writer
    # published in the index for this document.
    assert all(row["replayed_span_sha256"] in index_spans
               for row in evidence_rows)
    print("E1_PACKET_EXCERPT", json.dumps({
        "status": pfe["status"], "headline": pfe["headline"],
        "what_changed": pfe["what_changed"], "sources": pfe["sources"]},
        sort_keys=True))


def test_26_e2_http_scan_supported(tmp_path, monkeypatch, target_registry):
    # Catches: the HTTP bridge refusing a configured fresh source.
    real_now = datetime.now(UTC)
    routes = std_routes(submissions_bytes=submissions_json(
        [pfe_row(accepted=_fmt(real_now - timedelta(hours=2)))]))
    store = open_local_store(tmp_path / "store")
    work = tmp_path / "work"
    work.mkdir()
    result, _ = run(store, FakeSession(routes), clock=make_clock(
        real_now - timedelta(minutes=1)), work_root=work)
    assert result.outcome == "COMPLETE"
    source = build_admitted_source(store, universe=(PFE,))
    catalyst_admission.configure(source)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    ci._reset_rate_limits_for_tests()
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    response = client.post("/api/catalyst/scan", json={"tickers": ["PFE"]})
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "catalyst.scan/v2"
    assert _row(body, "PFE")["status"] == "SUPPORTED"
    assert EXHIBIT_URL in json.dumps(body)


def test_27_flag_off_http_disabled(tmp_path, monkeypatch):
    # Catches: the disabled flag still reaching admission.
    monkeypatch.delenv("CATALYST_PUBLIC_ENABLED", raising=False)
    reads = {"n": 0}

    def forbidden(now_utc=None):
        reads["n"] += 1
        raise AssertionError("admission must not be read while disabled")
    from engine.marketing import catalyst_scan
    monkeypatch.setattr(catalyst_scan, "read_qualified_event_context", forbidden)
    ci._reset_rate_limits_for_tests()
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    with pytest.raises(HTTPException) as excinfo:
        ci._require_enabled("CATALYST_PUBLIC_ENABLED")
    disabled_detail = excinfo.value.detail
    response = client.post("/api/catalyst/scan", json={"tickers": ["PFE"]})
    assert response.status_code == 503
    assert response.json()["detail"] == disabled_detail
    assert reads["n"] == 0


def test_28_d4_writer_persists_no_document_bytes(tmp_path, monkeypatch, target_registry):
    # Catches: a writer that persists SEC document bytes to any path outside the namespaced store.
    systmp = tmp_path / "systmp"
    systmp.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(systmp))
    monkeypatch.setenv("TMPDIR", str(systmp))
    marker = FIXTURE.read_bytes()[200:264]
    leaks: list[str] = []
    real_open = builtins.open

    class _SpyHandle:
        def __init__(self, handle, path):
            self._handle = handle
            self._path = path

        def write(self, data):
            blob = (data.encode("utf-8", "surrogateescape")
                    if isinstance(data, str) else bytes(data))
            if marker in blob:
                leaks.append(self._path)
            return self._handle.write(data)

        def __getattr__(self, name):
            return getattr(self._handle, name)

        def __enter__(self):
            self._handle.__enter__()
            return self

        def __exit__(self, *exc):
            return self._handle.__exit__(*exc)

    def spy_open(file, mode="r", *args, **kwargs):
        handle = real_open(file, mode, *args, **kwargs)
        if any(flag in mode for flag in "wax+"):
            try:
                path = str(Path(file).resolve())
            except Exception:
                path = str(file)
            return _SpyHandle(handle, path)
        return handle

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_open)
    work = tmp_path / "work"
    work.mkdir()
    store = open_local_store(tmp_path / "store")
    result, _ = run(store, FakeSession(std_routes()), work_root=work)
    assert result.outcome == "COMPLETE"
    assert leaks == []
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert marker not in path.read_bytes(), path
    now = datetime(2026, 8, 5, 12, 5, 0, tzinfo=UTC)
    source = build_admitted_source(store, universe=(PFE,), clock=lambda: now)
    catalyst_admission.configure(source)
    scan = ci.scan_with_reader(["PFE"], now_utc=now)
    assert _row(scan, "PFE")["status"] == "SUPPORTED"
    assert leaks == []
