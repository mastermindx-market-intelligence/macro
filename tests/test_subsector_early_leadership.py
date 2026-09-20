from __future__ import annotations

import math

import numpy as np
import pandas as pd

from engine.subsector_early_leadership import (
    COVERAGE_TARGET_IDS,
    compute_early_leadership,
)


def _idx(n: int = 90) -> pd.DatetimeIndex:
    return pd.bdate_range("2026-01-05", periods=n)


def _series_from_returns(idx: pd.DatetimeIndex, daily_returns: list[float], start: float = 100.0) -> pd.Series:
    assert len(daily_returns) == len(idx) - 1
    vals = [start]
    for r in daily_returns:
        vals.append(vals[-1] * (1.0 + r))
    return pd.Series(vals, index=idx, dtype="float64")


def _flat(idx: pd.DatetimeIndex, value: float = 100.0) -> pd.Series:
    return pd.Series(value, index=idx, dtype="float64")


def _tree() -> list[dict]:
    return [
        {
            "theme": "Semiconductors",
            "subsectors": [
                {"key": "semiscompute", "name": "Compute", "description": "Logic & CPUs, GPUs, Accelerators", "members": ["A", "B", "C", "DUP"]},
                {"key": "semismemory", "name": "Memory", "description": "Memory & Storage", "members": ["M1", "M2", "M3", "DUP"]},
                {"key": "semislithography", "name": "Lithography", "description": "Equipment, Lithography & Deposition", "members": ["E1", "E2", "E3"]},
            ],
        },
        {
            "theme": "Hardware",
            "subsectors": [
                {"key": "hardwareservers", "name": "Servers", "description": "Servers, OEMs & Enterprise Systems", "members": ["S1", "S2", "S3", "S4"]},
                {"key": "hardwarestorage", "name": "Storage", "description": "Storage", "members": ["H1", "H2", "H3"]},
                {"key": "hardwaretelecom", "name": "Telecom", "description": "Communications & Telecom", "members": ["O1", "O2", "O3"]},
            ],
        },
    ]


def _base_panel(idx: pd.DatetimeIndex) -> pd.DataFrame:
    tickers = [
        "A", "B", "C", "DUP", "M1", "M2", "M3", "E1", "E2", "E3",
        "S1", "S2", "S3", "S4", "H1", "H2", "H3", "O1", "O2", "O3",
    ]
    return pd.DataFrame({ticker: _flat(idx) for ticker in tickers}, index=idx)


def _find(result: dict, key: str) -> dict:
    return next(row for row in result["subthemes"] if row["key"] == key)


def _find_parent(result: dict, theme: str) -> dict:
    return next(row for row in result["parents"] if row["theme"] == theme)


def test_strong_subtheme_is_visible_inside_flat_deduplicated_parent() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    # Compute cohort rises ~10.4% in five sessions; memory falls by the same amount.
    for ticker in ("A", "B", "C", "DUP"):
        panel.loc[idx[-6]:, ticker] = 100.0 * np.cumprod([1.0] + [1.02] * 5)
    for ticker in ("M1", "M2", "M3"):
        panel.loc[idx[-6]:, ticker] = 100.0 * np.cumprod([1.0] + [0.98] * 5)

    result = compute_early_leadership(_tree(), panel, _flat(idx))
    compute = _find(result, "semiscompute")
    parent = _find_parent(result, "Semiconductors")

    assert compute["horizons"]["5"]["return_pct"] > 9.0
    assert abs(parent["horizons"]["5"]["return_pct"]) < 2.0
    assert compute["horizons"]["5"]["rel_parent_pct"] > 7.0
    assert parent["population"]["configured_n"] == 10  # DUP counted once, not twice.
    assert parent["duplicate_members_collapsed"] == 1
    assert result["permissions"]["may_rank"] is False
    assert result["permissions"]["may_trade"] is False


def test_short_window_improvement_is_not_hidden_by_negative_long_window() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    # Long decline followed by a five-session rebound that still leaves 60d negative.
    r = [-0.006] * 84 + [0.025] * 5
    rebound = _series_from_returns(idx, r)
    for ticker in ("M1", "M2", "M3", "DUP"):
        panel[ticker] = rebound

    result = compute_early_leadership(_tree(), panel, _flat(idx))
    memory = _find(result, "semismemory")

    assert memory["horizons"]["5"]["rel_market_pct"] > 0
    assert memory["horizons"]["60"]["rel_market_pct"] < 0
    assert memory["strength"]["state"] == "short_leading_long_lagging"
    assert memory["persistence"]["state"] == "short_only"


