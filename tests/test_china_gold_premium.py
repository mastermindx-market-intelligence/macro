from __future__ import annotations

from importlib import import_module
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
import numpy as np
import pandas as pd
import pytest


TROY_OZ_GRAMS = 31.1034768


def _mod():
    return import_module("engine.china_gold_premium")


def _frame(values, start="2026-08-01", freq="D", column="value"):
    idx = pd.date_range(start, periods=len(values), freq=freq)
    return pd.DataFrame({column: values}, index=idx)


def _leg(group, name, column="value", label="Fixture", entitled=True):
    return {
        "group": group,
        "name": name,
        "column": column,
        "source_label": label,
        "entitled": entitled,
    }


def test_daily_benchmark_matches_screenshot_formula():
    m = _mod()
    usdcny = 7.0
    target_sge_usd_oz = 4398.94
    sge_rmb_g = target_sge_usd_oz * usdcny / TROY_OZ_GRAMS

    out = m.compute_daily_benchmark(
        _frame([sge_rmb_g], column="sge"),
        _frame([4391.59], column="london"),
        _frame([usdcny], column="fx"),
        sge_column="sge",
        london_column="london",
        fx_column="fx",
    )

    assert len(out) == 1
    row = out.iloc[-1]
    assert row["sge_usd_oz"] == pytest.approx(4398.94, abs=1e-6)
    assert row["spread_usd_oz"] == pytest.approx(7.35, abs=1e-6)
    assert row["premium_pct"] == pytest.approx((4398.94 / 4391.59 - 1) * 100, abs=1e-9)


def test_daily_benchmark_uses_only_same_date_positive_finite_rows():
    m = _mod()
    sge = pd.DataFrame(
        {"v": [700.0, np.inf, -1.0, 710.0]},
        index=pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13"]),
    )
    london = pd.DataFrame(
        {"v": [3000.0, 3010.0, 3020.0]},
        index=pd.to_datetime(["2026-09-10", "2026-09-12", "2026-09-13"]),
    )
    fx = pd.DataFrame(
        {"v": [7.0, 7.0, 0.0]},
        index=pd.to_datetime(["2026-09-10", "2026-09-12", "2026-09-13"]),
    )

    out = m.compute_daily_benchmark(sge, london, fx, sge_column="v", london_column="v", fx_column="v")

    assert list(out.index) == [pd.Timestamp("2026-09-10")]
    assert np.isfinite(out.iloc[0]["premium_pct"])


def test_intraday_proxy_rejects_timestamp_skew_and_accepts_aligned_snapshots():
    m = _mod()
    sge = pd.DataFrame({"v": [700.0]}, index=[pd.Timestamp("2026-09-18T02:00:00Z")])
    london = pd.DataFrame({"v": [3100.0]}, index=[pd.Timestamp("2026-09-18T02:12:00Z")])
    fx = pd.DataFrame({"v": [7.0]}, index=[pd.Timestamp("2026-09-18T02:10:00Z")])

    ok = m.compute_intraday_proxy(
        sge, london, fx, sge_column="v", london_column="v", fx_column="v", max_skew_minutes=15
    )
    assert len(ok) == 1
    assert ok.iloc[0]["methodology"] == "intraday_indicative"

    rejected = m.compute_intraday_proxy(
        sge, london, fx, sge_column="v", london_column="v", fx_column="v", max_skew_minutes=5
    )
    assert rejected.empty


def test_build_view_model_requires_every_source_leg_to_be_explicitly_entitled():
    m = _mod()
    frames = {
        ("sge", "pm"): _frame([700.0]),
        ("lbma", "am"): _frame([3100.0]),
        ("fx", "usdcny"): _frame([7.0]),
    }

    def reader(group, name):
        return frames.get((group, name))

    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm", label="SGE benchmark"),
            "london": _leg("lbma", "am", label="London benchmark", entitled=False),
            "fx": _leg("fx", "usdcny", label="USDCNY"),
        }
    }

    vm = m.build_view_model(cfg, reader=reader, now=pd.Timestamp("2026-08-01T18:00:00Z"))

    assert vm["available"] is False
    assert vm["status"] == "unavailable"
    assert vm["reason_code"] == "source_not_entitled"
    assert "entitled" in vm["reason_en"].lower()


