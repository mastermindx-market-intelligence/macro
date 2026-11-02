"""Pure-function tests for the strategic-reserves display leaf (no network).

Covers fill/cover/change helpers, the country-row merge (curated + live JODI),
the global aggregate, and — critically — the invariant that this display leaf is
never wired into any scoring path.
"""
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import strategic_reserves as sr  # noqa: E402


def _monthly(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"level": values, "assess": [1] * len(values)}, index=idx)


def test_fill_pct():
    assert sr.fill_pct(357, 714) == 50.0
    assert sr.fill_pct(None, 714) is None
    assert sr.fill_pct(300, 0) is None
    assert sr.fill_pct(300, None) is None


def test_change_and_pct():
    s = _monthly([100, 110, 90, 120])["level"]
    assert sr.change(s, 1) == 30.0            # 120 - 90
    assert sr.change(s, 3) == 20.0            # 120 - 100
    assert sr.change(None, 1) is None
    assert sr.pct_change(s, 3) == 20.0        # +20% over 3 steps
    # asking for more periods than history clamps to the earliest point, never crashes
    assert sr.change(s, 99) == 20.0


def test_days_of_cover():
    assert sr.days_of_cover(357_000, 16_000) == 22.3   # kbbl / (kbbl/d)
    assert sr.days_of_cover(357_000, 0) is None
    assert sr.days_of_cover(None, 16_000) is None


def test_trend_word():
    assert sr.trend_word(_monthly([100, 101, 103, 110])["level"], months=3) == "rising"
    assert sr.trend_word(_monthly([110, 105, 100, 90])["level"], months=3) == "falling"
    assert sr.trend_word(_monthly([100, 100.2, 99.9, 100.1])["level"], months=3) == "flat"
    assert sr.trend_word(None) == "—"


def test_assess_word():
    assert sr.assess_word(1) == "reported"
    assert sr.assess_word(3) == "estimate"
    assert sr.assess_word(3, lang="zh") == "估算"
    assert sr.assess_word(None) == ""


def test_series_is_nan_and_unit_safe():
    df = _monthly([100.0, np.nan, 120.0])
    s = sr.series(df)
    assert sr.last_value(df) == 120.0          # trailing handled, NaN dropped
    assert len(s) == 2
    assert sr.series(None) is None


def test_global_aggregate():
    m = {"US": _monthly([730_000]), "JP": _monthly([330_000]), "KR": _monthly([100_000])}
    agg = sr.global_aggregate(m)
    assert agg["n_reporting"] == 3
    assert agg["total_mb"] == 1160.0           # (730000+330000+100000)/1000
    assert sr.global_aggregate({})["total_mb"] is None


def test_merge_country_row_us_live_override():
    cfg = {"iso": "US", "name": "United States", "flag": "🇺🇸", "live": "spr",
           "strategic_mb": 413, "strategic_type": "government", "capacity_mb": 714,
           "days_cover": 125, "source": "EIA", "as_of": "2025-12"}
    jodi = _monthly([700_000, 720_000])        # total US crude (incl commercial+SPR)
    row = sr.merge_country_row(cfg, jodi, live_level_mb=349.0)
    assert row["live"] is True
    assert row["strategic_mb"] == 349.0        # live SPR overrides the curated 413
    assert row["fill_pct"] == round(100 * 349 / 714, 1)
    assert row["jodi_total_mb"] == 720.0       # MMbbl
    assert row["jodi_mom_mb"] == 20.0
    assert row["jodi_assess"] == 1


def test_merge_country_row_china_no_jodi():
    cfg = {"iso": "CN", "name": "China", "flag": "🇨🇳", "no_jodi": True,
           "strategic_mb": 360, "total_mb": 1400, "strategic_type": "estimate",
           "source": "EIA est.", "as_of": "2025-12"}
    # even if a JODI frame is passed, no_jodi must suppress the live column
    row = sr.merge_country_row(cfg, _monthly([1, 2, 3]))
    assert row["jodi_total_mb"] is None
    assert row["strategic_mb"] == 360
    assert row["curated_total_mb"] == 1400


