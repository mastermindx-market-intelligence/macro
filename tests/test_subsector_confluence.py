"""Tests for the Subsector Confluence desk (engine/subsector_confluence.py).

Pure-logic tests (classification, the double-gate factor, the funnel) run with no data.
A guarded integration test exercises the real composition (basket index -> cascade ->
regime) on one S&P sub-industry IF the OHLCV store is present.
"""
from __future__ import annotations

import pytest

from engine import subsector_confluence as sc


# ----------------------------------------------------------------- pure logic ----

def test_slug():
    assert sc._slug("Software - Infrastructure") == "software-infrastructure"
    assert sc._slug("Diagnostics & Research") == "diagnostics-research"
    assert sc._slug("REIT - Healthcare Facilities") == "reit-healthcare-facilities"
    assert sc._slug("") == "x"


def test_seed_members_dedupes_and_shapes():
    m = sc._seed_members(["AAPL", "MSFT", "AAPL", None, "NVDA"])
    assert [x["ticker"] for x in m] == ["AAPL", "MSFT", "NVDA"]
    assert all(x["removed"] is None and "added" in x for x in m)


def test_classify_headwind_dominates_buyable():
    # a fresh cascade tier that coincides with a TOPPING/SELL regime is NOT entry-now —
    # the validated AVOID edge wins (don't label a distributing subsector buy-ready).
    assert sc._classify(buyable=True, tier="T1", state="TOPPING") == "headwind"
    assert sc._classify(buyable=True, tier="T2", state="SELL") == "headwind"


def test_classify_entry_forming_tailwind_late_neutral():
    assert sc._classify(True, "T1", "EXTENDED") == "entry_now"       # buyable, not headwind
    assert sc._classify(True, "T2", "BELOW_TREND") == "entry_now"
    assert sc._classify(False, "T4", "NEUTRAL") == "forming"
    assert sc._classify(False, None, "BUY_PARTIAL") == "tailwind"
    assert sc._classify(False, None, "EXTENDED") == "late"
    assert sc._classify(False, None, "NEUTRAL") == "neutral"


def test_subsector_factor_is_max_of_entry_and_regime_and_zero_for_headwind():
    assert sc._subsector_factor(1.0, "BELOW_TREND") == 1.0          # entry tier dominates
    assert sc._subsector_factor(0.0, "BUY_PARTIAL") == 0.60         # regime carries it
    assert sc._subsector_factor(0.4, "BUY") == 0.80                 # regime > weak tier
    assert sc._subsector_factor(0.0, "TOPPING") == 0.0             # headwind contributes nothing
    assert sc._subsector_factor(0.0, "SELL") == 0.0


def _grp(key, state, entry_tier, entry_w, buyable, members):
    tailwind = state in sc._TAILWIND_STATES
    headwind = state in sc._HEADWIND_STATES
    return {
        "key": key, "label": key, "sector": "X", "kind": "subsector",
        "entry": {"tier": entry_tier, "weight": entry_w, "buyable": buyable},
        "regime": {"state": state, "side": "buy" if tailwind else ("avoid" if headwind else "neutral"),
                   "tailwind": tailwind, "headwind": headwind},
        "members": members,
    }


def _mem(tk, tier, w, buyable, vs=0.0):
    return {"ticker": tk, "price": 10.0, "stock_tier": tier, "stock_weight": w,
            "stock_ticks": 0, "stock_bars_to_cross": None, "stock_buyable": buyable, "vs_basket": vs}


def test_funnel_double_buy_and_headwind_split():
    groups = [
        # entry-now subsector (T1) -> its buyable member is a top double-buy (1.0 * 1.0)
        _grp("alpha", "BELOW_TREND", "T1", 1.0, True, [_mem("AAA", "T1", 1.0, True), _mem("BBB", None, 0.0, False)]),
        # regime tailwind (no cascade tier) -> buyable member still funnels, factor 0.6
        _grp("beta", "BUY_PARTIAL", None, 0.0, False, [_mem("CCC", "T2", 0.8, True)]),
        # headwind subsector -> a buyable member is a WARNING, never a double-buy
        _grp("gamma", "TOPPING", None, 0.0, False, [_mem("DDD", "T1", 1.0, True)]),
    ]
    ff = sc.funnel(groups)
    db = {r["ticker"]: r for r in ff["double_buy"]}
    hw = {r["ticker"]: r for r in ff["headwind_warn"]}
    assert set(db) == {"AAA", "CCC"}
    assert set(hw) == {"DDD"}
    assert db["AAA"]["combined_score"] == 1.0                       # 1.0 stock * 1.0 subsector
    assert db["CCC"]["combined_score"] == pytest.approx(0.48)       # 0.8 stock * 0.6 regime factor
    # best-first ordering
    assert ff["double_buy"][0]["ticker"] == "AAA"
    # a non-buyable member never appears
    assert "BBB" not in db and "BBB" not in hw