def test_build_view_model_prefers_fresh_intraday_but_keeps_canonical_history_separate():
    m = _mod()
    dates = pd.date_range("2026-08-01", periods=35, freq="D")
    sge_values = pd.Series(np.linspace(680.0, 714.0, 35), index=dates)
    london_values = pd.Series(np.linspace(3000.0, 3034.0, 35), index=dates)
    fx_values = pd.Series(np.full(35, 7.0), index=dates)

    frames = {
        ("sge", "pm"): pd.DataFrame({"value": sge_values}),
        ("lbma", "am"): pd.DataFrame({"value": london_values}),
        ("fx", "daily"): pd.DataFrame({"value": fx_values}),
        ("sge", "au9999"): pd.DataFrame(
            {"value": [715.0]}, index=[pd.Timestamp("2026-09-04T02:00:00Z")]
        ),
        ("lbma", "spot"): pd.DataFrame(
            {"value": [3040.0]}, index=[pd.Timestamp("2026-09-04T02:03:00Z")]
        ),
        ("fx", "intraday"): pd.DataFrame(
            {"value": [7.0]}, index=[pd.Timestamp("2026-09-04T02:02:00Z")]
        ),
    }

    def reader(group, name):
        return frames.get((group, name))

    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm", label="SGE SHAUPM"),
            "london": _leg("lbma", "am", label="LBMA AM"),
            "fx": _leg("fx", "daily", label="USDCNY daily"),
            "max_age_days": 10,
        },
        "intraday": {
            "sge": _leg("sge", "au9999", label="SGE Au99.99"),
            "london": _leg("lbma", "spot", label="London spot"),
            "fx": _leg("fx", "intraday", label="USDCNY"),
            "max_skew_minutes": 10,
            "max_age_minutes": 30,
        },
    }

    vm = m.build_view_model(cfg, reader=reader, now=pd.Timestamp("2026-09-04T02:10:00Z"))

    assert vm["available"] is True
    assert vm["current_method"] == "intraday"
    assert vm["methodology_label_en"] == "Indicative intraday basis"
    assert vm["canonical"]["available"] is True
    assert vm["intraday"]["available"] is True
    assert len(vm["chart"]["canonical"]) == 35
    assert vm["chart"]["intraday"] is not None
    assert vm["stats"]["avg_5"] == pytest.approx(
        pd.Series([p["premium_pct"] for p in vm["chart"]["canonical"]]).tail(5).mean()
    )
    last_30 = pd.Series([p["premium_pct"] for p in vm["chart"]["canonical"]]).tail(30)
    assert vm["stats"]["range_30"] == pytest.approx([last_30.min(), last_30.max()])


def test_build_view_model_without_config_is_honestly_unavailable():
    m = _mod()
    vm = m.build_view_model({}, reader=lambda *_: None, now=pd.Timestamp("2026-09-18T12:00:00Z"))

    assert vm["available"] is False
    assert vm["reason_code"] == "not_configured"
    assert "configured" in vm["reason_en"].lower()
    assert vm["chart"]["canonical"] == []
    assert vm["chart"]["intraday"] is None