def test_caveat_is_bilingual_and_non_directional():
    for k in ("en", "zh"):
        assert k in sr.SPR_CAVEAT and len(sr.SPR_CAVEAT[k]) > 40
    assert "not a price signal" in sr.SPR_CAVEAT["en"]


def _annual(values, start_year=2022):
    idx = pd.to_datetime([f"{start_year + i}-12-31" for i in range(len(values))])
    return pd.Series(values, index=idx, dtype="float64")


def _monthly_flow(values, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"level": values, "assess": [1] * len(values)}, index=idx)


def test_net_imports_smoothed():
    imp = _monthly_flow([6000, 6200, 6400])     # kbd
    exp = _monthly_flow([3000, 3400, 3800])
    # trailing-window mean of imports − mean of exports
    assert sr.net_imports(imp, exp, window=3) == round((6200) - (3400), 1)
    assert sr.net_imports(imp, None, window=3) == 6200.0   # missing exports -> 0
    assert sr.net_imports(None, exp) is None
    # net exporter -> negative (caller skips import-cover)
    assert sr.net_imports(_monthly_flow([100]), _monthly_flow([500])) == -400.0


def test_merge_country_row_trade_cover():
    cfg = {"iso": "JP", "name": "Japan", "flag": "🇯🇵"}
    crude = _annual([300_000, 330_000])           # kbbl (reused annual helper ok)
    imp = _monthly_flow([2700, 2730])             # kbd
    exp = _monthly_flow([0, 0])
    row = sr.merge_country_row(cfg, crude, jodi_imports=imp, jodi_exports=exp)
    assert row["net_imports_kbd"] == 2715.0       # mean(2700,2730) − 0
    assert row["stock_cover_days"] == sr.days_of_cover(330_000, 2715.0)


def test_gold_value_share():
    assert sr.gold_value_share(100.0, 25.0) == {"value_usd": 75.0, "share_pct": 75.0}
    assert sr.gold_value_share(None, 25.0)["value_usd"] is None
    assert sr.gold_value_share(0.0, 0.0)["value_usd"] is None
    assert sr.gold_value_share(100.0, 120.0)["value_usd"] is None   # negative -> guarded


def test_total_official_tonnes():
    rows = [{"tonnes": 8133.5}, {"tonnes": 2280.0}, {"tonnes": None}]
    assert sr.total_official_tonnes(rows) == 10414.0
    assert sr.total_official_tonnes([]) is None


def test_merge_gold_row_live():
    cfg = {"iso": "USA", "name": "United States", "flag": "🇺🇸", "tonnes": 8133.5,
           "trend": "stable"}
    total = _annual([770.0, 910.0])     # 2022, 2023
    exgold = _annual([220.0, 228.0])
    row = sr.merge_gold_row(cfg, total, exgold)
    assert row["tonnes"] == 8133.5
    assert row["trend_en"] == "stable"
    assert row["value_usd"] == 910.0 - 228.0          # latest gold value
    assert row["share_pct"] == round(100 * 682 / 910, 1)
    # YoY value vs prior year: (910-228)/(770-220) - 1
    assert row["value_yoy_pct"] == round(100 * (682 / 550 - 1), 1)


def test_merge_gold_row_no_wb():
    cfg = {"iso": "TWN", "name": "Taiwan", "flag": "🇹🇼", "tonnes": 423.6,
           "trend": "stable", "no_wb": True}
    row = sr.merge_gold_row(cfg, _annual([1, 2]), _annual([1, 1]))
    assert row["tonnes"] == 423.6
    assert row["value_usd"] is None and row["share_pct"] is None   # suppressed


def test_gold_caveat_bilingual():
    for k in ("en", "zh"):
        assert k in sr.GOLD_CAVEAT and len(sr.GOLD_CAVEAT[k]) > 40
    assert "not a trade signal" in sr.GOLD_CAVEAT["en"]


