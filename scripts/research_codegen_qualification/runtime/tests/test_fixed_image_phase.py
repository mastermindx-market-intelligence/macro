import hashlib
import json
from types import SimpleNamespace as NS
import pytest
import fixed_image_phase as m
import transport


def raw(doc): return json.dumps(doc,sort_keys=True,separators=(',',':')).encode()


class Fixture:
    def __init__(self, missing=False):
        self.missing=missing;self.calls=[];self.intents=[];self.events=[]
        self.overrides={};self.observations=[]
        self.installer=NS(status='OK_INSTALLED',frozen=False,
            binding=NS(operation_id='rf-fixed-smoke-runsc-01a1333c-v4'),
            docker_config_path='/invented/own/client',
            _verify_client_config=lambda:None,
            socket_inspector=lambda *_:{'dev':1,'ino':2},
            socket_facts={'dev':1,'ino':2},layout=NS(docker_socket='/var/run/docker.sock'),
            root_uid=0,daemon_id='fixture-daemon',host_id='fixture-host')
        self.transport=NS(collect_process=self.collect,
                          control_permission_refusal=transport.control_permission_refusal)
    def result(self, code, output, **kw):
        return NS(returncode=code,output=output,timed_out=kw.get('timeout',False),
                  output_truncated=kw.get('truncated',False),error_type=kw.get('error'))
    def image(self):
        return [{'Id':m.gate.IMAGE_ID,'RepoDigests':[m.gate.IMAGE],'Os':'linux',
                 'Architecture':'amd64','Config':{'Entrypoint':None,'Cmd':['python3'],
                 'User':'','WorkingDir':'/','Volumes':None,'Env':list(m.gate.ENV)}}]
    def collect(self, argv, **bounds):
        self.calls.append((argv,bounds));tail=argv[5:]
        self.events.append(tuple(tail[:2]))
        count=len(self.calls)
        if count in self.overrides:return self.overrides[count]
        if tail[0]=='version':return self.result(0,raw({'Client':'29.1.3','Server':'29.1.3'}))
        if tail[0]=='info':return self.result(0,raw({'ID':'fixture-daemon','Name':'fixture-host',
            'KernelVersion':'fixture-kernel','OperatingSystem':'fixture-os','ServerVersion':'29.1.3',
            'OSType':'linux','Architecture':'x86_64','Containers':0,'ContainersRunning':0}))
        if tail[:2]==('image','inspect'):
            return self.result(1,b'[]\n'+m.gate.ABSENCE) if self.missing else self.result(0,raw(self.image()))
        if tail[:2]==('image','pull'):
            self.missing=False;return self.result(0,b'fixture pull complete\n')
        raise AssertionError('uncommissioned argv')
    def persist(self, intent):
        self.intents.append(intent);self.events.append(('durable-intent',))
        return hashlib.sha256(raw(intent)).hexdigest()
    def run(self, **kwargs):
        opts=dict(deadline=240,raw_cap=16384,before_pull=self.persist,
                  observe=self.observations.append,clock=lambda:0)
        opts.update(kwargs)
        return m.prepare(self.installer,self.transport,**opts)
    def pulls(self):return [a for a,b in self.calls if a[5:7]==('image','pull')]


def test_present_reuses_exact_image_and_retains_raw():
    f=Fixture();r=f.run()
    assert r['pull_count']==0 and not f.intents and not f.pulls()
    assert r['status']=='PRESENT' and r['candidate_admission'] is False
    assert r['raw_bytes']==sum(x['raw_bytes'] for x in r['observations'])
    assert all(x['raw_b64'] for x in r['observations'])
    assert all(a[:5]==('/usr/bin/docker','--host','unix:///var/run/docker.sock',
                      '--config','/invented/own/client') for a,b in f.calls)


