"""GLT T09 regression net: C16 forecast identity, C17 publication-clock
leakage, C18 dispositions — plus runner, ledger, outage and card contracts.

Synthetic frames and tmp_path fixtures only: no data/ read, no parquet engine,
no network (CI installs pytest, pandas, numpy, pyyaml only).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from engine import global_liquidity_forecast as glf
from engine.global_liquidity_outlook import (
    H41_NONRESERVE_LIABILITY_LINES,
    H41_TGA_LINE,
)
from scripts import research_global_liquidity_forecast as runner

REPO = Path(__file__).resolve().parents[1]
REAL_CONFIG = REPO / "config" / "global_liquidity_forecast_v1.yml"
FIXTURE_SEED = 20261019
SMALL_WINDOWS = {
    "train_start": "2008-01-04", "train_end": "2011-12-30",
    "dev_start": "2012-01-02", "dev_end": "2015-12-25",
    "reserved_start": "2016-01-04", "reserved_end": "2016-12-30",
}


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def real_family():
    return glf.load_family(REAL_CONFIG)


@pytest.fixture(scope="module")
def small_config(tmp_path_factory):
    """The REAL config with only the windows (and the two min_* origins knobs)
    reduced; family, margins, intervals, clocks and calendar stay byte-for-byte."""
    raw = yaml.safe_load(REAL_CONFIG.read_text())
    raw["windows"].update(SMALL_WINDOWS)
    raw["origins"].update({"min_train_weeks": 52, "min_train_examples": 52})
    path = tmp_path_factory.mktemp("smallcfg") / "small.yml"
    path.write_text(yaml.safe_dump(raw))
    return path


def _small_family(small_config):
    return glf.load_family(small_config)


_TAX_DAYS = {(1, 15), (4, 15), (6, 15), (9, 15), (12, 15)}


def _tax_mask(days):
    """One jump on the first business day at or after each tax date (a weekend
    tax date still moves the account on the next business day)."""
    mask = np.zeros(len(days), dtype=float)
    pos = {ts: i for i, ts in enumerate(days)}
    last = days[-1]
    for year in range(days[0].year, last.year + 1):
        for month, day in _TAX_DAYS:
            ts = pd.Timestamp(year, month, day)
            while ts not in pos and ts < last:
                ts = ts + pd.Timedelta(days=1)
            if ts in pos:
                mask[pos[ts]] += 1.0
    return mask


def _daily_level(rng, days, *, base, sigma, phi, jump, sign, tax):
    """AR(1) daily increments + tax-day jumps (adapted from the I1A smoke)."""
    n = len(days)
    e = rng.normal(0.0, sigma, n)
    inc = np.zeros(n)
    for i in range(1, n):
        inc[i] = phi * inc[i - 1] + e[i]
    return base + np.cumsum(sign * (inc + jump * tax))


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    """Seeded synthetic sources: TGA ($mn, business days), reserves ($mn,
    Wednesdays), RRP ($bn, business days) with a 2009 training outage, a
    2012 dev-window outage, and ABSURD (1e12) values from reserved_start on."""
    rng = np.random.default_rng(FIXTURE_SEED)
    d = tmp_path_factory.mktemp("fixture")
    days = pd.date_range("2007-01-02", "2016-12-31", freq="B")
    tax = _tax_mask(days)
    tga = pd.DataFrame({
        "obs_date": days,
        "value": _daily_level(rng, days, base=60_000.0, sigma=100.0, phi=0.95,
                              jump=12_000.0, sign=1.0, tax=tax),
    })
    res_level = _daily_level(rng, days, base=1_500_000.0, sigma=200.0, phi=0.95,
                             jump=12_000.0, sign=-1.0, tax=tax)
    res = pd.DataFrame({
        "obs_date": days[days.weekday == 2],
        "value": res_level[days.weekday == 2],
    })
    rrp_level = _daily_level(rng, days, base=40.0, sigma=1.2, phi=0.9, jump=0.0, sign=1.0,
                               tax=np.zeros(len(days)))
    rrp = pd.DataFrame({"obs_date": days, "value": rrp_level})
    rrp = rrp[~((rrp["obs_date"] >= "2009-01-01") & (rrp["obs_date"] < "2009-07-01"))]
    rrp = rrp[~((rrp["obs_date"] >= "2012-07-02") & (rrp["obs_date"] < "2012-09-03"))]

    def _absurd(frame):
        frame = frame.copy()
        frame.loc[frame["obs_date"] >= pd.Timestamp("2016-01-04"), "value"] = 1e12
        return frame

    for name, frame in (("reserves_wresbal.csv", res), ("tga.csv", tga), ("rrp.csv", rrp)):
        _absurd(frame).to_csv(d / name, index=False)
    return d


@pytest.fixture(scope="module")
def e2e(small_config, fixture_dir, tmp_path_factory):
    """The runner twice against the fixture: same ledger, two as-of stamps."""
    d = tmp_path_factory.mktemp("e2e")
    root = d / "root"
    root.mkdir()
    ledger = d / "ledger.jsonl"
    cards, outs, rcs = [], [], []
    stamps = ("2026-10-19T09:00:00+00:00", "2026-10-19T09:05:00+00:00")
    for i, as_of in enumerate(stamps):
        out = d / f"card{i + 1}.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = runner.main(["--config", str(small_config), "--root", str(root),
                              "--fixture", str(fixture_dir), "--ledger", str(ledger),
                              "--out", str(out), "--as-of", as_of])
        rcs.append(rc)
        outs.append(buf.getvalue())
        cards.append(json.loads(out.read_text()) if rc == 0 and out.exists() else None)
    return {"cards": cards, "outs": outs, "rcs": rcs, "ledger": ledger, "root": root}


def _run_args(tmp_path, root, **over):
    argv = ["--config", over.get("config", str(REAL_CONFIG)), "--root", str(root),
            "--ledger", str(over.get("ledger", tmp_path / "ledger.jsonl")),
            "--out", str(over.get("out", tmp_path / "card.json")),
            "--as-of", over.get("as_of", "2026-10-19T09:00:00+00:00")]
    return argv


def _panel(fridays, seed=3):
    rng = np.random.default_rng(seed)
    level = 100.0 + np.cumsum(rng.normal(0.0, 1.0, len(fridays)))
    return pd.DataFrame({"level": level, "obs_date": fridays,
                         "available": np.ones(len(fridays), dtype=bool)}, index=fridays)


def _design(fridays, horizon_weeks=4):
    return glf.build_design(_panel(fridays), horizon_weeks=horizon_weeks, target="tga_bn")


def _train_frame(maturities, origin, seed=5):
    """A synthetic design-like training frame (all features finite)."""
    rng = np.random.default_rng(seed)
    n = len(maturities)
    cols = {"maturity": pd.to_datetime(list(maturities)), "y": rng.normal(0.0, 1.0, n)}
    for k in (1, 2, 3, 4):
        cols[f"d_lag{k}"] = rng.normal(0.0, 1.0, n)
        cols[f"r_lag{k}"] = cols[f"d_lag{k}"]
    cols["ann_change"] = np.zeros(n)
    for name in glf.CALENDAR_INDICATORS:
        cols[f"cal_{name}"] = rng.integers(0, 2, n).astype(float)
    cols["iso_week"] = rng.integers(1, 53, n)
    frame = pd.DataFrame(cols)
    frame["y_res"] = frame["y"] - frame["ann_change"]
    return frame


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_keys(value)


# --------------------------------------------------------------------------- #
# C17 — publication clocks and training scope (leakage)
# --------------------------------------------------------------------------- #
def test_c17_tga_frame_without_publication_clock_is_refused():
    days = pd.bdate_range("2012-01-02", periods=40)
    eco = pd.DataFrame({"obs_date": days, "value": np.arange(40, dtype=float)})
    with pytest.raises(glf.MissingPublicationClock):
        glf.information_set(eco, origin=pd.Timestamp("2012-02-24"))
    clocked = glf.attach_publication_clock(eco, rule="dts_next_business_day_1600")
    all_nat = clocked.copy()
    all_nat["published_at_utc"] = pd.NaT
    with pytest.raises(glf.MissingPublicationClock):
        glf.information_set(all_nat, origin=pd.Timestamp("2012-02-24"))


def test_c17_shifting_publication_clock_changes_information_set():
    days = pd.bdate_range("2012-01-02", periods=30)
    frame = glf.attach_publication_clock(
        pd.DataFrame({"obs_date": days, "value": np.arange(30, dtype=float)}),
        rule="same_day_1315")
    origin = pd.Timestamp("2012-02-03")  # Friday
    admitted = glf.information_set(frame, origin=origin)
    assert pd.Timestamp("2012-02-02") in set(admitted["obs_date"])
    moved = frame.copy()
    moved.loc[moved["obs_date"] == pd.Timestamp("2012-02-02"), "published_at_utc"] = \
        pd.Timestamp("2012-02-06T00:00:00", tz="UTC")
    after = glf.information_set(moved, origin=origin)
    assert pd.Timestamp("2012-02-02") not in set(after["obs_date"])
    print("excluded row: obs_date=2012-02-02 published_at_utc moved to "
          "2012-02-06T00:00:00+00:00, origin cutoff 2012-02-03T00:00:00 America/New_York")


def test_c17_calibration_residual_at_or_after_origin_raises():
    origin = pd.Timestamp("2012-06-01")
    fitted = glf.fit_baseline("persistence", _train_frame(["2012-05-18", "2012-05-25"], origin),
                              origin=origin, min_train_examples=2)
    at_origin = pd.Series([1.0, 2.0], index=[pd.Timestamp("2012-05-25"), pd.Timestamp("2012-06-01")])
    with pytest.raises(glf.LeakedValidationResidual):
        glf.calibrate_interval(fitted, at_origin, nominal_levels=(80, 90))
    after = pd.Series([1.0], index=[pd.Timestamp("2012-06-08")])
    with pytest.raises(glf.LeakedValidationResidual):
        glf.calibrate_interval(fitted, after, nominal_levels=(80, 90))


def test_c17_training_frame_with_maturity_at_origin_is_refused():
    origin = pd.Timestamp("2012-06-01")
    clean = _train_frame(["2012-05-18", "2012-05-25"], origin)
    glf.fit_baseline("persistence", clean, origin=origin, min_train_examples=2)
    leak = _train_frame(["2012-05-18", "2012-06-01"], origin)
    with pytest.raises(glf.LeakedValidationResidual):
        glf.fit_baseline("persistence", leak, origin=origin)
    with pytest.raises(glf.LeakedValidationResidual):
        glf.fit_candidate(glf.CandidateConfig(id="ar1", kind="residual_ar", p=1), leak, origin=origin)


def test_c17_transforms_are_training_scoped():
    fridays = pd.date_range("2010-01-01", "2012-12-28", freq="W-FRI")
    design = _design(fridays)
    o_early = pd.Timestamp("2011-01-07")
    o_late = pd.Timestamp("2012-12-28")
    tr_early = glf.training_rows(design, origin=o_early, horizon_weeks=4, purge_weeks=12,
                                 train_start=date(2010, 1, 1))
    tr_late = glf.training_rows(design, origin=o_late, horizon_weeks=4, purge_weeks=12,
                                train_start=date(2010, 1, 1))
    cfg = glf.CandidateConfig(id="ridge", kind="ridge_residual", alpha=1.0)
    f_early = glf.fit_candidate(cfg, tr_early, origin=o_early, min_train_examples=10)
    f_late = glf.fit_candidate(cfg, tr_late, origin=o_late, min_train_examples=10)
    assert any(a != b for a, b in zip(f_early.feature_mean, f_late.feature_mean))
    assert any(a != b for a, b in zip(f_early.feature_std, f_late.feature_std))
    with pytest.raises(glf.LeakedValidationResidual):
        glf.fit_candidate(cfg, design, origin=o_early, min_train_examples=10)


def test_c17_training_rows_are_purged():
    fridays = pd.date_range("2010-01-01", "2012-12-28", freq="W-FRI")
    design = _design(fridays)
    purge_weeks = 12
    origin = pd.Timestamp("2011-06-03")
    tr = glf.training_rows(design, origin=origin, horizon_weeks=4, purge_weeks=purge_weeks,
                           train_start=date(2010, 1, 1))
    limit = origin - pd.Timedelta(days=7 * purge_weeks)
    assert len(tr) > 0
    assert (pd.to_datetime(tr["maturity"]) <= limit).all()
    assert (pd.to_datetime(tr.index) >= pd.Timestamp(date(2010, 1, 1))).all()


def test_c17_weekly_panel_admits_only_published_anchors():
    days = pd.bdate_range("2012-01-02", "2012-03-30")
    frame = glf.attach_publication_clock(
        pd.DataFrame({"obs_date": days, "value": np.arange(len(days), dtype=float)}),
        rule="same_day_1315")
    fridays = pd.date_range("2012-01-06", "2012-03-30", freq="W-FRI")
    panel = glf.weekly_panel(frame, fridays=fridays, max_anchor_age_days=7)
    assert panel["available"].all()  # Thursday obs, published same day 13:15 ET
    assert panel.loc[fridays[0], "obs_date"] == pd.Timestamp("2012-01-05")
    late = frame.copy()
    late.loc[late["obs_date"].dt.weekday == 3, "published_at_utc"] = \
        pd.Timestamp("2012-06-01", tz="UTC")  # every Thursday unpublished before no Friday
    stale = glf.weekly_panel(late, fridays=fridays, max_anchor_age_days=1)
    assert not stale["available"].any()
    assert stale["level"].isna().all()
    print(f"Friday {fridays[0].date()}: anchor obs 2012-01-05 published after the "
          f"Friday cutoff -> available=False, level=NaN")


def _per_friday_reference(frame, fridays, max_anchor_age_days):
    """Spec section 3, literally: per Friday, the admitted row with the greatest obs_date.

    Tie rule: first release wins among equal obs_date (cohort-1 first-release
    semantics) - the admitted rows are ordered by publication clock (stable)
    and the first row carrying the greatest obs_date is taken. Shares nothing
    with weekly_panel except information_set, which the spec names.
    """
    fridays = pd.DatetimeIndex(fridays)
    rows = []
    for f in fridays:
        admitted = glf.information_set(frame, origin=f.date())
        admitted = admitted.assign(obs_date=pd.to_datetime(admitted["obs_date"]))
        admitted = admitted[admitted["obs_date"].notna()]
        if admitted.empty:
            rows.append((np.nan, pd.NaT, False))
            continue
        admitted = admitted.sort_values("published_at_utc", kind="mergesort")
        top = admitted[admitted["obs_date"] == admitted["obs_date"].max()].iloc[0]
        value = float(pd.to_numeric(pd.Series([top["value"]]), errors="coerce").iloc[0])
        available = bool((f - top["obs_date"]).days <= max_anchor_age_days and np.isfinite(value))
        rows.append((value if available else np.nan, top["obs_date"], available))
    ref = pd.DataFrame(rows, columns=["level", "obs_date", "available"], index=fridays)
    ref["level"] = ref["level"].astype(float)
    ref["obs_date"] = pd.to_datetime(ref["obs_date"]).astype("datetime64[ns]")
    ref["available"] = ref["available"].astype(bool)
    ref.index.name = "friday"
    return ref


def _ny_cutoff(day):
    """Local midnight America/New_York of ``day`` in UTC (independent of the module)."""
    return pd.Timestamp(day).tz_localize("America/New_York").tz_convert("UTC")


def test_c17_weekly_panel_vectorised_equals_per_friday_definition():
    """Spec section 3: the vectorised weekly_panel MUST equal the per-Friday definition.

    Checked on the three publication-clock rules and on a hand-built adversarial
    frame (shuffled rows, a revision, NaN and NaT rows, a publication exactly at a
    Friday cutoff and one a second after, the max-age boundary, both 2012 US DST
    changes). Tie rule: first release wins among equal obs_date.
    """
    rng = np.random.default_rng(20261019)
    days = pd.bdate_range("2012-02-20", "2012-03-30").append(pd.bdate_range("2012-10-15", "2012-11-23"))
    base = pd.DataFrame({"obs_date": days, "value": rng.normal(100.0, 5.0, len(days))})
    base.loc[base["obs_date"] == pd.Timestamp("2012-03-08"), "value"] = np.nan
    fridays = pd.date_range("2012-02-10", "2012-12-07", freq="W-FRI")
    assert len(glf.CLOCK_RULES) == 3
    for rule in glf.CLOCK_RULES:
        frame = glf.attach_publication_clock(base, rule=rule)
        frame = frame.iloc[rng.permutation(len(frame))].reset_index(drop=True)
        got = glf.weekly_panel(frame, fridays=fridays, max_anchor_age_days=7)
        pd.testing.assert_frame_equal(got, _per_friday_reference(frame, fridays, 7))

    ts = pd.Timestamp
    adv = pd.DataFrame([
        (ts("2012-02-28"), 1.0, _ny_cutoff("2012-03-02") - pd.Timedelta(hours=1)),
        (ts("2012-03-01"), 2.0, _ny_cutoff("2012-03-02")),                            # exactly at the cutoff
        (pd.NaT, 99.0, _ny_cutoff("2012-03-02") - pd.Timedelta(hours=5)),             # NaT obs_date
        (ts("2012-03-08"), 3.0, _ny_cutoff("2012-03-09") + pd.Timedelta(seconds=1)),  # one second late
        (ts("2012-02-27"), 0.5, _ny_cutoff("2012-03-16") - pd.Timedelta(minutes=30)),  # old obs, late clock
        (ts("2012-03-15"), 4.0, _ny_cutoff("2012-03-16") - pd.Timedelta(hours=2)),    # first release
        (ts("2012-03-15"), 40.0, _ny_cutoff("2012-03-16") - pd.Timedelta(hours=1)),   # revision, same obs
        (ts("2012-03-16"), 5.0, _ny_cutoff("2012-03-23") - pd.Timedelta(hours=3)),    # 7 days old at 03-23
        (ts("2012-03-29"), np.nan, _ny_cutoff("2012-03-30") - pd.Timedelta(hours=1)),  # newest is NaN
        (ts("2012-03-20"), 7.0, ts("2013-01-01", tz="UTC")),                          # never published in time
        (ts("2012-11-01"), 9.0, _ny_cutoff("2012-11-02") - pd.Timedelta(hours=1)),    # EDT Friday
        (ts("2012-11-08"), 8.0, ts("2012-11-09 04:30", tz="UTC")),                    # before the EST cutoff 05:00Z
    ], columns=["obs_date", "value", "published_at_utc"])
    adv["published_at_utc"] = pd.to_datetime(adv["published_at_utc"], utc=True)
    adv = adv.iloc[rng.permutation(len(adv))].reset_index(drop=True)
    adv_fridays = pd.DatetimeIndex(["2012-02-24", "2012-03-02", "2012-03-09", "2012-03-16", "2012-03-23",
                                    "2012-03-30", "2012-11-02", "2012-11-09"])
    ref = _per_friday_reference(adv, adv_fridays, 7)
    pd.testing.assert_frame_equal(glf.weekly_panel(adv, fridays=adv_fridays, max_anchor_age_days=7), ref)

    # the adversarial frame really exercises each boundary
    assert not ref.loc["2012-02-24", "available"] and pd.isna(ref.loc["2012-02-24", "obs_date"])
    assert ref.loc["2012-03-02", "obs_date"] == ts("2012-03-01") and ref.loc["2012-03-02", "level"] == 2.0
    assert not ref.loc["2012-03-09", "available"]                     # newest admitted anchor is 8 days old
    assert ref.loc["2012-03-16", "level"] == 4.0                      # first release, not the revision
    assert ref.loc["2012-03-23", "available"] and ref.loc["2012-03-23", "level"] == 5.0  # exactly 7 days
    assert ref.loc["2012-03-30", "obs_date"] == ts("2012-03-29") and not ref.loc["2012-03-30", "available"]
    assert ref.loc["2012-11-02", "level"] == 9.0 and ref.loc["2012-11-09", "level"] == 8.0
    print("weekly_panel == per-Friday definition on 3 clock rules x "
          f"{len(fridays)} Fridays + {len(adv_fridays)} adversarial Fridays")


# --------------------------------------------------------------------------- #
# C16 — forecast identity on the H.4.1 Table 5 anchor
# --------------------------------------------------------------------------- #
def _anchor_row():
    """A balanced H.4.1 Table 5 anchor row in $ millions (FIXTURE_ROW shape)."""
    return {
        "Federal Reserve notes, net of F.R. Bank holdings": 2_300_000.0,
        "Reverse repurchase agreements: Foreign official and international accounts": 380_000.0,
        "Reverse repurchase agreements: Others": 150_000.0,
        "Deposits: Term deposits held by depository institutions": 0.0,
        H41_TGA_LINE: 800_000.0,
        "Deposits: Foreign official": 10_000.0,
        "Deposits: Other": 120_000.0,
        "Deferred availability cash items": 1_000.0,
        "Treasury contributions to credit facilities": 5_000.0,
        "Earnings remittances due to the U.S. Treasury": -230_000.0,
        "Other liabilities and accrued dividends": 40_000.0,
        "Total capital": 50_000.0,
        "Reserve balances with Federal Reserve Banks": 3_000_000.0,
        "Total assets": 6_626_000.0,
    }


def _consistent_paths(d_tga=12.0, d_rrp=-5.0):
    return {"tga_bn": d_tga, "rrp_bn": d_rrp,
            "reserves_wresbal_bn": -(d_tga + d_rrp)}


def test_c16_forecast_identity_reconciles_with_residual_printed():
    out = glf.reconcile_forecast_identity(_consistent_paths(), _anchor_row())
    assert out["available"] is True
    assert out["reconciles"] is True
    assert out["residual"] == pytest.approx(0.0, abs=1e-6)
    print(f"forecast identity residual ($mn): {out['residual']}")


def test_c16_dropped_liability_fails_with_nonzero_residual():
    dropped = tuple(n for n in H41_NONRESERVE_LIABILITY_LINES if n != H41_TGA_LINE)
    out = glf.reconcile_forecast_identity(_consistent_paths(), _anchor_row(),
                                          nonreserve_lines=dropped)
    assert out["reconciles"] is False
    assert out["t08"]["residual"] != 0.0
    assert abs(out["t08"]["residual"]) == pytest.approx(812_000.0, rel=1e-9)
    print(f"dropped TGA liability residual ($mn): {out['t08']['residual']}")


def test_c16_double_counted_liability_fails():
    doubled = tuple(list(H41_NONRESERVE_LIABILITY_LINES) + [H41_TGA_LINE])
    out = glf.reconcile_forecast_identity(_consistent_paths(), _anchor_row(),
                                          nonreserve_lines=doubled)
    assert out["reconciles"] is False
    dup = [k for k in out["t08"] if "duplicate" in str(k)]
    assert dup and out["t08"][dup[0]], f"double counting not reported: {list(out['t08'])}"
    assert abs(out["t08"]["residual"]) == pytest.approx(812_000.0, rel=1e-9)


def test_c16_inconsistent_component_paths_fail():
    paths = dict(_consistent_paths(), reserves_wresbal_bn=-(12.0 - 5.0) + 3.0)
    out = glf.reconcile_forecast_identity(paths, _anchor_row())
    assert out["reconciles"] is False
    assert abs(out["residual"]) == pytest.approx(3_000.0, rel=1e-9)
    print(f"inconsistent component paths residual ($mn): {out['residual']}")


def test_c16_no_anchor_is_unavailable_record():
    out = glf.reconcile_forecast_identity(None, None)
    assert out == {"available": False, "reason": "no_h41_table5_anchor_in_inputs",
                   "residual": None}


# --------------------------------------------------------------------------- #
# C18 — dispositions
# --------------------------------------------------------------------------- #
def _c18_cell(**over):
    cell = {
        "target": "tga_bn", "horizon_weeks": 4, "candidate": "ridge_residual_a1.0",
        "cell_index": 16, "best_baseline": "training_only_ar", "relative_gain": 0.12,
        "gain_ci": {"level": 90, "low": 0.04, "high": 0.2},
        "errors": {name: {"mae": 1.0, "rmse": 1.4}
                   for name in list(glf.BASELINE_LADDER) + ["ridge_residual_a1.0"]},
        "intervals": {
            "80": {"nominal": 80, "observed_coverage": 81.2, "mean_width": 12.5, "n_missing": 0},
            "90": {"nominal": 90, "observed_coverage": 89.7, "mean_width": 16.1, "n_missing": 0},
        },
        "denominators": {"n_origins_total": 100, "n_outage": 0, "outage_share": None,
                         "n_outcome_unavailable": 0, "n_model_unavailable": 0,
                         "n_origins_scored": 100, "source_status": "loaded"},
        "first_origin": "2012-01-06", "last_origin": "2013-11-29",
    }
    cell.update(over)
    return cell


def test_c18_gain_below_margin_is_withheld_no_gain_naming_baseline(real_family):
    cell = _c18_cell(relative_gain=0.01)
    disposition, reason = glf.dispose_with_reason(cell, real_family.margins)
    assert disposition == "withheld_no_gain"
    assert "training_only_ar" in reason
    assert "0.01" in reason


def test_c18_ci_low_not_positive_is_withheld_no_gain(real_family):
    cell = _c18_cell(gain_ci={"level": 90, "low": -0.01, "high": 0.2})
    assert glf.dispose(cell, real_family.margins) == "withheld_no_gain"


def test_c18_insufficient_sample_is_withheld(real_family):
    cell = _c18_cell(denominators={"n_origins_total": 51, "n_outage": 0, "outage_share": None,
                                   "n_outcome_unavailable": 0, "n_model_unavailable": 0,
                                   "n_origins_scored": 51, "source_status": "loaded"})
    disposition, reason = glf.dispose_with_reason(cell, real_family.margins)
    assert disposition == "withheld_insufficient_sample"
    assert "51" in reason and "52" in reason


def test_c18_miscalibrated_coverage_is_withheld(real_family):
    iv80 = dict(_c18_cell()["intervals"]["80"], observed_coverage=70.0)
    cell = _c18_cell(intervals={"80": iv80, "90": _c18_cell()["intervals"]["90"]})
    disposition, reason = glf.dispose_with_reason(cell, real_family.margins)
    assert disposition == "withheld_miscalibrated"
    assert "70" in reason and "80" in reason


def test_c18_cell_without_interval_is_never_issued(real_family):
    variants = []
    n_missing = _c18_cell()
    n_missing["intervals"]["80"]["n_missing"] = 3
    variants.append(n_missing)
    no_cov = _c18_cell()
    no_cov["intervals"]["90"]["observed_coverage"] = None
    variants.append(no_cov)
    no_width = _c18_cell()
    no_width["intervals"]["80"]["mean_width"] = None
    variants.append(no_width)
    for cell in variants:
        assert glf.dispose(cell, real_family.margins) == "withheld_miscalibrated"


def test_c18_issued_requires_coverage_and_width(real_family):
    assert glf.dispose(_c18_cell(), real_family.margins) == "issued"
    no_cov = _c18_cell()
    no_cov["intervals"]["90"]["observed_coverage"] = None
    assert glf.dispose(no_cov, real_family.margins) != "issued"
    no_width = _c18_cell()
    no_width["intervals"]["80"]["mean_width"] = None
    assert glf.dispose(no_width, real_family.margins) != "issued"


def test_c18_no_scored_origins_is_unavailable(real_family):
    cell = _c18_cell(
        relative_gain=None, gain_ci={"level": 90, "low": None, "high": None},
        denominators={"n_origins_total": 100, "n_outage": 100, "outage_share": 1.0,
                      "n_outcome_unavailable": 0, "n_model_unavailable": 0,
                      "n_origins_scored": 0,
                      "source_status": "source_missing:data/fred/RRPONTSYD.parquet"})
    disposition, reason = glf.dispose_with_reason(cell, real_family.margins)
    assert disposition == "unavailable"
    for token in ("100", "1", "source_missing:data/fred/RRPONTSYD.parquet"):
        assert token in reason


def test_c18_precedence_is_fixed(real_family):
    no_gain = _c18_cell(relative_gain=0.01)
    bad_cov = no_cov_cell = _c18_cell()
    bad_cov["intervals"]["80"]["observed_coverage"] = 70.0
    everything = _c18_cell(
        relative_gain=0.01,
        intervals=no_cov_cell["intervals"],
        denominators={"n_origins_total": 100, "n_outage": 100, "outage_share": 1.0,
                      "n_outcome_unavailable": 0, "n_model_unavailable": 0,
                      "n_origins_scored": 0, "source_status": "loaded"})
    assert glf.dispose(everything, real_family.margins) == "unavailable"  # rule 1 first
    small = _c18_cell(relative_gain=0.01,
                      denominators={"n_origins_total": 51, "n_outage": 0, "outage_share": None,
                                    "n_outcome_unavailable": 0, "n_model_unavailable": 0,
                                    "n_origins_scored": 51, "source_status": "loaded"})
    assert glf.dispose(small, real_family.margins) == "withheld_insufficient_sample"  # 2 < 3
    assert glf.dispose(no_gain, real_family.margins) == "withheld_no_gain"  # 3 < 4


# --------------------------------------------------------------------------- #
# reserved window
# --------------------------------------------------------------------------- #
def test_reserved_origin_at_or_after_reserved_start_raises():
    idx = pd.date_range("2012-01-06", "2013-12-27", freq="W-FRI")
    with pytest.raises(glf.ReservedWindowTouched):
        glf.rolling_origins(idx, train_end=date(2011, 12, 30), dev_end=date(2013, 12, 27),
                            reserved_start=date(2012, 6, 1), min_train_weeks=52,
                            step_weeks=1, horizon_weeks=4, purge_weeks=12)
    with pytest.raises(glf.ReservedWindowTouched):
        glf.rolling_origins(idx, train_end=date(2011, 12, 30), dev_end=date(2013, 12, 27),
                            reserved_start=date(2013, 12, 27), min_train_weeks=52,
                            step_weeks=1, horizon_weeks=4, purge_weeks=12)


def test_reserved_maturity_after_dev_end_raises():
    with pytest.raises(glf.ReservedWindowTouched) as excinfo:
        glf.assert_outside_reserved([pd.Timestamp("2013-11-01")], horizon_weeks=4,
                                    dev_end=date(2013, 11, 20), reserved_start=date(2014, 1, 6))
    assert "2013-11-01" in str(excinfo.value)


def test_rolling_origins_stay_inside_card_windows(real_family):
    fam = real_family
    fridays = glf.panel_fridays(fam.windows, fam.origins)
    idx = fridays[(fridays >= pd.Timestamp(fam.windows.train_start))
                  & (fridays <= pd.Timestamp(fam.windows.dev_end))]
    for h in fam.horizons_weeks:
        origins = glf.rolling_origins(
            idx, train_end=fam.windows.train_end, dev_end=fam.windows.dev_end,
            reserved_start=fam.windows.reserved_start,
            min_train_weeks=fam.origins.min_train_weeks, step_weeks=fam.origins.step_weeks,
            horizon_weeks=h, purge_weeks=fam.windows.purge_weeks)
        assert len(origins) > 0
        for o in origins:
            assert o < pd.Timestamp(fam.windows.reserved_start)
            assert o + pd.Timedelta(days=7 * h) <= pd.Timestamp(fam.windows.dev_end)


# --------------------------------------------------------------------------- #
# family declaration and ledger
# --------------------------------------------------------------------------- #
def _mutated_config(tmp_path, mutate):
    raw = yaml.safe_load(REAL_CONFIG.read_text())
    mutate(raw)
    path = tmp_path / "mutated.yml"
    path.write_text(yaml.safe_dump(raw))
    return path


def test_family_real_config_declares_45_cells_in_order(real_family):
    fam = real_family
    cells = fam.cells()
    assert len(cells) == 45 == fam.n_trials_total
    assert (cells[0][0], cells[0][1], cells[0][2].id) == ("reserves_wresbal_bn", 4, "residual_ar_p1")
    assert (cells[16][0], cells[16][1], cells[16][2].id) == ("tga_bn", 4, "residual_ar_p2")
    assert (cells[44][0], cells[44][1], cells[44][2].id) == ("rrp_bn", 13, "ridge_residual_a10.0")
    assert fam.card_ref["card_hash"].startswith("da060bf4")
    assert fam.card_ref["card_hash"].endswith("6aee")


def test_family_n_trials_mismatch_raises_at_load_family(tmp_path):
    path = _mutated_config(tmp_path, lambda raw: raw["family"].update(n_trials_total=44))
    with pytest.raises(glf.FamilyDeclarationError):
        glf.load_family(path)


def test_family_purge_rule_mismatch_raises(tmp_path):
    bad_weeks = _mutated_config(tmp_path, lambda raw: raw["windows"].update(purge_weeks=11))
    with pytest.raises(glf.FamilyDeclarationError):
        glf.load_family(bad_weeks)
    bad_rule = _mutated_config(tmp_path, lambda raw: raw["windows"].update(purge_rule="n/5"))
    with pytest.raises(glf.FamilyDeclarationError):
        glf.load_family(bad_rule)


def test_family_validated_true_is_refused(tmp_path):
    path = _mutated_config(tmp_path, lambda raw: raw.update(validated=True))
    with pytest.raises(glf.FamilyDeclarationError):
        glf.load_family(path)


def test_register_family_logs_budget_before_trials(real_family):
    class _SpyLedger:
        def __init__(self):
            self.calls = []

        def log_declared_budget(self, n, *, family=None, reason=None, **kw):
            self.calls.append(("budget", n, family, reason))
            return True

        def log_trial(self, config, *, family=None, info_cutoff=None, **kw):
            self.calls.append(("trial", config, info_cutoff))
            return True

    spy = _SpyLedger()
    fam = real_family
    info = {(t, h): "2021-12-31" for t in fam.targets for h in fam.horizons_weeks}
    n_new = glf.register_family(spy, fam, info_cutoffs=info)
    assert n_new == 45
    assert spy.calls[0][0] == "budget"
    assert spy.calls[0][1] == 45
    trials = spy.calls[1:]
    assert len(trials) == 45
    for (_kind, config, cutoff), (t, h, c) in zip(trials, fam.cells()):
        assert config == fam.trial_config(t, h, c)
        assert cutoff == "2021-12-31"


def test_ledger_literal_n_equals_family_and_rerun_adds_zero(e2e, small_config):
    fam = _small_family(small_config)
    ledger = runner.TrialLedger(e2e["ledger"], family=fam.name)
    assert ledger.literal_n() == 45 == fam.n_trials_total
    card = e2e["cards"][0]
    assert len(card["cells"]) == 45
    assert card["family"]["n_trials_total"] == 45
    assert "new_trials=0" in e2e["outs"][1]


def test_rerun_reproduces_card_except_run_clock(e2e):
    assert e2e["rcs"] == [0, 0]
    card1, card2 = e2e["cards"]
    assert card1["run"]["as_of"] != card2["run"]["as_of"]
    del card1["run"]["as_of"]
    del card2["run"]["as_of"]
    assert card1 == card2


# --------------------------------------------------------------------------- #
# outage and sources
# --------------------------------------------------------------------------- #
def test_outage_origin_counted_not_dropped(e2e):
    cells = e2e["cards"][0]["cells"]
    for h in (4, 8, 13):
        rrp = next(c for c in cells if c["target"] == "rrp_bn" and c["horizon_weeks"] == h)
        tga = next(c for c in cells if c["target"] == "tga_bn" and c["horizon_weeks"] == h)
        den = rrp["denominators"]
        assert den["n_outage"] > 0
        assert den["n_origins_total"] == tga["denominators"]["n_origins_total"]
        print(f"rrp h{h}: n_outage={den['n_outage']} of n_origins_total="
              f"{den['n_origins_total']} counted, not dropped")
    for cell in cells:
        d = cell["denominators"]
        assert (d["n_outage"] + d["n_outcome_unavailable"] + d["n_model_unavailable"]
                + d["n_origins_scored"]) == d["n_origins_total"]


def test_missing_source_cells_are_unavailable(small_config):
    fam = _small_family(small_config)
    sources = {t: {"frame": None, "status": f"source_missing:data/fred/{t}.parquet"}
               for t in fam.targets}
    cells = glf.run_study(sources, family=fam)
    assert len(cells) == 45
    assert all(c["disposition"] == "unavailable" for c in cells)
    statuses = sorted({str(c["denominators"]["source_status"]) for c in cells})
    print(f"source_status: {statuses}")
    assert all(s.startswith("source_missing:") for s in statuses)


def test_absurd_post_window_values_never_reach_the_card(e2e, small_config):
    fam = _small_family(small_config)
    card = e2e["cards"][0]
    for rec in card["inputs"]["sources"]:
        assert rec["last_obs"] is None or rec["last_obs"] <= fam.windows.dev_end.isoformat()
    maes = [ev["mae"] for c in card["cells"] for ev in c["errors"].values()
            if ev and ev.get("mae") is not None]
    assert maes and max(maes) < 1e6


def test_real_loader_matches_canon_and_truncates(small_config, tmp_path, monkeypatch):
    fam = _small_family(small_config)
    root = tmp_path
    days = pd.bdate_range("2012-01-02", "2014-06-30")
    rng = np.random.default_rng(11)
    tga_mn = pd.Series(50_000.0 + np.cumsum(rng.normal(0.0, 50.0, len(days))), index=days)
    rrp = pd.Series(40.0 + np.cumsum(rng.normal(0.0, 1.0, len(days))), index=days)
    wres = pd.Series(1_500_000.0 + np.cumsum(rng.normal(0.0, 400.0, len(days))), index=days)
    walcl = wres + tga_mn + 1000.0 * rrp + 500_000.0
    fakes = {
        "tga.parquet": pd.DataFrame({"tga_mn": tga_mn}),
        "RRPONTSYD.parquet": pd.DataFrame({"on_rrp": rrp}),
        "WALCL.parquet": pd.DataFrame({"walcl": walcl}),
        "WRESBAL.parquet": pd.DataFrame({"obs_date": days,
                                         "reserve_balances": wres.to_numpy()}),
    }
    for rel in ("data/treasury/tga.parquet", "data/fred/RRPONTSYD.parquet",
                "data/fred/WALCL.parquet", "data/fred/WRESBAL.parquet"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"dummy-bytes:" + rel.encode())

    def fake_read_parquet(path, *args, **kwargs):
        return fakes[Path(path).name]

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)
    sources, receipts = runner.load_real_sources(root, fam)
    cut_days = days[days <= pd.Timestamp(fam.windows.dev_end)]

    def _vals(source, expected):
        got = source["frame"].set_index("obs_date")["value"]
        common = got.index.intersection(expected.index)
        assert len(common) >= len(cut_days) - 10  # the dev_end clock filter may drop late rows
        assert np.allclose(got.loc[common].to_numpy(), expected.loc[common].to_numpy(), atol=1e-9)
        assert source["frame"]["obs_date"].max() <= pd.Timestamp(fam.windows.dev_end)

    assert sources["tga_bn"]["status"] == "loaded"
    assert sources["rrp_bn"]["status"] == "loaded"
    assert sources["reserves_wresbal_bn"]["status"] == "loaded"
    _vals(sources["tga_bn"], tga_mn / 1000.0)
    _vals(sources["rrp_bn"], rrp)
    _vals(sources["reserves_wresbal_bn"], wres / 1000.0)

    rec = {r["target"]: r for r in receipts}
    assert rec["tga_bn"]["sha256"] == hashlib.sha256(
        (root / "data/treasury/tga.parquet").read_bytes()).hexdigest()
    assert rec["tga_bn"]["rows_loaded"] == len(cut_days)
    assert rec["tga_bn"]["last_obs"] <= fam.windows.dev_end.isoformat()

    (root / "data/fred/WRESBAL.parquet").unlink()
    sources2, receipts2 = runner.load_real_sources(root, fam)
    assert sources2["reserves_wresbal_bn"]["status"] == \
        "source_missing:data/fred/WRESBAL.parquet"
    assert sources2["reserves_wresbal_bn"]["frame"] is None
    assert {r["target"]: r for r in receipts2}["reserves_wresbal_bn"]["sha256"] is None


# --------------------------------------------------------------------------- #
# vocabulary and output
# --------------------------------------------------------------------------- #
def test_card_has_no_forbidden_keys(e2e):
    card = e2e["cards"][0]
    bad = [k for k in _walk_keys(card) if glf.FORBIDDEN_KEY_RE.search(k)]
    assert bad == []
    assert '"validated": true' not in json.dumps(card)


def test_notice_line_is_annotation_shaped(e2e):
    out = e2e["outs"][0]
    lines = [ln for ln in out.split("\n") if ln.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("ledger: new_trials=")
    notice = lines[1]
    m = re.match(r"^::notice title=glt-t09::(\d+) cells, (\d+) issued, literal_n=(\d+)$",
                 notice)
    assert m, notice
    card = e2e["cards"][0]
    assert int(m.group(1)) == len(card["cells"]) == 45
    assert int(m.group(2)) == card["summary"]["dispositions"]["issued"]
    assert int(m.group(3)) == card["trial_ledger"]["literal_n"] == 45
    assert out.index("ledger: new_trials=") < out.index("::notice")


def test_runner_refuses_nightly_ledger_path(small_config, fixture_dir, tmp_path):
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)
    argv = _run_args(tmp_path, root, config=str(small_config),
                     ledger=root / "data" / "trial_ledger.jsonl")
    assert runner.main(argv) == 2


def test_runner_refuses_naive_as_of(small_config, fixture_dir, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    argv = _run_args(tmp_path, root, config=str(small_config),
                     as_of="2026-10-19T09:00:00")
    assert runner.main(argv) == 2
    argv[argv.index("--as-of") + 1] = "not-a-time"
    assert runner.main(argv) == 2


def test_runner_refuses_out_under_data_or_site(small_config, fixture_dir, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    for bad in ("data", "site"):
        (root / bad).mkdir(exist_ok=True)
        argv = _run_args(tmp_path, root, config=str(small_config), out=root / bad / "card.json")
        assert runner.main(argv) == 2


def test_c18_bootstrap_uses_candidate_errors_not_forecasts(real_family):
    """Spec section 7: the paired bootstrap resamples gain_r = 1 - mean|e_c| /
    mean|e_best| on the SAME indices — never mean|forecast|. One candidate's
    forecasts equal the best baseline's forecasts exactly, so its errors equal
    the baseline's everywhere: the point gain is exactly 0 and every resampled
    gain is 0 (CI = (0, 0)). Averaging |forecast| instead (forecast 7 vs errors
    of +-3) pushes the whole CI below 0 and fails low <= 0 <= high.
    """
    family = real_family
    n = 2 * family.margins.block_weeks  # 26 >= block_weeks scored origins
    index = pd.date_range("2012-01-06", periods=n, freq="W-FRI")
    frame = pd.DataFrame(index=index)
    frame["source_available"] = np.ones(n, dtype=bool)
    frame["outcome_available"] = np.ones(n, dtype=bool)
    frame["y"] = 7.0 + 3.0 * np.where(np.arange(n) % 2, 1.0, -1.0)
    for name in glf.BASELINE_LADDER:
        frame[f"f_{name}"] = 7.0  # the best baseline's forecasts
    for cfg in family.candidates:
        frame[f"f_{cfg.id}"] = 7.0 if cfg.id == "residual_ar_p1" else 0.0
        for level in family.intervals.nominal_levels:
            frame[f"q{level}_{cfg.id}"] = 10.0
    cells = glf.score_cells(frame, target="tga_bn", horizon_weeks=4,
                            family=family, cell_index_start=0)
    cell = {c["candidate"]: c for c in cells}["residual_ar_p1"]
    assert cell["relative_gain"] == 0.0
    ci = cell["gain_ci"]
    assert ci is not None and ci["low"] <= 0.0 <= ci["high"]


# --------------------------------------------------------------------------- #
# issued path (end-to-end)
# --------------------------------------------------------------------------- #
def test_e2e_fixture_issues_at_least_one_cell(e2e):
    card = e2e["cards"][0]
    issued = [c for c in card["cells"] if c["disposition"] == "issued"]
    assert issued, f"no issued cell; dispositions={card['summary']['dispositions']}"
    for c in issued:
        for level in ("80", "90"):
            assert c["intervals"][level]["observed_coverage"] is not None
            assert c["intervals"][level]["mean_width"] is not None
        assert c["estimate_type"] == "statistical_forecast"
        assert c["abstention_reason"] is None
    print("issued cells: " + ", ".join(
        f"{c['target']}/h{c['horizon_weeks']}/{c['candidate']}" for c in issued))


def test_gain_ci_brackets_point_gain(e2e):
    """A bootstrap CI of a statistic must bracket the full-sample statistic.

    Whatever the fixture's seeded realization, every reported gain_ci must
    contain the cell's own full-sample relative_gain.
    """
    for cell in e2e["cards"][0]["cells"]:
        ci, gain = cell["gain_ci"], cell["relative_gain"]
        if ci is None or gain is None:
            continue
        assert ci["low"] <= gain <= ci["high"], (
            f"{cell['target']} h{cell['horizon_weeks']} {cell['candidate']}: "
            f"gain={gain} outside its own gain_ci=({ci['low']}, {ci['high']})")