def test_leaf_is_never_wired_into_a_scoring_path():
    """Guardrail: strategic reserves are DISPLAY-ONLY. The leaf must not import any
    scoring/alert/conviction module."""
    import_lines = "\n".join(ln for ln in inspect.getsource(sr).splitlines()
                             if ln.strip().startswith(("import ", "from ")))
    for forbidden in ("conviction", "alerts", "signals", "master_brain", "axes",
                      "regime", "meta_label"):
        assert forbidden not in import_lines, f"leaf must not import {forbidden}"


# P12.T22: a named weekly comparison must not borrow a shorter window.
def _weekly_spr(values):
    return pd.Series(values, index=pd.date_range("2025-10-31", periods=len(values), freq="W-FRI"))


def _spr_vm(monkeypatch, values, feeds=None):
    from scripts import build_spr
    feeds = feeds or {}
    monkeypatch.setattr(build_spr.store, "read", lambda group, name: feeds.get(name))
    return build_spr._us_spr_vm(_weekly_spr(values), {"spr_capacity_mb": 714.0})


def _render_spr_context(us):
    from jinja2 import Environment, StrictUndefined
    source = (Path(__file__).resolve().parents[1] / "templates/spr.html.j2").read_text()
    macros = source[:source.index("<!DOCTYPE html>")]
    hero = source[source.index("  <!-- ===================== US SPR HERO"):
                  source.index("  <!-- ===================== SPR vs OIL PRICE")]
    return Environment(autoescape=True, undefined=StrictUndefined).from_string(macros + hero).render(
        us=us, caveat=sr.SPR_CAVEAT, as_of=us["as_of"])


def test_us_spr_named_windows_require_the_requested_observations(monkeypatch):
    for count, four, fifty_two in ((1, None, None), (2, None, None), (4, None, None),
                                   (5, 4.0, None), (52, 4.0, None), (53, 4.0, 52.0)):
        vm = _spr_vm(monkeypatch, [400000 + 1000 * i for i in range(count)])
        assert vm["chg_4w_mb"] == four, count
        assert vm["chg_52w_mb"] == fifty_two, count
        assert vm["level_mb"] == 400 + count - 1
        assert vm["as_of"] == _weekly_spr(range(count)).index[-1].strftime("%b %d, %Y")


def test_us_spr_measured_flat_and_signed_full_history_are_preserved(monkeypatch):
    flat = _spr_vm(monkeypatch, [400000] * 53)
    assert flat["chg_4w_mb"] == flat["chg_52w_mb"] == 0.0
    declining = _spr_vm(monkeypatch, [400000 - 1000 * i for i in range(60)])
    assert declining["chg_4w_mb"] == -4.0
    assert declining["chg_52w_mb"] == -52.0


def test_us_spr_missing_comparisons_render_unavailable_not_flat(monkeypatch):
    import re
    missing = _render_spr_context(_spr_vm(monkeypatch, [400000]))
    flat = _render_spr_context(_spr_vm(monkeypatch, [400000] * 53))
    metric = r'<div class="v [^"]*">(.*?)<small> M</small>'
    assert re.findall(metric, missing)[:2] == ["—", "—"]
    assert re.findall(metric, flat)[:2] == ["+0.0", "+0"]
    assert "4-week" in missing and "4周" in missing
    assert "52-week" in missing and "52周" in missing
    assert "Comparison unavailable where the weekly endpoint is missing." in missing
    assert "缺少每周比较端点的窗口暂不可用。" in missing
    assert "Comparison unavailable where the weekly endpoint is missing." not in flat


