"""Payload integrity and denied launch only. Never runs sudo or Docker."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import pytest
import canary_carrier as m


def inputs():
    b=b'''def bootstrap(capsule,sha,commission,clock):
    assert clock()==123.5
    return {"status":"INVENTED_ONLY", "candidate_admission":False}
'''
    c=b'invented capsule'
    return b,hashlib.sha256(b).hexdigest(),c,hashlib.sha256(c).hexdigest(),'a'*64


def test_payload_executes_exact_sealed_stub_and_preserves_start():
    data=m.payload(*inputs(),123.5)
    out=io.StringIO()
    with contextlib.redirect_stdout(out):exec(compile(data,'invented','exec'),{})
    doc=json.loads(out.getvalue())
    assert doc=={'status':'INVENTED_ONLY','candidate_admission':False}


def test_bootstrap_exception_returns_type_without_private_text():
    b=b'def bootstrap(*args,**kwargs): raise ValueError("invented private text")'
    args=list(inputs());args[:2]=[b,hashlib.sha256(b).hexdigest()]
    out=io.StringIO()
    with contextlib.redirect_stdout(out):exec(compile(m.payload(*args,123.5),'invented','exec'),{})
    doc=json.loads(out.getvalue())
    assert doc['status']=='BOOTSTRAP_STOPPED_NO_RETRY' and doc['failure_type']=='ValueError'
    assert 'private text' not in out.getvalue()


@pytest.mark.parametrize('index',[1,3,4])
def test_wrong_hash_or_commission_fails_before_process(index,monkeypatch):
    args=list(inputs());args[index]='invalid'
    monkeypatch.setattr(m.subprocess,'Popen',lambda *_a,**_k:pytest.fail('process launched'))
    with pytest.raises(ValueError):m.launch(*args)


def test_denied_launch_has_one_attempt_and_no_signal(monkeypatch):
    calls=[]
    def denied(argv,**kwargs):
        calls.append((argv,kwargs));raise PermissionError('invented')
    monkeypatch.setattr(m.subprocess,'Popen',denied)
    monkeypatch.setattr(m.os,'killpg',lambda *_:pytest.fail('signal after no launch'))
    result=m.launch(*inputs())
    assert len(calls)==1 and calls[0][0]==m.ARGV
    assert calls[0][1]['env']==m.ENV
    assert result['problem']=='PermissionError' and result['pid'] is None
    assert result['physical_result_accepted'] is False