def test_commodity_builder_attaches_monitor_only_to_gold():
    from scripts import build_commodities

    vm = {
        "detail": [
            {"name": "gold", "label_en": "Gold"},
            {"name": "silver", "label_en": "Silver"},
            {"name": "copper", "label_en": "Copper"},
            {"name": "oil", "label_en": "Oil"},
        ]
    }

    out = build_commodities._attach_china_gold_premium(
        vm,
        {"china_gold_premium": {}},
        reader=lambda *_: None,
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    gold = next(row for row in out["detail"] if row["name"] == "gold")
    assert gold["china_gold_premium"]["reason_code"] == "not_configured"
    for name in ("silver", "copper", "oil"):
        row = next(row for row in out["detail"] if row["name"] == name)
        assert "china_gold_premium" not in row


def _available_ui_vm():
    return {
        "available": True,
        "status": "available",
        "reason_code": None,
        "reason_en": None,
        "reason_zh": None,
        "current_method": "intraday",
        "methodology_label_en": "Indicative intraday basis",
        "methodology_label_zh": "日内指示性价差",
        "state": "premium",
        "state_en": "Premium",
        "state_zh": "溢价",
        "premium_pct": 0.1674,
        "spread_usd_oz": 7.35,
        "sge_usd_oz": 4398.94,
        "london_usd_oz": 4391.59,
        "price_currency": "USD",
        "spread_price_oz": 7.35,
        "sge_price_oz": 4398.94,
        "reference_price_oz": 4391.59,
        "stats": {"avg_5": 0.22, "range_30": [-0.23, 0.41]},
        "canonical": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18",
            "sources": ["SGE SHAUPM", "LBMA AM", "USDCNY"],
        },
        "intraday": {
            "available": True,
            "fresh": True,
            "asof": "2026-09-18T02:10:00+00:00",
            "sources": ["SGE Au99.99", "London spot", "USDCNY"],
        },
        "chart": {
            "canonical": [
                {
                    "date": "2026-09-16",
                    "premium_pct": 0.12,
                    "spread_usd_oz": 5.1,
                    "sge_usd_oz": 4305.1,
                    "london_usd_oz": 4300.0,
                    "spread_price_oz": 5.1,
                    "sge_price_oz": 4305.1,
                    "reference_price_oz": 4300.0,
                    "ma5_pct": 0.10,
                },
                {
                    "date": "2026-09-17",
                    "premium_pct": -0.08,
                    "spread_usd_oz": -3.5,
                    "sge_usd_oz": 4346.5,
                    "london_usd_oz": 4350.0,
                    "spread_price_oz": -3.5,
                    "sge_price_oz": 4346.5,
                    "reference_price_oz": 4350.0,
                    "ma5_pct": 0.02,
                },
                {
                    "date": "2026-09-18",
                    "premium_pct": 0.17,
                    "spread_usd_oz": 7.35,
                    "sge_usd_oz": 4398.94,
                    "london_usd_oz": 4391.59,
                    "spread_price_oz": 7.35,
                    "sge_price_oz": 4398.94,
                    "reference_price_oz": 4391.59,
                    "ma5_pct": 0.07,
                },
            ],
            "proxy": [],
            "display_source": "canonical",
            "intraday": {
                "ts": "2026-09-18T02:10:00+00:00",
                "premium_pct": 0.1674,
                "spread_usd_oz": 7.35,
                "sge_usd_oz": 4398.94,
                "london_usd_oz": 4391.59,
                "ma5_pct": 0.1674,
            },
        },
    }


