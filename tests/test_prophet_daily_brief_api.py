"""Route-boundary tests for the authenticated daily brief transport.

The route-boundary tests use TEST-OWNER stubs: these prove only this
router's auth ordering, exact query grammar, status framing and verbatim
pass-through on the new router mounted alone. They are NOT live or native
producer/source proof — the real B1 native fixture proof is integrated by the
final registered-app test below using the actual native writer/reader.
"""
from __future__ import annotations

from contextlib import nullcontext

import importlib
import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

URL = "/api/prophet/daily-brief/v1"
SOURCE = "sha256:" + "a" * 64
PAIR = "b" * 32
RECEIPT = "sha256:" + "c" * 64
GENERATION = "peg:" + "d" * 64
GOOD = {"source_sha256": SOURCE, "pair_id": PAIR, "selection_receipt": RECEIPT}

DASHED_UUID = "8b14c2d3-4f5a-4b6c-8d9e-0f1a2b3c4d5e"  # incumbent emits UUIDs; the pin is 32-hex only
BARE_RECEIPT = "c" * 64
BARE_GENERATION = "d" * 64
SHORT_GENERATION = "peg:" + "d" * 63

AVAILABLE = {
    "status": "AVAILABLE",
    "reason_codes": [],
    "reference_session": "2026-10-12",
    "episodes": [{"pair_id": PAIR, "ticker": "AMZN"}],
}

REPEATED_SOURCE = (
    "?" + "&".join(["source_sha256=" + SOURCE, "source_sha256=" + SOURCE,
                    "pair_id=" + PAIR, "selection_receipt=" + RECEIPT])
)


def _query(pairs: dict) -> str:
    return "?" + "&".join(f"{key}={value}" for key, value in pairs.items())


INVALID_QUERIES = [
    "",  # nothing pinned
    "?source_sha256=",  # empty pin
    "?source_sha256=deadbeef",  # missing sha256: prefix
    "?source_sha256=sha256:" + "a" * 63,  # short digest
    "?source_sha256=sha256:" + "A" * 64,  # uppercase hex
    "?source_sha256=SHA256:" + "a" * 64,  # uppercase prefix
    _query({"source_sha256": SOURCE, "pair_id": PAIR}),  # missing selection_receipt
    _query({**GOOD, "selection_receipt": ""}),
    _query({**GOOD, "selection_receipt": BARE_RECEIPT}),
    _query({"source_sha256": SOURCE, "pair_id": PAIR[:31], "selection_receipt": RECEIPT}),
    _query({"source_sha256": SOURCE, "pair_id": PAIR.upper(), "selection_receipt": RECEIPT}),
    _query({"source_sha256": SOURCE, "pair_id": DASHED_UUID, "selection_receipt": RECEIPT}),
    _query({"source_sha256": SOURCE, "pair_id": "../../private", "selection_receipt": RECEIPT}),
    _query({**GOOD, "candidate_generation_id": BARE_GENERATION}),
    _query({**GOOD, "candidate_generation_id": SHORT_GENERATION}),
    _query({**GOOD, "candidate_generation_id": "PEG:" + "d" * 64}),
    _query({**GOOD, "root": "/private"}),  # no server path override query
    _query({**GOOD, "day": "2026-10-12"}),
    REPEATED_SOURCE,  # repeated pin
]


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def forbidden_owner(*_args, **_kwargs):
    pytest.fail("this request must not reach the owner read")


def recording_owner(calls, envelope):
    """Test-owned producer stub: records the forwarded pins, returns one envelope."""

    def read_today_candidate_projection(repo_root, *, expected_source_sha256,
                                        expected_pair_id, expected_selection_receipt,
                                        expected_candidate_generation_id=None):
        calls.append({
            "repo_root": repo_root,
            "expected_source_sha256": expected_source_sha256,
            "expected_pair_id": expected_pair_id,
            "expected_selection_receipt": expected_selection_receipt,
            "expected_candidate_generation_id": expected_candidate_generation_id,
        })
        return envelope() if callable(envelope) else dict(envelope)

    return read_today_candidate_projection


def bind_owner(monkeypatch, stub):
    """Point the route's request-scoped owner import at the test stub."""
    try:
        module = importlib.import_module("scripts.build_stock_library")
    except Exception:  # noqa: BLE001 — absent/optional in this tree; inject a bare stand-in
        module = types.ModuleType("scripts.build_stock_library")
        monkeypatch.setitem(sys.modules, "scripts.build_stock_library", module)
    # raising=False: the owner function may not be landed in a partial tree.
    monkeypatch.setattr(module, "read_today_candidate_projection", stub, raising=False)


