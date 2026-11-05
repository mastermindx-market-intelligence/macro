"""Hermetic sequencing tests. No physical dependencies or subprocesses used."""
import json
import pytest
import fixed_canary as m
from phase_budget import QualificationBudget, PHASE_ORDER, PHASE_SECONDS


class Fixture:
    def __init__(self):
        self.now = 0
        self.calls = []
        self.budget = QualificationBudget(lambda: self.now)
        self.actions = {name: self.action(name) for name in PHASE_ORDER}
    def action(self, name):
        def act(grant, report):
            self.calls.append((name, grant))
            report.observe(name, {'status': 'invented'}, 0 if name == 'archive' else 10)
            self.now += 1
            return True
        return act
    def run(self):
        return m.sequence(self.actions, self.budget, 'a'*64)


def test_exact_order_original_deadlines_and_false_admission():
    f=Fixture();r=f.run()
    assert r['status']=='FIXED_SMOKE_PASSED'
    assert [name for name,_ in f.calls]==list(PHASE_ORDER)
    assert [g.deadline for _,g in f.calls]==[PHASE_SECONDS[n]+i for i,n in enumerate(PHASE_ORDER)]
    assert r['captured_raw_bytes']==40
    assert r['candidate_admission'] is r['containment_qualified'] is False
    assert len(m.raw(r))+r['captured_raw_bytes']<=65536


@pytest.mark.parametrize('failure_phase', PHASE_ORDER)
def test_failed_phase_never_advances_or_retries(failure_phase):
    f=Fixture()
    def failed(grant, report):
        f.calls.append((failure_phase,grant))
        report.observe('failed_capture', {'unconfirmed':True}, 3 if failure_phase!='archive' else 0)
        raise PermissionError('invented refusal')
    f.actions[failure_phase]=failed
    r=f.run();index=PHASE_ORDER.index(failure_phase)
    assert r['status']=='STOPPED_NO_RETRY' and r['budget']['frozen'] is True
    assert [n for n,_ in f.calls]==list(PHASE_ORDER[:index+1])
    assert r['completed_phases']==list(PHASE_ORDER[:index])
    assert r['observations']['failed_capture']['unconfirmed'] is True


def test_late_output_stays_in_failure_report_with_actual_count():
    f=Fixture()
    def late(grant, report):
        f.now=grant.deadline+1
        report.observe('late',{'raw_sha256':'b'*64},27)
        return True
    f.actions['cli']=late
    r=f.run()
    assert r['status']=='STOPPED_NO_RETRY' and r['captured_raw_bytes']==27
    assert 'late' in r['observations'] and not r['completed_phases']


@pytest.mark.parametrize('value',[None,1,'PASS',{},False])
def test_truthiness_is_not_phase_acceptance(value):
    f=Fixture();f.actions['cli']=lambda *_:value
    assert f.run()['status']=='STOPPED_NO_RETRY'


def test_metadata_pressure_stops_before_more_effects():
    f=Fixture()
    def large(grant,report):
        report.observe('large',{'fixture':'x'*50000},16384)
        return True
    f.actions['cli']=large
    r=f.run()
    assert r['status']=='EVIDENCE_RETURN_OVERFLOW' and f.calls==[]
    assert r['captured_raw_bytes']==16384 and len(m.raw(r))<2048


def test_second_sequence_does_not_reset_shared_budget():
    f=Fixture();assert f.run()['status']=='FIXED_SMOKE_PASSED'
    before=len(f.calls);r=f.run()
    assert r['status']=='STOPPED_NO_RETRY' and len(f.calls)==before


def test_short_remaining_raw_pool_refuses_before_phase():
    f=Fixture()
    def large(grant,report):
        report.observe('large',{'fixture':'x'*48000},1000)
        return True
    f.actions['cli']=large
    r=f.run()
    assert r['status']=='STOPPED_NO_RETRY'
    assert [n for n,_ in f.calls]==['archive']


def test_missing_or_added_phase_rejected_before_any_action():
    f=Fixture();f.actions['extra']=lambda *_:True
    with pytest.raises(m.CanaryRefused):f.run()
    assert f.calls==[]


def test_production_entry_rejects_override_before_imports():
    with pytest.raises(m.CanaryRefused):
        m.execute('/invented','/invented',QualificationBudget(lambda:0),'a'*64)


def test_original_attempt_error_survives_failed_partial_capture():
    f=Fixture();r=m.Report(f.budget,'a'*64)
    def failed():raise PermissionError('invented original')
    def retain():raise m.BudgetRefused('invented expired')
    with pytest.raises(PermissionError,match='invented original'):
        m.retain_after_attempt(failed,retain,r)
    assert r.doc['original_attempt_failure_type']=='PermissionError'
    assert r.doc['capture_retention_failure_type']=='BudgetRefused'


def test_success_does_not_survive_failed_evidence_retention():
    f=Fixture();r=m.Report(f.budget,'a'*64)
    def retain():raise m.BudgetRefused('invented expired')
    with pytest.raises(m.BudgetRefused):m.retain_after_attempt(lambda:'success',retain,r)