def _render_premium_partial(g):
    repo = Path(__file__).resolve().parents[1]
    env = Environment(
        loader=FileSystemLoader(str(repo / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env.get_template("_china_gold_premium.html.j2").render(g=g)


def test_gold_premium_partial_renders_three_modes_ranges_and_bilingual_copy():
    html = _render_premium_partial(_available_ui_vm())

    for text in (
        "China physical premium",
        "中国实物黄金溢价",
        "% Premium",
        "$/oz Spread",
        "Price Level",
        "1W",
        "1M",
        "3M",
        "6M",
        "1Y",
        "3Y",
        "Max",
        "Premium",
        "溢价",
        "+0.17%",
        "$4,398.94",
        "$4,391.59",
    ):
        assert text in html
    assert 'data-cgp-state="premium"' in html
    assert 'data-cgp-series=' in html
    assert 'class="cgp-chart"' in html


def test_gold_premium_partial_renders_honest_unavailable_state_without_fake_chart():
    m = _mod()
    vm = m.build_view_model({}, reader=lambda *_: None, now=pd.Timestamp("2026-09-18T12:00:00Z"))

    html = _render_premium_partial(vm)

    assert "Entitled Shanghai/London benchmark sources are not configured yet." in html
    assert "尚未配置已获授权的上海／伦敦基准数据源。" in html
    assert 'data-cgp-state="unavailable"' in html
    assert 'class="cgp-chart"' not in html
    assert "GC=F" not in html


def test_commodities_template_includes_monitor_only_inside_gold_detail():
    repo = Path(__file__).resolve().parents[1]
    src = (repo / "templates" / "commodities.html.j2").read_text()

    needle = '{% include "_china_gold_premium.html.j2" %}'
    assert needle in src
    include_at = src.index(needle)
    guard_at = src.rfind("{% if d.name == 'gold' %}", 0, include_at)
    end_at = src.find("{% endif %}", include_at)
    assert guard_at != -1
    assert end_at != -1


def test_gold_premium_partial_labels_stale_canonical_observation():
    vm = _available_ui_vm()
    vm["current_method"] = "canonical"
    vm["methodology_label_en"] = "Official daily benchmark basis"
    vm["methodology_label_zh"] = "官方日度基准价差"
    vm["canonical"]["fresh"] = False
    vm["intraday"]["available"] = False
    vm["intraday"]["fresh"] = False

    html = _render_premium_partial(vm)

    assert "Stale benchmark" in html
    assert "基准数据已陈旧" in html


def test_view_model_ignores_future_canonical_rows_before_selecting_current():
    m = _mod()
    now = pd.Timestamp("2026-09-18T18:00:00Z")
    frames = {
        ("sge", "pm"): pd.DataFrame(
            {"value": [700.0, 900.0]},
            index=pd.to_datetime(["2026-09-18", "2026-09-19"]),
        ),
        ("london", "am"): pd.DataFrame(
            {"value": [3100.0, 3200.0]},
            index=pd.to_datetime(["2026-09-18", "2026-09-19"]),
        ),
        ("fx", "daily"): pd.DataFrame(
            {"value": [7.0, 7.0]},
            index=pd.to_datetime(["2026-09-18", "2026-09-19"]),
        ),
    }
    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm", label="SGE SHAUPM"),
            "london": _leg("london", "am", label="LBMA AM"),
            "fx": _leg("fx", "daily", label="USDCNY"),
            "max_age_days": 5,
        }
    }

    vm = m.build_view_model(cfg, reader=lambda g, n: frames.get((g, n)), now=now)

    assert vm["available"] is True
    assert vm["current_method"] == "canonical"
    assert vm["canonical"]["asof"] == "2026-09-18"
    expected = (700.0 * TROY_OZ_GRAMS / 7.0 / 3100.0 - 1.0) * 100.0
    assert vm["premium_pct"] == pytest.approx(expected)


def test_stale_intraday_without_canonical_benchmark_is_unavailable():
    m = _mod()
    now = pd.Timestamp("2026-09-18T12:00:00Z")
    frames = {
        ("sge", "au9999"): pd.DataFrame(
            {"value": [700.0]}, index=[pd.Timestamp("2026-09-18T09:00:00Z")]
        ),
        ("london", "spot"): pd.DataFrame(
            {"value": [3100.0]}, index=[pd.Timestamp("2026-09-18T09:03:00Z")]
        ),
        ("fx", "intraday"): pd.DataFrame(
            {"value": [7.0]}, index=[pd.Timestamp("2026-09-18T09:02:00Z")]
        ),
    }
    cfg = {
        "intraday": {
            "sge": _leg("sge", "au9999", label="SGE Au99.99"),
            "london": _leg("london", "spot", label="London spot"),
            "fx": _leg("fx", "intraday", label="USDCNY"),
            "max_skew_minutes": 10,
            "max_age_minutes": 30,
        }
    }

    vm = m.build_view_model(cfg, reader=lambda g, n: frames.get((g, n)), now=now)

    assert vm["available"] is False
    assert vm["reason_code"] == "stale_observation"
    assert vm["chart"]["canonical"] == []
    assert vm["chart"]["intraday"] is None


def test_default_config_exposes_entitled_provider_seam_without_fake_sources():
    from lib import config

    premium_cfg = config.load()["commodities"]["china_gold_premium"]

    assert premium_cfg["canonical"] == {}
    assert premium_cfg["intraday"] == {}
    assert premium_cfg["close_proxy"]["sge"]["entitled"] is True
    assert premium_cfg["close_proxy"]["global"]["entitled"] is True


def test_malformed_optional_timing_config_fails_closed():
    m = _mod()
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
            "max_age_days": "not-a-number",
        }
    }

    vm = m.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-08-01T18:00:00Z"),
    )

    assert vm["available"] is False
    assert vm["reason_code"] == "source_config_invalid"


def test_malformed_source_timestamp_fails_closed_instead_of_crashing_page():
    m = _mod()
    frames = {
        ("sge", "pm"): pd.DataFrame({"value": [700.0]}, index=["not-a-date"]),
        ("london", "am"): _frame([3100.0]),
        ("fx", "daily"): _frame([7.0]),
    }
    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm"),
            "london": _leg("london", "am"),
            "fx": _leg("fx", "daily"),
        }
    }

    vm = m.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-08-01T18:00:00Z"),
    )

    assert vm["available"] is False
    assert vm["reason_code"] == "no_aligned_observation"


