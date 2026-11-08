"""Read-only named-provenance comparison for one existing A1 owner receipt.

No grading, refresh, publication, prices, claims parsing, service changes or
authentication. Only match booleans and changed metadata categories are emitted.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import sys
import time

ROOT = Path('/opt/macro')
EXPECTED = {
    'scripts/grade_qledger.py': '56d49a99be7105c29f80795c2c2af8d89605f660f6280042fdb28072731155b2',
    'engine/qledger.py': '6473c710806b26bc5ee3da3ad781d07b3ca02f208f9789a723186216819c1e00',
    'engine/qledger_store.py': '3a1d30cbd20a09bc428d069fcd9548f17ff94763ffcfdd83041d6c11edd6e3db',
    'engine/qledger_evidence_clock.py': 'f553456b749bf9d98b01954e1e32ec61f1a0c436ae4ed20303323db2319af943',
    'admin/intelligence_os.py': '45eceabbee1d04ecf820b1d2ca5b24a5c0b417ec27a6171ed5939f7010e59873',
}


def identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def bounded(path, limit):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError('not_bounded_regular_file')
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise ValueError('changed_during_open')
        with os.fdopen(fd, 'rb') as stream:
            fd = -1
            data = stream.read(limit + 1)
            after_fd = os.fstat(stream.fileno())
        if len(data) > limit or identity(opened) != identity(after_fd) or identity(opened) != identity(path.lstat()):
            raise ValueError('changed_during_read')
        return data
    finally:
        if fd >= 0:
            os.close(fd)


def source_matches():
    return {rel: hashlib.sha256(bounded(ROOT / rel, 2 * 1024 * 1024)).hexdigest() == expected
            for rel, expected in EXPECTED.items()}


def small_file_match(old, current):
    if not isinstance(old, dict) or not isinstance(current, dict):
        return {'shape_match': False}
    return {'present_match': old.get('present') == current.get('present'),
            'sha256_match': old.get('sha256') == current.get('sha256'),
            'host_metadata_match': old.get('host_local_stat') == current.get('host_local_stat')}


def metadata_diff(old, current):
    names = ['device', 'inode', 'bytes', 'mtime_ns', 'ctime_ns']
    if not isinstance(old, list) or not isinstance(current, list) or len(old) != 5 or len(current) != 5:
        return ['presence_or_shape'] if old != current else []
    return [name for name, a, b in zip(names, old, current) if a != b]


class ObservationBudgetExpired(BaseException):
    pass


def timeout(_signum, _frame):
    raise ObservationBudgetExpired('named_metadata_budget')


def normalized_recorded_at(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.isoformat() if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except ValueError:
        return None


def main():
    result = {'schema': 'eval_os.a1_named_generation_diff.v1',
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'qualified_source': '5aae3c5e97dcdcf85d0745062fe9424f1ed7c0c7',
              'owner_artifact': 'site/qledger/track_record.json',
              'panel_calls': 0, 'metadata_generation_calls': 0, 'retry': False}
    started = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(15)
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = 1024 * 1024 * 1024 if hard == resource.RLIM_INFINITY else min(hard, 1024 * 1024 * 1024)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        os.environ[key] = '1'
    try:
        before_sources = source_matches()
        result['named_source_matches_before'] = before_sources
        if not all(before_sources.values()):
            raise ValueError('source_mismatch')
        sys.path.insert(0, str(ROOT))
        from scripts import grade_qledger as grade
        from admin.intelligence_os import _valid_recorded_readiness
        path = ROOT / result['owner_artifact']
        before_identity = identity(path.lstat())
        owner_bytes = bounded(path, 16 * 1024 * 1024)
        document = json.loads(owner_bytes)
        payload = document.get('promotion_readiness')
        receipt = document.get('promotion_readiness_receipt')
        if not isinstance(receipt, dict) or not _valid_recorded_readiness(payload):
            raise ValueError('unqualified_owner_payload')
        recorded = receipt.get('source_generation')
        families = sorted(key for key in payload if not key.startswith('_'))
        if len(families) > 32 or any(not re.fullmatch(r'[a-z0-9_]{1,64}', family) for family in families):
            raise ValueError('family_bound')
        valid = (isinstance(recorded, dict) and receipt.get('schema') == grade.READINESS_RECEIPT_SCHEMA
                 and receipt.get('producer') == grade.READINESS_RECEIPT_PRODUCER
                 and receipt.get('payload_digest') == grade.readiness_payload_digest(payload)
                 and recorded.get('families') == families
                 and recorded.get('qualified_scope') == 'named_ledger_metadata_config_clocks_owner_code'
                 and recorded.get('portability') == 'host_local_metadata'
                 and recorded.get('all_inputs_qualification') == 'unavailable')
        if not valid:
            raise ValueError('unqualified_recorded_provenance')
        evaluation_date = recorded['evaluation_date']
        if datetime.datetime.strptime(evaluation_date, '%Y-%m-%d').strftime('%Y-%m-%d') != evaluation_date:
            raise ValueError('evaluation_date')
        result['metadata_generation_calls'] += 1
        current = grade.readiness_source_generation(ROOT, families, evaluation_date)
        result['metadata_generation_calls'] += 1
        after = grade.readiness_source_generation(ROOT, families, evaluation_date)
        keys = ['portability', 'host_scope_digest', 'selected_claims', 'grades', 'qual_ladder',
                'control_policy_digest', 'clocks', 'owner_code', 'families', 'evaluation_date',
                'duel_baseline_digest', 'qualified_scope', 'all_inputs_qualification', 'excluded_scope']
        owner_digest = hashlib.sha256(owner_bytes).hexdigest()
        after_owner_digest = hashlib.sha256(bounded(path, 16 * 1024 * 1024)).hexdigest()
        stable = current == after and before_identity == identity(path.lstat()) and owner_digest == after_owner_digest
        result.update(status='completed' if stable else 'changed_during_observation', recorded_provenance_valid=True,
                      recorded_at=normalized_recorded_at(document.get('promotion_readiness_at')), evaluation_date=evaluation_date,
                      family_count=len(families), named_generation_match=recorded == current,
                      current_generation_stable=current == after,
                      owner_artifact_stable=before_identity == identity(path.lstat()),
                      owner_content_digest=owner_digest,
                      owner_content_stable=owner_digest == after_owner_digest,
                      recorded_generation_digest=grade.readiness_payload_digest(recorded),
                      current_generation_digest=grade.readiness_payload_digest(current),
                      missing_recorded_keys=[key for key in keys if key not in recorded],
                      unexpected_recorded_key_count=len(set(recorded) - set(keys)),
                      component_match={key: recorded.get(key) == current.get(key) for key in keys},
                      selected_claims_metadata_differences=metadata_diff(recorded.get('selected_claims', {}).get('identity'), current['selected_claims'].get('identity')),
                      grades_metadata_differences=metadata_diff(recorded.get('grades'), current.get('grades')),
                      qual_ladder=small_file_match(recorded.get('qual_ladder'), current.get('qual_ladder')),
                      owner_code={key: small_file_match(recorded.get('owner_code', {}).get(key), value) for key, value in current['owner_code'].items()},
                      clocks={family: {kind: small_file_match(recorded.get('clocks', {}).get(family, {}).get(kind), value) for kind, value in row.items()} for family, row in current['clocks'].items()},
                      current_source_qualification='unavailable', all_inputs_qualification='unavailable')
        result['named_source_matches_after'] = source_matches()
        result['named_source_stable'] = before_sources == result['named_source_matches_after'] and all(result['named_source_matches_after'].values())
        if not result['named_source_stable']:
            result['status'] = 'changed_during_observation'
    except (OSError, ValueError, TypeError, KeyError, AttributeError, MemoryError, ObservationBudgetExpired) as error:
        result.update(status='unavailable', error_type=type(error).__name__)
    finally:
        signal.alarm(0)
    result['wall_seconds'] = round(time.monotonic() - started, 6)
    result['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['limits'] = ['One owner receipt, not four unique snapshots.',
                        'Named metadata comparison only; does not establish causes or current/all-input freshness.',
                        'No grading, price load, readiness publication, panel replay, native activation or service change.',
                        'Named source qualification is not a complete loaded-byte attestation.']
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
