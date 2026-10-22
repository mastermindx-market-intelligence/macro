"""Synthetic analyst-intake tests; no model call, scraped corpus or outcome lookup."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import pytest
from engine.market_navigator import ContractError
from engine import market_navigator_research as research
from engine.research_intelligence import extractor

CLAIM='If SPY closes above 500 tomorrow, a rebound toward 510 is possible.'
BODY=CLAIM+' A close below 495 would weaken that view.'
DOC={'id':'synthetic-analyst-case','source_type':'other','source_name':'Synthetic analyst',
     'published_at':'2026-10-21T20:00:00Z','content_sha256':sha256(BODY.encode()).hexdigest()}

def output(claims=None):
    return {'schema':'mastermind.research_intelligence.v1','document':deepcopy(DOC),
        'claims':[{'statement':s,'evidence':[{'quote_span':s}],'numbers':['510'],
                   'entities':['SPY'],'horizon':'tomorrow','explicit':True}
                  for s in (claims or [CLAIM])],
        'analysis':{'thesis':{'summary':'The source frames a possible recovery contingent on price confirmation.',
                             'direction':'mixed','support_claim_indices':[0]},
                    'forecasts':[{'statement':'An analyst interpretation, not a calibrated probability.',
                      'confidence':'99%','horizon':'next day','support_claim_indices':[0]}]}}

def ruler(**changes):
    args=dict(claim_id=research.claim_identity(DOC['content_sha256'],CLAIM),
        annotation_ref='fixture:reviewed-ruler',annotation_available_at='2026-10-21T20:55:00Z',
        subject='SPY:ARCX',outcome='level_touch',decision_at='2026-10-21T21:00:00Z',
        deadline='2026-10-22T20:00:00Z',horizon='next_session',conditional=True,
        trigger_ref='fixture:completed-close',invalidation_ref='fixture:495-close')
    return research.ResearchRuler(**(args|changes))

def run(value=None,**changes):
    args=dict(document=DOC,source_body=BODY,captured_at='2026-10-21T21:01:00Z',
        revision_available_at='2026-10-21T20:00:01Z',rulers=(ruler(),))
    return research.audit_extraction(json.dumps(value or output()),**(args|changes))

def test_complete_fields_are_not_forecast_or_prospective_proof(monkeypatch):
    def forbidden(*a,**k): raise AssertionError('model call prohibited')
    monkeypatch.setattr(extractor,'_default_call',forbidden)
    result=run();row=result['claims'][0]
    assert row['status']=='ruler_fields_present_not_validated' and row['gaps']==[]
    assert not row['prospective_proof'] and row['forecast_probability'] is None
    assert not result['trial_registered'] and not result['source_authenticity_proven']
    assert not any(result['authority'].values())
    assert '99%' not in json.dumps(result) and CLAIM not in json.dumps(result)

def test_missing_ruler_and_revision_are_retained_as_unscoreable():
    out=run(rulers=(),revision_available_at=None)
    assert out['counts']=={'grounded_claims':1,'unscoreable':1}
    assert out['claims'][0]['gaps']==['original_revision_availability_unknown','reviewed_ruler_missing']

def test_current_revision_cannot_launder_historical_knowledge():
    result=run(revision_available_at='2026-10-22T12:00:00Z',captured_at='2026-10-22T12:01:00Z')
    assert 'source_revision_after_decision' in result['claims'][0]['gaps']

def test_retrospective_ruler_not_forward_evidence():
    result=run(rulers=(ruler(annotation_available_at='2026-10-22T19:00:00Z'),))
    assert 'retrospective_annotation' in result['claims'][0]['gaps']
    assert not result['claims'][0]['prospective_proof']

@pytest.mark.parametrize('missing',['subject','outcome','decision_at','deadline','horizon','conditional','trigger_ref','invalidation_ref'])
def test_missing_forecast_fields_are_not_invented(missing):
    result=run(rulers=(ruler(**{missing:None}),))
    assert result['claims'][0]['gaps']
    assert result['claims'][0]['status']=='not_scoreable_as_specified'

def test_option_profit_needs_instrument_expression():
    row=run(rulers=(ruler(outcome='option_pnl'),))['claims'][0]
    assert 'executable_option_expression_unspecified' in row['gaps']

def test_qualitative_analysis_is_not_scored_as_prediction():
    row=run(rulers=(ruler(outcome='qualitative'),))['claims'][0]
    assert 'qualitative_not_scored' in row['gaps']

@pytest.mark.parametrize('quote',[
    'a rebound toward 510 is possible.',
    'SPY will rebound to 510 tomorrow.',
    'If SPY closes above 500 tomorrow, a rebound toward 510 is guaranteed.'
])
def test_lost_condition_or_changed_modality_rejected(quote):
    with pytest.raises(ContractError,match='grounding'):
        run(output([quote]),rulers=())

def test_source_hash_mismatch_rejected():
    with pytest.raises(ContractError,match='source body differs'):
        run(source_body=BODY+' Added later.')

def test_dropped_source_claim_does_not_rebind_annotation_index():
    extra='An unrelated fabricated claim.'
    with pytest.raises(ContractError,match='absent or ungrounded'):
        run(output([CLAIM,extra]),rulers=(ruler(claim_id=research.claim_identity(DOC['content_sha256'],extra)),))

def test_duplicate_annotation_rejected():
    with pytest.raises(ContractError,match='duplicate'):run(rulers=(ruler(),ruler()))

def test_duplicate_source_claim_rejected():
    with pytest.raises(ContractError,match='deduplication'):run(output([CLAIM,CLAIM]))

@pytest.mark.parametrize('changes',[
    {'outcome':'profitable_trade'}, {'conditional':1}, {'deadline':'2026-10-21T20:59:00Z'},
    {'decision_at':'2026-10-21'}, {'annotation_ref':''}, {'claim_id':'not-a-digest'}])
def test_malformed_ruler(changes):
    with pytest.raises(ContractError):ruler(**changes)

@pytest.mark.parametrize('changes',[
    {'captured_at':'2026-10-21T19:00:00Z'},
    {'revision_available_at':'2026-10-21T21:02:00Z'},
    {'revision_available_at':'2026-10-21T19:59:00Z'}])
def test_source_clock_order(changes):
    with pytest.raises(ContractError):run(**changes)

def test_date_only_publication_is_unknown_not_midnight():
    value=output();doc=DOC|{'published_at':'2026-10-21'};value['document']=doc
    assert 'publication_clock_unknown' in run(value,document=doc)['claims'][0]['gaps']

def test_input_objects_preserved_and_no_source_prose_in_output():
    value=output();before=deepcopy(value);result=run(value)
    assert value==before
    assert not result['raw_source_included'] and BODY not in json.dumps(result)
