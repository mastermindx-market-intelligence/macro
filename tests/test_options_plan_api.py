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






@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setenv("OPTIONS_PLAN_REFERENCE_ENABLED", "1")
    monkeypatch.setenv("OPTIONS_PLAN_REFERENCE_PATH", "/qualified/private/reference.json")
    monkeypatch.setenv("OPTIONS_PLAN_REFERENCE_SHA256", "a" * 64)


@pytest.fixture
def client():
    app = FastAPI(); app.include_router(api.router)
    return TestClient(app)


def allow(monkeypatch):
    monkeypatch.setattr(api, "resolve_entitled_options_principal", lambda _: OptionsPrincipal("subject", "issuer", "epoch", 9999999999))


def test_absent_and_denied_auth_cannot_call_source(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "prepare_retained_plan", lambda *a, **k: calls.append(True))
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
    def prepare(payload, *, reference_path, expected_sha256):
        calls.append((payload, str(reference_path), expected_sha256)); return dict(status="PREPARED_EXPIRY_PAYOFF")
    monkeypatch.setattr(api, "prepare_retained_plan", prepare)
    response = client.post("/api/options/plan/expiry", json=plan(), headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert "Authorization" in response.headers["vary"]
    assert calls == [(plan(), "/qualified/private/reference.json", "a" * 64)]


@pytest.mark.parametrize("mutation", ["contexts", "reference_observation", "reference_sha256", "extra"])
def test_caller_cannot_supply_source_evidence(mutation):
    payload = plan(); payload[mutation] = {"verdict": "entitled", "sha256": "a" * 64}
    with pytest.raises(ValueError):
        source.plan_inputs(payload, known_by="2026-10-24T12:00:00Z")


@pytest.mark.parametrize("change", ["mixed_expiry", "missing_entry", "adjusted", "bad_spots", "wrong_basis"])
def test_invalid_math_rejected_before_source(change, monkeypatch):
    payload = plan()
    if change == "mixed_expiry":
        payload["draft"]["legs"].append(copy.deepcopy(payload["draft"]["legs"][0]))
        payload["draft"]["legs"][1]["snapshot"]["identity"]["exp"] = "2026-10-30"
    if change == "missing_entry": payload["draft"]["legs"][0]["assumptions"]["entry"] = None
    if change == "adjusted": payload["draft"]["legs"][0]["snapshot"]["identity"]["adjustedRootHint"] = True
    if change == "bad_spots": payload["spots"] = [float("nan")]
    if change == "wrong_basis": payload["payoff_basis"]["expiration"] = "2026-10-30"
    monkeypatch.setattr(source, "read_private_reference", lambda *a, **k: pytest.fail("invalid math must not read source"))
    with pytest.raises((ValueError, TypeError)):
        source.prepare_retained_plan(payload, reference_path=None, expected_sha256="a" * 64)






def test_http_body_bounds_duplicate_nonfinite_and_errors_no_store(client, monkeypatch):
    allow(monkeypatch)
    for raw, status in [(b"x" * (65536 + 1), 413), (b'{"schema":1,"schema":2}', 422), (b'{"spots":[NaN]}', 422)]:
        response = client.post("/api/options/plan/expiry", content=raw,
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"})
        assert response.status_code == status
        assert response.headers["cache-control"] == "private, no-store"
    def fail(*args, **kwargs):
        raise source.PlanSourceUnavailable("contract_terms_unavailable")
    monkeypatch.setattr(api, "prepare_retained_plan", fail)
    response = client.post("/api/options/plan/expiry", json=plan(), headers={"Authorization": "Bearer token"})
    assert response.status_code == 503
    assert response.json() == dict(status="UNAVAILABLE", reason="contract_terms_unavailable")




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




def retained_observation():
    return dict(schema="options_reference_capability_observation/v1", state="response_observed",
        origin="https://api.polygon.io", path="/v3/reference/options/contracts",
        params=dict(underlying_ticker="SPY", expiration_date="2026-10-23", as_of="2026-10-19"),
        capability=dict(http_status=200, verdict="entitled"), contracts=[contract_row()],
        payload_sha256="b" * 64, completed_at="2026-10-20T08:43:25.307134+00:00",
        historical_first_availability_established=False)


def private_artifact(tmp_path, observation=None):
    from hashlib import sha256
    directory = tmp_path / "qualified-capture"; directory.mkdir(mode=0o700)
    path = directory / "reference.json"
    raw = json.dumps(observation or retained_observation()).encode()
    path.write_bytes(raw); path.chmod(0o600)
    return path, sha256(raw).hexdigest()


def test_fixed_private_reference_to_curve_never_acquires_provider(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    path, digest = private_artifact(tmp_path)
    monkeypatch.setattr("requests.Session.get", lambda *a, **k: pytest.fail("provider must never be called"))
    result = source.prepare_retained_plan(plan(), reference_path=path, expected_sha256=digest,
        now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc))
    assert result["status"] == "PREPARED_EXPIRY_PAYOFF"
    assert result["curve"]["pnl"] == [-200, -200, 0, 500]
    boundary = result["source_boundary"]
    assert boundary["terms"] == "server_held_qualified_reference"
    assert boundary["reference_as_of"] == "2026-10-19"
    assert boundary["reference_observed_at"] == "2026-10-20T08:43:25.307134+00:00"
    assert result["known_by"] == "2026-10-24T12:00:00+00:00"
    assert boundary["reference_request_count"] == 0
    assert boundary["reference_root"] == "SPY" and boundary["reference_contract_count"] == 1
    assert boundary["reference_expirations"] == ["2026-10-23"]
    assert boundary["current_terms_qualified"] is False
    assert boundary["original_response_bytes_replayed"] is False


@pytest.mark.parametrize("change", ["missing", "hash", "mode", "parent", "symlink", "duplicate", "nonfinite", "future", "denied"])
def test_private_reader_rejects_unqualified_or_changed_artifact(tmp_path, change):
    from hashlib import sha256
    path, digest = private_artifact(tmp_path)
    if change == "missing": path.unlink()
    if change == "hash": digest = "c" * 64
    if change == "mode": path.chmod(0o644)
    if change == "parent": path.parent.chmod(0o755)
    if change == "symlink":
        other = path.with_name("original.json"); path.rename(other); path.symlink_to(other)
    if change == "duplicate": path.write_bytes(b'{"schema":"x","schema":"y"}'); digest = sha256(path.read_bytes()).hexdigest()
    if change == "nonfinite": path.write_bytes(b'{"value":NaN}'); digest = sha256(path.read_bytes()).hexdigest()
    if change in {"future", "denied"}:
        observed = retained_observation()
        if change == "future": observed["completed_at"] = "2099-01-01T00:00:00Z"
        if change == "denied": observed["capability"]["verdict"] = "not_entitled"
        path.write_bytes(json.dumps(observed).encode()); digest = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(source.PlanSourceUnavailable): source.read_private_reference(path, digest)


def test_mismatched_reference_does_not_substitute_another_contract(tmp_path):
    observed = retained_observation(); observed["contracts"][0]["strike_price"] = 764
    observed["contracts"][0]["ticker"] = "O:SPY261023C00764000"
    path, digest = private_artifact(tmp_path, observed)
    result = source.prepare_retained_plan(plan(), reference_path=path, expected_sha256=digest)
    assert result["status"] == "UNPRICED" and result["curve"] is None
    assert any(r["code"] == "TERMS_UNQUALIFIED" for r in result["reasons"])
    assert result["source_boundary"]["reference_root"] == "SPY"
    assert result["source_boundary"]["reference_contract_count"] == 1
    assert result["source_boundary"]["reference_expirations"] == ["2026-10-23"]
