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


def test_gold_premium_receipt_exposes_close_proxy_dataos_promotion_readiness(tmp_path):
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

    machine = {
        "available": True,
        "method": "close_proxy",
        "state": "premium",
        "premium_pct": 0.1674,
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_fresh": True,
        "official_canonical_available": False,
        "context_only": True,
    }
    doc = audit.write_receipt(
        vm,
        html,
        machine_projection=machine,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["machine_projection_consistent"] is True
    assert doc["close_proxy_dataos_promotion_ready"] is False
    assert (
        "source artifacts were not proven"
        in doc["close_proxy_dataos_promotion_blockers"]
    )


def test_gold_premium_receipt_blocks_dataos_promotion_for_honest_unavailable(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": False,
        "status": "unavailable",
        "state": "unavailable",
        "reason_code": "source_data_unavailable",
        "current_method": None,
        "premium_pct": None,
        "price_currency": None,
        "stats": {"avg_5": None, "range_30": None},
        "chart": {"canonical": [], "proxy": [], "intraday": None, "display_source": None},
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

    assert doc["close_proxy_dataos_promotion_ready"] is False
    assert "status is honest_unavailable, not available_fresh" in doc["close_proxy_dataos_promotion_blockers"]
    assert "headline method is none, required close_proxy" in doc["close_proxy_dataos_promotion_blockers"]


def test_gold_premium_audit_checks_machine_projection_consistency():
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "stats": {"avg_5": 0.12, "range_30": [-0.4, 0.5]},
        "chart": {"display_source": "proxy", "proxy": [{"date": "2026-09-18"}]},
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
        'data-cgp-state="premium" data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" data-cgp-source-asof="2026-09-18T07:30:00+00:00" '
        'data-cgp-premium="0.167400"></section>'
    )
    machine = {
        "available": True,
        "method": "close_proxy",
        "state": "premium",
        "premium_pct": 0.1674,
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_fresh": True,
        "official_canonical_available": False,
        "context_only": True,
    }

    doc = audit.evaluate(
        vm,
        html,
        machine_projection=machine,
        checked_at="2026-09-18T12:00:00+00:00",
    )

    assert doc["machine_projection_consistent"] is True
    assert doc["violations"] == []


def test_gold_premium_audit_rejects_drifted_machine_projection():
    from scripts import audit_china_gold_premium as audit

    vm = {
        "available": True,
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "stats": {"avg_5": 0.12, "range_30": [-0.4, 0.5]},
        "chart": {"display_source": "proxy", "proxy": [{"date": "2026-09-18"}]},
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
        'data-cgp-state="premium" data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" data-cgp-source-asof="2026-09-18T07:30:00+00:00" '
        'data-cgp-premium="0.167400"></section>'
    )
    machine = {
        "available": True,
        "method": "canonical",
        "state": "premium",
        "premium_pct": 0.10,
        "source_asof": "2026-09-17",
        "source_fresh": True,
        "official_canonical_available": False,
        "context_only": True,
    }

    doc = audit.evaluate(
        vm,
        html,
        machine_projection=machine,
        checked_at="2026-09-18T12:00:00+00:00",
    )

    assert doc["machine_projection_consistent"] is False
    assert doc["status"] == "render_mismatch"
    assert "machine.method: expected close_proxy, rendered canonical" in doc["violations"]
    assert "machine.premium_pct: expected 0.1674, rendered 0.1" in doc["violations"]


def _live_proxy_vm_for_audit():
    return {
        "available": True,
        "status": "available",
        "state": "premium",
        "current_method": "close_proxy",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "stats": {"avg_5": 0.12, "range_30": [-0.4, 0.5]},
        "chart": {"display_source": "proxy", "proxy": [{"date": "2026-09-18"}]},
        "canonical": {"available": False, "fresh": False, "asof": None, "sources": []},
        "intraday": {"available": False, "fresh": False, "asof": None, "sources": []},
        "close_proxy": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T07:30:00+00:00",
            "sources": ["Shanghai Gold Exchange Au99.99", "Global XAU/CNY spot"],
        },
    }


def _live_proxy_html_for_audit():
    return (
        '<section id="gold-china-premium" '
        'data-cgp-state="premium" data-cgp-display-source="proxy" '
        'data-cgp-currency="CNY" data-cgp-source-asof="2026-09-18T07:30:00+00:00" '
        'data-cgp-premium="0.167400"></section>'
    )