def test_us_spr_optional_feed_fields_are_explicit_and_render_independently(monkeypatch):
    cases = (
        ({}, (), ("imp", "exp", "net")),
        ({"crude_imports": 7000.0}, (("7.0", "imp", "进"),), ("exp", "net")),
        ({"crude_exports": 5000.0}, (("5.0", "exp", "出"),), ("imp", "net")),
        ({"crude_net_imports": 1000.0}, (("1.0", "net", "净"),), ("imp", "exp")),
        ({"crude_imports": 0.0, "crude_exports": 0.0},
         (("0.0", "imp", "进"), ("0.0", "exp", "出")), ("net",)),
        ({"crude_imports": 7000.0, "crude_exports": 5000.0, "crude_net_imports": 2000.0},
         (("7.0", "imp", "进"), ("5.0", "exp", "出"), ("2.0", "net", "净")), ()),
    )
    import re
    for feeds, expected, absent in cases:
        vm = _spr_vm(monkeypatch, [400000] * 53,
                     {name: _weekly_spr([value] * 53) for name, value in feeds.items()})
        assert all(key in vm for key in ("days_cover", "import_cover_days", "imports_mbd",
                                        "exports_mbd", "net_imports_mbd"))
        rendered = _render_spr_context(vm)
        row = re.search(r'US crude trade.*?</div>', rendered, re.S)
        if not expected:
            assert row is None
            continue
        assert row is not None
        text = row.group()
        for value, en, zh in expected:
            assert f"<b>{value}</b>" in text
            assert f'class="l-en">{en}</span>' in text
            assert f'class="l-zh">{zh}</span>' in text
        for en in absent:
            assert f'class="l-en">{en}</span>' not in text
        assert "undefined" not in text.lower() and "None" not in text



def test_us_spr_named_windows_use_dated_endpoints_despite_interior_gaps(monkeypatch):
    from scripts import build_spr
    monkeypatch.setattr(build_spr.store, "read", lambda *args: None)
    full = _weekly_spr([400000 + 1000 * i for i in range(60)])
    scfg = {"spr_capacity_mb": 714.0}
    missing_four = build_spr._us_spr_vm(full.drop(full.index[-5]), scfg)
    assert missing_four["chg_4w_mb"] is None and missing_four["chg_52w_mb"] == 52.0
    missing_year = build_spr._us_spr_vm(full.drop(full.index[-53]), scfg)
    assert missing_year["chg_52w_mb"] is None and missing_year["chg_4w_mb"] == 4.0
    endpoints_only = build_spr._us_spr_vm(full.iloc[[-53, -1]], scfg)
    assert endpoints_only["chg_52w_mb"] == 52.0 and endpoints_only["chg_4w_mb"] is None
    four_endpoints = build_spr._us_spr_vm(full.iloc[[-5, -1]], scfg)
    assert four_endpoints["chg_4w_mb"] == 4.0 and four_endpoints["chg_52w_mb"] is None


def test_us_spr_partial_trade_average_uses_truthful_bilingual_basis(monkeypatch):
    feeds = {"crude_exports": _weekly_spr([5000.0])}
    vm = _spr_vm(monkeypatch, [400000] * 53, feeds)
    assert vm["exports_mbd"] == 5.0 and vm["trade_basis"] is False
    rendered = _render_spr_context(vm)
    assert "available-history avg" in rendered and "已有历史均值" in rendered
    assert "1y avg" not in rendered
    full = _spr_vm(monkeypatch, [400000] * 53,
                   {"crude_exports": _weekly_spr([5000.0] * 53)})
    assert full["trade_basis"] is True and "1y avg" in _render_spr_context(full)


def test_us_spr_partial_net_import_cover_names_its_available_history(monkeypatch):
    vm = _spr_vm(monkeypatch, [400000] * 53,
                 {"crude_net_imports": _weekly_spr([1000.0])})
    assert vm["import_cover_days"] == 400.0 and vm["net_imports_mbd"] == 1.0
    rendered = _render_spr_context(vm)
    assert "available-history mean of net crude imports" in rendered
    assert "原油净进口已有历史均值" in rendered
    assert "52-week mean" not in rendered


def test_us_spr_gapped_trade_history_does_not_claim_one_year(monkeypatch):
    exports = _weekly_spr([5000.0] * 60)
    exports = exports.drop(exports.index[-3])
    vm = _spr_vm(monkeypatch, [400000] * 53, {"crude_exports": exports})
    assert vm["exports_mbd"] == 5.0 and vm["trade_basis"] is False
    assert "available-history avg" in _render_spr_context(vm)
