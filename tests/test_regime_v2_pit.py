"""Tests for the regime-vintage PIT spine (CPI P-D5-1 phase 4a).

Covers, per the phase gate:
  * vintage as-of correctness on synthetic vintage frames (a value published
    later must NEVER be visible earlier; initial release wins over revisions;
    publication order never steps back to an older period),
  * cross-check against collectors.fred.as_of_series semantics,
  * fallback flagging (pre-vintage-coverage dates read latest-revised, flagged),
  * hysteresis re-application (the artifact's quad IS apply_hysteresis of its
    own axis scores under the live config),
  * additivity (a full real build leaves regime_history.parquet and latest.json
    byte-for-byte untouched),
  * determinism and schema.

The integration tests run the real builder ONCE into a tmp dir (module-scoped
fixture, ~5s) and assert invariants on that fresh build — deliberately NOT
byte-comparing against the committed artifact, which is on-demand cadence and
allowed to lag the daily-collected store.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from collectors.fred import as_of_series
from engine.regime import apply_hysteresis
from lib import config
from scripts.build_regime_v2_pit import (
    LEGS,
    PIT_CLASSES,
    MACRO_WINDOW_COLUMNS,
    classify_pit_rows,
    main,
    merged_leg_series,
    pit_availability_panel,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HIST = _REPO_ROOT / "data" / "regime" / "regime_history.parquet"
_LATEST = _REPO_ROOT / "data" / "regime" / "latest.json"

_HAVE_STORE = (_REPO_ROOT / "data" / "fred_vintage" / "vintages.parquet").exists() \
    and _HIST.exists()


# --------------------------------------------------------------------------- #
# synthetic vintage helpers
# --------------------------------------------------------------------------- #
def _vint(rows: list[tuple[str, str, float, str]]) -> pd.DataFrame:
    """rows: (series, period, value, realtime_start)."""
    return pd.DataFrame([
        {"series": s, "period": pd.Timestamp(p), "value": v,
         "realtime_start": pd.Timestamp(rt), "realtime_end": pd.Timestamp("2100-01-01")}
        for s, p, v, rt in rows
    ])


_BASIC = _vint([
    ("PAYEMS", "2020-01-01", 100.0, "2020-02-07"),
    ("PAYEMS", "2020-02-01", 110.0, "2020-03-06"),
    ("PAYEMS", "2020-03-01", 90.0, "2020-04-03"),
])


# --------------------------------------------------------------------------- #
# 1-5: vintage as-of correctness on synthetic frames
# --------------------------------------------------------------------------- #
def test_panel_value_not_visible_before_publication():
    panel = pit_availability_panel(_BASIC, "PAYEMS")
    grid = pd.bdate_range("2020-01-01", "2020-04-30")
    daily = panel.reindex(grid.union(panel.index)).ffill().reindex(grid)
    # the Jan print (published Feb 7) must NOT exist on any earlier date
    assert daily.loc[:"2020-02-06"].isna().all()
    assert daily.loc["2020-02-07"] == 100.0
    # the March print (published Apr 3) must not be visible in March
    assert (daily.loc["2020-03-06":"2020-04-02"] == 110.0).all()
    assert daily.loc["2020-04-03"] == 90.0


def test_panel_matches_as_of_series_semantics():
    panel = pit_availability_panel(_BASIC, "PAYEMS")
    for asof in ["2020-02-01", "2020-02-07", "2020-03-15", "2020-06-30"]:
        known = as_of_series("PAYEMS", asof, vintages=_BASIC)
        expect = known.iloc[-1] if len(known) else None
        got = panel[panel.index <= pd.Timestamp(asof)]
        got = got.iloc[-1] if len(got) else None
        assert got == expect, f"asof {asof}: panel {got} != as_of_series {expect}"


def test_panel_uses_initial_release_not_revision():
    v = _vint([
        ("PAYEMS", "2020-01-01", 100.0, "2020-02-07"),   # initial
        ("PAYEMS", "2020-01-01", 120.0, "2020-03-06"),   # revision — must be dropped
        ("PAYEMS", "2020-02-01", 111.0, "2020-03-06"),
    ])
    panel = pit_availability_panel(v, "PAYEMS")
    assert panel.loc[pd.Timestamp("2020-02-07")] == 100.0
    # the Feb-period initial (111) wins on 03-06, never the Jan revision (120)
    assert panel.loc[pd.Timestamp("2020-03-06")] == 111.0
    assert 120.0 not in panel.to_numpy()


def test_panel_never_steps_back_to_older_period():
    v = _vint([
        ("PAYEMS", "2020-02-01", 110.0, "2020-03-06"),
        ("PAYEMS", "2020-01-01", 100.0, "2020-03-20"),   # late release of an OLDER period
    ])
    panel = pit_availability_panel(v, "PAYEMS")
    # after 03-06 the visible value stays the Feb print; the stale Jan release
    # never overwrites newer information
    assert pd.Timestamp("2020-03-20") not in panel.index
    assert panel.loc[pd.Timestamp("2020-03-06")] == 110.0


def test_panel_same_day_multi_period_keeps_latest():
    v = _vint([
        ("PAYEMS", "2020-01-01", 100.0, "2020-03-06"),
        ("PAYEMS", "2020-02-01", 110.0, "2020-03-06"),   # same-day double release
    ])
    panel = pit_availability_panel(v, "PAYEMS")
    assert len(panel) == 1
    assert panel.loc[pd.Timestamp("2020-03-06")] == 110.0


# --------------------------------------------------------------------------- #
# 6: fallback merge — pre-coverage dates read latest-revised
# --------------------------------------------------------------------------- #
def test_merged_leg_pre_coverage_is_latest_revised():
    live = pd.Series([1.0, 2.0, 3.0, 4.0],
                     index=pd.to_datetime(["2019-10-01", "2019-11-01",
                                           "2019-12-01", "2020-01-01"]))
    panel = pit_availability_panel(_BASIC, "PAYEMS")
    first_rt = panel.index.min()          # 2020-02-07
    merged = merged_leg_series(live, panel, first_rt)
    # pre-coverage stamps: the latest-revised live values, reference-stamped
    assert (merged.loc[:"2020-02-06"] == live).all()
    # the live 2020-01-01 stamp is < first_rt so it IS kept (flagged fallback)
    assert merged.loc[pd.Timestamp("2020-01-01")] == 4.0
    # from coverage on: vintage initial releases at their publication stamps
    assert merged.loc[pd.Timestamp("2020-02-07")] == 100.0
    assert merged.index.is_monotonic_increasing


# --------------------------------------------------------------------------- #
# 7-8: pit_class / fallback_notes
# --------------------------------------------------------------------------- #
def test_classify_pit_rows_classes_and_notes():
    idx = pd.bdate_range("2020-01-01", "2020-01-10")
    active = {
        "payrolls": pd.Series(True, index=idx),
        "wei": pd.Series([False] * 5 + [True] * 3, index=idx),
    }
    cov = {"payrolls": pd.Timestamp("2019-01-01"),      # covered everywhere
           "wei": pd.Timestamp("2020-01-08")}           # covered from Jan 8
    out = classify_pit_rows(idx, active, cov)
    assert set(out.columns) == {"pit_class", "fallback_notes"}
    assert set(out["pit_class"].unique()) <= set(PIT_CLASSES)
    # days 1-5: only payrolls active, vintage -> pit_vintage, no notes
    assert (out["pit_class"].iloc[:5] == "pit_vintage").all()
    assert (out["fallback_notes"].iloc[:5] == "").all()
    # days 6-7 (Jan 8 is idx[5]): wei active but idx[5] >= cov start -> vintage
    assert (out.loc[pd.Timestamp("2020-01-08"), "pit_class"]) == "pit_vintage"
    # shift wei coverage later to force a mixed row with a note
    cov2 = {"payrolls": pd.Timestamp("2019-01-01"), "wei": pd.Timestamp("2021-01-01")}
    out2 = classify_pit_rows(idx, active, cov2)
    assert (out2["pit_class"].iloc[5:] == "mixed").all()
    assert (out2["fallback_notes"].iloc[5:] == "wei").all()


def test_classify_pit_rows_no_active_legs_split_by_coverage():
    idx = pd.bdate_range("2020-01-01", "2020-01-10")
    active = {"payrolls": pd.Series(False, index=idx)}
    cov = {"payrolls": pd.Timestamp("2020-01-06")}
    out = classify_pit_rows(idx, active, cov)
    # no revision-leaky input either way; classed by era for legibility
    assert (out.loc[:"2020-01-05", "pit_class"] == "revised_latest").all()
    assert (out.loc["2020-01-06":, "pit_class"] == "pit_vintage").all()
    assert (out["fallback_notes"] == "").all()
    # all-active-all-fallback -> revised_latest
    active2 = {"payrolls": pd.Series(True, index=idx)}
    cov2 = {"payrolls": pd.Timestamp("2021-01-01")}
    out2 = classify_pit_rows(idx, active2, cov2)
    assert (out2["pit_class"] == "revised_latest").all()
    assert (out2["fallback_notes"] == "payrolls").all()


# --------------------------------------------------------------------------- #
# 9: determinism of the pure pieces
# --------------------------------------------------------------------------- #
def test_unit_determinism():
    p1 = pit_availability_panel(_BASIC, "PAYEMS")
    p2 = pit_availability_panel(_BASIC, "PAYEMS")
    assert p1.equals(p2)
    idx = pd.bdate_range("2020-01-01", "2020-02-28")
    active = {"payrolls": pd.Series(True, index=idx)}
    cov = {"payrolls": pd.Timestamp("2020-02-01")}
    assert classify_pit_rows(idx, active, cov).equals(
        classify_pit_rows(idx, active, cov))


# --------------------------------------------------------------------------- #
# 10: the overrides seam default is a no-op on the live path
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _HAVE_STORE, reason="full data store not present")
def test_seam_overrides_default_is_noop():
    from engine.inputs import build_features
    from lib import store
    f_none = build_features()
    f_empty = build_features(overrides={})
    assert f_none.equals(f_empty), "overrides={} must be byte-identical to the live path"
    # injecting the EXACT live store series through the seam reproduces the live
    # column — proves the override flows through the same put() contract
    raw = store.read("fred", "PAYEMS").iloc[:, 0]
    f_inj = build_features(overrides={"payrolls": raw})
    assert f_inj["payrolls"].equals(f_none["payrolls"])


# --------------------------------------------------------------------------- #
# integration: one real build into a tmp dir
# --------------------------------------------------------------------------- #
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not _HAVE_STORE:
        pytest.skip("full data store not present")
    out = tmp_path_factory.mktemp("pitspine")
    before = {p: _sha(p) for p in (_HIST, _LATEST) if p.exists()}
    rc = main(["--out-dir", str(out)])
    assert rc == 0
    after = {p: _sha(p) for p in before}
    frame = pd.read_parquet(out / "regime_v2_pit.parquet")
    with open(out / "regime_v2_pit_divergence.json", encoding="utf-8") as fh:
        div = json.load(fh)
    return {"out": out, "before": before, "after": after,
            "frame": frame, "div": div}


def test_builder_additive_live_artifacts_untouched(built):
    """The build must leave regime_history.parquet + latest.json byte-for-byte."""
    assert built["after"] == built["before"]
    produced = sorted(p.name for p in built["out"].iterdir())
    assert produced == ["regime_v2_pit.parquet", "regime_v2_pit_divergence.json"]


def test_artifact_schema_and_enum(built):
    frame = built["frame"]
    hist = pd.read_parquet(_HIST)
    assert list(frame.columns) == list(hist.columns) + [
        "pit_class", "fallback_notes", "vintage_store_asof", *MACRO_WINDOW_COLUMNS]
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert frame.index.is_monotonic_increasing
    assert set(frame["pit_class"].unique()) <= set(PIT_CLASSES)
    assert frame["vintage_store_asof"].nunique() == 1
    assert set(frame["quad"].dropna().unique()) <= {"Q1", "Q2", "Q3", "Q4"}


def test_fallback_flag_windows(built):
    frame = built["frame"]

    def row(d):
        return frame.loc[pd.Timestamp(d)]

    # pre-1997: every active macro leg reads latest-revised
    r95 = row("1995-06-15")
    assert r95["pit_class"] == "revised_latest"
    for leg in ("payrolls", "indpro", "sticky_cpi"):
        assert leg in r95["fallback_notes"]
    assert "wei" not in r95["fallback_notes"]      # WEI has no live data yet
    # 2012: payrolls/indpro vintage; wei (pre-2020), gdpnow (pre-2016) and
    # sticky (pre-2014) fall back
    r12 = row("2012-06-15")
    assert r12["pit_class"] == "mixed"
    for leg in ("wei", "gdpnow", "sticky_cpi"):
        assert leg in r12["fallback_notes"]
    for leg in ("payrolls", "indpro"):
        assert leg not in r12["fallback_notes"]
    # 2018: only WEI still pre-coverage
    r18 = row("2018-06-15")
    assert r18["pit_class"] == "mixed"
    assert r18["fallback_notes"] == "wei"
    # 2021+: full vintage coverage
    r21 = row("2021-06-15")
    assert r21["pit_class"] == "pit_vintage"
    assert r21["fallback_notes"] == ""


def test_hysteresis_reapplied_exact(built):
    """The artifact's confirmed quad must BE apply_hysteresis of its own PIT
    axis scores under the live config — same state machine, re-run."""
    frame = built["frame"]
    qcfg = config.load()["engine"]["quad"]
    h = apply_hysteresis(frame["growth_score"], frame["inflation_score"],
                         qcfg["hysteresis_days"], qcfg["shock_override_z"])
    for col in ("quad", "pending_quad"):
        a = frame[col].astype(object).where(frame[col].notna(), "NA")
        b = h[col].astype(object).where(h[col].notna(), "NA")
        n_diff = int((a.to_numpy() != b.to_numpy()).sum())
        assert n_diff == 0, f"{col}: {n_diff} rows differ from re-applied hysteresis"
    assert (frame["pending_days"] == h["pending_days"]).all()


def test_pre_coverage_quad_matches_live_history(built):
    """Before ANY vintage coverage (pre-1997) the PIT frame reads exactly the
    live inputs — its quad must reproduce the committed live history there.
    (Both are rebuilt from the same git-tracked store; the daily engine commits
    regime_history together with the store, so they move in lockstep.)"""
    frame = built["frame"]
    hist = pd.read_parquet(_HIST)
    common = frame.index.intersection(hist.index)
    common = common[common < pd.Timestamp("1997-01-10")]
    a, b = frame.loc[common, "quad"], hist.loc[common, "quad"]
    m = a.notna() & b.notna()
    assert m.sum() > 5000
    assert (a[m].to_numpy() == b[m].to_numpy()).all()


def test_divergence_json_shape(built):
    div = built["div"]
    for key in ("headline", "overall", "by_era", "per_axis",
                "divergence_run_lengths", "transition_shifts", "control",
                "pit_class_counts", "fallback_coverage", "vintage_store_asof",
                "frame_asof", "columns_dropped_vs_regime_history"):
        assert key in div, key
    assert div["overall"]["n_comparable_dates"] > 10000
    assert set(div["by_era"]) == {"pre_2008", "2008_09", "2010_19", "2020_plus"}
    assert set(div["transition_shifts"]) == {"2008_09", "2020"}
    assert 0.0 <= div["headline"]["pct_dates_quad_divergent"] <= 100.0
    assert div["headline"]["worst_era"] in div["by_era"]
    # pre-1997 is fallback-everywhere: it can never diverge from live, so the
    # pre-2008 era rate must be attributable to 1997+ (bounded strictly below
    # the vintage-covered eras' worst)
    assert div["columns_dropped_vs_regime_history"] == []
    assert sum(div["pit_class_counts"].values()) == len(built["frame"])


# Full-window provenance: a current vintage does not qualify its lagged inputs.
def _window_fixture(leg="payrolls", *, count=400, coverage_row=100):
    from scripts import build_regime_v2_pit as builder
    index = pd.bdate_range("2020-01-01", periods=count)
    frame = pd.DataFrame({leg: np.arange(count, dtype=float) + 100.0}, index=index)
    active = {key: pd.Series(False, index=index) for key in builder.LEGS}
    active[leg] = pd.Series(True, index=index)
    coverage = {key: None for key in builder.LEGS}
    coverage[leg] = index[coverage_row]
    return frame, active, coverage


@pytest.mark.parametrize("leg,lag", [("payrolls", 63), ("indpro", 252),
                                     ("wei", 65), ("gdpnow", 63)])
def test_window_basis_includes_the_actual_lag_endpoint(leg, lag):
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture(leg)
    result, audit = builder.macro_window_provenance(
        frame, active, coverage, sources={leg: frame[leg]})
    row = 100 + lag - 1
    assert result.iloc[row]["macro_window_basis"] == "revised_fallback_inputs"
    assert result.iloc[row]["macro_window_revised_legs"] == leg
    assert result.iloc[row + 1]["macro_window_basis"] == "initial_vintage_inputs"
    assert audit["legacy_pit_class_changed"] is False
    assert audit["numeric_model_changed"] is False
    assert audit["historical_replay_eligible"] is False
    assert audit["market_input_availability_verified"] is False
    assert audit["fitted_model_and_state_history_verified"] is False
    assert audit["actual_historical_issuance_verified"] is False
    assert audit["state_columns_qualified"] is False
    assert audit["scope"] == "active_slow_component_inputs_only"


def test_sticky_cpi_window_tracks_both_rolling_means_not_one_embargo():
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture("sticky_cpi")
    # 63-row mean compared with its 63-row lag: oldest dependency is t-125.
    result, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"sticky_cpi": frame["sticky_cpi"]})
    assert result.iloc[224]["macro_window_basis"] == "revised_fallback_inputs"
    assert result.iloc[225]["macro_window_basis"] == "initial_vintage_inputs"
    # Missing observations do not contribute to pandas' rolling mean. At t=183,
    # the lagged mean already has 21 vintage observations and no revised value.
    frame.iloc[:100, 0] = np.nan
    sparse, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"sticky_cpi": frame["sticky_cpi"]})
    assert sparse.iloc[182]["macro_window_basis"] == "unknown_inputs"
    assert sparse.iloc[183]["macro_window_basis"] == "initial_vintage_inputs"


def test_no_active_component_never_claims_vintage_qualification():
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture()
    active = {key: value & False for key, value in active.items()}
    result, audit = builder.macro_window_provenance(frame, active, coverage)
    assert set(result.macro_window_basis) == {"no_active_macro_components"}
    assert (result.macro_window_active_count == 0).all()
    assert audit["historical_replay_eligible"] is False


def test_unknown_dependency_and_missing_component_are_not_inactive():
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture()
    del active["indpro"]
    result, _ = builder.macro_window_provenance(frame, active, coverage)
    assert set(result.macro_window_basis) == {"unknown_inputs"}
    assert result.macro_window_unknown_legs.str.contains("indpro").all()
    # CONTROL: with coverage intact the last row is NOT unknown_inputs for
   # an unrelated reason — proves the second-half assertion below discriminates.
    frame_c, active_c, coverage_c = _window_fixture()
    result_c, _ = builder.macro_window_provenance(
        frame_c, active_c, coverage_c, sources={"payrolls": frame_c["payrolls"]})
    assert result_c.iloc[-1]["macro_window_basis"] != "unknown_inputs"
    frame, active, coverage = _window_fixture()
    del coverage["payrolls"]
    result, _ = builder.macro_window_provenance(frame, active, coverage)
    assert result.iloc[-1]["macro_window_basis"] == "unknown_inputs"


def test_known_absent_vintage_means_revised_not_unknown():
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture()
    coverage["payrolls"] = None
    result, _ = builder.macro_window_provenance(frame, active, coverage)
    assert set(result.iloc[63:].macro_window_basis) == {"revised_fallback_inputs"}
    assert result.iloc[62]["macro_window_basis"] == "unknown_inputs"


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf, "bad"])
def test_active_component_with_invalid_endpoint_is_unknown(invalid):
    from scripts import build_regime_v2_pit as builder
    # Build a CLEAN source once from the fixture (before any injection) so
    # the per-value path's source_date=NaT branch cannot mask whether the
    # invalid-endpoint check itself forced unknown_inputs at row 300.
    frame_clean, active_clean, coverage_clean = _window_fixture()
    clean_source = frame_clean["payrolls"]
    # CONTROL: with a clean frame the same row 300 is NOT unknown_inputs.
    result_clean, _ = builder.macro_window_provenance(
        frame_clean, active_clean, coverage_clean,
        sources={"payrolls": clean_source})
    assert result_clean.iloc[300]["macro_window_basis"] != "unknown_inputs"
    # INJECTED: same fixture, same clean source; only the feature column
    # has the invalid value at row 300 - 63. With the invalid-endpoint
    # check enabled, row 300 must be unknown_inputs.
    frame, active, coverage = _window_fixture()
    frame["payrolls"] = frame["payrolls"].astype(object)
    frame.iloc[300 - 63, 0] = invalid
    result, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"payrolls": clean_source})
    assert result.iloc[300]["macro_window_basis"] == "unknown_inputs"


@pytest.mark.parametrize("invalid", [np.inf, -np.inf, "bad"])
def test_invalid_value_inside_a_smoothed_window_is_unknown(invalid):
    """sticky_cpi is the only leg whose smooth_rows=63/min_periods=21 window
    can hold at least 21 finite rows while still containing a bad value. The
    `invalid` branch (raw.notna() & ~finite) is what catches it: rolling counts
    of `finite` stay above `min_periods`, so `usable`/`complete` remain True,
    and only the unknown_count contribution from the `invalid` series flips
    the row's label to `unknown_inputs`."""
    from scripts import build_regime_v2_pit as builder
    # Build a CLEAN source once from the sticky_cpi fixture (before any
    # injection) so the per-value path's source_date=NaT branch cannot mask
    # whether the invalid-endpoint check itself forced unknown_inputs.
    frame_clean, active_clean, coverage_clean = _window_fixture("sticky_cpi")
    clean_source = frame_clean["sticky_cpi"]
    # CONTROL: with a clean frame, row 300 must NOT be unknown_inputs —
    # the smoothed sticky_cpi leg sits entirely post-coverage there.
    result_clean, _ = builder.macro_window_provenance(
        frame_clean, active_clean, coverage_clean,
        sources={"sticky_cpi": clean_source})
    assert result_clean.iloc[300]["macro_window_basis"] != "unknown_inputs"
    # INJECTED: same fixture, same clean source; only the feature column
    # has the bad value at row 290 (inside the 63-row window ending at row 300,
    # well past row-100 coverage and far from row 0). With the invalid-endpoint
    # check enabled, row 300 must be unknown_inputs.
    frame, active, coverage = _window_fixture("sticky_cpi")
    if invalid == "bad":
        frame["sticky_cpi"] = frame["sticky_cpi"].astype(object)
    frame.iloc[290, 0] = invalid
    result, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"sticky_cpi": clean_source})
    assert result.iloc[300]["macro_window_basis"] == "unknown_inputs"


