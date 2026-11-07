"""Anticipation Engine invariants + POINT-IN-TIME guarantee.

The honesty guards are load-bearing: short-horizon direction must read as a coin-flip,
the cone must widen with horizon, display-only legs must never be marked scored without
a GO gate, and the feature engine must have NO look-ahead (truncate-and-recompute ==
full at past dates). Reads the repo data store; skips cleanly if absent.

Run: python3 -m tests.test_anticipation
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import anticipation, canon, forward_dist, velocity, vol_forecast  # noqa: E402

STOCKS = Path("data/stocks")
_NAMES = ["NVDA", "AAPL", "JPM", "XOM"]


def _load(name):
    f = STOCKS / f"{name}.parquet"
    if not f.exists():
        return None
    return pd.read_parquet(f)["close"].dropna()


def _bench():
    f = Path("data/yahoo/SPY.parquet")
    return pd.read_parquet(f)["close"] if f.exists() else None


def test_crps_basic():
    from engine import validation
    assert abs(validation.crps_ensemble([3.0], 5.0) - 2.0) < 1e-9          # point = |x-y|
    assert validation.crps_ensemble([4, 5, 6], 5) < validation.crps_ensemble([0, 5, 10], 5)
    print("ok test_crps_basic")


def test_har_vol_forecasts_forward_vol():
    """Vol IS forecastable — the cone-width anchor must beat noise (R² well > 0)."""
    c = _load("AAPL")
    if c is None:
        print("skip test_har_vol (no data)"); return
    har = vol_forecast.cone_vol_ann(c)
    fwd = vol_forecast.forward_vol_ann(c, 22)
    j = pd.concat([har.rename("h"), fwd.rename("f")], axis=1).dropna()
    r2 = float(j["h"].corr(j["f"]) ** 2)
    assert r2 > 0.1, f"HAR forward-vol R2 too low: {r2}"
    print(f"ok test_har_vol_forecasts_forward_vol (R2={r2:.3f})")


def test_cone_widens_with_horizon():
    c = _load("NVDA")
    if c is None:
        print("skip test_cone_widens (no data)"); return
    a = anticipation.anticipate(c, bench=_bench(), asset="NVDA", gate={})
    widths = []
    for k in ("short", "medium", "long"):
        rq = a["horizons"][k].get("ret_q")
        if rq:
            widths.append(rq["p95"] - rq["p5"])
    assert len(widths) >= 2 and all(np.diff(widths) >= -1e-6), f"cone not widening: {widths}"
    print(f"ok test_cone_widens_with_horizon (widths={[round(w,1) for w in widths]})")


def test_short_direction_is_coinflip():
    c = _load("NVDA")
    if c is None:
        print("skip test_short_coinflip (no data)"); return
    a = anticipation.anticipate(c, bench=_bench(), asset="NVDA", gate={})
    s = a["horizons"]["short"]
    assert s["conviction"] == "TOSS_UP", s["conviction"]
    assert 0.43 <= s["p_up"] <= 0.58, f"p_up outside reliable cap: {s['p_up']}"
    assert s["direction"] == "coin-flip"
    print("ok test_short_direction_is_coinflip")


def test_display_only_until_go():
    c = _load("AAPL")
    if c is None:
        print("skip test_display_only (no data)"); return
    a0 = anticipation.anticipate(c, bench=_bench(), asset="AAPL", gate={})
    assert all(d["display_only"] and not d["scored"] for d in a0["drivers"]), "empty gate must be all display-only"
    a1 = anticipation.anticipate(c, bench=_bench(), asset="AAPL",
                                 gate={"vol_pct": "GO", "neg_trend_vel": "GO"})
    scored = {d["axis"] for d in a1["drivers"] if d["scored"]}
    assert scored <= {"vol_pct", "neg_trend_vel"} and scored, f"gate not honored: {scored}"
    print("ok test_display_only_until_go")


def test_direction_is_display_only():
    c = _load("NVDA")
    if c is None:
        print("skip test_direction_display_only (no data)"); return
    a = anticipation.anticipate(c, bench=_bench(), asset="NVDA", gate={})
    assert a["guards"]["direction"] == "display-only"
    assert "display-only" in a["direction_trust"]
    print("ok test_direction_is_display_only")


def test_macro_overlay_scored_and_widens():
    """Validated macro legs appear as SCORED drivers + a stress/width block; high
    stress widens the cone (width_mult > 1)."""
    c = _load("AAPL")
    if c is None:
        print("skip test_macro_overlay (no data)"); return
    mf = anticipation.macro_legs_frame()
    if mf.empty:
        print("skip test_macro_overlay (no macro data)"); return
    a = anticipation.anticipate(c, bench=_bench(), asset="AAPL", macro_frame=mf,
                                gate={"m_hy_oas": "GO", "m_nfci": "GO"})
    assert "macro" in a and a["macro"]["width_mult"] >= 1.0
    scored_macro = [d for d in a["drivers"] if d["axis"].startswith("m_") and d["scored"]]
    assert scored_macro, "validated macro legs must surface as scored drivers"
    # GEX must never be a macro leg (no history to validate)
    assert not any(d["axis"] == "gex" for d in a["drivers"])
    print(f"ok test_macro_overlay_scored_and_widens (stress {a['macro']['stress_pct']}%, x{a['macro']['width_mult']})")


def test_builder_returns_empty_on_short_series():
    c = pd.Series(np.linspace(100, 110, 50),
                  index=pd.date_range("2024-01-01", periods=50, freq="B"))
    assert anticipation.anticipate(c) == {}
    print("ok test_builder_returns_empty_on_short_series")


def test_point_in_time_no_lookahead():
    """The feature/state engine must use only trailing data: features computed on the
    FULL series, truncated at T, must equal features computed on close[:T] — at dates
    well clear of the truncation edge. A forward window / full-sample fit fails here."""
    c = _load("AAPL")
    if c is None:
        print("skip test_pit (no data)"); return
    bench = _bench()
    T = c.index[-400]                                   # cut 400 bars before the end
    cmp_end = c.index[-520]                             # 120-bar clearance from the edge
    full_legs, full_conf = anticipation._legs(c, bench, None)
    tr_legs, tr_conf = anticipation._legs(c.loc[:T], bench, None)
    a = full_conf.loc[:cmp_end].dropna()
    b = tr_conf.loc[:cmp_end].dropna()
    idx = a.index.intersection(b.index)[-200:]
    diff = (a.loc[idx] - b.loc[idx]).abs()
    rel = diff / a.loc[idx].abs().clip(lower=1e-6)
    assert float(rel.max()) < 0.01, f"look-ahead leak in confluence state: max rel diff {float(rel.max()):.4f}"
    print(f"ok test_point_in_time_no_lookahead (max rel diff {float(rel.max()):.5f})")


def test_net_liquidity_mixed_unit_invariant():
    """Audit #28: net liquidity must be a CONSISTENT-UNITS 3-term billions series
    (WALCL/1000 - RRP - TGA/1000).  Redesigned 2026-07: the original invariant used the
    ON-RRP drain as the billions-scale reference ("WALCL-in-trillions < RRP-in-bn"),
    which ROTTED when ON-RRP drained to ~$0-6bn — a trillions WALCL (~6.7) is no longer
    smaller than the drain.  Scale is now judged ABSOLUTELY:

      1. WALCL_bn must be THOUSANDS-scale (median > 1,000) — a trillions-scaled WALCL is
         ~2-9, so this cannot rot however far the drain falls.  It must also remain the
         largest-magnitude component (>= RRP_bn, >= TGA_bn in median).
      2. netliq.diff must NOT be (near-)perfectly correlated with -RRP.diff.  NaN-safe:
         a fully-drained flat RRP has a degenerate diff and an undefined corr — that is
         a PASS (no proxy), not a failure.
      3. Guard-the-guard: the PRODUCTION detector (canon._assert_billions_scale, via
         canon.net_liquidity_bn) must REJECT the old /1e6 trillions construction —
         independent of where the drain happens to sit.
    """
    idx = pd.bdate_range("2000-01-01", "2027-01-01")
    comps = anticipation._net_liquidity_bn(idx)
    win = idx[idx >= idx[-1] - pd.Timedelta(days=365)]
    mw = float(comps["walcl_bn"].reindex(win).median())
    mr = float(comps["rrp_bn"].reindex(win).median())
    mt = float(comps["tga_bn"].reindex(win).median())
    if not (mw > 0):
        print("skip test_net_liquidity_mixed_unit_invariant (no WALCL data)")
        return

    # Invariant 1: WALCL in billions is ABSOLUTELY thousands-scale, and dominant.
    assert mw > 1000, f"WALCL_bn median {mw:.1f} — trillions-scale mixup (audit #28)?"
    assert mw >= mr, f"WALCL_bn ({mw:.0f}) < RRP_bn ({mr:.0f}) — mixed-unit scaling!"
    assert mw >= mt, f"WALCL_bn ({mw:.0f}) < TGA_bn ({mt:.0f}) — mixed-unit scaling!"

    # Invariant 2: netliq velocity is not a pure -RRP proxy (NaN corr ⇒ PASS).
    d_net = comps["netliq_bn"].reindex(win).diff()
    d_negrrp = (-comps["rrp_bn"].reindex(win).diff())
    corr = float(d_net.corr(d_negrrp))
    assert not (corr >= 0.99), \
        f"netliq.diff is a pure -RRP proxy (corr {corr:.3f}) — WALCL annihilated!"

    # Guard-the-guard: the old trillions WALCL must be REJECTED by the production
    # detector itself (drain-independent; try/except keeps the __main__ runner pytest-free).
    old_walcl_tn = comps["walcl_bn"] / 1000.0                 # bn/1000 == the old /1e6 trillions
    try:
        canon.net_liquidity_bn(old_walcl_tn, comps["rrp_bn"], comps["tga_bn"])
    except ValueError as e:
        assert "audit #28" in str(e), f"trillions WALCL rejected for the wrong reason: {e}"
    else:
        raise AssertionError("canon must reject a trillions-scale WALCL (audit #28 detector)")
    print(f"ok test_net_liquidity_mixed_unit_invariant "
          f"(WALCL={mw:.0f} RRP={mr:.0f} TGA={mt:.0f} bn; corr {corr:.2f})")



# --- W18-D-D1 (Spec ANT-W18D-1): page-render harness — appended, self-contained.
# The engine tests above read data/stocks; these render the Jinja page with
# synthetic fixtures only and exercise the header-date helpers with node.
import json  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

_W18D1_ROOT = Path(__file__).resolve().parent.parent


def _w18d1_render(payload):
    env = Environment(loader=FileSystemLoader(str(_W18D1_ROOT / "templates")), autoescape=True)
    return env.get_template("anticipation.html.j2").render(
        d=payload, data_json=json.dumps(payload, separators=(",", ":")),
        generated_utc="2026-10-19 07:05 UTC")


def _w18d1_horizon():
    return {"cell_n": 40, "conviction": 0.5, "dd_avg": -5.0, "dd_tail": -12.0,
            "dir_legs": [], "direction": "flip", "direction_scored": False,
            "mfe_med": 3.2, "oos_r2": 0.05, "p_up": 0.5, "r_hat": 0.0,
            "range_td": 21, "ret_q": {"p5": -8.0, "p50": 0.8, "p95": 9.0},
            "thin": False, "underpowered": False, "window_td": 21}


def _w18d1_asset(ticker, name, group, as_of):
    return {"anticipation_index": 50.0, "as_of": as_of, "asset": ticker,
            "asset_class": group, "caveats": [], "confluence_value": 0.4,
            "direction_model": "flip", "direction_trust": 0.5, "drivers": [],
            "group": group, "guards": [], "horizons": {"short": _w18d1_horizon()},
            "index_band": "mid", "macro": None, "n_go_legs": 0, "name": name,
            "trust": [], "vol_cone_ann": 0.12}


_W18D1_PAYLOAD = {
    "as_of": "2026-10-16", "generated_utc": "2026-10-19 07:05 UTC",
    "go_legs": [], "macro": None,
    "horizons_meta": {"short": [5, 21], "medium": [21, 63], "long": [63, 252]},
    "n_assets": 2,
    "assets": [_w18d1_asset("SPY", "S&P 500", "index", "2026-10-16"),
               _w18d1_asset("WMT", "Walmart", "stock", "2026-10-06")],
}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_w18d1_asof_helper_prefers_the_asset_date():
    """Header date follows the SELECTED asset; DATA.as_of is only the fallback."""
    html = _w18d1_render(_W18D1_PAYLOAD)
    i = html.find("function asofFor(")
    assert i >= 0, "asofFor helper missing from templates/anticipation.html.j2"
    helper = html[i:html.index("\n", i)]
    js = ("var DATA={as_of:'2026-10-16'};" + helper +
          "console.log('R1='+asofFor({as_of:'2026-10-06'}));"
          "console.log('R2='+asofFor({}));"
          "console.log('R3='+asofFor(null));"
          "DATA={};console.log('R4=['+asofFor({})+']');")
    proc = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"node failed rc={proc.returncode}: {proc.stderr}"
    out = proc.stdout
    assert "R1=2026-10-06" in out, f"asset date must win: {out}"
    assert "R2=2026-10-16" in out, f"missing asset date must fall back to DATA: {out}"
    assert "R3=2026-10-16" in out, f"null asset must fall back to DATA: {out}"
    assert "R4=[]" in out, f"empty DATA must print the empty string, not undefined: {out}"
    print("ok test_w18d1_asof_helper_prefers_the_asset_date")


def test_w18d1_set_asset_updates_the_header_date():
    """setAsset must rewrite #asof from the selected asset via asofFor(a)."""
    html = _w18d1_render(_W18D1_PAYLOAD)
    s = html.index("function setAsset(")
    e = html.index("\n  }\n", s) + len("\n  }")
    body = html[s:e]
    needle = "document.getElementById('asof').textContent = asofFor(a);"
    assert needle in body, "setAsset does not update the header date from the asset"
    print("ok test_w18d1_set_asset_updates_the_header_date")


