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
    fn=js[js.index('  function relocateLegacyEnvelope()'):js.index('  function unpaint(')]
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


# Second slice: the SAME producer's facts reach a useful reason and a live read.
def source_envelope():
    e = envelope()
    e['hazard_summary']['contributing_sources'] = ['leadership-crack-latest', 'risk-radar-us']
    e['provenance']['sources'][0]['detail']['any_input_stale'] = True
    e['provenance']['sources'][1].update(coverage='FRESH', detail={'cohort_role': 'tracked_ai_hardware_damage_monitor'})
    e['provenance']['sources'].append(dict(source_id='risk-radar-us', role='hazard_evidence',
        state='caution', hazard_stage='FRAGILE', coverage='FRESH', required=False,
        label_en='Cross-asset scares', label_zh='跨资产风险', score=56, as_of='2026-09-18',
        detail={'label_en':'Credit stress', 'label_zh':'信用压力'}))
    return e


def _context_copy():
    import re
    html = render(source_envelope())
    return json.loads(re.search(r'id="gde-context-copy">(.*?)</script>', html, re.S)[1])['copy']


def _live_fixture():
    e=source_envelope()
    e.update(source_session='2026-09-19', revision='live_provisional', precedence='live',
        live_active=True, built='2026-09-19 15:00:00 UTC', stale_after_min=5,
        overlays={'settled_bundle_id':'test-settled-bundle'},
        live_transition={'candidate_stage':'FRAGILE', 'stable_stage':'FRAGILE', 'pending':None})
    return e


def _js_value(statement, feed=None):
    if not shutil.which('node'):
        pytest.skip('Node required for actual shipped consumer')
    src=(ROOT/'templates/risk_envelope_live.js').read_text()
    src=src[:src.index('  if (document.readyState !== "loading") tick();')]
    script='var window = {};\n'+src+'\nvar COPY='+json.dumps(_context_copy())+';\nvar FEED='+json.dumps(feed or _live_fixture())+';\n'
    script+='Date.now=()=>Date.parse("2026-09-19T15:01:00Z");\n'
    script+=statement+'\n})();'
    run=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stderr
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_source_causes_and_older_input_caveat_are_visible():
    visible=_default_visible(_dlg(render(source_envelope())))
    assert 'AI-hardware leaders: damaged' in visible and 'Credit stress: building' in visible
    assert 'AI硬件龙头：受损' in visible and '信用压力：积聚中' in visible
    assert 'Trend includes older inputs.' in visible
    assert 'The trend is positive, but underlying stress remains.' not in visible


def test_existing_risk_button_carries_separate_internals_hint():
    import re
    html=render(source_envelope())
    button=re.search(r'<button[^>]*id="mx5BtnRisk".*?</button>',html,re.S)[0]
    assert 'Risk Detail' in button and 'Fragile internals' in button
    assert 'mx5OpenDlg(\'dlg-risk\')' in button and html.count('id="gde-button-context"')==1


def test_unknown_policy_count_is_not_zero():
    e=source_envelope();e['policy_summary']={}
    html=_dlg(render(e))
    assert 'Capital controls: unavailable.' in html
    assert 'Capital controls: none active.' not in html


def test_live_reason_matches_the_same_ssr_lexicon_without_mutation():
    result=_js_value('var before=JSON.stringify(FEED); var view=contextView(FEED,COPY); console.log(JSON.stringify({view,unchanged:before===JSON.stringify(FEED)}));')
    assert result['unchanged']
    assert result['view']['causes']==['AI-hardware leaders: damaged · Credit stress: building', 'AI硬件龙头：受损 · 信用压力：积聚中']
    assert result['view']['stage']=='FRAGILE' and not result['view']['pending']


@pytest.mark.parametrize('coverage',['STALE','MISSING','UNKNOWN'])
def test_live_causes_do_not_promote_unreadable_sources(coverage):
    e=_live_fixture();e['provenance']['sources'][1]['coverage']=coverage
    result=_js_value('console.log(JSON.stringify(contextView(FEED,COPY)));',e)
    assert 'AI-hardware leaders' not in result['causes'][0]
    assert 'Credit stress: building' in result['causes'][0]