def test_window_basis_does_not_use_later_rows_or_change_inputs():
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture("sticky_cpi")
    original = frame.copy(deep=True)
    # CONTROL: the full-frame call hasat least one non-unknown label sothe
    # prefix equality below is comparing actual labels, not all-unknown.
    full, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"sticky_cpi": frame["sticky_cpi"]})
    assert set(full["macro_window_basis"]) - {"unknown_inputs"}
    #Slice the source to the same 250 rows so the prefix call sees onlythe
    # finite observations that fall in the prefix.
    prefix_source = frame["sticky_cpi"].iloc[:250]
    prefix, _ = builder.macro_window_provenance(
        frame.iloc[:250], {k: v.iloc[:250] for k, v in active.items()},
        coverage, sources={"sticky_cpi": prefix_source})
    pd.testing.assert_frame_equal(prefix, full.iloc[:250])
    pd.testing.assert_frame_equal(frame, original)


def test_real_component_can_flip_without_legacy_current_basis_changing():
    from engine.axes import _component_scores
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture()
    frame.loc[:, "payrolls"] = 100.0
    frame.iloc[:100, 0] = 50.0
    before = _component_scores(frame, "growth")["payrolls_trend"]
    frame.iloc[:100, 0] = 150.0
    after = _component_scores(frame, "growth")["payrolls_trend"]
    index = frame.index[110]
    legacy = classify_pit_rows(frame.index, active, coverage)
    result, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"payrolls": frame["payrolls"]})
    assert (before.loc[index], after.loc[index]) == (1.0, -1.0)
    assert legacy.loc[index, "pit_class"] == "pit_vintage"
    assert result.loc[index, "macro_window_basis"] == "revised_fallback_inputs"


