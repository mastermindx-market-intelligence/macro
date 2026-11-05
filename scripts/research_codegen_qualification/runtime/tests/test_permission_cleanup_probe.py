"""Root review probe: invented member bytes, denied fake write, no privileged effect."""
from pathlib import Path
import io
import sys
from types import SimpleNamespace
import pytest

import test_runsc_install as original
m = original.mod


def test_denied_bundle_write_does_not_apply_metadata_after_refusal(tmp_path, monkeypatch):
    fx = original.Fixture()
    try:
        engine = fx.engine()
        fake_tar = SimpleNamespace(extractfile=lambda _: io.BytesIO(original.MEMBER_PAYLOADS['runsc']))
        def denied_write(*_): raise PermissionError('injected write denial')
        monkeypatch.setattr(m.os, 'write', denied_write)
        with pytest.raises(PermissionError):
            engine._consume_member(fake_tar, object(), 'runsc', str(tmp_path))
        assert fx.chown_calls == [], 'metadata mutation attempted after write denial'
        assert engine.frozen
    finally: fx.close()