def test_daily_brief_route_is_available():
    assert importlib.util.find_spec("app.prophet_daily_brief"), "daily brief transport is absent"


def test_optional_owner_runtime_does_not_break_router_load_or_anonymous_auth(tmp_path):
    """Router import and a denied request stay free of the heavy producer runtime."""
    probe = r'''
import builtins
import sys

real_import = builtins.__import__
def without_optional(name, *args, **kwargs):
    if name.split(".", 1)[0] in {"pyarrow", "pandas"}:
        raise ModuleNotFoundError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = without_optional

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.prophet_daily_brief as brief

URL = "/api/prophet/daily-brief/v1"
GOOD = ("?source_sha256=sha256:" + "a" * 64 + "&pair_id=" + "b" * 32
        + "&selection_receipt=sha256:" + "c" * 64)

assert "scripts.build_stock_library" not in sys.modules
app = FastAPI()
app.include_router(brief.router)
client = TestClient(app)
denied = client.get(URL + GOOD)
assert denied.status_code == 401, denied.text
assert denied.headers["cache-control"] == "private, no-store"
assert denied.headers["vary"] == "Authorization"
assert "scripts.build_stock_library" not in sys.modules
'''
    environment = os.environ.copy()
    environment["BIOCATALYST_PUBLIC_ROOT"] = str(tmp_path / "not-provisioned")
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=Path(__file__).resolve().parents[1],
        env=environment, capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def route(monkeypatch, tmp_path):
    mod = importlib.import_module("app.prophet_daily_brief")
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    return mod


@pytest.fixture
def client(route):
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "paid-fixture"}
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("denial", [401, 403])
@pytest.mark.parametrize("busy", [False, True])
def test_real_auth_chain_denies_before_query_or_owner_read(route, monkeypatch, denial, busy):
    import app.main as main
    import app.paywall as paywall

    calls = []
    def authenticate(_authorization):
        calls.append("authenticate")
        if denial == 401:
            raise HTTPException(401, "missing bearer token")
        return {"id": "free-fixture"}
    def entitle(_user, *, always=False):
        assert always is True
        calls.append("entitle")
        raise HTTPException(403, "site_full required")
    monkeypatch.setattr(main, "require_user", authenticate)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    bind_owner(monkeypatch, forbidden_owner)
    app = FastAPI()
    app.include_router(route.router)
    with route._READ_ADMISSION if busy else nullcontext():
        with TestClient(app) as boundary:
            response = boundary.get(URL + "?source_sha256=not-a-hash&pair_id=../private")
    assert response.status_code == denial
    assert calls == (["authenticate"] if denial == 401 else ["authenticate", "entitle"])
    private(response)


def test_available_envelope_passes_through_untouched(client, route, monkeypatch, tmp_path):
    calls = []
    bind_owner(monkeypatch, recording_owner(calls, AVAILABLE))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 200
    assert response.json() == AVAILABLE  # the producer's own envelope
    assert set(response.json()) == set(AVAILABLE)  # nothing added: no receipt, no selection, no timestamps
    assert str(tmp_path) not in response.text
    private(response)
    call = calls[0]
    assert call["repo_root"] == route._REPO_ROOT
    assert call["expected_source_sha256"] == SOURCE
    assert call["expected_pair_id"] == PAIR
    assert call["expected_selection_receipt"] == RECEIPT
    assert call["expected_candidate_generation_id"] is None


def test_partial_envelope_is_also_success(client, monkeypatch):
    calls = []
    envelope = {"status": "PARTIAL", "reason_codes": ["EPISODE_SOURCE_LAGGED"], "episodes": []}
    bind_owner(monkeypatch, recording_owner(calls, envelope))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 200
    assert response.json() == envelope
    private(response)


@pytest.mark.parametrize("reason", ["SOURCE_BINDING_MISMATCH", "SELECTION_BINDING_MISMATCH"])
def test_producer_binding_mismatch_is_a_conflict(client, monkeypatch, reason):
    calls = []
    envelope = {"status": "UNAVAILABLE", "reason_codes": [reason]}
    bind_owner(monkeypatch, recording_owner(calls, envelope))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 409
    assert response.json() == envelope
    private(response)