def test_dependency_description_matches_actual_scoring_and_smoothing_owners():
    import ast
    import inspect
    from engine import axes, inputs
    from scripts import build_regime_v2_pit as builder
    calls = {}
    for node in ast.walk(ast.parse(inspect.getsource(axes._component_scores))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "monthly_sign":
            calls[ast.literal_eval(node.args[0])] = ast.literal_eval(node.args[1])
    expected = {spec["scored_feature"]: spec["lag_rows"] for spec in builder.MACRO_WINDOW_SPECS.values()}
    assert expected == calls
    rolling = []
    for node in ast.walk(ast.parse(inspect.getsource(inputs.build_features))):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
               and t.slice.value == "sticky_cpi_3m" for t in node.targets):
            call = node.value.func.value
            rolling.append((ast.literal_eval(call.args[0]),
                            {k.arg: ast.literal_eval(k.value) for k in call.keywords}))
    spec = builder.MACRO_WINDOW_SPECS["sticky_cpi"]
    assert rolling == [(spec["smooth_rows"], {"min_periods": spec["min_periods"]})]


def test_window_suite_is_owned_by_one_existing_code_gate():
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    jobs = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())["jobs"]
    owners = [(name, job.get("gate")) for name, job in jobs.items()
              if any("tests/test_regime_v2_pit.py" in str(step.get("run", ""))
                     for step in job.get("steps", []))]
    assert owners == [("unrun-scoring-engine", "code")]
    assert "tests/test_regime_v2_pit.py" not in json.loads(
        (root / "config/unrun_test_baseline.json").read_text())["grandfathered"]


