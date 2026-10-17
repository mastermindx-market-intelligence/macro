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
    assert set(config)=={'copy','settled_stage','settled_hint'}
    # The one added field is the actual bilingual UI hint, not another data
    # envelope, source payload, forecast or private policy receipt.
    assert config['settled_hint'] == config['copy']['hint'][config['settled_stage']]
    assert isinstance(config['settled_hint'], list) and len(config['settled_hint']) == 2
    assert all(isinstance(word, str) for word in config['settled_hint'])
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


@pytest.mark.parametrize("lead_state,radar_state,expected_en,expected_zh", [
    ("CRACKING", "calm", "AI-hardware leaders: weakening", "AI硬件龙头：转弱"),
    ("INTACT", "elevated", "Rates / inflation shock: elevated", "利率／通胀冲击：偏高"),
    ("INTACT", "risk-off", "Rates / inflation shock: stressed", "利率／通胀冲击：承压"),
])
def test_native_producer_warning_reaches_existing_radar_and_foreground_context(
    monkeypatch, lead_state, radar_state, expected_en, expected_zh,
):
    """Real transport -> shared source adapter -> composer -> existing Jinja UI.

    Do not hand-author the expected hazard stage in the fixture: that would hide
    the producer-vocabulary defect this test is meant to catch.
    """
    from engine import market_state as ms_owner
    from engine.risk_envelope import compose_envelope
    from scripts.build_risk_envelope import build_sources

    monkeypatch.setattr(ms_owner, "_rr_scorecard_track", lambda market: None)
    session = "2026-09-18"
    radar = ms_owner._radar_to_rd({
        "schema": "risk_radar.v2", "asof": session, "state": radar_state,
        "top_score": 85, "can_force": False,
        "dominant_label_en": "Rates / inflation shock", "dominant_label_zh": "利率／通胀冲击",
    })
    measured = {"asof": session, "verdict": "MIXED", "score": 50, "radar": radar}
    leadership = {"asof": session, "state": lead_state,
                  "cohort_role": "tracked_ai_hardware_damage_monitor"}
    e = compose_envelope(
        sources=build_sources(measured, leadership, session), market="US",
        source_session=session, observed_at="2026-09-18T21:00:00Z",
        produced_at="2026-09-18T21:00:00Z", as_of=session,
    )
    html = render(e)
    visible = _default_visible(_dlg(html))
    assert expected_en in visible
    assert expected_zh in visible
    assert 'id="gde-button-context"' in html
    assert 'data-gde-stage="FRAGILE"' in html
    assert "Fragile internals" in html
    assert e["measured_state"]["score"] == 50
    assert e["authority"]["envelope_may_gate"] is False
    assert e["authority"]["envelope_may_size"] is False


def _partial_live_warning(reason="required_coverage_unavailable"):
    e = _live_fixture()
    e["hazard_summary"].update(stage=None, stage_reason=reason)
    e["live_transition"].update(candidate_stage=None, stable_stage=None, pending=None)
    for source in e["provenance"]["sources"]:
        source["as_of"] = e["source_session"]
    e["provenance"]["sources"][1]["coverage"] = "MISSING"
    return e


@pytest.mark.parametrize("reason", ["required_coverage_unavailable", "required_source_state_unmapped"])
def test_partial_live_read_keeps_independently_qualified_warning_without_promoting_stage(reason):
    e = _partial_live_warning(reason)
    out = _js_value('var before=JSON.stringify(FEED);var view=contextView(FEED,COPY);console.log(JSON.stringify({view,unchanged:before===JSON.stringify(FEED)}));', e)
    assert out["unchanged"]
    assert out["view"]["stage"] is None
    assert not out["view"]["pending"]
    assert out["view"]["label"] == ["Incomplete read", "数据不全"]
    assert out["view"]["causes"] == ["Credit stress: building", "信用压力：积聚中"]
    assert out["view"]["hint"] == ["Warning · partial read", "警告 · 信息不全"]


def test_partial_source_warning_is_visible_at_the_existing_live_button():
    out = _js_value(_LIVE_DOM + 'applyFeed(FEED);console.log(JSON.stringify(result()));', _partial_live_warning())
    assert out["cause"] == "Credit stress: building"
    assert out["hint"] == "Live: Warning · partial read"
    assert "Incomplete read" in out["stage"]
    assert not out["live"]


def test_partial_settled_warning_reaches_existing_button_without_new_stage():
    import re
    e = source_envelope()
    e["hazard_summary"].update(stage=None, stage_reason="required_coverage_unavailable")
    e["provenance"]["sources"][1]["coverage"] = "MISSING"
    html = render(e)
    button = re.search(r'<button[^>]*id="mx5BtnRisk".*?</button>', html, re.S)[0]
    assert "Warning · partial read" in button
    assert "警告 · 信息不全" in button
    assert 'data-gde-stage="UNKNOWN"' in button
    assert "Credit stress: building" in _default_visible(_dlg(html))


@pytest.mark.parametrize("mutation", ["stale", "off_session", "missing_clock", "not_contributing", "unknown_reason", "malformed_transition"])
def test_partial_warning_never_uses_stale_unattributed_or_malformed_evidence(mutation):
    e = _partial_live_warning()
    radar = e["provenance"]["sources"][2]
    if mutation == "stale": radar["coverage"] = "STALE"
    elif mutation == "off_session": radar["as_of"] = "2026-09-18"
    elif mutation == "missing_clock": radar["as_of"] = None
    elif mutation == "not_contributing": e["hazard_summary"]["contributing_sources"] = []
    elif mutation == "unknown_reason": e["hazard_summary"]["stage_reason"] = "UNRECOGNISED"
    else:
        e["hazard_summary"]["stage"] = "FRAGILE"
        e["live_transition"]["candidate_stage"] = "NONE"
    out = _js_value('console.log(JSON.stringify(contextView(FEED,COPY)));', e)
    assert out["stage"] is None
    assert out["causes"] == ["", ""]
    assert out["hint"] == ["Partial read", "读数不全"]