def test_gold_premium_run_checks_incumbent_machine_projection(tmp_path, monkeypatch):
    import json
    from scripts import audit_china_gold_premium as audit

    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    commodity = data_root / "commodity"
    site_root.mkdir(parents=True)
    commodity.mkdir(parents=True)
    site_root.joinpath("commodities.html").write_text(_live_proxy_html_for_audit())

    machine = {
        "available": True,
        "method": "close_proxy",
        "state": "premium",
        "premium_pct": 0.1674,
        "price_currency": "CNY",
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_fresh": True,
        "avg_5_pct": 0.12,
        "range_30_pct": [-0.4, 0.5],
        "official_canonical_available": False,
        "context_only": True,
    }
    commodity.joinpath("latest.json").write_text(json.dumps({
        "gold_context": {"china_physical_premium": machine}
    }))

    monkeypatch.setattr(audit.config, "ROOT", tmp_path)
    monkeypatch.setattr(audit.config, "data_dir", lambda: data_root)
    monkeypatch.setattr(
        audit.config,
        "load",
        lambda: {
            "storage": {"site_dir": "site"},
            "commodities": {"china_gold_premium": {}},
        },
    )
    monkeypatch.setattr(
        audit.china_gold_premium,
        "build_view_model",
        lambda cfg: _live_proxy_vm_for_audit(),
    )

    rc = audit.run(strict_render=True)
    receipt = json.loads(
        data_root.joinpath("quality", "china_gold_premium.json").read_text()
    )

    assert rc == 0
    assert receipt["machine_projection_consistent"] is True
    assert receipt["violations"] == []


def test_gold_premium_run_fails_closed_when_machine_projection_is_missing(tmp_path, monkeypatch):
    import json
    from scripts import audit_china_gold_premium as audit

    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    site_root.mkdir(parents=True)
    site_root.joinpath("commodities.html").write_text(_live_proxy_html_for_audit())

    monkeypatch.setattr(audit.config, "ROOT", tmp_path)
    monkeypatch.setattr(audit.config, "data_dir", lambda: data_root)
    monkeypatch.setattr(
        audit.config,
        "load",
        lambda: {
            "storage": {"site_dir": "site"},
            "commodities": {"china_gold_premium": {}},
        },
    )
    monkeypatch.setattr(
        audit.china_gold_premium,
        "build_view_model",
        lambda cfg: _live_proxy_vm_for_audit(),
    )

    rc = audit.run(strict_render=True)
    receipt = json.loads(
        data_root.joinpath("quality", "china_gold_premium.json").read_text()
    )

    assert rc == 2
    assert receipt["machine_projection_consistent"] is False
    assert "machine.method: expected close_proxy, rendered None" in receipt["violations"]


