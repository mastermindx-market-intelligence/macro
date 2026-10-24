"""Private HTTP/source seam: all provider and Auth effects are explicit stubs."""
import copy
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import options_plan as api, options_plan_source as source
from app.options_auth import OptionsPrincipal
from engine.intelligence_workspace.options_use import OptionUseRefused


def plan():
    return dict(schema="options.plan_expiry_request/v1", draft=dict(schema="options_plan_draft.v1",
        research=dict(thesis="", invalidation="", horizon=""), legs=[dict(
            snapshot=dict(pinKey="test", identity=dict(root="SPY", exp="2026-10-23", right="C",
                strike=763, terms=dict(multiplier=None, deliverable=None, settlement=None, exercise_style=None), adjustedRootHint=False),
                session="2026-10-19", asofRaw="2026-10-20T12:00:00Z", sourceStale=True, schema=None),
            assumptions=dict(side="buy", quantity=1, entry=dict(kind="user_assumption", premium_per_unit=2, currency="USD")))]),
        spots=[760, 763, 765, 770], payoff_basis=dict(kind="hold_to_expiry_intrinsic", expiration="2026-10-23"))


def contract_row():
    return dict(ticker="O:SPY261023C00763000", underlying_ticker="SPY", expiration_date="2026-10-23",
                contract_type="call", strike_price=763, exercise_style="american", shares_per_contract=100,
                cfi="OCASPS", primary_exchange="BATO")


class Response:
    status_code = 200
    def __init__(self, payload=None):
        self.raw = json.dumps(payload or dict(status="OK", results=[contract_row()])).encode()
        self.closed = False
    def iter_content(self, chunk_size):
        yield self.raw
    def close(self):
        self.closed = True


class Session:
    def __init__(self, response=None, fail=False):
        self.headers = {}; self.calls = []; self.response = response or Response(); self.fail = fail
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.fail:
            raise TimeoutError("secret vendor token must never escape")
        return self.response


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setattr(source, "_SOURCE_STOPPED", False)
    monkeypatch.setenv("OPTIONS_PLAN_REFERENCE_ENABLED", "1")
    monkeypatch.setattr(api, "_server_key", lambda: "provisioned-test-key")


@pytest.fixture
def client():
    app = FastAPI(); app.include_router(api.router)
    return TestClient(app)


def allow(monkeypatch):
    monkeypatch.setattr(api, "resolve_entitled_options_principal", lambda _: OptionsPrincipal("subject", "issuer", "epoch", 9999999999))


def test_absent_and_denied_auth_cannot_call_source(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "prepare_authenticated_plan", lambda *a, **k: calls.append(True))
    assert client.post("/api/options/plan/expiry", json=plan()).status_code == 401
    for reason, expected in [("authentication_unavailable", 401), ("entitlement_unavailable", 403)]:
        def refuse(_):
            raise OptionUseRefused(reason)
        monkeypatch.setattr(api, "resolve_entitled_options_principal", refuse)
        response = client.post("/api/options/plan/expiry", json=plan(), headers={"Authorization": "Bearer token"})
        assert response.status_code == expected
        assert response.headers["cache-control"] == "private, no-store"
    assert calls == []


