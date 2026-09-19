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


# China close-basis proxy contract (stacked source slice).
def test_close_aligned_proxy_compares_rmb_per_ounce_directly():
    from engine import china_gold_premium as cgp

    idx = [pd.Timestamp("2026-09-18T07:30:00")]
    sge = pd.DataFrame({"rmb_per_g": [820.50]}, index=idx)
    global_spot = pd.DataFrame({"cny_per_oz": [25490.0]}, index=idx)

    out = cgp.compute_close_aligned_proxy(
        sge,
        global_spot,
        sge_column="rmb_per_g",
        global_column="cny_per_oz",
        max_skew_minutes=2,
    )

    assert len(out) == 1
    row = out.iloc[-1]
    expected_local = 820.50 * cgp.TROY_OZ_GRAMS
    assert row["sge_cny_oz"] == pytest.approx(expected_local)
    assert row["reference_cny_oz"] == pytest.approx(25490.0)
    assert row["spread_cny_oz"] == pytest.approx(expected_local - 25490.0)
    assert row["premium_pct"] == pytest.approx((expected_local / 25490.0 - 1.0) * 100.0)


def test_proxy_only_view_model_is_available_and_keeps_canonical_separate():
    from engine import china_gold_premium as cgp

    idx = pd.date_range("2026-09-01 07:30:00", periods=18, freq="D")
    sge = pd.DataFrame({"rmb_per_g": [810.0 + i for i in range(18)]}, index=idx)
    global_spot = pd.DataFrame({"cny_per_oz": [25200.0 + 25 * i for i in range(18)]}, index=idx)
    frames = {
        ("gold_china_basis", "sge_au9999"): sge,
        ("gold_china_basis", "xaucny_spot"): global_spot,
    }
    cfg = {
        "canonical": {},
        "intraday": {},
        "close_proxy": {
            "sge": {
                "group": "gold_china_basis",
                "name": "sge_au9999",
                "column": "rmb_per_g",
                "source_label": "Shanghai Gold Exchange Au99.99",
                "entitled": True,
            },
            "global": {
                "group": "gold_china_basis",
                "name": "xaucny_spot",
                "column": "cny_per_oz",
                "source_label": "Global XAU/CNY spot",
                "entitled": True,
            },
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    assert vm["available"] is True
    assert vm["current_method"] == "close_proxy"
    assert vm["methodology_label_en"] == "Indicative Shanghai-close basis"
    assert vm["price_currency"] == "CNY"
    assert vm["canonical"]["available"] is False
    assert vm["close_proxy"]["available"] is True
    assert len(vm["chart"]["canonical"]) == 0
    assert len(vm["chart"]["proxy"]) == 18
    assert vm["chart"]["display_source"] == "proxy"
    assert vm["stats"]["avg_5"] is not None
    assert vm["stats"]["range_30"] is None  # 18 observations must not masquerade as 30 sessions
    assert vm["sge_price_oz"] == pytest.approx(vm["chart"]["proxy"][-1]["sge_price_oz"])
    assert vm["reference_price_oz"] == pytest.approx(vm["chart"]["proxy"][-1]["reference_price_oz"])


def test_same_date_canonical_benchmark_outranks_close_proxy():
    from engine import china_gold_premium as cgp

    idx = [pd.Timestamp("2026-09-18")]
    proxy_idx = [pd.Timestamp("2026-09-18T07:30:00")]
    frames = {
        ("sge", "pm"): pd.DataFrame({"v": [820.0]}, index=idx),
        ("lbma", "am"): pd.DataFrame({"v": [3700.0]}, index=idx),
        ("fx", "daily"): pd.DataFrame({"v": [6.95]}, index=idx),
        ("basis", "sge"): pd.DataFrame({"v": [820.0]}, index=proxy_idx),
        ("basis", "global"): pd.DataFrame({"v": [25450.0]}, index=proxy_idx),
    }
    leg = lambda g, n, label: {
        "group": g, "name": n, "column": "v", "source_label": label, "entitled": True
    }
    cfg = {
        "canonical": {
            "sge": leg("sge", "pm", "SGE SHAUPM"),
            "london": leg("lbma", "am", "LBMA AM"),
            "fx": leg("fx", "daily", "USDCNY"),
            "max_age_days": 4,
        },
        "close_proxy": {
            "sge": leg("basis", "sge", "SGE Au99.99"),
            "global": leg("basis", "global", "Global XAU/CNY"),
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }

    vm = cgp.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    assert vm["current_method"] == "canonical"
    assert vm["price_currency"] == "USD"
    assert vm["chart"]["display_source"] == "canonical"


def test_gold_premium_quality_receipt_marks_fresh_close_proxy_consistent(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "status": "available",
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "chart": {"display_source": "proxy"},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "close_proxy": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T07:30:00+00:00",
            "sources": ["Shanghai Gold Exchange Au99.99", "Global XAU/CNY spot"],
        },
    }
    html = (
        '<section id="gold-china-premium" '
        'data-cgp-state="premium" '
        'data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" '
        'data-cgp-source-asof="2026-09-18T07:30:00+00:00" '
        'data-cgp-premium="0.167400"></section>'
    )

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["schema"] == "commodity.china_gold_premium_quality.v1"
    assert doc["status"] == "available_fresh"
    assert doc["render_consistent"] is True
    assert doc["headline_method"] == "close_proxy"
    assert doc["source_asof"] == "2026-09-18T07:30:00+00:00"
    assert doc["violations"] == []
    assert (tmp_path / "china_gold_premium.json").exists()


def test_gold_premium_quality_receipt_accepts_honest_unavailable_state(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": False,
        "status": "unavailable",
        "state": "unavailable",
        "reason_code": "source_data_unavailable",
        "current_method": None,
        "premium_pct": None,
        "price_currency": None,
        "chart": {"display_source": None},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "close_proxy": {"available": False, "fresh": False, "asof": None, "sources": []},
    }
    html = '<section id="gold-china-premium" data-cgp-state="unavailable" data-cgp-display-source="canonical" data-cgp-currency="USD"></section>'

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["status"] == "honest_unavailable"
    assert doc["render_consistent"] is True
    assert doc["reason_code"] == "source_data_unavailable"
    assert doc["violations"] == []


def test_gold_premium_quality_receipt_detects_render_contract_mismatch(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "status": "available",
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "chart": {"display_source": "proxy"},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "close_proxy": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T07:30:00+00:00",
            "sources": ["Shanghai Gold Exchange Au99.99", "Global XAU/CNY spot"],
        },
    }
    html = '<section id="gold-china-premium" data-cgp-state="premium" data-cgp-display-source="canonical" data-cgp-currency="USD"></section>'

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["status"] == "render_mismatch"
    assert doc["render_consistent"] is False
    assert "display_source: expected proxy, rendered canonical" in doc["violations"]
    assert "currency: expected CNY, rendered USD" in doc["violations"]


def test_gold_premium_quality_receipt_detects_stale_rendered_asof_or_value(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "status": "available",
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "chart": {"display_source": "proxy"},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "close_proxy": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T07:30:00+00:00",
            "sources": ["Shanghai Gold Exchange Au99.99", "Global XAU/CNY spot"],
        },
    }
    html = (
        '<section id="gold-china-premium" '
        'data-cgp-state="premium" '
        'data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" '
        'data-cgp-source-asof="2026-09-17T07:30:00+00:00" '
        'data-cgp-premium="0.111100"></section>'
    )

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["status"] == "render_mismatch"
    assert doc["render_consistent"] is False
    assert (
        "source_asof: expected 2026-09-18T07:30:00+00:00, "
        "rendered 2026-09-17T07:30:00+00:00"
    ) in doc["violations"]
    assert "premium_pct: expected 0.1674, rendered 0.1111" in doc["violations"]


