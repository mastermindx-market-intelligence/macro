"""Synthetic, pre-outcome acceptance tests proposed for options_history_retrospective.

The module under test is loaded under its eventual repository import name.  All
prices/panels are constructed in memory; this module never opens Theta data.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.research import options_history_retrospective as r


def _sessions(start: date, end: date) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(r.nyse_calendar.sessions_between(start, end))


def _prices(sessions: pd.DatetimeIndex, base: float = 100.0) -> pd.Series:
    return pd.Series(base + np.arange(len(sessions), dtype=float), index=sessions)


def _panel(
    calendar: pd.DatetimeIndex, root_number: int, horizon: int, *, constant_x=False
):
    # Five nonconstant cross-sectional observations yield a daily Spearman IC.
    x = (
        np.full(len(calendar), 1.0)
        if constant_x
        else np.arange(1, len(calendar) + 1, dtype=float) * (root_number + 1)
    )
    # Root order reverses on alternating days so HAC input is nonconstant.
    y = np.full(
        len(calendar), float(root_number if calendar[0].day % 2 else -root_number)
    )
    y = np.array(
        [root_number if i % 2 == 0 else -root_number for i in range(len(calendar))],
        dtype=float,
    )
    return pd.DataFrame(
        {
            "net_gamma_norm": x,
            "mom5": np.arange(1, len(calendar) + 1, dtype=float) * (root_number + 2),
            f"rv_{horizon}": y,
            f"excess_{horizon}": y,
            f"label_reason_{horizon}": [None] * len(calendar),
        },
        index=calendar,
    )


def _five_root_panels(calendar, horizon, *, constant_x=False):
    return {
        f"R{i}": _panel(calendar, i, horizon, constant_x=constant_x) for i in range(5)
    }


def test_calendar_hac_preserves_missing_calendar_positions():
    # v1.1: n=4 observed; zero residuals remain at the two absent calendar slots.
    got = r.calendar_hac([1.0, 2.0, np.nan, np.nan, 4.0, 3.0], h=1)
    assert got["reason"] is None
    assert got["lag"] == 2
    assert got["variance"] == pytest.approx(0.4375)
    assert got["df"] == 3


def test_effective_blocks_refuse_shared_forward_endpoint_overlap():
    calendar = _sessions(date(2020, 1, 2), date(2020, 2, 14))
    # t0 and t1 have overlapping [t+1, t+h] windows; t0 and t+h+1 do not.
    dates = [calendar[0], calendar[1], calendar[6]]
    assert r.effective_blocks(dates, h=5) == 2


def test_rank_ic_rejects_too_few_and_constant_cross_sections():
    assert (
        r.rank_ic(np.array([1.0, 2.0, 3.0, 4.0]), np.array([4.0, 3.0, 2.0, 1.0]))[2]
        == "INSUFFICIENT_ROOTS"
    )
    assert r.rank_ic(np.ones(5), np.arange(5.0, dtype=float))[2] == "CONSTANT_FEATURE"
    assert r.rank_ic(np.arange(5.0, dtype=float), np.ones(5))[2] == "CONSTANT_TARGET"


def test_label_requires_exact_root_and_spy_native_windows_and_valid_prices():
    sessions = _sessions(date(2020, 1, 2), date(2020, 2, 14))
    t, h = sessions[0], 5
    expected = sessions[1 : h + 2]
    root, spy = _prices(sessions), _prices(sessions, 200.0)
    ok = r.label_at(root, spy, t, h, expected[-1], expected)
    assert ok["reason"] is None
    assert np.isfinite(ok["excess"]) and np.isfinite(ok["rv"])
    assert (
        r.label_at(None, spy, t, h, expected[-1], expected)["reason"]
        == "ROOT_PRICE_UNAVAILABLE"
    )
    assert (
        r.label_at(root, None, t, h, expected[-1], expected)["reason"]
        == "SPY_PRICE_UNAVAILABLE"
    )

    assert (
        r.label_at(root.drop(expected[2]), spy, t, h, expected[-1], expected)["reason"]
        == "ROOT_NATIVE_SESSION_WINDOW_MISMATCH"
    )
    assert (
        r.label_at(root, spy.drop(expected[2]), t, h, expected[-1], expected)["reason"]
        == "SPY_NATIVE_SESSION_WINDOW_MISMATCH"
    )
    root_nan = root.copy()
    root_nan.loc[expected[2]] = np.nan
    assert (
        r.label_at(root_nan, spy, t, h, expected[-1], expected)["reason"]
        == "ROOT_INVALID_WINDOW_PRICE"
    )

    seam = root.copy()
    seam.loc[expected[1] :] *= 2.0
    assert (
        r.label_at(seam, spy, t, h, expected[-1], expected)["reason"]
        == "ROOT_SPLIT_SEAM"
    )
    assert (
        r.label_at(root, spy, t, h, expected[-2], expected)["reason"]
        == "ERA_BOUNDARY_PURGE"
    )


def test_d5_uses_exact_cross_year_nyse_session_and_does_not_bridge_missing_observation():
    calendar = _sessions(date(2019, 12, 16), date(2020, 1, 17))
    target = next(
        t
        for t in calendar
        if t.year == 2020 and r.nyse_calendar.session_n_back(t.date(), 5).year == 2019
    )
    back = pd.Timestamp(r.nyse_calendar.session_n_back(target.date(), 5))
    daily = pd.DataFrame(
        {
            "atm_iv": np.arange(len(calendar), dtype=float),
            "cw_ivspread": np.arange(len(calendar), dtype=float) / 10,
            "skew": np.arange(len(calendar), dtype=float) / 100,
            "oi_total": 100.0 + np.arange(len(calendar), dtype=float),
        },
        index=calendar,
    )
    prices = _prices(calendar)
    out = r.add_calendar_changes(daily, "R0", prices, calendar)
    position = calendar.get_loc(target)
    assert out.at[target, "d5_atm_iv"] == pytest.approx(5.0)
    assert out.at[target, "doi5"] == pytest.approx(5.0 / (100.0 + position - 5.0))

    missing = r.add_calendar_changes(daily.drop(back), "R0", prices, calendar)
    assert np.isnan(missing.at[target, "d5_atm_iv"])
    assert np.isnan(missing.at[target, "doi5"])


def test_non_evaluable_cells_never_emit_p_values_under_date_or_block_thresholds():
    contrast = "GEX_NORM_TO_FWD_RV"
    # Direct panels provide labels only; no market data or outcome computation is used.
    cal_125 = _sessions(date(2020, 1, 2), date(2020, 7, 31))[:125]
    era_125 = {"id": "E", "start": cal_125[0], "end": cal_125[-1]}
    result = r.evaluate_cell(
        _five_root_panels(cal_125, 5),
        [f"R{i}" for i in range(5)],
        cal_125,
        era_125,
        5,
        contrast,
    )
    assert result["reason"] == "INSUFFICIENT_IC_DATES"
    assert result["state"] == "NON_EVALUABLE" and result["raw_p"] is None

    cal_126 = _sessions(date(2020, 1, 2), date(2020, 9, 30))[:126]
    era_126 = {"id": "E", "start": cal_126[0], "end": cal_126[-1]}
    result = r.evaluate_cell(
        _five_root_panels(cal_126, 21),
        [f"R{i}" for i in range(5)],
        cal_126,
        era_126,
        21,
        contrast,
    )
    assert result["n_dates"] == 126
    assert result["reason"] == "INSUFFICIENT_NONOVERLAPPING_BLOCKS"
    assert result["effective_blocks"] < 30
    assert result["raw_p"] is None and result["bh_adj_p"] is None


def test_global_bh_uses_registered_60_slot_family_even_when_most_cells_are_sparse():
    # Only evaluable raw p-values enter BH; its denominator remains the frozen 60 slots.
    adjusted = r._bh_fdr({"one_evaluable_cell": 0.001}, k_family=60, alpha=0.10)
    row = adjusted["one_evaluable_cell"]
    assert row["rank"] == 1
    assert row["bh_adj_p"] == pytest.approx(0.060)
    assert row["reject_h0"] is True


def test_native_feature_schema_duplicates_empty_and_strict_delta():
    D = date(2024, 1, 2)
    E1 = date(2024, 2, 1)
    E2 = date(2024, 4, 1)
    rows = []
    for exp in (E1, E2):
        for strike in (95.0, 100.0, 105.0):
            for right, delta in (("C", 0.50), ("P", -0.25)):
                rows.append(
                    dict(
                        date=D,
                        expiration=exp,
                        strike=strike,
                        right=right,
                        underlying="QQQ",
                        bid=1.0,
                        ask=1.2,
                        implied_vol=0.20 + (right == "P") * 0.01,
                        underlying_price=100.0,
                        delta=delta,
                        gamma=0.01,
                        vanna=0.02,
                        charm=0.03,
                    )
                )
    g = pd.DataFrame(rows)
    o = g[["date", "expiration", "strike", "right", "underlying"]].copy()
    o["open_interest"] = 100.0
    daily, q = r.features_for_year(g, o, "QQQ", 2024)
    assert isinstance(daily.index, pd.DatetimeIndex) and len(daily) == 1
    assert (
        daily.loc[pd.Timestamp(D), "cw_ivspread"] is not None
        and daily.loc[pd.Timestamp(D), "skew"] is not None
    )
    assert (
        daily.loc[pd.Timestamp(D), "atm_iv"] is not None
        and daily.loc[pd.Timestamp(D), "oi_total"] == 1200.0
    )
    # Empty and OI-only, invalid dates, and remove-all duplicate policy.
    e, q = r.features_for_year(None, None, "QQQ", 2024)
    assert isinstance(e.index, pd.DatetimeIndex) and e.empty
    o2 = o.iloc[:1].copy()
    d2 = date(2024, 1, 3)
    o2["date"] = d2
    o2["expiration"] = E1
    d2f, q2 = r.features_for_year(None, o2, "QQQ", 2024)
    assert list(d2f.index) == [pd.Timestamp(d2)] and d2f.iloc[0].oi_total == 100.0
    bad = g.iloc[:1].copy()
    bad["date"] = "nonsense"
    _, qb = r.features_for_year(bad, o.iloc[:0].copy(), "QQQ", 2024)
    assert qb["counts"]["greeks_invalid_date_rows"] == 1
    dup = pd.concat([g.iloc[:1], g.iloc[:1]], ignore_index=True)
    _, qd = r.features_for_year(dup, o.iloc[:0].copy(), "QQQ", 2024)
    assert qd["counts"]["greeks_duplicate_rows_removed"] == 2
    # ATM admits finite delta .99; skew removes it, so strict skew refuses with no valid call.
    gatm = g.copy()
    gatm.loc[gatm.right.eq("C"), "delta"] = 0.99
    ad, _ = r.features_for_year(gatm, o, "QQQ", 2024)
    assert pd.notna(ad.iloc[0]["atm_iv"]) and pd.isna(ad.iloc[0]["skew"])

    # Manifest-native schema uses `root`, not the compatibility `underlying` alias.
    groot = g.rename(columns={"underlying": "root"})
    oroot = o.rename(columns={"underlying": "root"})
    root_daily, root_quality = r.features_for_year(groot, oroot, "QQQ", 2024)
    assert root_daily.iloc[0]["cw_ivspread"] == daily.iloc[0]["cw_ivspread"]
    assert root_quality["counts"]["joined_quote_excluded_rows"] == 0
    required_counters = {
        "greeks_raw_input_rows",
        "oi_raw_input_rows",
        "greeks_root_mismatch_rows",
        "oi_root_mismatch_rows",
        "greeks_invalid_date_rows",
        "oi_invalid_date_rows",
        "greeks_non_session_rows",
        "oi_non_session_rows",
        "greeks_invalid_identity_rows",
        "oi_invalid_identity_rows",
        "greeks_duplicate_rows_removed",
        "oi_duplicate_rows_removed",
        "greeks_valid_rows",
        "oi_valid_rows",
        "greeks_empty_input",
        "oi_empty_input",
        "oi_total_dates",
        "greeks_unmatched_rows",
        "oi_unmatched_rows",
        "joined_rows",
        "joined_quote_excluded_rows",
    }
    assert required_counters <= root_quality["counts"].keys()


def test_cw_uses_sum_of_call_put_oi_and_no_weight_fallback():
    day, expiry = date(2024, 1, 2), date(2024, 2, 1)
    rows = []
    oi_values = []
    for strike, p_iv, c_oi, p_oi in [
        (95.0, 0.21, 1.0, 100.0),
        (100.0, 0.22, 2.0, 2.0),
        (105.0, 0.25, 100.0, 1.0),
    ]:
        for right, iv, oi, delta in [("C", 0.20, c_oi, 0.5), ("P", p_iv, p_oi, -0.25)]:
            rows.append(
                dict(
                    root="QQQ",
                    date=day,
                    expiration=expiry,
                    strike=strike,
                    right=right,
                    bid=1.0,
                    ask=1.2,
                    implied_vol=iv,
                    underlying_price=100.0,
                    delta=delta,
                    gamma=0.01,
                    vanna=0.02,
                    charm=0.03,
                )
            )
            oi_values.append(oi)
    g = pd.DataFrame(rows)
    o = g[["root", "date", "expiration", "strike", "right"]].copy()
    o["open_interest"] = oi_values
    daily, _ = r.features_for_year(g, o, "QQQ", 2024)
    assert daily.iloc[0]["cw_ivspread"] == pytest.approx(-0.02981)
    o["open_interest"] = 0.0
    daily, _ = r.features_for_year(g, o, "QQQ", 2024)
    assert pd.isna(daily.iloc[0]["cw_ivspread"])


def test_unusable_quote_and_insufficient_greek_coverage_are_explicit():
    day, expiry = date(2024, 1, 2), date(2024, 2, 1)
    rows = [
        dict(
            root="QQQ",
            date=day,
            expiration=expiry,
            strike=95.0 + i,
            right=side,
            bid=1.0,
            ask=1.2,
            implied_vol=0.2,
            underlying_price=100.0,
            delta=0.5 if side == "C" else -0.5,
            gamma=0.01,
            vanna=0.02,
            charm=0.03,
        )
        for i in range(6)
        for side in ["C", "P"]
    ]
    g = pd.DataFrame(rows)
    o = g[["root", "date", "expiration", "strike", "right"]].copy()
    o["open_interest"] = 100.0
    g.loc[:1, "gamma"] = np.nan
    daily, q = r.features_for_year(g, o, "QQQ", 2024)
    assert daily.iloc[0]["net_gamma_norm_reason"] == "GAMMA_COVERAGE_LT_90"
    assert pd.isna(daily.iloc[0]["net_gamma_norm"])
    g["bid"] = 2.0
    daily, q = r.features_for_year(g, o, "QQQ", 2024)
    assert q["counts"]["joined_quote_excluded_rows"] == 12
    assert daily.iloc[0]["net_gamma_norm_reason"] == "NO_VALID_UNCROSSED_QUOTE"


def write_chain(path, root, day, oi_bump=0.0):
    (path / "greeks" / root).mkdir(parents=True, exist_ok=True)
    (path / "oi" / root).mkdir(parents=True, exist_ok=True)
    expiry = date(day.year, 2, 16)
    g = pd.DataFrame(
        {
            "root": [root, root],
            "date": [day, day],
            "expiration": [expiry, expiry],
            "strike": [100.0, 100.0],
            "right": ["C", "P"],
            "bid": [1.0, 1.0],
            "ask": [1.2, 1.2],
            "underlying_price": [100.0, 100.0],
            "implied_vol": [0.2, 0.22],
            "delta": [0.5, -0.5],
            "gamma": [0.01, 0.01],
            "vanna": [0.1, 0.1],
            "charm": [0.01, 0.01],
        }
    )
    o = g[["root", "date", "expiration", "strike", "right"]].copy()
    o["open_interest"] = [100.0 + oi_bump, 110.0]
    pq.write_table(
        pa.Table.from_pandas(g, preserve_index=False),
        path / "greeks" / root / f"{day.year}.parquet",
    )
    pq.write_table(
        pa.Table.from_pandas(o, preserve_index=False),
        path / "oi" / root / f"{day.year}.parquet",
    )


def write_prices(path, root, days):
    path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {"close": np.arange(100, 100 + len(days), dtype=float)},
        index=pd.DatetimeIndex(days),
    )
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=True), path / f"{root}.parquet"
    )


def expect(exc, fn):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


def test_manifest_binds_actual_inputs_and_all_60_sparse_cells(tmp_path):
    source = Path(r.__file__).resolve().parents[2]
    review = tmp_path / "source"
    for folder in ["engine", "lib"]:
        shutil.copytree(
            source / folder,
            review / folder,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    for relative in [
        "scripts/research/options_history_gauntlet.py",
        "scripts/research/options_history_retrospective.py",
        "config/ruling_graph.yml",
    ]:
        target = review / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    helper = review / "scripts/research/options_history_retrospective.py"
    protocol = (
        source
        / "research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json"
    )
    td = tmp_path
    store, prices, day = td / "theta", td / "yahoo", date(2017, 1, 3)
    write_chain(store, "QQQ", day)
    write_prices(prices, "QQQ", [day])
    write_prices(prices, "SPY", [day])
    manifest = r.prepare_manifest(store, prices, protocol, review)
    frozen = r.sha_bytes(r.canonical_bytes(manifest))
    assert manifest["expected_slot_count"] == 435 and len(manifest["entries"]) == 435
    assert sum(x["state"] == "missing" for x in manifest["entries"]) > 0
    r.verify_manifest(manifest, frozen, store, prices, protocol, review)
    g = pd.read_parquet(store / "greeks/QQQ/2017.parquet")
    o = pd.read_parquet(store / "oi/QQQ/2017.parquet")
    daily, receipt = r.features_for_year(g, o, "QQQ", 2017)
    assert len(daily) > 0 and any(
        np.isfinite(daily[c]).any()
        for c in ("net_gamma_norm", "net_vanna_norm", "net_charm_norm")
    )
    result = r.run_analysis(manifest, frozen, store, prices, protocol, review)
    assert (
        result["n_cells"] == 60
        and len(result["cells"]) == 60
        and all(c["state"] == "NON_EVALUABLE" for c in result["cells"])
    )
    expect(ValueError, lambda: r.canonical_bytes({"bad": float("nan")}))
    dup = dict(manifest)
    dup["entries"] = manifest["entries"] + [dict(manifest["entries"][0])]
    expect(
        ValueError,
        lambda: r.verify_manifest(
            dup, r.sha_bytes(r.canonical_bytes(dup)), store, prices, protocol, review
        ),
    )
    write_chain(store, "QQQ", day, oi_bump=1.0)
    expect(
        ValueError,
        lambda: r.verify_manifest(manifest, frozen, store, prices, protocol, review),
    )
    manifest = r.prepare_manifest(store, prices, protocol, review)
    frozen = r.sha_bytes(r.canonical_bytes(manifest))
    write_chain(store, "ARKK", day)
    expect(
        ValueError,
        lambda: r.verify_manifest(manifest, frozen, store, prices, protocol, review),
    )
    manifest = r.prepare_manifest(store, prices, protocol, review)
    frozen = r.sha_bytes(r.canonical_bytes(manifest))
    helper.write_bytes(helper.read_bytes() + b"\n# synthetic source mutation\n")
    expect(
        ValueError,
        lambda: r.verify_manifest(manifest, frozen, store, prices, protocol, review),
    )
    out = td / "report.json"
    r.write_artifact(out, r.canonical_bytes({"ok": True}), [store, prices, review])
    expect(
        FileExistsError, lambda: r.write_artifact(out, b"{}", [store, prices, review])
    )
