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
