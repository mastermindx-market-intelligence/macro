"""Execute the real Sector Intelligence interval view, not a Python mirror."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'templates/sector_central.html.j2'
pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='Node required for shipped JS')
NOW = 1791905400000  # 2026-10-13 15:30 UTC; injected, never wall-clock dependent


def comparison(**changes):
    return dict(schema='basket_intraday_comparison.v1', status='observed', benchmark='SPY',
                method='matched_member_equal_weight', session_date='2026-10-13',
                reference_asof='2026-10-13T14:59:00+00:00', source_asof='2026-10-13T15:29:00+00:00',
                elapsed_minutes=30, max_clock_skew_seconds=60, matched_members=2,
                total_members=4, coverage_pct=50, relative_change_pct=0.990099,
                absolute_change_pct=2, benchmark_change_pct=1) | changes


def run_js(command: str, payload=None, *, lang='en'):
    text = PAGE.read_text()
    first = text.index('/* intraday-observation:start */')
    last = text.index('/* intraday-observation:end */', first)
    region = text[first:last]
    prelude = r'''
const vm = require('node:vm');
var host = {innerHTML:'',querySelectorAll:()=>[],contains:()=>false};
var more = {hidden:false,attrs:{},setAttribute(k,v){this.attrs[k]=v;}};
var timers=[];
var context = {console,Intl,Date,Number,JSON,Math,Object,
 document:{activeElement:null,getElementById:id=>id==='si-intraday-body'?host:more},
 clearTimeout:()=>{},setTimeout:(fn,ms)=>{timers.push(ms);return timers.length;},
 L:(en,zh)=>LANG==='zh'?zh:en,
 esc:s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 nameEn:id=>id,nameZh:id=>id,tryRender:()=>{},payload:PAYLOAD,now:NOW,
 host,more,timers};
context.Date.now=()=>NOW;
vm.createContext(context);
'''
    prelude = prelude.replace('LANG', json.dumps(lang)).replace('PAYLOAD',json.dumps(payload)).replace('NOW',str(NOW))
    script = prelude + 'vm.runInContext('+json.dumps(region)+',context);\n' + 'console.log(JSON.stringify(vm.runInContext('+json.dumps(command)+',context)));'
    completed = subprocess.run(['node','-e',script],text=True,capture_output=True,check=True,timeout=15)
    return json.loads(completed.stdout)


def pulse(raw=None, **changes):
    return {'schema':'basket_pulse.v1','market':'us','baskets':[{
        'id':'Example group','live_ew_chg_pct':0,'intraday_comparison':raw if raw is not None else comparison()}]} | changes


def test_real_shipped_reader_keeps_price_benchmark_and_coverage():
    got=run_js('readIntradayView(payload,now)',comparison())
    assert got['absolute']==2 and got['relative']==0.990099 and got['benchmark']==1
    assert got['n']==2 and got['total']==4 and got['seconds']==1800 and got['skew']==60


@pytest.mark.parametrize('change',[
    {'relative_change_pct':True},{'absolute_change_pct':float('nan')},
    {'matched_members':True},{'coverage_pct':25},{'elapsed_minutes':5},
    {'reference_asof':'2026-10-13T14:59:00'},{'max_clock_skew_seconds':61},
    {'relative_change_pct':5},{'status':'baseline_missing'},{'benchmark':'QQQ'},
    {'session_date':'2026-10-12'},{'observation_kind':'overnight'},
])
def test_unqualified_observations_do_not_become_numbers(change):
    assert run_js('readIntradayView(payload,now)',comparison(**change)) is None


def test_zero_daily_return_does_not_hide_intraday_change():
    html=run_js("renderIntradayComparisons(payload,'ready');host.innerHTML",pulse())
    assert '0.00%' in html and '+2.00%' in html and '+0.99%' in html
    assert '2/4' in html and '1800s' in html and '60s' in html
    assert '2026-10-13 14:59:00Z' in html


def test_stale_and_future_clock_remain_unavailable():
    raw=comparison()
    assert run_js('readIntradayView(payload,now+46*60000)',raw) is None
    assert run_js('readIntradayView(payload,now-2*60000)',raw) is None


def test_relative_winner_can_still_have_negative_price_change():
    html=run_js("renderIntradayComparisons(payload,'ready');host.innerHTML",pulse(comparison(
        absolute_change_pct=-2,benchmark_change_pct=-3,relative_change_pct=1.030928)))
    assert '\u22122.00%' in html and '+1.03%' in html


@pytest.mark.parametrize('state,word',[('loading','Loading'),('denied','Sign in'),('invalid','verified'),('unavailable','loaded')])
def test_explicit_failure_state_clears_old_numbers(state,word):
    html=run_js("host.innerHTML='old +9%';renderIntradayComparisons(payload,"+json.dumps(state)+");host.innerHTML",pulse())
    assert word in html and '+9%' not in html and 'si-intra-row' not in html


def test_dangerous_label_is_escaped_not_executable_html():
    p=pulse();p['baskets'][0]['id']='<img src=x onerror=alert(1)>'
    html=run_js("renderIntradayComparisons(payload,'ready');host.innerHTML",p)
    assert '<img' not in html and '&lt;img' in html


def test_language_and_unknown_state_have_plain_copy():
    html=run_js("renderIntradayComparisons(payload,'ready');host.innerHTML",pulse(comparison(status='benchmark_nonadvancing')),lang='zh')
    assert '\u7b49\u5f85' in html and 'benchmark_nonadvancing' not in html


def test_expiry_only_renders_and_does_not_poll_another_data_source():
    timers=run_js("renderIntradayComparisons(payload,'ready');timers",pulse())
    assert timers == [44*60000+1]
    source=PAGE.read_text();region=source.split('/* intraday-observation:start */')[1].split('/* intraday-observation:end */')[0]
    assert 'fetch(' not in region and 'setInterval(' not in region


def test_view_is_in_existing_moving_workspace_with_one_pulse_fetch():
    source=PAGE.read_text()
    assert source.index('data-view="moving">') < source.index('id="si-intraday"')
    assert source.count("fetchJson('live/basket_pulse.json'") == 1
    assert 'pulseInFlight' in source and 'aria-labelledby="si-intraday-title"' in source


def test_future_clock_disagreement_has_explicit_copy_without_accepting_it():
    raw=comparison(reference_asof='2026-10-13T15:00:00+00:00',source_asof='2026-10-13T15:30:01+00:00',elapsed_minutes=30+1/60)
    assert run_js('readIntradayView(payload,now)',raw) is None
    text=run_js('intradayPlainReason(payload,now)',raw)
    assert 'clock' in text.lower()


def test_malformed_observed_row_says_verification_not_missing_data():
    text=run_js('intradayPlainReason(payload,now)',comparison(coverage_pct=25))
    assert 'verified' in text.lower()


def test_unknown_failure_state_does_not_render_object_prototype():
    html=run_js("renderIntradayComparisons(payload,'constructor');host.innerHTML",pulse())
    assert 'function Object' not in html and 'verified' in html


def test_unbounded_day_number_does_not_overrun_the_cell():
    p=pulse();p['baskets'][0]['live_ew_chg_pct']=1e100
    html=run_js("renderIntradayComparisons(payload,'ready');host.innerHTML",p)
    assert 'e+100' not in html and '\u2014' in html


def test_relative_moves_heading_is_direction_neutral_and_focus_landing_exists():
    source=PAGE.read_text()
    assert 'Intraday relative moves' in source
    assert 'id="si-intraday-body" tabindex="-1"' in source
    assert 'id="si-intraday-more" type="button" aria-controls="si-intraday-body"' in source


@pytest.mark.parametrize('band_present',[True,False])
def test_shared_tape_renderer_clears_slim_overview_on_missing_pulse(band_present):
    source=PAGE.read_text();start=source.index('  function renderTapeBand(pulse){')
    region=source[start:source.index('/* intraday-observation:start */',start)]
    script='''const vm=require('node:vm');var calls=[];var band={classList:{remove:x=>calls.push('band-clear'),add:x=>calls.push('band-show')}};
var c={document:{getElementById:()=>BAND},renderSlimStrip:p=>calls.push(p?'strip-data':'strip-clear'),renderTapeStrip:p=>calls.push('full-data')};vm.createContext(c);
'''.replace('BAND','band' if band_present else 'null')
    script+='vm.runInContext('+json.dumps(region+'\nrenderTapeBand(null);')+',c);console.log(JSON.stringify(calls));'
    result=subprocess.run(['node','-e',script],text=True,capture_output=True,check=True,timeout=15)
    calls=json.loads(result.stdout)
    assert calls.count('strip-clear')==1 and 'strip-data' not in calls and 'full-data' not in calls
