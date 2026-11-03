"""Focused offline tests for the bounded portfolio forward-evaluation contract."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


SHA_A = "a" * 40
SHA_B = "b" * 40


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


@pytest.fixture()
def isolated_root(tmp_path: Path, monkeypatch) -> Path:
    from portfolio import forward_evaluation, registry

    monkeypatch.setattr(registry, "_ROOT", tmp_path)
    monkeypatch.setattr(forward_evaluation, "_utc_today", lambda: "2026-08-13")
    return tmp_path


def _activate_start() -> None:
    from portfolio import forward_evaluation

    forward_evaluation.initialize_start(SHA_A, "2026-08-11")
    forward_evaluation.finalize_start(SHA_A)


def _seed_legacy(book_dir: Path) -> None:
    _write_json(book_dir / "account.json", {
        "starting_nav": 1_000_000.0,
        "cash": 400_000.0,
        # Deliberately no current_price: concentration must prefer latest.json weights.
        "positions": {
            "AAPL": {"shares": 4_000.0, "avg_cost": 100.0},
            "MSFT": {"shares": 500.0, "avg_cost": 400.0},
        },
    })
    _write_json(book_dir / "latest.json", {
        "as_of": "2026-08-11",
        "gross": 0.60,
        "cash": 0.40,
        "positions": [
            {"ticker": "AAPL", "weight": 0.40},
            {"ticker": "MSFT", "weight": 0.20},
        ],
    })
    _write_jsonl(book_dir / "decisions.jsonl", [{
        "asof": "2026-08-11", "target_status": "executed", "decision_effective": True,
        "effective_holdings": [{"ticker": "AAPL", "action_effective": "hold"}],
    }])
    _write_jsonl(book_dir / "fills.jsonl", [{
        "date": "2026-08-11", "ticker": "AAPL", "side": "buy",
        "shares": 100.0, "price": 100.0, "value": 10_000.0,
    }])
    _write_jsonl(book_dir / "nav_history.jsonl", [{
        "date": "2026-08-11", "nav": 1_000_000.0, "cash": 400_000.0,
        "invested": 600_000.0, "spy_nav": 1_000_000.0, "benchmark": "SPY",
    }])
    _write_json(book_dir / "positions_ledger.json", {})


def _seed_forward(root: Path, book_dir: Path) -> None:
    _write_json(book_dir / "latest.json", {
        "as_of": "2026-08-13", "gross": 0.80, "cash": 0.20,
        "positions": [
            {"ticker": "AAPL", "weight": 0.50},
            {"ticker": "MSFT", "weight": 0.20},
            {"ticker": "GOOG", "weight": 0.10},
        ],
    })
    legacy_decision = json.loads((book_dir / "decisions.jsonl").read_text().splitlines()[0])
    decisions = [legacy_decision, {
        "asof": "2026-08-12",
        "target_status": "executed",
        "decision_effective": True,
        "effective_holdings": [{
            "ticker": "GOOG", "weight": 0.10, "action_effective": "add",
            "evidence": ["prophet:index:2026-08-12"],
            "source_provenance": ["prophet:index:2026-08-12"],
            "why_now": "Confirmed turn", "falsifier": "RS breaks",
            "expected_horizon": "21 sessions", "exit_plan": "Exit on falsifier",
        }],
        "requested_exit_decisions": [{"ticker": "AAPL", "reason": "rotate"}],
        "exit_decisions": [{
            "ticker": "AAPL", "reason": "rotate", "why_now": "leadership changed",
            "evidence": ["relative strength"],
        }],
        "submission_audit": {
            "blocked_exits": [{"ticker": "MSFT", "reason": "hysteresis"}],
            "carried": [{"ticker": "MSFT", "reason": "missing_explicit_exit_decision"}],
            "rejected": [],
        },
        "decision_memo": {
            "candidate_funnel": {
                "candidates": ["GOOG", "AMZN", "META"],
                "finalists": ["GOOG", "AMZN"],
            },
            "selected": [{
                "ticker": "GOOG", "source_provenance": ["prophet:index:2026-08-12"],
            }],
            "rejected": [
                {"ticker": "AMZN", "reason": "weaker confirmation", "sources": ["intake"]},
                {"ticker": "META", "reason": None, "sources": ["prophet"]},
            ],
        },
        "executed": [{"ticker": "GOOG", "side": "buy"}],
    }, {
        "asof": "2026-08-13",
        "target_status": "executed",
        "decision_effective": True,
        "effective_holdings": [{"ticker": "GOOG", "action_effective": "hold"}],
        "decision_memo": {
            "candidate_funnel": {"candidates": ["GOOG"], "finalists": ["GOOG"]},
            "selected": [{"ticker": "GOOG", "source_provenance": ["intake"]}],
            "rejected": [],
        },
    }]
    # Reorder the legacy row during compaction: content IDs, not line positions, own the boundary.
    _write_jsonl(book_dir / "decisions.jsonl", [decisions[1], decisions[0], decisions[2]])

    legacy_fill = json.loads((book_dir / "fills.jsonl").read_text().splitlines()[0])
    _write_jsonl(book_dir / "fills.jsonl", [
        {"date": "2026-08-12", "ticker": "GOOG", "side": "buy",
         "shares": 50.0, "price": 100.0, "value": 5_000.0},
        legacy_fill,
        {"date": "2026-08-13", "ticker": "AAPL", "side": "sell",
         "shares": 100.0, "price": 110.0, "value": 11_000.0},
    ])
    _write_jsonl(book_dir / "nav_history.jsonl", [
        {"date": "2026-08-11", "nav": 1_000_000.0, "cash": 400_000.0,
         "invested": 600_000.0, "spy_nav": 1_000_000.0, "benchmark": "SPY"},
        {"date": "2026-08-12", "nav": 1_010_000.0, "cash": 300_000.0,
         "invested": 710_000.0, "spy_nav": 1_005_000.0, "benchmark": "SPY"},
        {"date": "2026-08-13", "nav": 1_020_000.0, "cash": 204_000.0,
         "invested": 816_000.0, "spy_nav": 1_006_000.0, "benchmark": "SPY"},
    ])
    _write_json(book_dir / "positions_ledger.json", {
        "brain:GOOG": {
            "ticker": "GOOG", "sleeve": "brain", "still_open": False,
            "history": [
                {"event": "open", "as_of": "2026-08-12"},
                {"event": "close", "as_of": "2026-08-13"},
            ],
        },
    })
    _write_json(root / "data" / "portfolio_learning" / "autonomous" / "post_sell.json", {
        "schema": "portfolio.post_sell.v1", "book": "autonomous", "asof": "2026-08-13",
        "exits": [
            {"exit_id": "autonomous:2026-08-13:AAPL:2", "exit_date": "2026-08-13",
             "sale_kind": "full_exit", "decision": {
                 "reason": "rotate", "why_now": "leadership changed", "evidence": ["RS"],
             }},
            {"exit_id": "autonomous:2026-08-13:MSFT:3", "exit_date": "2026-08-13",
             "sale_kind": "partial_trim"},
        ],
    })


def test_not_started_and_archived_are_strict_no_write(isolated_root: Path) -> None:
    from portfolio import forward_evaluation

    active = forward_evaluation.evaluate("autonomous", "2026-08-11")
    assert active["status"] == "not_started"
    assert active["sample_counts"] == forward_evaluation._zero_sample_counts()
    assert not forward_evaluation._output_root().exists()

    archived = forward_evaluation.evaluate("flagship", "2026-08-11")
    assert archived["status"] == "archived"
    assert archived["write_permitted"] is False
    assert not forward_evaluation._output_root().exists()


@pytest.mark.parametrize("book", ["../autonomous", "autonomous/../../escape", "/tmp/escape"])
def test_book_paths_reject_request_controlled_segments(isolated_root: Path, book: str) -> None:
    from portfolio import forward_evaluation

    for resolver in (
        forward_evaluation._book_output_dir,
        forward_evaluation._post_sell_path,
        forward_evaluation._portfolio_data_dir,
    ):
        with pytest.raises(ValueError, match="unknown portfolio book"):
            resolver(book)
    assert not (isolated_root / "escape").exists()


def test_start_is_create_once_and_corrupt_existing_marker_freezes(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _seed_legacy(registry.data_dir("autonomous"))
    first = forward_evaluation.initialize_start(SHA_A, "2026-08-11")
    path = forward_evaluation._start_path()
    before = path.read_bytes()
    assert first["initialized"] is True
    assert first["release_state"] == "pending_health"
    assert first["books"]["autonomous"]["row_counts"]["decisions"] == 1
    assert first["books"]["autonomous"]["row_hashes"]["decisions"]

    pending = forward_evaluation.evaluate("autonomous", "2026-08-11")
    assert pending["status"] == "not_started"
    assert pending["missing_reason"] == "exact_v2_deployment_health_not_verified"
    assert not forward_evaluation._book_output_dir("autonomous").exists()

    second = forward_evaluation.initialize_start(SHA_A, "2026-08-12")
    assert second["initialized"] is False
    assert second["preserved_existing_start"] is True
    assert second["deployment_sha"] == SHA_A
    assert path.read_bytes() == before

    with pytest.raises(RuntimeError, match="different deployment"):
        forward_evaluation.initialize_start(SHA_B, "2026-08-12")
    finalized = forward_evaluation.finalize_start(SHA_A)
    assert finalized["release_state"] == "active"
    active_bytes = path.read_bytes()
    preserved = forward_evaluation.initialize_start(SHA_B, "2026-08-12")
    assert preserved["deployment_sha"] == SHA_A
    assert path.read_bytes() == active_bytes

    path.write_text("{broken", encoding="utf-8")
    broken = path.read_bytes()
    with pytest.raises(RuntimeError, match="invalid; refusing reset"):
        forward_evaluation.initialize_start(SHA_B, "2026-08-12")
    assert path.read_bytes() == broken


def test_release_cli_override_targets_canonical_live_data_only(
    isolated_root: Path, monkeypatch, capsys,
) -> None:
    from portfolio import forward_evaluation, registry

    canonical = isolated_root / "canonical-live-data"
    _write_jsonl(canonical / "portfolios" / "autonomous" / "decisions.jsonl", [{
        "decision_id": "canonical", "asof": "2026-08-11",
    }])
    _write_jsonl(registry.data_dir("autonomous") / "decisions.jsonl", [
        {"decision_id": "decoy-1", "asof": "2026-08-11"},
        {"decision_id": "decoy-2", "asof": "2026-08-11"},
    ])
    monkeypatch.setenv(forward_evaluation._RELEASE_STATE_ROOT_ENV, str(canonical))

    assert forward_evaluation._cli([
        "init", "--deployment-sha", SHA_A, "--asof", "2026-08-11",
    ]) == 0
    init_payload = json.loads(capsys.readouterr().out)
    marker = canonical / "portfolio_forward_evaluation" / "start.json"
    assert marker.exists()
    assert init_payload["books"]["autonomous"]["row_counts"]["decisions"] == 1
    assert not (isolated_root / "data" / "portfolio_forward_evaluation" / "start.json").exists()
    assert forward_evaluation.load_start() is None  # context reset; normal API sees only decoy data

    assert forward_evaluation._cli(["finalize", "--deployment-sha", SHA_A]) == 0
    capsys.readouterr()
    assert forward_evaluation._cli(["status"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["release_state"] == "active"


def test_snapshot_filters_baseline_and_is_byte_idempotent(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    book_dir = registry.data_dir("autonomous")
    _seed_legacy(book_dir)
    _activate_start()
    _seed_forward(isolated_root, book_dir)

    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-13")
    metrics = snapshot["metrics"]
    assert snapshot["cohort"]["deployment_sha"] == SHA_A
    assert snapshot["sample_counts"] == {
        "marked_sessions": 2, "decisions": 2, "effective_decisions": 2,
        "fills": 2, "closed_positions": 1, "post_sell_sales": 2,
        "selected_names": 2, "rejected_names": 2,
    }
    assert metrics["top_1_weight_pct"]["value"] == 50.0
    assert metrics["top_3_weight_pct"]["value"] == 80.0
    assert metrics["position_hhi"]["value"] == 0.30
    assert metrics["gross_exposure_pct"]["sample_n"] == 1
    assert metrics["cash_pct"]["sample_n"] == 1
    assert metrics["net_exposure_pct"]["status"] == "available"
    assert metrics["decision_count"]["value"] == 2  # legacy row excluded
    assert metrics["fill_count"]["value"] == 2      # legacy buy excluded from count
    assert metrics["candidate_count"]["value"] == 4
    assert metrics["finalist_count"]["value"] == 3
    assert metrics["requested_exit_count"]["value"] == 1
    assert metrics["effective_exit_count"]["value"] == 1
    assert metrics["blocked_exit_count"]["value"] == 1
    assert metrics["omission_carried_exit_count"]["value"] == 1
    assert metrics["closed_hold_days_average"]["value"] == 1.0
    assert metrics["closed_within_1_day_rate_pct"]["value"] == 100.0
    assert metrics["closed_hold_sessions_average"]["value"] == 1.0
    assert metrics["full_exit_hit_rate_pct"]["value"] == 100.0
    assert metrics["full_exit_hit_rate_pct"]["status"] == "partial"
    assert metrics["full_exit_hit_rate_pct"]["missing_reason"] == (
        "some_durable_full_closes_lack_complete_fifo_basis"
    )
    assert metrics["benchmark_session_hit_rate_pct"]["sample_n"] == 1
    assert metrics["full_exit_explicit_memo_coverage_pct"]["value"] == 100.0
    assert metrics["partial_trim_explicit_memo_coverage_pct"]["value"] == 0.0
    assert metrics["entry_evidence_coverage_pct"]["value"] == 100.0
    assert metrics["early_max_adverse_excursion_pct"] == {
        "value": None, "sample_n": 0, "status": "missing",
        "missing_reason": "authoritative_point_in_time_per_ticker_price_path_unavailable",
    }
    assert metrics["return_contribution_by_sleeve_pct"]["status"] == "missing"
    assert all(set(metric) == {"value", "sample_n", "status", "missing_reason"}
               for metric in metrics.values())

    dated = forward_evaluation._book_output_dir("autonomous") / "2026-08-13.json"
    latest = forward_evaluation._book_output_dir("autonomous") / "latest.json"
    before = (dated.read_bytes(), latest.read_bytes(), dated.stat().st_mtime_ns,
              latest.stat().st_mtime_ns)
    repeated = forward_evaluation.evaluate("autonomous", "2026-08-13")
    after = (dated.read_bytes(), latest.read_bytes(), dated.stat().st_mtime_ns,
             latest.stat().st_mtime_ns)
    assert repeated == snapshot
    assert after == before


def test_active_missing_artifacts_never_become_zero(isolated_root: Path) -> None:
    from portfolio import forward_evaluation

    _activate_start()
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-11")
    assert snapshot["sample_counts"] == forward_evaluation._zero_sample_counts()
    assert snapshot["metrics"]["gross_exposure_pct"]["value"] is None
    assert snapshot["metrics"]["marked_session_count"]["value"] is None
    assert snapshot["metrics"]["decision_count"]["value"] is None
    assert snapshot["metrics"]["traded_value_turnover_pct"]["value"] is None
    assert snapshot["metrics"]["max_drawdown_pct"]["status"] == "insufficient_sample"


def test_pending_transaction_admits_only_post_baseline_rows_after_health(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    forward_evaluation.initialize_start(SHA_A, "2026-08-11")
    _write_jsonl(registry.data_dir("autonomous") / "decisions.jsonl", [
        {"asof": "2026-08-11", "target_status": "executed", "decision_effective": True},
        {"asof": "2026-08-12", "target_status": "executed", "decision_effective": True},
    ])
    pending = forward_evaluation.evaluate("autonomous", "2026-08-12")
    assert pending["status"] == "not_started"
    assert not forward_evaluation._book_output_dir("autonomous").exists()
    forward_evaluation.finalize_start(SHA_A)
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-12")
    assert snapshot["sample_counts"]["decisions"] == 2
    assert snapshot["cohort"]["quarantined_start_day_sources"] == []
    assert snapshot["cohort"]["boundary"] == (
        "stopped_service_baseline_ids_plus_inclusive_date_window"
    )


def test_stopped_service_baseline_blocks_legacy_and_admits_target_same_day_rows(
    isolated_root: Path,
) -> None:
    from portfolio import forward_evaluation, registry

    book_dir = registry.data_dir("autonomous")
    _seed_legacy(book_dir)
    forward_evaluation.initialize_start(SHA_A, "2026-08-11")
    # The service is stopped at baseline creation. Any mutation after this point belongs to the
    # target v2 process; evaluation itself remains dormant until exact-SHA health activation.
    _write_jsonl(book_dir / "decisions.jsonl", [{
        "asof": "2026-08-11", "target_status": "executed", "decision_effective": True,
        "effective_holdings": [{"ticker": "AAPL", "action_effective": "add"}],
        "executed": [{"ticker": "AAPL", "side": "buy"}],
    }])
    _write_jsonl(book_dir / "fills.jsonl", [{
        "date": "2026-08-11", "ticker": "AAPL", "side": "buy",
        "shares": 101.0, "price": 100.0, "value": 10_100.0,
    }])
    _write_jsonl(book_dir / "nav_history.jsonl", [{
        "date": "2026-08-11", "nav": 1_001_000.0, "cash": 399_000.0,
        "invested": 602_000.0, "spy_nav": 1_000_500.0, "benchmark": "SPY",
    }])
    _write_json(book_dir / "positions_ledger.json", {
        "brain:AAPL": {"ticker": "AAPL", "still_open": False, "history": [
            {"event": "open", "as_of": "2026-08-11"},
            {"event": "close", "as_of": "2026-08-11"},
        ]},
    })
    _write_json(isolated_root / "data" / "portfolio_learning" / "autonomous" /
                "post_sell.json", {"exits": [{
                    "exit_id": "autonomous:2026-08-11:AAPL:1",
                    "exit_date": "2026-08-11", "sale_kind": "full_exit",
                }]})

    assert forward_evaluation.evaluate("autonomous", "2026-08-12")["status"] == "not_started"
    forward_evaluation.finalize_start(SHA_A)
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-12")
    assert snapshot["sample_counts"]["decisions"] == 1
    assert snapshot["sample_counts"]["fills"] == 1
    assert snapshot["sample_counts"]["closed_positions"] == 1
    assert snapshot["sample_counts"]["post_sell_sales"] == 1


def test_explicit_logical_id_prevents_mutable_legacy_row_resurrection(
    isolated_root: Path,
) -> None:
    from portfolio import forward_evaluation, registry

    path = registry.data_dir("autonomous") / "decisions.jsonl"
    _write_jsonl(path, [{
        "decision_id": "legacy-decision", "asof": "2026-08-11",
        "target_status": "executed", "decision_effective": True,
    }])
    _activate_start()
    _write_jsonl(path, [
        {"decision_id": "legacy-decision", "asof": "2026-08-11",
         "target_status": "executed", "decision_effective": True, "later_grade": "augmented"},
        {"decision_id": "v2-decision", "asof": "2026-08-11",
         "target_status": "executed", "decision_effective": True},
    ])
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-11")
    assert snapshot["sample_counts"]["decisions"] == 1


def test_same_asof_correction_preserves_prior_revision_and_receipt(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    book_dir = registry.data_dir("autonomous")
    _seed_legacy(book_dir)
    _activate_start()
    _seed_forward(isolated_root, book_dir)
    prior = forward_evaluation.evaluate("autonomous", "2026-08-13")

    latest = json.loads((book_dir / "latest.json").read_text(encoding="utf-8"))
    latest["positions"][0]["weight"] = 0.45
    _write_json(book_dir / "latest.json", latest)
    replacement = forward_evaluation.evaluate("autonomous", "2026-08-13")
    assert replacement["metrics"]["top_1_weight_pct"]["value"] == 45.0

    out = forward_evaluation._book_output_dir("autonomous")
    revisions = list((out / "revisions" / "2026-08-13").glob("*.json"))
    receipts = list((out / "corrections" / "2026-08-13").glob("*.json"))
    assert len(revisions) == 1 and len(receipts) == 1
    assert json.loads(revisions[0].read_text(encoding="utf-8")) == prior
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["reason"] == "durable_source_artifact_changed_for_same_asof"
    assert receipt["prior_snapshot_sha256"] != receipt["replacement_snapshot_sha256"]

    forward_evaluation.evaluate("autonomous", "2026-08-13")
    assert len(list((out / "revisions" / "2026-08-13").glob("*.json"))) == 1
    assert len(list((out / "corrections" / "2026-08-13").glob("*.json"))) == 1


def test_read_only_api_serves_status_without_evaluating_or_writing(
    isolated_root: Path, monkeypatch,
) -> None:
    from app import web
    from portfolio import forward_evaluation

    _activate_start()
    forward_evaluation.evaluate("autonomous", "2026-08-11")
    tree = forward_evaluation._output_root()
    before = {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*.json")}
    monkeypatch.setattr(
        forward_evaluation, "evaluate",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("API must not compute")),
    )

    response = web.api_forward_evaluation("autonomous", None)
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["status"] == "available"
    assert payload["snapshot"]["book"] == "autonomous"
    assert {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*.json")} == before
    assert web.api_forward_evaluation("../../escape", None).status_code == 404


def test_partial_inputs_taint_every_dependent_metric(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    base = registry.data_dir("autonomous")
    (base / "decisions.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (base / "decisions.jsonl").write_text(
        json.dumps({
            "asof": "2026-08-12", "target_status": "executed", "decision_effective": True,
            "effective_holdings": [{"ticker": "AAPL", "action_effective": "add",
                                    "evidence": ["x"]}],
        }) + "\n{broken\n", encoding="utf-8")
    (base / "fills.jsonl").write_text(
        json.dumps({"date": "2026-08-12", "ticker": "AAPL", "side": "buy",
                    "shares": 10, "price": 100}) + "\n" +
        json.dumps({"date": "2026-08-13", "ticker": "AAPL", "side": "sell",
                    "shares": 10, "price": 110}) + "\n{broken\n", encoding="utf-8")
    (base / "nav_history.jsonl").write_text(
        json.dumps({"date": "2026-08-12", "nav": 1000, "cash": 500,
                    "invested": 500, "spy_nav": 1000, "benchmark": "SPY"}) + "\n" +
        json.dumps({"date": "2026-08-13", "nav": 1010, "cash": 510,
                    "invested": 500, "spy_nav": 1005, "benchmark": "SPY"}) +
        "\n{broken\n", encoding="utf-8")

    metrics = forward_evaluation.evaluate("autonomous", "2026-08-13")["metrics"]
    for name in ("decision_count", "effective_decision_count", "entry_evidence_coverage_pct",
                 "marked_session_count", "inception_benchmark_relative_return_pct",
                 "max_drawdown_pct", "fill_count", "traded_value_turnover_pct",
                 "full_exit_hit_rate_pct"):
        assert metrics[name]["status"] != "available", name


def test_duplicate_nav_dates_are_one_partial_session(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    _write_jsonl(registry.data_dir("autonomous") / "nav_history.jsonl", [
        {"date": "2026-08-12", "nav": 1000, "cash": 500, "invested": 500,
         "spy_nav": 1000, "benchmark": "SPY"},
        {"date": "2026-08-12", "nav": 1002, "cash": 502, "invested": 500,
         "spy_nav": 1001, "benchmark": "SPY"},
        {"date": "2026-08-13", "nav": 1010, "cash": 510, "invested": 500,
         "spy_nav": 1005, "benchmark": "SPY"},
    ])
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-13")
    assert snapshot["sample_counts"]["marked_sessions"] == 2
    assert snapshot["metrics"]["marked_session_count"]["value"] == 2
    assert snapshot["metrics"]["marked_session_count"]["status"] == "partial"
    assert snapshot["metrics"]["benchmark_session_hit_rate_pct"]["sample_n"] == 1
    assert snapshot["inputs"]["nav"]["deduplicated_row_count"] == 1


def test_latest_is_monotonic_and_future_asof_is_no_write(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    _write_jsonl(registry.data_dir("autonomous") / "nav_history.jsonl", [
        {"date": "2026-08-12", "nav": 1000, "cash": 500, "invested": 500},
        {"date": "2026-08-13", "nav": 1010, "cash": 510, "invested": 500},
    ])
    forward_evaluation.evaluate("autonomous", "2026-08-13")
    forward_evaluation.evaluate("autonomous", "2026-08-12")
    assert forward_evaluation.load_snapshot("autonomous")["asof"] == "2026-08-13"
    future = forward_evaluation.evaluate("autonomous", "2026-08-14")
    assert future["status"] == "future_asof"
    assert not (forward_evaluation._book_output_dir("autonomous") / "2026-08-14.json").exists()


def test_stale_latest_weights_fall_back_to_current_account_marks(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    base = registry.data_dir("autonomous")
    _write_jsonl(base / "nav_history.jsonl", [{
        "date": "2026-08-13", "nav": 1000, "cash": 500, "invested": 500,
    }])
    _write_json(base / "latest.json", {
        "as_of": "2026-08-12", "positions": [{"ticker": "AAPL", "weight": 0.8}],
    })
    _write_json(base / "account.json", {
        "cash": 500, "positions": {"AAPL": {"shares": 5, "current_price": 100}},
    })
    metric = forward_evaluation.evaluate("autonomous", "2026-08-13")["metrics"][
        "top_1_weight_pct"
    ]
    assert metric == {"value": 50.0, "sample_n": 1, "status": "available",
                      "missing_reason": None}


def test_malformed_nested_ledgers_are_missing_not_false_zero(isolated_root: Path) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    base = registry.data_dir("autonomous")
    _write_json(base / "positions_ledger.json", {"broken:AAPL": []})
    _write_json(isolated_root / "data" / "portfolio_learning" / "autonomous" /
                "post_sell.json", {
                    "schema": "portfolio.post_sell.v1", "exits": {"not": "a list"},
                })
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-11")
    assert snapshot["inputs"]["positions"]["status"] == "invalid"
    assert snapshot["inputs"]["post_sell"]["status"] == "invalid"
    assert snapshot["metrics"]["closed_position_count"]["value"] is None
    assert snapshot["metrics"]["post_sell_sale_count"]["value"] is None


def test_empty_latest_positions_cannot_claim_zero_concentration_with_exposure(
    isolated_root: Path,
) -> None:
    from portfolio import forward_evaluation, registry

    _activate_start()
    base = registry.data_dir("autonomous")
    _write_jsonl(base / "nav_history.jsonl", [{
        "date": "2026-08-13", "nav": 1000, "cash": 500, "invested": 500,
    }])
    _write_json(base / "latest.json", {"as_of": "2026-08-13", "positions": []})
    _write_json(base / "account.json", {
        "cash": 500, "positions": {"AAPL": {"shares": 5, "avg_cost": 100}},
    })
    metric = forward_evaluation.evaluate("autonomous", "2026-08-13")["metrics"][
        "top_1_weight_pct"
    ]
    assert metric["value"] is None
    assert metric["status"] == "partial"
    assert metric["missing_reason"] == "some_current_positions_lack_durable_weight_or_mark"


def test_effective_exits_lifecycle_and_failure_status_are_honest(
    isolated_root: Path, monkeypatch,
) -> None:
    from app import scheduler
    from portfolio import forward_evaluation, registry

    _activate_start()
    _write_jsonl(registry.data_dir("autonomous") / "decisions.jsonl", [{
        "asof": "2026-08-12", "target_status": "rejected_quote_gap",
        "decision_effective": False, "exit_decisions": [{"ticker": "AAPL"}],
    }])
    snapshot = forward_evaluation.evaluate("autonomous", "2026-08-12")
    assert snapshot["metrics"]["effective_exit_count"]["value"] == 0
    assert forward_evaluation.status("self_directed")["status"] == "unsupported_book"
    assert forward_evaluation.status("autonomous", "2026-08-10")["status"] == (
        "before_evaluation_start"
    )

    failures: list[dict] = []
    monkeypatch.setattr(forward_evaluation, "evaluate", lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(RuntimeError("evaluation broke"))
    ))
    monkeypatch.setattr(scheduler, "_step_failed_event",
                        lambda *args, **kwargs: failures.append({"args": args, "kwargs": kwargs}))
    result = scheduler._post_mark_forward_evaluation("autonomous", asof="2026-08-13")
    assert result["status"] == "error"
    assert failures[0]["kwargs"]["severity"] == "FREEZE"
    assert forward_evaluation.status("autonomous")["status"] == "stale_after_error"


def test_daily_mark_book_failure_has_visible_step_event() -> None:
    import inspect
    from app import scheduler

    source = inspect.getsource(scheduler._daily_mark_job)
    assert '_step_failed_event("daily_mark", pid, f"mark:{pid}", exc, severity="FREEZE")' in source


@pytest.mark.parametrize(
    ("job_name", "module_name", "runner_name", "book"),
    [
        ("_autonomous_job", "bot.autonomous", "run_autonomous", "autonomous"),
        ("_china_job", "bot.china", "run_china", "china"),
        ("_hk_job", "bot.hk", "run_hk", "hk"),
    ],
)
def test_scheduled_post_mark_evaluation_runs_inside_book_lock(
    monkeypatch, job_name: str, module_name: str, runner_name: str, book: str,
) -> None:
    import importlib
    from app import scheduler
    from portfolio import forward_evaluation

    locked = {"active": False}
    calls: list[tuple[str, str]] = []

    class Lock:
        def __enter__(self):
            locked["active"] = True
            return self

        def __exit__(self, *_args):
            locked["active"] = False

    from control_plane import locks
    monkeypatch.setattr(locks, "acquire_or_log", lambda *args, **kwargs: Lock())
    module = importlib.import_module(module_name)

    def runner():
        assert locked["active"] is True
        return {"asof": "2026-08-12"}

    def evaluate(pid, asof):
        assert locked["active"] is True
        calls.append((pid, asof))
        return {"status": "available"}

    monkeypatch.setattr(module, runner_name, runner)
    monkeypatch.setattr(forward_evaluation, "evaluate", evaluate)
    monkeypatch.setattr(scheduler, "_ledger_start", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "_ledger_end", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "_maybe_schedule_brain_retry", lambda *args, **kwargs: None)

    getattr(scheduler, job_name)()
    assert calls == [(book, "2026-08-12")]
    assert locked["active"] is False


def test_deploy_transaction_closes_race_noop_and_failure_paths(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    script = (root / "scripts" / "deploy_code_to_vps.sh").read_text(encoding="utf-8")
    marker_write = script.index("release marker write failed")
    stop = script.index("systemctl stop '$SVC'", marker_write)
    init = script.index("python3 -m portfolio.forward_evaluation init", stop)
    restart = script.index("systemctl restart '$SVC'", init)
    health = script.index('if [[ "$CODE" == "200" ]]', restart)
    finalize = script.index("python3 -m portfolio.forward_evaluation finalize", health)
    verify = script.index("python3 -m portfolio.forward_evaluation status", finalize)
    success = script.index('log "deploy OK: $SVC healthy at commit $EXPECTED_SHA"')
    assert stop < init < restart < health < finalize < verify < success
    assert '&& probe_forward_evaluation; then' in script
    assert 'LIVE_DATA_PATH="${MASTERMIND_VPS_LIVE_DATA_PATH:-/opt/mastermind-live-data}"' in script
    assert script.count("MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH'") >= 4
    assert 'FORWARD_START_CREATED=1' in script
    assert "rm -f '$LIVE_DATA_PATH/portfolio_forward_evaluation/start.json'" in script
    assert 'fail_release "forward evaluation pending start initialization failed"' in script
    assert 'fail_release "forward evaluation activation/status verification failed"' in script
    assert subprocess.run(["bash", "-n", str(root / "scripts" / "deploy_code_to_vps.sh")],
                          check=False).returncode == 0

    # Pin the bounded rollback semantic: only a marker explicitly attributed to this failed
    # release is removed; a pre-existing marker survives.
    marker = tmp_path / "new-start-marker.json"
    marker.write_text("new", encoding="utf-8")
    try:
        result = subprocess.run(
            ["bash", "-c", (
                f"start_marker='{marker}'; FORWARD_START_CREATED=1; "
                'if [ "$FORWARD_START_CREATED" -eq 1 ]; then rm -f "$start_marker"; fi; '
                "false"
            )],
            check=False,
        )
        assert result.returncode != 0
        assert not marker.exists()
    finally:
        marker.unlink(missing_ok=True)
