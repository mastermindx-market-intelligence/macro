"""No subprocesses or Docker; receipt call trace only."""
import pytest
import qualification_smoke as q
import test_qualification_smoke as f
from test_qualification_smoke import no_subprocess, sources, comp

def test_already_frozen_attempt_never_publishes(comp,monkeypatch):
    engine=q.FixedQualificationEngine(comp.t,comp.plan)
    engine._frozen=True; calls=[]
    monkeypatch.setattr(q,'_write_receipt',lambda *a,**kw:calls.append(a))
    with pytest.raises(comp.t.TransportPermissionRefusal):q.execute_attempt(comp,engine,'/invented-unused')
    assert calls == []

def test_refused_orchestrator_does_not_append_privileged_receipt(comp,monkeypatch):
    engine=q.FixedQualificationEngine(comp.t,comp.plan); calls=[]
    monkeypatch.setattr(q,'_write_receipt',lambda *a,**kw:calls.append(a))
    def refuse(*_):
        engine._frozen=True
        raise comp.t.TransportPermissionRefusal('invented denial')
    monkeypatch.setattr(comp.t.TransportOrchestrator,'execute',refuse)
    with pytest.raises(comp.t.TransportPermissionRefusal):q.execute_attempt(comp,engine,'/invented-unused')
    assert len(calls)==1, 'only precreate publication is allowed before denial'

def test_returned_frozen_attempt_never_publishes_settlement(comp,monkeypatch):
    engine=q.FixedQualificationEngine(comp.t,comp.plan); calls=[]
    monkeypatch.setattr(q,'_write_receipt',lambda *a,**kw:calls.append(a))
    def frozen_return(*_):
        engine._frozen=True
        return object() # no attempt fields may be consulted after frozen effect
    monkeypatch.setattr(comp.t.TransportOrchestrator,'execute',frozen_return)
    with pytest.raises(comp.t.TransportPermissionRefusal):q.execute_attempt(comp,engine,'/invented-unused')
    assert len(calls)==1