def test_live_failure_restores_the_actual_settled_partial_warning_not_generic_copy():
    import re
    e = source_envelope()
    e["hazard_summary"].update(stage=None, stage_reason="required_coverage_unavailable")
    e["provenance"]["sources"][1]["coverage"] = "MISSING"
    config = json.loads(re.search(r'id="gde-context-copy">(.*?)</script>', render(e), re.S)[1])
    command = _LIVE_DOM + 'nodes["gde-context-copy"].textContent=JSON.stringify(' + json.dumps(config) + ');applyFeed(FEED);unpaint(true);console.log(JSON.stringify(result()));'
    out = _js_value(command)
    assert out["hint"] == "Warning · partial read"
    assert out["live"]
    assert not out["fallback"]


@pytest.mark.parametrize("state", ["__proto__", "constructor", "toString"])
def test_partial_live_warning_requires_own_native_vocabulary_entry(state):
    e = _partial_live_warning()
    e["provenance"]["sources"][2]["state"] = state
    out = _js_value('console.log(JSON.stringify(contextView(FEED,COPY)));', e)
    assert out["stage"] is None
    assert out["causes"] == ["", ""]
    assert out["hint"] == ["Partial read", "读数不全"]


def test_partial_warning_does_not_repeat_or_resolve_duplicate_source_identity():
    e = _partial_live_warning()
    e["provenance"]["sources"].append(deepcopy(e["provenance"]["sources"][2]))
    out = _js_value('console.log(JSON.stringify(contextView(FEED,COPY)));', e)
    assert out["causes"] == ["", ""]
    assert out["hint"] == ["Partial read", "读数不全"]


@pytest.mark.parametrize("mutation", ["duplicate", "non_string_clock"])
def test_partial_settled_warning_requires_unique_source_and_string_clock(mutation):
    import re
    e = source_envelope()
    e["hazard_summary"].update(stage=None, stage_reason="required_coverage_unavailable")
    e["provenance"]["sources"][1]["coverage"] = "MISSING"
    radar = e["provenance"]["sources"][2]
    if mutation == "duplicate":
        e["provenance"]["sources"].append(deepcopy(radar))
    else:
        radar["as_of"] = e["source_session"] = 20260918
    button = re.search(r'<button[^>]*id="mx5BtnRisk".*?</button>', render(e), re.S)[0]
    assert "Warning · partial read" not in button
    assert "Partial read" in button


@pytest.mark.parametrize("bad_hint", ["ab", {"0": "not", "1": "a pair"}, ["one"], ["one", "two", "three"]])
def test_restore_ignores_malformed_settled_hint_and_uses_existing_enum(bad_hint):
    command = _LIVE_DOM + 'var config=JSON.parse(nodes["gde-context-copy"].textContent);config.settled_hint=' + json.dumps(bad_hint) + ';nodes["gde-context-copy"].textContent=JSON.stringify(config);applyFeed(FEED);unpaint(true);console.log(JSON.stringify(result()));'
    out = _js_value(command)
    assert out["hint"] == "Fragile internals"


@pytest.mark.parametrize("mutation", ["missing_stage", "string_contributors", "mapping_contributors"])
def test_partial_warning_rejects_malformed_owner_contract_in_all_web_lanes(mutation):
    """An omitted required stage is malformed, not an explicit unknown read.

    The owner schema requires stage and an array of contributor identities. Do
    not repair a cross-lane discrepancy by making the live lane more permissive.
    """
    import re
    e = _partial_live_warning()
    if mutation == "missing_stage":
        del e["hazard_summary"]["stage"]
    elif mutation == "string_contributors":
        e["hazard_summary"]["contributing_sources"] = "risk-radar-us,leadership-crack-latest"
    else:
        e["hazard_summary"]["contributing_sources"] = {"risk-radar-us": True}
    live = _js_value('console.log(JSON.stringify(contextView(FEED,COPY)));', e)
    assert live["causes"] == ["", ""]
    assert live["hint"] == ["Partial read", "读数不全"]
    button = re.search(r'<button[^>]*id="mx5BtnRisk".*?</button>', render(e), re.S)[0]
    assert "Warning · partial read" not in button
    assert "Partial read" in button


@pytest.mark.parametrize("mutation", ["missing_stage", "string_contributors", "duplicate_source", "older_source", "unknown_state"])
def test_partial_settled_cause_line_uses_the_same_qualification_as_its_button(mutation):
    e = _partial_live_warning()
    radar = e["provenance"]["sources"][2]
    if mutation == "missing_stage": del e["hazard_summary"]["stage"]
    elif mutation == "string_contributors": e["hazard_summary"]["contributing_sources"] = "risk-radar-us"
    elif mutation == "duplicate_source": e["provenance"]["sources"].append(deepcopy(radar))
    elif mutation == "older_source": radar["as_of"] = "2026-09-18"
    else: radar["state"] = "UNRECOGNISED"
    assert 'class="gde-causes"' not in _dlg(render(e))


