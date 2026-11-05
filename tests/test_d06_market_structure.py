"""D06: supplied data stays distinct from absent values in the display owner."""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

import pytest

from scripts.build_market_structure_page import _weekly_display, render

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/market_structure_latest.json"


@pytest.mark.parametrize(("updates", "bands"), [
    ({"band_2sigma_lo": None, "band_2sigma_hi": None}, [1]),
    ({"band_1sigma_lo": None, "band_1sigma_hi": None, "locked_close": None}, [2]),
    ({"band_1sigma_lo": 9000, "band_1sigma_hi": 1000}, [2]),
    ({"band_1sigma_lo": "7364", "band_2sigma_hi": False}, []),
    ({"band_1sigma_lo": 7500, "band_1sigma_hi": 7500}, [1, 2]),
])
def test_weekly_bands_are_independent_and_never_synthesized(tmp_path, updates, bands):
    payload = json.loads(FIXTURE.read_text())
    payload["week_map"].update(updates)
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(payload))
    html = render(ROOT, fixture=path)
    observed = [int(v) for v in re.findall(r'data-band="([12])"', html)]
    assert observed == bands
    for sigma in (1, 2):
        assert f'data-sigma="{sigma}" data-available="{str(sigma in bands).lower()}"' in html
    assert "0.975" not in html and "1.025" not in html
    assert "about 95% of weeks" not in html
    if updates.get("band_1sigma_lo") == updates.get("band_1sigma_hi") == 7500:
        assert '<line data-band="1"' in html


def test_weekly_display_rejects_nonfinite_and_keeps_a_true_zero():
    view = _weekly_display({"week_map": {
        "band_1sigma_lo": float("nan"), "band_1sigma_hi": float("inf"),
        "band_2sigma_lo": 0, "band_2sigma_hi": 0, "locked_close": 0, "gamma_flip": 0,
    }, "gamma": {"spot": 0}})
    assert not view["bands"][0]["available"]
    assert view["bands"][1]["available"]
    assert view["close"] == view["spot"] == view["flip"] == 0
    assert view["spot_x"] == view["flip_x"] == 300
    assert view["bands"][1]["x"] == 300
    assert all(math.isfinite(v) for v in [view["spot_x"], view["flip_x"]])


def _chart_js(body):
    source = (ROOT / "templates/market_structure.html.j2").read_text()
    helpers = source[source.index("function polyline("):source.index("// Describe only the observations")]
    prefix = """
      const UP='up',DN='down',MUT='muted',BLUE='blue',AMB='amber',LINE='line';
      class Node {
        constructor(tag){this.tag=tag;this.attrs={};this.children=[]}
        setAttribute(k,v){this.attrs[k]=String(v)}
        appendChild(n){this.children.push(n)}
        get firstChild(){return this.children[0]}
        removeChild(n){this.children.splice(this.children.indexOf(n),1)}
      }
      const nodes={};
      for(const id of ['#gex-chart','#spx-flip-chart','#sys-chart','#cor-chart'])nodes[id]=new Node('svg');
      function qs(id){return nodes[id]}
      global.document={createElementNS:(_,tag)=>new Node(tag)};
    """
    result = subprocess.run(["node", "-e", prefix + helpers + body], capture_output=True, text=True, check=True, timeout=10)
    return json.loads(result.stdout)


def test_chart_gaps_keep_original_slots_zero_and_healthy_sibling():
    got = _chart_js("""
      global.MSP_GAMMA_HIST=[
        {net_gex_bn:1,spot:100,flip:99,regime:'long'},
        {net_gex_bn:null,spot:null,flip:100},
        {net_gex_bn:0,spot:110,flip:101},
        {net_gex_bn:-2,spot:112,flip:102,regime:'short'}
      ];
      const availability=drawGex(126);
      console.log(JSON.stringify({gex:nodes['#gex-chart'].children,price:nodes['#spx-flip-chart'].children,availability}));
    """)
    bars = [n for n in got["gex"] if n["tag"] == "rect"]
    assert len(bars) == 3
    assert [n["attrs"]["data-value"] for n in bars] == ["1", "0", "-2"]
    assert float(bars[1]["attrs"]["x"]) - float(bars[0]["attrs"]["x"]) == 394
    price = got["price"]
    spot = [n for n in price if n["attrs"].get("data-series") == "spot"]
    assert [n["tag"] for n in spot] == ["circle", "path"]
    flip = [n for n in price if n["attrs"].get("data-series") == "flip"]
    assert len(flip) == 1 and flip[0]["tag"] == "path"
    assert "3/4" in got["availability"]["en"]
    assert "unavailable" in got["availability"]["en"]
    assert "缺口为数据暂缺" in got["availability"]["zh"]


