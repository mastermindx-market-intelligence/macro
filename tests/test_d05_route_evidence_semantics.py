"""D05 consumer semantics through the real board/detail renderers and page builders.

These are local deterministic fixtures, not market or publication proof.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]


def _node(program):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the actual vanilla-JS consumers")
    result = subprocess.run([node, "-e", program], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def _env():
    return Environment(loader=ChoiceLoader([
        DictLoader({"_site_nav.html.j2": ""}),
        FileSystemLoader(str(ROOT / "templates")),
    ]), autoescape=True)


def _group(**values):
    return {
        "key": "energy", "label": "Energy", "label_zh": "能源", "sector": "Energy",
        "class": "entry_now", "chart_key": "energy", "n_members": 10,
        "n_priced": 5, "n_live": 4, "coverage_pct": 0.75, "as_of": "2026-10-30",
        "reliability": "med", "entry": {"tier": "T1", "buyable": False},
        "regime": {"label": "Forming", "rs_60d": 2.4}, "members": [], **values,
    }


def _detail(group):
    html = _env().get_template("subsector_detail.html.j2").render(
        detail_json=json.dumps({"group": group, "kind": "subsector"}),
        group_name="Energy", chart_key=None, has_signals=False,
    )
    script = next(s for s in re.findall(r"<script>(.*?)</script>", html, re.S) if "const DETAIL" in s)
    return _node("""
const vm=require('node:vm');
const app={innerHTML:''};
const document={getElementById:()=>app,addEventListener:()=>{}};
vm.runInNewContext(""" + json.dumps(script) + """, {document,window:{}});
console.log(JSON.stringify(app.innerHTML));
""")


def _board(groups, coverage=None, tab="subsectors", sort_clicks=0):
    payload = {"ok": True, "as_of": "2026-10-30", "subsectors": groups, "baskets": groups,
               "entry_now": [g["key"] for g in groups], "forming": [], "headwind": [],
               "sectors": [], "double_gated": [],
               "coverage": coverage if coverage is not None else {"n_subsectors": 10, "n_gateable": len(groups)}}
    source = (ROOT / "templates/subsectors.js").read_text()
    return _node("""
const vm=require('node:vm');
function el(id){return {id,innerHTML:'',textContent:'',classList:{toggle(){}},
 addEventListener(k,f){this[k]=f},querySelectorAll(){return []},
 getAttribute(k){return k==='data-tab'?id:null}}}
const ids={};const tabs=['subsectors','baskets','nasdaq','russell'].map(el);
const document={readyState:'complete',documentElement:{getAttribute:()=> 'en'},
 getElementById:id=>ids[id]||(ids[id]=el(id)),
 querySelectorAll:selector=>selector==='.sc-tab'?tabs:[],querySelector:()=>null};