# ---- W18-D lane D24 (Specs ANT-W18D-2/-4): horizon-card run-up + samples ----


_W18D24_ROOT = Path(__file__).resolve().parent.parent


def _w18d24_render(payload):
    env = Environment(loader=FileSystemLoader(str(_W18D24_ROOT / "templates")),
                      autoescape=True)
    return env.get_template("anticipation.html.j2").render(
        d=payload, data_json=json.dumps(payload, separators=(",", ":")),
        generated_utc="2026-10-19 07:05 UTC")


def _w18d24_horizon(**kw):
    h = {"cell_n": 1726, "conviction": 0.52, "dd_avg": -11.12, "dd_tail": -37.61,
         "dir_legs": ["credit"], "direction": "neutral", "direction_scored": False,
         "mfe_med": 15.75, "oos_r2": None, "p_up": 0.5, "r_hat": None,
         "range_td": [21, 63],
         "ret_q": {"p5": -28.0, "p25": -9.5, "p50": 4.1, "p75": 16.0, "p95": 33.0},
         "thin": False, "underpowered": False, "window_td": 63}
    h.update(kw)
    return h


def _w18d24_payload():
    asset = {"anticipation_index": 55.0, "as_of": "2026-10-16", "asset": "NVDA",
             "asset_class": "stock", "caveats": ["synthetic fixture caveat"],
             "confluence_value": 1.0, "direction_model": {},
             "direction_trust": "coin-flip", "drivers": [], "group": "stock",
             "guards": {},
             "horizons": {"short": _w18d24_horizon(range_td=[1, 10]),
                          "medium": _w18d24_horizon(),
                          "long": _w18d24_horizon(cell_n=455, mfe_med=23.6,
                                                  underpowered=True)},
             "index_band": "elevated", "macro": None, "n_go_legs": 7,
             "name": "NVIDIA Corp", "trust": [], "vol_cone_ann": 0.294}
    return {"as_of": "2026-10-16", "generated_utc": "2026-10-19 07:05 UTC",
            "go_legs": ["credit"], "macro": None,
            "horizons_meta": {"short": [1, 10], "medium": [21, 63],
                              "long": [126, 252]},
            "n_assets": 1, "assets": [asset]}