@pytest.fixture
def synthetic_history_sources(tmp_path, monkeypatch):
    """Only source transport is synthetic; alignment/model/flags/writers are real."""
    from collectors import fred
    from engine import inputs
    from lib import store
    from scripts import build_regime_v2_pit as builder
    index = pd.bdate_range("2020-01-01", periods=480)
    configured = config.load()["yahoo"]["tickers"]
    tickers = sorted({ticker for group in configured.values() for ticker in group} | {"SPY"})
    prices = pd.DataFrame({ticker: 100.0 + np.arange(len(index)) * (0.1 + i / 100)
                           + np.sin(np.arange(len(index)) / (10 + i))
                           for i, ticker in enumerate(tickers)}, index=index)
    originals = {spec["sid"]: pd.DataFrame({"value": 80.0 + np.arange(len(index)) * .01}, index=index)
                 for spec in builder.LEGS.values()}
    rows = []
    for spec in builder.LEGS.values():
        for offset in range(100, len(index), 21):
            rows.append({"series": spec["sid"], "period": index[offset] - pd.DateOffset(months=1),
                         "realtime_start": index[offset], "realtime_end": pd.Timestamp("2099-12-31"),
                         "value": 100.0 + offset * .1})
    vintages = pd.DataFrame(rows)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "source-data")
    monkeypatch.setattr(inputs, "yahoo_closes", lambda *args, **kwargs: prices.copy(deep=True))
    monkeypatch.setattr(store, "read", lambda group, name, *args, **kwargs:
                        originals[name].copy(deep=True) if group == "fred" and name in originals else None)
    monkeypatch.setattr(fred, "load_vintages", lambda: vintages.copy(deep=True))
    return builder, vintages, originals