def test_gold_premium_dataos_promotion_requires_machine_projection_proof(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = _live_proxy_vm_for_audit()
    vm["chart"]["proxy"] = [
        {"date": f"2026-08-{i:02d}"} for i in range(1, 31)
    ]
    html = _live_proxy_html_for_audit()

    doc = audit.write_receipt(
        vm,
        html,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["machine_projection_consistent"] is None
    assert doc["close_proxy_dataos_promotion_ready"] is False
    assert (
        "machine projection was not proven consistent"
        in doc["close_proxy_dataos_promotion_blockers"]
    )


def _promotion_machine_for_audit():
    return {
        "available": True,
        "method": "close_proxy",
        "state": "premium",
        "premium_pct": 0.1674,
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_fresh": True,
        "official_canonical_available": False,
        "context_only": True,
    }


def _promotion_source_artifacts_for_audit():
    return [
        {
            "role": "sge",
            "dataset_id": "commodity.gold.sge_au9999.close",
            "registry_status": "PROPOSED",
            "path": "data/gold_china_basis/sge_au9999.parquet",
            "exists": True,
            "rows": 30,
            "sha256": "a" * 64,
            "asof": "2026-09-18T07:30:00+00:00",
            "selected_asof_present": True,
        },
        {
            "role": "global",
            "dataset_id": "commodity.gold.xaucny.close_ref",
            "registry_status": "PROPOSED",
            "path": "data/gold_china_basis/xaucny_spot.parquet",
            "exists": True,
            "rows": 30,
            "sha256": "b" * 64,
            "asof": "2026-09-18T07:30:00+00:00",
            "selected_asof_present": True,
        },
    ]


def test_gold_premium_dataos_promotion_rejects_incomplete_source_artifact_binding(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = _live_proxy_vm_for_audit()
    vm["chart"]["proxy"] = [
        {"date": f"2026-08-{i:02d}"} for i in range(1, 31)
    ]

    doc = audit.write_receipt(
        vm,
        _live_proxy_html_for_audit(),
        machine_projection=_promotion_machine_for_audit(),
        source_artifacts=[{"role": "sge", "exists": True}],
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["close_proxy_dataos_promotion_ready"] is False
    assert (
        "source artifact global was not proven"
        in doc["close_proxy_dataos_promotion_blockers"]
    )


def test_gold_premium_dataos_promotion_accepts_two_bound_current_source_artifacts(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = _live_proxy_vm_for_audit()
    vm["chart"]["proxy"] = [
        {"date": f"2026-08-{i:02d}"} for i in range(1, 31)
    ]

    doc = audit.write_receipt(
        vm,
        _live_proxy_html_for_audit(),
        machine_projection=_promotion_machine_for_audit(),
        source_artifacts=_promotion_source_artifacts_for_audit(),
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["close_proxy_dataos_promotion_ready"] is True
    assert doc["close_proxy_dataos_promotion_blockers"] == []


def test_gold_premium_run_binds_real_source_store_artifacts_for_dataos_promotion(
    tmp_path, monkeypatch
):
    import json

    import pandas as pd

    from engine import china_gold_premium
    from lib import config, store
    from scripts import audit_china_gold_premium as audit

    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    commodity_root = data_root / "commodity"
    site_root.mkdir(parents=True)
    commodity_root.mkdir(parents=True)

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: data_root)

    idx = pd.date_range("2026-08-20 07:30:00", periods=30, freq="D")
    store.upsert(
        "gold_china_basis",
        "sge_au9999",
        pd.DataFrame({"rmb_per_g": [820.0 + i * 0.1 for i in range(30)]}, index=idx),
        normalize_index=False,
    )
    store.upsert(
        "gold_china_basis",
        "xaucny_spot",
        pd.DataFrame({"cny_per_oz": [25450.0 + i for i in range(30)]}, index=idx),
        normalize_index=False,
    )

    def leg(name, column, label):
        return {
            "group": "gold_china_basis",
            "name": name,
            "column": column,
            "source_label": label,
            "entitled": True,
        }

    premium_cfg = {
        "canonical": {},
        "intraday": {},
        "close_proxy": {
            "sge": leg("sge_au9999", "rmb_per_g", "Shanghai Gold Exchange Au99.99"),
            "global": leg("xaucny_spot", "cny_per_oz", "Global XAU/CNY spot"),
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }
    now = pd.Timestamp("2026-09-18T12:00:00Z")
    vm = china_gold_premium.build_view_model(premium_cfg, now=now)
    assert vm["current_method"] == "close_proxy"
    assert vm["stats"]["range_30"] is not None

    site_root.joinpath("commodities.html").write_text(
        '<section id="gold-china-premium" '
        f'data-cgp-state="{vm["state"]}" '
        f'data-cgp-display-source="{vm["chart"]["display_source"]}" '
        f'data-cgp-currency="{vm["price_currency"]}" '
        f'data-cgp-source-asof="{vm["close_proxy"]["asof"]}" '
        f'data-cgp-premium="{vm["premium_pct"]:.6f}"></section>'
    )
    machine = {
        "available": True,
        "method": "close_proxy",
        "state": vm["state"],
        "premium_pct": vm["premium_pct"],
        "price_currency": "CNY",
        "source_asof": vm["close_proxy"]["asof"],
        "source_fresh": True,
        "avg_5_pct": vm["stats"]["avg_5"],
        "range_30_pct": vm["stats"]["range_30"],
        "official_canonical_available": False,
        "context_only": True,
    }
    commodity_root.joinpath("latest.json").write_text(
        json.dumps({"gold_context": {"china_physical_premium": machine}})
    )

    monkeypatch.setattr(
        audit.config,
        "load",
        lambda: {
            "storage": {"site_dir": "site"},
            "commodities": {"china_gold_premium": premium_cfg},
        },
    )
    real_build_view_model = china_gold_premium.build_view_model
    monkeypatch.setattr(
        audit.china_gold_premium,
        "build_view_model",
        lambda cfg: real_build_view_model(cfg, now=now),
    )

    rc = audit.run(
        strict_render=True,
        require_live_ready=True,
        required_method="close_proxy",
    )
    receipt = json.loads(
        data_root.joinpath("quality", "china_gold_premium.json").read_text()
    )

    assert rc == 0
    assert receipt["close_proxy_dataos_promotion_ready"] is True
    assert receipt["close_proxy_dataos_promotion_blockers"] == []
    assert [item["role"] for item in receipt["source_artifacts"]] == ["sge", "global"]
    for item in receipt["source_artifacts"]:
        assert item["exists"] is True
        assert item["rows"] == 30
        assert len(item["sha256"]) == 64
        assert item["asof"] == vm["close_proxy"]["asof"]
        assert item["path"].startswith("data/gold_china_basis/")


def test_gold_premium_audit_treats_unreadable_source_store_as_honest_unavailable(
    tmp_path, monkeypatch
):
    import json

    from lib import config
    from scripts import audit_china_gold_premium as audit

    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    commodity_root = data_root / "commodity"
    source_root = data_root / "gold_china_basis"
    site_root.mkdir(parents=True)
    commodity_root.mkdir(parents=True)
    source_root.mkdir(parents=True)

    # Existing-but-corrupt source files model an upstream artifact outage. The
    # scheduled proof path must report honest unavailability, not crash the
    # entire commodity builder merely because the audit cannot parse a source.
    source_root.joinpath("sge_au9999.parquet").write_bytes(b"not parquet")
    source_root.joinpath("xaucny_spot.parquet").write_bytes(b"not parquet")

    site_root.joinpath("commodities.html").write_text(
        '<section id="gold-china-premium" '
        'data-cgp-state="unavailable" '
        'data-cgp-display-source="canonical" '
        'data-cgp-currency="USD"></section>'
    )
    commodity_root.joinpath("latest.json").write_text(
        json.dumps(
            {
                "gold_context": {
                    "china_physical_premium": {
                        "available": False,
                        "method": None,
                        "state": "unavailable",
                        "premium_pct": None,
                        "source_asof": None,
                        "source_fresh": False,
                        "official_canonical_available": False,
                        "context_only": True,
                    }
                }
            }
        )
    )

    def leg(name, column, label):
        return {
            "group": "gold_china_basis",
            "name": name,
            "column": column,
            "source_label": label,
            "entitled": True,
        }

    premium_cfg = {
        "canonical": {},
        "intraday": {},
        "close_proxy": {
            "sge": leg("sge_au9999", "rmb_per_g", "Shanghai Gold Exchange Au99.99"),
            "global": leg("xaucny_spot", "cny_per_oz", "Global XAU/CNY spot"),
            "max_skew_minutes": 2,
            "max_age_days": 4,
        },
    }

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: data_root)
    monkeypatch.setattr(
        config,
        "load",
        lambda: {
            "storage": {"site_dir": "site"},
            "commodities": {"china_gold_premium": premium_cfg},
        },
    )

    rc = audit.main(["--strict-render"])
    receipt = json.loads(
        data_root.joinpath("quality", "china_gold_premium.json").read_text()
    )

    assert rc == 0
    assert receipt["status"] == "honest_unavailable"
    assert receipt["close_proxy_dataos_promotion_ready"] is False
    assert [item["rows"] for item in receipt["source_artifacts"]] == [0, 0]


def test_close_proxy_artifact_dataset_ids_are_resolved_from_dataos_registry(
    tmp_path, monkeypatch
):
    import pandas as pd

    from lib import config, store
    from scripts import audit_china_gold_premium as audit

    data_root = tmp_path / "data"
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: data_root)
    idx = pd.DatetimeIndex([pd.Timestamp("2026-09-18T07:30:00")])
    store.upsert(
        "gold_china_basis",
        "sge_au9999",
        pd.DataFrame({"rmb_per_g": [820.5]}, index=idx),
        normalize_index=False,
    )
    store.upsert(
        "gold_china_basis",
        "xaucny_spot",
        pd.DataFrame({"cny_per_oz": [25490.0]}, index=idx),
        normalize_index=False,
    )

    class Contract:
        def __init__(self, dataset_id, storage):
            self.dataset_id = dataset_id
            self.storage = storage

    class Registry:
        def all(self):
            return (
                Contract(
                    "fixture.sge.authority",
                    "data/gold_china_basis/sge_au9999.parquet",
                ),
                Contract(
                    "fixture.global.authority",
                    "data/gold_china_basis/xaucny_spot.parquet",
                ),
            )

    monkeypatch.setattr(audit, "load_registry", lambda: Registry(), raising=False)
    cfg = {
        "close_proxy": {
            "sge": {
                "group": "gold_china_basis",
                "name": "sge_au9999",
                "column": "rmb_per_g",
            },
            "global": {
                "group": "gold_china_basis",
                "name": "xaucny_spot",
                "column": "cny_per_oz",
            },
        }
    }

    artifacts = audit._close_proxy_source_artifacts(cfg)

    assert [item["dataset_id"] for item in artifacts] == [
        "fixture.sge.authority",
        "fixture.global.authority",
    ]


def test_gold_premium_dataos_promotion_requires_registry_dataset_id_binding(tmp_path):
    from scripts import audit_china_gold_premium as audit

    vm = _live_proxy_vm_for_audit()
    vm["chart"]["proxy"] = [
        {"date": f"2026-08-{i:02d}"} for i in range(1, 31)
    ]
    artifacts = _promotion_source_artifacts_for_audit()
    artifacts[0] = dict(artifacts[0], dataset_id=None)

    doc = audit.write_receipt(
        vm,
        _live_proxy_html_for_audit(),
        machine_projection=_promotion_machine_for_audit(),
        source_artifacts=artifacts,
        out_path=tmp_path / "china_gold_premium.json",
        checked_at="2026-09-18T23:00:00+00:00",
    )

    assert doc["close_proxy_dataos_promotion_ready"] is False
    assert (
        "source artifact sge Data OS id is not bound"
        in doc["close_proxy_dataos_promotion_blockers"]
    )


def test_gold_premium_live_ready_close_proxy_requires_bound_source_artifacts(
    tmp_path, monkeypatch
):
    from scripts import audit_china_gold_premium as audit

    site = tmp_path / "site"
    site.mkdir()
    site.joinpath("commodities.html").write_text("<html></html>")

    monkeypatch.setattr(audit.config, "ROOT", tmp_path)
    monkeypatch.setattr(audit.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(
        audit.config,
        "load",
        lambda: {
            "storage": {"site_dir": "site"},
            "commodities": {"china_gold_premium": {}},
        },
    )
    monkeypatch.setattr(
        audit.china_gold_premium,
        "build_view_model",
        lambda cfg: {},
    )
    ready_without_artifacts = {
        "status": "available_fresh",
        "render_consistent": True,
        "machine_projection_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
        "headline_method": "close_proxy",
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_artifacts": [],
    }
    monkeypatch.setattr(
        audit,
        "write_receipt",
        lambda *args, **kwargs: dict(ready_without_artifacts),
    )

    rc = audit.run(
        strict_render=True,
        require_live_ready=True,
        required_method="close_proxy",
    )

    assert rc == 3


def test_dataos_promotion_allows_newer_unmatched_global_rows_when_headline_row_is_bound():
    from scripts import audit_china_gold_premium as audit

    headline = "2026-09-18T07:30:00+00:00"
    doc = {
        "status": "available_fresh",
        "render_consistent": True,
        "machine_projection_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
        "headline_method": "close_proxy",
        "source_asof": headline,
        "source_artifacts": [
            {
                "role": "sge",
                "dataset_id": "commodity.gold.sge_au9999.close",
                "registry_status": "PROPOSED",
                "exists": True,
                "rows": 30,
                "sha256": "a" * 64,
                "asof": headline,
                "selected_asof_present": True,
            },
            {
                "role": "global",
                "dataset_id": "commodity.gold.xaucny.close_ref",
                "registry_status": "PROPOSED",
                "exists": True,
                "rows": 31,
                "sha256": "b" * 64,
                # Global gold/CNY may have a newer raw bar on a China-only holiday.
                "asof": "2026-09-21T07:30:00+00:00",
                "selected_asof_present": True,
            },
        ],
    }

    assert audit.live_ready_violations(
        doc,
        required_method="close_proxy",
        require_machine_projection=True,
        require_source_artifacts=True,
    ) == []


def test_gold_premium_dataos_promotion_rejects_invalid_registry_status():
    from scripts import audit_china_gold_premium as audit

    headline = "2026-09-18T07:30:00+00:00"
    doc = {
        "status": "available_fresh",
        "render_consistent": True,
        "machine_projection_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
        "headline_method": "close_proxy",
        "source_asof": headline,
        "source_artifacts": [
            {
                "role": "sge",
                "dataset_id": "commodity.gold.sge_au9999.close",
                "registry_status": "REJECTED",
                "exists": True,
                "rows": 30,
                "sha256": "a" * 64,
                "asof": headline,
                "selected_asof_present": True,
            },
            {
                "role": "global",
                "dataset_id": "commodity.gold.xaucny.close_ref",
                "registry_status": "PROPOSED",
                "exists": True,
                "rows": 30,
                "sha256": "b" * 64,
                "asof": headline,
                "selected_asof_present": True,
            },
        ],
    }

    blockers = audit.live_ready_violations(
        doc,
        required_method="close_proxy",
        require_machine_projection=True,
        require_source_artifacts=True,
    )

    assert "source artifact sge registry status is REJECTED" in blockers


def _dataos_promotion_receipt(root=None):
    import hashlib
    from datetime import datetime, timezone

    sge_bytes = b"sge-parquet-fixture"
    global_bytes = b"global-parquet-fixture"
    if root is not None:
        source_dir = root / "data" / "gold_china_basis"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_dir.joinpath("sge_au9999.parquet").write_bytes(sge_bytes)
        source_dir.joinpath("xaucny_spot.parquet").write_bytes(global_bytes)

    return {
        "schema": "commodity.china_gold_premium_quality.v1",
        "close_proxy_dataos_promotion_ready": True,
        "close_proxy_dataos_promotion_blockers": [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "available_fresh",
        "headline_method": "close_proxy",
        "render_consistent": True,
        "machine_projection_consistent": True,
        "stats_5_ready": True,
        "stats_30_ready": True,
        "source_asof": "2026-09-18T07:30:00+00:00",
        "source_artifacts": [
            {
                "role": "sge",
                "dataset_id": "commodity.gold.sge_au9999.close",
                "registry_status": "PROPOSED",
                "path": "data/gold_china_basis/sge_au9999.parquet",
                "exists": True,
                "rows": 30,
                "sha256": hashlib.sha256(sge_bytes).hexdigest(),
                "selected_asof_present": True,
            },
            {
                "role": "global",
                "dataset_id": "commodity.gold.xaucny.close_ref",
                "registry_status": "PROPOSED",
                "path": "data/gold_china_basis/xaucny_spot.parquet",
                "exists": True,
                "rows": 30,
                "sha256": hashlib.sha256(global_bytes).hexdigest(),
                "selected_asof_present": True,
            },
        ],
    }


def _dataos_promotion_registry_text():
    return """schema: dataset_registry.v1
updated: "2026-09-19"
datasets:
  - dataset_id: commodity.gold.sge_au9999.close
    layer: L1
    status: PROPOSED
    storage: data/gold_china_basis/sge_au9999.parquet
  - dataset_id: commodity.gold.xaucny.close_ref
    layer: L1
    status: PROPOSED
    storage: data/gold_china_basis/xaucny_spot.parquet
  - dataset_id: unrelated.fixture
    layer: L1
    status: PROPOSED
    storage: data/unrelated.parquet
"""


def test_china_gold_dataos_promoter_dry_run_plans_exact_two_rows(tmp_path):
    import json

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    receipt.write_text(json.dumps(_dataos_promotion_receipt(tmp_path)))
    before = _dataos_promotion_registry_text()
    registry.write_text(before)

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=False,
    )

    assert result["eligible"] is True
    assert result["pending"] == [
        "commodity.gold.sge_au9999.close",
        "commodity.gold.xaucny.close_ref",
    ]
    assert result["already_produced"] == []
    assert result["blockers"] == []
    assert registry.read_text() == before


def test_china_gold_dataos_promoter_apply_updates_only_two_target_statuses(tmp_path):
    import json
    import yaml

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    receipt.write_text(json.dumps(_dataos_promotion_receipt(tmp_path)))
    registry.write_text(_dataos_promotion_registry_text())

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=True,
    )

    payload = yaml.safe_load(registry.read_text())
    statuses = {
        row["dataset_id"]: row["status"]
        for row in payload["datasets"]
    }
    assert result["eligible"] is True
    assert result["applied"] == list(promote.TARGET_DATASET_IDS)
    assert result["pending"] == []
    assert statuses["commodity.gold.sge_au9999.close"] == "PRODUCED"
    assert statuses["commodity.gold.xaucny.close_ref"] == "PRODUCED"
    assert statuses["unrelated.fixture"] == "PROPOSED"


def test_china_gold_dataos_promoter_is_idempotent_after_production(tmp_path):
    import json

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    receipt.write_text(json.dumps(_dataos_promotion_receipt(tmp_path)))
    registry.write_text(
        _dataos_promotion_registry_text().replace(
            "status: PROPOSED",
            "status: PRODUCED",
            2,
        )
    )
    before = registry.read_text()

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=True,
    )

    assert result["eligible"] is True
    assert result["applied"] == []
    assert result["already_produced"] == list(promote.TARGET_DATASET_IDS)
    assert registry.read_text() == before


def test_china_gold_dataos_promoter_refuses_receipt_without_live_proof(tmp_path):
    import json

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    doc = _dataos_promotion_receipt(tmp_path)
    doc["close_proxy_dataos_promotion_ready"] = False
    doc["close_proxy_dataos_promotion_blockers"] = ["source artifacts were not proven"]
    receipt.write_text(json.dumps(doc))
    before = _dataos_promotion_registry_text()
    registry.write_text(before)

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=True,
    )

    assert result["eligible"] is False
    assert result["applied"] == []
    assert "quality receipt is not close-proxy Data OS promotion-ready" in result["blockers"]
    assert registry.read_text() == before


def test_china_gold_dataos_promoter_refuses_source_file_changed_since_receipt(tmp_path):
    import json

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    registry.write_text(_dataos_promotion_registry_text())
    doc = _dataos_promotion_receipt(tmp_path)
    receipt.write_text(json.dumps(doc))

    source_dir = tmp_path / "data" / "gold_china_basis"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_dir.joinpath("sge_au9999.parquet").write_bytes(b"changed-after-receipt")
    source_dir.joinpath("xaucny_spot.parquet").write_bytes(b"changed-after-receipt")

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=False,
    )

    assert result["eligible"] is False
    assert any("current sha256 does not match receipt" in x for x in result["blockers"])


def test_china_gold_dataos_promoter_revalidates_live_receipt_fields(tmp_path):
    import json

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    registry.write_text(_dataos_promotion_registry_text())
    doc = _dataos_promotion_receipt(tmp_path)
    # A single forged/stale ready bit must not override the underlying proof.
    doc.update(
        {
            "status": "available_fresh",
            "headline_method": "close_proxy",
            "render_consistent": False,
            "machine_projection_consistent": True,
            "stats_5_ready": True,
            "stats_30_ready": True,
            "source_asof": "2026-09-18T07:30:00+00:00",
        }
    )
    receipt.write_text(json.dumps(doc))

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=False,
    )

    assert result["eligible"] is False
    assert "quality receipt render contract is not consistent" in result["blockers"]


