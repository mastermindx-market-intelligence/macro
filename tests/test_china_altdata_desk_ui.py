"""Render and interaction contracts for the progressively enhanced evidence desk."""
import json
from pathlib import Path
import re
import subprocess

from jinja2 import Environment, FileSystemLoader
from engine import i18n
from engine.china_altdata_desk import build_desk

ROOT=Path(__file__).parents[1]


def render(**overrides):
    raw=json.loads((ROOT/"tests/fixtures/china_altdata_desk.json").read_text())
    raw.update(overrides)
    desk=build_desk(**raw)
    env=Environment(loader=FileSystemLoader(str(ROOT/"templates")),autoescape=False)
    env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
    html=env.get_template("china_altdata.html.j2").render(desk=desk,zt=[],zt_breadth=[],narr=[],narr_asof=None,broker_gold=[],lab=None)
    return html,desk


def test_preview_is_bounded_and_full_universe_remains_in_sidecar_model():
    html,desk=render()
    body=html.split('<tbody id="ced-rows">')[1].split('</tbody>')[0]
    assert body.count("<tr>")==8 and len(desk["rows"])==19
    script=re.search(r'<script id="ced-preview" type="application/json">(.*?)</script>',html,re.S).group(1)
    assert len(json.loads(script)["rows"])==8
    assert '<noscript>' in html and 'china_lookup.html#600000.SS' in html
    assert 'china-altdata-desk.css' in html and 'china-altdata-desk.js' in html


def test_date_gap_and_validation_remain_visible_in_both_languages():
    html,_=render()
    section=html.split('id="participation"')[1].split('</section>')[0]
    for text in ("2026-10-22","2026-10-23","Calendar gap","日历间隔","not a trading-session","不等于交易日","point-in-time backtest","时点回测","1875"):
        assert text in section
    assert "cad-gauge" not in html and "g-score" not in html
    for old_claim in ("smart money","who controls the tape","independent smart-money","Institution-led"):
        assert old_claim not in html
    assert 'Context only' in html and '仅供研究参考' in html


def test_catalyst_source_health_and_field_keys_survive_redesign():
    html,_=render()
    events=html.split('id="catalysts"')[1].split('</section>')[0]
    for text in ("6 of 7 event sources","Risk warnings","风险警示","2026-10-13","unreadable sources","项来源无法读取","10.5× existing free float"):
        assert text in events
    _,desk=render(special={"inquiry":{"letters":[{"secCode":"920493","secName":"并行科技","date":"2026-10-15"}]}})
    assert desk["events"][0]["name"]=="并行科技"


def test_hostile_source_strings_cannot_become_markup_or_urls():
    evil='<img src=x onerror=alert(1)>'
    html,desk=render(rows=[{"ticker":"javascript:alert(1)","name":evil,"name_zh":evil,"convergence":.3,"value":.2,"margin":0,"flags":[]}])
    assert evil not in html and "&lt;img" in html
    assert 'href="javascript:' not in html.split('<main class="ced"')[1]
    assert desk["rows"][0]["href"] is None
    assert "\\u003cimg" in html  # safe JSON embedding closes no script


def test_empty_payload_keeps_explanations_and_useful_navigation():
    html,desk=render(rows=[],participation={},special={})
    assert "No eligible company rows" in html and "暂无合资格公司数据" in html
    assert "No event feed is available" in html
    assert 'href="#sources"' in html and 'href="china.html"' in html
    assert desk["data_health"]["state"]=="unavailable"


def test_legacy_malformed_staleness_never_leaks_internal_tokens():
    for gaps in (None,5,"broken",[None,3,"snapshot_staleness:published row 2026-09-29 is 17d behind tape tail 2026-10-16"]):
        html,desk=render(participation={"date":"2026-09-29","regime":"dormant","turnover_z20":-.5,"margin_chg_5d":0,"data_gaps":gaps})
        visible=html.split('<script id="ced-preview"')[0]
        assert "snapshot_staleness:" not in visible
        if isinstance(gaps,list):
            assert desk["data_health"]["lag_calendar_days"]==17
            assert "2026-10-16" in visible


def test_all_emitted_crowding_flags_have_bilingual_labels():
    from engine.china_crowding import FLAG_LABELS
    for key in ("margin_froth","pledge_tail","limitup_froth","attention_spike","rich_valuation","leverage_crowded"):
        assert key in FLAG_LABELS and all(FLAG_LABELS[key])
        assert FLAG_LABELS[key][0]!=key and FLAG_LABELS[key][1]!=key
    html,desk=render(rows=[dict(ticker="600000.SS",name="Example",convergence=.4,value=.3,margin=0,flags=["leverage_crowded"])],flag_labels=FLAG_LABELS)
    visible=html.split('<script id="ced-preview"')[0]
    assert "leverage_crowded" not in visible and "Leverage crowded" in visible


def test_filter_sort_and_schema_safety_in_actual_browser_module():
    code=r"""
const assert=require("node:assert/strict");
const desk=require("./templates/china-altdata-desk.js");
const rows=[
 {ticker:"600002.SS",name:"Beta",name_zh:"测试乙",available:7,side:"cautionary",alignment:-.4,conflicting:4,flags:[{}]},
 {ticker:"600001.SS",name:"Alpha",name_zh:"测试甲",available:3,side:"constructive",alignment:.4,conflicting:1,flags:[]},
 {ticker:"600000.SS",name:"Another",name_zh:"甲公司",available:2,side:"constructive",alignment:.4,conflicting:0,flags:[]}
];
assert.deepEqual(desk.selectRows(rows,{sort:"alignment"}).map(r=>r.ticker),["600000.SS","600001.SS","600002.SS"]);
assert.equal(desk.selectRows(rows,{query:"测试甲"})[0].ticker,"600001.SS");
assert.equal(desk.selectRows(rows,{query:"６００００２"})[0].ticker,"600002.SS");
assert.equal(desk.selectRows(rows,{side:"cautionary",coverage:5,flagged:true}).length,1);
assert.equal(desk.selectRows(rows,{query:"no such company"}).length,0);
assert.equal(desk.selectRows(rows,{coverage:7,side:"constructive"}).length,0);
assert.equal(desk.selectRows(rows,{sort:"conflict"})[0].ticker,"600002.SS");
assert.equal(rows[0].ticker,"600002.SS"); // sorting never mutates input
assert.equal(desk.selectEvents([{type:"unlock",horizon:"upcoming"},{type:"earnings",horizon:"undated"}],{type:"earnings",horizon:"upcoming"}).length,0);
assert.equal(desk.safeFilingHref("https://reportdocs.static.szse.cn/files/example.pdf"),true);
assert.equal(desk.safeFilingHref("https://szse.cn.evil.test/example.pdf"),false);
assert.equal(desk.safeFilingHref("javascript:alert(1)"),false);
assert.equal(desk.safeHref("javascript:alert(1)"),false);
assert.equal(desk.safeHref("//evil.test"),false);
assert.equal(desk.safeHref("china_lookup.html#600000.SS"),true);
assert.equal(desk.validPayload({schema:"wrong",rows:[]}),false);
console.log("FILTER_SORT_SCHEMA_PASS");
"""
    result=subprocess.run(["node","-e",code],cwd=ROOT,text=True,capture_output=True,check=True)
    assert "FILTER_SORT_SCHEMA_PASS" in result.stdout
