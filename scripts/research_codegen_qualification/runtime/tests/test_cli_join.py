from pathlib import Path
import pytest
import cli29_anonymous_config as m


def test_expired_outer_deadline_stops_before_fixture(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    monkeypatch.setattr(m.tempfile,'mkdtemp',lambda **_:pytest.fail('fixture created'))
    with pytest.raises(RuntimeError,match='invalid_original_envelope'):
        m.execute(tmp_path,absolute_deadline=0)


def test_permission_denied_does_not_delete_fixture_or_start_client(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    fixture=tmp_path/'f';fixture.mkdir(mode=0o700)
    monkeypatch.setattr(m.tempfile,'mkdtemp',lambda **_:str(fixture))
    monkeypatch.setattr(m.os,'fsencode',lambda _:b'/invented/short/api.sock')
    def denied(*args,**kwargs):raise PermissionError('invented')
    monkeypatch.setattr(m,'private_file',denied)
    monkeypatch.setattr(m.shutil,'rmtree',lambda *_:pytest.fail('cleanup after refusal'))
    monkeypatch.setattr(m.subprocess,'Popen',lambda *_:pytest.fail('client after refusal'))
    r=m.execute(tmp_path)
    assert r['status']=='FAIL' and r['permission_frozen'] is True
    assert r['cleanup_obligation'] is True and r['raw_output_bytes']==0


def test_cleanup_error_returns_partial_capture_facts(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    fixture=tmp_path/'f';fixture.mkdir(mode=0o700)
    monkeypatch.setattr(m.tempfile,'mkdtemp',lambda **_:str(fixture))
    monkeypatch.setattr(m.os,'fsencode',lambda _:b'/invented/short/api.sock')
    def failure(*args,**kwargs):raise RuntimeError('invented ordinary failure')
    def cleanup_failure(*args):raise OSError('invented')
    monkeypatch.setattr(m,'private_file',failure)
    monkeypatch.setattr(m.shutil,'rmtree',cleanup_failure)
    r=m.execute(tmp_path)
    assert r['status']=='FAIL' and r['problem']=='fixture_cleanup_unconfirmed'
    assert r['raw_output_bytes']==0 and r['commands']==[]