def test_china_gold_dataos_promoter_rejects_stale_receipt_replay(tmp_path):
    import json
    from datetime import datetime, timezone

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    registry.write_text(_dataos_promotion_registry_text())
    doc = _dataos_promotion_receipt(tmp_path)
    doc["checked_at"] = "2026-09-17T10:00:00+00:00"
    receipt.write_text(json.dumps(doc))

    result = promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=False,
        now=datetime(2026, 9, 19, 16, 0, tzinfo=timezone.utc),
    )

    assert result["eligible"] is False
    assert "quality receipt is older than 24 hours" in result["blockers"]


def test_china_gold_dataos_promoter_apply_stamps_registry_update_date(tmp_path):
    import json
    import yaml
    from datetime import datetime, timezone

    from scripts import promote_china_gold_dataos as promote

    receipt = tmp_path / "receipt.json"
    registry = tmp_path / "dataset_registry.yml"
    doc = _dataos_promotion_receipt(tmp_path)
    doc["checked_at"] = "2026-09-20T01:00:00+00:00"
    receipt.write_text(json.dumps(doc))
    registry.write_text(_dataos_promotion_registry_text())

    promote.promote(
        receipt_path=receipt,
        registry_path=registry,
        apply=True,
        now=datetime(2026, 9, 20, 2, 0, tzinfo=timezone.utc),
    )

    payload = yaml.safe_load(registry.read_text())
    assert payload["updated"] == "2026-09-20"