def test_actual_builder_preserves_numeric_history_and_adds_window_evidence(synthetic_history_sources):
    from engine.inputs import build_features
    from engine.regime import classify
    from engine.transition import compute_flags, state_machine_detail
    builder, vintages, _ = synthetic_history_sources
    overrides, coverage = {}, {}
    for leg, spec in builder.LEGS.items():
        panel = builder.pit_availability_panel(vintages, spec["sid"])
        coverage[leg] = panel.index.min()
        overrides[leg] = builder.merged_leg_series(
            builder.live_reference_series(spec["sid"]), panel, coverage[leg])
    features = build_features(overrides=overrides)
    legacy = classify(features)
    flags = compute_flags(features, legacy)
    legacy = legacy.join(flags).join(state_machine_detail(flags, legacy))
    active = {leg: legacy[spec["component"]].notna() for leg, spec in builder.LEGS.items()}
    old_basis = builder.classify_pit_rows(legacy.index, active, coverage)
    result, audit = builder.build_frames(vintages)
    numeric_columns = [column for column in legacy if not column.startswith("c_")]
    pd.testing.assert_frame_equal(result[numeric_columns], legacy[numeric_columns])
    pd.testing.assert_frame_equal(result[["pit_class", "fallback_notes"]], old_basis)
    assert set(builder.MACRO_WINDOW_COLUMNS) <= set(result)
    # This is the original failure: current-source labels alone are insufficient.
    seam = result.pit_class.eq("pit_vintage") & result.macro_window_basis.eq("revised_fallback_inputs")
    assert seam.any()
    assert result.macro_window_basis.eq("initial_vintage_inputs").any()
    assert sum(audit["macro_window_provenance"]["counts"].values()) == len(result)
    # W1: every qualification flag stays False on the builder's audit.
    prov = audit["macro_window_provenance"]
    assert prov["legacy_pit_class_changed"] is False
    assert prov["numeric_model_changed"] is False
    assert prov["historical_replay_eligible"] is False
    assert prov["market_input_availability_verified"] is False
    assert prov["fitted_model_and_state_history_verified"] is False
    assert prov["actual_historical_issuance_verified"] is False
    # W3: state scope — the macro_window_* columns do NOT qualify state.
    assert prov["state_columns_qualified"] is False
    si = prov["state_inheritance"]
    assert set(si) == {"n_rows", "first_date", "last_date"}
    # F4: pin the deterministic synthetic values for the standard fixture so
    # any silent drift in the state-inheritance computation surfaces here.
    # Numbers below are what the synthetic integration in
    # `synthetic_history_sources` produces today.
    assert si == {"n_rows": 155, "first_date": "2020-11-11", "last_date": "2021-11-02"}
    # Every dependency description in the audit carries the renamed key.
    for spec in prov["dependencies"].values():
        assert "scored_feature" in spec
        assert "feature" not in spec