def test_pending_change_is_a_candidate_not_a_confirmed_upgrade():
    e=_live_fixture();e['hazard_summary']['stage']='TRANSMITTING'
    e['live_transition'].update(candidate_stage='TRANSMITTING',pending={'stage':'TRANSMITTING','ticks':1,'needs':2})
    result=_js_value('console.log(JSON.stringify(contextView(FEED,COPY)));',e)
    assert result['stage']=='TRANSMITTING' and result['pending']
    assert result['hint']==['Checking stress','压力待确认']


@pytest.mark.parametrize('mutation',['missing_candidate','missing_stable','mismatched_stable','invalid_pending','unknown_stage'])
def test_malformed_live_transition_is_not_a_healthy_read(mutation):
    e=_live_fixture()
    if mutation=='missing_candidate': e['live_transition'].pop('candidate_stage')
    elif mutation=='missing_stable': e['live_transition'].pop('stable_stage')
    elif mutation=='mismatched_stable': e['live_transition']['stable_stage']='NONE'
    elif mutation=='invalid_pending': e['live_transition']['pending']={'stage':'BREAKDOWN','ticks':0,'needs':2}
    else: e['hazard_summary']['stage']='NEW_ENUM'
    result=_js_value('console.log(JSON.stringify(contextView(FEED,COPY)));',e)
    assert result['stage'] is None and result['label']==['Incomplete read','数据不全']


@pytest.mark.parametrize('mutation',['valid','future','expired','invalid_horizon','missing_session','old_session','wrong_bundle','closed'])
def test_live_acceptance_uses_real_identity_and_freshness(mutation):
    e=_live_fixture()
    if mutation=='future': e['built']='2026-09-19 15:02:00 UTC'
    elif mutation=='expired': e['built']='2026-09-19 14:00:00 UTC'
    elif mutation=='invalid_horizon': e['stale_after_min']=-1
    elif mutation=='missing_session': e.pop('source_session')
    elif mutation=='old_session': e['source_session']='2026-09-17'
    elif mutation=='wrong_bundle': e['overlays']['settled_bundle_id']='unrelated'
    elif mutation=='closed': e['live_active']=False
    result=_js_value('var band={getAttribute:k=>k==="data-bundle-id"?"test-settled-bundle":"2026-09-18"}; console.log(JSON.stringify(active(FEED,band)));',e)
    assert result is (mutation=='valid')


_LIVE_DOM = r"""
var nodes={};
function element(id){
 var children={'.l-en':{textContent:''},'.l-zh':{textContent:''},'.gde-live-time':{textContent:''}};
 return nodes[id]={hidden:true,textContent:'',attrs:{},querySelector:k=>children[k]||null,
  getAttribute:function(k){return this.attrs[k]||'';},setAttribute:function(k,v){this.attrs[k]=v;},closest:()=>true};
}
['risk-envelope-band','gde-context-copy','gde-live-chip','gde-pending-chip','gde-live-receipt',
 'gde-live-reading','gde-live-stage','gde-live-cause','gde-live-fallback','gde-button-context'].forEach(element);
var document={getElementById:k=>nodes[k]||null};
nodes['gde-context-copy'].textContent=JSON.stringify({copy:COPY,settled_stage:'FRAGILE'});
nodes['risk-envelope-band'].attrs={'data-bundle-id':'test-settled-bundle','data-settled-session':'2026-09-18'};
function result(){return {live:nodes['gde-live-reading'].hidden,clock:nodes['gde-live-chip'].hidden,
 receipt:nodes['gde-live-receipt'].hidden,fallback:nodes['gde-live-fallback'].hidden,
 hint:nodes['gde-button-context'].querySelector('.l-en').textContent,
 stage:nodes['gde-live-stage'].querySelector('.l-en').textContent,
 cause:nodes['gde-live-cause'].querySelector('.l-en').textContent};}
"""


def test_live_feed_reaches_existing_button_and_visible_reason():
    out=_js_value(_LIVE_DOM+'applyFeed(FEED);console.log(JSON.stringify(result()));')
    assert not out['live'] and not out['clock'] and not out['receipt']
    assert out['hint']=='Live: Fragile internals'
    assert out['stage']=='Live stress: Fragile' and 'Credit stress: building' in out['cause']


def test_network_failure_clears_live_and_restores_settled_hint():
    out=_js_value(_LIVE_DOM+"applyFeed(FEED);global.fetch=()=>Promise.reject(Error('network fixture'));tick();setImmediate(()=>console.log(JSON.stringify(result())));")
    assert out['live'] and out['clock'] and out['receipt']
    assert not out['fallback'] and out['hint']=='Fragile internals'


