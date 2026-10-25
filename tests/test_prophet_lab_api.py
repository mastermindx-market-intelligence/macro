"""Transport-layer contract tests for ``GET /api/prophet/lab/v1``.

These tests exercise auth, the kill switch, response framing, and app.main
router registration in isolation from the projection itself (that is
exhaustively covered, fixture-by-fixture, in tests/test_prophet_lab.py).
``app.prophet_lab.build_lab_response`` is monkeypatched to a canned payload
throughout so a failure here can only be a transport-layer regression.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

pytest.importorskip("fastapi", reason="Prophet Lab API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.prophet_lab as prophet_lab_api  # noqa: E402
from engine.prophet_lab.contracts import ALL_FALSE_AUTHORITY, KILL_SWITCH_ENV, SCHEMA_LAB_BOARD  # noqa: E402
from engine.prophet_lab.intelligence_vector import (  # noqa: E402
    ALL_FALSE_AUTHORITY as D5_ALL_FALSE_AUTHORITY,
    SCHEMA_INTELLIGENCE_VECTOR,
    build_earnings_intelligence_vector,
)
from engine.neuralweb.company_intelligence_reader import WorkspaceChainIntegrityError  # noqa: E402
from engine.us_candidate_episode import (  # noqa: E402
    CandidateEpisodeStoreSnapshot,
    EpisodeContractError,
    ValidatedCandidateEpisodeGeneration,
    canonical_json,
    episode_id as b1_episode_id,
    load_candidate_episode_store_snapshot,
)
from lib.dataos.identity import IssuerMaster  # noqa: E402

_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _assert_private_headers(response) -> None:
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers.get(name) == value


def _canned_payload() -> dict:
    return {
        "schema": SCHEMA_LAB_BOARD,
        "health": {"radar_spool_readable": False},
        "authority": dict(ALL_FALSE_AUTHORITY),
        "boards": {},
    }


_D5_EPISODE_GENERATION = "peg:" + "a" * 64
_D5_EPISODE_KNOWN_AT = "2026-07-30T20:05:00Z"
_D5_ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-07-30T20:00:00Z",
    "price": "100.0000",
    "basis": "turn_watch.reset_low",
    "source_receipt": "sha256:" + "b" * 64,
}
_D5_EPISODE_ID = b1_episode_id(
    "SEC:US-XNAS-AAPL", "epoch_0", _D5_ANCHOR, 1,
)

#: A canonical B1 identity this store never held. An unknown ID must be
#: unknown HISTORY, not a live OPENED event with its row removed: the second
#: is an impossible generation, and the two must never answer the same way.
_D5_UNKNOWN_EPISODE_ID = b1_episode_id(
    "SEC:US-XNAS-AAPL", "epoch_0", {**_D5_ANCHOR, "price": "101.0000"}, 1,
)


def _d5_episode() -> dict:
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": _D5_EPISODE_ID,
        "company_id": "ISS:US:320193",
        "security_id": "SEC:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "state": "CANDIDATE",
        "opened_at": _D5_EPISODE_KNOWN_AT,
        "opened_session": "2026-07-30",
        "structural_anchor": deepcopy(_D5_ANCHOR),
        "expert_events": ["radar:event:content-addressed-1"],
    }


def _d5_snapshot(*, episodes: tuple[dict, ...] | None = None) -> CandidateEpisodeStoreSnapshot:
    episode_rows = episodes if episodes is not None else (_d5_episode(),)
    return CandidateEpisodeStoreSnapshot(
        generation_id=_D5_EPISODE_GENERATION,
        generation=ValidatedCandidateEpisodeGeneration(
            path=Path("/not/serialized/b1-generation"),
            events=({
                "event_type": "OPENED",
                "episode_id": _D5_EPISODE_ID,
                "known_at": _D5_EPISODE_KNOWN_AT,
            },),
            suppressions=(),
            episodes=episode_rows,
            receipt={},
        ),
    )


def _d5_master(*, include_cik: bool) -> IssuerMaster:
    return IssuerMaster.from_records([{
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US:320193",
        "issuer_state": "active",
        "listing_key": "US:XNAS:AAPL",
        "issuer_cik": "0000320193" if include_cik else None,
    }])


def _raise_integrity_error(_company_id: str):
    raise WorkspaceChainIntegrityError("dummy source chain hash mismatch")


@pytest.fixture()
def episode_intelligence_client(monkeypatch):
    monkeypatch.setattr(
        prophet_lab_api,
        "load_candidate_episode_store_snapshot",
        lambda _root: _d5_snapshot(),
        raising=False,
    )
    monkeypatch.setattr(
        prophet_lab_api,
        "_load_issuer_master",
        lambda _path: _d5_master(include_cik=False),
        raising=False,
    )
    monkeypatch.setattr(
        prophet_lab_api,
        "build_earnings_intelligence_vector",
        build_earnings_intelligence_vector,
        raising=False,
    )
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    app.dependency_overrides[prophet_lab_api.require_site_full_user] = lambda: {"id": "u-paid"}
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setattr(prophet_lab_api, "build_lab_response", lambda roots: _canned_payload())
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    app.dependency_overrides[prophet_lab_api.require_site_full_user] = lambda: {"id": "u-paid"}
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------
def test_paid_user_gets_200_with_frozen_schema_and_all_false_authority(app_client) -> None:
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA_LAB_BOARD
    assert body["authority"] == ALL_FALSE_AUTHORITY
    assert all(v is False for v in body["authority"].values())
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# auth: anonymous -> 401, free tier -> 403, paid -> 200 (house pattern)
# ---------------------------------------------------------------------------
def test_anonymous_caller_is_401(monkeypatch) -> None:
    monkeypatch.setattr(prophet_lab_api, "build_lab_response", lambda roots: _canned_payload())
    import app.main as main_mod

    monkeypatch.setattr(
        main_mod,
        "require_user",
        lambda _authorization: (_ for _ in ()).throw(HTTPException(401, "missing bearer token")),
    )
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as client:
        response = client.get("/api/prophet/lab/v1")
    assert response.status_code == 401
    _assert_private_headers(response)


def test_free_tier_caller_is_403(monkeypatch) -> None:
    monkeypatch.setattr(prophet_lab_api, "build_lab_response", lambda roots: _canned_payload())
    import app.main as main_mod
    import app.paywall as paywall_mod

    monkeypatch.setattr(main_mod, "require_user", lambda _authorization: {"id": "u-free"})
    monkeypatch.setattr(paywall_mod, "_entitled", lambda _user_id, _feature: (False, "free"))
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as client:
        response = client.get(
            "/api/prophet/lab/v1", headers={"Authorization": "Bearer free-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"]["required_feature"] == "site_full"
    _assert_private_headers(response)


def test_paid_caller_authenticates_then_entitles_in_order(monkeypatch) -> None:
    import app.main as main_mod
    import app.paywall as paywall_mod

    calls: list[tuple[str, object]] = []
    user = {"id": "u-paid"}
    entitled = {"id": "u-paid", "tier": "pro"}

    def require_user(authorization):
        calls.append(("require_user", authorization))
        return user

    def enforce_site_full(candidate, *, always=False):
        calls.append(("enforce_site_full", (candidate, always)))
        return entitled

    monkeypatch.setattr(main_mod, "require_user", require_user)
    monkeypatch.setattr(paywall_mod, "enforce_site_full", enforce_site_full)
    assert prophet_lab_api.require_site_full_user("Bearer paid-token") == entitled
    assert calls == [
        ("require_user", "Bearer paid-token"),
        ("enforce_site_full", (user, True)),
    ]


def test_402_from_enforce_site_full_propagates_with_private_headers(monkeypatch) -> None:
    import app.main as main_mod
    import app.paywall as paywall_mod

    monkeypatch.setattr(main_mod, "require_user", lambda _authorization: {"id": "u-free"})

    def deny(_user, *, always=False):
        assert always is True
        raise HTTPException(402, "site_full required", headers={"Retry-After": "60"})

    monkeypatch.setattr(paywall_mod, "enforce_site_full", deny)
    with pytest.raises(HTTPException) as excinfo:
        prophet_lab_api.require_site_full_user("Bearer free-token")
    assert excinfo.value.status_code == 402
    assert excinfo.value.headers["Retry-After"] == "60"
    assert excinfo.value.headers.get("Cache-Control") == "private, no-store"
    assert excinfo.value.headers.get("Vary") == "Authorization"


# ---------------------------------------------------------------------------
# kill switch (PROPHET_LAB_DISABLED) — independent of Radar's own switches
# ---------------------------------------------------------------------------
def test_kill_switch_returns_503_and_skips_the_projection(app_client, monkeypatch) -> None:
    def _boom(roots):
        raise AssertionError("projection must not run while PROPHET_LAB_DISABLED=1")

    monkeypatch.setattr(prophet_lab_api, "build_lab_response", _boom)
    monkeypatch.setenv(KILL_SWITCH_ENV, "1")
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "prophet_lab_disabled"
    _assert_private_headers(response)


@pytest.mark.parametrize(
    "off_value",
    # review N4: the OFF set is case-insensitive, and "no"/"off" join the
    # original "0"/"false"/"" set.
    ["0", "false", "False", "FALSE", "", "no", "No", "NO", "off", "OFF", "Off"],
)
def test_kill_switch_off_values_serve_normally(app_client, monkeypatch, off_value) -> None:
    monkeypatch.setenv(KILL_SWITCH_ENV, off_value)
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 200


@pytest.mark.parametrize("on_value", ["1", "true", "TRUE", "yes", "banana"])
def test_kill_switch_any_unrecognized_or_truthy_value_disables(
    app_client, monkeypatch, on_value,
) -> None:
    # review N4: fail TOWARD disabled — an operator typo or an unexpected
    # value takes the Lab down rather than silently leaving it up.
    monkeypatch.setenv(KILL_SWITCH_ENV, on_value)
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 503
    assert response.json()["error"] == "prophet_lab_disabled"


def test_kill_switch_is_independent_of_radar_live_switches(app_client, monkeypatch) -> None:
    # Radar's own kill switch must have zero effect on the Lab API — LAB-0 §5:
    # "Kill switch: PROPHET_LAB_DISABLED stands the API down independently of
    # Radar's own ENTRY_RADAR_LIVE_ENABLE".
    monkeypatch.setenv("ENTRY_RADAR_LIVE_DISABLED", "1")
    monkeypatch.delenv(KILL_SWITCH_ENV, raising=False)
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# review S2 (cheap half) — the spool-source label the health block echoes
# ---------------------------------------------------------------------------
def test_resolve_roots_labels_the_primary_env_var(monkeypatch) -> None:
    monkeypatch.setenv("PROPHET_LAB_RADAR_SPOOL_DIR", "/tmp/prophet-lab-spool")
    monkeypatch.delenv("ENTRY_RADAR_SPOOL_DIR", raising=False)
    roots = prophet_lab_api._resolve_roots()  # noqa: SLF001
    assert roots.radar_spool_source_label == "PROPHET_LAB_RADAR_SPOOL_DIR"
    assert str(roots.radar_spool_dir) == "/tmp/prophet-lab-spool"


def test_resolve_roots_labels_the_fallback_env_var(monkeypatch) -> None:
    monkeypatch.delenv("PROPHET_LAB_RADAR_SPOOL_DIR", raising=False)
    monkeypatch.setenv("ENTRY_RADAR_SPOOL_DIR", "/tmp/entry-radar-spool")
    roots = prophet_lab_api._resolve_roots()  # noqa: SLF001
    assert roots.radar_spool_source_label == "ENTRY_RADAR_SPOOL_DIR"
    assert str(roots.radar_spool_dir) == "/tmp/entry-radar-spool"


def test_resolve_roots_labels_unconfigured_when_neither_env_var_is_set(monkeypatch) -> None:
    monkeypatch.delenv("PROPHET_LAB_RADAR_SPOOL_DIR", raising=False)
    monkeypatch.delenv("ENTRY_RADAR_SPOOL_DIR", raising=False)
    roots = prophet_lab_api._resolve_roots()  # noqa: SLF001
    assert roots.radar_spool_source_label == "unconfigured"
    assert roots.radar_spool_dir is None


# ---------------------------------------------------------------------------
# a failed projection is a clean 503, never a 500
# ---------------------------------------------------------------------------
def test_projection_failure_is_503_not_500(app_client, monkeypatch) -> None:
    def _boom(roots):
        raise RuntimeError("boom")

    monkeypatch.setattr(prophet_lab_api, "build_lab_response", _boom)
    response = app_client.get("/api/prophet/lab/v1")
    assert response.status_code == 503
    assert response.json()["error"] == "prophet_lab_unavailable"
    _assert_private_headers(response)


# ---------------------------------------------------------------------------
# GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence — D5 Task 3
# ---------------------------------------------------------------------------
def _episode_intelligence_url(episode_id: str = _D5_EPISODE_ID) -> str:
    return f"/api/prophet/lab/v1/episodes/{episode_id}/intelligence"


def test_episode_intelligence_paid_user_gets_exact_b1_generation_and_private_200(
    episode_intelligence_client,
) -> None:
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == SCHEMA_INTELLIGENCE_VECTOR
    assert body["episode_ref"] == {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": _D5_EPISODE_ID,
        "generation_id": _D5_EPISODE_GENERATION,
        "identity_ref": "ISS:US:320193",
    }
    assert body["decision_cut"]["known_at"] == _D5_EPISODE_KNOWN_AT
    assert body["authority"] == D5_ALL_FALSE_AUTHORITY
    assert body["fusion_bindings"] == []
    _assert_private_headers(response)


def test_episode_intelligence_anonymous_caller_is_401(monkeypatch) -> None:
    import app.main as main_mod

    monkeypatch.setattr(
        main_mod,
        "require_user",
        lambda _authorization: (_ for _ in ()).throw(HTTPException(401, "missing bearer token")),
    )
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as client:
        response = client.get(_episode_intelligence_url())
    assert response.status_code == 401
    _assert_private_headers(response)


def test_episode_intelligence_free_tier_caller_is_403(monkeypatch) -> None:
    import app.main as main_mod
    import app.paywall as paywall_mod

    monkeypatch.setattr(main_mod, "require_user", lambda _authorization: {"id": "u-free"})
    monkeypatch.setattr(paywall_mod, "_entitled", lambda _user_id, _feature: (False, "free"))
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as client:
        response = client.get(
            _episode_intelligence_url(), headers={"Authorization": "Bearer free-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"]["required_feature"] == "site_full"
    _assert_private_headers(response)


def test_episode_intelligence_kill_switch_is_503_and_skips_b1(
    episode_intelligence_client, monkeypatch,
) -> None:
    def _boom(_root):
        raise AssertionError("B1 must not be read while PROPHET_LAB_DISABLED is active")

    monkeypatch.setattr(
        prophet_lab_api, "load_candidate_episode_store_snapshot", _boom, raising=False,
    )
    monkeypatch.setenv(KILL_SWITCH_ENV, "1")
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 503
    assert response.json()["error"] == "prophet_lab_disabled"
    _assert_private_headers(response)


def test_episode_intelligence_absent_episode_is_private_404(
    episode_intelligence_client,
) -> None:
    """An identity this generation never held is the incumbent private 404.

    The unknown identity is unknown HISTORY — not a live OPENED event whose
    row was removed. The latter is an impossible generation under the real
    loader, and it answers 503 (below), never this 404.
    """
    response = episode_intelligence_client.get(
        _episode_intelligence_url(_D5_UNKNOWN_EPISODE_ID),
    )
    assert response.status_code == 404
    assert response.json() == {"error": "prophet_episode_not_found"}
    _assert_private_headers(response)


def test_episode_intelligence_absent_projection_without_owner_withdrawal_is_private_503(
    episode_intelligence_client, monkeypatch,
) -> None:
    """A live OPENED event whose row vanished is a contract failure, not a 404.

    The B1 owner removes an episode row only when its own opening event is
    retracted, so a row-absent/OPENED-present generation cannot be explained —
    it must fail closed instead of masquerading as an unknown identity.
    """
    monkeypatch.setattr(
        prophet_lab_api,
        "load_candidate_episode_store_snapshot",
        lambda _root: _d5_snapshot(episodes=()),
        raising=False,
    )
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 503
    assert response.json() == {
        "error": "prophet_episode_intelligence_unavailable",
        "detail": "Episode intelligence temporarily unavailable",
    }
    _assert_private_headers(response)


def test_episode_intelligence_identity_unresolved_is_typed_200(
    episode_intelligence_client,
) -> None:
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 200
    family = response.json()["evidence_families"][0]
    assert family["identity_state"] == "UNRESOLVED"
    assert family["coverage"] == {
        "state": "UNKNOWN",
        "basis": "canonical_identity_unresolved",
    }
    assert family["observations"][0]["absence_reasons"] == ["IDENTITY_UNRESOLVED"]


def test_episode_intelligence_not_covered_is_typed_200(
    episode_intelligence_client, monkeypatch,
) -> None:
    monkeypatch.setattr(
        prophet_lab_api,
        "_load_issuer_master",
        lambda _path: _d5_master(include_cik=True),
        raising=False,
    )

    def _not_covered(**kwargs):
        return build_earnings_intelligence_vector(
            **kwargs, find_event_id=lambda _company_id: None,
        )

    monkeypatch.setattr(
        prophet_lab_api, "build_earnings_intelligence_vector", _not_covered, raising=False,
    )
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 200
    family = response.json()["evidence_families"][0]
    assert family["identity_state"] == "RESOLVED"
    assert family["coverage"] == {
        "state": "NOT_COVERED",
        "basis": "no_current_generation_event",
    }
    assert family["observations"][0]["absence_reasons"] == ["NOT_COVERED"]


def test_episode_intelligence_corrupt_b1_is_private_503(
    episode_intelligence_client, monkeypatch,
) -> None:
    def _corrupt(_root):
        raise EpisodeContractError("dummy corrupt HEAD")

    monkeypatch.setattr(
        prophet_lab_api, "load_candidate_episode_store_snapshot", _corrupt, raising=False,
    )
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 503
    assert response.json() == {
        "error": "prophet_episode_intelligence_unavailable",
        "detail": "Episode intelligence temporarily unavailable",
    }
    _assert_private_headers(response)


def test_episode_intelligence_source_integrity_failure_is_private_503(
    episode_intelligence_client, monkeypatch,
) -> None:
    monkeypatch.setattr(
        prophet_lab_api,
        "_load_issuer_master",
        lambda _path: _d5_master(include_cik=True),
        raising=False,
    )

    def _integrity_failure(**kwargs):
        return build_earnings_intelligence_vector(
            **kwargs, find_event_id=_raise_integrity_error,
        )

    monkeypatch.setattr(
        prophet_lab_api,
        "build_earnings_intelligence_vector",
        _integrity_failure,
        raising=False,
    )
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 503
    assert response.json() == {
        "error": "prophet_episode_intelligence_unavailable",
        "detail": "Episode intelligence temporarily unavailable",
    }
    assert "dummy" not in response.text
    _assert_private_headers(response)


def test_episode_intelligence_response_has_no_prohibited_or_raw_fields(
    episode_intelligence_client, monkeypatch,
) -> None:
    episode = _d5_episode()
    episode.update({
        "body": "DUMMY RAW EPISODE BODY MUST NOT LEAK",
        "private_path": "/private/dummy-episode.json",
    })
    monkeypatch.setattr(
        prophet_lab_api,
        "load_candidate_episode_store_snapshot",
        lambda _root: _d5_snapshot(episodes=(episode,)),
        raising=False,
    )
    response = episode_intelligence_client.get(_episode_intelligence_url())
    assert response.status_code == 200
    body = response.json()
    prohibited = {
        "score", "rank", "weight", "confidence", "conviction", "evidence_count",
        "entry_open", "ENTRY_OPEN", "body", "claims", "transcript", "private_path",
        "path", "url", "workspace", "source_span",
    }

    def _keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from _keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from _keys(child)

    assert prohibited.isdisjoint(set(_keys(body)))
    serialized = json.dumps(body, sort_keys=True)
    assert "DUMMY RAW EPISODE BODY MUST NOT LEAK" not in serialized
    assert "/private/dummy-episode.json" not in serialized


def test_load_issuer_master_constructs_the_canonical_reader_from_parquet(tmp_path) -> None:
    pandas = pytest.importorskip("pandas")
    parquet_path = tmp_path / "security_master.parquet"
    pandas.DataFrame([{
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US:320193",
        "issuer_state": "active",
        "listing_key": "US:XNAS:AAPL",
        "issuer_cik": "0000320193",
    }]).to_parquet(parquet_path, index=False)
    master = prophet_lab_api._load_issuer_master(parquet_path)  # noqa: SLF001
    assert isinstance(master, IssuerMaster)
    assert master.cik_of_issuer("ISS:US:320193") == "0000320193"


# ---------------------------------------------------------------------------
# app.main registration
# ---------------------------------------------------------------------------
def test_route_declares_the_paid_dependency() -> None:
    route_dependencies = {
        route.path: {dependency.call for dependency in route.dependant.dependencies}
        for route in prophet_lab_api.router.routes
    }
    assert prophet_lab_api.require_site_full_user in route_dependencies["/api/prophet/lab/v1"]
    assert prophet_lab_api.require_site_full_user in route_dependencies[
        "/api/prophet/lab/v1/episodes/{episode_id}/intelligence"
    ]


def test_route_is_mounted_on_the_production_app() -> None:
    import app.main as main_mod

    public_paths = main_mod.app.openapi().get("paths", {})
    assert "/api/prophet/lab/v1" in public_paths
    assert "/api/prophet/lab/v1/episodes/{episode_id}/intelligence" in public_paths
    assert "/api/hub/prophet" in public_paths


# ---------------------------------------------------------------------------
# GET /api/hub/prophet — INTERNAL-ONLY (DEC:B1-PROPHET-PUBLIC-SPLIT)
#
# The guard reads request.client + headers directly rather than through a
# FastAPI Depends, so it is exercised as a plain function against hand-built
# Starlette Requests (deterministic — no TestClient transport ambiguity about
# what "client host" a test harness uses) and the route itself is exercised
# through TestClient with the guard monkeypatched, matching how every other
# test in this file isolates the transport layer from its dependency.
# ---------------------------------------------------------------------------
from starlette.requests import Request  # noqa: E402


def _hub_request(*, client_host: str | None, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/hub/prophet",
        "raw_path": b"/api/hub/prophet",
        "query_string": b"",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
        "client": (client_host, 51000) if client_host is not None else None,
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_hub_prophet_guard_allows_loopback_with_no_peer_header() -> None:
    assert prophet_lab_api._hub_prophet_authorized(  # noqa: SLF001
        _hub_request(client_host="127.0.0.1")
    ) is True
    assert prophet_lab_api._hub_prophet_authorized(  # noqa: SLF001
        _hub_request(client_host="::1")
    ) is True


def test_hub_prophet_guard_denies_loopback_carrying_a_peer_header() -> None:
    """Caddy's header_up REPLACES any inbound X-MM-Peer with the real TCP peer on
    every edge-proxied /api/* request, so its PRESENCE means this request came
    through the public edge even though the TCP peer still reads 127.0.0.1."""
    assert prophet_lab_api._hub_prophet_authorized(  # noqa: SLF001
        _hub_request(client_host="127.0.0.1", headers={"x-mm-peer": "203.0.113.7"})
    ) is False


def test_hub_prophet_guard_denies_non_loopback_peer() -> None:
    assert prophet_lab_api._hub_prophet_authorized(  # noqa: SLF001
        _hub_request(client_host="10.0.0.5")
    ) is False


def test_hub_prophet_guard_denies_when_client_is_unknown() -> None:
    assert prophet_lab_api._hub_prophet_authorized(  # noqa: SLF001
        _hub_request(client_host=None)
    ) is False


@pytest.fixture()
def hub_client(monkeypatch):
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as client:
        yield client


def test_hub_prophet_denied_caller_gets_401_json_no_detail(hub_client, monkeypatch) -> None:
    monkeypatch.setattr(prophet_lab_api, "_hub_prophet_authorized", lambda request: False)
    response = hub_client.get("/api/hub/prophet")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_hub_prophet_authorized_caller_gets_the_same_canonical_bytes(
    hub_client, monkeypatch, tmp_path
) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_bytes(b'{"schema": "prophet.index/v1", "plans": []}')
    monkeypatch.setattr(prophet_lab_api, "_hub_prophet_authorized", lambda request: True)
    monkeypatch.setattr(
        prophet_lab_api,
        "_resolve_roots",
        lambda: prophet_lab_api.LabRoots(prophet_index_path=index_path),
    )
    response = hub_client.get("/api/hub/prophet")
    assert response.status_code == 200
    assert response.content == index_path.read_bytes()
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.headers.get("cache-control") == "no-store"


def test_hub_prophet_missing_index_file_is_503(hub_client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(prophet_lab_api, "_hub_prophet_authorized", lambda request: True)
    monkeypatch.setattr(
        prophet_lab_api,
        "_resolve_roots",
        lambda: prophet_lab_api.LabRoots(prophet_index_path=tmp_path / "missing.json"),
    )
    response = hub_client.get("/api/hub/prophet")
    assert response.status_code == 503
    assert response.json() == {"error": "prophet_index_unavailable"}


def test_hub_prophet_reuses_the_lab_routes_own_path_resolution(monkeypatch) -> None:
    """Both routes must serve ONE file — this pins that hub_prophet reads through
    the exact same _resolve_roots() helper lab_v1 uses, not a second invented path."""
    sentinel = object()
    calls: list[object] = []
    monkeypatch.setattr(
        prophet_lab_api,
        "_resolve_roots",
        lambda: calls.append(sentinel) or prophet_lab_api.LabRoots(prophet_index_path=None),
    )
    monkeypatch.setattr(prophet_lab_api, "_hub_prophet_authorized", lambda request: True)
    request = _hub_request(client_host="127.0.0.1")
    prophet_lab_api.hub_prophet(request)
    assert calls == [sentinel]


@pytest.fixture
def earnings_detail_client(monkeypatch,tmp_path):
    from tests.test_intelligence_vector_units import _q06_vector,_install_q06
    _install_q06(tmp_path)
    app=FastAPI();app.include_router(prophet_lab_api.router)
    app.dependency_overrides[prophet_lab_api.require_site_full_user]=lambda:{"sub":"paid-fixture"}
    monkeypatch.delenv(KILL_SWITCH_ENV,raising=False)
    monkeypatch.setattr(prophet_lab_api,"_REPO_ROOT",tmp_path)
    monkeypatch.setattr(prophet_lab_api,"load_candidate_episode_store_snapshot",lambda _: _d5_snapshot())
    monkeypatch.setattr(prophet_lab_api,"_load_issuer_master",lambda _: _d5_master(include_cik=True))
    calls=[]
    def native_vector(**kwargs):
        calls.append(kwargs)
        return _q06_vector()
    monkeypatch.setattr(prophet_lab_api,"build_earnings_intelligence_vector",native_vector)
    with TestClient(app) as client:
        yield client,app,calls,tmp_path


def _earnings_detail_url(episode_id: str = _D5_EPISODE_ID):
    return f"/api/prophet/lab/v1/episodes/{episode_id}/earnings"


def test_earnings_detail_actual_route_uses_one_native_d5_read(earnings_detail_client):
    client,_,calls,_=earnings_detail_client
    response=client.get(_earnings_detail_url())
    assert response.status_code==200,response.text
    _assert_private_headers(response)
    body=response.json()
    assert body["schema"]=="prophet.episode_earnings_detail/v1"
    assert body["dossier"]["reported_changes"][0]["change_pct"]==pytest.approx(16.356501765281383)
    assert len(calls)==1
    assert all(v is False for v in body["authority"].values())


@pytest.mark.parametrize("status",[401,403])
def test_earnings_detail_auth_blocks_before_any_data(earnings_detail_client,status):
    client,app,calls,_=earnings_detail_client
    def deny():raise HTTPException(status_code=status,detail="fixture denial")
    app.dependency_overrides[prophet_lab_api.require_site_full_user]=deny
    assert client.get(_earnings_detail_url()).status_code==status
    assert calls==[]


def test_earnings_detail_kill_switch_inherited(earnings_detail_client,monkeypatch):
    client,_,calls,_=earnings_detail_client
    monkeypatch.setenv(KILL_SWITCH_ENV,"1")
    response=client.get(_earnings_detail_url())
    assert response.status_code==503
    _assert_private_headers(response);assert calls==[]


def test_earnings_detail_missing_episode_inherits_private_404(earnings_detail_client):
    client,_,calls,_=earnings_detail_client
    response=client.get(_earnings_detail_url(_D5_UNKNOWN_EPISODE_ID))
    assert response.status_code==404
    _assert_private_headers(response);assert calls==[]


def test_earnings_detail_source_contract_absence_does_not_hide_research(earnings_detail_client):
    from engine.prophet_lab.earnings_dossier import Q06_CONTRACT_PATH
    client,_,calls,root=earnings_detail_client
    (root/Q06_CONTRACT_PATH).unlink()
    response=client.get(_earnings_detail_url())
    assert response.status_code==200,response.text
    assert response.json()["comparison_state"]=="SOURCE_CONTRACT_NOT_INSTALLED"
    assert response.json()["current_observations"][0]["value_usd"]==109417000000
    assert len(calls)==1


def test_earnings_detail_corrupt_native_projection_is_private_503(earnings_detail_client,monkeypatch):
    client,_,_,_=earnings_detail_client
    monkeypatch.setattr(prophet_lab_api,"build_earnings_intelligence_vector",lambda **_: {"schema":"bad"})
    response=client.get(_earnings_detail_url())
    assert response.status_code==503
    _assert_private_headers(response)
    assert "Traceback" not in response.text


def test_existing_episode_endpoint_remains_native_vector(earnings_detail_client):
    client,_,calls,_=earnings_detail_client
    response=client.get(_episode_intelligence_url())
    assert response.status_code==200
    assert response.json()["schema"]==SCHEMA_INTELLIGENCE_VECTOR
    assert "dossier" not in response.json()
    assert len(calls)==1



def test_earnings_detail_route_is_mounted_on_existing_production_router():
    from app.main import app
    target="/api/prophet/lab/v1/episodes/{episode_id}/earnings"
    # Native include-router mounting may be deferred; exercise routing rather
    # than mistake a shallow route-list representation for a missing endpoint.
    assert target in app.openapi()["paths"]
    response=TestClient(app).get(target.replace("{episode_id}","fixture"))
    assert response.status_code==401



def test_full_native_earnings_route_preserves_b1_d5_and_source_field(monkeypatch,tmp_path):
    from tests.test_intelligence_vector_units import _q06_vector,_install_q06
    episode,master,revisions=_q06_vector(return_inputs=True)
    _install_q06(tmp_path)
    snapshot=CandidateEpisodeStoreSnapshot(generation_id=_D5_EPISODE_GENERATION,
        generation=ValidatedCandidateEpisodeGeneration(path=tmp_path/"not-serialized",
            events=({"event_type":"OPENED","episode_id":episode["episode_id"],
                     "known_at":episode["opened_at"]},),suppressions=(),episodes=(episode,),receipt={}))
    monkeypatch.setattr(prophet_lab_api,"load_candidate_episode_store_snapshot",lambda _:snapshot)
    monkeypatch.setattr(prophet_lab_api,"_load_issuer_master",lambda _:master)
    monkeypatch.setattr(prophet_lab_api,"_REPO_ROOT",tmp_path)
    monkeypatch.delenv(KILL_SWITCH_ENV,raising=False)
    reads=[]
    def exact_revision_reader(event_id):
        reads.append(event_id);return revisions
    def native_builder(**kwargs):
        return build_earnings_intelligence_vector(**kwargs,
            find_event_id=lambda _:"evt_cik0000320193_2026q3_results",
            read_revisions=exact_revision_reader)
    monkeypatch.setattr(prophet_lab_api,"build_earnings_intelligence_vector",native_builder)
    app=FastAPI();app.include_router(prophet_lab_api.router)
    app.dependency_overrides[prophet_lab_api.require_site_full_user]=lambda:{"sub":"paid-fixture"}
    response=TestClient(app).get(f"/api/prophet/lab/v1/episodes/{episode['episode_id']}/earnings")
    assert response.status_code==200,response.text
    _assert_private_headers(response)
    body=response.json()
    assert body["episode_ref"]["episode_id"]==episode["episode_id"]
    assert body["episode_ref"]["generation_id"]==_D5_EPISODE_GENERATION
    assert body["decision_cut"]["opened_at"]==episode["opened_at"]
    assert body["dossier"]["reported_changes"][0]["change_pct"]==pytest.approx(16.356501765281383)
    assert "evidence_brief" in body
    brief=body["evidence_brief"]
    assert brief["supporting_facts"][0]["code"]=="REPORTED_INCREASE"
    assert brief["supporting_facts"][0]["values"]["change_pct"]==pytest.approx(16.356501765281383)
    assert "QUALIFIED_PRE_RELEASE_EXPECTATION" in brief["not_established"]
    assert "CURRENT_MARKET_AND_PORTFOLIO_PERMISSION" in brief["not_established"]
    assert "MATCHED_PERIOD_CASH_FLOW_RECONCILIATION" in brief["not_established"]
    assert "cash_flow_reconciliations" not in body["dossier"]
    assert all(v is False for v in brief["authority"].values())
    assert reads==["evt_cik0000320193_2026q3_results"]
    assert body["is_original_as_run_recommendation"] is False


# ---------------------------------------------------------------------------
# B2-1 — correction visibility on the exact episode read
#
# Every test in this section runs against a REAL B1 store: the real producer
# (scripts/reconcile_us_candidate_episodes.reconcile), the real HEAD and
# generation bytes it publishes, and the real
# engine.us_candidate_episode.load_candidate_episode_store_snapshot reader. No
# snapshot is faked here. Only the D5 projection is ever stubbed, and only
# where a test must observe that a downstream read did or did not run.
# ---------------------------------------------------------------------------
_B1_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "us_candidate_episode" / "intake"
_B1_RECORDED_AT = "2026-11-27T18:05:00Z"
_B1_LATER_RECORDED_AT = "2026-11-28T18:05:00Z"
_B1_WITHDRAWAL_REASON = "PRIVATE-OPERATOR-REASON-MUST-NOT-LEAK"
_B1_UNKNOWN_EPISODE_ID = b1_episode_id(
    "SEC:US-XNAS-ALFA", "epoch_0",
    {
        "kind": "turn_watch_reset_low",
        "time": "2026-11-27T18:00:00Z",
        "price": "99.0000",
        "basis": "adjusted_close",
    },
    1,
)


def _b1_seed_sources(repo_root: Path) -> None:
    pd = pytest.importorskip("pandas")
    data = repo_root / "data"
    (data / "reference").mkdir(parents=True)
    pd.DataFrame(json.loads((_B1_FIXTURE_ROOT / "security_master.json").read_text())).to_parquet(
        data / "reference" / "security_master.parquet", index=False,
    )
    pd.DataFrame(json.loads((_B1_FIXTURE_ROOT / "vendor_aliases.json").read_text())).to_parquet(
        data / "reference" / "vendor_aliases.parquet", index=False,
    )
    turn = data / "us_prophet_rank" / "episode_inputs" / "turn_watch" / "2026-11-27.json"
    turn.parent.mkdir(parents=True)
    shutil.copyfile(_B1_FIXTURE_ROOT / "turn_watch.json", turn)


def _b1_store_root(repo_root: Path) -> Path:
    return repo_root / "data" / "us_prophet_rank" / "episodes"


def _b1_turn_watch_path(repo_root: Path) -> Path:
    return (
        repo_root / "data" / "us_prophet_rank" / "episode_inputs"
        / "turn_watch" / "2026-11-27.json"
    )


def _b1_rewrite_turn_watch(repo_root: Path, mutate) -> None:
    """Change the owned TURN WATCH source row and re-seal its content hash."""
    path = _b1_turn_watch_path(repo_root)
    document = json.loads(path.read_text())
    mutate(document)
    material = {key: value for key, value in document.items() if key != "content_sha256"}
    document["content_sha256"] = sha256(canonical_json(material).encode("utf-8")).hexdigest()
    path.write_text(canonical_json(document) + "\n")


def _b1_run_nightly(
    repo_root: Path, *, correction_path: Path | None = None,
    recorded_at: str = _B1_RECORDED_AT,
) -> dict:
    from scripts import reconcile_us_candidate_episodes as writer

    return writer.reconcile(
        repo_root=repo_root, nightly=True, replay=False,
        recorded_at=recorded_at, correction_path=correction_path,
    )


def _b1_snapshot(repo_root: Path) -> CandidateEpisodeStoreSnapshot:
    return load_candidate_episode_store_snapshot(_b1_store_root(repo_root))


def _b1_opened_events(repo_root: Path) -> list[dict]:
    return [
        event for event in _b1_snapshot(repo_root).generation.events
        if event["event_type"] == "OPENED"
    ]


def _b1_opened_event(repo_root: Path) -> dict:
    opened = _b1_opened_events(repo_root)
    assert len(opened) == 1
    return opened[0]


def _b1_command(
    event: dict, *, event_type: str, source_event_id: str, occurred_at: str,
    known_at: str, payload: dict, correction_of: str | None = None,
) -> dict:
    return {
        "event_type": event_type,
        "episode_id": event["episode_id"],
        "source_system": "operator_correction",
        "source_schema": "prophet.candidate_episode_correction/v1",
        "source_event_id": source_event_id,
        "occurred_at": occurred_at,
        "known_at": known_at,
        "source_receipt": "sha256:" + "9" * 64,
        "correction_of": correction_of,
        "payload": payload,
    }


def _b1_publish_correction(repo_root: Path, name: str, command: dict, *, recorded_at: str) -> dict:
    correction = repo_root / name
    correction.write_text(canonical_json(command) + "\n")
    return _b1_run_nightly(repo_root, correction_path=correction, recorded_at=recorded_at)


def _b1_withdraw_opening(repo_root: Path, event: dict, *, recorded_at: str) -> dict:
    """Append a real opening retraction and publish the next generation."""
    return _b1_publish_correction(
        repo_root, "withdrawal.jsonl",
        _b1_command(
            event, event_type="RETRACTED", source_event_id="retract-opening-1",
            occurred_at=recorded_at, known_at=recorded_at,
            payload={"reason": _B1_WITHDRAWAL_REASON},
            correction_of=event["event_id"],
        ),
        recorded_at=recorded_at,
    )


def _b1_intelligence_url(episode_id: str) -> str:
    return f"/api/prophet/lab/v1/episodes/{episode_id}/intelligence"


@pytest.fixture()
def b1_store_client(tmp_path, monkeypatch):
    """A REAL B1 store published by the real producer and served by the real route."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _b1_seed_sources(repo_root)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    _b1_run_nightly(repo_root)
    monkeypatch.setenv("PROPHET_LAB_EPISODE_STORE_ROOT", str(_b1_store_root(repo_root)))
    monkeypatch.setenv(
        "PROPHET_LAB_SECURITY_MASTER_PATH",
        str(repo_root / "data" / "reference" / "security_master.parquet"),
    )
    monkeypatch.delenv(KILL_SWITCH_ENV, raising=False)
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    app.dependency_overrides[prophet_lab_api.require_site_full_user] = lambda: {"id": "u-paid"}
    with TestClient(app) as client:
        yield client, repo_root


def test_b1_real_store_current_episode_reads_the_incumbent_d5_response(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == SCHEMA_INTELLIGENCE_VECTOR
    assert body["episode_ref"]["episode_id"] == opened["episode_id"]
    assert body["episode_ref"]["generation_id"] == _b1_snapshot(repo_root).generation_id
    assert body["decision_cut"]["known_at"] == opened["known_at"]
    _assert_private_headers(response)


def test_b1_withdrawn_opening_reads_private_410_with_owner_facts(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    generation_before = _b1_snapshot(repo_root).generation_id
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 410
    body = response.json()
    assert body["error"] == "prophet_episode_withdrawn"
    assert body["episode_id"] == opened["episode_id"]
    assert body["generation_id"] != generation_before
    assert body["generation_id"] == _b1_snapshot(repo_root).generation_id
    withdrawal = body["withdrawal"]
    assert withdrawal["event_id"].startswith("pee:")
    assert withdrawal["correction_of"] == opened["event_id"]
    assert withdrawal["known_at"] == _B1_LATER_RECORDED_AT
    _assert_private_headers(response)


def test_b1_withdrawn_opening_leaves_the_old_generation_bytes_untouched(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    old_generation = _b1_snapshot(repo_root).generation.path
    before = {
        str(path.relative_to(old_generation)): path.read_bytes()
        for path in sorted(old_generation.rglob("*")) if path.is_file()
    }
    old_projection = json.loads((old_generation / "all_candidates.json").read_text())

    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    after = {
        str(path.relative_to(old_generation)): path.read_bytes()
        for path in sorted(old_generation.rglob("*")) if path.is_file()
    }
    assert after == before
    assert [row["episode_id"] for row in old_projection["episodes"]] == [opened["episode_id"]]
    assert _b1_snapshot(repo_root).generation.episodes == ()


def test_b1_unknown_identity_stays_private_404_after_a_withdrawal(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    response = client.get(_b1_intelligence_url(_B1_UNKNOWN_EPISODE_ID))
    assert response.status_code == 404
    assert response.json() == {"error": "prophet_episode_not_found"}
    _assert_private_headers(response)


def test_b1_observation_retraction_does_not_withdraw_the_episode(b1_store_client):
    """A retracted OBSERVED event is not an opening withdrawal — the episode stays."""
    client, repo_root = b1_store_client
    _b1_rewrite_turn_watch(
        repo_root, lambda document: document["rows"][0].__setitem__("observation_revision", 2),
    )
    _b1_run_nightly(repo_root, recorded_at=_B1_LATER_RECORDED_AT)
    observed = [
        event for event in _b1_snapshot(repo_root).generation.events
        if event["event_type"] == "OBSERVED"
    ]
    assert len(observed) == 1

    _b1_publish_correction(
        repo_root, "observation-withdrawal.jsonl",
        _b1_command(
            observed[0], event_type="RETRACTED", source_event_id="retract-observed-1",
            occurred_at="2026-11-28T19:00:00Z", known_at="2026-11-28T19:00:00Z",
            payload={"reason": _B1_WITHDRAWAL_REASON},
            correction_of=observed[0]["event_id"],
        ),
        recorded_at="2026-11-28T20:00:00Z",
    )

    opened = _b1_opened_event(repo_root)
    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 200, response.text
    assert response.json()["schema"] == SCHEMA_INTELLIGENCE_VECTOR


def test_b1_withdrawal_does_not_ban_another_episode_of_the_same_security(b1_store_client):
    """The withdrawal is scoped to one exact episode identity, never to a ticker."""
    client, repo_root = b1_store_client
    first = _b1_opened_event(repo_root)

    _b1_publish_correction(
        repo_root, "state-correction.jsonl",
        _b1_command(
            first, event_type="STATE_TRANSITIONED", source_event_id="state-resolved-1",
            occurred_at="2026-11-27T19:00:00Z", known_at="2026-11-27T19:00:00Z",
            payload={"episode_state": "RESOLVED", "terminal_reason": "operator-resolved"},
        ),
        recorded_at="2026-11-27T20:00:00Z",
    )
    _b1_rewrite_turn_watch(
        repo_root, lambda document: document["rows"][0]["reset"].__setitem__("reset_low", 43.2),
    )
    _b1_run_nightly(repo_root, recorded_at=_B1_LATER_RECORDED_AT)
    opened = _b1_opened_events(repo_root)
    assert len(opened) == 2
    second = [event for event in opened if event["episode_id"] != first["episode_id"]][0]
    assert second["episode_id"].startswith("pe:SEC:US-XNAS-ALFA:")

    _b1_publish_correction(
        repo_root, "second-withdrawal.jsonl",
        _b1_command(
            second, event_type="RETRACTED", source_event_id="retract-opening-2",
            occurred_at="2026-11-28T19:00:00Z", known_at="2026-11-28T19:00:00Z",
            payload={"reason": _B1_WITHDRAWAL_REASON},
            correction_of=second["event_id"],
        ),
        recorded_at="2026-11-28T20:00:00Z",
    )

    withdrawn = client.get(_b1_intelligence_url(second["episode_id"]))
    assert withdrawn.status_code == 410
    assert withdrawn.json()["error"] == "prophet_episode_withdrawn"
    sibling = client.get(_b1_intelligence_url(first["episode_id"]))
    assert sibling.status_code == 200, sibling.text
    assert sibling.json()["episode_ref"]["episode_id"] == first["episode_id"]


def test_b1_withdrawal_loads_no_identity_and_no_earnings_source(b1_store_client, monkeypatch):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)
    calls: list[str] = []

    def _forbidden_identity(_path):
        calls.append("identity")
        raise AssertionError("issuer identity must not be read after a withdrawal")

    def _forbidden_earnings(**_kwargs):
        calls.append("earnings")
        raise AssertionError("D5 must not be built after a withdrawal")

    monkeypatch.setattr(prophet_lab_api, "_load_issuer_master", _forbidden_identity)
    monkeypatch.setattr(prophet_lab_api, "build_earnings_intelligence_vector", _forbidden_earnings)

    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 410
    assert calls == []


def test_b1_earnings_route_inherits_the_withdrawal_410(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    response = client.get(f"/api/prophet/lab/v1/episodes/{opened['episode_id']}/earnings")
    assert response.status_code == 410
    assert response.json()["error"] == "prophet_episode_withdrawn"
    _assert_private_headers(response)


def test_b1_withdrawal_response_carries_only_the_allowlisted_owner_facts(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 410
    body = response.json()
    assert set(body) == {"error", "detail", "episode_id", "generation_id", "withdrawal"}
    assert set(body["withdrawal"]) == {"event_id", "correction_of", "known_at"}
    serialized = json.dumps(body, sort_keys=True)
    assert _B1_WITHDRAWAL_REASON not in serialized
    assert "reason" not in body["withdrawal"]
    assert "ISS:US-XNAS-ALFA" not in serialized
    assert str(repo_root) not in serialized
    assert "/data/" not in serialized


def test_b1_read_loads_exactly_one_validated_snapshot_per_request(b1_store_client, monkeypatch):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    calls: list[object] = []
    real_loader = prophet_lab_api.load_candidate_episode_store_snapshot

    def _counting(root):
        calls.append(root)
        return real_loader(root)

    monkeypatch.setattr(prophet_lab_api, "load_candidate_episode_store_snapshot", _counting)

    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 200, response.text
    assert len(calls) == 1


def test_b1_anonymous_caller_is_blocked_before_the_withdrawal_is_disclosed(
    b1_store_client, monkeypatch,
):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)
    import app.main as main_mod

    monkeypatch.setattr(
        main_mod,
        "require_user",
        lambda _authorization: (_ for _ in ()).throw(HTTPException(401, "missing bearer token")),
    )
    app = FastAPI()
    app.include_router(prophet_lab_api.router)
    with TestClient(app) as anonymous:
        response = anonymous.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 401
    assert "prophet_episode_withdrawn" not in response.text
    _assert_private_headers(response)


def test_b1_corrupt_generation_is_private_503_after_a_withdrawal(b1_store_client):
    client, repo_root = b1_store_client
    opened = _b1_opened_event(repo_root)
    _b1_withdraw_opening(repo_root, opened, recorded_at=_B1_LATER_RECORDED_AT)

    generation = _b1_snapshot(repo_root).generation.path
    projection = generation / "all_candidates.json"
    projection.write_bytes(projection.read_bytes() + b"\x00")

    response = client.get(_b1_intelligence_url(opened["episode_id"]))
    assert response.status_code == 503
    assert response.json() == {
        "error": "prophet_episode_intelligence_unavailable",
        "detail": "Episode intelligence temporarily unavailable",
    }
    _assert_private_headers(response)