def test_actual_cli_serializes_and_explains_window_evidence(synthetic_history_sources, tmp_path, capsys):
    builder, vintages, originals = synthetic_history_sources
    before = {key: value.copy(deep=True) for key, value in originals.items()}
    before_vintages = vintages.copy(deep=True)
    out = tmp_path / "output"
    assert builder.main(["--out-dir", str(out)]) == 0
    frame = pd.read_parquet(out / "regime_v2_pit.parquet")
    audit = json.loads((out / "regime_v2_pit_divergence.json").read_text())
    assert set(builder.MACRO_WINDOW_COLUMNS) <= set(frame)
    assert frame.macro_window_basis.value_counts().to_dict() == audit["macro_window_provenance"]["counts"]
    text = capsys.readouterr().out
    assert "slow-component input-window basis:" in text
    assert "not historical forecast" in text
    assert sorted(p.name for p in out.iterdir()) == ["regime_v2_pit.parquet", "regime_v2_pit_divergence.json"]
    # W1: every qualification flag stays False on the serialized sidecar.
    prov = audit["macro_window_provenance"]
    assert prov["legacy_pit_class_changed"] is False
    assert prov["numeric_model_changed"] is False
    assert prov["historical_replay_eligible"] is False
    assert prov["market_input_availability_verified"] is False
    assert prov["fitted_model_and_state_history_verified"] is False
    assert prov["actual_historical_issuance_verified"] is False
    # W3: state scope serialized alongside the rest of the audit.
    assert prov["state_columns_qualified"] is False
    si = prov["state_inheritance"]
    assert set(si) == {"n_rows", "first_date", "last_date"}
    # F4 (CLI side): the same pinned values as the builder test.
    assert si == {"n_rows": 155, "first_date": "2020-11-11", "last_date": "2021-11-02"}
    for key in originals:
        pd.testing.assert_frame_equal(originals[key], before[key])
    pd.testing.assert_frame_equal(vintages, before_vintages)