def test_one_unqualified_partial_source_does_not_hide_a_different_qualified_warning():
    e = _partial_live_warning()
    lead = e["provenance"]["sources"][1]
    lead.update(coverage="FRESH", state="CRACKING", hazard_stage="FRAGILE", as_of="2026-09-18")
    html = _dlg(render(e))
    import re
    causes = re.search(r'<p class="gde-causes">(.*?)</p>', html, re.S)[1]
    assert "Credit stress: building" in causes
    assert "AI-hardware leaders" not in causes


# Oct15 Chairman foreground slice: the full evidence dialog stays in place,
# but qualified risk must be visible before a user reads the slower score.
def _foreground_render(e, expected_session=None):
    vm = _vm(risk_envelope=e)
    vm['market_state'].update(asof=expected_session or e.get('source_session'),
                             score=50, color='yellow', label_en='Mixed', label_zh='混合')
    return _render(vm)


def _foreground_fragment(html):
    import re
    match = re.search(r'<section\b[^>]*id="risk-response-summary".*?</section>', html, re.S)
    assert match, 'No foreground risk summary exists before the gauge'
    return match[0]


def test_qualified_risk_is_visible_before_the_unchanged_background_gauge():
    e = source_envelope()
    for source in e['provenance']['sources']: source['as_of'] = e['source_session']
    html = _foreground_render(e)
    summary = _foreground_fragment(html)
    assert html.count('id="risk-response-summary"') == 1
    assert html.index('id="risk-response-summary"') < html.index('class="mx5-sc-left"')
    assert html.index('id="risk-response-summary"') < html.index('id="dlg-risk"')
    assert 'Risk warning' in summary and '风险警告' in summary
    assert 'Credit stress: building' in summary
    assert 'Review exposure. Respect existing stops.' in summary
    assert '2026-09-18' in summary
    assert 'aria-controls="dlg-risk"' in summary
    assert 'data-state="warning"' in summary
    assert '<span class="mx5-big-score">50</span>' in html
    assert '99' not in summary and 'EMERGENCY' not in summary


def test_partial_foreground_warning_is_not_hidden_by_unknown_aggregate():
    e = _partial_live_warning(); e.pop('live_transition', None)
    summary = _foreground_fragment(_foreground_render(e))
    assert 'data-state="partial-warning"' in summary
    assert 'Credit stress: building' in summary
    assert 'Partial' in summary or 'partial' in summary


@pytest.mark.parametrize('case', ['missing', 'older_envelope', 'unqualified_sources'])
def test_foreground_unknown_does_not_invent_a_current_warning_or_all_clear(case):
    e = source_envelope()
    expected = e['source_session']
    if case == 'missing': e = {}
    elif case == 'older_envelope': expected = '2026-09-21'
    else:
        e['hazard_summary'].update(stage=None, stage_reason='required_coverage_unavailable')
        for source in e['provenance']['sources']: source['coverage'] = 'STALE'
    summary = _foreground_fragment(_foreground_render(e, expected))
    assert 'data-state="unavailable"' in summary
    assert 'Risk read unavailable' in summary
    assert 'Credit stress: building' not in summary
    assert 'all-clear' not in summary.lower()


def test_fully_qualified_quiet_read_does_not_create_a_foreground_alarm():
    e = source_envelope(); e['hazard_summary']['stage'] = 'NONE'
    for source in e['provenance']['sources']:
        source['as_of'] = e['source_session']
        if source['role'] == 'hazard_evidence': source.update(state='calm', hazard_stage='NONE')
    summary = _foreground_fragment(_foreground_render(e))
    assert 'data-state="quiet"' in summary
    assert ' hidden' in summary.split('>')[0]


_FOREGROUND_DOM = _LIVE_DOM + r'''
['risk-response-summary','risk-response-title','risk-response-cause','risk-response-action','risk-response-date'].forEach(element);
nodes['risk-response-summary'].hidden=false;
nodes['risk-response-summary'].attrs={'data-state':'partial-warning','data-expected-session':'2026-09-18'};
nodes['risk-response-title'].querySelector('.l-en').textContent='Risk warning';
nodes['risk-response-title'].querySelector('.l-zh').textContent='风险警告';
nodes['risk-response-cause'].querySelector('.l-en').textContent='Saved dated warning';
nodes['risk-response-date'].querySelector('.l-en').textContent='Settled: 2026-09-18';
function foregroundResult(){return {hidden:nodes['risk-response-summary'].hidden,
 state:nodes['risk-response-summary'].getAttribute('data-state'),
 title:nodes['risk-response-title'].querySelector('.l-en').textContent,
 cause:nodes['risk-response-cause'].querySelector('.l-en').textContent,
 action:nodes['risk-response-action'].querySelector('.l-en').textContent,
 date:nodes['risk-response-date'].querySelector('.l-en').textContent};}
'''


def test_same_live_consumer_updates_foreground_without_opening_dialog():
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));', _partial_live_warning())
    assert out['state'] == 'partial-warning' and not out['hidden']
    assert out['title'] == 'Risk warning'
    assert 'Credit stress: building' in out['cause']
    assert 'Review exposure' in out['action']
    assert '2026-09-19' in out['date'] and '15:00' not in out['date']


def test_live_failure_restores_foreground_original_dated_warning():
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);unpaint(true);console.log(JSON.stringify(foregroundResult()));')
    assert out['state'] == 'partial-warning' and not out['hidden']
    assert out['cause'] == 'Saved dated warning'
    assert out['date'] == 'Settled: 2026-09-18'


def test_pending_deescalation_does_not_clear_the_foreground_warning():
    e = _live_fixture(); e['hazard_summary']['stage']='NONE'
    e['live_transition'].update(candidate_stage='NONE', pending={'stage':'NONE','ticks':1,'needs':2})
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));', e)
    assert out['state'] == 'checking' and not out['hidden']
    assert 'confirm' in out['title'].lower() or 'checking' in out['title'].lower()


