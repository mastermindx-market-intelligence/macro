"""Assemble the pinned trusted canary sources as data; never execute a probe."""
import base64
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAYLOAD_NAMES = (
    'runsc_install.py', 'qualification_smoke.py', 'qualification_runsc_smoke.py',
    'fixed_smoke_probe.py', 'transport.py', 'qualification_manifest.py',
    'cli29_anonymous_config.py', 'phase_budget.py', 'pinned_archive_phase.py',
    'image_preparation_gate.py', 'fixed_image_phase.py', 'fixed_canary.py',
)


def build_capsule(transport_source=None):
    """Explicit dependency seam still requires the exact accepted transport pin.

    This creates bytes only. It never imports the executable probe, writes files,
    invokes a subprocess, chooses a host, commissions effects or issues admission.
    """
    manifest = json.loads((HERE / 'source_manifest.json').read_bytes())
    transport = Path(transport_source) if transport_source is not None else REPO / manifest['transport_source']
    rows = {}
    for name in PAYLOAD_NAMES:
        data = (transport if name == 'transport.py' else HERE / name).read_bytes()
        expected = (manifest['transport_sha256'] if name == 'transport.py'
                    else manifest['source_sha256'][name])
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('qualified_source_pin_mismatch:' + name)
        compile(data, name, 'exec')  # Syntax only, including the executable probe.
        rows[name] = {'size': len(data), 'sha256': expected,
                      'base64': base64.b64encode(data).decode('ascii')}
    capsule = {'schema': 'rf.fixed_canary_capsule.v2',
               'root': manifest['original_root'], 'files': rows}
    result = json.dumps(capsule, sort_keys=True, separators=(',', ':')).encode('ascii')
    if hashlib.sha256(result).hexdigest() != manifest['physical_capsule_sha256']:
        raise ValueError('qualified_capsule_pin_mismatch')
    return result