def test_private_success_uses_only_server_owned_source(client, monkeypatch):
    allow(monkeypatch)
    calls = []
    def prepare(payload, *, key):
        calls.append((payload, key)); return dict(status="PREPARED_EXPIRY_PAYOFF")
    monkeypatch.setattr(api, "prepare_authenticated_plan", prepare)
    response = client.post("/api/options/plan/expiry", json=plan(), headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert "Authorization" in response.headers["vary"]
    assert calls == [(plan(), "provisioned-test-key")]


@pytest.mark.parametrize("mutation", ["contexts", "reference_observation", "reference_sha256", "extra"])
def test_caller_cannot_supply_source_evidence(mutation):
    payload = plan(); payload[mutation] = {"verdict": "entitled", "sha256": "a" * 64}
    with pytest.raises(ValueError):
        source.plan_inputs(payload, known_by="2026-10-24T12:00:00Z")


@pytest.mark.parametrize("change", ["mixed_expiry", "missing_entry", "adjusted", "bad_spots", "wrong_basis"])
def test_invalid_math_rejected_before_network(change, monkeypatch):
    payload = plan()
    if change == "mixed_expiry":
        payload["draft"]["legs"].append(copy.deepcopy(payload["draft"]["legs"][0]))
        payload["draft"]["legs"][1]["snapshot"]["identity"]["exp"] = "2026-10-30"
    if change == "missing_entry": payload["draft"]["legs"][0]["assumptions"]["entry"] = None
    if change == "adjusted": payload["draft"]["legs"][0]["snapshot"]["identity"]["adjustedRootHint"] = True
    if change == "bad_spots": payload["spots"] = [float("nan")]
    if change == "wrong_basis": payload["payoff_basis"]["expiration"] = "2026-10-30"
    session = Session()
    with pytest.raises((ValueError, TypeError)):
        source.prepare_authenticated_plan(payload, key="test", session=session)
    assert session.calls == []


def test_exact_reference_get_is_bounded_no_retry_and_no_quote():
    payload = plan(); contexts = source.plan_inputs(payload, known_by="2026-10-24T12:00:00Z")
    session = Session()
    observed = source.read_plan_reference(contexts, key="test", known_by="2026-10-24T12:00:00Z", session=session)
    assert len(session.calls) == 1
    url, kwargs = session.calls[0]
    assert url == "https://api.polygon.io/v3/reference/options/contracts"
    assert kwargs["params"] == dict(underlying_ticker="SPY", expiration_date="2026-10-23", as_of="2026-10-23",
        **{"strike_price.gte": 763.0, "strike_price.lte": 763.0}, limit=100)
    assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
    assert "apiKey" not in kwargs["params"]
    assert observed["contracts"] == [contract_row()]
    assert observed["historical_first_availability_established"] is False
    assert session.response.closed


@pytest.mark.parametrize("mode", ["timeout", "denied", "pagination", "oversize"])
def test_failure_stops_source_lane_without_retry_or_fallback(mode):
    response = Response()
    if mode == "denied": response.status_code = 403
    if mode == "pagination": response.raw = json.dumps(dict(status="OK", results=[contract_row()], next_url="https://elsewhere.test")).encode()
    if mode == "oversize": response.raw = b" " * (262144 + 1)
    session = Session(response=response, fail=mode == "timeout")
    contexts = source.plan_inputs(plan(), known_by="2026-10-24T12:00:00Z")
    for _ in range(2):
        with pytest.raises(source.PlanSourceUnavailable, match="contract_terms_unavailable"):
            source.read_plan_reference(contexts, key="test", known_by="2026-10-24T12:00:00Z", session=session)
    assert len(session.calls) == 1


def test_http_body_bounds_duplicate_nonfinite_and_errors_no_store(client, monkeypatch):
    allow(monkeypatch)
    for raw, status in [(b"x" * (65536 + 1), 413), (b'{"schema":1,"schema":2}', 422), (b'{"spots":[NaN]}', 422)]:
        response = client.post("/api/options/plan/expiry", content=raw,
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"})
        assert response.status_code == status
        assert response.headers["cache-control"] == "private, no-store"
    def fail(*args, **kwargs):
        raise source.PlanSourceUnavailable("contract_terms_unavailable")
    monkeypatch.setattr(api, "prepare_authenticated_plan", fail)
    response = client.post("/api/options/plan/expiry", json=plan(), headers={"Authorization": "Bearer token"})
    assert response.status_code == 503
    assert response.json() == dict(status="UNAVAILABLE", reason="contract_terms_unavailable")


def test_actual_server_source_to_incumbent_curve_keeps_historical_context():
    result = source.prepare_authenticated_plan(plan(), key="test", session=Session())
    assert result["status"] == "PREPARED_EXPIRY_PAYOFF"
    assert result["curve"]["pnl"] == [-200, -200, 0, 500]
    assert result["source_boundary"]["terms"] == "server_observed_bounded_https_reference"
    assert result["source_boundary"]["discovery_snapshot_authenticated"] is False
    assert result["source_boundary"]["current_quote_eligible"] is False
    assert result["temporal_context"]["historical_first_availability_established"] is False


@pytest.mark.parametrize("access,expiry,allowed", [("feature", 9999999999, True), ("unlimited", 9999999999, True),
    ("operator", 9999999999, True), ("denied", 9999999999, False), ("feature", 1, False), ("outage", 9999999999, False)])
def test_existing_uncached_entitlement_rule_shared_by_private_read(monkeypatch, access, expiry, allowed):
    from app import options_auth as auth, billing, paywall
    principal = OptionsPrincipal("subject", "issuer", "epoch", expiry)
    monkeypatch.setattr(auth, "_authenticate", lambda _: (principal, "operator@example.test"))
    record = {"features": ["terminal_live_options"] if access == "feature" else [], "tier": "unlimited" if access == "unlimited" else "pro"}
    monkeypatch.setattr(billing, "read_entitlement", lambda _: None if access == "outage" else record)
    monkeypatch.setattr(paywall, "_operator_unlimited", lambda _: access == "operator")
    if allowed:
        assert auth.resolve_entitled_options_principal("token") == principal
    else:
        with pytest.raises(OptionUseRefused, match="entitlement_unavailable"):
            auth.resolve_entitled_options_principal("token")


def test_reference_constructor_pins_qualified_origin_profile_and_bounds(monkeypatch):
    actual = source.RestProber
    seen = []
    def make(*args, **kwargs):
        seen.append(kwargs.copy())
        return actual(*args, **kwargs)
    monkeypatch.setattr(source, "RestProber", make)
    contexts = source.plan_inputs(plan(), known_by="2026-10-24T12:00:00Z")
    source.read_plan_reference(contexts, key="test", known_by="2026-10-24T12:00:00Z", session=Session())
    assert seen[0]["base_url"] == "https://api.polygon.io"
    assert seen[0]["profile"] == "selected_expiry"
    assert seen[0]["max_bytes"] == 262144 and seen[0]["max_rows"] == 100
    assert seen[0]["request_budget"].max_gets == 1
