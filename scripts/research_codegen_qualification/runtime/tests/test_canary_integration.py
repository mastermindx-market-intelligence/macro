"""Join real phase dispatcher/projection/binding with invented physical facts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import pytest

import fixed_canary as m
import runsc_install as install
import qualification_smoke as smoke
import qualification_runsc_smoke as runsc
import qualification_manifest as projection
import pinned_archive_phase as archive
import fixed_image_phase as image
import cli29_anonymous_config as cli
from phase_budget import QualificationBudget
from test_qualification_manifest import successful_result


def test_production_helpers_join_and_project_real_contracts(tmp_path,monkeypatch):
    base=tmp_path/'operation';base.mkdir();source=base/'source';source.mkdir();work=base/'work';work.mkdir()
    monkeypatch.setattr(m,'BASE',base)
    monkeypatch.setattr(m.os,'geteuid',lambda:0)
    events=[];store={}
    def write(path,data,mode,owner,chown_fn,checkpoint=None):
        assert mode==0o600 and owner==(0,0) and callable(chown_fn)
        checkpoint();Path(path).write_bytes(data)
    monkeypatch.setattr(install,'write_private_file',write)
    monkeypatch.setattr(cli,'execute',lambda path,**kw: events.append('cli') or
                        {'status':'PASS','raw_output_bytes':7})
    doc=successful_result()
    doc['operation_id']=doc['binding']['operation_id']=m.OPERATION
    monkeypatch.setattr(archive,'acquire',lambda path,deadline: events.append('archive') or
        {'archive_path':str(work/'archive'),'member_sha256':doc['bundle']['member_sha256']})
    class FakeInstaller:
        def __init__(self,layout,runner,*,budget):
            self.host_id='fixture-host';self.daemon_id='fixture-daemon';self.frozen=False
            self.docker_config_path='/invented/private/config';self.layout=layout
            self.socket_facts={'identity':'invented'}
            self.socket_inspector=lambda *_:self.socket_facts
            self._verify_client_config=lambda:None
        def execute(self,path,sha):
            binding=json.loads(Path(path).read_bytes())
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
            assert binding['operation_id']==m.OPERATION and binding['root_id']==m.ROOT
            events.append('install');return 0,copy.deepcopy(doc)
    monkeypatch.setattr(install,'InstallEngine',FakeInstaller)
    monkeypatch.setattr(smoke,'load_transport_module',lambda _:NS())
    def prepare(engine,transport,**kw):
        events.append('image');kw['observe']({'raw_bytes':5,'name':'invented'})
        intent={'phase':'invented-only'}
        assert kw['before_pull'](intent)==m.digest(intent)
        return {'status':'PRESENT','host':{'Name':'fixture-host','KernelVersion':'fixture-kernel',
            'OperatingSystem':'fixture-os'},'observations':[{'already-retained':True}]}
    monkeypatch.setattr(image,'prepare',prepare)
    def verify(manifest):
        assert manifest['actual_hostname']=='fixture-host'
        assert manifest['members']['runsc']['sha256']==projection.RUNSC
        events.append('verify-installed')
    monkeypatch.setattr(runsc,'verify_installed_bundle',verify)
    monkeypatch.setattr(runsc,'build_runsc_composition',lambda *args:NS(t=NS(),plan=NS()))
    monkeypatch.setattr(smoke,'_real_executor',lambda _:lambda *a,**kw:pytest.fail('real executor called'))
    class FakeSmoke:
        def __init__(self,t,plan,**kw):
            self.ledger=[];self.settled_cid='c'*64;self.self_cleanup_confirmed=True;self.frozen=False
            assert set(kw['binding'])==smoke._BINDING_KEYS
            store['binding']=kw['binding']
        def evidence_ledger(self):return [{'invented':'only'}]
    monkeypatch.setattr(runsc,'RunscQualificationEngine',FakeSmoke)
    def attempt(comp,engine,path):
        events.append('smoke')
        engine.ledger.append({'stdout':b'invented','stderr':b''})
        assert engine._t0>=0
        return NS()
    monkeypatch.setattr(smoke,'execute_attempt',attempt)
    monkeypatch.setattr(smoke,'validate_verdict',lambda *_:{'mechanical_checks_passed':True,
                         'candidate_admission':False,'containment_qualified':False})
    r=m.execute(str(source),str(work),QualificationBudget(lambda:0),'a'*64,clock=lambda:0)
    assert r['status']=='FIXED_SMOKE_PASSED',r
    assert events==['cli','archive','install','image','verify-installed','smoke']
    assert r['captured_raw_bytes']==20
    assert len([k for k in r['observations'] if k.startswith('image_capture_')])==1
    assert 'observations' not in r['observations']['image']
    assert store['binding']['client_config_sha256']==smoke.ANONYMOUS_CLIENT_CONFIG_SHA256


def test_actual_smoke_clock_origin_includes_pre_create_setup(monkeypatch):
    physical=runsc.RunscQualificationEngine(NS(),NS())
    physical._t0=110
    monkeypatch.setattr(smoke.time,'monotonic',lambda:239)
    assert physical._budget('absence','cleanup',10)==1
    monkeypatch.setattr(smoke.time,'monotonic',lambda:240)
    physical._t=NS(TransportStateError=ValueError)
    with pytest.raises(ValueError,match='attempt budget exhausted'):
        physical._budget('absence','cleanup',10)
