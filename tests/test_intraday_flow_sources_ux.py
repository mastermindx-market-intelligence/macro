"""R3 source-details contracts: presentation only, never a second freshness policy."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
PAGES=[ROOT/'templates/intraday_flow.html.j2',ROOT/'site/intraday_flow.html']
needs_node=pytest.mark.skipif(not shutil.which('node'),reason='Executed JavaScript contracts require Node')

def region(source,start,end):
    assert start in source, 'Missing R3 source-details function: '+start
    i=source.index(start)
    return source[i:source.index(end,i)]

def run_js(code):
    result=subprocess.run(['node','-e',code],capture_output=True,text=True,check=True)
    return json.loads(result.stdout)

@needs_node
@pytest.mark.parametrize('path',PAGES,ids=['template','site'])
@pytest.mark.parametrize('lane,status,stale,coverage,label,kind',[
    ('quotes','live',False,1,'Received · delayed','received'),
    ('quotes','connecting',False,0,'Checking…','checking'),
    ('quotes','unavailable',False,0.25,'Limited coverage','limited'),
    ('quotes','unavailable',False,0,'Unavailable','unavailable'),
    ('tape','live',True,1,'Marked stale','stale'),
    ('tape','unavailable',True,0.5,'Marked stale','stale'),
    ('tape','live','true',1,'Received · check time','received'),
    ('tape','unavailable',False,0.2,'Limited coverage','limited'),
    ('options','live',False,None,'Received · approximate','received'),
    ('options','unavailable',False,None,'Unavailable','unavailable'),
    ('options','connecting',False,None,'Checking…','checking'),
])
def test_independent_source_statuses_do_not_create_freshness(lane,status,stale,coverage,label,kind,path):
    helper=region(path.read_text(),'function sourceDetailStatus(', 'function renderSourceDetails(')
    out=run_js(helper+'\nconsole.log(JSON.stringify(sourceDetailStatus(...'+json.dumps([lane,status,stale,coverage])+')));')
    assert out['en']==label and out['kind']==kind
    assert out['zh'] and out['whyEn'] and out['whyZh']
    assert not any(word in out['en'].lower() for word in ('live','fresh','buy','sell'))
    assert 'Date.now' not in helper and 'setInterval' not in helper

@needs_node
@pytest.mark.parametrize('path',PAGES,ids=['template','site'])
def test_source_panel_keeps_independent_clocks_and_quiet_updates(path):
    src=path.read_text()
    js=region(src,'function displaySourceTime(', 'function updateSourceTimes(')
    setup=r'''
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function lz(en,zh){return '<span class="l-en">'+en+'</span><span class="l-zh">'+zh+'</span>';}
var writes=0,html='';
var host={get innerHTML(){return html;},set innerHTML(v){writes++;html=v;}};
var document={getElementById:id=>id==='ift-source-detail-rows'?host:null};
var quotesStatus='live',pulseStatus='live',flowStatus='unavailable',pulseSourceStale=true;
var quotesSourceAsof=null,pulseSourceAsof='2026-11-02T15:00:00Z',flowAsof='<img src=x onerror=alert(1)>';
function boardPriceCoverage(){return 1;}function boardPulseCoverage(){return 1;}
'''
    out=run_js(setup+js+'\nrenderSourceDetails();renderSourceDetails();console.log(JSON.stringify({html,writes}));')
    assert out['writes']==1
    assert out['html'].count('data-source-lane=')==3
    assert all(s in out['html'] for s in ('Received · delayed','Marked stale','Unavailable','2026-11-02 15:00 UTC','time unavailable'))
    assert '<img' not in out['html'] and 'onerror=' not in out['html']
    assert 'No directional inference' in out['html']

@pytest.mark.parametrize('path',PAGES,ids=['template','site'])
def test_static_native_disclosure_and_existing_refresh_contract(path):
    src=path.read_text()
    for value in ['id="ift-source-details-open"','id="ift-source-panel"','id="ift-source-detail-rows"','id="ift-source-refresh"','id="ift-source-close"','id="ift-source-back"','aria-labelledby="ift-source-title"','popover="auto"','role="dialog"']:
        assert value in src
    render=region(src,'function renderSourceDetails(', 'function updateSourceTimes(')
    assert 'ift-source-detail-rows' in render and 'ift-source-panel\'' not in render
    assert 'refreshButton.click()' in src
    assert 'renderSourceDetails();' in region(src,'function updateSourceTimes(', 'function updateFlowStamp(')
    assert 'setInterval(fetchQuotes, 60*1000)' in src
    assert 'setInterval(fetchPulse, 5*60*1000)' in src

@pytest.mark.parametrize('path',[ROOT/'templates/intraday-flow.css',ROOT/'site/intraday-flow.css'])
def test_disclosure_has_governed_style_and_mobile_targets(path):
    css=path.read_text()
    assert '.ift-source-panel' in css and '.ift-source-actions' in css
    assert re.search(r'\.ift-source-actions[^{}]*\{[^}]*min-height:\s*44px',css)
    assert 'max-height:' in css and 'overflow-y:auto' in css
    assert 'color:var(--ink-warn,var(--warn))' in css
    assert 'padding-bottom:env(safe-area-inset-bottom' not in css  # no unbounded mobile-only padding trick