def _w18d24_slice_line(html, fname):
    start = html.index("\n  function " + fname + "(") + 1
    return html[start:html.index("\n", start)]


def _w18d24_slice_block(html, fname):
    start = html.index("\n  function " + fname)
    end = html.index("\n  }", start) + len("\n  }")
    return html[start:end]


def _w18d24_node(script):
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_w18d24_card_line_shows_run_up_and_samples():
    html = _w18d24_render(_w18d24_payload())
    js = "function T(en,zh){return en+'|'+(zh||en);}\n"
    js += _w18d24_slice_line(html, "f1") + "\n"
    js += _w18d24_slice_line(html, "pct") + "\n"
    js += _w18d24_slice_block(html, "rv2Line") + "\n"
    js += ("console.log(rv2Line({ret_q:{p50:4.1},mfe_med:15.75,cell_n:1726,"
           "thin:false}));\n")
    js += ("console.log(rv2Line({ret_q:{p50:4.1},mfe_med:15.75,cell_n:1726,"
           "thin:true}));\n")
    out = _w18d24_node(js).splitlines()
    fat, thin = out[0], out[1]
    for needle in ("median return", "+4.1%", "typical run-up", "常见上冲",
                   "+15.8%", "samples", "样本数", "1726"):
        assert needle in fat, fat
    assert "low-n" not in fat and "样本少" not in fat, fat
    assert "low-n" in thin and "样本少" in thin, thin


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_w18d24_missing_fields_print_dashes():
    html = _w18d24_render(_w18d24_payload())
    js = "function T(en){return en;}\n"
    js += _w18d24_slice_line(html, "f1") + "\n"
    js += _w18d24_slice_line(html, "pct") + "\n"
    js += _w18d24_slice_block(html, "rv2Line") + "\n"
    js += "console.log(rv2Line({}));\n"
    out = _w18d24_node(js)
    assert "median return —" in out, out
    for bad in ("undefined", "NaN", "null"):
        assert bad not in out, out
    assert "samples" not in out and "样本数" not in out, out