def test_expiry_clears_live_even_while_fetch_hangs():
    out=_js_value(_LIVE_DOM+"applyFeed(FEED);Date.now=()=>Date.parse('2026-09-19T15:10:00Z');global.fetch=()=>new Promise(()=>{});tick();console.log(JSON.stringify(result()));")
    assert out['live'] and out['clock'] and not out['fallback']
    assert out['hint']=='Fragile internals'


def test_same_poller_never_launches_overlapping_requests():
    out=_js_value(_LIVE_DOM+"var count=0;global.fetch=()=>{count++;return new Promise(()=>{});};tick();tick();console.log(JSON.stringify({count}));")
    assert out['count']==1


def test_recovery_removes_fallback_and_closed_market_is_not_an_outage():
    out=_js_value(_LIVE_DOM+"applyFeed(FEED);applyFeed(null);var failed=result();applyFeed(FEED);var recovered=result();applyFeed({...FEED,live_active:false});console.log(JSON.stringify({failed,recovered,closed:result()}));")
    assert not out['failed']['fallback']
    assert out['recovered']['fallback'] and not out['recovered']['live']
    assert out['closed']['fallback'] and out['closed']['live']
    assert out['closed']['hint']=='Fragile internals'


def test_live_evidence_preserves_independent_source_dates():
    e=_live_fixture();e['provenance']['sources'][1].update(as_of='2026-09-17',coverage='STALE')
    out=_js_value('console.log(JSON.stringify(contextView(FEED,COPY)));',e)
    assert '2026-09-17 · older read' in out['sourceLines'][0]
    assert '2026-09-17 · 较早读数' in out['sourceLines'][1]
    assert '15:00' not in out['sourceLines'][0]


def test_embedded_copy_does_not_publish_a_second_envelope_payload():
    import re
    e=source_envelope();e['private_policy_receipt']='not-for-html-fixture'
    html=render(e)
    config=json.loads(re.search(r'id="gde-context-copy">(.*?)</script>',html,re.S)[1])
    assert set(config)=={'copy','settled_stage'}
    assert 'not-for-html-fixture' not in html
    assert 'innerHTML' not in (ROOT/'templates/risk_envelope_live.js').read_text()


def test_pending_deescalation_never_announces_an_all_clear():
    e=_live_fixture();e['hazard_summary']['stage']='NONE'
    e['live_transition'].update(candidate_stage='NONE',pending={'stage':'NONE','ticks':1,'needs':2})
    out=_js_value(_LIVE_DOM+'applyFeed(FEED);console.log(JSON.stringify(result()));',e)
    assert out['hint']=='Live: Checking stress'
    assert out['stage']=='Live candidate: No stress flagged'
    assert out['hint']!='Live: No stress flagged'


def test_fetch_deadline_releases_single_flight_for_the_next_existing_tick():
    script=_LIVE_DOM+"var deadline=0,count=0;global.AbortSignal={timeout:ms=>{deadline=ms;return {aborted:true};}};global.fetch=(url,options)=>{count++;return options.signal.aborted?Promise.reject(Error('timeout fixture')):new Promise(()=>{});};applyFeed(FEED);tick();setImmediate(()=>{tick();setImmediate(()=>console.log(JSON.stringify({deadline,count,state:result()})));});"
    out=_js_value(script)
    assert out['deadline']==10000 and out['count']==2
    assert out['state']['live'] and not out['state']['fallback']



def probability_evidence(*, n=746, observed=0.12198391420911528, thin=False, matched=True):
    return {
        "schema": "risk_radar_probability_evidence.v1",
        "evidence_class": "reconstructed_historical",
        "precision_grade": False,
        "horizons": {
            "h21": {
                "matched": matched,
                "displayed_probability": 0.16 if not thin else 0.25,
                "n": n,
                "events": 91 if not thin else 11,
                "observed_rate": observed,
                "observed_rate_ci90": [0.074072, 0.174791] if not thin else [0.0, 0.615385],
                "thin": thin,
                "from": "2020-01-02",
                "through": "2026-08-19",
                "population_sha256": "fixture",
            }
        },
    }


