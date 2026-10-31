"""Catalyst Session03 offline first-value UX: no backend/publication effects."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "render_catalyst_scan.py"
SOURCE_HTML = ROOT / "templates" / "catalyst_scan.html.j2"
SOURCE_JS = ROOT / "templates" / "catalyst_scan.js"
SOURCE_CSS = ROOT / "templates" / "catalyst_scan.css"


def _builder():
    spec = importlib.util.spec_from_file_location("catalyst_scan_preview", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_preview_render_scan_first_navigable(tmp_path):
    builder = _builder()
    page = builder.render_preview(tmp_path / "preview")
    assert page.is_file()
    html = page.read_text(encoding="utf-8")
    assert 'content="noindex,nofollow"' in html
    assert 'OFFLINE UI PREVIEW' in html
    assert 'name="referrer" content="no-referrer"' in html
    assert html.index('id="cs-scan-form"') < html.index('id="cs-optin"')
    assert 'id="cs-results"' in html and 'id="cs-optin"' in html
    assert 'id="cs-verify-form"' in html
    assert 'id="cs-js-needed"' in html
    assert 'href="/us_stocks.html"' in html
    assert "/stocks.html" not in html
    assert 'id="cs-scan-controls" disabled' in html
    assert 'name="email" type="email"' in html
    assert '<noscript>' in html and 'Nothing has been submitted' in html
    assert (page.parent / "catalyst_scan.js").read_bytes() == SOURCE_JS.read_bytes()
    assert (page.parent / "catalyst_scan.css").read_bytes() == SOURCE_CSS.read_bytes()
    assert page.parent == tmp_path / "preview"


def test_preview_refuses_live_site_and_overwrites(tmp_path):
    build = _builder()
    with pytest.raises(ValueError, match="live repository"):
        build.render_preview(ROOT / "site")
    with pytest.raises(ValueError, match="live repository"):
        build.render_preview(ROOT / "site" / "catalyst")
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "valuable.txt").write_text("do not touch")
    with pytest.raises(ValueError, match="empty"):
        build.render_preview(occupied)
    assert (occupied / "valuable.txt").read_text() == "do not touch"


def test_css_accessible_narrow_layout_and_focus():
    css = SOURCE_CSS.read_text(encoding="utf-8")
    assert "@media(max-width:600px)" in css
    assert "@media(max-width:345px)" in css
    assert "grid-template-columns:1fr" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert ".cs-scan-form fieldset" in css


def test_frontend_never_embeds_identity_or_receipt_in_share_urls():
    js = SOURCE_JS.read_text(encoding="utf-8")
    assert 'url.searchParams.set("tickers", lastTickers.join(","))' in js
    assert "window.location.pathname" in js
    assert "new URL(window.location.pathname, window.location.origin)" in js
    assert "credentials: \"same-origin\"" in js
    assert "referrerPolicy: \"no-referrer\"" in js
    assert "localStorage.setItem" not in js
    assert "localStorage.removeItem" not in js
    assert "sessionStorage." not in js
    assert "result.public_ref" in js
    assert "scan_receipt: scanReceipt" in js
    assert 'el("cs-scan-controls").disabled = false' in js


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_parses_with_node():
    out = subprocess.run(["node", "--check", str(SOURCE_JS)],
                         text=True, capture_output=True, timeout=12, check=False)
    assert out.returncode == 0, out.stderr


# ---------------------------------------------------------------------------
# A2-CASES-r1 — anonymous-journey witnesses for the reviewed docket acceptance
# rows A01, A02, A04, A05 and A07. Everything below is hermetic: synthetic
# fixtures ("SYNTHETIC TEST FIXTURE" material only), one fixed clock NOW, no
# network, no identity, no wall-clock dependence. Producers are exercised at
# their public seams (admission read -> compose_scan -> sanitize_public_scan ->
# render_first_value / routes / templates/catalyst_scan.js in node's vm).
# ---------------------------------------------------------------------------
import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import catalyst_integration as ci
from engine.marketing import catalyst_admission, catalyst_scan
from engine.marketing.catalyst_packets import (
    PublicSourceGrant,
    VerifiedDocumentObservation,
    VerifiedEarningsFigure,
    build_event_packet,
)
from engine.marketing.catalyst_scan import SourceCoverageReceipt, compose_scan

UTC = timezone.utc
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
MIN = timedelta(minutes=1)
# The producer's five clocks, all pinned to distinct instants.
T_ACC = NOW - 4 * MIN        # SEC acceptance (engine-internal packet clock)
T_FIRST = NOW - 3 * MIN      # first verified availability (public source clock)
T_DOCHECK = NOW - 2 * MIN    # document recheck (packet/observation clock)
# The producer's complete-current window spans the full 7-day pilot lookback,
# attested by a check no older than ten minutes.
W_START = NOW - timedelta(days=7)
W_END, W_CHECKED = NOW - MIN, NOW - MIN
DOC_SHA = "a2" + "0" * 62
SPAN_EPS = "b2" + "0" * 62
SPAN_REV = "c2" + "0" * 62
SNAP = "a2-snapshot-001"
K0 = "0000078003:0000078003-26-000094"
K1 = "0000078003:0000078003-26-000111"
K2 = "0000078003:0000078003-26-000222"
K3 = "0000078003:0000078003-26-000333"
URL0 = ("https://www.sec.gov/Archives/edgar/data/78003/000007800326000094/"
        "0000078003-26-000094-index.htm")
URL1 = ("https://www.sec.gov/Archives/edgar/data/78003/000007800326000111/"
        "0000078003-26-000111-index.htm")
URL2 = ("https://www.sec.gov/Archives/edgar/data/78003/000007800326000222/"
        "0000078003-26-000222-index.htm")
URL3 = ("https://www.sec.gov/Archives/edgar/data/78003/000007800326000333/"
        "0000078003-26-000333-index.htm")
GRANT_URLS = {"sec:" + key: url for key, url in ((K0, URL0), (K1, URL1), (K2, URL2), (K3, URL3))}
UNIVERSE = {
    "PFE": {"supported": True, "issuer_id": "cik:0000078003", "dossier_path": "/stocks/PFE/"},
    # Known-unsupported symbol stays NOT_COVERED, never hides the sibling result.
    "ZZZZ": {"supported": False, "issuer_id": "cik:0000000055"},
}
CLAIM_EPS = "PFE reported GAAP EPS of 0.42 USD/share."
CLAIM_EPS_CORRECTED = "PFE reported GAAP EPS of 0.43 USD/share."
_FORBIDDEN_EMPTY_LANGUAGE = ("no news", "no qualifying", "nothing new", "no events")


def _stamp(moment):
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _assert_no_empty_language(text):
    low = text.lower()
    for phrase in _FORBIDDEN_EMPTY_LANGUAGE:
        assert phrase not in low, f"forbidden empty-result phrase leaked: {phrase}"


def _grant(source_id, url, sha=DOC_SHA, clock=NOW):
    return PublicSourceGrant(
        source_id=source_id, receipt_id="a2-synthetic-grant-0001",
        owner_ref="a2-synthetic-rights-owner", audience="public_anonymous",
        effective_at_utc=clock - timedelta(days=1),
        expires_at_utc=clock + timedelta(days=1),
        display_link=True, display_title=True, display_facts=True,
        document_url=url, document_sha256=sha)


def _resolver(state):
    def resolve(source_id, clock):
        if not state["granted"] or source_id not in GRANT_URLS:
            return None
        return _grant(source_id, GRANT_URLS[source_id], clock=clock)
    return resolve


def _observation(source_id, url, sha=DOC_SHA, *, eps=0.42, first=T_FIRST,
                 checked=T_DOCHECK, form="", amends=""):
    return VerifiedDocumentObservation(
        source_id=source_id, document_url=url, document_sha256=sha,
        receipt_id="a2-synthetic-retained-receipt-0001",
        owner_ref="a2-synthetic-retained-reader",
        first_verified_at_utc=first, checked_at_utc=checked,
        source_snapshot_version=SNAP, filing_form=form, amends_filing_key=amends,
        verified_figures=(
            VerifiedEarningsFigure("eps_actual", eps, "gaap", sha, SPAN_EPS),
            VerifiedEarningsFigure("rev_actual", 21000000000.0, "reported", sha, SPAN_REV),
        ))


def _pfe_event(filing_key=K0, url=URL0, *, eps=0.42, acceptance=T_ACC,
               form=None, correction=None):
    event = {"source": "edgar_8k_202", "filing_key": filing_key, "cik": 78003,
             "ticker": "PFE", "acceptance_datetime": acceptance, "source_url": url,
             "eps_actual": eps, "_eps_basis": "gaap"}
    if form is not None:
        event["form"] = form
    if correction:
        event.update(correction)
    return event


_CORRECTED_FIELDS = {"correction_generation": 1, "revision_status": "corrected",
                     "supersedes_generation": 0, "correction_reason": "official_amendment"}


def _pkt(event=None, observation=None, *, granted=True, clock=NOW):
    state = {"granted": granted}
    event = event or _pfe_event()
    observation = observation or _observation("sec:" + event["filing_key"],
                                              event["source_url"],
                                              eps=event.get("eps_actual", 0.42))
    event = {key: value for key, value in event.items() if key != "_observation"}
    return build_event_packet(event, issuers=UNIVERSE, rights_resolver=_resolver(state),
                              as_of=clock, document_observation=observation,
                              max_age=timedelta(days=7))


def _coverage(**changes):
    fields = dict(
        source="edgar_8k_202", receipt_id="a2-synthetic-complete-window-0001",
        owner_ref="a2-synthetic-retained-reader", snapshot_version=SNAP,
        issuer_tickers=frozenset({"PFE"}),
        window_start_utc=W_START, window_end_utc=W_END, checked_at_utc=W_CHECKED,
        outcome="COMPLETE", pagination_exhausted=True, truncated=False,
        returned_events=1, event_limit=20)
    fields.update(changes)
    return SourceCoverageReceipt(**fields)


def _public_scan(packets, coverage=None, *, tickers=("PFE",), issuers=UNIVERSE, as_of=NOW):
    scan = compose_scan(list(tickers), packets=list(packets), issuers=issuers,
                        as_of=as_of, coverage=coverage)
    return ci.sanitize_public_scan(scan, list(tickers), now_utc=as_of)


def _admit(monkeypatch, *, events, granted=True, coverage, issuers=UNIVERSE):
    """Wire the real admission port to synthetic owner data (rights gate patched
    open exactly as tests/test_catalyst_admission.py does; the logic under test
    sits downstream of that gate)."""
    from engine.theme_graph import rights
    monkeypatch.setattr(rights, "assert_public_emission_allowed", lambda family: None)
    state = {"granted": granted}
    source = catalyst_admission.AdmittedEdgarSource(
        lambda clock: issuers,
        lambda since, current, limit: events,
        _resolver(state),
        lambda event, clock: event["_observation"],
        lambda since, current, checked: coverage)
    catalyst_admission.configure(source)
    return state


@pytest.fixture(autouse=True)
def _a2_reset_global_sources():
    yield
    catalyst_admission.configure(None)
    ci._reset_rate_limits_for_tests()


# ---------------------------------------------------------------- A01 ------

def test_a01_anonymous_supported_and_unsupported_rows_before_any_email_control(monkeypatch):
    """Catches: an anonymous supported result dropped, demoted behind an email or
    opt-in control, or its unsupported sibling silently dropped (all-or-nothing)."""
    event = _pfe_event()
    event["_observation"] = _observation("sec:" + K0, URL0)
    _admit(monkeypatch, events=[event], coverage=_coverage())
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    # Fixed clock through the real route (the route itself takes no clock).
    monkeypatch.setattr(ci, "public_scan_with_receipt",
                        lambda tickers, event_id=None: ci.scan_with_reader(
                            tickers, event_id, now_utc=NOW))
    ci._reset_rate_limits_for_tests()
    try:
        body = client.get("/api/catalyst/scan?tickers=PFE,ZZZZ").json()
        assert body["results"][0]["status"] == "SUPPORTED"
        assert body["results"][1]["status"] == "NOT_COVERED"
        source = body["results"][0]["sources"][0]
        assert source["first_verified_at_utc"] == _stamp(T_FIRST)
        assert source["url"] == URL0

        page = client.get("/api/catalyst?tickers=PFE,ZZZZ")
        assert page.status_code == 200
        text = page.text
        # (a) supported result rendered with its dated source, in document order
        # BEFORE any email or opt-in control.
        assert CLAIM_EPS in text
        assert f'href="{URL0}"' in text
        assert f'<time datetime="{_stamp(T_FIRST)}">' in text
        assert text.index(CLAIM_EPS) < text.index("id='catalyst-optin'")
        assert text.index(CLAIM_EPS) < text.index("id='catalyst-email'")
        # (b) the unsupported sibling keeps its own row and explanation while
        # the supported result survives: no silent drop, no all-or-nothing.
        assert "ZZZZ · NOT_COVERED" in text
        assert "This ticker is not covered" in text
        assert CLAIM_EPS in text
        # (c) no login or email wall precedes the result: the controls exist
        # only as a hidden optional section after the results div.
        assert "id='catalyst-optin' hidden" in text
        assert "Sign in" not in text and "Log in" not in text
        assert "login" not in text.lower()
    finally:
        ci._reset_rate_limits_for_tests()


def test_a01_stale_packet_not_served_as_current():
    """Catches: a packet past the producer's cache/freshness ceiling still shown
    as the current result instead of the can't-verify state."""
    fresh = _public_scan([_pkt()], _coverage(), as_of=NOW + 3 * MIN)
    assert fresh["results"][0]["status"] == "SUPPORTED"
    assert CLAIM_EPS in ci.render_first_value(fresh, "PFE")
    # 7 scan-time minutes later the packet's 5-minute cache has expired while
    # the coverage receipt is still current: only the claim may drop out.
    stale = _public_scan([_pkt()], _coverage(), as_of=NOW + 7 * MIN)
    assert stale["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    page = ci.render_first_value(stale, "PFE")
    assert CLAIM_EPS not in page
    assert URL0 not in page
    assert "Current source evidence is unavailable" in page
    _assert_no_empty_language(page)


# ---------------------------------------------------------------- A02 ------

def test_a02_complete_empty_renders_no_event_copy_with_checked_window():
    """Catches: a complete-empty scan rendering the no-event verdict without its
    attested checked window, or any other state stealing that verdict."""
    scan = _public_scan([], _coverage(returned_events=0))
    assert scan["publication_state"] == "COMPLETE_EMPTY"
    assert scan["results"][0]["status"] == "NO_QUALIFIED_EVENT"
    page = ci.render_first_value(scan, "PFE")
    assert "No qualifying earnings event in the verified checked window" in page
    assert (f"Checked {_stamp(W_START)} through {_stamp(W_END)}" in page)
    assert CLAIM_EPS not in page


def test_a02_source_failed_renders_cant_verify_not_complete_empty(monkeypatch):
    """Catches: a failed/unavailable source rendered as a coverage verdict
    (not-covered or no-event) instead of the can't-verify refusal."""
    unavailable = compose_scan(["PFE"], packets=[], issuers=UNIVERSE, as_of=NOW)
    assert unavailable["publication_state"] == "UNAVAILABLE"
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setattr(ci, "public_scan_with_receipt",
                        lambda tickers, event_id=None: ci.scan_with_reader(
                            tickers, event_id,
                            reader=lambda *a, **k: unavailable, now_utc=NOW))
    ci._reset_rate_limits_for_tests()
    try:
        page = client.get("/api/catalyst?tickers=PFE")
        assert page.status_code == 503
        assert "Qualified event source unavailable" in page.text
        assert 'role="alert"' in page.text
        # A failed source is not a coverage verdict for a known issuer.
        assert "This ticker is not covered" not in page.text
        assert CLAIM_EPS not in page.text
        _assert_no_empty_language(page.text)
    finally:
        ci._reset_rate_limits_for_tests()


def test_a02_truncated_event_count_above_admission_maximum_renders_cant_verify(monkeypatch):
    """Catches: an event count above the admission reader maximum (_MAX_EVENTS)
    still certified as a complete current read and rendered as no-event."""
    events, issuers = [], dict(UNIVERSE)
    for index in range(21):
        cik = 90000 + index
        key = f"{cik:010d}:{cik:010d}-26-{index:06d}"
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
               f"{cik:010d}{index:06d}/index.htm")
        ticker = f"SY{index:02d}"
        issuers[ticker] = {"supported": True, "issuer_id": f"cik:{cik:010d}"}
        event = {"source": "edgar_8k_202", "filing_key": key, "cik": cik,
                 "ticker": ticker, "acceptance_datetime": T_ACC, "source_url": url}
        event["_observation"] = _observation("sec:" + key, url)
        events.append(event)
    tickers = frozenset({"PFE", *(event["ticker"] for event in events)})
    _admit(monkeypatch, events=events, granted=False,
           coverage=_coverage(issuer_tickers=tickers, returned_events=21, event_limit=21),
           issuers=issuers)
    assert catalyst_scan.read_qualified_event_context(NOW) == ((), {}, None)
    with pytest.raises(HTTPException) as error:
        ci.scan_with_reader(["PFE"], now_utc=NOW)
    assert error.value.status_code == 503
    assert error.value.detail == "Qualified event source unavailable"
    page = ci.render_first_value(None, "PFE", str(error.value.detail))
    assert 'role="alert"' in page
    assert CLAIM_EPS not in page
    assert "This ticker is not covered" not in page
    _assert_no_empty_language(page)