def test_w18d24_card_uses_the_helper():
    html = _w18d24_render(_w18d24_payload())
    card = _w18d24_slice_block(html, "setAsset")
    assert "rv2Line(h)" in card
    assert "T('typical dip','常见回撤')" in card
    assert "T('long n','长周期 n')" in card


# ---------------------------------------------------------------------------
# W18-D-3 (Spec ANT-W18D-3) — the selected-asset header prints the committed
# vol_cone_ann the cone is built from. The engine tests above read data/stocks;
# these render the page template from a SYNTHETIC fixture (no data/, no site/),
# then run the page's own JS under node. Copy stays bilingual via the page T().
# ---------------------------------------------------------------------------


_W18D3_ROOT = Path(__file__).resolve().parent.parent

_W18D3_AMD = {                                # values quoted from the committed seed
    "asset": "AMD", "name": "Advanced Micro Devices", "group": "stock",
    "asset_class": "equity", "as_of": "2026-10-17", "anticipation_index": 71.0,
    "index_band": "high", "confluence_value": 0.21, "direction_model": "har-ri",
    "direction_trust": 0.42, "drivers": [], "guards": [], "horizons": {},
    "macro": {"stress_pct": 62.0, "width_mult": 1.18, "go_legs": ["gold"]},
    "n_go_legs": 6, "trust": 0.51, "vol_cone_ann": 0.541,
}