def test_all_missing_chart_does_not_draw_a_zero_axis_or_zero_price():
    got = _chart_js("""
      global.MSP_GAMMA_HIST=[{net_gex_bn:null,spot:null,flip:null},{net_gex_bn:false,spot:'0',flip:Infinity}];
      const availability=drawGex(126);
      console.log(JSON.stringify({gex:nodes['#gex-chart'].children,price:nodes['#spx-flip-chart'].children,availability}));
    """)
    assert got["gex"] == got["price"] == []
    assert got["availability"]["en"] == "GEX unavailable · SPX unavailable · Flip level unavailable"


def test_single_observation_and_constant_domains_are_visible():
    got = _chart_js("""
      global.MSP_SYS_HIST=[{vc_alloc_bn:0,spx_close:100}];
      drawSys(252);
      console.log(JSON.stringify({nodes:nodes['#sys-chart'].children,domain:chartDomain([5,5,5]),missing:chartDomain([null,false,NaN])}));
    """)
    assert got["missing"] is None
    assert got["domain"] == [4.5, 5.5]
    assert len(got["nodes"]) == 2
    assert all(n["tag"] == "circle" and n["attrs"]["cx"] == "400" and n["attrs"]["cy"] == "80" for n in got["nodes"])


def test_correlation_area_does_not_bridge_gaps_or_recalculate_regime_threshold():
    got = _chart_js("""
      global.MSP_COR_HIST=[{cor1m:2},{cor1m:3},{cor1m:null},{cor1m:0},{cor1m:null},{cor1m:4},{cor1m:4}];
      drawCor(252);
      console.log(JSON.stringify(nodes['#cor-chart'].children));
    """)
    assert [n["tag"] for n in got] == ["path", "path", "circle", "path", "path"]
    assert not any("stroke-dasharray" in n["attrs"] for n in got)
    assert all("NaN" not in json.dumps(n) and "Infinity" not in json.dumps(n) for n in got)
    source = (ROOT / "templates/market_structure.html.j2").read_text()
    assert "dispThreshold" not in source and "COR_PCTILE_LO" not in source

@pytest.mark.parametrize("reading,available", [(None, False), (0, True)])
def test_missing_modeled_flow_is_not_an_observed_pause(tmp_path, reading, available):
    payload = json.loads(FIXTURE.read_text())
    system = payload["systematic"]
    system["flow_window_n"] = 5
    system["agreement"] = "paused"
    system["vc"].update(state="pausing", flow_5d_bn=reading, flow_window_n=5)
    system["cta"].update(state="pausing", flow_5d=reading, flow_window_n=5)
    path = tmp_path / "flow.json"
    path.write_text(json.dumps(payload))
    html = render(ROOT, fixture=path)
    section = html.split('<section class="msp-driver" data-driver="flows">', 1)[1].split("</section>", 1)[0]
    if available:
        assert "Pausing over 5 days" in section
        assert "holding steady over 5 days" in section
    else:
        assert "window change unavailable" in section
        assert "Pausing over" not in section
        assert "holding steady over" not in section


# W2.R continuation: source clocks, cached weeks and exact observation access.
from datetime import datetime, timezone


