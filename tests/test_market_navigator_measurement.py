from dataclasses import replace
import pytest
from engine.market_navigator import ContractError
from engine.market_navigator_measurement import IndexSession,vix1d_measurement_context,threshold_study_coverage

S=IndexSession('fixture:regular-session','v1','2026-10-20T12:00:00Z',
    '2026-10-21T13:31:00Z','2026-10-21T20:00:00Z','2026-10-21T20:15:00Z')

def annotate(time,session=S,cutoff='2026-10-21T21:00:00Z'):
    return vix1d_measurement_context(observed_at=time,as_of=cutoff,session=session)

@pytest.mark.parametrize('clock,phase',[
    ('13:31:00','near_and_next_term'),('19:00:00','near_and_next_term'),
    ('19:00:01','persisted_near_term_interpolation'),('19:59:59','persisted_near_term_interpolation'),
    ('20:00:00','next_term_only'),('20:15:00','next_term_only')])
def test_exact_phase_boundaries(clock,phase):
    out=annotate('2026-10-21T'+clock+'Z')
    assert out['phase']==phase and out['methodology_annotation_only']
    assert not out['directional_signal'] and not any(out['authority'].values())

@pytest.mark.parametrize('clock',['13:30:59','20:15:01'])
def test_outside_publication_window(clock):
    assert annotate('2026-10-21T'+clock+'Z')['status']=='outside_supplied_dissemination_window'

def test_early_close_comes_from_owner_not_hardcoded_1600():
    early=replace(S,near_expiry='2026-10-21T17:00:00Z',dissemination_end='2026-10-21T17:15:00Z')
    assert annotate('2026-10-21T16:30:00Z',early)['phase']=='persisted_near_term_interpolation'
    assert annotate('2026-10-21T17:00:00Z',early)['phase']=='next_term_only'

def test_offset_equivalence():
    assert annotate('2026-10-21T16:00:00-04:00')==annotate('2026-10-21T20:00:00Z')

def test_unknown_calendar_and_future_evidence_abstain():
    assert annotate('2026-10-21T14:00:00Z',None)['status']=='calendar_evidence_missing'
    late=replace(S,available_at='2026-10-21T15:00:00Z')
    assert annotate('2026-10-21T14:00:00Z',late,'2026-10-21T14:01:00Z')['status']=='calendar_evidence_not_yet_available'
    assert annotate('2026-10-21T14:02:00Z',S,'2026-10-21T14:01:00Z')['status']=='observation_not_yet_available'

@pytest.mark.parametrize('changes',[{'near_expiry':S.dissemination_start},
    {'dissemination_end':'2026-10-21T15:00:00Z'}, {'available_at':'2026-10-22T00:00:00Z'},
    {'source_revision':''}, {'near_expiry':'2026-10-21'}])
def test_invalid_session_refused(changes):
    with pytest.raises(ContractError): replace(S,**changes)

def test_daily_data_cannot_qualify_intraday_rule():
    out=threshold_study_coverage(frequency='daily',original_availability=False,
        joint_underlying=False,executable_option_quotes=False,ordering_resolved=False)
    assert len(out['missing_requirements'])==5
    assert not out['predictive_validation'] and not out['trial_admitted']

def test_minute_data_without_path_order_is_not_exact():
    out=threshold_study_coverage(frequency='minute',original_availability=True,
        joint_underlying=True,executable_option_quotes=True,ordering_resolved=False)
    assert out['missing_requirements']==['path_order_unresolved']

def test_all_flags_still_do_not_prove_source_or_admission():
    out=threshold_study_coverage(frequency='tick',original_availability=True,
        joint_underlying=True,executable_option_quotes=True,ordering_resolved=True)
    assert out['status']=='declared_coverage_only' and out['missing_requirements']==[]
    assert not out['source_verified'] and not out['trial_admitted']

def test_truthy_string_is_not_coverage():
    with pytest.raises(ContractError):
        threshold_study_coverage(frequency='tick',original_availability='yes',
            joint_underlying=True,executable_option_quotes=True,ordering_resolved=True)
