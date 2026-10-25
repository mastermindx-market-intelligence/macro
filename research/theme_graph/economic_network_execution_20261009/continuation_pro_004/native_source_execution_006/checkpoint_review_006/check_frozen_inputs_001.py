from pathlib import Path
import hashlib
import json

ROOT = Path('/workspace/scratch/9fd3d58c239a')
LANES = [
    'native_massive_us_feasibility_v1', 'native_us_slice_005',
    'native_mu_capture_principal_v1', 'native_mu_capture_review_v1',
    'native_massive_env_route_v1', 'native_mu_capture_principal_v2',
    'native_mu_owner_bootstrap_review_v1', 'pro003_publication_recovery_v1',
]
OUT = ROOT / 'lanes/pro004_native_source_checkpoint_review_006'

def identity(p):
    b = p.read_bytes()
    return {'path': p.relative_to(ROOT).as_posix(), 'byte_length': len(b),
            'sha256': hashlib.sha256(b).hexdigest()}

members = []
manifests = []
for name in LANES:
    lane = ROOT / 'lanes' / name
    for p in sorted(lane.rglob('*')):
        assert not p.is_symlink(), str(p)
        if p.is_file():
            members.append(identity(p))
    for p in sorted(lane.rglob('*MANIFEST*.json')):
        d = json.loads(p.read_text())
        checked = []
        for r in d.get('files', []):
            q = p.parent / r['path']
            actual = identity(q)
            assert actual['byte_length'] == r.get('byte_length', r.get('bytes')), str(q)
            assert actual['sha256'] == r['sha256'], str(q)
            checked.append(actual)
        manifests.append({'manifest': identity(p), 'declared_files_verified': len(checked)})

assert len(members) == 87
v3 = ROOT / 'lanes/wp02_ci_applied_review_v1/revision_3'
expected = {
    'PREPARATION_SCOPE_V3.json': '2651f18e0c1d86f885850179a4a82b05635095b58c20923da1c120176d012ebe',
    'verify_combined_candidate_ci_v3.py': '967c63de9e7270860a024e3168d8d0249a9bb0189d52f552aaa6e40132375df2',
}
for name, sha in expected.items():
    assert identity(v3 / name)['sha256'] == sha

drafts = [identity(ROOT / 'lanes/pro004_native_source_checkpoint_006' / name)
          for name in ['README.md', 'EXECUTION_STATUS_20261009_006.md', 'SOURCE_EVIDENCE_README.md']]
receipt = {
    'schema': 'economic_network.checkpoint_006_frozen_input_review/v1',
    'status': 'PASS_INPUT_IDENTITIES_ARCHIVE_NOT_YET_REVIEWED',
    'source_members': members,
    'source_member_count': len(members),
    'source_member_bytes': sum(r['byte_length'] for r in members),
    'lane_manifests_checked_with_original_scope': manifests,
    'drafts_reviewed': drafts,
    'v3_preparation_unchanged': expected,
    'native_provider_app_git_operations': 0,
    'note': 'Local hashing/JSON parsing only. No archived native action or application verifier executed.',
}
with (OUT / 'INPUT_VERIFICATION_001.json').open('x') as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write('\n')
print(json.dumps({'status': receipt['status'], 'members': len(members),
                  'bytes': receipt['source_member_bytes'], 'lane_manifests': len(manifests),
                  'drafts': drafts, 'v3_unchanged': True}, sort_keys=True))