def test_gold_premium_quality_receipt_preserves_method_separation(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "status": "available",
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "stats": {"avg_5": 0.12, "range_30": [-0.4, 0.5]},
        "chart": {
            "display_source": "proxy",
            "proxy": [{"date": f"2026-08-{i:02d}"} for i in range(1, 31)],
            "canonical": [],
            "intraday": None,
        },
        "canonical": {
            "available": False,
            "fresh": False,
            "asof": None,
            "sources": [],
        },
        "intraday": {
            "available": False,
            "fresh": False,
            "asof": None,
            "sources": [],
        },
        "close_proxy": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T07:30:00+00:00",
            "sources": ["Shanghai Gold Exchange Au99.99", "Global XAU/CNY spot"],
        },
    }
    html = (
        '<section id="gold-china-premium" '
        'data-cgp-state="premium" '
        'data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" '
        'data-cgp-source-asof="2026-09-18T07:30:00+00:00" '
        'data-cgp-premium="0.167400"></section>'
    )

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["methods"]["canonical"] == {
        "available": False,
        "fresh": False,
        "asof": None,
    }
    assert doc["methods"]["close_proxy"] == {
        "available": True,
        "fresh": True,
        "asof": "2026-09-18T07:30:00+00:00",
    }
    assert doc["official_canonical_available"] is False
    assert doc["history_points"] == 30
    assert doc["stats_5_ready"] is True
    assert doc["stats_30_ready"] is True