def test_builder_premium_failure_preserves_existing_commodity_detail(monkeypatch):
    from engine import china_gold_premium
    from scripts import build_commodities

    vm = {
        "stance": {"word_en": "Mixed conditions"},
        "detail": [
            {"name": "gold", "label_en": "Gold"},
            {"name": "silver", "label_en": "Silver"},
        ],
    }

    def boom(*args, **kwargs):
        raise RuntimeError("fixture premium engine failure")

    monkeypatch.setattr(china_gold_premium, "build_view_model", boom)

    out = build_commodities._attach_china_gold_premium(vm, {"china_gold_premium": {}})

    assert out["stance"]["word_en"] == "Mixed conditions"
    assert [row["name"] for row in out["detail"]] == ["gold", "silver"]
    gold = out["detail"][0]
    assert gold["china_gold_premium"]["available"] is False
    assert gold["china_gold_premium"]["reason_code"] == "source_data_unavailable"


def test_display_state_calls_values_that_render_zero_near_parity():
    m = _mod()

    assert m._state(0.004) == ("parity", "Near parity", "接近平价")
    assert m._state(-0.004) == ("parity", "Near parity", "接近平价")
    assert m._state(0.006)[0] == "premium"
    assert m._state(-0.006)[0] == "discount"


# China close-basis proxy render contract (stacked source slice).
def test_proxy_partial_renders_cny_close_basis_as_primary_display():
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from engine import china_gold_premium as cgp

    idx = pd.date_range("2026-09-10 07:30:00", periods=9, freq="D")
    frames = {
        ("basis", "sge"): pd.DataFrame({"v": [818.0 + i for i in range(9)]}, index=idx),
        ("basis", "global"): pd.DataFrame({"v": [25400.0 + 20 * i for i in range(9)]}, index=idx),
    }
    leg = lambda g, n, label: {
        "group": g, "name": n, "column": "v", "source_label": label, "entitled": True
    }
    vm = cgp.build_view_model(
        {
            "canonical": {},
            "intraday": {},
            "close_proxy": {
                "sge": leg("basis", "sge", "Shanghai Gold Exchange Au99.99"),
                "global": leg("basis", "global", "Global XAU/CNY spot"),
                "max_skew_minutes": 2,
                "max_age_days": 4,
            },
        },
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T12:00:00Z"),
    )

    repo = Path(__file__).resolve().parents[1]
    env = Environment(
        loader=FileSystemLoader(str(repo / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("_china_gold_premium.html.j2").render(g=vm)

    assert "Indicative Shanghai-close basis" in html
    assert "上海收盘指示性价差" in html
    assert "Shanghai CNY/oz" in html
    assert "Global spot CNY/oz" in html
    assert "CNY/oz Spread" in html
    assert 'data-cgp-display-source="proxy"' in html
    assert 'data-cgp-currency="CNY"' in html
    assert 'class="cgp-chart"' in html
    assert "Shanghai Gold Exchange Au99.99" in html
    assert "Global XAU/CNY spot" in html
    assert "Tushare" not in html
    assert "Massive" not in html


def test_gold_premium_partial_embeds_machine_proof_attrs_for_current_method():
    vm = _available_ui_vm()

    html = _render_premium_partial(vm)

    assert 'data-cgp-source-asof="2026-09-18T02:10:00+00:00"' in html
    assert 'data-cgp-premium="0.167400"' in html


def test_stats_do_not_mislabel_partial_history_as_5_or_30_sessions():
    m = _mod()
    dates = pd.date_range("2026-09-16", periods=3, freq="D")
    frames = {
        ("sge", "pm"): pd.DataFrame({"value": [700.0, 701.0, 702.0]}, index=dates),
        ("london", "am"): pd.DataFrame({"value": [3100.0, 3101.0, 3102.0]}, index=dates),
        ("fx", "daily"): pd.DataFrame({"value": [7.0, 7.0, 7.0]}, index=dates),
    }
    cfg = {
        "canonical": {
            "sge": _leg("sge", "pm", label="SGE SHAUPM"),
            "london": _leg("london", "am", label="LBMA AM"),
            "fx": _leg("fx", "daily", label="USDCNY"),
            "max_age_days": 5,
        }
    }

    vm = m.build_view_model(
        cfg,
        reader=lambda group, name: frames.get((group, name)),
        now=pd.Timestamp("2026-09-18T18:00:00Z"),
    )

    assert vm["available"] is True
    assert len(vm["chart"]["canonical"]) == 3
    assert vm["stats"]["avg_5"] is None
    assert vm["stats"]["range_30"] is None


def test_gold_premium_copy_describes_relative_pricing_without_claiming_demand_causality():
    html = _render_premium_partial(_available_ui_vm())

    assert "firmer local physical-market pricing" in html
    assert "demand, import constraints, supply, or market structure" in html
    assert "本地实物市场定价更强" in html
    assert "需求、进口约束、供应或市场结构" in html
    assert "firmer local physical demand" not in html
    assert "本地实物需求更强" not in html


def test_premium_chart_keeps_raw_line_continuous_across_zero_crossings():
    """Sign coloring must not create visible gaps where the basis crosses zero."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "templates" / "_china_gold_premium.html.j2").read_text()
    anchor = "var key=mode==='spread'?'spread_price_oz':'premium_pct';"
    continuous = "main.setAttribute('d',path(rows,key,min,max,null));"
    positive = "pos.setAttribute('d',path(rows,key,min,max,1));"
    negative = "neg.setAttribute('d',path(rows,key,min,max,-1));"

    assert anchor in src
    assert continuous in src
    assert src.index(anchor) < src.index(continuous) < src.index(positive) < src.index(negative)


def test_premium_chart_legend_tracks_selected_metric_in_both_languages():
    """Spread/price modes must not keep claiming the chart is premium + MA."""
    html = _render_premium_partial(_available_ui_vm())

    assert 'data-cgp-legend-main' in html
    assert 'data-cgp-legend-avg' in html
    assert 'data-cgp-legend-alt' in html
    assert 'function updateLegend()' in html
    assert "avg.hidden=mode!=='premium'" in html
    assert "alt.hidden=mode!=='price'" in html
    for text in (
        "Premium / discount",
        "Premium spread",
        "Shanghai price",
        "5-session avg",
        "London reference",
        "溢价 / 折价",
        "溢价价差",
        "上海价格",
        "5期均值",
        "伦敦参考价",
    ):
        assert text in html


def test_hidden_metric_legends_are_not_revived_by_component_display_css():
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / "templates" / "commodities.html.j2").read_text()
    assert ".cgp-leg[hidden] { display:none; }" in css


def test_intraday_without_compatible_canonical_history_does_not_render_blank_proxy_chart():
    vm = _available_ui_vm()
    vm["current_method"] = "intraday"
    vm["price_currency"] = "USD"
    vm["chart"] = {
        "canonical": [],
        "proxy": [
            {
                "date": "2026-09-18",
                "premium_pct": 0.12,
                "spread_price_oz": 30.0,
                "sge_price_oz": 25530.0,
                "reference_price_oz": 25500.0,
                "ma5_pct": 0.12,
            }
        ],
        "intraday": {
            "ts": "2026-09-18T02:10:00+00:00",
            "premium_pct": 0.1674,
            "spread_usd_oz": 7.35,
            "sge_usd_oz": 4398.94,
            "london_usd_oz": 4391.59,
            "ma5_pct": 0.1674,
        },
        "display_source": None,
    }

    html = _render_premium_partial(vm)

    assert "Indicative intraday basis" in html
    assert 'class="cgp-chart"' not in html
    assert "No compatible history for this intraday method yet." in html
    assert "当前日内方法尚无兼容的历史序列。" in html
    assert "Proxy history remains methodologically separate." in html


def test_gold_premium_partial_renders_accessible_table_for_active_history():
    html = _render_premium_partial(_available_ui_vm())

    assert '<details class="cgp-data">' in html
    assert '<table class="cgp-data-table">' in html
    assert '<caption>' in html
    assert 'China gold premium history table' in html
    assert '中国黄金溢价历史表' in html
    assert 'scope="col"' in html
    for text in (
        "Observation",
        "Premium %",
        "Spread / oz",
        "Shanghai / oz",
        "Reference / oz",
        "5-session avg",
        "2026-09-16",
        "+0.12%",
        "+5.10",
        "4,305.10",
        "4,300.00",
        "+0.10%",
    ):
        assert text in html


def test_intraday_without_compatible_history_omits_data_table():
    vm = _available_ui_vm()
    vm["current_method"] = "intraday"
    vm["chart"] = {
        "canonical": [],
        "proxy": [],
        "intraday": vm["chart"]["intraday"],
        "display_source": None,
    }

    html = _render_premium_partial(vm)

    assert '<table class="cgp-data-table">' not in html