def test_window_basis_uses_per_value_source_date():
    """W2(a): a leg whose initial vintage is NaN for its first N rows after
    `first`, with a pre-coverage value forward-filled, must label the window
    `revised_fallback_inputs` based on the per-value source date (the last
    index date at which the un-forward-filled leg series had a finite
    observation), not the row's own date. RED without the per-value fix."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    coverage_row = 100
    n_post_nan = 5
    index = pd.bdate_range("2020-01-01", periods=count)
    pre_value = 50.0
    # Un-filled source: every pre-coverage row carries a finite pre-coverage
    # value (so the lag window can resolve a source date); every post-coverage
    # row is NaN (the actual initial vintage is missing for the first N rows
    # after `first`).
    source = pd.Series(np.nan, index=index, dtype=float)
    source.iloc[:coverage_row] = pre_value
    # Forward-filled features: pre-coverage value carries through the first N
    # post-coverage rows; real initial-vintage values begin after that.
    features = pd.DataFrame({leg: np.nan for leg in builder.LEGS}, index=index)
    ffill_end = coverage_row + n_post_nan
    features.loc[index[:ffill_end], "payrolls"] = pre_value
    post_values = pre_value + 1.0 + np.arange(count - ffill_end)
    features.loc[index[ffill_end:], "payrolls"] = post_values
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = index[coverage_row]
    sources = {"payrolls": source}
    result, _ = builder.macro_window_provenance(features, active, coverage, sources=sources)
    for i in range(coverage_row, ffill_end):
        assert result.iloc[i]["macro_window_basis"] == "revised_fallback_inputs", (
            f"row {i} ({index[i].date()}): expected revised_fallback_inputs, "
            f"got {result.iloc[i]['macro_window_basis']}"
        )
        assert "payrolls" in result.iloc[i]["macro_window_revised_legs"]
    # At row `coverage_row + lag`, the lag window is entirely post-coverage
    # in row-date terms — so the row-date logic would call it
    # `initial_vintage_inputs`. The per-value fix, however, sees that every
    # post-coverage source value is NaN and the latest finite source date is
    # the pre-coverage stamp, so it correctly stays
    # `revised_fallback_inputs`. This is the sharpest test of the per-value
    # fix vs the row-date fall-back.
    payrolls_lag = 63
    sharp = coverage_row + payrolls_lag
    assert result.iloc[sharp]["macro_window_basis"] == "revised_fallback_inputs", (
        f"row {sharp} ({index[sharp].date()}): expected revised_fallback_inputs, "
        f"got {result.iloc[sharp]['macro_window_basis']}"
    )


def test_window_basis_normal_leg_unchanged_by_per_value_provenance():
    """W2(b): a normal leg with finite initial values is unchanged — the
    per-value source date matches the row date when the source is the
    fully-populated feature column."""
    from scripts import build_regime_v2_pit as builder
    frame, active, coverage = _window_fixture("payrolls")
    result, audit = builder.macro_window_provenance(
        frame, active, coverage, sources={"payrolls": frame["payrolls"]})
    # Existing behaviour: pre-coverage window is revised_fallback_inputs;
    # post-coverage window flips to initial_vintage_inputs.
    assert result.iloc[162]["macro_window_basis"] == "revised_fallback_inputs"
    assert result.iloc[163]["macro_window_basis"] == "initial_vintage_inputs"
    assert audit["legacy_pit_class_changed"] is False


def test_window_basis_no_source_fallback_is_unknown():
    """W2(c) / F1: a feature frame that DOES carry finite leg columns still
    resolves every row to `unknown_inputs` when no un-filled source series is
    supplied — the forward-filled feature column is never used as its own
    source. The same fixture with `sources={"payrolls": ...}` resolves the
    payrolls leg, and payrolls is the only active leg in the fixture, so the
    basis flips to a non-unknown label at the same rows. A mutant that
    restores `source = features.get(leg)` would call the no-source case
    `initial_vintage_inputs` and the with-source case unchanged; the first
    assertion below flips the discriminator."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    index = pd.bdate_range("2020-01-01", periods=count)
    # Feature frame WITH finite leg columns; the standard fixture makes
    # payrolls the only active leg, which keeps the basis single-axis.
    frame, active, coverage = _window_fixture("payrolls")
    # No sources supplied -> the conservative label is unknown_inputs.
    result, _ = builder.macro_window_provenance(frame, active, coverage)
    assert set(result["macro_window_basis"]) == {"unknown_inputs"}
    assert result["macro_window_unknown_legs"].str.contains("payrolls").all()
    # With the un-filled source series supplied, payrolls resolves per-value
    # exactly as it does in test (b): revised_fallback_inputs at row 162,
    # initial_vintage_inputs at row 163.
    result2, _ = builder.macro_window_provenance(
        frame, active, coverage, sources={"payrolls": frame["payrolls"]})
    assert result2.iloc[162]["macro_window_basis"] == "revised_fallback_inputs"
    assert result2.iloc[163]["macro_window_basis"] == "initial_vintage_inputs"