def test_exact_absence_one_pull_after_durable_intent_and_readback():
    f=Fixture(missing=True);r=f.run()
    assert r['pull_count']==1 and len(f.pulls())==1
    assert f.events.index(('durable-intent',)) < f.events.index(('image','pull'))
    a,b=next(x for x in f.calls if x[0][5:7]==('image','pull'))
    assert a[-1]==m.gate.IMAGE and b['deadline_seconds']<=200 and b['output_cap_bytes']<8192
    assert r['observations'][-1]['name']=='image_inspect'


@pytest.mark.parametrize('first', [
    NS(returncode=0,output=b'{}',timed_out=True,output_truncated=False,error_type=None),
    NS(returncode=0,output=b'{}',timed_out=False,output_truncated=True,error_type=None),
    NS(returncode=0,output=b'{}',timed_out=False,output_truncated=False,error_type='PermissionError'),
    NS(returncode=0,output=b'Error response from daemon: permission denied\n',timed_out=False,
       output_truncated=False,error_type=None)])
def test_incomplete_or_denied_control_never_advances(first):
    f=Fixture(True);f.overrides[1]=first
    with pytest.raises(m.ImagePhaseRefused):f.run()
    assert len(f.calls)==1 and not f.pulls()


def test_arbitrary_not_found_never_pulls():
    f=Fixture(True);f.overrides[3]=f.result(1,b'Error: NotFound\n')
    with pytest.raises(m.gate.ImageGateRefused):f.run()
    assert len(f.calls)==3 and not f.pulls()


def test_changed_daemon_after_absence_never_pulls():
    f=Fixture(True);f.overrides[5]=f.result(0,raw({'ID':'replacement'}))
    with pytest.raises(m.ImagePhaseRefused):f.run()
    assert len(f.calls)==5 and not f.pulls()


@pytest.mark.parametrize('receipt',[None,False,'0'*64])
def test_unconfirmed_intent_never_pulls(receipt):
    f=Fixture(True)
    with pytest.raises(m.ImagePhaseRefused):f.run(before_pull=lambda _:receipt)
    assert not f.pulls()


def test_intent_permission_refusal_has_no_followup_command():
    f=Fixture(True)
    def denied(_):raise PermissionError('invented')
    with pytest.raises(PermissionError):f.run(before_pull=denied)
    assert len(f.calls)==5 and not f.pulls()


def test_unknown_pull_never_retries_or_verifies():
    f=Fixture(True);f.overrides[6]=f.result(None,b'partial',timeout=True)
    with pytest.raises(m.ImagePhaseRefused):f.run()
    assert len(f.pulls())==1 and len(f.calls)==6
    assert len(f.observations)==6
    assert f.observations[-1]['raw_bytes']==len(b'partial')
    assert f.observations[-1]['timed_out'] is True


def test_observer_failure_preserves_capture_and_stops_before_followup():
    f=Fixture(True)
    def refused(record):
        f.observations.append(record)
        raise RuntimeError('invented sink failure')
    with pytest.raises(RuntimeError):f.run(observe=refused)
    assert len(f.calls)==1 and len(f.observations)==1 and not f.pulls()


def test_source_socket_and_operation_changes_stop_before_command():
    for name in ('socket','operation','config'):
        f=Fixture()
        if name=='socket':f.installer.socket_facts={'dev':1,'ino':99}
        elif name=='operation':f.installer.binding.operation_id='unrelated'
        else:
            def denied():raise PermissionError('invented config denial')
            f.installer._verify_client_config=denied
        with pytest.raises((m.ImagePhaseRefused,PermissionError)):f.run()
        assert f.calls==[]


def test_unsafe_present_image_is_not_repaired_or_pulled():
    f=Fixture();doc=f.image();doc[0]['Config']['Volumes']={'/unexpected':{}}
    f.overrides[3]=f.result(0,raw(doc))
    with pytest.raises(m.gate.ImageGateRefused):f.run()
    assert not f.pulls() and len(f.calls)==3