def test_a02_rights_withheld_renders_distinct_rights_state(monkeypatch):
    """Catches: rights-withheld collapsing into the unavailable or no-event
    state, or its claims surviving a withheld display grant."""
    event = _pfe_event()
    event["_observation"] = _observation("sec:" + K0, URL0)
    state = _admit(monkeypatch, events=[event], granted=False, coverage=_coverage())
    assert state["granted"] is False
    scan = ci.scan_with_reader(["PFE"], now_utc=NOW)
    assert scan["results"][0]["status"] == "RIGHTS_BLOCKED"
    page = ci.render_first_value(scan, "PFE")
    assert "Source-display permission is not confirmed" in page
    # Distinct from the unavailable state, from complete-empty, and from support.
    assert "Current source evidence is unavailable" not in page
    assert "No qualifying earnings event" not in page
    assert CLAIM_EPS not in page and URL0 not in page
    _assert_no_empty_language(page)


# ---------------------------------------------------------------- A04 ------

def test_a04_first_verified_without_publication_sanitizer_path():
    """Catches: a first-availability-only v2 source refused, reclassified as a
    rights block, or labelled/clocked as official publication."""
    scan = {"schema": "catalyst.scan/v2", "schema_version": 2,
            "requested_tickers": ["PFE"], "event_id": "a2-fixture-event-0001",
            "generation": 0, "as_of_utc": _stamp(NOW), "publication_state": "PARTIAL",
            "checked_window": {"kind": "earnings_8k", "start_utc": _stamp(W_START),
                               "end_utc": _stamp(W_END), "checked_at_utc": _stamp(W_CHECKED)},
            "results": [{
                "ticker": "PFE", "status": "SUPPORTED", "relationship": "DIRECT",
                "public_safe": True, "correction_state": "CURRENT",
                "as_of_utc": _stamp(NOW), "headline": "SYNTHETIC TEST FIXTURE filing",
                "headline_evidence_ids": ["sec:a2-fixture-source-1"],
                "relationship_evidence_ids": [],
                "what_changed": [{"text": "SYNTHETIC TEST FIXTURE first-value claim.",
                                  "evidence_ids": ["sec:a2-fixture-source-1"]}],
                "scenarios": [], "invalidators": [], "dossier_path": None,
                "sources": [{
                    "source_id": "sec:a2-fixture-source-1", "display_rights": "ALLOWED",
                    "rights_receipt_id": "a2-synthetic-grant-0001",
                    "title": "SYNTHETIC TEST FIXTURE — SEC-shaped source",
                    "url": URL0, "published_at_utc": None,
                    "first_verified_at_utc": _stamp(T_FIRST)}]}]}
    public = ci.sanitize_public_scan(scan, ["PFE"], now_utc=NOW)
    assert public["results"][0]["status"] == "SUPPORTED"
    source = public["results"][0]["sources"][0]
    assert source["published_at_utc"] is None
    assert source["first_verified_at_utc"] == _stamp(T_FIRST)
    page = ci.render_first_value(public, "PFE")
    assert "first verified available" in page
    assert "· published" not in page
    assert f'<time datetime="{_stamp(T_FIRST)}">' in page
    # Never another clock's value: the acceptance and recheck instants must not
    # be shown as source stamps.
    assert _stamp(T_ACC) not in page
    assert _stamp(T_DOCHECK) not in page
    assert _stamp(W_CHECKED) not in page