def test_one_name_concentration_is_disclosed_not_mistaken_for_breadth() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    panel.loc[idx[-6]:, "A"] = 100.0 * np.cumprod([1.0] + [1.05] * 5)

    result = compute_early_leadership(_tree(), panel, _flat(idx))
    compute = _find(result, "semiscompute")
    h5 = compute["horizons"]["5"]

    assert h5["participation"]["up_fraction"] == 0.25
    assert h5["concentration"]["top_ticker"] == "A"
    assert h5["concentration"]["top_share"] > 0.95
    assert h5["concentration"]["concentrated"] is True


def test_sparse_listing_and_missing_endpoint_degrade_per_window_without_fill() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    panel.loc[idx[:-10], "S3"] = np.nan  # newly listed
    panel.loc[idx[-1], "S2"] = np.nan    # no exact close at as-of

    result = compute_early_leadership(_tree(), panel, _flat(idx))
    servers = _find(result, "hardwareservers")

    assert servers["population"]["observed_n"] == 3
    assert servers["population"]["status"] == "partial"
    assert servers["horizons"]["5"]["coverage"]["eligible_n"] == 3
    assert servers["horizons"]["60"]["coverage"]["eligible_n"] == 2
    assert servers["horizons"]["60"]["return_pct"] is None
    assert "INSUFFICIENT_HORIZON_COVERAGE" in servers["horizons"]["60"]["reason_codes"]


def test_provisional_terminal_bar_is_excluded_before_common_session_alignment() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    benchmark = _flat(idx)
    panel.loc[idx[-1], "A"] = 150.0

    result = compute_early_leadership(
        _tree(), panel, benchmark, provisional_dates=[idx[-1]],
    )

    assert result["asof"] == idx[-2].strftime("%Y-%m-%d")
    assert result["observation"]["excluded_provisional_dates"] == [idx[-1].strftime("%Y-%m-%d")]
    assert _find(result, "semiscompute")["horizons"]["1"]["return_pct"] == 0.0


def test_raw_split_candidate_is_excluded_and_receipted() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    panel.loc[idx[-4]:, "E1"] = 50.0  # raw 2-for-1-like discontinuity

    result = compute_early_leadership(
        _tree(), panel, _flat(idx), price_basis="raw_unadjusted_close",
    )
    equipment = _find(result, "semislithography")

    assert "E1" in result["data_quality"]["corporate_action_candidates"]
    assert "E1" in result["data_quality"]["excluded_unadjusted_candidates"]
    assert equipment["horizons"]["5"]["coverage"]["eligible_n"] == 2
    assert equipment["horizons"]["5"]["return_pct"] is None
    assert "INSUFFICIENT_HORIZON_COVERAGE" in equipment["horizons"]["5"]["reason_codes"]


def test_failed_breakout_cools_instead_of_remaining_reaccelerating() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    # Prior range around 100, then an attempted breakout to 112 and close back below 100.
    tail = [100.0] * 21 + [102.0, 108.0, 112.0, 104.0, 98.0]
    for ticker in ("O1", "O2", "O3"):
        panel.loc[idx[-26]:, ticker] = tail

    result = compute_early_leadership(_tree(), panel, _flat(idx))
    optics_proxy = _find(result, "hardwaretelecom")

    assert optics_proxy["breakout"]["attempted_n"] == 3
    assert optics_proxy["breakout"]["failed_n"] == 3
    assert optics_proxy["acceleration"]["state"] == "cooling_after_failed_breakout"
    assert "FAILED_BREAKOUT" in optics_proxy["acceleration"]["reason_codes"]


def test_membership_revision_is_current_snapshot_receipt_not_pit_claim() -> None:
    idx = _idx()
    revision = {
        "source": "data/themes_heatmap/themes_tree.json",
        "sha256": "abc123",
        "observed_at": "2026-09-19T22:30:00Z",
        "supersedes": "old456",
    }
    result = compute_early_leadership(
        _tree(), _base_panel(idx), _flat(idx), membership_revision=revision,
    )

    assert result["basis"]["membership"] == "current_tree_snapshot_not_historical_pit"
    assert result["membership_revision"] == revision
    assert result["basis"]["historical_membership_replay"] is False


