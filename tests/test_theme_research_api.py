"""T09 transport contract tests for the GMI semiconductor theme research API.

Two harnesses share this file:

* an *isolated* ``api_client`` fixture that mounts only ``app.theme_research.router``
  on a fresh :class:`fastapi.FastAPI` so the auth order can be proven without any
  other router's behaviour shaping the response;
* the *real* :mod:`app.main` app via :class:`fastapi.testclient.TestClient`, with
  only the existing principal / entitlement seams overridden exactly the way
  ``tests/test_earnings_api.py`` does it — no new auth surface.

The T09 contract pinned here:

* auth (the ``require_site_full_user`` dependency) resolves BEFORE any reader or
  bundle construction, BEFORE the body is parsed — anonymous + malformed body
  yields a 401/403 with the four private headers, never a leaked 422;
* every response on these paths — 200, 400, 401, 403, 404, 405, 409, 413, 503 —
  carries the four private headers;
* no write side-effect: ``engine.theme_graph.store.write_evidence``,
  ``subprocess.Popen`` and ``os.system`` are never called;
* rights filtering is fresh-snapshot: a rights decision that moves between two
  same-process requests reaches the route without a watcher or a restart;
* unknown / out-of-scope / valid-but-unauthorized assertion refs map to the
  SAME not_available body — no existence disclosure;
* production default is 503 service_unavailable (private reader unbound);
* the route is mounted on the production app exactly once and the existing
  site-access regression suite still passes.

Run with the repo's virtualenv::

    ~/lanes/venv/bin/python -m pytest tests/test_theme_research_api.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.theme_research as theme_research  # noqa: E402
import app.earnings as earnings_api  # noqa: E402
from engine.theme_graph import rights as rights_module  # noqa: E402
import engine.theme_graph.store as theme_store  # noqa: E402
from app.main import app as production_app  # noqa: E402
from tests.semiconductor_research_helpers import (  # noqa: E402
    load_bundle_case,
    load_case,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "contracts"
    / "market_ontology"
    / "semiconductor_theme_research.v1.schema.json"
)
_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}
_PAID_USER = {"id": "paid-user", "tier": "essential"}
_FREE_USER = {"id": "free-user", "tier": "free"}
# The full body shape (all optional fields supplied) so the body parser
# succeeds for the entitlement-gated happy paths.
_WITNESS_BODY = {
    "anchor_theme_id": "ai_semiconductors",
    "slice_key": "hbm_packaging",
    "view": "composition",
    "time_mode": "latest",
    "source_cutoff": None,
    "recorded_cutoff": None,
    "offset": 0,
    "limit": 50,
    "expected_generation": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_private_headers(response) -> None:
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value, (
            f"private header {name!r} expected {value!r}, got {response.headers.get(name)!r}"
        )


def _valid_body(**overrides: Any) -> dict:
    body = dict(_WITNESS_BODY)
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Isolated harness — only theme_research.router; auth override permitted
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client(monkeypatch):
    """A FastAPI() with only the theme_research router, no overrides.

    Used by the auth-order test: this fixture must NOT override the
    auth dependency, so the natural deny path proves the route.
    """
    monkeypatch.delenv("MACRO_REPO", raising=False)
    app = FastAPI()
    app.include_router(theme_research.router)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Real-app harness — production app, principal seam overridden the same way as
# tests/test_earnings_api.py
# ---------------------------------------------------------------------------

@pytest.fixture
def entitled_client(monkeypatch):
    """Real app with the existing principal/entitlement seam overridden.

    Mirrors ``tests/test_earnings_api.py::entitled_client`` so the production
    route is exercised end-to-end. FastAPI's ``dependency_overrides`` is keyed
    on the original callable object, so it works regardless of whether the
    router captured the function before or after the override. The override
    callable MUST be zero-arg — FastAPI inspects the override signature and
    would otherwise turn the parameters into query params.
    """
    paid = lambda: dict(_PAID_USER)
    production_app.dependency_overrides[earnings_api.require_site_full_user] = paid
    try:
        with TestClient(production_app, raise_server_exceptions=False) as client:
            yield client
    finally:
        production_app.dependency_overrides.pop(earnings_api.require_site_full_user, None)


@pytest.fixture
def free_client(monkeypatch):
    """Real app with a registered-but-unpaid principal to test the 403 branch."""

    def raise_forbid():
        # Use _private_error so the four private headers ride on the 403 — the
        # production override goes through the same wrapper.
        raise earnings_api._private_error(
            403, detail={"locked": True, "required_feature": "site_full"},
        )

    production_app.dependency_overrides[earnings_api.require_site_full_user] = raise_forbid
    try:
        with TestClient(production_app, raise_server_exceptions=False) as client:
            yield client
    finally:
        production_app.dependency_overrides.pop(earnings_api.require_site_full_user, None)


@pytest.fixture
def bundle_loader(monkeypatch):
    """Install a synthetic bundle loader that returns ``witness_hbm_packaging``
    for any query. Tests that need a different fixture override the loader
    directly. Tracks reader calls so anonymous paths can assert zero calls."""
    calls: list[dict] = []

    def _loader(query, *, principal):
        calls.append({"query": query, "principal": principal})
        case = load_case("witness_hbm_packaging")
        from engine.market_ontology.semiconductor_theme_research import (
            OwnerBundle, ResearchQuery,
        )
        src = case["bundle"]
        bundle = OwnerBundle(
            revision_tuple=tuple(tuple(x) for x in src["revision_tuple"]),
            rights_revision=src["rights_revision"],
            assertions=tuple(src["assertions"]),
            identity_results=tuple(src["identity_results"]),
            event_workspaces=tuple(src["event_workspaces"]),
            financial_packets=tuple(src["financial_packets"]),
            interpretation_blocks=tuple(src["interpretation_blocks"]),
            native_refs=tuple(src["native_refs"]),
            omissions=tuple(src["omissions"]),
        )
        return ResearchQuery(**case["query"]), bundle

    # Replace with a simple wrapper: the function returns a tuple (query, bundle),
    # but the route expects just the bundle. We adapt to fit both shapes.
    def loader(query, *, principal):
        calls.append({"query": query, "principal": principal})
        case = load_case("witness_hbm_packaging")
        from engine.market_ontology.semiconductor_theme_research import (
            OwnerBundle,
        )
        src = case["bundle"]
        return OwnerBundle(
            revision_tuple=tuple(tuple(x) for x in src["revision_tuple"]),
            rights_revision=src["rights_revision"],
            assertions=tuple(src["assertions"]),
            identity_results=tuple(src["identity_results"]),
            event_workspaces=tuple(src["event_workspaces"]),
            financial_packets=tuple(src["financial_packets"]),
            interpretation_blocks=tuple(src["interpretation_blocks"]),
            native_refs=tuple(src["native_refs"]),
            omissions=tuple(src["omissions"]),
        )

    monkeypatch.setattr(theme_research, "load_authorized_owner_bundle", loader)
    return calls


# ---------------------------------------------------------------------------
# 1. AUTH ORDER — the verbatim plan test
# ---------------------------------------------------------------------------

def test_unauthorized_request_never_constructs_private_reader(api_client, monkeypatch):
    """Anonymous + bad body → 401/403 with private headers; reader untouched.

    This is the verbatim plan test: the auth dep must reject BEFORE the reader
    is constructed and BEFORE the body is parsed, so the framework's 422
    cannot leak before the privacy envelope.
    """
    import app.theme_research as route

    def forbidden_reader(*args, **kwargs):
        raise AssertionError("private reader touched before authorization")

    monkeypatch.setattr(route, "load_authorized_owner_bundle", forbidden_reader)

    response = api_client.post("/api/themes/v1/research/query", json={})

    assert response.status_code in (401, 403), response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# 2. AUTH SURFACE — anonymous, expired-token, free-tier → 401/403 private
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/themes/v1/research/query",
                                  "/api/themes/v1/research/evidence"])
def test_anonymous_request_is_rejected_with_private_headers(api_client, path):
    response = api_client.post(path, json=_valid_body())
    assert response.status_code in (401, 403), response.text
    _assert_private_headers(response)


def test_expired_token_is_rejected_with_private_headers(monkeypatch):
    """An expired/invalid bearer must surface the same private 401/403."""

    def deny():
        raise earnings_api._private_error(401, "invalid token")

    app = FastAPI()
    app.include_router(theme_research.router)
    app.dependency_overrides[earnings_api.require_site_full_user] = deny
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/themes/v1/research/query",
                json=_valid_body(),
                headers={"Authorization": "Bearer expired"},
            )
    finally:
        app.dependency_overrides.pop(earnings_api.require_site_full_user, None)
    assert response.status_code == 401, response.text
    _assert_private_headers(response)


def test_free_tier_principal_is_rejected_with_private_headers(free_client, monkeypatch):
    monkeypatch.setattr(
        theme_research, "load_authorized_owner_bundle",
        lambda *_a, **_kw: pytest.fail("reader touched for an unpaid principal"),
    )
    response = free_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert response.status_code == 403, response.text
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# 3. BODY VALIDATION — bad bodies surface a private 400 (or 422) AFTER auth
# ---------------------------------------------------------------------------

def _auth_ok_app(monkeypatch) -> TestClient:
    paid = lambda: dict(_PAID_USER)
    app = FastAPI()
    app.include_router(theme_research.router)
    app.dependency_overrides[earnings_api.require_site_full_user] = paid
    # Install an empty bundle loader so the route reaches the validator layer
    # (which surfaces 400 on offset>0-without-expected_generation, etc.) instead
    # of falling through to PrivateStoreUnavailable → 503. The body-shape
    # mutations in test_authenticated_malformed_body_is_rejected_with_private_headers
    # happen BEFORE the loader runs, so this only matters for the post-body
    # validator checks (offset>0 page2, future/missing cutoffs, etc.).
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle
    empty_bundle = OwnerBundle(
        revision_tuple=(("identity", "identity-vintage-empty"),),
        rights_revision="synthetic-rights-empty",
        assertions=(),
        identity_results=(), event_workspaces=(), financial_packets=(),
        interpretation_blocks=(), native_refs=(), omissions=(),
    )
    monkeypatch.setattr(
        theme_research, "load_authorized_owner_bundle",
        lambda *a, **kw: empty_bundle,
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("mutation", [
    pytest.param({"limit": 0}, id="limit-zero"),
    pytest.param({"limit": 101}, id="limit-above-max"),
    pytest.param({"offset": -1}, id="offset-negative"),
    pytest.param({"offset": 1}, id="page2-without-expected_generation"),
    pytest.param({"slice_key": "bogus_slice"}, id="bad-slice"),
    pytest.param({"view": "bogus_view"}, id="bad-view"),
    pytest.param({"time_mode": "future"}, id="bad-time-mode"),
    pytest.param({"anchor_theme_id": "BAD-ID"}, id="bad-anchor-theme"),
    pytest.param({"unexpected": True}, id="extra-field"),
])
def test_authenticated_malformed_body_is_rejected_with_private_headers(
    monkeypatch, mutation,
):
    body = _valid_body()
    body.update(mutation)
    client = _auth_ok_app(monkeypatch)
    response = client.post("/api/themes/v1/research/query", json=body)
    assert response.status_code in (400, 422), response.text
    _assert_private_headers(response)


def test_malformed_json_is_rejected_with_private_headers(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    response = client.post(
        "/api/themes/v1/research/query",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422), response.text
    _assert_private_headers(response)


def test_unparseable_object_body_is_rejected_with_private_headers(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    response = client.post(
        "/api/themes/v1/research/query",
        content=b"[1, 2, 3]",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422), response.text
    _assert_private_headers(response)


def test_oversized_body_is_rejected_with_413_private_headers(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    huge = {"anchor_theme_id": "ai_semiconductors",
            "slice_key": "hbm_packaging",
            "view": "composition",
            "time_mode": "latest",
            "source_cutoff": None,
            "recorded_cutoff": None,
            "offset": 0,
            "limit": 50,
            "expected_generation": None,
            "padding": "x" * (9 * 1024)}
    response = client.post(
        "/api/themes/v1/research/query", json=huge,
    )
    assert response.status_code == 413, response.text
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# 4. WRONG METHOD and REMAINDER path
# ---------------------------------------------------------------------------

def test_get_on_query_route_returns_405_with_private_headers(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    response = client.get("/api/themes/v1/research/query")
    assert response.status_code == 405, response.text
    _assert_private_headers(response)


def test_get_on_evidence_route_returns_405_with_private_headers(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    response = client.get("/api/themes/v1/research/evidence")
    assert response.status_code == 405, response.text
    _assert_private_headers(response)


def test_remainder_path_returns_private_404_behind_auth(monkeypatch):
    client = _auth_ok_app(monkeypatch)
    response = client.post("/api/themes/v1/research/bogus/deep/path", json=_valid_body())
    assert response.status_code == 404, response.text
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# 5. HAPPY PATH — entitled + synthetic bundle → 200, schema, headers, authority
# ---------------------------------------------------------------------------

def _witness_query_and_bundle() -> tuple[dict, Any]:
    case = load_case("witness_hbm_packaging")
    return case["query"], case["bundle"]


def test_entitled_query_returns_200_and_validates_against_schema(
    entitled_client, bundle_loader, monkeypatch,
):
    response = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert response.status_code == 200, response.text
    _assert_private_headers(response)
    payload = response.json()
    assert payload["schema"] == "semiconductor_theme_research.v1"
    assert payload["definition_version"] == "2026-09-24.1"
    assert payload["authority"] == {
        "can_rank": False, "can_gate": False, "can_size": False,
        "can_originate": False, "can_open_entry": False,
    }
    assert bundle_loader, "reader must be called for entitled callers"
    # Validate against the published schema.
    schema = json.loads(SCHEMA_PATH.read_text())
    import jsonschema  # noqa: PLC0415 — schema validation is test-side only
    jsonschema.validate(payload, schema)
    assert payload["generation"].startswith("gen_")
    assert len(payload["generation"]) == 4 + 32
    assert payload["authorized_coverage"]["selected"] >= 0


def test_evidence_route_with_returned_generation_returns_200(
    entitled_client, bundle_loader, monkeypatch,
):
    case = load_case("witness_hbm_packaging")
    witness_query = case["query"]
    # First fetch the generation from a snapshot call.
    snapshot = entitled_client.post(
        "/api/themes/v1/research/query",
        json={"anchor_theme_id": witness_query["anchor_theme_id"],
               "slice_key": witness_query["slice_key"],
               "view": witness_query["view"],
               "time_mode": witness_query["time_mode"],
               "source_cutoff": witness_query["source_cutoff"],
               "recorded_cutoff": witness_query["recorded_cutoff"],
               "offset": witness_query["offset"],
               "limit": witness_query["limit"],
               "expected_generation": witness_query["expected_generation"]},
    )
    assert snapshot.status_code == 200, snapshot.text
    snapshot_payload = snapshot.json()
    generation = snapshot_payload["generation"]
    # Pick one assertion_ref out of the snapshot.
    refs = [r for r in snapshot_payload["evidence_refs"] if r.get("kind") == "assertion"]
    if not refs:
        pytest.skip("witness fixture has no selected assertions (rights filter emptied it)")
    ref = refs[0]["assertion_ref"]

    response = entitled_client.post(
        "/api/themes/v1/research/evidence",
        json={"anchor_theme_id": witness_query["anchor_theme_id"],
              "slice_key": witness_query["slice_key"],
              "view": witness_query["view"],
              "time_mode": witness_query["time_mode"],
              "source_cutoff": witness_query["source_cutoff"],
              "recorded_cutoff": witness_query["recorded_cutoff"],
              "offset": witness_query["offset"],
              "limit": witness_query["limit"],
              "expected_generation": generation,
              "assertion_ref": ref},
    )
    assert response.status_code == 200, response.text
    _assert_private_headers(response)
    payload = response.json()
    assert payload["assertion_ref"] == ref


def test_evidence_with_stale_generation_returns_409_refresh_required(
    entitled_client, bundle_loader,
):
    case = load_case("witness_hbm_packaging")
    q = case["query"]
    refs = []
    snapshot = entitled_client.post(
        "/api/themes/v1/research/query",
        json={"anchor_theme_id": q["anchor_theme_id"], "slice_key": q["slice_key"],
              "view": q["view"], "time_mode": q["time_mode"],
              "source_cutoff": q["source_cutoff"], "recorded_cutoff": q["recorded_cutoff"],
              "offset": q["offset"], "limit": q["limit"], "expected_generation": None},
    )
    assert snapshot.status_code == 200
    refs = [r for r in snapshot.json()["evidence_refs"] if r.get("kind") == "assertion"]
    if not refs:
        pytest.skip("witness has no selected assertions")
    ref = refs[0]["assertion_ref"]
    # Use a stale generation.
    response = entitled_client.post(
        "/api/themes/v1/research/evidence",
        json={"anchor_theme_id": q["anchor_theme_id"], "slice_key": q["slice_key"],
              "view": q["view"], "time_mode": q["time_mode"],
              "source_cutoff": q["source_cutoff"], "recorded_cutoff": q["recorded_cutoff"],
              "offset": q["offset"], "limit": q["limit"],
              "expected_generation": "gen_" + "0" * 32,
              "assertion_ref": ref},
    )
    assert response.status_code == 409, response.text
    _assert_private_headers(response)
    body = response.json()
    assert body == {"error": {"code": "refresh_required", "action": "reset_to_first_page"}} \
        or body.get("detail") == {"error": {"code": "refresh_required",
                                            "action": "reset_to_first_page"}}


# ---------------------------------------------------------------------------
# 6. EVIDENCE 404 — unknown / out-of-scope / valid-but-unauthorized share shape
# ---------------------------------------------------------------------------

def _evidence_body_with(ref: str, generation: str = "gen_" + "a" * 32) -> dict:
    body = _valid_body(expected_generation=generation)
    body["assertion_ref"] = ref
    return body


def test_unknown_out_of_scope_and_unauthorized_refs_share_byte_identical_404(
    entitled_client, bundle_loader,
):
    fixture = load_case("unauthorized_missing_or_hidden")
    refs = fixture["assertion_refs"]
    expected_body = fixture["expected_404_body"]

    # Fetch the real generation first — without it, the route would 409 on
    # generation_changed BEFORE reaching the assertion-ref lookup, and we would
    # be measuring the wrong failure shape (the test is about existence
    # disclosure, not about stale-generation disclosure).
    snapshot = entitled_client.post("/api/themes/v1/research/query", json=_valid_body())
    assert snapshot.status_code == 200, snapshot.text
    generation = snapshot.json()["generation"]

    bodies: list[bytes] = []
    for label, ref in refs.items():
        response = entitled_client.post(
            "/api/themes/v1/research/evidence",
            json=_evidence_body_with(ref, generation=generation),
        )
        assert response.status_code == 404, (label, response.text)
        _assert_private_headers(response)
        body = response.json()
        # FastAPI wraps HTTPException detail under "detail"
        actual = body.get("detail", body)
        assert actual == expected_body, (label, actual)
        bodies.append(response.content)

    # Byte-identical bodies: no existence disclosure across the three shapes.
    assert bodies[0] == bodies[1] == bodies[2]


def test_evidence_route_never_calls_reader_when_anonymous(api_client, monkeypatch):
    """The private reader must not run for unauthenticated callers — even when
    the body would have been a valid-looking evidence request."""
    fixture = load_case("unauthorized_missing_or_hidden")
    ref = fixture["assertion_refs"]["valid_but_unauthorized"]
    calls: list[Any] = []

    def forbidden(*_a, **_kw):
        calls.append(1)
        raise AssertionError("reader touched for anonymous caller")

    monkeypatch.setattr(theme_research, "load_authorized_owner_bundle", forbidden)
    response = api_client.post(
        "/api/themes/v1/research/evidence", json=_evidence_body_with(ref),
    )
    assert response.status_code in (401, 403), response.text
    assert calls == [], "reader was called for an anonymous caller"
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# 7. REVOKED RIGHTS WARM — fresh snapshot, no restart
# ---------------------------------------------------------------------------

def test_revoked_rights_warm_drops_assertions_after_registry_flip(
    entitled_client, monkeypatch, tmp_path,
):
    """Same process, two calls: the first returns N selected; the registry
    flips to ``unresolved`` for the witness family; the second call (no
    restart, no watcher) drops the family's assertions, adds the
    ``rights_refused_families_hidden`` limitation, and the generation changes
    because the snapshot revision moved."""
    fixture = load_case("revoked_rights_warm")
    bundle_spec = fixture["bundle"]
    family = fixture["rights_family_used"]
    initial_path = tmp_path / "theme_sources.yml"
    revoked_path = tmp_path / "theme_sources_revoked.yml"
    initial_path.write_text(json.dumps(fixture["rights_registry_initial"]))
    # The initial file is allowed (direct_display_ok); we keep it on disk so the
    # first call reads from initial_path.
    revoked_path.write_text(json.dumps(fixture["rights_registry_revoked"]))

    # Monkey-patch the registry_path() function so it points at initial_path;
    # after the first call we swap the on-disk bytes and re-route to
    # revoked_path. load_registry_snapshot() re-reads the bytes on every call.
    path_box: dict[str, Path] = {"path": initial_path}
    monkeypatch.setattr(
        rights_module, "registry_path", lambda: path_box["path"],
    )

    from engine.market_ontology.semiconductor_theme_research import (
        OwnerBundle, ResearchQuery,
    )
    q = fixture["query"]
    query_obj = ResearchQuery(**q)
    # The bundle's rights_revision is built from the FRESH snapshot so the
    # generation fingerprint moves when the on-disk registry flips. Same
    # fixture, same revision_tuple; only the snapshot revision changes.
    def loader(*_a, **_kw):
        snap_revision, _ = rights_module.load_registry_snapshot()
        return OwnerBundle(
            revision_tuple=tuple(tuple(x) for x in bundle_spec["revision_tuple"]),
            rights_revision=snap_revision,
            assertions=tuple(bundle_spec["assertions"]),
            identity_results=tuple(bundle_spec["identity_results"]),
            event_workspaces=tuple(bundle_spec["event_workspaces"]),
            financial_packets=tuple(bundle_spec["financial_packets"]),
            interpretation_blocks=tuple(bundle_spec["interpretation_blocks"]),
            native_refs=tuple(bundle_spec["native_refs"]),
            omissions=tuple(bundle_spec["omissions"]),
        )
    monkeypatch.setattr(
        theme_research, "load_authorized_owner_bundle", loader,
    )

    # First call: registry allows the family — all assertions selected.
    first = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["authorized_coverage"]["selected"] == fixture["expected_first_selected"]
    assert "rights_refused_families_hidden" not in first_payload["limitations"]
    first_generation = first_payload["generation"]
    assert first_generation.startswith("gen_")

    # Flip the registry: the same family is now unresolved.
    path_box["path"] = revoked_path

    # Same process, second call: snapshot re-reads the file, the family is
    # refused, every assertion whose source_uri maps to it is dropped.
    second = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    assert second_payload["authorized_coverage"]["selected"] == fixture["expected_after_revocation_selected"]
    assert "rights_refused_families_hidden" in second_payload["limitations"]
    # Generation must change because the snapshot revision moved.
    assert second_payload["generation"] != first_generation


# ---------------------------------------------------------------------------
# 8. NO-WRITE proof — write_evidence / subprocess / os.system never called
# ---------------------------------------------------------------------------

def test_no_write_side_effects_on_any_success_path(entitled_client, monkeypatch):
    write_calls: list[Any] = []
    popen_calls: list[Any] = []
    system_calls: list[Any] = []

    def write_blocked(*a, **kw):
        write_calls.append((a, kw))
        raise AssertionError("write_evidence called inside the read-only transport")

    def popen_blocked(*a, **kw):
        popen_calls.append((a, kw))
        raise AssertionError("subprocess called inside the read-only transport")

    def system_blocked(*a, **kw):
        system_calls.append((a, kw))
        raise AssertionError("os.system called inside the read-only transport")

    monkeypatch.setattr(theme_store, "write_evidence", write_blocked)
    monkeypatch.setattr(subprocess, "Popen", popen_blocked)
    monkeypatch.setattr(os, "system", system_blocked)

    case = load_case("witness_hbm_packaging")
    from engine.market_ontology.semiconductor_theme_research import (
        OwnerBundle, ResearchQuery,
    )
    src = case["bundle"]
    bundle = OwnerBundle(
        revision_tuple=tuple(tuple(x) for x in src["revision_tuple"]),
        rights_revision=src["rights_revision"],
        assertions=tuple(src["assertions"]),
        identity_results=tuple(src["identity_results"]),
        event_workspaces=tuple(src["event_workspaces"]),
        financial_packets=tuple(src["financial_packets"]),
        interpretation_blocks=tuple(src["interpretation_blocks"]),
        native_refs=tuple(src["native_refs"]),
        omissions=tuple(src["omissions"]),
    )
    monkeypatch.setattr(
        theme_research, "load_authorized_owner_bundle",
        lambda *a, **kw: bundle,
    )

    response = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert response.status_code == 200, response.text

    assert write_calls == [], "write_evidence was reached on a read-only path"
    assert popen_calls == [], "subprocess.Popen was reached on a read-only path"
    assert system_calls == [], "os.system was reached on a read-only path"


# ---------------------------------------------------------------------------
# 9. PRODUCTION DEFAULT — without monkeypatch, entitled → 503, no leak
# ---------------------------------------------------------------------------

def test_production_default_returns_503_service_unavailable_with_no_leak(
    entitled_client,
):
    """No monkeypatch on the loader → default raises PrivateStoreUnavailable →
    503 with the private envelope, body contains no path/URL/exception text."""
    response = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert response.status_code == 503, response.text
    _assert_private_headers(response)
    body_text = response.text
    for forbidden in (
        "PrivateStoreUnavailable", "Traceback", "/opt/", "config/", "fixtures/",
        "registry_path", "Exception",
    ):
        assert forbidden not in body_text, f"leak: {forbidden!r} in {body_text!r}"
    body = response.json()
    payload = body.get("detail", body)
    assert payload == {"error": {"code": "service_unavailable", "action": "retry_later"}}


# ---------------------------------------------------------------------------
# 10. ROUTE UNIQUENESS — paid routes are mounted on the production app
# ---------------------------------------------------------------------------

def test_paid_theme_research_routes_are_mounted_on_production_app():
    schema = production_app.openapi()
    paths = schema.get("paths", {})
    for expected in (
        "/api/themes/v1/research/query",
        "/api/themes/v1/research/evidence",
    ):
        assert expected in paths, expected
        assert "post" in paths[expected]
    # The private remainder route is include_in_schema=False; only a real
    # request proves it is mounted, so a TestClient hit must 401 (not 404).
    client = TestClient(production_app, raise_server_exceptions=False)
    r = client.post("/api/themes/v1/research/anything/here")
    assert r.status_code == 401, r.text


def test_theme_research_routes_are_unique_against_existing_themes_prefix():
    """No new themes-prefix route shadows an existing one (the gate the spec
    requires). The schema dump is the canonical list."""
    paths = set(production_app.openapi().get("paths", {}).keys())
    themes_paths = {p for p in paths if "/api/themes/" in p}
    assert themes_paths == {
        "/api/themes/v1/research/query",
        "/api/themes/v1/research/evidence",
    }


# ---------------------------------------------------------------------------
# 11. OWNER PARITY — the verdict is ASKED of engine.theme_graph.rights, never
# restated locally (T09 review fix)
# ---------------------------------------------------------------------------

def _install_warm_owner_state(monkeypatch, tmp_path) -> dict:
    """Shared setup for the owner-parity tests: point the rights OWNER at the
    fixture's PERMITTING synthetic registry and install the warm bundle whose
    every assertion maps to ``mastermind_curated`` (rights class
    ``direct_display_ok`` in that registry). Returns the fixture dict."""
    fixture = load_case("revoked_rights_warm")
    registry = tmp_path / "theme_sources_owner_parity.yml"
    registry.write_text(json.dumps(fixture["rights_registry_initial"]))
    monkeypatch.setattr(rights_module, "registry_path", lambda: registry)

    from engine.market_ontology.semiconductor_theme_research import OwnerBundle

    bundle_spec = fixture["bundle"]

    def loader(*_a, **_kw):
        snap_revision, _ = rights_module.load_registry_snapshot()
        return OwnerBundle(
            revision_tuple=tuple(tuple(x) for x in bundle_spec["revision_tuple"]),
            rights_revision=snap_revision,
            assertions=tuple(bundle_spec["assertions"]),
            identity_results=tuple(bundle_spec["identity_results"]),
            event_workspaces=tuple(bundle_spec["event_workspaces"]),
            financial_packets=tuple(bundle_spec["financial_packets"]),
            interpretation_blocks=tuple(bundle_spec["interpretation_blocks"]),
            native_refs=tuple(bundle_spec["native_refs"]),
            omissions=tuple(bundle_spec["omissions"]),
        )

    monkeypatch.setattr(theme_research, "load_authorized_owner_bundle", loader)
    return fixture


def test_tightening_the_rights_owner_drops_assertions_through_the_route(
    entitled_client, monkeypatch, tmp_path,
):
    """The transport must OBSERVE the owner's rule, not restate it.

    Same process, registry bytes UNCHANGED (the family is still
    ``direct_display_ok``): the first call is a permit control, then ONLY the
    owner's ``engine.theme_graph.rights.EMISSION_OK`` is tightened to drop
    ``direct_display_ok`` — and the second call must drop the family's
    assertions and append ``rights_refused_families_hidden``. Against the
    rejected local-copy design this is exactly the case that failed open."""
    fixture = _install_warm_owner_state(monkeypatch, tmp_path)

    # Permit control with the owner as shipped: every assertion is kept.
    permit = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert permit.status_code == 200, permit.text
    permit_payload = permit.json()
    assert permit_payload["authorized_coverage"]["selected"] == \
        fixture["expected_first_selected"]
    assert "rights_refused_families_hidden" not in permit_payload["limitations"]

    # Tighten ONLY the owner's rule; the registry on disk does not move.
    monkeypatch.setattr(
        rights_module, "EMISSION_OK", frozenset({"derived_display_ok"}),
    )

    tightened = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert tightened.status_code == 200, tightened.text
    tightened_payload = tightened.json()
    assert tightened_payload["authorized_coverage"]["selected"] == \
        fixture["expected_after_revocation_selected"]
    assert "rights_refused_families_hidden" in tightened_payload["limitations"]


def test_owner_permitting_keeps_assertions_with_no_rights_limitation(
    entitled_client, monkeypatch, tmp_path,
):
    """Permit counterpart: with the owner permitting the family, the verdict
    keeps every assertion and the response carries NO
    ``rights_refused_families_hidden`` limitation."""
    fixture = _install_warm_owner_state(monkeypatch, tmp_path)

    response = entitled_client.post(
        "/api/themes/v1/research/query", json=_valid_body(),
    )
    assert response.status_code == 200, response.text
    _assert_private_headers(response)
    payload = response.json()
    assert payload["authorized_coverage"]["selected"] == \
        fixture["expected_first_selected"]
    assert "rights_refused_families_hidden" not in payload["limitations"]


def test_transport_carries_no_local_rights_restatement():
    """No-restatement source scan: the transport asks the owner, so
    ``app/theme_research.py`` must carry neither the owner's permission-set
    constant nor any rights-class literal, and must call the owner's veto."""
    source = (ROOT / "app" / "theme_research.py").read_text(encoding="utf-8")
    for forbidden in ("EMISSION_OK", "direct_display_ok", "derived_display_ok"):
        assert forbidden not in source, f"restated rights constant: {forbidden!r}"
    assert "assert_current_emission_allowed(" in source