def test_a04_first_verified_without_publication_reader_path():
    """Catches: the default reader path dropping, blocking or re-clocking a v2
    source whose official publication is absent but first availability is kept."""
    packet = _pkt()
    # The producer carries both a delayed first observation and an earlier SEC
    # acceptance; they stay distinct values end to end.
    assert packet["event_time_utc"] == _stamp(T_ACC)
    assert packet["first_observed_at_utc"] == _stamp(T_FIRST)
    assert packet["event_time_utc"] != packet["first_observed_at_utc"]
    assert packet["sources"][0]["published_at_utc"] is None
    assert packet["sources"][0]["first_verified_at_utc"] == _stamp(T_FIRST)
    public = _public_scan([packet], _coverage())
    assert public["results"][0]["status"] == "SUPPORTED"
    source = public["results"][0]["sources"][0]
    assert source["published_at_utc"] is None
    assert source["first_verified_at_utc"] == _stamp(T_FIRST)
    page = ci.render_first_value(public, "PFE")
    assert "first verified available" in page
    assert "· published" not in page
    assert CLAIM_EPS in page
    # The earlier SEC-acceptance clock never leaks in as a displayed stamp.
    assert _stamp(T_ACC) not in page
    assert _stamp(T_DOCHECK) not in page


# ---------------------------------------------------------------- A05 ------