def test_focus_coverage_declares_direct_proxy_and_unmapped_granularity() -> None:
    idx = _idx()
    result = compute_early_leadership(_tree(), _base_panel(idx), _flat(idx))
    coverage = {row["target_id"]: row for row in result["coverage"]}

    assert tuple(coverage) == COVERAGE_TARGET_IDS
    assert coverage["gpu_accelerators"]["mapped"] is True
    assert coverage["gpu_accelerators"]["source_nodes"][0]["relationship"] == "direct"
    assert coverage["hbm"]["source_nodes"][0]["relationship"] == "proxy"
    assert coverage["hbm"]["granularity_gap"] is not None
    assert coverage["equipment"]["eligible"] is True
    assert coverage["optics"]["source_nodes"][0]["relationship"] == "proxy"


def test_volume_and_reclaim_are_independent_optional_evidence() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    volume = pd.DataFrame(100.0, index=idx, columns=panel.columns)
    volume.loc[idx[-5]:, ["A", "B", "C", "DUP"]] = 200.0
    # All compute members reclaim their prior 20-session high at the close.
    panel.loc[idx[-1], ["A", "B", "C", "DUP"]] = 101.0

    result = compute_early_leadership(_tree(), panel, _flat(idx), volume_panel=volume)
    compute = _find(result, "semiscompute")

    assert math.isclose(compute["volume"]["median_5v20_ratio"], 2.0, rel_tol=1e-9)
    assert compute["volume"]["above_prior_average_fraction"] == 1.0
    assert compute["reclaim"]["reclaimed_20d_high_n"] == 4


def test_incumbent_rotation_owner_exposes_the_additive_entrypoint() -> None:
    import json
    from engine import subsector_rotation as owner

    idx = _idx()
    result = owner.compute_early_leadership(_tree(), _base_panel(idx), _flat(idx))
    assert result["schema"] == "subsector_rotation.early_leadership.v1"
    assert json.loads(json.dumps(result))["asof"] == idx[-1].strftime("%Y-%m-%d")


def test_unavailable_receipt_preserves_zero_authority() -> None:
    from engine import subsector_rotation as owner

    result = owner.unavailable_early_leadership("GROUP_READ_PLANE_UNAVAILABLE")
    assert result["status"] == "unavailable"
    assert result["reason_codes"] == ["GROUP_READ_PLANE_UNAVAILABLE"]
    assert not any(value for key, value in result["permissions"].items() if key.startswith("may_"))


def test_missing_holiday_row_keeps_session_windows_positional() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    benchmark = _flat(idx)
    # Simulate a market holiday / source calendar with no row at all.  Five sessions
    # still means five observed sessions, not five calendar dates or a filled phantom bar.
    missing = idx[-4]
    panel = panel.drop(index=missing)
    benchmark = benchmark.drop(index=missing)
    panel.loc[panel.index[-6]:, ["A", "B", "C", "DUP"]] = (
        100.0 * np.cumprod([1.0] + [1.01] * 5)
    )[:, None]

    result = compute_early_leadership(_tree(), panel, benchmark)
    compute = _find(result, "semiscompute")

    assert result["asof"] == panel.index[-1].strftime("%Y-%m-%d")
    assert compute["horizons"]["5"]["return_pct"] > 5.0
    assert missing.strftime("%Y-%m-%d") not in result["observation"].get(
        "excluded_provisional_dates", []
    )


def test_total_loss_return_does_not_emit_infinite_rs_slope() -> None:
    idx = _idx()
    panel = _base_panel(idx)
    panel.loc[idx[-1], ["A", "B", "C", "DUP"]] = 0.0

    result = compute_early_leadership(
        _tree(), panel, _flat(idx), price_basis="caller_supplied_adjusted_close",
    )
    compute = _find(result, "semiscompute")

    assert compute["rs_slope_pct_per_session"]["1"] is None
    assert compute["rs_slope_change_pct_per_session"]["1"] is None