@pytest.mark.parametrize("reason", [
    "SOURCE_UNREADABLE", "SOURCE_CORRUPT", "SELECTION_RACE",
    "CANDIDATE_GENERATION_MISMATCH",
])
def test_unavailable_envelope_is_a_private_outage(client, monkeypatch, reason):
    calls = []
    envelope = {"status": "UNAVAILABLE", "reason_codes": [reason]}
    bind_owner(monkeypatch, recording_owner(calls, envelope))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 503
    assert response.json() == envelope
    private(response)
    assert len(calls) == 1  # exactly one owner read; the route never retries or refreshes


def test_optional_generation_pin_is_forwarded(client, monkeypatch):
    calls = []
    bind_owner(monkeypatch, recording_owner(calls, {"status": "AVAILABLE", "reason_codes": []}))
    pinned = {**GOOD, "candidate_generation_id": GENERATION}
    assert client.get(URL, params=pinned).status_code == 200
    assert calls[-1]["expected_candidate_generation_id"] == GENERATION
    assert client.get(URL, params=GOOD).status_code == 200
    assert calls[-1]["expected_candidate_generation_id"] is None


def test_request_rereads_owner_on_each_call(client, monkeypatch):
    calls = []
    readings = iter([
        {"status": "AVAILABLE", "reason_codes": [], "edition": "first"},
        {"status": "UNAVAILABLE", "reason_codes": ["SELECTION_RACE"], "edition": "second"},
    ])
    bind_owner(monkeypatch, recording_owner(calls, lambda: dict(next(readings))))
    first = client.get(URL, params=GOOD)
    second = client.get(URL, params={**GOOD, "selection_receipt": "sha256:" + "e" * 64})
    assert first.status_code == 200
    assert first.json()["edition"] == "first"
    assert second.status_code == 503
    assert second.json()["edition"] == "second"
    assert len(calls) == 2  # no cached projection and no public polling between calls


@pytest.mark.parametrize("query", INVALID_QUERIES)
def test_invalid_query_is_rejected_before_owner_read(client, monkeypatch, query):
    bind_owner(monkeypatch, forbidden_owner)
    response = client.get(URL + query)
    assert response.status_code == 400
    assert response.json() == {"error": "INVALID_QUERY"}
    private(response)


def test_owner_runtime_failure_collapses_to_generic_private_outage(client, monkeypatch):
    def broken_owner(*_args, **_kwargs):
        raise RuntimeError("boom /private/secret/source.parquet")

    bind_owner(monkeypatch, broken_owner)
    response = client.get(URL, params=GOOD)
    assert response.status_code == 503
    assert response.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
    assert "private/secret" not in response.text
    private(response)


def test_missing_owner_module_is_a_private_outage(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "scripts.build_stock_library", None)
    response = client.get(URL, params=GOOD)
    assert response.status_code == 503
    assert response.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
    private(response)


def test_unknown_envelope_shape_is_a_private_outage(client, monkeypatch):
    calls = []
    bind_owner(monkeypatch, recording_owner(calls, {"status": "MYSTERY", "reason_codes": []}))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 503
    assert response.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
    private(response)


@pytest.mark.parametrize("bad_value", [float("nan"), {"unsupported"}])
def test_non_json_owner_envelope_retains_private_unavailable(client, monkeypatch, bad_value):
    bind_owner(monkeypatch, recording_owner([], {"status": "PARTIAL", "reason_codes": [], "invalid_value": bad_value}))
    response = client.get(URL, params=GOOD)
    assert response.status_code == 503
    assert response.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
    private(response)