def test_a05a_revoked_grant_second_scan_shows_rights_state_not_claim(monkeypatch):
    """Catches: a withdrawn source grant still serving the prior claim and
    citation as current, or the withdrawal shown as a non-rights state."""
    event = _pfe_event()
    event["_observation"] = _observation("sec:" + K0, URL0)
    state = _admit(monkeypatch, events=[event], coverage=_coverage())
    first = ci.scan_with_reader(["PFE"], now_utc=NOW)
    assert first["results"][0]["status"] == "SUPPORTED"
    first_page = ci.render_first_value(first, "PFE")
    assert CLAIM_EPS in first_page and URL0 in first_page
    # Rights are withdrawn between two scans of the same ticker.
    state["granted"] = False
    second = ci.scan_with_reader(["PFE"], now_utc=NOW)
    assert second["results"][0]["status"] == "RIGHTS_BLOCKED"
    second_page = ci.render_first_value(second, "PFE")
    assert CLAIM_EPS not in second_page
    assert URL0 not in second_page
    assert "SEC Form 8-K Item 2.02" not in second_page
    assert "Source-display permission is not confirmed" in second_page
    assert "Current source evidence is unavailable" not in second_page
    _assert_no_empty_language(second_page)


def test_a05b_corrected_generation_replaces_predecessor():
    """Catches: a CORRECTED generation not superseding its attested predecessor,
    so a stale claim stays current."""
    original = _pkt(_pfe_event(), _observation("sec:" + K0, URL0))
    amendment = _pkt(
        _pfe_event(K1, URL1, eps=0.43, acceptance=T_ACC + MIN,
                   form="8-K/A", correction=dict(_CORRECTED_FIELDS)),
        _observation("sec:" + K1, URL1, eps=0.43, form="8-K/A", amends=K0))
    assert amendment["generation"] == 1
    assert amendment["correction_state"] == "CORRECTED"
    assert amendment["amends_filing_key"] == K0
    assert amendment["event_id"] == original["event_id"]
    public = _public_scan([original, amendment], _coverage(returned_events=2))
    assert public["generation"] == 1
    row = public["results"][0]
    assert row["status"] == "SUPPORTED"
    assert row["correction_state"] == "CORRECTED"
    texts = " ".join(claim["text"] for claim in row["what_changed"])
    assert CLAIM_EPS_CORRECTED in texts
    assert "0.42" not in texts
    page = ci.render_first_value(public, "PFE")
    assert "Correction state: CORRECTED" in page
    assert "0.42" not in page
    assert "0.43" in page


