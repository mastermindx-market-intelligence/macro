"""FIF V0-a: measured per-route latency, declared SLO budgets, entitled report.

Unit contracts for the bounded recorder (nearest-rank percentiles, window
eviction, the 65-template overflow bucket), the declared SLO config loader
and evaluator, and the HTTP surface: every forensics SUCCESS response
carries ``Server-Timing`` (the contract is success responses only — error
responses carry none), only 2xx/3xx responses enter the percentile window,
recording never changes a status or body, and the SLO report sits behind the
same entitlement as health and never reports an unreadable config as within.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def test_b_error_counts_live_outside_the_percentile_window() -> None:
    """4xx raises ``client_error_n``, 5xx raises ``error_n``; neither lands
    in the window — only the 200 sample does."""
    recorder = LatencyRecorder(window=8)
    for status in (200, 429, 500, 503):
        recorder.record("/t", 1.0, status)
    summary = recorder.snapshot()["/t"]
    assert summary["error_n"] == 2
    assert summary["client_error_n"] == 1
    assert summary["window_n"] == 1
    assert summary["count_total"] == 4


def test_b_client_and_server_errors_stay_outside_the_percentile_window() -> None:
    """MAJOR-1: a burst of fast rejections must never drag p95 down."""
    recorder = LatencyRecorder(window=16)
    for value in range(1, 11):
        recorder.record("/t", float(value), 200)
    before = recorder.snapshot()["/t"]
    for _ in range(25):
        recorder.record("/t", 0.1, 401)
    recorder.record("/t", 0.1, 500)
    after = recorder.snapshot()["/t"]
    assert after["window_n"] == before["window_n"] == 10
    assert after["p95_ms"] == before["p95_ms"] == 10.0
    assert after["client_error_n"] == 25
    assert after["error_n"] == 1
    assert after["count_total"] == 36


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
        "client_error_n": 0,
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
    # Compare the recorder's effect at the same evaluation instant. Otherwise
    # crossing a second changes evaluated_at independently of recorder failure.
    evaluation_time = forensics_api.datetime.now(forensics_api.timezone.utc)
    evaluate_health = forensics_api.evaluate_health

    def _same_instant(root, **kwargs):
        return evaluate_health(root, **{**kwargs, "now": evaluation_time})

    monkeypatch.setattr(forensics_api, "evaluate_health", _same_instant)
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


def test_f_client_error_burst_never_pollutes_the_percentile_window(
    router_app,
) -> None:
    """MAJOR-1: anonymous rejections are counted, never windowed (HTTP path)."""
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for _ in range(5):
            response = client.get(_HEALTH_PATH)
            assert response.status_code in (401, 403)
        # MINOR-1: the Server-Timing contract is success responses only.
        assert "Server-Timing" not in response.headers
    summary = RECORDER.snapshot()["/api/forensics/health"]
    assert summary["window_n"] == 0
    assert summary["p95_ms"] is None
    assert summary["client_error_n"] == 5
    assert summary["error_n"] == 0


def test_f_method_not_allowed_handlers_are_not_recorded(paid_client) -> None:
    """MAJOR-1: a private 405 never reaches handler work, so nothing is
    recorded on the real route template."""
    response = paid_client.get("/api/forensics/v1/financial/query")
    assert response.status_code == 405
    assert "/api/forensics/v1/financial/query" not in RECORDER.snapshot()


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


def test_g_slo_route_sends_the_full_private_header_set(paid_client) -> None:
    """MINOR-3: ``{**_PRIVATE_HEADERS, "Cache-Control": "no-store"}``."""
    response = paid_client.get(_SLO_PATH)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def test_g_slo_route_reports_the_recorders_actual_window(
    router_app, monkeypatch
) -> None:
    """MINOR-4: the reported window is the recorder's, not the config's."""
    monkeypatch.setattr(forensics_api, "RECORDER", LatencyRecorder(window=7))
    monkeypatch.setattr(forensics_api, "_SLO_CONFIG_CACHE", None)
    router_app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "paid-user"
    }
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = client.get(_SLO_PATH)
    assert response.status_code == 200, response.text
    assert response.json()["window"] == 7


# ---------------------------------------------------------------------------
# (h) The offline benchmark: status accounting and budget exclusion
# ---------------------------------------------------------------------------


def test_h_benchmark_counts_statuses_fails_on_a_500_and_excludes_it_from_the_budget(
    monkeypatch, tmp_path
) -> None:
    """MAJOR-2: statuses are counted per route, an unexpected status makes the
    run exit nonzero, and the failed response contributes no budget sample."""
    import scripts.fif_latency_benchmark as bench
    from engine.fundamental_forensics import production_datasets as datasets

    class _Response:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    class _StubClient:
        """Stands in for TestClient plus the driven app: returns canned
        statuses and records every response into the in-process recorder
        exactly the way the timed route would."""

        def __init__(self, app: Any, **_kwargs: Any) -> None:
            self._app = app

        def __enter__(self) -> "_StubClient":
            return self

        def __exit__(self, *_exc: Any) -> None:
            return None

        def get(self, path: str) -> _Response:
            return self._serve(path, 200)

        def post(
            self,
            path: str,
            content: bytes | None = None,
            headers: dict | None = None,
        ) -> _Response:
            status = 500 if path == "/api/forensics/v1/financial/revisions" else 200
            return self._serve(path, status)

        def _serve(self, path: str, status_code: int) -> _Response:
            # A failing handler would have burned wall-clock too; the huge
            # duration proves the sample never reaches the budget.
            duration = 99999.0 if status_code >= 400 else 5.0
            RECORDER.record(path, duration, status_code)
            return _Response(status_code)

    class _Generation:
        def statement_accessions(self) -> list[str]:
            return ["synthetic-accession"]

    monkeypatch.setattr("fastapi.testclient.TestClient", _StubClient)
    monkeypatch.setattr(datasets, "build_production_dataset_store", lambda _dir: object())
    monkeypatch.setattr(
        datasets,
        "latest_generation_summary",
        lambda _store, _issuer: {
            "dataset_generation_id": "synthetic-generation",
            "admitted_at": "2026-01-01T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        datasets, "load_generation", lambda _store, _issuer, _gid: _Generation()
    )
    # main() exports its production-mode env; restore the ambient one after.
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    monkeypatch.delenv("FIF_PRODUCTION_DATASET_LOCAL_STORE", raising=False)

    out = tmp_path / "bench-report.json"
    rc = bench.main(
        [
            "--local-store", str(tmp_path),
            "--issuer", "ISS:US-XNAS-TEST",
            "--iterations", "1",
            "--out", str(out),
        ]
    )
    assert rc == 3
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status_counts"]["/api/forensics/v1/financial/revisions"] == {"500": 1}
    assert report["status_counts"]["/api/forensics/health"] == {"200": 1}
    # The failed response never entered the latency budget: its route holds no
    # window sample, while the success routes do.
    routes = report["evaluation"]["routes"]
    assert routes["/api/forensics/v1/financial/revisions"]["window_n"] == 0
    assert routes["/api/forensics/v1/financial/revisions"]["p95_ms"] is None
    assert routes["/api/forensics/health"]["window_n"] == 1
    assert report["snapshot"]["/api/forensics/v1/financial/revisions"]["error_n"] == 1