def test_actual_native_owner_pending_then_same_source_api_reread(tmp_path, monkeypatch):
    from app import prophet_daily_brief as route
    from app import main as auth_owner
    from app import paywall

    spec = importlib.util.spec_from_file_location("native_today_source", Path(__file__).with_name("test_prophet_today_provenance.py"))
    _native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_native)
    source, _candidate = _native._native_today(tmp_path, monkeypatch)
    original = source.read_bytes()
    monkeypatch.setattr(route, "_REPO_ROOT", tmp_path)
    calls = []

    def authenticated(request):
        calls.append("authenticated")
        return {"sub": "explicit-native-test-user"}

    def entitled(user, request=None, always=False):
        calls.append("paid")
        assert always is True
        return None

    monkeypatch.setattr(auth_owner, "require_user", authenticated)
    monkeypatch.setattr(paywall, "enforce_site_full", entitled)
    app = auth_owner.app
    assert auth_owner.prophet_daily_brief_router is route.router
    client = TestClient(app)
    binding = _native.producer.today_selection_source_binding(original)
    params = {key: binding[key] for key in ("source_sha256", "pair_id", "selection_receipt")}
    first = client.get("/api/prophet/daily-brief/v1", params=params)
    assert first.status_code == 200
    assert first.json()["status"] == "PARTIAL"
    assert first.json()["candidates"][0]["reason_codes"] == ["CANDIDATE_RECONCILIATION_PENDING"]
    _native.writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
        recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    second = client.get("/api/prophet/daily-brief/v1", params=params)
    assert second.status_code == 200
    assert second.json()["status"] == "PARTIAL"
    assert second.json()["source_binding"] == first.json()["source_binding"]
    assert second.json()["candidate_generation_id"] != first.json()["candidate_generation_id"]
    assert second.json()["candidates"][0]["status"] == "AVAILABLE"
    assert second.json()["candidates"][0]["candidate_input"]["selection_receipt"] == params["selection_receipt"]
    assert source.read_bytes() == original
    stale = client.get("/api/prophet/daily-brief/v1", params={**params, "source_sha256": "sha256:" + "0" * 64})
    assert stale.status_code == 409
    old_generation = client.get("/api/prophet/daily-brief/v1", params={**params,
        "candidate_generation_id": first.json()["candidate_generation_id"]})
    assert old_generation.status_code == 503
    assert old_generation.json()["reason_codes"] == ["CANDIDATE_GENERATION_MISMATCH"]
    for response in (first, second, stale, old_generation):
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"
    assert calls == ["authenticated", "paid"] * 4


def test_overlapping_read_is_refused_without_queuing_and_then_recovers(client, monkeypatch):
    """One expensive read must not admit another or block an unrelated route."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()
    calls = []

    def held_owner(*args, **kwargs):
        calls.append((args, kwargs))
        entered.set()
        assert release.wait(15), "test did not release the owner"
        return AVAILABLE

    bind_owner(monkeypatch, held_owner)
    client.app.add_api_route("/health-for-admission-test", lambda: {"ok": True})
    pool = ThreadPoolExecutor(max_workers=2)
    first = pool.submit(client.get, URL, params=GOOD)
    try:
        assert entered.wait(5), "first owner read did not start"
        second = pool.submit(client.get, URL, params=GOOD)
        busy = second.result(timeout=5)
        assert busy.status_code == 503
        assert busy.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
        private(busy)
        assert len(calls) == 1
        assert not first.done()
        health = pool.submit(client.get, "/health-for-admission-test").result(timeout=5)
        assert health.status_code == 200 and health.json() == {"ok": True}
    finally:
        release.set()
        pool.shutdown(wait=True)
    response = first.result()
    assert response.status_code == 200 and response.json() == AVAILABLE
    private(response)
    after = client.get(URL, params=GOOD)
    assert after.status_code == 200 and after.json() == AVAILABLE
    assert len(calls) == 2


@pytest.mark.parametrize("failure", ["import", "owner", "serialization", "shape"])
def test_failed_read_releases_admission_for_next_request(client, route, monkeypatch, failure):
    with monkeypatch.context() as patch:
        if failure == "import":
            patch.setitem(sys.modules, "scripts.build_stock_library", None)
        elif failure == "owner":
            def broken_owner(*args, **kwargs):
                raise RuntimeError("private source detail")
            bind_owner(patch, broken_owner)
        elif failure == "serialization":
            bind_owner(patch, recording_owner([], {"status": "AVAILABLE", "bad": float("nan")}))
        else:
            bind_owner(patch, lambda *args, **kwargs: None)
        refused = client.get(URL, params=GOOD)
        assert refused.status_code == 503
        assert refused.json() == {"error": "DAILY_BRIEF_UNAVAILABLE"}
        private(refused)
    calls = []
    bind_owner(monkeypatch, recording_owner(calls, AVAILABLE))
    recovered = client.get(URL, params=GOOD)
    assert recovered.status_code == 200 and recovered.json() == AVAILABLE
    private(recovered)
    assert len(calls) == 1


def test_busy_reader_does_not_replace_invalid_query_response(client, route, monkeypatch):
    bind_owner(monkeypatch, forbidden_owner)
    with route._READ_ADMISSION:
        response = client.get(URL, params={**GOOD, "root": "/private"})
    assert response.status_code == 400
    assert response.json() == {"error": "INVALID_QUERY"}
    private(response)