def _w18d3_payload():
    """Top-key shape mirrors scripts/build_anticipation.py:96-103."""
    return {"as_of": "2026-10-17", "generated_utc": "2026-10-19 07:05 UTC",
            "go_legs": ["credit", "gold", "netliq", "oil_vrp", "term", "vrp"],
            "macro": _W18D3_AMD["macro"],
            "horizons_meta": {"short": [1, 10], "medium": [21, 63], "long": [126, 252]},
            "n_assets": 1, "assets": [_W18D3_AMD]}


def _w18d3_render(payload):
    env = Environment(loader=FileSystemLoader(str(_W18D3_ROOT / "templates")),
                      autoescape=True)
    return env.get_template("anticipation.html.j2").render(
        d=payload, data_json=json.dumps(payload, separators=(",", ":")),
        generated_utc="2026-10-19 07:05 UTC")


def _w18d3_slice(html, header):
    """Slice one page function: `header` through its own closing `\n  }` line."""
    i = html.find(header)
    assert i >= 0, f"page function not found in rendered HTML: {header!r}"
    j = html.find("\n  }", i)
    assert j >= 0, f"unterminated slice for {header!r}"
    return html[i:j + len("\n  }")]


def _w18d3_real_T(html):
    """The page's own bilingual T() (templates/anticipation.html.j2:166) verbatim."""
    for line in html.splitlines():
        if line.strip().startswith("function T(en,zh){"):
            return line.strip()
    raise AssertionError("page T() helper not found in rendered HTML")