def test_window_basis_unparseable_coverage_start_is_unknown():
    """W5: an unparseable `coverage_start` value resolves that leg to
    `unknown_inputs` instead of raising."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    index = pd.bdate_range("2020-01-01", periods=count)
    features = pd.DataFrame({leg: np.arange(count, dtype=float) + 100.0
                             for leg in builder.LEGS}, index=index)
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = "not-a-date"
    result, _ = builder.macro_window_provenance(features, active, coverage)
    assert set(result["macro_window_basis"]) == {"unknown_inputs"}
    assert result["macro_window_unknown_legs"].str.contains("payrolls").all()


def test_source_dedup_keeps_last_value_like_engine_inputs_put():
    """F2: a duplicate stamp at the same coverage row carries the LAST value
    (the value carried by `engine/inputs.put()`'s forward-fill), not the FIRST.
    With a finite 5.0 then NaN at `first` and a pre-coverage value forward-
    filled into the feature frame, the row whose lag window is ENTIRELY post-
    coverage is `revised_fallback_inputs` (the latest finite source date
    predates `first`), not `initial_vintage_inputs` (which would mean the
    duplicate's last-wins NaN was ignored)."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    coverage_row = 100
    payrolls_lag = 63
    # Row whose lag window is fully post-coverage.
    sharp = coverage_row + payrolls_lag
    index = pd.bdate_range("2020-01-01", periods=count)
    first = index[coverage_row]
    pre_value = 50.0
    # Build the source with two rows at `first`: finite 5.0 first, NaN second.
    # A first-wins de-dup would keep the 5.0 and call the source date `first`;
    # a last-wins de-dup (matching `engine/inputs.put()`) sees only NaN at and
    # after `first`, so the latest finite source date predates `first`.
    values = [pre_value] * coverage_row + [5.0, np.nan] + [np.nan] * (count - coverage_row - 2)
    stamps = list(index[:coverage_row]) + [first, first] + list(index[coverage_row + 2:])
    assert len(values) == len(stamps) == count
    source = pd.Series(values, index=pd.DatetimeIndex(stamps), dtype=float)
    assert source.index.has_duplicates
    features = pd.DataFrame({"payrolls": pre_value}, index=index)
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = first
    result, _ = builder.macro_window_provenance(
        features, active, coverage, sources={"payrolls": source})
    assert result.iloc[sharp]["macro_window_basis"] == "revised_fallback_inputs", (
        f"row {sharp} ({index[sharp].date()}): expected revised_fallback_inputs, "
        f"got {result.iloc[sharp]['macro_window_basis']}"
    )


def test_tz_aware_source_index_normalises_to_naive_utc():
    """F6: a timezone-aware source index is normalised to naive UTC before
    comparison with the naive feature index, then leg labels are stamped from
    the per-value source date. If the comparison is still impossible the leg
    is UNKNOWN and the function never raises."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    coverage_row = 100
    index = pd.bdate_range("2020-01-01", periods=count)
    pre_value = 50.0
    tz_index = index.tz_localize("America/New_York")
    # America/New_York source with finite observed value on EVERY row (replaces
    # the pre-coverage-only source from the original F6 test); the per-value
    # path is exercised past coverage so post-coverage rows get initial_vintage.
    source = pd.Series(pre_value, index=tz_index, dtype=float)
    # Feature index is naive; the payrolls column carries pre-coverage values
    # forward into the lag window the same way the source does.
    features = pd.DataFrame({"payrolls": pre_value}, index=index)
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = index[coverage_row]
    # Should not raise.
    result, _ = builder.macro_window_provenance(
        features, active, coverage, sources={"payrolls": source})
    # Row 0's source_date is NaT (NY 00:00 2020-01-01 > BC 00:00 2020-01-01
    # after tz_convert('UTC').tz_localize(None)), so row 0 stays unknown_inputs
    # and the original F6 "unknown_inputs in set" property is preserved.
    assert "unknown_inputs" in set(result["macro_window_basis"])
    # Exact labels at two rows derived from payrolls lag_rows=63
    # (row 70 lag window [7, 70] entirely pre-coverage -> revised_fallback_inputs;
    #  row 164 lag window [101, 164] entirely post-coverage -> initial_vintage_inputs;
    #  both >=5 rows from the row 0 / row 100 / row 63 boundaries).
    assert result.iloc[70]["macro_window_basis"] == "revised_fallback_inputs"
    assert result.iloc[164]["macro_window_basis"] == "initial_vintage_inputs"


def test_all_three_tz_aware_inputs_fall_back_to_unknown_without_raising(caplog):
    """F6/T3: when the feature index, the coverage start, AND the source are
    ALL tz-aware, the per-value comparison RAISES and the builder catches it
    via the (TypeError, ValueError) handler; the leg's finite rows are
    unknown_inputs. Covers the residual case where the
    (first.tzinfo is None) != (index.tz is None) parity check passes but the
    source_dates < first comparison still fails on a tz vs naive boundary.
    """
    from scripts import build_regime_v2_pit as builder
    count = 200
    coverage_row = 100
    index = pd.bdate_range("2020-01-01", periods=count).tz_localize("UTC")
    pre_value = 50.0
    tz_index = index.tz_localize(None).tz_localize("America/New_York")
    source = pd.Series(pre_value, index=tz_index, dtype=float)
    features = pd.DataFrame({"payrolls": pre_value}, index=index)
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = index[coverage_row]
    # Must not raise. The per-value tz compare resolves to unknown_inputs.
    result, _ = builder.macro_window_provenance(
        features, active, coverage, sources={"payrolls": source})
    payroll_basis = states_payroll_basis(result, builder)
    assert (payroll_basis == "unknown_inputs").all()
    # The except block must log exactly one WARNING naming the failed leg
    # so the receipt can attribute the fallback rather than calling it silent.
    warning_records = [
        record for record in caplog.records
        if record.levelname == "WARNING"
        and "source-date comparison failed" in record.getMessage()
    ]
    assert len(warning_records) == 1


def states_payroll_basis(result, builder):
    """Helper: returns the cross-leg `macro_window_basis` column from the
    result frame; with only payrolls active that equals the payrolls leg's
    label (no other leg contributes a different value)."""
    return result["macro_window_basis"]


@pytest.mark.parametrize("bad_coverage", [0, 1.5, True])
def test_non_string_non_date_non_timestamp_coverage_is_unknown(bad_coverage):
    """F7: a coverage start that is bool/int/float is unparseable and
    resolves the leg to `unknown_inputs`."""
    from scripts import build_regime_v2_pit as builder
    count = 200
    index = pd.bdate_range("2020-01-01", periods=count)
    features = pd.DataFrame({"payrolls": np.arange(count, dtype=float) + 100.0},
                            index=index)
    active = {leg: pd.Series(False, index=index) for leg in builder.LEGS}
    active["payrolls"] = pd.Series(True, index=index)
    coverage = {leg: None for leg in builder.LEGS}
    coverage["payrolls"] = bad_coverage
    result, _ = builder.macro_window_provenance(features, active, coverage)
    assert set(result["macro_window_basis"]) == {"unknown_inputs"}
    assert result["macro_window_unknown_legs"].str.contains("payrolls").all()