def _at(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.parametrize("instant,phase", [
    ("2026-10-31T12:00:00Z", "upcoming"),
    ("2026-11-02T04:59:59Z", "upcoming"),
    ("2026-11-02T05:00:00Z", "current"),
    ("2026-11-06T21:59:59Z", "current"),
    ("2026-11-06T22:00:00Z", "expired"),
    ("2026-11-09T12:00:00Z", "expired"),
])
def test_weekly_dates_use_new_york_sessions_and_expire_without_changing_bands(instant, phase):
    from scripts.build_market_structure_page import _weekly_display
    raw = {"week_map": {"week_start": "2026-11-02", "week_end": "2026-11-06",
        "locked_at": "2026-10-30T00:00:00", "locked_close": 100,
        "band_1sigma_lo": 95, "band_1sigma_hi": 105}}
    before = json.dumps(raw)
    view = _weekly_display(raw, now=_at(instant))
    assert view["phase"] == phase
    assert view["expires_at"] == "2026-11-06T17:00:00-05:00"
    assert view["bands"][0]["lo"] == 95 and view["bands"][0]["hi"] == 105
    assert not view["bands"][1]["available"]
    assert json.dumps(raw) == before


def test_weekly_holiday_end_uses_last_actual_session():
    from scripts.build_market_structure_page import _weekly_clock
    view = _weekly_clock({"week_start": "2026-03-30", "week_end": "2026-04-03",
        "locked_at": "2026-03-27"}, now=_at("2026-04-02T21:00:00Z"))
    assert view["phase"] == "expired"
    assert view["expires_at"] == "2026-04-02T17:00:00-04:00"


@pytest.mark.parametrize("changes", [
    {"locked_at": None}, {"locked_at": "not-a-date"}, {"locked_at": "2026-11-02"},
    {"week_start": "2026-02-30"}, {"week_end": "2026-11-01"},
    {"week_end": "2026-12-06"}, {"week_start": False}, {"week_end": []},
])
def test_unverifiable_week_never_claims_current(changes):
    from scripts.build_market_structure_page import _weekly_clock
    record = {"week_start": "2026-11-02", "week_end": "2026-11-06", "locked_at": "2026-10-30"}
    record.update(changes)
    view = _weekly_clock(record, now=_at("2026-11-05T12:00:00Z"))
    assert view["phase"] == "unknown"
    assert view["starts_at"] is None and view["expires_at"] is None


def test_gamma_observation_does_not_borrow_build_or_artifact_date():
    from scripts.build_market_structure_page import _snapshot_display
    raw = {"built_at": "2026-11-05T12:00:00Z", "asof": "2026-11-05",
           "gamma": {"spot": 100, "gamma_flip": 101, "coverage": {"last_obs": "2026-11-03"}}}
    view = _snapshot_display(raw, now=_at("2026-11-05T12:00:00Z"))
    assert view["observed"] == "2026-11-03"
    assert view["expected"] == "2026-11-04" and view["state"] == "stale"
    assert view["valid_until"] == "2026-11-05T17:00:00-05:00"
    raw["gamma"]["coverage"] = {}
    assert _snapshot_display(raw, now=_at("2026-11-05T12:00:00Z"))["observed"] is None


def test_snapshot_zero_missing_future_date_and_malformed_coverage_are_distinct():
    from scripts.build_market_structure_page import _snapshot_display
    raw = {"gamma": {"spot": 0, "gamma_flip": False, "asof": "2026-11-06",
        "coverage": {"missing_recent": ["2026-11-02", None, {}, "2026-02-30"],
                     "missing_in_regime": ["2026-11-02", "2026-11-03"]}}}
    view = _snapshot_display(raw, now=_at("2026-11-05T12:00:00Z"))
    assert view["spot"] == 0 and view["flip"] is None
    assert view["state"] == "future" and view["missing_count"] == 2
    raw["gamma"]["coverage"] = ["bad shape"]
    assert _snapshot_display(raw)["missing_count"] == 0


def test_spx_observation_and_switch_level_are_before_chart_and_outside_disclosure(tmp_path):
    raw = json.loads(FIXTURE.read_text())
    raw["gamma"]["coverage"] = {"last_obs": "2026-11-03", "complete": False}
    raw["gamma"].update(spot=7568.9199, gamma_flip=7654.546915, regime="short")
    fixture = tmp_path / "dated.json"
    fixture.write_text(json.dumps(raw))
    html = render(ROOT, fixture=fixture)
    start = html.index('id="msp-overview"')
    end = html.index("</section>", start)
    overview = html[start:end]
    assert start < html.index('id="gex-chart"') < html.index('id="msp-snapshot-details"')
    assert "<details" not in overview
    for expected in ("7568.9", "7654.5", "2026-11-03", "Hedging may amplify swings",
                     "对冲可能放大波动", "Incomplete source history", "来源历史不完整"):
        assert expected in overview
    assert "buy-the-dip" not in html and "逢低买入" not in html


def _observation_js(body):
    source = (ROOT / "templates/market_structure.html.j2").read_text()
    helpers = source[source.index("var observationColumns="):source.index("function bilingualNode(")]
    prefix = "function finiteNumber(v){return typeof v==='number'&&Number.isFinite(v)}\n"
    prefix += "function sliceTail(arr,n){return n>=9000?arr:arr.slice(-n)}\n"
    result = subprocess.run(["node", "-e", prefix+helpers+body], capture_output=True,
                            text=True, check=True, timeout=10)
    return json.loads(result.stdout)


def test_exact_csv_preserves_zero_and_missing_and_rejects_formula_strings():
    import csv
    import io
    got = _observation_js("""
      const rows=[
        {date:'2026-11-02',net_gex_bn:-44.185835,spot:0,flip:null},
        {date:'=HYPERLINK("bad")',net_gex_bn:false,spot:'7568.9',flip:Infinity},
        {date:'2026-02-30',net_gex_bn:0,spot:7568.9199,flip:7654.546915}
      ];
      const before=JSON.stringify(rows);
      console.log(JSON.stringify({csv:observationsCsv(rows,9999,observationColumns.gex),
        exact:exactObservationRows(rows,9999,observationColumns.gex),unchanged:JSON.stringify(rows)===before}));
    """)
    parsed = list(csv.reader(io.StringIO(got["csv"])))
    assert parsed[1] == ["2026-11-02", "-44.185835", "0", ""]
    assert parsed[2] == ["", "", "", ""]
    assert parsed[3] == ["", "0", "7568.9199", "7654.546915"]
    assert parsed[1:] == got["exact"] and got["unchanged"]


def test_exact_observations_follow_each_selected_window_and_source_units():
    got = _observation_js("""
      const rows=Array.from({length:30},(_,i)=>({date:'2026-11-02',cor1m:i===29?16.39:i}));
      console.log(JSON.stringify({short:exactObservationRows(rows,21,observationColumns.cor),
                                 all:exactObservationRows(rows,9999,observationColumns.cor)}));
    """)
    assert len(got["short"]) == 21 and len(got["all"]) == 30
    assert got["short"][0][1] == "9" and got["short"][-1][1] == "16.39"