def test_probability_evidence_is_compact_metadata_inside_existing_radar_context():
    vm = _vm(risk_envelope=envelope())
    vm["market_state"]["radar"]["dd_evidence"] = probability_evidence()
    html = _dlg(_render(vm))
    band = html[html.index('id="risk-envelope-band"'):html.index("</section>", html.index('id="risk-envelope-band"'))]
    visible = _default_visible(band)
    assert html.count('class="gde-prob-evidence"') == 1
    assert "Odds evidence" in visible and "概率证据" in visible
    assert "21d history" in visible and "21日历史" in visible
    assert "n=746" in visible
    assert "observed" in visible and "12%" in visible
    assert "thin history" not in visible


def test_thin_probability_evidence_does_not_publish_noisy_realized_rate():
    vm = _vm(risk_envelope=envelope())
    vm["market_state"]["radar"]["dd_evidence"] = probability_evidence(
        n=34, observed=0.3235294117647059, thin=True
    )
    html = _default_visible(_dlg(_render(vm)))
    assert 'class="gde-prob-evidence is-thin"' in html
    assert "21d thin history" in html and "21日样本偏少" in html
    assert "n=34" in html
    assert "observed 32%" not in html


def test_unmatched_or_absent_probability_evidence_stays_invisible():
    for evidence in (None, probability_evidence(matched=False)):
        vm = _vm(risk_envelope=envelope())
        vm["market_state"]["radar"]["dd_evidence"] = evidence
        assert "gde-prob-evidence" not in _dlg(_render(vm))



def test_market_state_view_model_carries_probability_evidence_without_interpreting_it(monkeypatch):
    from engine.market_state import _radar_to_rd

    evidence = probability_evidence()
    monkeypatch.setattr("engine.market_state._rr_scorecard_track", lambda _mkt: None)
    rd = _radar_to_rd({
        "state": "caution",
        "top_score": 56.1,
        "dominant_label_en": "Credit stress",
        "dominant_label_zh": "信用压力",
        "drawdown_prob": {
            "h5": 0.03, "h10": 0.08, "h21": 0.16,
            "lift_h21": 0.9,
            "base_h5": 0.036, "base_h10": 0.086, "base_h21": 0.178,
            "calibration_evidence": evidence,
        },
    })
    assert rd["dd21"] == 0.16
    assert rd["dd_evidence"] == evidence


def _duration_envelope(sessions=5, since="2026-09-14"):
    e = source_envelope()
    rr = next(
        row for row in e["provenance"]["sources"]
        if row["source_id"] == "risk-radar-us"
    )
    rr["detail"].update({
        "issued_warning_sessions": sessions,
        "issued_warning_since": since,
        "issued_warning_persistent": sessions >= 5,
        "issued_warning_floor": 5,
        "issued_warning_basis": "risk_radar_forward_log_first_writer_sessions",
    })
    return e


def test_persistent_issued_warning_is_quiet_duration_context_inside_radar():
    html = _dlg(render(_duration_envelope(7, "2026-09-10")))
    visible = _default_visible(html)
    assert "Risk pressure" in visible
    assert "7 issued sessions" in visible
    assert "since 2026-09-10" in visible
    assert "风险压力" in html and "7 个已发布交易日" in html and "始于" in html
    # The research ceiling is explicit: duration is not a new alert/probability claim.
    duration = html[html.index('class="gde-stamp gde-duration"'):]
    duration = duration[:duration.index("</span>", duration.index("</span>") + 7) + 7]
    for forbidden in ("more likely", "higher odds", "validated", "Buy", "de-risk"):
        assert forbidden not in duration


def test_short_or_absent_warning_streak_does_not_render_duration_badge():
    short = _dlg(render(_duration_envelope(4, "2026-09-15")))
    assert 'class="gde-stamp gde-duration"' not in short
    base = _dlg(render(source_envelope()))
    assert 'class="gde-stamp gde-duration"' not in base


def test_duration_context_does_not_mutate_envelope_or_replace_odds_evidence():
    e = _duration_envelope(5, "2026-09-14")
    before = deepcopy(e)
    vm = _vm(risk_envelope=e)
    vm["market_state"]["radar"]["dd_evidence"] = {
        "horizons": {"h21": {
            "matched": True, "thin": False, "n": 300, "observed_rate": .01
        }}
    }
    html = _dlg(_render(vm))
    assert "Risk pressure" in html and "5 issued sessions" in html
    assert "Odds evidence" in html and "n=300" in html
    assert e == before
