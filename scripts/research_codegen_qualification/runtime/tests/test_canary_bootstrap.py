import base64
import hashlib
import json
from pathlib import Path
import pytest
import canary_bootstrap as m


def capsule():
    import os
    from build_capsule import build_capsule
    return json.loads(build_capsule(os.environ.get('RF_QUALIFICATION_TRANSPORT_SOURCE')))


def decode(doc):
    data=json.dumps(doc).encode()
    return m.decode(data,hashlib.sha256(data).hexdigest())


def test_actual_draft_decodes_all_hashes_without_execution():
    files=decode(capsule())
    assert set(files)==m.FILES and len(files)==12
    assert all(isinstance(v,bytes) for v in files.values())


@pytest.mark.parametrize('change',['name','size','hash','root','extra','syntax'])
def test_corrupt_or_extra_source_is_rejected_before_writes(change):
    doc=capsule();f=doc['files']['fixed_canary.py']
    if change=='name':doc['files']['../escape.py']=doc['files'].pop('fixed_canary.py')
    elif change=='size':f['size']+=1
    elif change=='hash':f['sha256']='0'*64
    elif change=='root':doc['root']='other'
    elif change=='extra':f['effect_permission']=True
    else:
        data=b'not valid python!'
        f.update(size=len(data),sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode())
    with pytest.raises((m.BootstrapRefused,SyntaxError)):decode(doc)


def test_wrong_outer_hash_and_duplicate_keys_rejected():
    with pytest.raises(m.BootstrapRefused):m.decode(b'{}','0'*64)
    data=b'{"schema":1,"schema":2}'
    with pytest.raises(m.BootstrapRefused):m.decode(data,hashlib.sha256(data).hexdigest())


def test_unsafe_parent_is_never_chmodded(tmp_path):
    tmp_path.chmod(0o777)
    with pytest.raises(m.BootstrapRefused):m.safe_dir(tmp_path)
    assert tmp_path.stat().st_mode & 0o777 == 0o777


def test_existing_file_is_not_replaced(tmp_path):
    p=tmp_path/'owned';p.write_bytes(b'prior')
    with pytest.raises(FileExistsError):m._new_file(p,b'new',lambda:None)
    assert p.read_bytes()==b'prior'


def test_denied_checkpoint_prevents_file_creation(tmp_path):
    def denied():raise PermissionError('invented')
    with pytest.raises(PermissionError):m._new_file(tmp_path/'new',b'data',denied)
    assert not (tmp_path/'new').exists()


def test_decode_time_is_inside_original_900_seconds(monkeypatch):
    data=json.dumps(capsule()).encode()
    readings=iter([0,901])
    monkeypatch.setattr(m.os,'geteuid',lambda:0)
    monkeypatch.setattr(m.platform,'system',lambda:'Linux')
    monkeypatch.setattr(m.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(m,'safe_dir',lambda *_:pytest.fail('filesystem after expiry'))
    with pytest.raises(m.BootstrapRefused,match='overall_deadline'):
        m.bootstrap(data,hashlib.sha256(data).hexdigest(),'a'*64,clock=lambda:next(readings))