@pytest.mark.parametrize('mutation', ['old_source', 'duplicate', 'unknown_source_word'])
def test_foreground_live_warning_requires_attributable_current_source(mutation):
    e = _partial_live_warning()
    radar = e['provenance']['sources'][2]
    if mutation == 'old_source': radar['as_of']='2026-09-18'
    elif mutation == 'duplicate': e['provenance']['sources'].append(deepcopy(radar))
    else: radar['state']='UNRECOGNISED'
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',e)
    assert not out['hidden'] and out['state']=='unavailable'
    assert 'Credit stress: building' not in out['cause']


def test_failed_live_warning_cannot_restore_an_older_quiet_foreground_as_all_clear():
    """No new warning-retention store: simply refuse an implied recovery on outage."""
    command = _FOREGROUND_DOM + "nodes['risk-response-summary'].hidden=true;nodes['risk-response-summary'].attrs['data-state']='quiet';applyFeed(FEED);unpaint(true);console.log(JSON.stringify(foregroundResult()));"
    out = _js_value(command,_partial_live_warning())
    assert out['state']=='unavailable'
    assert not out['hidden']
    assert out['title']=='Risk read unavailable'
    assert '2026-09-18' in out['date']


@pytest.mark.parametrize('mutation', ['missing_stage', 'empty_session', 'foreign_market'])
def test_foreground_does_not_promote_an_invalid_or_foreign_owner_read(mutation):
    e = _partial_live_warning()
    e.pop('live_transition', None)
    if mutation == 'missing_stage': del e['hazard_summary']['stage']
    elif mutation == 'empty_session':
        e['source_session'] = ''
        for s in e['provenance']['sources']: s['as_of'] = ''
    else: e['market'] = 'CN'
    summary = _foreground_fragment(_foreground_render(e))
    assert 'data-state="unavailable"' in summary
    assert 'Credit stress: building' not in summary


@pytest.mark.parametrize('initial', ['quiet', 'unavailable'])
def test_foreground_always_keeps_bilingual_date_nodes_for_later_live_paint(initial):
    import re
    e = source_envelope()
    if initial == 'quiet':
        e['hazard_summary']['stage'] = 'NONE'
        for s in e['provenance']['sources']:
            s['as_of'] = e['source_session']
            if s['role'] == 'hazard_evidence': s.update(state='calm', hazard_stage='NONE')
    else: e = {}
    html = _foreground_fragment(_foreground_render(e))
    date_node = re.search(r'<p[^>]*id="risk-response-date"[^>]*>(.*?)</p>', html, re.S)[1]
    assert 'class="l-en"' in date_node and 'class="l-zh"' in date_node


@pytest.mark.parametrize('expected', ['2026-09-21', None])
def test_foreground_uses_independent_expected_session_not_the_old_parent_date(expected):
    e = source_envelope()
    for s in e['provenance']['sources']: s['as_of'] = e['source_session']
    vm = _vm(risk_envelope=e)
    vm['market_state'].update(asof=e['source_session'], score=50,
        freshness={'data_asof': e['source_session'], 'expected_asof': expected, 'stale': True})
    summary = _foreground_fragment(_render(vm))
    assert 'data-state="unavailable"' in summary
    assert 'Credit stress: building' not in summary


@pytest.mark.parametrize('mutation', ['older_than_expected', 'foreign_market'])
def test_live_foreground_checks_independent_session_floor_and_market(mutation):
    e = _partial_live_warning()
    setup = _FOREGROUND_DOM
    if mutation == 'older_than_expected':
        setup += "nodes['risk-response-summary'].attrs['data-expected-session']='2026-09-21';"
    else: e['market'] = 'CN'
    out = _js_value(setup+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));', e)
    assert out['state'] == 'unavailable' and not out['hidden']
    assert 'Credit stress: building' not in out['cause']


@pytest.mark.parametrize('usable', [False, None, 'true'])
def test_foreground_quiet_requires_a_usable_measured_read(usable):
    e = source_envelope()
    e['hazard_summary'].update(stage='NONE', contributing_sources=[])
    e['measured_state']['usable'] = usable
    summary = _foreground_fragment(_foreground_render(e))
    assert 'data-state="unavailable"' in summary
    assert ' hidden' not in summary.split('>')[0]
    live = _live_fixture()
    live['hazard_summary'].update(stage='NONE', contributing_sources=[])
    live['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
    live['measured_state']['usable'] = usable
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));', live)
    assert out['state'] == 'unavailable' and not out['hidden']


def test_foreground_warning_exposes_live_status_and_existing_dialog_semantics():
    summary = _foreground_fragment(_foreground_render(source_envelope()))
    opening = summary.split('>')[0]
    assert 'role="status"' in opening
    assert 'aria-live="polite"' in opening
    assert 'aria-atomic="true"' in opening
    assert 'aria-haspopup="dialog"' in summary


def test_foreground_settled_session_does_not_accept_a_timestamp_as_a_day():
    e = source_envelope()
    e['source_session'] = '2026-09-18T20:00:00Z'
    for s in e['provenance']['sources']: s['as_of'] = e['source_session']
    summary = _foreground_fragment(_foreground_render(e))
    assert 'data-state="unavailable"' in summary
    assert 'Credit stress: building' not in summary


