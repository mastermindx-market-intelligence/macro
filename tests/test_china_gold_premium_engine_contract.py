"""Merge-gate contract for the China physical-gold premium engine.

This file is intentionally engine-only so the gate:code conviction-profile job
can exercise source entitlement, calculation, and temporal-alignment invariants
without importing the heavier commodity renderer. Product/template coverage stays
in tests/test_china_gold_premium.py on the render/data lane.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import china_gold_premium as cgp


def _frame(values, *, column="value", dates=None):
    if dates is None:
        dates = pd.date_range("2026-09-01", periods=len(values), freq="D")
    return pd.DataFrame({column: values}, index=pd.to_datetime(dates))


def _leg(group, name, *, entitled=True):
    return {
        "group": group,
        "name": name,
        "column": "value",
        "source_label": f"{group}:{name}",
        "entitled": entitled,
    }


def test_canonical_formula_normalizes_rmb_per_gram_to_usd_per_troy_ounce():
    london = 4391.59
    fx = 7.0
    target_sge_usd = 4398.94
    sge_rmb_g = target_sge_usd * fx / cgp.TROY_OZ_GRAMS

    out = cgp.compute_daily_benchmark(
        _frame([sge_rmb_g], column="sge"),
        _frame([london], column="london"),
        _frame([fx], column="fx"),
        sge_column="sge",
        london_column="london",
        fx_column="fx",
    )

    row = out.iloc[-1]
    assert row["sge_usd_oz"] == pytest.approx(target_sge_usd)
    assert row["spread_usd_oz"] == pytest.approx(target_sge_usd - london)
    assert row["premium_pct"] == pytest.approx((target_sge_usd / london - 1) * 100)


def test_canonical_daily_series_rejects_nonfinite_nonpositive_and_unaligned_rows():
    sge = _frame(
        [700.0, np.inf, -1.0, 710.0],
        dates=["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13"],
    )
    london = _frame(
        [3000.0, 3010.0, 3020.0],
        dates=["2026-09-10", "2026-09-12", "2026-09-13"],
    )
    fx = _frame(
        [7.0, 7.0, 0.0],
        dates=["2026-09-10", "2026-09-12", "2026-09-13"],
    )

    out = cgp.compute_daily_benchmark(
        sge, london, fx,
        sge_column="value", london_column="value", fx_column="value",
    )

    assert list(out.index) == [pd.Timestamp("2026-09-10")]
    assert np.isfinite(out["premium_pct"].iloc[0])


def test_intraday_proxy_requires_all_three_latest_legs_within_max_skew():
    sge = _frame([700.0], dates=["2026-09-18T02:00:00Z"])
    london = _frame([3100.0], dates=["2026-09-18T02:12:00Z"])
    fx = _frame([7.0], dates=["2026-09-18T02:10:00Z"])

    accepted = cgp.compute_intraday_proxy(
        sge, london, fx,
        sge_column="value", london_column="value", fx_column="value",
        max_skew_minutes=15,
    )
    rejected = cgp.compute_intraday_proxy(
        sge, london, fx,
        sge_column="value", london_column="value", fx_column="value",
        max_skew_minutes=5,
    )

    assert len(accepted) == 1
    assert accepted.iloc[-1]["methodology"] == "intraday_indicative"
    assert rejected.empty


def test_view_model_refuses_unentitled_source_instead_of_substituting_a_proxy():
    frames = {
        ("sge", "pm"): _frame([700.0]),
        ("london", "am"): _frame([3100.0]),
        ("fx", "usdcny"): _frame([7.0]),
    }

    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm"),
            "london": _leg("london", "am", entitled=False),
            "fx": _leg("fx", "usdcny"),
        }
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-01T18:00:00Z"),
    )

    assert vm["available"] is False
    assert vm["reason_code"] == "source_not_entitled"
    assert vm["chart"]["canonical"] == []
    assert vm["chart"]["intraday"] is None


def test_view_model_does_not_look_ahead_to_future_daily_rows():
    now = pd.Timestamp("2026-09-18T18:00:00Z")
    frames = {
        ("sge", "pm"): _frame([700.0, 900.0], dates=["2026-09-18", "2026-09-19"]),
        ("london", "am"): _frame([3100.0, 3200.0], dates=["2026-09-18", "2026-09-19"]),
        ("fx", "daily"): _frame([7.0, 7.0], dates=["2026-09-18", "2026-09-19"]),
    }
    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm"),
            "london": _leg("london", "am"),
            "fx": _leg("fx", "daily"),
            "max_age_days": 5,
        }
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=now,
    )

    assert vm["available"] is True
    assert vm["canonical"]["asof"] == "2026-09-18"


def test_stale_intraday_alone_cannot_become_the_current_read():
    now = pd.Timestamp("2026-09-18T12:00:00Z")
    frames = {
        ("sge", "au9999"): _frame([700.0], dates=["2026-09-18T09:00:00Z"]),
        ("london", "spot"): _frame([3100.0], dates=["2026-09-18T09:03:00Z"]),
        ("fx", "intraday"): _frame([7.0], dates=["2026-09-18T09:02:00Z"]),
    }
    cfg = {
        "intraday": {
            "sge": _leg("sge", "au9999"),
            "london": _leg("london", "spot"),
            "fx": _leg("fx", "intraday"),
            "max_skew_minutes": 10,
            "max_age_minutes": 30,
        }
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=now,
    )

    assert vm["available"] is False
    assert vm["reason_code"] == "stale_observation"


def test_malformed_freshness_setting_is_refused_instead_of_raising():
    frames = {
        ("sge", "pm"): _frame([700.0]),
        ("london", "am"): _frame([3100.0]),
        ("fx", "daily"): _frame([7.0]),
    }
    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm"),
            "london": _leg("london", "am"),
            "fx": _leg("fx", "daily"),
            "max_age_days": "invalid",
        }
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-01T18:00:00Z"),
    )

    assert vm["available"] is False
    assert vm["reason_code"] == "source_config_invalid"