def _w18d3_volchip_src(html):
    return _w18d3_real_T(html) + "\n" + _w18d3_slice(html, "  function volChip(a){")


def _w18d3_node(body):
    res = subprocess.run(["node", "-e", body], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    return res.stdout


_W18D3_JS_VALUES = ("\nprocess.stdout.write(JSON.stringify([volChip({vol_cone_ann:0.541}), "
                    "volChip({vol_cone_ann:0.104}), volChip({vol_cone_ann:0.294})]));")
_W18D3_JS_GUARDS = ("\nprocess.stdout.write(JSON.stringify([volChip({}), "
                    "volChip({vol_cone_ann:null}), volChip({vol_cone_ann:'x'}), "
                    "volChip(null)]));")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_w18d3_vol_chip_prints_yearly_volatility():
    """The cone width is set by vol_cone_ann: AMD 54% vs SPY 10% must be readable."""
    if shutil.which("node") is None:
        print("skip test_w18d3_vol_chip (no node)"); return
    html = _w18d3_render(_w18d3_payload())
    assert '"vol_cone_ann":0.541' in html, "committed vol_cone_ann never reaches the page"
    amd, spy, nvda = json.loads(_w18d3_node(_w18d3_volchip_src(html) + _W18D3_JS_VALUES))
    for chip in (amd, spy, nvda):
        assert "expected vol (yearly)" in chip, f"missing EN label: {chip}"
        assert "预期年化波动" in chip, f"missing ZH label: {chip}"
        assert 'class="chip"' in chip, f"must reuse the existing .chip class: {chip}"
        assert "NaN" not in chip and "undefined" not in chip
    assert "54%" in amd, f"AMD 0.541 must read 54%: {amd}"
    assert "10%" in spy, f"SPY 0.104 must read 10%: {spy}"
    assert "29%" in nvda, f"NVDA 0.294 must read 29%: {nvda}"
    print("ok test_w18d3_vol_chip_prints_yearly_volatility")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_w18d3_vol_chip_absent_without_a_number():
    """No number, no chip: a missing/null/non-numeric field must print nothing."""
    if shutil.which("node") is None:
        print("skip test_w18d3_vol_chip_guards (no node)"); return
    html = _w18d3_render(_w18d3_payload())
    vals = json.loads(_w18d3_node(_w18d3_volchip_src(html) + _W18D3_JS_GUARDS))
    assert vals == ["", "", "", ""], f"number guard leaked a chip: {vals}"


def test_w18d3_header_wires_the_vol_chip():
    """setAsset prints the chip once, between the stretch badge and stress chip."""
    sa = _w18d3_slice(_w18d3_render(_w18d3_payload()), "  function setAsset(tk){")
    assert "volChip(a)" in sa, "htitle never prints the cone-vol chip"
    assert sa.count("volChip(a)") == 1, "the chip must be printed exactly once"
    badge, chip, stress = (sa.find("idxbadge"), sa.find("volChip(a)"),
                           sa.find("T('market stress','市场压力')"))
    assert 0 <= badge < chip < stress, (
        f"chip belongs between badge and stress chip: {badge} {chip} {stress}")
    print("ok test_w18d3_header_wires_the_vol_chip")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} anticipation tests passed.")