def test_gold_premium_live_ready_gate_requires_fresh_render_and_full_stats():
    from scripts import audit_china_gold_premium as audit

    ready = {
        "status": "available_fresh",
        "render_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
    }
    assert audit.live_ready_violations(ready) == []

    unavailable = dict(ready, status="honest_unavailable")
    assert "status is honest_unavailable, not available_fresh" in audit.live_ready_violations(unavailable)

    stale = dict(ready, status="available_stale")
    assert "status is available_stale, not available_fresh" in audit.live_ready_violations(stale)

    short_history = dict(ready, stats_30_ready=False)
    assert "30-session range is not ready" in audit.live_ready_violations(short_history)


def test_gold_premium_main_forwards_require_live_ready(monkeypatch):
    from scripts import audit_china_gold_premium as audit

    seen = {}

    def fake_run(*, strict_render=False, require_live_ready=False, required_method=None):
        seen.update(
            strict_render=strict_render,
            require_live_ready=require_live_ready,
            required_method=required_method,
        )
        return 0

    monkeypatch.setattr(audit, "run", fake_run)

    assert audit.main(["--strict-render", "--require-live-ready"]) == 0
    assert seen == {
        "strict_render": True,
        "require_live_ready": True,
        "required_method": None,
    }


def test_gold_premium_live_ready_gate_can_require_close_proxy_method():
    from scripts import audit_china_gold_premium as audit

    ready = {
        "status": "available_fresh",
        "render_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
        "headline_method": "close_proxy",
    }
    assert audit.live_ready_violations(ready, required_method="close_proxy") == []

    canonical = dict(ready, headline_method="canonical")
    assert (
        "headline method is canonical, required close_proxy"
        in audit.live_ready_violations(canonical, required_method="close_proxy")
    )


def test_gold_premium_main_forwards_required_method(monkeypatch):
    from scripts import audit_china_gold_premium as audit

    seen = {}

    def fake_run(*, strict_render=False, require_live_ready=False, required_method=None):
        seen.update(
            strict_render=strict_render,
            require_live_ready=require_live_ready,
            required_method=required_method,
        )
        return 0

    monkeypatch.setattr(audit, "run", fake_run)

    assert audit.main([
        "--strict-render",
        "--require-live-ready",
        "--require-method",
        "close_proxy",
    ]) == 0
    assert seen == {
        "strict_render": True,
        "require_live_ready": True,
        "required_method": "close_proxy",
    }