const payload=""" + json.dumps(payload) + """;
const fetch=async url=>({ok:true,json:async()=>url.includes('confluence')?payload:null});
vm.runInNewContext(""" + json.dumps(source) + """,{document,window:{},fetch,console});
setImmediate(()=>{
 tabs.find(t=>t.id===""" + json.dumps(tab) + """).click();
 for(let i=0;i<""" + str(sort_clicks) + """;i++){
  ids['sc-app'].click({target:{closest:selector=>selector==='th.sortable'?{getAttribute:()=> 'n'}:null}});
 }
 console.log(JSON.stringify(ids['sc-app'].innerHTML));
});
""")


@pytest.mark.parametrize("value,display", [(0, "0 / 10"), (None, "— / 10"), (3, "3 / 10"), (10, "10 / 10"), (-1, "— / 10"), ("10", "— / 10")])
def test_price_histories_are_not_roster_substitutes(value, display):
    group = _group(n_priced=value)
    detail, board = _detail(group), _board([group])
    assert display in detail and display in board
    assert "price histories / configured" in board
    assert "Price histories / configured members" in detail
    assert "75.0% · 4" in detail  # independent native positive-volume fraction/count
    if value is None or value == -1 or isinstance(value, str):
        assert "10 / 10" not in board


def test_absent_history_count_and_absent_volume_coverage_remain_unavailable():
    group = _group()
    for name in ("n_priced", "n_live", "coverage_pct"):
        group.pop(name)
    detail = _detail(group)
    assert "— / 10" in detail
    assert "— · —" in detail
    assert "75.0%" not in detail
    assert "— / 10" in _board([group])


@pytest.mark.parametrize("tab,total_field", [("subsectors", "n_subsectors"), ("baskets", "n_listed")])
def test_census_counts_scored_groups_not_entry_permission(tab, total_field):
    html = _board([_group()], {total_field: 10, "n_gateable": 1, "n_thin": 9}, tab)
    assert '1</span> of <span class="num">10' in html
    assert " scored" in html and "已评分" in html
    assert "have enough data to time" not in html
    missing = _board([_group()], {"n_gateable": 1, "n_baskets": 1}, tab)
    assert '1</span> of' not in missing
    assert "undefined" not in missing


def test_member_units_and_independent_stock_gate_in_table_and_cards():
    html = _detail(_group(members=[{
        "ticker": "XOM", "price": 100.0, "ret_20d": 4.2, "vs_basket": 1.7,
        "stock_tier": "T1", "stock_buyable": True, "stock_state": "Confirmed",
    }]))
    assert "Setup not yet confirmed" in html  # group buyable remains false
    assert '<tr class="buyable">' in html and 'member-card buyable' in html
    assert html.count("+4.2%") == 2 and html.count("+1.7 pp") == 2
    assert "20-session return (%)" in html and "Excess vs group (pp)" in html
    assert "individual observation dates are not supplied" in html
    assert "forward-filled member closes" in html
    assert "stock.html#XOM" in html


def _builder(monkeypatch, china=False):
    name = "scripts.build_subsector_rotation_pages"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/build_subsector_rotation_pages.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    if china:
        spec = importlib.util.spec_from_file_location("d05_china_builder", ROOT / "scripts/build_subsector_rotation_china_pages.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    # Only filesystem/nav fixture edges are replaced; the real builder, ordering,
    # source arguments, Jinja template and native listing links execute unchanged.
    monkeypatch.setattr(module.config, "ROOT", ROOT)
    monkeypatch.setattr(module, "Environment", lambda **kwargs: _env())
    monkeypatch.setattr(module, "write_page", lambda path, html: path.write_text(html))
    return module


def _sub(accel=0, member_count=31):
    return {
        "key": "energy", "name": "Energy", "name_zh": "能源", "theme": "Resources", "theme_zh": "资源",
        "quadrant": "leading", "n_members": 40, "rank": 1,
        "rs_ratio": 1.2, "rs_mom": 0.5, "accel": accel, "emerging_score": 2.1,
        "perf": {"1D": 0.1, "1W": 1, "1M": 2, "MTD": 0, "3M": 3, "6M": 4, "1Y": 5, "YTD": 6},
        "members": [{"t": "000001.SZ" if i == member_count - 1 else "STOCK" + str(i), "1M": i} for i in range(member_count)],
    }


@pytest.mark.parametrize("accel,en,zh", [(None, "unavailable", "不可用"), (-1, "negative", "为负"), (0, "zero", "为零"), (1, "positive", "为正")])
def test_acceleration_copy_keeps_zero_distinct(monkeypatch, accel, en, zh):
    builder = _builder(monkeypatch)
    lede_en, lede_zh = builder._lede(_sub(accel))
    assert "Acceleration is " + en in lede_en and "加速度" + zh in lede_zh
    if accel == 0:
        assert "negative" not in lede_en
        assert "rates are equal" in lede_en


@pytest.mark.parametrize("china", [False, True])
@pytest.mark.parametrize("asof", ["2026-10-30", None])
def test_real_builder_preserves_date_eight_horizons_cap_and_native_links(tmp_path, monkeypatch, china, asof):
    builder = _builder(monkeypatch, china)
    site = tmp_path / "site"
    (site / "marketdata").mkdir(parents=True)
    suffix = "_china" if china else ""
    (site / "marketdata" / ("subsector_rotation" + suffix + ".json")).write_text(
        json.dumps({"asof": asof, "generated_utc": "2099-01-01", "subsectors": [_sub()]}))
    assert builder.build(site) == 1
    html = (site / ("rotation" + suffix) / "energy.html").read_text()
    assert "2099-01-01" not in html
    assert (asof or "Date unavailable") in html
    assert [r[0] for r in builder.PERF_ROWS] == ["1D", "1W", "1M", "MTD", "3M", "6M", "1Y", "YTD"]
    assert html.count('class="sp"') == 8 and "MTD" in html and ">0.0%</b>" in html
    assert html.count('class="sd-chip"') == 30
    assert "30 / 31" in html and "40 " in html and "configured stocks" in html
    assert "display limit" in html and "does not establish historical membership" in html
    assert ("china_lookup.html#000001.SZ" if china else "stock.html#000001.SZ") in html
    assert ("sector_central_china.html#si-movement" if china else "subsector_rotation.html") in html
    assert "dimensionless" in html and "pp/week" in html
    assert "Member returns are point-in-time snapshots" not in html


@pytest.mark.parametrize("sort_clicks,expected", [(1, ["Positive", "Zero", "Missing"]), (2, ["Zero", "Positive", "Missing"])])
def test_history_sort_keeps_zero_numeric_and_missing_last(sort_clicks, expected):
    groups = [_group(key="missing", label="Missing", n_priced=None),
              _group(key="zero", label="Zero", n_priced=0),
              _group(key="positive", label="Positive", n_priced=3)]
    html = _board(groups, sort_clicks=sort_clicks)
    table = html.split('id="sc-fulltable"', 1)[1].split("</table>", 1)[0]
    positions = [table.index(">" + name + "</a>") for name in expected]
    assert positions == sorted(positions)


def test_missing_mtd_is_not_replaced_by_one_month_return(monkeypatch):
    builder = _builder(monkeypatch)
    sub = _sub()
    sub["perf"]["MTD"] = None
    env = _env()
    env.globals["fmt_pc"] = builder._fmt_pc
    html = env.get_template("subsector_rotation_detail.html.j2").render(
        sub=sub, members=[], n_total=1, perf_rows=builder.PERF_ROWS, q_cls="q-lead",
        q_en="Leading", q_zh="领先", qx_en="strong", qx_zh="强",
        lede_en="", lede_zh="", asof=None, members_available=0, member_limit=30,
    )
    mtd = next(cell for cell in html.split('class="sp"')[1:] if ">MTD</span>" in cell)
    assert ">—</b>" in mtd.split("</div>", 1)[0]
