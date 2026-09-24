"""Offline characterization of the pinned GMI rights-reader cache.

This is research, not a repair or production-security test. All policy files
are synthetic and temporary. No network, repository, credential, or cloud write.
The source file must match the exact inspected Git blob before it is imported.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

PIN = '8db6896dab2199a4b7fc61a005c225380cac7cd6'
BLOB = '63ba2b60e9be6615208fab5b53b1fbcb44f4f433'

def run(source: Path) -> dict:
    body = source.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
    if blob != BLOB:
        raise ValueError('source_blob_mismatch: refusing import')
    spec = importlib.util.spec_from_file_location('healthcare_r8_pinned_rights', source)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load exact source')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = []
    def policy(path: Path, rights: str) -> None:
        path.write_text('families:\n  synthetic_reviewed_family:\n'
                        f'    rights_class: {rights}\n    auth_class: house\n', encoding='utf-8')
    def record(cid: str, kind: str, observed: bool, expected: bool, description: str) -> None:
        if observed is not expected:
            raise AssertionError(f'{cid}: characterization changed: {observed!r} != {expected!r}')
        cases.append({'id':cid, 'kind':kind, 'observed_allowed':observed,
                      'historical_expected_allowed':expected, 'reproduced':True,
                      'description':description})
    with tempfile.TemporaryDirectory(prefix='healthcare-r8-') as tmp:
        root = Path(tmp)
        a = root / 'policy.yml'
        policy(a, 'direct_display_ok')
        record('R8-P01','control',module.emission_allowed('synthetic_reviewed_family',path=a),True,
               'Initially admitted synthetic policy permits emission.')
        policy(a, 'internal_only')
        record('R8-P02','finding',module.emission_allowed('synthetic_reviewed_family',path=a),True,
               'Same-path policy revocation remains allowed in the already-warm module.')
        module._load.cache_clear()
        record('R8-P03','control',module.emission_allowed('synthetic_reviewed_family',path=a),False,
               'Explicit invalidation observes revocation and refuses.')
        b = root / 'initially-absent.yml'
        if module.emission_allowed('synthetic_reviewed_family',path=b):
            raise AssertionError('initially missing policy must refuse')
        policy(b, 'direct_display_ok')
        record('R8-P04','finding',module.emission_allowed('synthetic_reviewed_family',path=b),False,
               'Same-path policy arrival remains refused after an earlier missing-file read.')
        module._load.cache_clear()
        record('R8-P05','control',module.emission_allowed('synthetic_reviewed_family',path=b),True,
               'Explicit invalidation observes the new reviewed policy.')
        record('R8-P06','control',module.emission_allowed('unknown_family',path=b),False,
               'Unknown family still refuses.')
        c = root / 'invalid.yml'; policy(c,'not_a_rights_class')
        record('R8-P07','control',module.emission_allowed('synthetic_reviewed_family',path=c),False,
               'Unknown policy class still refuses.')
        d = root / 'immutable-policy-v2.yml'; policy(d,'internal_only')
        record('R8-P08','control',module.emission_allowed('synthetic_reviewed_family',path=d),False,
               'A separately read policy revision path observes refusal without reusing old path cache.')
    module._load.cache_clear()
    return {'artifact_kind':'offline_pinned_source_characterization','source_commit':PIN,
            'source_path':'engine/theme_graph/rights.py','source_blob':blob,
            'source_sha256':hashlib.sha256(body).hexdigest(),'findings_reproduced':2,
            'controls_reproduced':6,'cases':cases,'network_calls':0,
            'production_writes':0,'product_repaired':False,'live_incident_observed':False,
            'future_acceptance_cases_executed':0}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).parent/'pinned/engine/theme_graph/rights.py')
    args=parser.parse_args()
    print(json.dumps(run(args.source),ensure_ascii=False,indent=2))
