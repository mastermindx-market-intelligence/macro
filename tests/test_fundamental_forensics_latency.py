"""FIF V0-a: measured per-route latency, declared SLO budgets, entitled report.

Unit contracts for the bounded recorder (nearest-rank percentiles, window
eviction, the 65-template overflow bucket), the declared SLO config loader
and evaluator, and the HTTP surface: every forensics response carries
``Server-Timing``, recording never changes a status or body, and the SLO
report sits behind the same entitlement as health and never reports an
unreadable config as within.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.latency import (
    RECORDER,
    LatencyRecorder,
    evaluate_slo,
    load_slo_config,
)

ROOT = Path(__file__).resolve().parents[1]
_SLO_CONFIG_PATH = ROOT / "config" / "fundamental_forensics" / "slo.v1.json"
_HEALTH_PATH = "/api/forensics/health"
_SLO_PATH = "/api/forensics/slo"


@pytest.fixture(autouse=True)
def _clean_recorder():
    """The module-level recorder is shared process state; keep tests isolated."""
    RECORDER.reset()
    yield
    RECORDER.reset()


# ---------------------------------------------------------------------------
# (a) Nearest-rank percentiles
# ---------------------------------------------------------------------------


def test_a_nearest_rank_percentiles_on_one_to_hundred() -> None:
    recorder = LatencyRecorder(window=128)
    for value in range(1, 101):
        recorder.record("/t", float(value), 200)
    summary = recorder.snapshot()["/t"]
    assert summary["count_total"] == 100
    assert summary["window_n"] == 100
    assert summary["error_n"] == 0
    assert summary["p50_ms"] == 50.0
    assert summary["p95_ms"] == 95.0
    assert summary["p99_ms"] == 99.0
    assert summary["max_ms"] == 100.0


def test_a_values_round_to_a_tenth_of_a_millisecond() -> None:
    recorder = LatencyRecorder(window=8)
    recorder.record("/t", 1.234567, 200)
    assert recorder.snapshot()["/t"]["p99_ms"] == 1.2


# ---------------------------------------------------------------------------
# (b) Window eviction and the monotonic total
# ---------------------------------------------------------------------------


def test_b_window_evicts_oldest_while_count_total_keeps_counting() -> None:
    recorder = LatencyRecorder(window=4)
    for value in range(1, 7):  # 1..6 ms; the window keeps 3,4,5,6
        recorder.record("/t", float(value), 200)
    summary = recorder.snapshot()["/t"]
    assert summary["window_n"] == 4
    assert summary["count_total"] == 6
    assert summary["max_ms"] == 6.0
    assert summary["p50_ms"] == 4.0  # nearest rank of [3,4,5,6]
    assert summary["p99_ms"] == 6.0
    recorder.reset()
    assert recorder.snapshot() == {}


def test_b_error_n_counts_only_5xx_in_the_window() -> None:
    recorder = LatencyRecorder(window=8)
    for status in (200, 429, 500, 503):
        recorder.record("/t", 1.0, status)
    assert recorder.snapshot()["/t"]["error_n"] == 2


# ---------------------------------------------------------------------------
# (c) The 65-template overflow bucket
# ---------------------------------------------------------------------------


def test_c_sixty_fifth_template_lands_in_the_overflow_bucket() -> None:
    recorder = LatencyRecorder(window=8)
    for index in range(64):
        recorder.record(f"/route-{index:02d}", 1.0, 200)
    for extra in ("/route-64", "/route-65"):
        recorder.record(extra, 2.0, 200)
    snapshot = recorder.snapshot()
    assert len(snapshot) == 65
    assert "__overflow__" in snapshot
    assert "/route-64" not in snapshot
    assert "/route-65" not in snapshot
    assert snapshot["__overflow__"]["window_n"] == 2
    assert snapshot["__overflow__"]["count_total"] == 2
    assert snapshot["/route-63"]["window_n"] == 1


# ---------------------------------------------------------------------------
# (d) evaluate_slo states and the unbudgeted list
# ---------------------------------------------------------------------------

_EVAL_CONFIG = {
    "schema_version": "fif_slo.v1",
    "status": "proposed",
    "window": 512,
    "min_samples": 50,
    "routes": {
        "/ok": {"p95_ms": 100, "p99_ms": 200},
        "/slow-p95": {"p95_ms": 100, "p99_ms": 200},
        "/slow-p99": {"p95_ms": 100, "p99_ms": 200},
        "/quiet": {"p95_ms": 100, "p99_ms": 200},
        "/sparse": {"p95_ms": 100, "p99_ms": 200},
    },
}


def _measured(window_n: int, p95: float, p99: float) -> dict:
    return {
        "count_total": window_n,
        "window_n": window_n,
        "p50_ms": p95 / 2,
        "p95_ms": p95,
        "p99_ms": p99,
        "max_ms": p99,
        "error_n": 0,
    }


_EVAL_SNAPSHOT = {
    "/ok": _measured(60, 40.0, 80.0),
    "/slow-p95": _measured(60, 120.0, 180.0),
    "/slow-p99": _measured(60, 90.0, 250.0),
    "/sparse": _measured(10, 40.0, 80.0),
    "/extra": _measured(5, 2.0, 3.0),
}


def test_d_evaluate_slo_each_state_and_the_unbudgeted_list() -> None:
    report = evaluate_slo(_EVAL_SNAPSHOT, _EVAL_CONFIG)
    routes = report["routes"]
    assert set(routes) == set(_EVAL_CONFIG["routes"])
    assert routes["/ok"]["state"] == "within"
    assert routes["/slow-p95"]["state"] == "breach"
    assert routes["/slow-p99"]["state"] == "breach"
    assert routes["/quiet"]["state"] == "insufficient_samples"
    assert routes["/quiet"]["p95_ms"] is None
    assert routes["/quiet"]["p99_ms"] is None
    assert routes["/sparse"]["state"] == "insufficient_samples"
    assert routes["/ok"]["budget_p95_ms"] == 100
    assert routes["/ok"]["budget_p99_ms"] == 200
    assert routes["/ok"]["window_n"] == 60
    assert routes["/ok"]["p95_ms"] == 40.0
    # A measured template without a budget is named, never silently dropped.
    assert report["unbudgeted"] == ["/extra"]


# ---------------------------------------------------------------------------
# (e) Config loader: the three malformed shapes, the shipped file, the router
# ---------------------------------------------------------------------------


_VALID_CONFIG = {
    "schema_version": "fif_slo.v1",
    "status": "proposed",
    "window": 512,
    "min_samples": 50,
    "routes": {"/api/forensics/health": {"p95_ms": 300, "p99_ms": 600}},
}


def _write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "slo.v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_e_load_slo_config_refuses_wrong_schema_version(tmp_path) -> None:
    bad = dict(_VALID_CONFIG, schema_version="fif_slo.v2")
    with pytest.raises(ValueError):
        load_slo_config(_write_config(tmp_path, bad))


@pytest.mark.parametrize("budget", [0, -1, "800", None])
def test_e_load_slo_config_refuses_non_positive_budgets(tmp_path, budget) -> None:
    routes = {"/api/forensics/health": {"p95_ms": budget, "p99_ms": 600}}
    bad = dict(_VALID_CONFIG, routes=routes)
    with pytest.raises(ValueError):
        load_slo_config(_write_config(tmp_path, bad))


def test_e_load_slo_config_refuses_p95_above_p99(tmp_path) -> None:
    routes = {"/api/forensics/health": {"p95_ms": 700, "p99_ms": 600}}
    bad = dict(_VALID_CONFIG, routes=routes)
    with pytest.raises(ValueError):
        load_slo_config(_write_config(tmp_path, bad))


def test_e_shipped_config_loads_and_every_template_exists_on_the_router() -> None:
    config = load_slo_config(_SLO_CONFIG_PATH)
    assert config["schema_version"] == "fif_slo.v1"
    assert config["status"] == "proposed"
    assert config["window"] == 512
    assert config["min_samples"] == 50
    assert len(config["routes"]) == 10
    paths = {getattr(route, "path", None) for route in forensics_api.router.routes}
    missing = sorted(set(config["routes"]) - paths)
    assert missing == [], f"SLO config names templates absent from the router: {missing}"


# ---------------------------------------------------------------------------
# (f)/(g): HTTP surface over the mounted router
# ---------------------------------------------------------------------------


@pytest.fixture()
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    app = FastAPI()
    app.include_router(forensics_api.router)
    return app


@pytest.fixture()
def paid_client(router_app, monkeypatch) -> TestClient:
    monkeypatch.setattr(forensics_api, "_SLO_CONFIG_CACHE", None)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        yield client


def test_f_health_carries_server_timing_and_records_its_template(
    paid_client,
) -> None:
    response = paid_client.get(_HEALTH_PATH)
    assert response.status_code == 200, response.text
    header = response.headers.get("Server-Timing", "")
    assert header.startswith("fif;dur="), header
    float(header.split("=", 1)[1])  # the duration parses as a number
    summary = RECORDER.snapshot().get("/api/forensics/health")
    assert summary is not None
    assert summary["window_n"] == 1
    assert summary["count_total"] == 1


def test_f_recorder_failure_never_changes_status_or_body(
    paid_client, monkeypatch
) -> None:
    baseline = paid_client.get(_HEALTH_PATH)
    assert baseline.status_code == 200

    def _refuses(*_args, **_kwargs):
        raise RuntimeError("recorder refused")

    monkeypatch.setattr(RECORDER, "record", _refuses)
    degraded = paid_client.get(_HEALTH_PATH)
    assert degraded.status_code == baseline.status_code
    assert degraded.content == baseline.content
    # The header is set before recording, so even a failing recorder leaves it.
    assert degraded.headers.get("Server-Timing", "").startswith("fif;dur=")


def test_g_slo_route_returns_the_report_with_the_entitlement_override(
    paid_client,
) -> None:
    response = paid_client.get(_SLO_PATH)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    report = response.json()
    assert report["schema"] == "fif_slo_report.v1"
    assert report["config_status"] == "proposed"
    assert report["window"] == 512
    configured = json.loads(_SLO_CONFIG_PATH.read_text(encoding="utf-8"))["routes"]
    assert set(report["routes"]) == set(configured)
    for row in report["routes"].values():
        assert row["state"] in ("within", "breach", "insufficient_samples")
        assert {"p95_ms", "p99_ms", "budget_p95_ms", "budget_p99_ms", "window_n"} <= set(row)
    assert isinstance(report["unbudgeted"], list)
    # This fresh process has served health above but nothing else: the health
    # row is evaluated, and nothing is silently dropped.
    assert "/api/forensics/health" in report["routes"]


def test_g_slo_route_refuses_anonymous_exactly_like_health(router_app) -> None:
    with TestClient(router_app, raise_server_exceptions=False) as client:
        health = client.get(_HEALTH_PATH)
        slo = client.get(_SLO_PATH)
    assert health.status_code in (401, 403)
    assert slo.status_code == health.status_code


def test_g_slo_route_refuses_free_user_exactly_like_health(
    router_app, monkeypatch
) -> None:
    from fastapi import HTTPException

    import app.main as app_main
    import app.paywall as paywall_mod

    monkeypatch.setattr(
        app_main, "require_user", lambda auth: {"id": "free-user", "tier": "free"}
    )
    monkeypatch.setattr(
        paywall_mod,
        "enforce_site_full",
        lambda user, always=False: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="site_full required")
        ),
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        health = client.get(_HEALTH_PATH)
        slo = client.get(_SLO_PATH)
    assert health.status_code == 403
    assert slo.status_code == 403


def test_g_slo_route_returns_503_when_the_config_is_unreadable(
    router_app, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(forensics_api, "REPO", tmp_path)
    monkeypatch.setattr(forensics_api, "_SLO_CONFIG_CACHE", None)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.get(_SLO_PATH)
    assert response.status_code == 503
    assert response.json() == {"error": "slo_config_unavailable"}
    assert response.headers["cache-control"] == "no-store"


def test_g_slo_route_returns_503_when_the_config_is_malformed(
    router_app, monkeypatch, tmp_path
) -> None:
    config_dir = tmp_path / "config" / "fundamental_forensics"
    config_dir.mkdir(parents=True)
    (config_dir / "slo.v1.json").write_text(json.dumps({"schema_version": "nope"}), encoding="utf-8")
    monkeypatch.setattr(forensics_api, "REPO", tmp_path)
    monkeypatch.setattr(forensics_api, "_SLO_CONFIG_CACHE", None)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.get(_SLO_PATH)
    assert response.status_code == 503
    assert response.json() == {"error": "slo_config_unavailable"}
