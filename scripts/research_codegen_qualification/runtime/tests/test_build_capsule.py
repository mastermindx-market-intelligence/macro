import hashlib
import json
import os
from pathlib import Path
import pytest
import build_capsule as m


def test_capsule_reproduces_reviewed_bytes_without_importing_probe(monkeypatch):
    import sys
    assert 'fixed_smoke_probe' not in sys.modules
    blob=m.build_capsule(os.environ.get('RF_QUALIFICATION_TRANSPORT_SOURCE'))
    manifest=json.loads((m.HERE/'source_manifest.json').read_bytes())
    assert hashlib.sha256(blob).hexdigest()==manifest['physical_capsule_sha256']
    assert 'fixed_smoke_probe' not in sys.modules
    assert set(json.loads(blob)['files'])==set(m.PAYLOAD_NAMES)


def test_unqualified_transport_cannot_enter_capsule(tmp_path):
    path=tmp_path/'transport.py';path.write_bytes(b'raise RuntimeError("must never execute")')
    with pytest.raises(ValueError,match='qualified_source_pin_mismatch:transport.py'):
        m.build_capsule(path)