def test_a05b_correction_without_attested_predecessor_refused():
    """Catches: a corrected generation with no attested predecessor amendment
    displayed as a correction instead of being refused."""
    packet = _pkt(
        _pfe_event(K2, URL2, form="8-K", correction=dict(_CORRECTED_FIELDS)),
        _observation("sec:" + K2, URL2, form="", amends=""))
    assert packet["public_safe"] is False
    assert "amendment_lineage_not_attested" in packet["missing_data"]
    public = _public_scan([packet], _coverage())
    assert public["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    page = ci.render_first_value(public, "PFE")
    assert "Current source evidence is unavailable" in page
    assert "CORRECTED" not in page
    assert "correction" not in page.lower()
    assert "0.42" not in page and "0.43" not in page
    _assert_no_empty_language(page)


def test_a05b_amendment_with_wrong_predecessor_refused():
    """Catches: an 8-K/A amendment pointing at another issuer's filing accepted
    as a correction instead of being refused."""
    foreign_root = "0000009999:0000009999-26-000001"
    packet = _pkt(
        _pfe_event(K3, URL3, form="8-K/A", correction=dict(_CORRECTED_FIELDS)),
        _observation("sec:" + K3, URL3, form="8-K/A", amends=foreign_root))
    assert packet["public_safe"] is False
    assert "amendment_lineage_not_attested" in packet["missing_data"]
    public = _public_scan([packet], _coverage())
    assert public["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    page = ci.render_first_value(public, "PFE")
    assert "Current source evidence is unavailable" in page
    assert "CORRECTED" not in page
    assert "correction" not in page.lower()
    _assert_no_empty_language(page)


_JS_DOM_PREAMBLE = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
class Element {
  constructor(id=''){this.id=id;this.children=[];this.listeners={};this.value='';
    this.hidden=true;this.checked=false;this.disabled=false;this.textContent='';
    this.className='';this.dataset={};this.href='';this.dateTime='';}
  addEventListener(name,fn){this.listeners[name]=fn;}
  replaceChildren(...c){this.children=c;}
  appendChild(c){this.children.push(c);return c;}
  append(...c){this.children.push(...c);}
  setAttribute(k,v){this[k]=v;}
  focus(){} reset(){} scrollIntoView(){} checkValidity(){return true;}
}
const IDS=['cs-scan-form','cs-tickers','cs-scan-error','cs-progress','cs-scan-submit',
 'cs-results','cs-result-cards','cs-copy-link','cs-optin','cs-optin-form','cs-verify-form',
 'cs-email','cs-consent','cs-otp','cs-optin-status','cs-summary-status','cs-summary-clock',
 'cs-summary-event','cs-results-note','cs-js-needed','cs-scan-controls','cs-optin-submit',
 'cs-verify-submit'];
function makeDom(){
  const elements=Object.fromEntries(IDS.map(n=>[n,new Element(n)]));
  const document={getElementById:(id)=>elements[id],
    createElement:(tag)=>new Element(tag),
    documentElement:{setAttribute(){}}};
  const window={location:{origin:'https://www.mastermind-x.com',
    pathname:'/api/catalyst',search:''},
    localStorage:{getItem(){return null;}}};
  return {elements,document,window};
}
function collect(node){
  let out=(node.textContent||'')+'\n';
  for(const child of node.children||[]) out+=collect(child);
  return out;
}
function boot(payloadFetch){
  const dom=makeDom();
  vm.runInNewContext(source,{document:dom.document,window:dom.window,
    fetch:payloadFetch,URL,URLSearchParams,setTimeout,clearTimeout,
    AbortController,console});
  return dom;
}
const SUBMIT={preventDefault(){}};
"""

_A05C_BODY = r"""
const payloads=JSON.parse(process.argv[2]);
const calls=[]; const pending=[];
async function deferredFetch(path,opts){
  calls.push({path,body:JSON.parse(opts.body)});
  return new Promise((resolve)=>pending.push(resolve));
}
(async ()=>{
  const dom=boot(deferredFetch);
  dom.elements['cs-tickers'].value='NVDA';
  const inFlight=dom.elements['cs-scan-form'].listeners.submit(SUBMIT);
  assert.equal(calls.length,1);
  // A second submit while a scan is running is dropped, never queued: no
  // second request exists whose late answer could clobber a newer render.
  await dom.elements['cs-scan-form'].listeners.submit(SUBMIT);
  assert.equal(calls.length,1);
  pending[0]({ok:true,status:200,json:async()=>payloads.nvda});
  await inFlight;
  assert.equal(collect(dom.elements['cs-result-cards'])
    .includes(payloads.nvda.results[0].headline),true);
  // Now the visitor scans AMD; the response body that comes back is a stale
  // NVDA-shaped answer. It must not overwrite the current selection.
  dom.elements['cs-tickers'].value='AMD';
  const amdRequest=dom.elements['cs-scan-form'].listeners.submit(SUBMIT);
  assert.equal(calls.length,2);
  assert.deepEqual(calls[1].body.tickers,['AMD']);
  pending[1]({ok:true,status:200,json:async()=>payloads.nvda});
  await amdRequest;
  const afterStale=collect(dom.elements['cs-result-cards']);
  assert.equal(afterStale.includes(payloads.nvda.results[0].headline),false);
  assert.equal(afterStale.includes('NVDA'),false);
  assert.equal(dom.elements['cs-result-cards'].children.length,0);
  assert.equal(dom.elements['cs-scan-error'].textContent
    .includes('incompatible scan'),true);
  assert.equal(dom.elements['cs-results'].hidden,true);
  // The correctly-identified AMD answer still renders normally afterwards.
  const retry=dom.elements['cs-scan-form'].listeners.submit(SUBMIT);
  assert.equal(calls.length,3);
  pending[2]({ok:true,status:200,json:async()=>payloads.amd});
  await retry;
  const final=collect(dom.elements['cs-result-cards']);
  assert.equal(final.includes(payloads.amd.results[0].headline),true);
  assert.equal(final.includes(payloads.nvda.results[0].headline),false);
  console.log('A05C_STALE_RESPONSE_FENCE=PASS');
})().catch((e)=>{console.error(e.stack);process.exitCode=1;});
"""


def _wire_scan(ticker, headline, claim):
    """Minimal producer-shaped public scan wire dict for the JS renderer."""
    return {"schema": "catalyst.scan/v2", "schema_version": 2,
            "as_of_utc": _stamp(NOW), "event_id": "a2-fixture-event-0001",
            "generation": 0, "publication_state": "PARTIAL",
            "requested_tickers": [ticker],
            "coverage_note": "synthetic fixture only",
            "checked_window": {"kind": "earnings_8k", "start_utc": _stamp(W_START),
                               "end_utc": _stamp(W_END), "checked_at_utc": _stamp(W_CHECKED)},
            "results": [{
                "ticker": ticker, "status": "SUPPORTED", "relationship": "DIRECT",
                "correction_state": "CURRENT", "as_of_utc": _stamp(NOW),
                "headline": headline,
                "what_changed": [{"text": claim, "evidence_ids": ["sec:a2-fixture-source-1"]}],
                "scenarios": [], "invalidators": [],
                "dossier_path": f"/stocks/{ticker}.html",
                "sources": [{
                    "source_id": "sec:a2-fixture-source-1", "display_rights": "ALLOWED",
                    "title": "SYNTHETIC TEST FIXTURE — SEC-shaped source",
                    "url": URL0, "published_at_utc": None,
                    "first_verified_at_utc": _stamp(T_FIRST)}]}]}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a05c_stale_cross_ticker_response_never_overwrites_current_selection():
    """Catches: a stale response for an older ticker selection overwriting the
    current selection's render in templates/catalyst_scan.js."""
    payloads = {"nvda": _wire_scan("NVDA", "SYNTHETIC NVDA fixture headline",
                                   "SYNTHETIC NVDA fixture claim."),
                "amd": _wire_scan("AMD", "SYNTHETIC AMD fixture headline",
                                  "SYNTHETIC AMD fixture claim.")}
    done = subprocess.run(
        [shutil.which("node"), "-e", _JS_DOM_PREAMBLE + _A05C_BODY,
         str(SOURCE_JS), json.dumps(payloads)],
        text=True, capture_output=True, timeout=30, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "A05C_STALE_RESPONSE_FENCE=PASS" in done.stdout


# ---------------------------------------------------------------- A07 ------

_A07A_BODY = r"""
const cases=JSON.parse(process.argv[2]);
const out={};
(async ()=>{
  for(const c of cases){
    async function oneShot(path,opts){
      return {ok:true,status:200,json:async()=>c.payload};
    }
    const dom=boot(oneShot);
    dom.elements['cs-tickers'].value=c.input;
    await dom.elements['cs-scan-form'].listeners.submit(SUBMIT);
    out[c.name]=dom.elements['cs-result-cards'].children.map(collect);
  }
  console.log('A2_JS_RENDER='+JSON.stringify(out));
})().catch((e)=>{console.error(e.stack);process.exitCode=1;});
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a07_nojs_and_js_renderers_agree_on_truth_states():
    """Catches: the no-JS fallback and the JS renderer telling different truths
    for the same scan status (meaning, not bytes)."""
    packet = _pkt()
    two_rows = _public_scan([packet], _coverage(), tickers=("PFE", "ZZZZ"))
    complete_empty = _public_scan([], _coverage(returned_events=0))
    stale = _public_scan([_pkt()], _coverage(), as_of=NOW + 7 * MIN)
    blocked = _public_scan([_pkt(granted=False)], _coverage())
    server = {}
    for name, scan, ticker in (
            ("SUPPORTED", two_rows, "PFE"), ("NOT_COVERED", two_rows, "ZZZZ"),
            ("NO_QUALIFIED_EVENT", complete_empty, "PFE"),
            ("TEMPORARILY_UNAVAILABLE", stale, "PFE"),
            ("RIGHTS_BLOCKED", blocked, "PFE")):
        page = ci.render_first_value(scan, scan["requested_tickers"][0])
        section = page.split(f'<section aria-label="{ticker}">')[1].split("</section>")[0]
        server[name] = section.lower()
    cases = [
        {"name": "SUPPORTED", "input": "PFE,ZZZZ", "payload": two_rows, "card": 0},
        {"name": "NOT_COVERED", "input": "PFE,ZZZZ", "payload": two_rows, "card": 1},
        {"name": "NO_QUALIFIED_EVENT", "input": "PFE", "payload": complete_empty, "card": 0},
        {"name": "TEMPORARILY_UNAVAILABLE", "input": "PFE", "payload": stale, "card": 0},
        {"name": "RIGHTS_BLOCKED", "input": "PFE", "payload": blocked, "card": 0},
    ]
    done = subprocess.run(
        [shutil.which("node"), "-e", _JS_DOM_PREAMBLE + _A07A_BODY,
         str(SOURCE_JS), json.dumps([{"name": c["name"], "input": c["input"],
                                      "payload": c["payload"]} for c in cases])],
        text=True, capture_output=True, timeout=30, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    rendered = json.loads(
        done.stdout.split("A2_JS_RENDER=", 1)[1].strip().splitlines()[0])
    probes = {
        "SUPPORTED": [
            lambda t: CLAIM_EPS.lower() in t,
            lambda t: "first verified available" in t,
            lambda t: "sec form 8-k item 2.02" in t],
        "NOT_COVERED": [lambda t: "not covered" in t,
                        lambda t: CLAIM_EPS.lower() not in t],
        "NO_QUALIFIED_EVENT": [
            lambda t: "no qualifying earnings event" in t,
            lambda t: (f"checked {_stamp(W_START)} through {_stamp(W_END)}").lower() in t,
            lambda t: CLAIM_EPS.lower() not in t],
        "TEMPORARILY_UNAVAILABLE": [
            lambda t: "unavailable" in t and "try again" in t,
            lambda t: CLAIM_EPS.lower() not in t],
        "RIGHTS_BLOCKED": [lambda t: "permission" in t,
                           lambda t: CLAIM_EPS.lower() not in t],
    }
    for case in cases:
        name = case["name"]
        js_text = rendered[name][case["card"]].lower()
        nojs_text = server[name]
        assert js_text, f"JS renderer produced no card text for {name}"
        for probe in probes[name]:
            assert probe(js_text), f"JS renderer lost the {name} meaning: {js_text!r}"
            assert probe(nojs_text), f"no-JS fallback lost the {name} meaning: {nojs_text!r}"
        if name != "NO_QUALIFIED_EVENT":
            _assert_no_empty_language(js_text)
            _assert_no_empty_language(nojs_text)


def test_a07_hostile_urls_fail_closed_never_linked():
    """Catches: a javascript:-scheme or credential-bearing source URL emitted as
    a public link instead of failing the whole scan closed."""
    for hostile in ("javascript://example.com/alert(1)",
                    "https://user:secret@example.org/filing"):
        scan = {"schema": "catalyst.scan/v1", "schema_version": 1,
                "requested_tickers": ["PFE"], "event_id": "a2-fixture-event-0001",
                "generation": 0, "as_of_utc": _stamp(NOW), "publication_state": "PARTIAL",
                "results": [{
                    "ticker": "PFE", "status": "SUPPORTED", "relationship": "DIRECT",
                    "public_safe": True, "correction_state": "CURRENT",
                    "as_of_utc": _stamp(NOW), "headline": "SYNTHETIC TEST FIXTURE filing",
                    "headline_evidence_ids": ["sec:a2-fixture-source-1"],
                    "relationship_evidence_ids": [],
                    "what_changed": [{"text": "SYNTHETIC TEST FIXTURE claim.",
                                      "evidence_ids": ["sec:a2-fixture-source-1"]}],
                    "scenarios": [], "invalidators": [], "dossier_path": None,
                    "sources": [{
                        "source_id": "sec:a2-fixture-source-1", "display_rights": "ALLOWED",
                        "rights_receipt_id": "a2-synthetic-grant-0001",
                        "title": "SYNTHETIC TEST FIXTURE — SEC-shaped source",
                        "url": hostile, "published_at_utc": _stamp(T_FIRST)}]}]}
        with pytest.raises(HTTPException) as error:
            ci.scan_with_reader(["PFE"], reader=lambda *a, **k: scan, now_utc=NOW)
        assert error.value.status_code == 503
        assert hostile not in str(error.value.detail)
        page = ci.render_first_value(None, "PFE", str(error.value.detail))
        assert hostile not in page
        assert "user:secret" not in page
        assert 'href="javascript:' not in page.lower()