def test_funnel_skips_non_buyable_members():
    g = _grp("x", "BUY", "T1", 1.0, True, [_mem("NB", None, 0.0, False)])
    ff = sc.funnel([g])
    assert ff["double_buy"] == [] and ff["headwind_warn"] == []


# ---------------------------------------------------------------- integration ----

def _has_ohlcv():
    from lib import config
    return (config.data_dir() / "baskets" / "ohlcv").exists()


@pytest.mark.skipif(not _has_ohlcv(), reason="OHLCV store not present")
def test_score_group_real_subsector_semiconductors():
    from engine import subsector_scan
    groups = subsector_scan._industry_map()
    key = next(k for k in groups if k[1] == "Semiconductors")
    g = sc.score_group(sc._slug(key[1]), key[1], key[0], groups[key], None, {})
    assert g is not None
    assert g["key"] == "semiconductors"
    assert g["entry"]["tier"] in (None, "T1", "T2", "T3", "T4")
    assert g["regime"]["state"] in {
        "BUY", "BUY_PARTIAL", "SETUP_BUY", "NEUTRAL", "EXTENDED",
        "TOPPING", "SELL", "BELOW_TREND", "OVERSOLD_BOUNCE"}
    assert g["n_priced"] >= 3
    assert len(g["members"]) >= 3
    # the chart series + markers are present for the detail page
    assert "_candle" in g and not g["_candle"]["close"].dropna().empty
    # every member carries its own gate verdict shape
    for m in g["members"]:
        assert "stock_tier" in m and "stock_buyable" in m


# ----------------------------------------------------- China 同花顺 (THS) desk ----

def _has_china():
    from lib import config
    return (config.data_dir() / "china_stocks").exists() and \
        (config.data_dir() / "baskets_china_ths" / "membership.json").exists()


@pytest.mark.skipif(not _has_china(), reason="China stores not present")
def test_china_benchmark_and_member_loader_resolve():
    from engine import basket_index
    # CSI 300 benchmark loads (from data/china, not the member stores)
    b = sc._bench_close("510300.SS")
    assert b is not None and len(b) > 260
    # an A-share .SZ/.SS ticker now resolves through the member loader (the china_stocks fallback)
    df = basket_index._load_member_ohlcv("000725.SZ")
    assert df is not None and "close" in df and "open" in df  # open synthesised from close


@pytest.mark.skipif(not _has_china(), reason="China stores not present")
def test_china_ths_score_group_is_bilingual_and_uses_csi300():
    import json
    from lib import config
    mem = json.loads((config.data_dir() / "baskets_china_ths" / "membership.json").read_text())
    bench = sc._bench_close(mem.get("benchmark") or "510300.SS")
    bid, spec = next(iter(mem["baskets"].items()))
    tickers = [m["ticker"] for m in spec["members"] if not m.get("removed")]
    g = sc.score_group(sc._slug(bid), spec["name"], spec.get("category"), tickers, bench, {},
                       kind="concept", label_zh=spec.get("name_zh"), sector_zh=spec.get("category_zh"),
                       member_names={m["ticker"]: m.get("name_zh") for m in spec["members"]})
    assert g is not None
    assert g["kind"] == "concept"
    assert g["label_zh"] == spec.get("name_zh")        # bilingual label flows through
    assert g["regime"]["state"] in {
        "BUY", "BUY_PARTIAL", "SETUP_BUY", "NEUTRAL", "EXTENDED",
        "TOPPING", "SELL", "BELOW_TREND", "OVERSOLD_BOUNCE"}
    assert g["regime"]["rs_60d"] is not None           # measured vs CSI 300, not SPY
    # at least one member carries a Chinese name (the funnel/detail bilingual join key)
    assert any(m.get("name_zh") for m in g["members"])


