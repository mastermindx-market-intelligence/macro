from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile

ROOT = Path('/workspace/scratch/9fd3d58c239a')
REVIEW = ROOT / 'lanes/pro004_native_source_checkpoint_review_006'
AUTHOR = ROOT / 'lanes/pro004_native_source_checkpoint_006'
DELIVERY = ROOT / 'lanes/pro004_native_source_delivery_006'
PREFIX = 'research/theme_graph/economic_network_execution_20261009/continuation_pro_004'
BASE = DELIVERY / PREFIX
PACK = BASE / 'native_source_execution_006'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def identity(p):
    b = p.read_bytes()
    return {'path': p.relative_to(ROOT).as_posix(), 'byte_length': len(b), 'sha256': sha(b)}

m_path = PACK / 'ARCHIVE_MANIFEST.json'
assert sha(m_path.read_bytes()) == 'b997e5fb2d23ab18ae29e4700a6161b7fae2357f48b91fa21c6116120a03c7d4'
m = json.loads(m_path.read_text())
a_path = PACK / m['archive']['path']
assert len(a_path.read_bytes()) == 333956 == m['archive']['byte_length']
assert sha(a_path.read_bytes()) == m['archive']['sha256'] == '631890ba95d0fbaffe1f85d9e9c60edc9103be9b3b22d4f28bc3ab448e34d015'
declared = {r['path']: r for r in m['files']}
assert len(declared) == len(m['files']) == 87
original_inventory = json.loads((REVIEW / 'INPUT_VERIFICATION_001.json').read_text())
assert set(declared) == {r['path'] for r in original_inventory['source_members']}
actual_members = {}
with tarfile.open(a_path, 'r:gz') as tf:
    for member in tf:
        p = PurePosixPath(member.name)
        assert member.isfile() and not p.is_absolute() and '..' not in p.parts
        assert member.name not in actual_members and member.name in declared
        assert member.mode == 0o644
        body = tf.extractfile(member).read()
        r = declared[member.name]
        assert len(body) == member.size == r['byte_length']
        assert sha(body) == r['sha256']
        assert body == (ROOT / member.name).read_bytes()
        actual_members[member.name] = {'byte_length': len(body), 'sha256': sha(body)}
assert set(actual_members) == set(declared)
assert sum(r['byte_length'] for r in actual_members.values()) == 1309176 == m['archive']['member_bytes']
assert len(m['lanes']) == 8
for lane in m['lanes']:
    rows = [r for p, r in actual_members.items() if p.startswith('lanes/' + lane['lane'] + '/')]
    assert len(rows) == lane['file_count']
    assert sum(r['byte_length'] for r in rows) == lane['member_bytes']

copies = []
for row in m['browsable_exact_copies']:
    b = (PACK / row['path']).read_bytes()
    assert len(b) == row['byte_length'] and sha(b) == row['sha256']
    assert b == (ROOT / row['original_archive_member']).read_bytes()
    copies.append(row)
assert len(copies) == 12

draft = json.loads((AUTHOR / 'DRAFT_DELIVERY_MANIFEST_006.json').read_text())
delivery_rows = []
actual_files = [p for p in sorted(DELIVERY.rglob('*')) if p.is_file()]
assert len(actual_files) == len(draft['files']) == 18
assert {p.relative_to(DELIVERY).as_posix() for p in actual_files} == {r['path'] for r in draft['files']}
correction = None
for row in draft['files']:
    p = DELIVERY / row['path']
    b = p.read_bytes()
    if p.name == 'EXECUTION_STATUS_20261009_006.md':
        old = b'apply the already reviewed kernel job/inventory insertion exactly once'
        new = b'preserve the already-applied kernel job/inventory insertion exactly once'
        assert b.count(new) == 1 and old not in b
        inverted = b.replace(new, old)
        assert len(inverted) == row['byte_length'] and sha(inverted) == row['sha256']
        assert b == (AUTHOR / p.name).read_bytes()
        correction = {'before': row, 'after': identity(p), 'exact_single_replacement_verified': True}
    else:
        assert len(b) == row['byte_length'] and sha(b) == row['sha256']
    delivery_rows.append(identity(p))
assert correction is not None
assert (BASE / 'README.md').read_bytes() == (AUTHOR / 'README.md').read_bytes()
assert (PACK / 'README.md').read_bytes() == (AUTHOR / 'SOURCE_EVIDENCE_README.md').read_bytes()

v3 = original_inventory['v3_preparation_unchanged']
for name, h in v3.items():
    assert sha((ROOT / 'lanes/wp02_ci_applied_review_v1/revision_3' / name).read_bytes()) == h
receipt = {
    'schema': 'economic_network.checkpoint_006_archive_independent_review/v1',
    'verdict': 'PASS_ARCHIVE_AND_DELIVERY_IDENTITIES',
    'archive': identity(a_path), 'archive_manifest': identity(m_path),
    'original_member_count': 87, 'original_member_bytes': 1309176,
    'lane_count': 8, 'archive_member_equals_current_original_bytes': True,
    'regular_safe_unique_members': True, 'browsable_copies_checked': copies,
    'delivery_files': delivery_rows, 'delivery_file_count': 18,
    'one_status_wording_correction': correction,
    'draft_transport_index_precedes_correction': True,
    'principal_final_transport_manifest_pending': True,
    'v3_preparation_unchanged': v3,
    'native_provider_app_git_operations': 0,
    'archived_native_or_application_scripts_executed': 0,
    'scope': 'Scratch-only byte hashes, JSON parsing, in-memory tar reads, exact inverse wording delta. No extraction, source execution or store reads.'
}
with (REVIEW / 'ARCHIVE_VERIFICATION_002.json').open('x') as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write('\n')
print(json.dumps({'verdict': receipt['verdict'], 'members': 87, 'member_bytes': 1309176,
                  'lanes': 8, 'browsable_copies': len(copies), 'delivery_files': 18,
                  'status_correction_exact': True, 'v3_unchanged': True}, sort_keys=True))
