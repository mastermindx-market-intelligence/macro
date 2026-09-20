"""Risk-envelope presentation stays in Risk Radar, without fusing engine readings."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from tests.test_macro_risk_dialog import _vm, _render, _dlg, _default_visible

ROOT = Path(__file__).resolve().parents[1]


def envelope():
    return {
        "schema": "mastermind.risk_envelope/v1", "bundle_id": "test-settled-bundle",
        "source_session": "2026-09-18", "definition_id": "test-definition",
        "data_state": "FRESH",
        "measured_state": {"usable": True, "verdict": "RISK_ON", "score": 61, "as_of": "2026-09-18"},
        "hazard_summary": {"stage": "FRAGILE", "stage_reason": "observed_settled_evidence"},
        "coherence": {"state": "CONTRADICTORY", "scope": "market_reads"},
        "policy_summary": {"policy_count": 0},
        "provenance": {"sources": [
            {"source_id": "market-state-latest", "role": "measured_state", "label_en": "Market trend", "label_zh": "市场趋势", "state": "RISK_ON", "score": 61, "as_of": "2026-09-18", "coverage": "FRESH", "required": True, "detail": {}},
            {"source_id": "leadership-crack-latest", "role": "hazard_evidence", "hazard_stage": "FRAGILE", "label_en": "Leadership", "label_zh": "领涨股", "state": "BROKEN", "score": None, "as_of": "2026-09-17", "coverage": "STALE", "required": True, "detail": {}},
        ]},
    }


def render(e=None, **kwargs):
    return _render(_vm(risk_envelope=envelope() if e is None else e), **kwargs)


def test_only_instance_is_inside_existing_radar():
    html = render()
    assert html.count('id="risk-envelope-band"') == 1
    assert 'id="risk-envelope-band"' in _dlg(html)
    assert html.index('id="dlg-risk"') < html.index('id="risk-envelope-band"')
    assert 'class="panel span12 gde-band"' not in html
    assert 'Three reads, kept separate' not in html


def test_compact_read_retains_disagreement_and_defers_receipts():
    e = envelope()
    before = deepcopy(e)
    html = render(e)
    visible = _default_visible(_dlg(html))
    assert 'Signals diverge' in visible and 'Risk-on' in visible and 'Fragile' in visible
    assert 'Capital controls:' not in visible and 'test-definition' not in visible
    assert '2026-09-17' in _dlg(html)  # source's own date survives in evidence
    assert e == before


@pytest.mark.parametrize('state,label', [('ALIGNED', 'Signals align'), ('MIXED', 'Incomplete picture'), (None, 'Incomplete picture'), ('NEW_ENUM', 'Incomplete picture')])
def test_alignment_is_never_invented(state, label):
    e = envelope(); e['coherence']['state'] = state
    assert label in _default_visible(_dlg(render(e)))


def test_missing_inputs_never_render_calm_or_risk_on():
    e = envelope(); e['hazard_summary']['stage'] = None
    e['measured_state'].update(usable=False, verdict=None, score=None)
    html = _dlg(render(e)); start = html.index('id="risk-envelope-band"')
    compact = html[start:html.index('</section>', start)]
    visible = _default_visible(compact)
    assert 'Unavailable' in visible and 'Incomplete read' in visible
    assert 'not an all-clear' in visible
    assert 'Risk-on' not in visible and 'No stress flagged' not in visible


def test_missing_radar_does_not_hide_available_envelope():
    vm = _vm(risk_envelope=envelope()); vm['market_state']['radar'] = {}
    assert 'id="risk-envelope-band"' in _dlg(_render(vm))


def test_absent_artifact_and_stocks_mode_have_no_context():
    assert 'id="risk-envelope-band"' not in render({})
    assert 'id="risk-envelope-band"' not in render(mode='stocks')


def test_live_identity_hooks_and_both_languages_survive():
    html = _dlg(render())
    for key in ('gde-live-chip', 'gde-pending-chip', 'gde-live-receipt'):
        assert html.count(f'id="{key}"') == 1
    assert 'data-bundle-id="test-settled-bundle"' in html
    assert 'data-settled-session="2026-09-18"' in html
    for label in ('市场内部', '信号分歧', '压力', '脆弱', '依据'):
        assert label in html


def test_nonzero_policy_count_is_not_reported_as_none():
    e=envelope(); e['policy_summary']['policy_count']=2
    html=_dlg(render(e))
    assert 'Capital controls: 2 active.' in html
    assert 'Capital controls: none active.' not in html


@pytest.mark.skipif(shutil.which('node') is None, reason='node required for shipped JS')
@pytest.mark.parametrize('scenario', ['legacy', 'current', 'no-dialog', 'absent'])
def test_legacy_relocation_executes_once_without_cloning(scenario):
    js=(ROOT/'templates/risk_envelope_live.js').read_text()
    fn=js[js.index('  function relocateLegacyEnvelope()'):js.index('  function unpaint()')]
    runner=r'''
    class El {
      constructor(name){this.name=name;this.children=[];this.parent=null;this.hidden=false;this.style={};this.removed=[];this.classList={remove:(...v)=>this.removed.push(...v)};}
      appendChild(el){if(el.parent)el.parent.children=el.parent.children.filter(x=>x!==el);el.parent=this;this.children.push(el);return el;}
      insertBefore(el,ref){this.appendChild(el);}
      querySelector(){return null;}
      closest(){let p=this;while(p){if(p.name==='dialog')return p;p=p.parent;}return null;}
    }
    const scenario=SCENARIO;
    const outer=new El('outer'),body=new El('dialog'),band=new El('band');
    (scenario==='current'?body:outer).appendChild(band);
    const document={getElementById:()=>scenario==='absent'?null:band,querySelector:()=>scenario==='no-dialog'?null:body,createElement:(n)=>new El(n)};
    FUNCTION
    relocateLegacyEnvelope();relocateLegacyEnvelope();
    console.log(JSON.stringify({outer:outer.children.length,body:body.children.length,parent:band.parent.name,hidden:band.hidden,display:band.style.display||null,summary:body.children[0]?.children[0]?.children[0]?.textContent||null,removed:band.removed}));
    '''.replace('SCENARIO',json.dumps(scenario)).replace('FUNCTION',fn)
    result=json.loads(subprocess.check_output(['node','-e',runner],text=True))
    if scenario=='legacy':
        assert result['outer']==0 and result['body']==1 and result['parent']=='details'
        assert result['summary']=='Market internals · trend and stress'
        assert result['removed']==['panel','span12']
    elif scenario=='current':
        assert result['body']==1 and result['parent']=='dialog' and result['removed']==[]
    elif scenario=='no-dialog':
        assert result['hidden'] and result['display']=='none'
    else:
        assert result['outer']==1 and result['body']==0