def test_china_board_js_paints_sleeve_and_semis_from_record():
    """China board reads stored sleeve and semis sentences from the record."""
    from pathlib import Path
    js = Path(__file__).resolve().parents[1].joinpath(
        "templates", "subsectors_china.js").read_text(encoding="utf-8")
    assert "sleeve_chip" in js
    assert "ai_semis_confirmer" in js
    assert "label_zh" in js
    assert "-0.1874" not in js
    assert "1.00" not in js
    card = js.split("function cardHTML", 1)[1].split("function cardDeck", 1)[0]
    render = js.split("function render()", 1)[1].split("function boot", 1)[0]
    assert "sleeve_chip" in render
    assert "g.ai_semis_confirmer" in card


def _china_board_js_parts():
    """The script, its two text helpers, and the chip function, in the file's own bytes."""
    from pathlib import Path

    js = Path(__file__).resolve().parents[1].joinpath(
        "templates", "subsectors_china.js"
    ).read_text(encoding="utf-8")
    helpers = "\n".join(
        line for line in js.splitlines()
        if line.startswith("  var L = function") or line.startswith("  function esc(")
    )
    chip = "function storedChip" + js.split("function storedChip", 1)[1].split("function render()", 1)[0]
    return js, helpers + "\n" + chip + "\n"


def _run_node(source):
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    done = subprocess.run([node, "-e", source], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


def test_china_board_stored_chip_prints_the_sentence_and_its_date():
    _js, prelude = _china_board_js_parts()
    out = _run_node(prelude + """
console.log(JSON.stringify({
  none: storedChip(null, '2026-10-30'),
  blank: storedChip({label_en: ''}, '2026-10-30'),
  full: storedChip({label_en: 'a<b', label_zh: '\u7532<\u4e59'}, '<d>'),
  undated: storedChip({label_en: 'a'}, ''),
}));
""")
    assert out["none"] == ""
    assert out["blank"] == ""
    assert out["full"] == (
        '<div><span class="l-en">a&lt;b</span><span class="l-zh">\u7532&lt;\u4e59</span>'
        ' <span class="l-en">as of &lt;d&gt;</span><span class="l-zh">\u622a\u81f3 &lt;d&gt;</span></div>'
    )
    assert out["undated"] == '<div><span class="l-en">a</span><span class="l-zh">a</span></div>'


def test_china_board_header_prints_each_check_with_its_own_date():
    js, prelude = _china_board_js_parts()
    render = js.split("function render()", 1)[1]
    block = "var host" + render.split("var host", 1)[1].split("app.innerHTML", 1)[0]
    out = _run_node(prelude + """
var hostEl = {innerHTML: 'X'};
var document = {getElementById: function () { return hostEl; }};
var DATA = {
  sleeve_chip: {label_en: 'S', label_zh: 'S2', radar_as_of: '2026-10-30', as_of: 'WRONG'},
  ai_semis_confirmer: {label_en: 'G', label_zh: 'G2', as_of: '2026-10-29', radar_as_of: 'WRONG'},
};
""" + block + "\nconsole.log(JSON.stringify(hostEl.innerHTML));\n")
    assert out.startswith("X")
    assert "WRONG" not in out
    assert out.index(">S<") < out.index("2026-10-30") < out.index(">G<") < out.index("2026-10-29")


def test_china_board_card_pill_prints_only_when_the_card_has_the_sentence():
    js, prelude = _china_board_js_parts()
    card = js.split("function cardHTML", 1)[1].split("function cardDeck", 1)[0]
    assert "+ semiPill" in card
    pill = "var semi =" + card.split("var semi =", 1)[1].split("    }\n", 1)[0] + "    }\n"
    out = _run_node(prelude + "function pillOf(g) {\n" + pill + """
return semiPill;
}
console.log(JSON.stringify({
  none: pillOf({}),
  blank: pillOf({ai_semis_confirmer: {}}),
  full: pillOf({ai_semis_confirmer: {label_en: 'a<b', label_zh: '\u7532<\u4e59'}}),
}));
""")
    assert out["none"] == ""
    assert out["blank"] == ""
    assert out["full"] == (
        '<span class="pill"><span class="l-en">a&lt;b</span>'
        '<span class="l-zh">\u7532&lt;\u4e59</span></span>'
    )
