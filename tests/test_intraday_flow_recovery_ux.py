"""R2 display-only recovery contracts; execute actual template/site JavaScript."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = pytest.mark.parametrize('relative', ['templates/intraday_flow.html.j2', 'site/intraday_flow.html'])

def region(text, start, end):
    assert start in text, f'missing recovery presentation helper: {start}'
    return text[text.index(start):text.index(end, text.index(start))]

def run_js(code):
    if not shutil.which('node'):
        pytest.skip('Node required for executed display contracts')
    result = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

@PAGES
def test_query_only_clear_preserves_theme_stage_sort_and_returns_focus(relative):
    src = (ROOT / relative).read_text()
    helper = region(src, 'function clearSearch()', 'function resetFilters()')
    actual = run_js('''
var activeBasket='semicap', activeStance='get_ready', searchQ='ZZZ999';
var groupByStance=false, sortCol='rvol', sortDir=-1, boardExpanded=true;
var renders=0, focused=false, input={value:'ZZZ999',focus:function(){focused=true;}};
var document={getElementById:function(id){return id==='ift-search'?input:null;}};
function applyView(){renders++;}
''' + helper + '''
clearSearch();console.log(JSON.stringify({activeBasket,activeStance,searchQ,groupByStance,
sortCol,sortDir,boardExpanded,renders,focused,value:input.value}));
''')
    assert actual == dict(activeBasket='semicap',activeStance='get_ready',searchQ='',
        groupByStance=False,sortCol='rvol',sortDir=-1,boardExpanded=False,renders=1,focused=True,value='')

@PAGES
@pytest.mark.parametrize('has_watchlist,query', [(True,'ZZZ999'),(True,''),(False,'ZZZ999')])
def test_empty_result_and_unavailable_watchlist_have_distinct_actions(relative, has_watchlist, query):
    src=(ROOT/relative).read_text()
    helper=region(src,'function emptyScanContent()', 'function clearSearch()')
    esc=region(src,'function esc(s)', 'function lz(')
    out=run_js('var leaders='+('[{}]' if has_watchlist else '[]')+';var searchQ='+json.dumps(query)+';'+
        'function lz(en,zh){return en+"|"+zh;}'+esc+helper+'console.log(JSON.stringify(emptyScanContent()));')
    assert 'data-ift-empty-kind="'+('filtered' if has_watchlist else 'unavailable')+'"' in out
    if has_watchlist:
        assert 'No matching names' in out and '暂无匹配标的' in out
        assert 'data-reset-filters' in out
        assert ('data-clear-search' in out) == bool(query)
        assert 'data-reload-board' not in out
    else:
        assert 'Watchlist unavailable' in out and '观察名单不可用' in out
        assert 'data-reload-board' in out
        assert 'data-reset-filters' not in out and 'data-clear-search' not in out

@PAGES
def test_search_copy_escapes_hostile_query(relative):
    src=(ROOT/relative).read_text()
    helper=region(src,'function emptyScanContent()', 'function clearSearch()')
    esc=region(src,'function esc(s)', 'function lz(')
    out=run_js('var leaders=[{}];var searchQ="<img src=x onerror=1>";function lz(en,zh){return en+"|"+zh;}'+
        esc+helper+'console.log(JSON.stringify(emptyScanContent()));')
    assert '<img src=x' not in out and '&lt;img src=x onerror=1&gt;' in out

@PAGES
@pytest.mark.parametrize('has_watchlist',[False, True])
def test_missing_watchlist_counts_are_unknown_not_observed_zero(relative, has_watchlist):
    src=(ROOT/relative).read_text()
    helper=region(src,'function updateStanceCounts(counts)', '// Selected-name evidence')
    out=run_js('var leaders='+('[{}]' if has_watchlist else '[]')+''';
var element={textContent:'old'},calls=[];
var document={querySelector:function(){return element;}};
function animateCount(el,n){calls.push(n);el.textContent=String(n);}
'''+helper+'''updateStanceCounts({act:0});console.log(JSON.stringify({text:element.textContent,calls}));''')
    assert out == ({'text':'0','calls':[0]} if has_watchlist else {'text':'—','calls':[]})

@PAGES
def test_recovery_actions_are_wired_and_missing_board_footer_is_explicit(relative):
    src=(ROOT/relative).read_text()
    assert "closest('[data-clear-search]')" in src and "closest('[data-reload-board]')" in src
    assert 'window.location.reload()' in src
    assert "if (!leaders.length)" in region(src,"var lbl = document.getElementById('count-label')",'var ths =')
    assert 'id="ift-empty-clear-search"' in src  # stable refresh-focus target
    assert 'id="ift-empty-reset"' in src

@pytest.mark.parametrize('relative',['templates/intraday-flow.css','site/intraday-flow.css'])
def test_recovery_action_touch_targets_and_long_query_wrapping(relative):
    css=(ROOT/relative).read_text()
    assert '.ift-empty-actions' in css
    assert 'overflow-wrap:anywhere' in css or 'overflow-wrap: anywhere' in css
    assert 'min-height:44px' in css or 'min-height: 44px' in css
