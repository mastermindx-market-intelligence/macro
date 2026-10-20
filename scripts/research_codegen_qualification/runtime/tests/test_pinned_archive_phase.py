import hashlib
import io
import os
from pathlib import Path
import tarfile
from types import SimpleNamespace
import pytest
import pinned_archive_phase as m


def fixture_spec():
    data = {'runsc': b'\x7fELFinvented', 'gvisor-bin/invented': b'not executable'}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:bz2') as tf:
        for name, value in data.items():
            item = tarfile.TarInfo(name); item.size = len(value)
            tf.addfile(item, io.BytesIO(value))
    raw = buf.getvalue()
    spec = m.installer.Contract(archive_sha256=hashlib.sha256(raw).hexdigest(),
        archive_size=len(raw), runsc_member_sha256=hashlib.sha256(data['runsc']).hexdigest(),
        member_sizes={k:len(v) for k,v in data.items()}, expanded_total=sum(map(len,data.values())))
    return raw, spec


class Response(io.BytesIO):
    status = 200
    headers = {}
    def geturl(self): return m.URL


def run(tmp_path, *, payload=None, opener=None, clock=lambda:0, deadline=240):
    tmp_path.chmod(0o700)
    raw, spec = fixture_spec()
    calls = []
    def open_url(url, timeout):
        calls.append((url, timeout))
        return Response(raw if payload is None else payload)
    result = m._acquire(str(tmp_path), deadline, spec, opener or open_url,
                        clock, lambda _: SimpleNamespace(free=10**9))
    return result, calls


def test_one_pinned_acquisition_derives_members_without_execution(tmp_path):
    result, calls = run(tmp_path)
    assert len(calls) == 1 and calls[0][0] == m.URL
    assert result['executable_invoked'] is False
    assert set(result['member_sha256']) == {'runsc','gvisor-bin/invented'}
    assert (tmp_path / m.FILENAME).stat().st_mode & 0o777 == 0o600
    assert set(p.name for p in tmp_path.iterdir()) == {m.FILENAME}


def test_existing_path_never_repeats_network_request(tmp_path):
    (tmp_path / m.FILENAME).write_bytes(b'original')
    calls=[]
    with pytest.raises(FileExistsError): run(tmp_path, opener=lambda *a,**k:calls.append(a))
    assert calls == [] and (tmp_path / m.FILENAME).read_bytes() == b'original'


@pytest.mark.parametrize('payload', [b'wrong bytes', b'x'*1000])
def test_bad_hash_or_oversize_never_parses_or_deletes(tmp_path, payload, monkeypatch):
    calls=[]
    # Construct the fictional contract before replacing the parser.
    raw,spec=fixture_spec()
    monkeypatch.setattr(m.tarfile, 'open', lambda *a,**k:calls.append(a))
    tmp_path.chmod(0o700)
    with pytest.raises(m.ArchivePhaseRefused):
        m._acquire(str(tmp_path),240,spec,lambda *a,**k:Response(payload),lambda:0,
                   lambda _:SimpleNamespace(free=10**9))
    assert calls == [] and (tmp_path / m.FILENAME).exists()


def test_expired_before_effect(tmp_path):
    with pytest.raises(m.ArchivePhaseRefused): run(tmp_path,clock=lambda:240)
    assert not (tmp_path / m.FILENAME).exists()


def test_read_deadline_stops_before_write(tmp_path):
    now=[0]
    class Late(Response):
        def read(self, n): now[0]=241; return super().read(n)
    raw,_=fixture_spec()
    with pytest.raises(m.ArchivePhaseRefused):
        run(tmp_path,opener=lambda *a,**k:Late(raw),clock=lambda:now[0])
    assert (tmp_path / m.FILENAME).read_bytes() == b''


def test_permission_failure_retains_partial_file_without_retry(tmp_path,monkeypatch):
    calls=[]
    def denied(*a):calls.append(a);raise PermissionError('invented')
    monkeypatch.setattr(m.os,'write',denied)
    with pytest.raises(PermissionError):run(tmp_path)
    assert len(calls)==1 and (tmp_path/m.FILENAME).exists()


def test_short_writes_are_completed(tmp_path,monkeypatch):
    write=os.write
    monkeypatch.setattr(m.os,'write',lambda fd,raw:write(fd,raw[:3]))
    result,_=run(tmp_path)
    assert hashlib.sha256((tmp_path/m.FILENAME).read_bytes()).hexdigest()==result['archive_sha256']
