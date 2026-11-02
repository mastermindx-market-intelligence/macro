"""Native OLI context sibling on the EXISTING private research view.

These are REAL FastAPI fixture tests over the REAL route: a REAL on-disk
synthetic B1 generation, the REAL native B3 owner, the REAL Data OS alias
reader and the REAL D5 adapter.  No production source, no production outcome,
no browser, no credential and no owner plane is touched.

The route's own contract is preserved: authentication runs before any source
I/O, the kill switch stands down before any source I/O, the private headers
stay exact, the D5 ``/intelligence`` route keeps its own semantics, and a D5
failure is never restated as a D5 success.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.prophet_lab as api
from engine import prophet_candidate_state as b3_owner
from tests.test_prophet_candidate_state import (
    ASSEMBLY_NOW,
    CANDIDATE_ROW,
    FIXTURE_ROOT,
    _candidate_relation,
    _load_snapshot,
    _run_reconcile,
    _turn_watch_document,
    _write_candidates,
    _write_corrections,
    canonical_json,
)

#: The Data OS ``store`` alias row the native OLI read resolves.  The shared
#: intake fixture only carries the ``membership`` namespace; the native OLI
#: identity binding is defined over the ``store`` alias space, so the test
#: spine carries both rows for the same canonical security.
STORE_ALIAS_ROW = {
    "security_id": "SEC:US-XNAS-ALFA",
    "valid_from": "2020-01-01",
    "valid_to": None,
    "vendor": "store",
    "vendor_symbol": "ALFA",
}

WRAPPER_KEYS = {
    "schema", "status", "reason", "context", "identity_binding", "source_receipt",
}
CLOSED_CONTEXT_KEYS = {
    "schema", "identity", "decision_clock", "native_phase", "fresh_entry",
    "user_state", "evidence_summary", "forecast", "authority",
}


def _set_assembly_clock(monkeypatch, now=ASSEMBLY_NOW) -> None:
    monkeypatch.setattr(b3_owner, "_assembly_now", lambda: now)


def _identity_spine(data: Path, *, store_alias: bool = True) -> None:
    reference = data / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("security_master", "vendor_aliases"):
        rows = json.loads((FIXTURE_ROOT / f"{name}.json").read_text())
        if name == "vendor_aliases" and store_alias:
            rows = [*rows, dict(STORE_ALIAS_ROW)]
        pd.DataFrame(rows).to_parquet(reference / f"{name}.parquet", index=False)


def _build_store(root: Path, *, run2_candidates=(CANDIDATE_ROW,), store_alias: bool = True) -> Path:
    """Reconcile a REAL on-disk synthetic B1 generation (TURN WATCH, then candidate)."""
    data = root / "data"
    _identity_spine(data, store_alias=store_alias)
    turn_dir = data / "us_prophet_rank/episode_inputs/turn_watch"
    turn_dir.mkdir(parents=True)
    (turn_dir / "2026-11-27.json").write_text(
        canonical_json(_turn_watch_document("2026-11-27")) + "\n"
    )
    _run_reconcile(root, "2026-11-27T18:05:00Z")
    if run2_candidates:
        _write_candidates(data, list(run2_candidates))
        _run_reconcile(root, "2026-11-28T22:00:00Z")
    return root


def _episode_id(root: Path) -> str:
    return _load_snapshot(root).generation.episodes[0]["episode_id"]


@pytest.fixture(scope="module")
def oli_store(tmp_path_factory):
    return _build_store(tmp_path_factory.mktemp("oli_research_view_store"))


@pytest.fixture(scope="module")
def no_candidate_store(tmp_path_factory):
    """A generation whose episode has NO owner candidate relation at all."""
    return _build_store(
        tmp_path_factory.mktemp("oli_research_view_no_candidate"), run2_candidates=(),
    )


@pytest.fixture(scope="module")
def retracted_store(tmp_path_factory):
    """Correction/replay: the owner retracts the candidate relation."""
    root = _build_store(tmp_path_factory.mktemp("oli_research_view_retracted"))
    relation = _candidate_relation(_load_snapshot(root))
    corrections = _write_corrections(root, [{
        "event_type": "RETRACTED",
        "episode_id": relation["episode_id"],
        "source_system": "candidate_governance",
        "source_schema": "prophet_candidate_governance/v1",
        "source_event_id": "candidate_retraction:2026-11-28:ALFA:us_prophet_v3",
        "occurred_at": "2026-11-28T23:00:00Z",
        "known_at": "2026-11-28T23:00:00Z",
        "source_receipt": "sha256:" + "b" * 64,
        "correction_of": relation["event_id"],
        "payload": {"reason": "duplicate candidate source row"},
    }])
    _run_reconcile(root, "2026-11-28T23:30:00Z", corrections=corrections)
    return root


def _wire(monkeypatch, store: Path):
    monkeypatch.delenv("PROPHET_LAB_DISABLED", raising=False)
    monkeypatch.setenv(
        "PROPHET_LAB_EPISODE_STORE_ROOT", str(store / "data/us_prophet_rank/episodes"),
    )
    monkeypatch.setenv(
        "PROPHET_LAB_SECURITY_MASTER_PATH",
        str(store / "data/reference/security_master.parquet"),
    )
    monkeypatch.setenv(
        "PROPHET_LAB_VENDOR_ALIASES_PATH",
        str(store / "data/reference/vendor_aliases.parquet"),
    )


@pytest.fixture()
def client(monkeypatch, oli_store):
    _wire(monkeypatch, oli_store)
    _set_assembly_clock(monkeypatch)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        yield c, app


def _url(store: Path) -> str:
    return f"/api/prophet/lab/v1/episodes/{_episode_id(store)}/research-view"


def _private(response) -> None:
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


# ---------------------------------------------------------------------------
# auth / kill switch: nothing is read before the gates
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [401, 403])
def test_unentitled_caller_is_refused_before_any_source_read(monkeypatch, oli_store, code):
    import app.main as main
    import app.paywall as paywall

    _wire(monkeypatch, oli_store)
    calls = []

    def auth(value):
        calls.append(("auth", value))
        if code == 401:
            raise HTTPException(401, "sign in")
        return {"id": "test-free"}

    def entitle(user, always=False):
        calls.append(("entitlement", always))
        raise HTTPException(403, "site_full required")

    monkeypatch.setattr(main, "require_user", auth)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    monkeypatch.setattr(
        api, "load_candidate_episode_store_snapshot",
        lambda _root: pytest.fail("source read before the auth/entitlement gate"),
    )
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as c:
        response = c.get(_url(oli_store))
    assert response.status_code == code
    _private(response)
    assert calls[0] == ("auth", None)
    if code == 403:
        assert calls[1] == ("entitlement", True)


def test_kill_switch_stands_down_before_any_source_read(monkeypatch, oli_store):
    _wire(monkeypatch, oli_store)
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "true")
    monkeypatch.setattr(
        api, "load_candidate_episode_store_snapshot",
        lambda _root: pytest.fail("source read before the kill switch"),
    )
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(oli_store))
    assert response.status_code == 503
    _private(response)
    assert response.json()["error"] == "prophet_lab_disabled"


def test_invalid_options_are_refused_before_any_source_read(client, monkeypatch, oli_store):
    c, _ = client
    monkeypatch.setattr(
        api, "load_candidate_episode_store_snapshot",
        lambda _root: pytest.fail("source read before the option gate"),
    )
    response = c.get(_url(oli_store), params={"format": "xml"})
    assert response.status_code == 400
    _private(response)


# ---------------------------------------------------------------------------
# the happy path: one native OLI context beside the incumbent D5 read
# ---------------------------------------------------------------------------

def test_entitled_current_read_serves_one_native_opportunity_context(client, oli_store):
    c, _ = client
    response = c.get(_url(oli_store))
    assert response.status_code == 200
    _private(response)
    body = response.json()

    assert body["earnings_source_state"] == {"state": "AVAILABLE", "reason": None}

    opportunity = body["opportunity_context"]
    assert opportunity["schema"] == api.OPPORTUNITY_CONTEXT_SCHEMA
    assert opportunity["status"] == "AVAILABLE"
    assert opportunity["reason"] is None
    assert set(opportunity) == WRAPPER_KEYS

    # the closed OLI context.v1 is carried NESTED and is never widened
    context = opportunity["context"]
    assert context["schema"] == "prophet.lab_opportunity_context/v1"
    assert set(context) == CLOSED_CONTEXT_KEYS

    # one native B3 verified pair, bound to the source event's own session
    assert context["decision_clock"]["market_session"] == "2026-11-27"
    assert opportunity["source_receipt"].startswith("sha256:")

    # Data OS store alias round-trip, no ticker inference
    binding = opportunity["identity_binding"]
    assert binding["schema"] == "prophet.lab_opportunity_identity/v1"
    assert binding["alias_vendor"] == "store"
    assert binding["display_symbol"] == "ALFA"
    assert binding["security_id"] == "SEC:US-XNAS-ALFA"
    assert binding["decision_date"] == "2026-11-27"
    assert binding["episode_id"] == _episode_id(oli_store)

    # zero authority, and no owner state is invented
    assert all(value is False for value in context["authority"].values())
    assert all(value is False for value in binding["authority"].values())
    assert context["user_state"]["portfolio"]["state"] == "NOT_JOINED"
    assert context["evidence_summary"]["status"] == "NOT_JOINED"
    assert context["forecast"]["qualified"] is False


def test_missing_owner_b4_is_unknown_not_a_negative_permission(client, oli_store):
    c, _ = client
    body = c.get(_url(oli_store)).json()
    fresh_entry = body["opportunity_context"]["context"]["fresh_entry"]
    assert fresh_entry["state"] == "UNAVAILABLE_DATA"
    assert fresh_entry["entry_open"] is None
    assert fresh_entry["reason"] == "B4_NOT_AVAILABLE"
    assert fresh_entry["availability_id"] is None
    assert fresh_entry["blockers"] == ["B4_NOT_AVAILABLE"]


def test_private_headers_are_exact_on_both_the_view_and_the_sibling(client, oli_store):
    c, _ = client
    response = c.get(_url(oli_store))
    _private(response)
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"


def test_the_request_reads_the_candidate_store_exactly_once(client, monkeypatch, oli_store):
    c, _ = client
    calls = []
    real = api.load_candidate_episode_store_snapshot

    def counting(root):
        calls.append(root)
        return real(root)

    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", counting)
    response = c.get(_url(oli_store))
    assert response.status_code == 200
    assert response.json()["opportunity_context"]["status"] == "AVAILABLE"
    assert len(calls) == 1, "the research view must not read the B1 store twice"


def test_legacy_contract_siblings_keep_their_existing_trigger(client, oli_store):
    """The legacy pinned ``candidate_state`` sibling still needs a pinned generation."""
    c, _ = client
    unpinned = c.get(_url(oli_store)).json()
    assert "candidate_state" not in unpinned
    assert "candidate_state_context" not in unpinned

    generation = _load_snapshot(oli_store).generation_id
    pinned = c.get(_url(oli_store), params={"expected_generation": generation}).json()
    assert "candidate_state" in pinned
    assert pinned["opportunity_context"]["status"] == "AVAILABLE"


def test_the_d5_intelligence_route_keeps_its_own_semantics(client, oli_store):
    """The sibling is additive: the incumbent D5 route is unchanged."""
    c, _ = client
    original = c.get(
        f"/api/prophet/lab/v1/episodes/{_episode_id(oli_store)}/intelligence",
    )
    assert original.status_code == 200
    assert "opportunity_context" not in original.json()
    view = c.get(_url(oli_store)).json()
    assert view["source_projection_id"] == original.json()["projection_id"]
    assert view["episode_ref"] == original.json()["episode_ref"]


# ---------------------------------------------------------------------------
# typed refusals: never an empty success, never a fabricated identity
# ---------------------------------------------------------------------------

def test_absent_b1_source_is_a_typed_refusal(monkeypatch, no_candidate_store):
    _wire(monkeypatch, no_candidate_store)
    _set_assembly_clock(monkeypatch)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(no_candidate_store))
    assert response.status_code == 200
    _private(response)
    opportunity = response.json()["opportunity_context"]
    assert opportunity["status"] == "UNAVAILABLE"
    assert opportunity["reason"] == "SOURCE_UNAVAILABLE"
    assert opportunity["context"] is None
    assert opportunity["identity_binding"] is None
    assert opportunity["source_receipt"] is None


def test_a_wrong_source_receipt_is_a_typed_refusal(client, monkeypatch, oli_store):
    c, _ = client
    real = api._bind_candidate_source_relation

    def wrong(snapshot, episode_id):
        source_event_id, source_receipt, session = real(snapshot, episode_id)
        return source_event_id, "sha256:" + "0" * 64, session

    monkeypatch.setattr(api, "_bind_candidate_source_relation", wrong)
    response = c.get(_url(oli_store))
    assert response.status_code == 200
    opportunity = response.json()["opportunity_context"]
    assert opportunity["status"] == "UNAVAILABLE"
    assert opportunity["reason"] == "SOURCE_RECEIPT_MISMATCH"
    assert opportunity["context"] is None


def test_correction_replay_retraction_is_a_typed_refusal(monkeypatch, retracted_store):
    _wire(monkeypatch, retracted_store)
    _set_assembly_clock(monkeypatch)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(retracted_store))
    assert response.status_code == 200
    opportunity = response.json()["opportunity_context"]
    assert opportunity["status"] == "UNAVAILABLE"
    assert opportunity["reason"] in {"SOURCE_RETRACTED", "SOURCE_UNAVAILABLE"}
    assert opportunity["context"] is None


def test_an_unmapped_alias_is_a_typed_refusal(monkeypatch, tmp_path):
    """No ``store`` alias row at all: the identity binding is refused, not guessed."""
    root = _build_store(tmp_path / "noalias_store", store_alias=False)
    _wire(monkeypatch, root)
    _set_assembly_clock(monkeypatch)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(root))
    assert response.status_code == 200
    opportunity = response.json()["opportunity_context"]
    assert opportunity["status"] == "UNAVAILABLE"
    assert opportunity["reason"] == "ALIAS_UNAVAILABLE"


def test_ambiguous_source_is_a_typed_refusal():
    """Two owner relations at one session are a refusal, never a guess."""
    from types import SimpleNamespace

    events = (
        {
            "event_type": "OBSERVED", "event_id": "pee:a",
            "episode_id": "pe:x", "source_system": "candidate",
            "source_schema": "us_prophet_rank.candidates/v1",
            "source_event_id": "candidate:2026-11-27:ALFA:us_prophet_v3",
            "source_receipt": "sha256:" + "a" * 64,
        },
        {
            "event_type": "OBSERVED", "event_id": "pee:b",
            "episode_id": "pe:x", "source_system": "candidate",
            "source_schema": "us_prophet_rank.candidates/v1",
            "source_event_id": "candidate:2026-11-27:ALFA:us_prophet_v4",
            "source_receipt": "sha256:" + "b" * 64,
        },
    )
    snapshot = SimpleNamespace(generation=SimpleNamespace(events=events))
    with pytest.raises(api.OpportunityContextUnavailable) as excinfo:
        api._bind_candidate_source_relation(snapshot, "pe:x")
    assert excinfo.value.reason == "AMBIGUOUS_SOURCE"


def test_a_retracted_relation_is_never_selectable():
    from types import SimpleNamespace

    events = (
        {
            "event_type": "OBSERVED", "event_id": "pee:a",
            "episode_id": "pe:x", "source_system": "candidate",
            "source_schema": "us_prophet_rank.candidates/v1",
            "source_event_id": "candidate:2026-11-27:ALFA:us_prophet_v3",
            "source_receipt": "sha256:" + "a" * 64,
        },
        {
            "event_type": "RETRACTED", "event_id": "pee:r",
            "correction_of": "pee:a",
            "episode_id": "pe:x", "source_system": "candidate_governance",
            "source_schema": "prophet_candidate_governance/v1",
            "source_event_id": "candidate_retraction:2026-11-27:ALFA:us_prophet_v3",
            "source_receipt": "sha256:" + "b" * 64,
        },
    )
    snapshot = SimpleNamespace(generation=SimpleNamespace(events=events))
    with pytest.raises(api.OpportunityContextUnavailable) as excinfo:
        api._bind_candidate_source_relation(snapshot, "pe:x")
    assert excinfo.value.reason == "SOURCE_RETRACTED"


def test_the_closed_refusal_vocabulary_is_closed():
    assert api.OPPORTUNITY_UNAVAILABLE_REASONS == frozenset({
        "SOURCE_UNAVAILABLE",
        "SOURCE_RETRACTED",
        "SOURCE_RECEIPT_MISMATCH",
        "AMBIGUOUS_SOURCE",
        "ALIAS_UNAVAILABLE",
        "IDENTITY_UNAVAILABLE",
        "OWNER_UNAVAILABLE",
    })
    with pytest.raises(ValueError):
        api.OpportunityContextUnavailable("NOT_IN_THE_VOCABULARY")


# ---------------------------------------------------------------------------
# D5 unavailable: the native context still serves, and D5 is NOT restated
# ---------------------------------------------------------------------------

def _broken_earnings(**_kwargs):
    raise RuntimeError("private-path secret should not escape")


def test_d5_unavailable_serves_the_degraded_200_envelope(client, monkeypatch, oli_store):
    """The D5 owner did not answer; the native context did.

    The READ succeeded, so the composed envelope answers 200.  It is not an
    empty success and it is not a restated D5 success: it carries no earnings
    payload at all, the earnings section is absent rather than empty, and the
    typed earnings state names the missing owner out loud.
    """
    c, _ = client
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    response = c.get(_url(oli_store))
    _private(response)
    body = response.json()

    assert response.status_code == 200
    assert "private-path" not in response.text
    assert body["view_version"] == api.RESEARCH_OPPORTUNITY_VIEW_VERSION
    assert body["state"] == "PARTIAL"
    assert body["reason"] == "EARNINGS_UNAVAILABLE"
    assert body["earnings_source_state"] == {
        "state": "UNAVAILABLE", "reason": "EARNINGS_UNAVAILABLE",
    }
    assert body["episode_ref"]["episode_id"] == _episode_id(oli_store)
    assert all(value is False for value in body["authority"].values())

    # the wrapper is the SAME closed document, in its new PARTIAL state
    opportunity = body["opportunity_context"]
    assert opportunity["schema"] == api.OPPORTUNITY_CONTEXT_SCHEMA
    assert opportunity["status"] == "PARTIAL"
    assert opportunity["reason"] == "EARNINGS_UNAVAILABLE"
    assert set(opportunity) == WRAPPER_KEYS
    assert opportunity["context"]["schema"] == "prophet.lab_opportunity_context/v1"
    assert opportunity["identity_binding"]["display_symbol"] == "ALFA"
    assert opportunity["source_receipt"].startswith("sha256:")

    # NO earnings payload is present at all: the section is absent, not empty
    for key in ("metrics", "summary", "expectation_revision", "availability",
                "hold", "source_projection_id", "decision_cut", "coverage"):
        assert key not in body, f"{key} must not be present in a degraded view"

    # and no owner state is promoted
    context = opportunity["context"]
    assert context["fresh_entry"]["state"] == "UNAVAILABLE_DATA"
    assert context["fresh_entry"]["entry_open"] is None
    assert context["user_state"]["portfolio"]["state"] == "NOT_JOINED"
    assert context["evidence_summary"]["status"] == "NOT_JOINED"
    assert context["forecast"]["qualified"] is False
    assert all(value is False for value in context["authority"].values())


def test_the_full_earnings_view_is_unchanged(client, oli_store):
    """The incumbent D5 success branch keeps its own version and its own state."""
    c, _ = client
    body = c.get(_url(oli_store)).json()
    assert body["view_version"] == "earnings-detail/1"
    assert "state" not in body
    assert body["earnings_source_state"] == {"state": "AVAILABLE", "reason": None}
    assert body["opportunity_context"]["status"] == "AVAILABLE"


def test_d5_unavailable_html_keeps_its_own_503(client, monkeypatch, oli_store):
    """The private HTML surface is untouched by the degraded JSON envelope."""
    c, _ = client
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    response = c.get(_url(oli_store), params={"format": "html"})
    assert response.status_code == 503
    _private(response)
    assert response.json()["error"] == "prophet_episode_intelligence_unavailable"


def test_d5_and_oli_both_absent_keeps_the_503(monkeypatch, no_candidate_store):
    """No native context either: the original 503 stands, never an empty success."""
    _wire(monkeypatch, no_candidate_store)
    _set_assembly_clock(monkeypatch)
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(no_candidate_store))
    assert response.status_code == 503
    _private(response)
    body = response.json()
    assert body["error"] == "prophet_episode_intelligence_unavailable"
    assert body["earnings_source_state"] == {
        "state": "UNAVAILABLE", "reason": "EARNINGS_UNAVAILABLE",
    }
    assert body["opportunity_context"]["status"] == "UNAVAILABLE"


def test_the_kill_switch_is_never_answered_with_200(monkeypatch, oli_store):
    """The kill switch keeps its own 503 even though a native context exists."""
    _wire(monkeypatch, oli_store)
    _set_assembly_clock(monkeypatch)
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "true")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get(_url(oli_store))
    assert response.status_code == 503
    _private(response)
    assert response.json()["error"] == "prophet_lab_disabled"


def test_a_missing_episode_is_never_answered_with_200(monkeypatch, oli_store):
    """An episode that is not in this generation keeps its own 404."""
    _wire(monkeypatch, oli_store)
    _set_assembly_clock(monkeypatch)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as c:
        response = c.get("/api/prophet/lab/v1/episodes/pe:not-a-real-episode/research-view")
    assert response.status_code == 404
    _private(response)
    assert response.json()["error"] == "prophet_episode_not_found"


def test_the_d5_intelligence_route_keeps_its_own_503(client, monkeypatch, oli_store):
    """The degraded envelope is confined to the private research view."""
    c, _ = client
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    response = c.get(
        f"/api/prophet/lab/v1/episodes/{_episode_id(oli_store)}/intelligence",
    )
    assert response.status_code == 503
    _private(response)
    body = response.json()
    assert body["error"] == "prophet_episode_intelligence_unavailable"
    assert "opportunity_context" not in body
    assert "view_version" not in body


def test_the_degraded_envelope_is_language_specific(client, monkeypatch, oli_store):
    """EN and ZH carry the same closed presentation with their own wording."""
    c, _ = client
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    en = c.get(_url(oli_store), params={"language": "en"}).json()
    zh = c.get(_url(oli_store), params={"language": "zh"}).json()
    assert en["language"] == "en" and zh["language"] == "zh"
    assert en["presentation"]["title"] == (
        "Lifecycle context available; earnings evidence unavailable")
    assert zh["presentation"]["title"] == "\u751f\u547d\u5468\u671f\u4e0a\u4e0b\u6587\u53ef\u7528\uff1b\u8d22\u62a5\u8bc1\u636e\u4e0d\u53ef\u7528"
    assert set(en["presentation"]) == set(zh["presentation"])
    assert en["presentation"]["scope_notes"] != zh["presentation"]["scope_notes"]


def test_the_degraded_envelope_reads_the_candidate_store_exactly_once(client, monkeypatch, oli_store):
    """The degraded view still reads B1 exactly once per request."""
    c, _ = client
    calls = []
    real = api.load_candidate_episode_store_snapshot

    def counting(root):
        calls.append(root)
        return real(root)

    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", counting)
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", _broken_earnings)
    response = c.get(_url(oli_store))
    assert response.status_code == 200
    assert response.json()["state"] == "PARTIAL"
    assert len(calls) == 1, "the degraded view must not read the B1 store twice"


# ---------------------------------------------------------------------------
# generation pinning
# ---------------------------------------------------------------------------

def test_generation_movement_is_a_409(client, oli_store):
    c, _ = client
    response = c.get(
        _url(oli_store), params={"expected_generation": "peg:" + "0" * 64},
    )
    assert response.status_code == 409
    _private(response)
    assert response.json()["error"] == "prophet_episode_generation_changed"


def test_a_pinned_generation_that_moves_mid_read_is_a_409(client, monkeypatch, oli_store):
    c, _ = client
    generation = _load_snapshot(oli_store).generation_id
    real = api.load_candidate_episode_store_snapshot

    def moving(root):
        snapshot = real(root)
        monkeypatch.setattr(
            api, "_episode_intelligence_response",
            lambda *a, **k: api._response(
                {"error": "prophet_episode_generation_changed"}, status_code=409,
            ),
        )
        return snapshot

    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", moving)
    response = c.get(_url(oli_store), params={"expected_generation": generation})
    assert response.status_code == 409
    assert response.json()["error"] == "prophet_episode_generation_changed"


# ---------------------------------------------------------------------------
# the incumbent HTML surface is untouched
# ---------------------------------------------------------------------------

def test_the_html_surface_is_unchanged(client, oli_store):
    c, _ = client
    response = c.get(_url(oli_store), params={"format": "html", "language": "zh"})
    assert response.status_code == 200
    _private(response)
    assert "text/html" in response.headers["content-type"]
    assert "script-src 'none'" in response.headers["content-security-policy"]
    assert "<script" not in response.text
