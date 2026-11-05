"""D06 behavioral falsifiers for existing Stage readers and publication."""
from __future__ import annotations

import csv
import io
import json
import subprocess
from pathlib import Path

import pytest

from scripts.build_stage_analysis_page import _copy_stagedata, render

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/stage_analysis.html.j2"


def jsfn(name):
    source = TEMPLATE.read_text()
    start = source.index("  function " + name + "(")
    first = source[start:source.index("\n", start)]
    if first.rstrip().endswith("}"):
        return first
    end = source.index("\n  }", start) + len("\n  }")
    return source[start:end]


def node(source):
    result = subprocess.run(["node", "-e", source], text=True, capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


def test_failed_reader_deduplicates_and_requires_an_explicit_retry():
    got = node("\n".join(jsfn(n) for n in ("readOwnedSlice", "objectRecord", "objectRows", "rowEnvelope")) + r"""
(async()=>{
  let calls=0,queue=[],accepted=[],paints=[],states={};
  global.fetch=(url,options)=>{calls++;return new Promise(resolve=>queue.push({resolve,url,options}));};
  const repaint=()=>paints.push(states.main.phase);
  const accept=d=>accepted.push(d);
  const first=readOwnedSlice(states,'main','screener.json',rowEnvelope,accept,repaint,false);
  const dup=readOwnedSlice(states,'main','screener.json',rowEnvelope,accept,repaint,false);
  await Promise.resolve();
  const same=first===dup;
  queue.shift().resolve({ok:false});
  await first;
  readOwnedSlice(states,'main','screener.json',rowEnvelope,accept,repaint,false);
  const afterRevisit=calls;
  const retry=readOwnedSlice(states,'main','screener.json',rowEnvelope,accept,repaint,true);
  const retryDup=readOwnedSlice(states,'main','screener.json',rowEnvelope,accept,repaint,true);
  await Promise.resolve();
  const requested=queue.shift();
  requested.resolve({ok:true,json:async()=>({surface:'screener',rows:[]})});
  await retry;
  console.log(JSON.stringify({same,retrySame:retry===retryDup,afterRevisit,calls,phase:states.main.phase,accepted,paints,cache:requested.options.cache}));
})().catch(e=>{console.error(e);process.exit(1)});
""")
    assert got["same"] and got["retrySame"]
    assert got["afterRevisit"] == 1 and got["calls"] == 2
    assert got["phase"] == "ready"
    assert got["paints"] == ["loading", "error", "loading", "ready"]
    assert got["accepted"] == [{"surface": "screener", "rows": []}]
    assert got["cache"] == "no-store"


@pytest.mark.parametrize("payload", [None, [], {}, {"rows": {}}, {"rows": [None]}])
def test_reader_rejects_unusable_consumed_shape(payload):
    got = node("\n".join(jsfn(n) for n in ("readOwnedSlice", "objectRecord", "objectRows", "rowEnvelope")) + """
(async()=>{
 const states={};let accepted=false;
 global.fetch=async()=>({ok:true,json:async()=>(PAYLOAD)});
 await readOwnedSlice(states,'main','screener.json',rowEnvelope,()=>{accepted=true},()=>{});
 console.log(JSON.stringify({phase:states.main.phase,accepted}));
})().catch(e=>{console.error(e);process.exit(1)});
""".replace("PAYLOAD", json.dumps(payload)))
    assert got == {"phase": "error", "accepted": False}


def test_board_late_failure_does_not_replace_selected_success_or_reload_sibling():
    got = node("\n".join(jsfn(n) for n in ("readOwnedSlice", "objectRecord", "objectRows", "rowEnvelope", "loadBoard")) + r"""
(async()=>{
 var calls=[],pending={},paints=[];
 global.BOARD={weekly:null,daily:null};global.boardLoaded={};global.boardCadence='weekly';
 global.boardHead=()=>{};global.renderBoardProv=()=>{};
 global.renderBoard=()=>paints.push({selected:boardCadence,phase:(boardLoaded[boardCadence]||{}).phase});
 global.fetch=(url)=>{calls.push(url);return new Promise(resolve=>pending[url]=resolve);};
 loadBoard();await Promise.resolve();
 boardCadence='daily';
 pending['stagedata/stage_board_daily.json']({ok:true,json:async()=>({rows:[]})});
 await boardLoaded.daily.promise;
 const before=paints.length;
 pending['stagedata/stage_board_weekly.json']({ok:false});
 await boardLoaded.weekly.promise;
 const unchanged=paints.length===before;
 loadBoard('weekly',true);await Promise.resolve();
 pending['stagedata/stage_board_weekly.json']({ok:true,json:async()=>({rows:[{ticker:'ALFA'}]})});
 await boardLoaded.weekly.promise;
 console.log(JSON.stringify({unchanged,calls,paints,daily:BOARD.daily,weekly:BOARD.weekly}));
})().catch(e=>{console.error(e);process.exit(1)});
""")
    assert got["unchanged"]
    assert got["calls"] == [
        "stagedata/stage_board_weekly.json",
        "stagedata/stage_board_daily.json",
        "stagedata/stage_board_weekly.json",
    ]
    assert got["paints"][-1] == {"selected": "daily", "phase": "ready"}
    assert got["daily"]["rows"] == []
    assert got["weekly"]["rows"][0]["ticker"] == "ALFA"


@pytest.mark.parametrize(("counts", "status", "expected"), [
    ([None, None, None, None], "unspecified", "unknown"),
    ([0, 5, None, 2], "ok", "unknown"),
    ([0, 0, 0, 0], "ok", "empty"),
    ([0, 5, 0, 2], "ok", "ready"),
    ([1, 5, 1, 2], "no_target_week", "unknown"),
    ([False, 5, 1, 2], "ok", "unknown"),
    (["0", 5, 1, 2], "ok", "unknown"),
])
def test_arc_uses_typed_counts_and_never_normalizes_a_partial_population(counts, status, expected):
    prefix = """
const attrs={'data-counts':COUNTS,'data-population-status':STATUS};
const host={getAttribute:k=>attrs[k],setAttribute:(k,v)=>attrs[k]=v,innerHTML:''};
global.qs=()=>host;global.document={documentElement:{}};
global.getComputedStyle=()=>({getPropertyValue:()=> '#888888'});
global.isZH=()=>false;global.TT=(en,zh)=>en;global.esc=s=>s;
""".replace("COUNTS", json.dumps(json.dumps(counts))).replace("STATUS", json.dumps(status))
    got = node(prefix + jsfn("drawArc") + "\ndrawArc();console.log(JSON.stringify({attrs,html:host.innerHTML}));")
    assert got["attrs"]["data-population"] == expected
    assert "NaN" not in got["html"] and "undefined" not in got["html"]
    if expected == "unknown":
        assert "Classification population unavailable; no proportions are drawn." in got["html"]
        assert got["html"].count("<circle") == 4  # phase labels only
    if expected == "empty":
        assert "Known classified population is zero." in got["html"]
        assert got["html"].count("<circle") == 4
    if expected == "ready":
        assert "5 advancing" in got["html"]
        assert got["html"].count("<circle") > 4


def test_industry_divergence_preserves_unknown_and_a_real_zero():
    got = node("function TT(a,b){return a;}\n" + jsfn("divBar") + """
console.log(JSON.stringify([
 divBar({stage2_count:null,stage4_count:0}),
 divBar({stage2_count:0,stage4_count:0}),
 divBar({stage2_count:0,stage4_count:3})
]));
""")
    assert 'data-population="unknown"' in got[0]
    assert 'width:' not in got[0]
    assert 'data-population="empty"' in got[1] and 'width:' not in got[1]
    assert 'width:100%' in got[2] and 'width:0%' in got[2]


@pytest.mark.parametrize("zh", [False, True])
def test_csv_retains_full_view_units_dates_zero_null_and_escaping(zh):
    rows = [
        {"ticker": "A", "name": 'Comma, quote " and\n中文', "atr_ext": 0, "atr_pct_price": 0,
         "stage_current": True, "source": "live", "stage_week_end": "2026-10-30",
         "stage_source_asof": "2026-11-02"},
        {"ticker": "B", "atr_ext": None, "atr_pct_price": None, "stage_current": False,
         "source": "live", "stage_week_end": "2026-10-23"},
        {"ticker": "C", "source": "live", "stage_current": None},
    ] + [{"ticker": f"F{i}"} for i in range(600)]
    prefix = """
let captured=null,clicks=0;
global.isZH=()=>__LOCALE__;
global.LOADED={screener:{phase:'ready'}};
global.SCREENER_META={asof:'2026-11-03',built:'2026-11-04T00:12:00Z',
 target_stage_week:'2026-10-30',target_week_source:'population_modal',
 population:{status:'warn',data_session:'2026-11-02'}};
global.VIEW=ROWS;
global.URL={createObjectURL:b=>{captured=b;return 'blob:fixture'},revokeObjectURL:()=>{}};
global.document={createElement:()=>({click:()=>clicks++})};
global.setTimeout=()=>0;
""".replace("__LOCALE__", json.dumps(zh)).replace("ROWS", json.dumps(rows))
    got = node(prefix + jsfn("exportCSV") + """
(async()=>{
 exportCSV();const csv=await captured.text();
 LOADED.screener.phase='error';exportCSV();
 console.log(JSON.stringify({csv,clicks}));
})().catch(e=>{console.error(e);process.exit(1)});
""")
    parsed = list(csv.reader(io.StringIO(got["csv"])))
    assert got["clicks"] == 1
    assert len(parsed) == len(rows) + 1
    header = parsed[0]
    assert header[9] == ("拉伸（周ATR倍数）" if zh else "Extension (weekly ATR multiples)")
    assert header[10] == ("周ATR/价格（比例）" if zh else "Weekly ATR / price (fraction)")
    assert parsed[1][1] == rows[0]["name"]
    assert parsed[1][9:11] == ["0", "0"]
    assert parsed[2][9:11] == ["", ""]
    assert [r[16] for r in parsed[1:4]] == ["current", "stale", "unresolved"]
    assert parsed[2][17] == "2026-10-23" and parsed[2][18] == ""
    assert parsed[3][17:19] == ["", ""]
    assert parsed[1][19:] == [
        "2026-10-30", "population_modal", "warn", "2026-11-02", "2026-11-03", "2026-11-04T00:12:00Z"
    ]


@pytest.mark.parametrize("bad", ["{", "{}", "[]", "null", '""'])
def test_unusable_current_source_revokes_only_its_old_public_destination(tmp_path, bad):
    data = tmp_path / "data"
    site = tmp_path / "site"
    src = data / "stage_analysis"
    dst = site / "stagedata"
    src.mkdir(parents=True); dst.mkdir(parents=True)
    (src / "screener.json").write_text(bad)
    (dst / "screener.json").write_text('{"rows":[{"ticker":"OLD"}]}')
    healthy = '{"surface":"earnings_table","rows":[]}'
    (src / "earnings_table.json").write_text(healthy)
    copied, revoked, stale = _copy_stagedata(data, site)
    assert (copied, revoked, stale) == (1, 1, 0)
    assert not (dst / "screener.json").exists()
    assert (dst / "earnings_table.json").read_text() == healthy


def test_unreadable_source_revokes_and_republication_recovers(tmp_path, monkeypatch):
    data = tmp_path / "data"; site = tmp_path / "site"
    source = data / "stage_analysis/screener.json"
    target = site / "stagedata/screener.json"
    source.parent.mkdir(parents=True); target.parent.mkdir(parents=True)
    valid = '{"status":"stale","rows":[{"ticker":"KNOWN","stage_current":false}]}'
    source.write_text(valid); target.write_text("old")
    original = Path.read_text
    def unreadable(path, *args, **kwargs):
        if path == source:
            raise PermissionError("test read denial")
        return original(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", unreadable)
        assert _copy_stagedata(data, site) == (0, 1, 0)
    assert not target.exists()
    assert _copy_stagedata(data, site) == (1, 0, 1)
    assert target.read_text() == valid


def test_failure_to_revoke_stops_publication(tmp_path, monkeypatch):
    data = tmp_path / "data"; site = tmp_path / "site"
    target = site / "stagedata/screener.json"
    target.parent.mkdir(parents=True); target.write_text("old")
    original = Path.unlink
    def denied(path, *args, **kwargs):
        if path == target:
            raise PermissionError("test revoke denial")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", denied)
    with pytest.raises(RuntimeError, match="Cannot revoke unusable stagedata screener.json"):
        _copy_stagedata(data, site)
    assert target.read_text() == "old"

@pytest.mark.parametrize(("name", "payload"), [
    ("rowEnvelope", {"rows": [{"ticker": "AAA", "tags": "ai"}]}),
    ("rowEnvelope", {"rows": [{"ticker": 7}]}),
    ("rowEnvelope", {"rows": [{"new_tags": ["safe", None]}]}),
    ("seasonEnvelope", {"quarters": [{}]}),
    ("seasonEnvelope", {"quarters": [{"raisers": {"industry_allocation": [None]}, "decliners": {}}]}),
    ("researchEnvelope", {"items": [{"ticker_ui": 7}]}),
])
def test_consumed_nested_shapes_cannot_be_cached_ready(name, payload):
    code = "\n".join(jsfn(n) for n in ("objectRecord", "objectRows", name))
    assert node(code + "\nconsole.log(JSON.stringify(" + name + "(" + json.dumps(payload) + ")));") is False


def test_heatmap_missing_readings_remain_distinct_from_malformed_cells():
    code = "\n".join(jsfn(n) for n in ("objectRecord", "objectRows", "heatRegions"))
    code += """\nconsole.log(JSON.stringify([
      heatRegions({USA:{weeks:['2026-09-04'],rows:[{cells:[{combined:null,count:0}]}]}},'ec'),
      heatRegions({USA:{weeks:['2026-09-04'],rows:[{cells:[null]}]}},'ec'),
      heatRegions({USA:{weeks:['2026-09-04'],rows:[{cells:['bad']}]}},'ec'),
      heatRegions({USA:{weeks:['2026-09-04'],rows:[{ranks:[null]}]}},'rank'),
      heatRegions({USA:{weeks:[20260904],rows:[{ranks:[1]}]}},'rank')
    ]));"""
    assert node(code) == [True, True, False, True, False]


def test_renderer_failure_becomes_retryable_error_in_the_same_reader():
    code = jsfn("readOwnedSlice") + r"""
(async()=>{
 const states={};let fail=true,calls=0;
 global.fetch=async()=>{calls++;return {ok:true,json:async()=>({rows:[]})};};
 const paint=()=>{if(states.main.phase==='ready'&&fail)throw new Error('bad nested render');};
 await readOwnedSlice(states,'main','screener.json',()=>true,()=>{},paint);
 const first=states.main.phase;fail=false;
 await readOwnedSlice(states,'main','screener.json',()=>true,()=>{},paint,true);
 console.log(JSON.stringify({first,phase:states.main.phase,calls}));
})().catch(e=>{console.error(e);process.exit(1)});
"""
    assert node(code) == {"first": "error", "phase": "ready", "calls": 2}


@pytest.mark.parametrize(("status", "values", "message"), [
    ("no_target_week", [2, 3, 1, 2], "Stage read unavailable"),
    ("unavailable", [2, 3, 1, 2], "Stage read unavailable"),
    ("ok", [2, None, 1, 2], "Stage population unavailable"),
    ("ok", [2, True, 1, 2], "Stage population unavailable"),
    ("ok", [0, 0, 0, 0], "No classified names"),
])
def test_hero_withholds_stale_weather_without_usable_population(tmp_path, status, values, message):
    fixture = tmp_path / "context.json"
    fixture.write_text(json.dumps({
        "counts": dict(zip(("stage1", "stage2", "stage3", "stage4"), values)),
        "population": {"status": status, "current": None},
        "market": {"weather": "advancing"},
    }))
    html = render(ROOT, fixture=fixture)
    hero = html.split('<section class="hero ', 1)[1].split("</section>", 1)[0]
    assert message in hero
    assert "Most stocks are" not in hero
    assert 'class="stancepill' not in hero
