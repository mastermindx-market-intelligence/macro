"""Only invented fixture files; no Docker, sudo or host configuration."""
from pathlib import Path
import pytest
import test_runsc_install as original
m = original.mod

def test_frozen_receipt_performs_no_write():
    fx = original.Fixture()
    try:
        e = fx.engine(); e.freeze()
        p = str(Path(fx.scratch) / 'frozen-receipt.json')
        with pytest.raises(m.InstallError): e._write_receipt_file(p, {'state':'denied'})
        assert not Path(p).exists()
    finally: fx.close()

def test_expired_total_receipt_performs_no_write():
    fx = original.Fixture()
    try:
        e = fx.engine(); fx.clock.bump(1000)
        p = str(Path(fx.scratch) / 'expired-receipt.json')
        with pytest.raises(m.InstallError): e._write_receipt_file(p, {'state':'expired'})
        assert not Path(p).exists()
    finally: fx.close()

def test_receipt_write_denial_freezes_no_metadata_continuation(monkeypatch):
    fx = original.Fixture()
    try:
        e = fx.engine(); calls=[]
        monkeypatch.setattr(m.os, 'write', lambda *_: (_ for _ in ()).throw(PermissionError('fixture')))
        monkeypatch.setattr(e, 'chown_fn', lambda *_: calls.append('chown'))
        p = str(Path(fx.scratch) / 'denied-receipt.json')
        with pytest.raises((m.InstallError, PermissionError)): e._write_receipt_file(p, {'state':'fixture'})
        assert e.frozen
        assert calls == []
    finally: fx.close()