# R5: response ordering belongs to the existing live reader, not a second store.
def _quiet_response(feed, *, session=None, built=None):
    quiet = deepcopy(feed)
    if session is not None:
        quiet['source_session'] = session
    if built is not None:
        quiet['built'] = built
    quiet['hazard_summary'].update(stage='NONE', contributing_sources=[])
    quiet['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
    quiet['measured_state']['usable'] = True
    for source in quiet['provenance']['sources']:
        source['as_of'] = quiet['source_session']
        source['coverage'] = 'FRESH'
        if source.get('role') == 'hazard_evidence':
            source.update(state='calm', hazard_stage='NONE')
    return quiet


@pytest.mark.parametrize('ordering', ['earlier_session', 'earlier_publication', 'duplicate_publication'])
def test_delayed_quiet_response_cannot_replace_a_newer_rendered_warning(ordering):
    current = _partial_live_warning()
    current['built'] = '2026-09-19 15:00:30 UTC'
    delayed = _quiet_response(current)
    if ordering == 'earlier_session':
        delayed = _quiet_response(current, session='2026-09-18', built='2026-09-19 15:01:00 UTC')
    elif ordering == 'earlier_publication':
        delayed['built'] = '2026-09-19 15:00:00 UTC'
    command = (_FOREGROUND_DOM + 'applyFeed(FEED);var before=foregroundResult();var detailBefore=result();'
               + 'applyFeed(' + json.dumps(delayed) + ');'
               + 'console.log(JSON.stringify({before,after:foregroundResult(),detailBefore,detailAfter:result()}));')
    out = _js_value(command, current)
    assert out['before']['state'] == 'partial-warning'
    assert out['after'] == out['before']
    assert out['detailAfter'] == out['detailBefore']


def test_response_order_guard_survives_outage_without_retaining_a_live_warning_as_fresh():
    current = _partial_live_warning()
    delayed = _quiet_response(current, session='2026-09-18')
    command = (_FOREGROUND_DOM + "nodes['risk-response-summary'].hidden=true;nodes['risk-response-summary'].attrs['data-state']='quiet';"
               + 'applyFeed(FEED);unpaint(true);var outage=foregroundResult();'
               + 'applyFeed(' + json.dumps(delayed) + ');console.log(JSON.stringify({outage,after:foregroundResult()}));')
    out = _js_value(command, current)
    assert out['outage']['state'] == 'unavailable'
    assert not out['outage']['hidden']
    assert out['after'] == out['outage']


def test_newer_valid_quiet_response_can_clear_the_existing_foreground_warning():
    current = _partial_live_warning()
    recovery = _quiet_response(current, built='2026-09-19 15:01:00 UTC')
    command = (_FOREGROUND_DOM + 'applyFeed(FEED);applyFeed(' + json.dumps(recovery)
               + ');console.log(JSON.stringify(foregroundResult()));')
    out = _js_value(command, current)
    assert out['state'] == 'quiet' and out['hidden']


def test_foreign_market_payload_cannot_advance_the_us_response_order():
    valid = _partial_live_warning()
    foreign = deepcopy(valid)
    foreign.update(market='CN', source_session='2026-09-20')
    command = (_FOREGROUND_DOM + 'applyFeed(' + json.dumps(foreign)
               + ');applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));')
    out = _js_value(command, valid)
    assert out['state'] == 'partial-warning'
    assert '2026-09-19' in out['date']


def test_foreign_market_payload_never_replaces_the_existing_radar_detail():
    valid = _partial_live_warning()
    foreign = deepcopy(valid)
    foreign.update(market='CN', built='2026-09-19 15:01:00 UTC')
    foreign['provenance']['sources'][2]['detail']['label_en'] = 'Foreign-market-only cause'
    command = (_FOREGROUND_DOM + 'applyFeed(FEED);applyFeed(' + json.dumps(foreign)
               + ');console.log(JSON.stringify({foreground:foregroundResult(),detail:result()}));')
    out = _js_value(command, valid)
    assert out['foreground']['state'] == 'unavailable'
    assert 'Foreign-market-only cause' not in json.dumps(out)


def test_future_source_session_cannot_poison_ordering_or_suppress_a_current_warning():
    current = _partial_live_warning()
    future = deepcopy(current)
    future['source_session'] = '2099-12-31'
    for source in future['provenance']['sources']:
        source['as_of'] = future['source_session']
    command = (_FOREGROUND_DOM + 'applyFeed(' + json.dumps(future)
               + ');var rejected=foregroundResult();applyFeed(FEED);'
               + 'console.log(JSON.stringify({rejected,current:foregroundResult()}));')
    out = _js_value(command, current)
    assert out['rejected']['state'] == 'unavailable'
    assert out['current']['state'] == 'partial-warning'
    assert '2026-09-19' in out['current']['date']


def test_foreign_read_keeps_the_original_settled_date_as_unavailable_context():
    current = _partial_live_warning()
    foreign = deepcopy(current)
    foreign.update(market='CN', built='2026-09-19 15:01:00 UTC')
    command = (_FOREGROUND_DOM + 'applyFeed(FEED);applyFeed(' + json.dumps(foreign)
               + ');console.log(JSON.stringify(foregroundResult()));')
    out = _js_value(command, current)
    assert out['state'] == 'unavailable'
    assert '2026-09-18' in out['date']
    assert '2026-09-19' not in out['date']


# R6: a second display writer must not restore an add-risk instruction while
# the existing source-qualified foreground warning is visible. No new signals.
def _wtd_action_fragment(html):
    import re
    found = re.search(r'data-wtd-primary.*?<div class="mx5-action-label"[^>]*>(.*?)</div>', html, re.S)
    assert found, 'Existing primary action row is missing'
    return found[1]


@pytest.mark.parametrize('base,foreground,expected', [
    ('RISK_ON', 'warning', 'Review exposure. Respect existing stops.'),
    ('MIXED', 'warning', 'Review exposure. Respect existing stops.'),
    ('RISK_ON', 'unavailable', 'Verify conditions before adding risk.'),
    ('RISK_ON', 'quiet', 'Stay selective. Add where setups confirm.'),
    ('RISK_OFF', 'warning', 'Reduce risk. Protect capital.'),
    ('RISK_OFF', 'unavailable', 'Reduce risk. Protect capital.'),
])
def test_primary_action_agrees_with_qualified_warning_without_weakening_risk_off(base, foreground, expected):
    e = source_envelope()
    for source in e['provenance']['sources']:
        source['as_of'] = e['source_session']
    if foreground == 'unavailable':
        e['hazard_summary'].update(stage=None, stage_reason='required_coverage_unavailable', contributing_sources=[])
        for source in e['provenance']['sources']: source['coverage'] = 'MISSING'
    elif foreground == 'quiet':
        e['hazard_summary'].update(stage='NONE', contributing_sources=[])
        for source in e['provenance']['sources']:
            if source['role'] == 'hazard_evidence': source.update(state='calm', hazard_stage='NONE')
    vm = _vm(risk_envelope=e)
    color = {'RISK_ON':'green','MIXED':'yellow','RISK_OFF':'red'}[base]
    vm['market_state'].update(asof=e['source_session'], verdict=base, color=color,
                             participation_scope=None)
    before = deepcopy(vm)
    html = _render(vm)
    assert expected in _wtd_action_fragment(html)
    assert vm == before
    assert html.count('id="risk-response-summary"') == 1


_WTD_DOM = _FOREGROUND_DOM + r'''
var label=element('wtd-label');
label.attrs={'data-wtd-base-en':'Stay selective. Add where setups confirm.',
 'data-wtd-base-zh':'保持精选，仅在入场条件确认时加仓。','data-wtd-base-verdict':'RISK_ON'};
label.querySelector('.l-en').textContent=label.attrs['data-wtd-base-en'];
label.querySelector('.l-zh').textContent=label.attrs['data-wtd-base-zh'];
var wtdIcon={style:{display:''}};
document.querySelector=function(selector){
 if(selector==='[data-wtd-primary] .mx5-action-label')return label;
 if(selector==='[data-wtd-primary] .mx5-action-icon')return wtdIcon;
 return null;
};
function actionResult(){return {en:label.querySelector('.l-en').textContent,
 zh:label.querySelector('.l-zh').textContent,icon:wtdIcon.style.display,
 base:label.getAttribute('data-wtd-base-en')};}
'''


def test_live_warning_updates_the_existing_primary_action_immediately():
    out = _js_value(_WTD_DOM+'applyFeed(FEED);console.log(JSON.stringify(actionResult()));', _partial_live_warning())
    assert out['en'] == 'Review exposure. Respect existing stops.'
    assert out['zh'] == '检查风险敞口，遵守既定止损。'
    assert out['base'] == 'Stay selective. Add where setups confirm.'
    assert out['icon'] == 'none'


def test_live_warning_outage_does_not_restore_add_risk_in_primary_action():
    setup = _WTD_DOM+"nodes['risk-response-summary'].hidden=true;nodes['risk-response-summary'].attrs['data-state']='quiet';"
    out = _js_value(setup+'applyFeed(FEED);unpaint(true);console.log(JSON.stringify(actionResult()));', _partial_live_warning())
    assert out['en'] == 'Verify conditions before adding risk.'


def test_action_projection_never_weakens_existing_risk_off_response():
    setup = _WTD_DOM+"label.attrs['data-wtd-base-verdict']='RISK_OFF';label.attrs['data-wtd-base-en']='Reduce risk. Protect capital.';label.attrs['data-wtd-base-zh']='降低风险，保护本金。';"
    out = _js_value(setup+'applyFeed(FEED);console.log(JSON.stringify(actionResult()));', _partial_live_warning())
    assert out['en'] == 'Reduce risk. Protect capital.'
    assert out['icon'] == ''


def test_newer_quiet_read_restores_the_latest_measured_action_not_the_initial_one():
    quiet = _partial_live_warning()
    quiet['built'] = '2026-09-19 15:01:00 UTC'
    quiet['hazard_summary'].update(stage='NONE', contributing_sources=[])
    quiet['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
    quiet['measured_state']['usable'] = True
    command = _WTD_DOM+'applyFeed(FEED);'+"label.attrs['data-wtd-base-verdict']='MIXED';label.attrs['data-wtd-base-en']='Trade small. Stay selective.';label.attrs['data-wtd-base-zh']='缩小仓位，精选标的。';"+'applyFeed('+json.dumps(quiet)+');console.log(JSON.stringify(actionResult()));'
    out = _js_value(command, _partial_live_warning())
    assert out['en'] == 'Trade small. Stay selective.'
    assert out['icon'] == ''


@pytest.mark.parametrize('verdict,base,expected', [
    ('RISK_ON', ['Stay selective. Add where setups confirm.', '保持精选，仅在入场条件确认时加仓。'], 'Review exposure. Respect existing stops.'),
    ('MIXED', ['Trade small. Stay selective.', '缩小仓位，精选标的。'], 'Review exposure. Respect existing stops.'),
    ('RISK_OFF', ['Reduce risk. Protect capital.', '降低风险，保护本金。'], 'Reduce risk. Protect capital.'),
])
def test_market_state_action_selector_cannot_overwrite_a_visible_warning(verdict, base, expected):
    source = (ROOT/'templates/risk_state_live.js').read_text()
    source = source[:source.index('  if (document.readyState !== "loading") tick();')]
    source += '\nglobalThis.__selectMarketAction=actionForRiskResponse;\n})();'
    command = _WTD_DOM+'applyFeed(FEED);'+source+'console.log(JSON.stringify(globalThis.__selectMarketAction('+json.dumps(base)+','+json.dumps(verdict)+')));'
    result = _js_value(command, _partial_live_warning())
    assert result[0] == expected


def test_old_pages_without_foreground_keep_existing_market_action_selection():
    source = (ROOT/'templates/risk_state_live.js').read_text()
    source = source[:source.index('  if (document.readyState !== "loading") tick();')]
    source += '\nglobalThis.__selectMarketAction=actionForRiskResponse;\n})();'
    command = _LIVE_DOM+source+'console.log(JSON.stringify(globalThis.__selectMarketAction(["base en","base zh"],"RISK_ON")));'
    assert _js_value(command) == ['base en','base zh']


def test_primary_action_missing_envelope_remains_explicitly_unavailable():
    vm = _vm(risk_envelope=None)
    vm['market_state'].update(asof='2026-09-18', verdict='RISK_ON', color='green', participation_scope=None)
    html = _render(vm)
    assert 'Verify conditions before adding risk.' in _wtd_action_fragment(html)
    assert 'Add where setups confirm.' not in _wtd_action_fragment(html)
    assert 'data-state="unavailable"' in _foreground_fragment(html)


def test_risk_off_primary_action_survives_a_warning_then_live_outage():
    command = _WTD_DOM+"nodes['risk-response-summary'].hidden=true;nodes['risk-response-summary'].attrs['data-state']='quiet';applyFeed(FEED);label.attrs['data-wtd-base-verdict']='RISK_OFF';label.attrs['data-wtd-base-en']='Reduce risk. Protect capital.';label.attrs['data-wtd-base-zh']='降低风险，保护本金。';unpaint(true);console.log(JSON.stringify({action:actionResult(),foreground:foregroundResult()}));"
    out = _js_value(command, _partial_live_warning())
    assert out['foreground']['state'] == 'unavailable'
    assert out['action']['en'] == 'Reduce risk. Protect capital.'
    assert out['action']['icon'] == ''


@pytest.mark.parametrize('verdict,foreground,expected', [
    ('RISK_ON','warning','Review exposure. Respect existing stops.'),
    ('MIXED','unavailable','Verify conditions before adding risk.'),
    ('RISK_OFF','warning','Reduce risk. Protect capital.'),
    ('MIXED','quiet','Trade small. Stay selective.'),
])
def test_actual_market_state_patcher_preserves_warning_and_updates_recovery_baseline(verdict, foreground, expected):
    from tests.test_risk_state_live_session_floor import _harness, _us_feed, BAKED_SESSION
    action = ('Verify conditions before adding risk.' if foreground == 'unavailable'
              else 'Review exposure. Respect existing stops.')
    setup = "var fg=reg('#risk-response-summary',new El('risk-response-summary'));fg.hidden="+('true' if foreground=='quiet' else 'false')+";fg.setAttribute('data-state',"+json.dumps(foreground)+");var fgAction=reg('#risk-response-action',new El('risk-response-action'));fgAction.appendChild(new El('','l-en',"+json.dumps(action)+"));fgAction.appendChild(new El('','l-zh','风险说明'));\n"
    # The older stub always returns null for descendant selectors; this new
    # node needs the real DOM's class lookup for its bilingual action spans.
    setup += "fgAction.querySelector=function(selector){return this.children.find(function(child){return child.hasClass(selector.slice(1));})||null;};\n"
    source = setup + (ROOT/'templates/risk_state_live.js').read_text()
    source += "\nout.baseAction=action.getAttribute('data-wtd-base-en');out.baseVerdict=action.getAttribute('data-wtd-base-verdict');"
    result = _harness(source, _us_feed(BAKED_SESSION, 44, verdict, live=False), 'us')
    assert 'error' not in result
    assert result['action'] == expected
    assert result['baseVerdict'] == verdict
    assert result['baseAction'] == {'RISK_ON':'Stay selective. Add where setups confirm.',
                                    'MIXED':'Trade small. Stay selective.',
                                    'RISK_OFF':'Reduce risk. Protect capital.'}[verdict]
    assert result['score'] == result['big'] == '44'


# R10: a qualified RISK_OFF measured backdrop is not permission to hide the
# foreground when the separate systemic hazard organ says NONE or is partial.
# No escalation of the hazard stage, forecast probability or sizing authority.
def test_risk_off_measured_backdrop_does_not_disappear_under_quiet_hazard():
    e = source_envelope()
    e['measured_state'].update(usable=True, verdict='RISK_OFF', score=40,
                               as_of=e['source_session'])
    e['hazard_summary'].update(stage='NONE', contributing_sources=[])
    before = deepcopy(e)
    vm = _vm(risk_envelope=e)
    vm['market_state'].update(asof=e['source_session'], verdict='RISK_OFF',
                              color='red', score=40)
    html = _render(vm)
    fragment = _foreground_fragment(html)
    assert 'data-state="measured-risk-off"' in fragment
    assert 'hidden' not in fragment.split('>')[0]
    assert 'Risk-off market backdrop' in fragment
    assert 'Reduce risk. Protect capital.' in fragment
    assert '降低风险，保护本金。' in fragment
    assert 'Reduce risk. Protect capital.' in _wtd_action_fragment(html)
    assert e == before


def test_partial_hazard_cannot_downgrade_qualified_measured_risk_off_action():
    e = _partial_live_warning()
    e['measured_state'].update(usable=True, verdict='RISK_OFF', score=40,
                               as_of=e['source_session'])
    out = _js_value(_WTD_DOM+'applyFeed(FEED);console.log(JSON.stringify({foreground:foregroundResult(),action:actionResult()}));',e)
    assert out['foreground']['state'] == 'partial-warning'
    assert 'Credit stress: building' in out['foreground']['cause']
    assert out['foreground']['action'] == 'Reduce risk. Protect capital.'
    assert out['action']['en'] == 'Reduce risk. Protect capital.'


def test_live_measured_risk_off_with_quiet_hazard_is_visible_without_new_hazard():
    e = _partial_live_warning()
    e['hazard_summary'].update(stage='NONE', contributing_sources=[])
    e['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
    e['measured_state'].update(usable=True, verdict='RISK_OFF', score=40,
                               as_of=e['source_session'])
    before = deepcopy(e)
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));', e)
    assert out['state'] == 'measured-risk-off'
    assert not out['hidden']
    assert out['title'] == 'Risk-off market backdrop'
    assert out['action'] == 'Reduce risk. Protect capital.'
    assert e == before


def test_old_or_unqualified_risk_off_measurement_cannot_force_current_foreground():
    for mutation in ('stale', 'unusable'):
        e = _partial_live_warning()
        e['hazard_summary'].update(stage='NONE', contributing_sources=[])
        e['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
        e['measured_state'].update(usable=True, verdict='RISK_OFF', score=40,
                                   as_of=e['source_session'])
        if mutation == 'stale': e['measured_state']['as_of'] = '2026-09-18'
        else: e['measured_state']['usable'] = False
        out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',e)
        assert out['state'] != 'measured-risk-off'
        assert 'Risk-off market backdrop' not in out['title']


def test_unconfirmed_hazard_change_never_weakens_verified_measured_risk_off_action():
    e = _live_fixture()
    e['measured_state'].update(usable=True, verdict='RISK_OFF', score=40,
                               as_of=e['source_session'])
    e['hazard_summary'].update(stage='FRAGILE')
    e['live_transition'].update(stable_stage='NONE', candidate_stage='FRAGILE',
                                pending={'stage':'FRAGILE','ticks':1,'needs':2})
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',e)
    assert out['state'] == 'checking'
    assert not out['hidden']
    assert out['action'] == 'Reduce risk. Protect capital.'


# R13: show WHY a native partial warning cannot certify whole-market damage.
# An old required Leadership observation is NOT a new cohort-damage vote.
def test_partial_foreground_explains_old_required_leadership_date_in_both_clients():
    e = _partial_live_warning()
    lead = next(s for s in e['provenance']['sources'] if s['source_id'] == 'leadership-crack-latest')
    lead.update(coverage='STALE', state='CRACKING', as_of='2026-09-18', required=True)
    e['hazard_summary']['unreadable_sources'] = ['leadership-crack-latest']
    e.pop('live_transition', None)
    settled = _foreground_fragment(_foreground_render(e))
    assert 'data-state="partial-warning"' in settled
    assert 'Leadership cohort: older read (2026-09-18)' in settled
    assert '龙头股群体：较早读数（2026-09-18）' in settled
    assert 'AI-hardware leaders: weakening' not in settled
    live = _partial_live_warning()
    lead = next(s for s in live['provenance']['sources'] if s['source_id'] == 'leadership-crack-latest')
    lead.update(coverage='STALE', state='CRACKING', as_of='2026-09-18', required=True)
    live['hazard_summary']['unreadable_sources'] = ['leadership-crack-latest']
    out = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',live)
    assert out['state'] == 'partial-warning'
    assert 'Leadership cohort: older read (2026-09-18)' in out['cause']
    assert 'AI-hardware leaders: weakening' not in out['cause']
    assert out['action'] == 'Review exposure. Respect existing stops.'


@pytest.mark.parametrize('mutation', ['not_unreadable', 'duplicate', 'not_required', 'future_clock'])
def test_partial_foreground_does_not_invent_old_required_leadership_clock(mutation):
    e = _partial_live_warning()
    lead = next(s for s in e['provenance']['sources'] if s['source_id'] == 'leadership-crack-latest')
    lead.update(coverage='STALE', as_of='2026-09-18', required=True)
    e['hazard_summary']['unreadable_sources'] = ['leadership-crack-latest']
    if mutation == 'not_unreadable': e['hazard_summary']['unreadable_sources'] = []
    elif mutation == 'duplicate': e['provenance']['sources'].append(deepcopy(lead))
    elif mutation == 'not_required': lead['required'] = False
    else: lead['as_of'] = '2026-09-20'
    settled = _foreground_fragment(_foreground_render(e))
    live = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',e)
    for text in (settled, live['cause']):
        assert 'Leadership cohort: older read' not in text
        assert '2026-09-18' not in text or 'Settled:' in text
    assert live['state'] == 'partial-warning'


def test_missing_required_leadership_reports_unavailable_not_a_fake_date():
    e = _partial_live_warning()
    lead = next(s for s in e['provenance']['sources'] if s['source_id'] == 'leadership-crack-latest')
    lead.update(coverage='MISSING', as_of=None, state=None, required=True)
    e['hazard_summary']['unreadable_sources'] = ['leadership-crack-latest']
    settled = _foreground_fragment(_foreground_render(e))
    live = _js_value(_FOREGROUND_DOM+'applyFeed(FEED);console.log(JSON.stringify(foregroundResult()));',e)
    for text in (settled, live['cause']):
        assert 'Leadership cohort: unavailable' in text
        assert 'older read (' not in text
    assert 'Credit stress: building' in live['cause']
