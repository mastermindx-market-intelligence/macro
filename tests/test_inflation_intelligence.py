"""Contract tests for the display-only inflation intelligence foundation."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.inflation_intelligence import (
    build_inflation_intelligence,
    write_inflation_intelligence,
)
from scripts.build_inflation_intelligence import main

_AS_OF = "2026-08-08"


def _write_series(root: Path, series_id: str, column: str, values: list[float]) -> None:
    path = root / "data" / "fred" / f"{series_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    index = pd.date_range("2025-05-01", periods=len(values), freq="MS")
    pd.DataFrame({column: values}, index=index).to_parquet(path)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict], malformed: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        if malformed:
            handle.write("{not-json\n")


def _entry(
    release_type: str,
    period: str,
    release_date: str,
    point: float,
    *,
    current_components: bool = False,
) -> dict:
    entry = {
        "release": "cpi",
        "release_type": release_type,
        "period": period,
        "release_date": release_date,
        "days_to": 4 if period == "2026-07" else 34,
        "target": "mom_sa_pct",
        "projection": {
            "point": point,
            "p10": point - 0.2,
            "p25": point - 0.1,
            "p50": point,
            "p75": point + 0.1,
            "p90": point + 0.2,
        },
        "confidence": 0.4,
        "input_completeness": 0.9,
        "model_epoch": f"champion-model:{release_type}",
        "target_epoch": f"coherent-target:{release_type}",
        "code_receipt": "git:0123456789abcdef",
        "inputs_hash": f"sha256:champion-inputs:{release_type}:{period}",
        "primary_forecast_basis": "combined_v1_benchmark_augmented",
        "context_metrics_basis": "champion_legacy_target_v1",
        "basis_warning": "Combined point and champion context use different bases.",
        "coverage_flags": {
            "weight_coverage": 1.0,
            "fresh_proxy_coverage": 0.75,
            "non_vintaged_share": 0.25,
            "model_maturity": 2,
        },
        "pit": {
            "absent_legs": [],
            "revision_optimistic_legs": ["shelter_nowcast"],
            "range_violation_legs": [],
            "display_only": True,
            "authority": False,
        },
        "input_snapshot_ref": f"snapshots/{release_type}_{period}.json",
        "combined": {
            "combined_point": point + 0.02,
            "p10": point - 0.2,
            "p90": point + 0.2,
            "n_scored_basis": 1,
            "model_epoch": f"combined-model:{release_type}",
            "target_epoch": f"combined-target:{release_type}",
            "code_receipt": "git:combined012345",
            "inputs_hash": f"sha256:combined:{release_type}:{period}",
            "combined_components": {
                "inputs_used": ["champion", "cpi_bridge", "cleveland"],
                "input_hashes": {
                    "champion": f"sha256:champion:{release_type}:{period}",
                    "cpi_bridge": f"sha256:bridge:{release_type}:{period}",
                },
            },
        },
    }
    if current_components and release_type == "cpi_headline":
        entry["shadows"] = {
            "cpi_bridge": {
                "weight_coverage": 0.8,
                "prior_driven_share": 0.2,
                "weight_basis": "bls_dec_2025_starting_relative_importance_fixed_approximation",
                "weight_basis_warning": "BLS relative importance evolves monthly",
                "known_scope_mismatches": [
                    {
                        "series": "CUSR0000SASLE",
                        "warning": "includes shelter; not core services ex shelter",
                    }
                ],
                "components": [
                    {
                        "block": "energy_gasoline",
                        "mom_est": 1.2,
                        "weight": 3.0,
                        "contribution_pp": 0.036,
                        "confidence": 1.0,
                        "prior_only": False,
                        "degraded": False,
                        "legs_used": 1,
                        "legs_expected": 1,
                        "missing_legs": [],
                    },
                    {
                        "block": "unmodelled_residual",
                        "mom_est": 0.2,
                        "weight": 20.0,
                        "contribution_pp": 0.04,
                        "confidence": 0.0,
                        "prior_only": True,
                        "degraded": False,
                        "legs_used": 0,
                        "legs_expected": 0,
                        "missing_legs": [],
                    },
                ],
            }
        }
    return entry


def _fixture(root: Path) -> None:
    periods = 16
    _write_series(
        root,
        "CPIAUCSL",
        "headline_cpi",
        list(100.0 * np.power(1.01, np.arange(periods))),
    )
    _write_series(
        root,
        "CPILFESL",
        "core_cpi",
        list(100.0 * np.power(1.005, np.arange(periods))),
    )
    _write_series(root, "STICKCPIM157SFRBATL", "sticky_cpi", [0.2] * periods)
    _write_series(root, "FLEXCPIM157SFRBATL", "flex_cpi", [0.1] * periods)

    _write_json(root / "data" / "release_forecast" / "latest.json", {
        "schema": "release_forecast.v2",
        "asof": "2026-08-08T16:19:51Z",
        "display_only": True,
        "upcoming": [
            _entry("cpi_headline", "2026-07", "2026-08-12", 0.2),
            _entry("cpi_core", "2026-07", "2026-08-12", 0.3),
            _entry("cpi_headline", "2026-08", "2026-09-11", 0.4, current_components=True),
            _entry("cpi_core", "2026-08", "2026-09-11", 0.25),
        ],
    })
    _write_jsonl(root / "data" / "release_forecast" / "forward_ledger.jsonl", [
        {
            "row_type": "projection",
            "asof_night": "2026-08-01",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 0.1,
            "projection_p10": -0.1,
            "projection_p90": 0.3,
            "model_epoch": "champion-model:cpi_headline",
            "target_epoch": "coherent-target:cpi_headline",
            "code_receipt": "git:ledger-0801",
            "inputs_hash": "sha256:ledger-inputs-0801",
            "input_snapshot_ref": "snapshots/ledger-0801.json",
        },
        {
            "row_type": "projection",
            "asof_night": "2026-08-05",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 0.2,
        },
        # Same-asof append replaces the earlier receipt in the compact evolution.
        {
            "row_type": "projection",
            "asof_night": "2026-08-05",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 0.22,
            "prediction_id": "latest-same-day",
            "model_epoch": "champion-model:cpi_headline",
            "target_epoch": "coherent-target:cpi_headline",
            "code_receipt": "git:ledger-0805",
            "inputs_hash": "sha256:ledger-inputs-0805",
            "input_snapshot_ref": "snapshots/ledger-0805.json",
        },
        # A shadow model must not contaminate the champion evolution path.
        {
            "row_type": "shadow_projection",
            "model": "combined_v1",
            "asof_night": "2026-08-05",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 9.9,
        },
        {
            "row_type": "projection",
            "asof_night": "2026-08-05",
            "release": "cpi_core",
            "period": "2026-07",
            "projection_point": 0.3,
        },
        {
            "row_type": "projection",
            "asof_night": "2026-08-05",
            "release": "cpi_headline",
            "period": "2026-08",
            "projection_point": 0.4,
        },
        # The append-only ledger may be newer than a historical artifact build.
        # Later and unparseable clocks must fail closed for each matching target.
        {
            "row_type": "projection",
            "asof_night": "2026-08-09",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 8.9,
        },
        {
            "row_type": "projection",
            "asof_night": "not-a-date",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 7.7,
        },
        {
            "row_type": "projection",
            "asof_night": "2026-08",
            "release": "cpi_headline",
            "period": "2026-07",
            "projection_point": 7.6,
        },
        {
            "row_type": "projection",
            "asof_night": "2026-08-09",
            "release": "cpi_headline",
            "period": "2026-08",
            "projection_point": 6.6,
        },
    ])


def test_contract_separates_three_inflation_clocks(tmp_path: Path) -> None:
    _fixture(tmp_path)
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)

    assert state["schema"] == "inflation_intelligence.v1"
    assert state["display_only"] is True
    assert state["authority"] is False
    assert all(value is False for value in state["allowed_actions"].values())
    assert {
        "released_state",
        "next_release_forecast",
        "current_month_proxy_pressure",
    } <= set(state)

    assert state["released_state"]["headline"]["observation_period"] == "2026-08"
    assert state["next_release_forecast"]["period"] == "2026-07"
    assert state["next_release_forecast"]["release_date"] == "2026-08-12"
    assert state["current_month_proxy_pressure"]["period"] == "2026-08"
    assert state["freshness"]["status"] == "current_with_publication_lag"
    assert "rebuilding this wrapper" in state["freshness"]["policy"]

    rendered = json.dumps(state).lower()
    assert "current cpi" not in rendered
    assert "not an official cpi observation" in rendered


def test_released_state_uses_exact_3m_6m_annualization(tmp_path: Path) -> None:
    _fixture(tmp_path)
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    headline = state["released_state"]["headline"]
    expected = ((1.01**12) - 1.0) * 100.0
    assert headline["mom_pct"] == pytest.approx(1.0, abs=1e-6)
    assert headline["annualized_3m_pct"] == pytest.approx(expected, abs=1e-6)
    assert headline["annualized_6m_pct"] == pytest.approx(expected, abs=1e-6)
    assert headline["acceleration_3m_minus_6m_pp"] == pytest.approx(0.0, abs=1e-6)
    assert headline["revision_basis"] == "latest_local_fred_not_original_release_vintage"

    sticky = state["released_state"]["underlying_proxies"]["sticky"]
    sticky_expected = ((1.002**12) - 1.0) * 100.0
    assert sticky["annualized_3m_pct"] == pytest.approx(sticky_expected, abs=1e-6)


def test_forecast_evolution_is_append_order_deduped_and_shadow_free(tmp_path: Path) -> None:
    _fixture(tmp_path)
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    evolution = state["next_release_forecast"]["headline"]["forecast_evolution"]
    assert evolution["n_points"] == 2
    assert [point["asof"] for point in evolution["points"]] == ["2026-08-01", "2026-08-05"]
    assert evolution["points"][-1]["point"] == pytest.approx(0.22)
    assert evolution["points"][-1]["prediction_id"] == "latest-same-day"
    assert evolution["points"][-1]["code_receipt"] == "git:ledger-0805"
    assert evolution["points"][-1]["inputs_hash"] == "sha256:ledger-inputs-0805"
    assert all(point["point"] != 9.9 for point in evolution["points"])
    assert all(point["point"] not in {7.6, 7.7, 8.9} for point in evolution["points"])
    assert evolution["cutoff_asof"] == _AS_OF
    assert evolution["excluded_after_cutoff"] == 1
    assert evolution["excluded_unparseable_asof"] == 2


def test_forecast_evolution_uses_artifact_or_explicit_historical_cutoff(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)

    # With no caller override, the Release Radar artifact asof is authoritative.
    artifact_clock = build_inflation_intelligence(tmp_path)
    evolution = artifact_clock["next_release_forecast"]["headline"]["forecast_evolution"]
    assert artifact_clock["asof"] == _AS_OF
    assert evolution["cutoff_asof"] == _AS_OF
    assert evolution["last_asof"] == "2026-08-05"

    # A replay resolved to an earlier day may not see rows appended afterward.
    historical = build_inflation_intelligence(tmp_path, as_of="2026-08-03")
    historical_evolution = historical["next_release_forecast"]["headline"][
        "forecast_evolution"
    ]
    assert [point["asof"] for point in historical_evolution["points"]] == [
        "2026-08-01"
    ]
    assert historical_evolution["cutoff_asof"] == "2026-08-03"
    assert historical_evolution["last_asof"] == "2026-08-01"
    assert historical_evolution["excluded_after_cutoff"] == 3

    pressure_evolution = artifact_clock["current_month_proxy_pressure"][
        "headline_model_pressure"
    ]["forecast_evolution"]
    assert [point["asof"] for point in pressure_evolution["points"]] == ["2026-08-05"]
    assert pressure_evolution["excluded_after_cutoff"] == 1


def test_forecast_provenance_and_combined_basis_are_preserved(tmp_path: Path) -> None:
    _fixture(tmp_path)
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    target = state["next_release_forecast"]["headline"]

    assert target["model_epoch"] == "champion-model:cpi_headline"
    assert target["target_epoch"] == "coherent-target:cpi_headline"
    assert target["code_receipt"] == "git:0123456789abcdef"
    assert target["inputs_hash"] == "sha256:champion-inputs:cpi_headline:2026-07"
    assert target["input_snapshot_ref"] == "snapshots/cpi_headline_2026-07.json"
    assert target["primary_forecast_basis"] == "combined_v1_benchmark_augmented"
    assert target["context_metrics_basis"] == "champion_legacy_target_v1"
    assert target["basis_warning"].startswith("Combined point")

    combined = target["combined_display_estimate"]
    assert combined["model_epoch"] == "combined-model:cpi_headline"
    assert combined["target_epoch"] == "combined-target:cpi_headline"
    assert combined["code_receipt"] == "git:combined012345"
    assert combined["inputs_hash"] == "sha256:combined:cpi_headline:2026-07"
    assert combined["input_hashes"]["cpi_bridge"] == (
        "sha256:bridge:cpi_headline:2026-07"
    )


def test_component_freshness_and_coverage_are_explicit(tmp_path: Path) -> None:
    _fixture(tmp_path)
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    pressure = state["current_month_proxy_pressure"]
    assert pressure["coverage"]["bridge_known_scope_mismatches"][0]["series"] == (
        "CUSR0000SASLE"
    )
    assert "evolves monthly" in pressure["coverage"]["bridge_weight_basis_warning"]
    components = {row["component"]: row for row in pressure["component_freshness"]}
    assert components["energy_gasoline"]["status"] == "proxy_available"
    assert components["unmodelled_residual"]["status"] == "prior_only"
    assert pressure["coverage"]["radar_fresh_proxy_coverage"] == pytest.approx(0.75)
    assert pressure["coverage"]["bridge_modelled_weight_coverage"] == pytest.approx(0.8)
    assert pressure["coverage"]["revision_optimistic_legs"] == ["shelter_nowcast"]
    combined = pressure["headline_model_pressure"]["combined_display_estimate"]
    assert combined["includes_external_benchmark"] is True
    assert combined["authority"] is False


def test_missing_inputs_fail_open_and_writer_emits_valid_json(tmp_path: Path) -> None:
    state, target = write_inflation_intelligence(tmp_path, as_of=_AS_OF)
    assert target.exists()
    assert json.loads(target.read_text()) == state
    assert state["released_state"]["available"] is False
    assert state["next_release_forecast"]["available"] is False
    assert state["current_month_proxy_pressure"]["available"] is False
    assert state["gaps"]
    assert state["authority"] is False


def test_malformed_ledger_row_is_quarantined_not_fatal(tmp_path: Path) -> None:
    _fixture(tmp_path)
    ledger = tmp_path / "data" / "release_forecast" / "forward_ledger.jsonl"
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("{broken\n")
    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    status = state["source_status"]["release_radar_forward_ledger"]
    assert status["available"] is True
    assert status["malformed_rows"] == 1
    assert any("malformed_rows:1" in gap for gap in state["gaps"])


def test_fresh_wrapper_does_not_hide_stale_underlying_monthly_sources(
    tmp_path: Path,
) -> None:
    for series_id, column in (
        ("CPIAUCSL", "headline_cpi"),
        ("CPILFESL", "core_cpi"),
        ("STICKCPIM157SFRBATL", "sticky_cpi"),
        ("FLEXCPIM157SFRBATL", "flex_cpi"),
    ):
        _write_series(tmp_path, series_id, column, [100.0, 101.0, 102.0])
    _write_json(
        tmp_path / "data" / "release_forecast" / "latest.json",
        {"schema": "release_forecast.v2", "asof": f"{_AS_OF}T02:00:00Z", "upcoming": []},
    )
    _write_jsonl(
        tmp_path / "data" / "release_forecast" / "forward_ledger.jsonl",
        [],
    )

    state = build_inflation_intelligence(tmp_path, as_of=_AS_OF)

    assert state["asof"] == _AS_OF
    assert state["freshness"]["status"] == "degraded"
    assert any(
        reason.startswith("fred:CPIAUCSL:stale:")
        for reason in state["freshness"]["degraded_reasons"]
    )
    assert state["released_state"]["headline"]["freshness_status"] == "stale"
    assert state["source_status"]["fred"]["headline"]["freshness_status"] == "stale"


def test_cli_writes_requested_output(tmp_path: Path) -> None:
    _fixture(tmp_path)
    custom = tmp_path / "out" / "inflation.json"
    rc = main(["--root", str(tmp_path), "--as-of", _AS_OF, "--output", str(custom)])
    assert rc == 0
    assert custom.exists()
    assert json.loads(custom.read_text())["schema"] == "inflation_intelligence.v1"


# ---------------------------------------------------------------------------
# I0-BUILD: matched_lenses fixture helpers
# ---------------------------------------------------------------------------


def _write_daily_series(
    root: Path,
    series_id: str,
    column: str,
    values: list[float],
    end: str = "2026-08-07",
) -> None:
    path = root / "data" / "fred" / f"{series_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    index = pd.bdate_range(end=end, periods=len(values))
    pd.DataFrame({column: values}, index=index).to_parquet(path)


def _fixture_lenses(root: Path) -> None:
    """Build the rich fixture: base CPI/PCE/proxy + radar + breakevens + expinf + survey.

    Layered on top of ``_fixture`` so the existing test contract keeps working.
    PCE and breakeven/expinf/survey parquet are added at the same FRED paths the
    engine reads. ``data/release_forecast/latest.json`` is REWRITTEN in place so
    the 2026-07 entries carry benchmark_set, expectation_read, combined (with the
    new model_epoch/target_epoch/inputs_used), and entry-level model_epoch and
    target_epoch overlays.
    """
    _fixture(root)

    periods = 16
    _write_series(
        root,
        "PCEPI",
        "headline_pce",
        list(100.0 * np.power(1.002, np.arange(periods))),
    )
    _write_series(
        root,
        "PCEPILFE",
        "core_pce",
        list(100.0 * np.power(1.0025, np.arange(periods))),
    )

    _write_daily_series(root, "T10YIE", "breakeven_10y", [2.31] * 30)
    _write_daily_series(root, "T5YIFR", "breakeven_5y5y", [2.24] * 30)

    expinf_months = 6
    expinf_index = pd.date_range("2026-02-01", periods=expinf_months, freq="MS")
    for sid, col, val in (
        ("EXPINF1YR", "infl_exp_1y", 2.9),
        ("EXPINF5YR", "infl_exp_5y", 2.5),
        ("EXPINF10YR", "infl_exp_10y", 2.4),
        ("MICH", "umich_infl_exp", 4.1),
    ):
        path = root / "data" / "fred" / f"{sid}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({col: [val] * expinf_months}, index=expinf_index).to_parquet(path)

    latest_path = root / "data" / "release_forecast" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    overlays = {
        "cpi_headline": {
            "benchmark_set": {
                "cleveland_nowcast": 0.27,
                "market_implied": {
                    "source": "kalshi",
                    "event_ticker": "KXCPI-26JUL",
                    "implied_median": 0.4,
                    "asof": "2026-08-07",
                },
            },
            "expectation_read": {
                "expectation_median": 0.36,
                "sources": ["cleveland_nowcast", "market_implied"],
            },
            "combined": {
                "combined_point": 0.33,
                "p10": 0.13,
                "p25": 0.23,
                "p50": 0.33,
                "p75": 0.43,
                "p90": 0.53,
                "model_epoch": "combined_v1_legacy_target_v1",
                "target_epoch": "mixed_legacy_cross_vintage_v0",
                "combined_components": {
                    "inputs_used": ["champion", "cleveland"],
                },
            },
            "model_epoch": "champion_legacy_target_v1",
            "target_epoch": "legacy_cross_vintage_initial_levels_v0",
        },
        "cpi_core": {
            "benchmark_set": {
                "cleveland_nowcast": 0.22,
                "market_implied": {
                    "source": "kalshi",
                    "event_ticker": "KXCPICORE-26JUL",
                    "implied_median": 0.3,
                    "asof": "2026-08-07",
                },
            },
            "expectation_read": {
                "expectation_median": 0.25,
                "sources": ["cleveland_nowcast", "market_implied"],
            },
            "combined": {
                "combined_point": 0.28,
                "p10": 0.08,
                "p25": 0.18,
                "p50": 0.28,
                "p75": 0.38,
                "p90": 0.48,
                "model_epoch": "combined_v1_legacy_target_v1",
                "target_epoch": "mixed_legacy_cross_vintage_v0",
                "combined_components": {
                    "inputs_used": ["champion", "cleveland"],
                },
            },
            "model_epoch": "champion_legacy_target_v1",
            "target_epoch": "legacy_cross_vintage_initial_levels_v0",
        },
    }
    new_upcoming = []
    for entry in latest.get("upcoming", []):
        overlay = overlays.get(entry.get("release_type"))
        if overlay is not None and entry.get("period") == "2026-07":
            merged = {**entry, **overlay}
            merged["combined"] = {**entry.get("combined", {}), **overlay["combined"]}
            merged["combined"]["combined_components"] = {
                **entry.get("combined", {}).get("combined_components", {}),
                **overlay["combined"]["combined_components"],
            }
            new_upcoming.append(merged)
        else:
            new_upcoming.append(entry)
    latest["upcoming"] = new_upcoming
    latest_path.write_text(json.dumps(latest), encoding="utf-8")


# ---------------------------------------------------------------------------
# I0-BUILD: matched_lenses constants + payload digest helper
# ---------------------------------------------------------------------------

_GOLDEN_BASE_SHA = "81fd91b22fd8beae8e82f2ec6da4fdea2e85370361a068451f552f0a16bcb81e"
_GOLDEN_LENSES_SHA = "328329a0a47b5b60c9dd37ba962a887da34ac49064145a42c099070841a33d2f"


def _payload_digest(payload: dict, root: Path) -> str:
    body = dict(payload)
    body.pop("matched_lenses", None)
    canon = json.dumps(
        body,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).replace(str(root), "<ROOT>")
    return hashlib.sha256(canon.encode()).hexdigest()


_BASE_KEYS = {
    "schema",
    "asof",
    "display_only",
    "authority",
    "is_context_only",
    "allowed_actions",
    "authority_note",
    "released_state",
    "next_release_forecast",
    "current_month_proxy_pressure",
    "freshness",
    "source_status",
    "gaps",
}

_LENS_IDS = (
    "official_cpi_headline_mom",
    "official_cpi_headline_yoy",
    "official_cpi_core_mom",
    "official_cpi_core_yoy",
    "official_pce_headline_mom",
    "official_pce_headline_yoy",
    "official_pce_core_mom",
    "official_pce_core_yoy",
    "house_radar_cpi_headline_next_mom",
    "house_radar_cpi_core_next_mom",
    "house_radar_combined_cpi_headline_next_mom",
    "house_radar_combined_cpi_core_next_mom",
    "cleveland_nowcast_cpi_headline_next_mom",
    "cleveland_nowcast_cpi_core_next_mom",
    "radar_expectation_read_cpi_headline_next_mom",
    "radar_expectation_read_cpi_core_next_mom",
    "market_cpi_headline_next_mom",
    "market_cpi_core_next_mom",
    "market_breakeven_10y",
    "market_forward_5y5y",
    "model_cleveland_expected_inflation_1y",
    "model_cleveland_expected_inflation_5y",
    "model_cleveland_expected_inflation_10y",
    "survey_umich_1y",
)

_LENS_RECORD_KEYS = {
    "lens_id",
    "label_en",
    "source_class",
    "evidence_class",
    "measure",
    "basket_or_index",
    "scope",
    "frequency",
    "transform",
    "unit",
    "horizon",
    "reference_period",
    "value",
    "value_state",
    "interval",
    "observation_date",
    "source",
    "series_id",
    "blend_inputs",
    "limitations",
    "qualified",
}


# ---------------------------------------------------------------------------
# I0-BUILD: §2.8 contract tests for matched_lenses
# ---------------------------------------------------------------------------


def test_i0_existing_payload_bytes_unchanged(tmp_path: Path) -> None:
    _fixture(tmp_path)
    payload = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    assert _payload_digest(payload, tmp_path) == _GOLDEN_BASE_SHA
    assert set(payload) - _BASE_KEYS == {"matched_lenses"}

    lenses_root = tmp_path / "lenses"
    lenses_root.mkdir()
    _fixture_lenses(lenses_root)
    payload2 = build_inflation_intelligence(lenses_root, as_of=_AS_OF)
    assert _payload_digest(payload2, lenses_root) == _GOLDEN_LENSES_SHA
    assert set(payload2) - _BASE_KEYS == {"matched_lenses"}


def test_i0_lens_set_is_fixed_and_every_lens_carries_its_class(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]
    assert tuple(block["lenses"]) == _LENS_IDS
    for lens_id, record in block["lenses"].items():
        assert set(record) == _LENS_RECORD_KEYS, lens_id
        if record["source_class"] in {"external_model_nowcast", "external_benchmark_blend"}:
            assert record["evidence_class"] is None
            assert record["qualified"] is None
        else:
            assert record["evidence_class"] == record["qualified"]["evidence_class"]
    assert any(
        gap.startswith("b0_evidence_class_absent:external_model_nowcast") for gap in block["gaps"]
    )


def test_i0_cpi_and_pce_are_separate_lenses_never_compared(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]
    by_id = {cmp["comparison_id"]: cmp for cmp in block["comparisons"]}
    for cid in ("cpi_vs_pce_headline_mom", "cpi_vs_pce_core_yoy"):
        cmp = by_id[cid]
        assert cmp["status"] == "not_comparable"
        assert cmp["difference"] is None
        assert cmp["reason"] == "basis_mismatch:basket_or_index"
        assert isinstance(cmp["reason"], str)
    cpi = block["lenses"]["official_cpi_headline_mom"]["value"]
    pce = block["lenses"]["official_pce_headline_mom"]["value"]
    assert cpi is not None and pce is not None and cpi != pce


def test_i0_monthly_and_annual_are_separate(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]
    mom = block["lenses"]["official_cpi_headline_mom"]
    yoy = block["lenses"]["official_cpi_headline_yoy"]
    assert mom["unit"] == "pct_mom" and yoy["unit"] == "pct_yoy"
    assert mom["lens_id"] != yoy["lens_id"]
    assert abs(mom["value"] - 1.0) < 1e-6
    assert abs(yoy["value"] - 12.682503) < 1e-6
    pair_ids = {(cmp["left_lens"], cmp["right_lens"]) for cmp in block["comparisons"]}
    assert (mom["lens_id"], yoy["lens_id"]) not in pair_ids
    assert (yoy["lens_id"], mom["lens_id"]) not in pair_ids


def test_i0_next_month_cpi_vs_breakeven_is_structurally_not_comparable(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]
    by_id = {cmp["comparison_id"]: cmp for cmp in block["comparisons"]}
    for cid in (
        "next_cpi_mom_vs_breakeven_10y",
        "next_cpi_mom_market_vs_breakeven_10y",
    ):
        cmp = by_id[cid]
        assert cmp["status"] == "not_comparable"
        assert cmp["difference"] is None
        assert cmp["reason"] == "basis_mismatch:reference_end"
        assert isinstance(cmp["reason"], str)


def test_i0_block_emits_no_derived_number(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]

    def _walk(node, path=()):
        if isinstance(node, dict):
            for key, value in node.items():
                _walk(value, path + (key,))
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                _walk(value, path + (idx,))
        elif isinstance(node, bool):
            return
        elif isinstance(node, (int, float)):
            allowed = False
            if len(path) >= 3 and path[0] == "lenses":
                if len(path) == 3 and path[2] == "value":
                    allowed = True
                elif len(path) == 4 and path[2] == "interval":
                    allowed = True
                elif len(path) == 4 and path[2] == "qualified" and path[3] == "value":
                    allowed = True
            assert allowed, f"unexpected numeric leaf at {path!r}: {node!r}"

    _walk(block)
    for cmp in block["comparisons"]:
        assert cmp["difference"] is None


def test_i0_no_lens_is_relabelled_street_consensus(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    payload = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    block = dict(payload["matched_lenses"])
    block.pop("street_consensus", None)
    for lens in block["lenses"].values():
        lens["blend_inputs"] = None
    blob = json.dumps(block, sort_keys=True, ensure_ascii=False).lower()
    for forbidden in ("consensus", "surprise", "current cpi"):
        assert forbidden not in blob
    assert payload["matched_lenses"]["street_consensus"] == {
        "value": None,
        "value_state": "unavailable",
        "reason": "no_admitted_street_economist_survey_source",
    }


def test_i0_external_inputs_are_never_blended_into_one_value(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]

    expected = {
        "house_radar_cpi_headline_next_mom": round(0.2, 6),
        "house_radar_cpi_core_next_mom": round(0.3, 6),
        "house_radar_combined_cpi_headline_next_mom": round(0.33, 6),
        "house_radar_combined_cpi_core_next_mom": round(0.28, 6),
        "cleveland_nowcast_cpi_headline_next_mom": round(0.27, 6),
        "cleveland_nowcast_cpi_core_next_mom": round(0.22, 6),
        "radar_expectation_read_cpi_headline_next_mom": round(0.36, 6),
        "radar_expectation_read_cpi_core_next_mom": round(0.25, 6),
        "market_cpi_headline_next_mom": round(0.4, 6),
        "market_cpi_core_next_mom": round(0.3, 6),
    }
    for lens_id, want in expected.items():
        got = block["lenses"][lens_id]["value"]
        assert got == want, (lens_id, got, want)


def test_i0_gaps_stay_inside_the_block(tmp_path: Path) -> None:
    _fixture(tmp_path)
    payload_with = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    payload_without = dict(payload_with)
    payload_without.pop("matched_lenses")
    assert payload_with["matched_lenses"]["gaps"] and any(
        gap.startswith("fred:PCEPI:absent") for gap in payload_with["matched_lenses"]["gaps"]
    )
    assert not any(
        gap.startswith("fred:PCEPI:absent") for gap in payload_with["gaps"]
    )
    assert payload_without["gaps"] == payload_with["gaps"]
    assert payload_without["freshness"] == payload_with["freshness"]
    assert payload_without["source_status"] == payload_with["source_status"]
    assert _payload_digest(payload_with, tmp_path) == _GOLDEN_BASE_SHA


def test_i0_missing_inputs_are_missing_never_zero(tmp_path: Path, monkeypatch) -> None:
    from engine import rates_command_basis as rcb
    from engine.inflation_intelligence import _matched_lenses

    original_compare_qualified = rcb.compare_qualified
    spy_calls: list[tuple[Any, Any, Any]] = []

    def _spy_compare_qualified(left, right, rule, *args, **kwargs):
        spy_calls.append((left, right, rule))
        return original_compare_qualified(left, right, rule, *args, **kwargs)

    monkeypatch.setattr(rcb, "compare_qualified", _spy_compare_qualified)
    # Also patch the reference inside _matched_lenses' local `rcb` import
    # (the function looks up rcb via the imported alias; monkeypatching the
    # module attribute is enough because the alias resolves to the same object).

    _fixture(tmp_path)
    payload = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    block = payload["matched_lenses"]

    # PCE lens records: still missing, but carry a qualified B0 object
    # whose evidence_class is "official_measurement", basket_or_index is
    # "PCE", and value_state is "missing".
    for lens_id in (
        "official_pce_headline_mom",
        "official_pce_headline_yoy",
        "official_pce_core_mom",
        "official_pce_core_yoy",
    ):
        record = block["lenses"][lens_id]
        assert record["value"] is None
        assert record["value_state"] == "missing"
        assert record["evidence_class"] == "official_measurement"
        assert record["qualified"] is not None
        assert record["qualified"]["value_state"] == "missing"
        assert record["qualified"]["basket_or_index"] == "PCE"
        assert record["qualified"]["evidence_class"] == "official_measurement"

    by_id = {cmp["comparison_id"]: cmp for cmp in block["comparisons"]}
    for cid in ("cpi_vs_pce_headline_mom", "cpi_vs_pce_core_yoy"):
        cmp = by_id[cid]
        assert cmp["status"] == "unavailable"
        assert isinstance(cmp["reason"], str)
        assert cmp["reason"] == "operand_missing:right"

    # The spy saw two compare_qualified calls and the right operand carried
    # basket_or_index=PCE, evidence_class=official_measurement, value_state=missing
    cpi_pce_calls = [c for c in spy_calls
                     if c[2].rule_id == "cpi_vs_pce.v1"]
    assert len(cpi_pce_calls) == 2
    for _left, right, _rule in cpi_pce_calls:
        right_d = right.to_dict()
        assert right_d["basket_or_index"] == "PCE"
        assert right_d["evidence_class"] == "official_measurement"
        assert right_d["value_state"] == "missing"

    no_radar_root = tmp_path / "no_radar"
    no_radar_root.mkdir()
    _fixture_lenses(no_radar_root)
    (no_radar_root / "data" / "release_forecast" / "latest.json").unlink()
    block_no_radar = build_inflation_intelligence(
        no_radar_root, as_of=_AS_OF
    )["matched_lenses"]

    # 6 QUALIFIED next-print lenses: non-None qualified with value_state="missing"
    qualified_next_print_ids = (
        "house_radar_cpi_headline_next_mom",
        "house_radar_cpi_core_next_mom",
        "house_radar_combined_cpi_headline_next_mom",
        "house_radar_combined_cpi_core_next_mom",
        "market_cpi_headline_next_mom",
        "market_cpi_core_next_mom",
    )
    for lens_id in qualified_next_print_ids:
        record = block_no_radar["lenses"][lens_id]
        assert record["value"] is None
        assert record["value_state"] == "missing"
        assert record["qualified"] is not None
        assert record["qualified"]["value_state"] == "missing"
        assert "no_next_release_entry" in record["limitations"]
        assert any(gap == "no_next_release_entry" for gap in block_no_radar["gaps"])

    # 4 UNQUALIFIED next-print lenses: qualified None, evidence_class None
    unqualified_next_print_ids = (
        "cleveland_nowcast_cpi_headline_next_mom",
        "cleveland_nowcast_cpi_core_next_mom",
        "radar_expectation_read_cpi_headline_next_mom",
        "radar_expectation_read_cpi_core_next_mom",
    )
    for lens_id in unqualified_next_print_ids:
        record = block_no_radar["lenses"][lens_id]
        assert record["value"] is None
        assert record["value_state"] == "missing"
        assert record["qualified"] is None
        assert record["evidence_class"] is None
        assert "no_next_release_entry" in record["limitations"]


def test_i0_after_cutoff_evidence_is_refused(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of="2026-08-07")["matched_lenses"]
    for lens_id in (
        "house_radar_cpi_headline_next_mom",
        "house_radar_combined_cpi_headline_next_mom",
        "market_cpi_headline_next_mom",
        "house_radar_cpi_core_next_mom",
        "house_radar_combined_cpi_core_next_mom",
        "market_cpi_core_next_mom",
    ):
        record = block["lenses"][lens_id]
        assert record["value"] is None
        assert record["value_state"] == "refused"
        assert "after_cutoff" in record["limitations"]
    for lens_id in (
        "cleveland_nowcast_cpi_headline_next_mom",
        "cleveland_nowcast_cpi_core_next_mom",
        "radar_expectation_read_cpi_headline_next_mom",
        "radar_expectation_read_cpi_core_next_mom",
    ):
        record = block["lenses"][lens_id]
        assert record["value"] is None
        assert record["value_state"] == "refused"
        assert "after_cutoff" in record["limitations"]


def test_i0_internal_error_degrades_never_raises(monkeypatch, tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    from engine import rates_command_basis as rcb

    def _boom(*args, **kwargs):
        raise RuntimeError("synthetic explosion")

    monkeypatch.setattr(rcb, "compare_qualified", _boom)
    payload = build_inflation_intelligence(tmp_path, as_of=_AS_OF)
    block = payload["matched_lenses"]
    assert block["available"] is False
    assert block["reason"] == "internal_error:RuntimeError"
    assert "internal_error:RuntimeError" in block["gaps"]
    assert _payload_digest(payload, tmp_path) == _GOLDEN_LENSES_SHA


def test_i0_writer_emits_strict_json_with_block(tmp_path: Path) -> None:
    _fixture_lenses(tmp_path)
    payload, target = write_inflation_intelligence(
        root=tmp_path, as_of=_AS_OF
    )
    text = target.read_text(encoding="utf-8")

    def _parse_constant(_value):
        raise ValueError("nan not allowed in payload")

    assert json.loads(text, parse_constant=_parse_constant)["matched_lenses"]["schema"] == (
        "inflation_matched_lenses.v1"
    )
    assert payload["matched_lenses"]["schema"] == "inflation_matched_lenses.v1"


def test_i0_b0_consumed_only_through_public_names(tmp_path: Path) -> None:
    """The matched_lenses block consumes B0 only through public names.

    After the I0-BUILD marker line, no QualifiedObservation construction,
    no from_dict, no rcb.Precision references, and rcb.<name> only names
    a documented public B0 entry point.
    """
    import re as _re
    from pathlib import Path as _Path
    module_text = (_Path("engine") / "inflation_intelligence.py").read_text(encoding="utf-8")
    marker = "# I0-BUILD: matched_lenses block"
    assert marker in module_text, "I0-BUILD marker missing"
    tail = module_text.split(marker, 1)[1]
    names = set(_re.findall(r"\brcb\.(\w+)", tail))
    allowed = {
        "qualify_observation",
        "compare_qualified",
        "RULES",
        "EvidenceClass",
        "ValueState",
    }
    assert names, "no rcb.<name> reference found in appended block"
    assert names <= allowed, f"unexpected rcb.<name> names: {sorted(names - allowed)}"
    assert "QualifiedObservation" not in tail
    assert "from_dict" not in tail
    assert "rcb.Precision" not in tail


def test_i0_term_structure_lenses_keep_horizon_and_model(tmp_path: Path) -> None:
    from engine.inflation_intelligence import _add_years

    _fixture_lenses(tmp_path)
    block = build_inflation_intelligence(tmp_path, as_of=_AS_OF)["matched_lenses"]

    ten_yr = block["lenses"]["market_breakeven_10y"]
    assert ten_yr["qualified"]["tenor"] == "10y"
    assert ten_yr["reference_period"]["start"] == "2026-08-07"
    assert ten_yr["reference_period"]["end"] == "2036-08-07"

    fwd = block["lenses"]["market_forward_5y5y"]
    assert fwd["qualified"]["tenor"] == "5y5y"
    assert fwd["reference_period"]["start"] == "2031-08-07"
    assert fwd["reference_period"]["end"] == "2036-08-07"

    for lens_id, exp_start, exp_end in (
        ("model_cleveland_expected_inflation_1y", "2026-07-01", "2027-07-01"),
        ("model_cleveland_expected_inflation_5y", "2026-07-01", "2031-07-01"),
        ("model_cleveland_expected_inflation_10y", "2026-07-01", "2036-07-01"),
    ):
        record = block["lenses"][lens_id]
        assert record["qualified"]["tenor"] in ("1y", "5y", "10y")
        assert record["qualified"]["model_id"] == "cleveland_expinf"
        assert record["reference_period"]["start"] == exp_start
        assert record["reference_period"]["end"] == exp_end

    survey = block["lenses"]["survey_umich_1y"]
    assert survey["evidence_class"] == "survey_participant_projection"
    assert survey["reference_period"]["end"] == "2027-07-01"

    # _add_years spec: Feb 29 → Feb 28 only, no other normalization
    assert _add_years("2028-02-29", 10) == "2038-02-28"
    assert _add_years("2028-02-29", 4) == "2032-02-29"
    assert _add_years("2026-08-07", 10) == "2036-08-07"

    assert len(json.dumps(block, sort_keys=True, ensure_ascii=False)) < 60000
