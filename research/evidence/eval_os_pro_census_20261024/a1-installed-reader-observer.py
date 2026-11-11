"""One read-only A1 observation; execute via python -B on the installed host.

No application data, source, cache, service, or credential is written. The
existing execution boundary owns its child and enforces the existing limits.
Only fixed metadata and aggregate counts leave the process.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

ROOT = Path('/opt/macro')
QUALIFIED = '5aae3c5e97dcdcf85d0745062fe9424f1ed7c0c7'
SOURCE_PATHS = [
    'admin/intelligence_execution.py', 'admin/intelligence_os.py',
    'admin/evidence_status.py', 'admin/evidence_findings.py', 'admin/server.py',
    'engine/intelligence_registry.py', 'engine/output_health.py',
    'engine/qledger.py', 'engine/qledger_desk_adapter.py',
    'engine/qledger_evidence_clock.py', 'engine/qledger_store.py',
    'engine/qledger_store_protocol.py', 'engine/qledger_validity.py',
    'scripts/build_intelligence_registry.py', 'scripts/build_output_health.py',
    'scripts/grade_qledger.py', 'scripts/check_qledger_metric_validity.py',
    'scripts/check_synapse_reads.py',
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command(args):
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=8)
        return p.returncode, p.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return None, ''


def file_identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def bounded_source(path):
    limit = 2 * 1024 * 1024
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError('not_bounded_regular_file')
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or file_identity(opened) != file_identity(before):
            raise ValueError('source_changed_during_open')
        with os.fdopen(fd, 'rb') as stream:
            fd = -1
            data = stream.read(limit + 1)
            after_fd = os.fstat(stream.fileno())
        after_path = path.lstat()
        if len(data) > limit or file_identity(opened) != file_identity(after_fd) or file_identity(opened) != file_identity(after_path):
            raise ValueError('source_changed_during_read')
        return data
    finally:
        if fd >= 0:
            os.close(fd)


def identity():
    result = {'at': now(), 'files': {}, 'services': {}}
    rc, head = command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'])
    result['installed_head'] = head if rc == 0 and len(head) == 40 else None
    for rel in SOURCE_PATHS:
        path = ROOT / rel
        record = {'matches_qualified': False}
        try:
            data = bounded_source(path)
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            rc, expected = command(['git', '-C', str(ROOT), 'rev-parse', f'{QUALIFIED}:{rel}'])
            record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          git_blob=blob, qualified_blob=expected if rc == 0 else None,
                          matches_qualified=rc == 0 and blob == expected)
        except OSError:
            record['unavailable'] = 'file_unavailable'
        except ValueError as error:
            record['unavailable'] = str(error)
        result['files'][rel] = record
    for service in ['macro-api.service', 'admin.service']:
        rc, raw = command(['systemctl', 'show', service,
                           '--property=ActiveState,SubState,MainPID,ExecMainStartTimestamp,LoadState'])
        fields = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
        fields['command_ok'] = rc == 0
        pid = fields.get('MainPID', '')
        try:
            fields['process_cwd_matches'] = pid.isdigit() and os.readlink(f'/proc/{pid}/cwd') == str(ROOT)
        except OSError:
            fields['process_cwd_matches'] = False
        result['services'][service] = fields
    return result


OBSERVER = r'''
import collections, datetime, json, pathlib, resource, sys, time
root = pathlib.Path('/opt/macro')
sys.path.insert(0, str(root))
from admin import intelligence_execution
expected = (1024 * 1024 * 1024, 45.0, 16 * 1024 * 1024, 2.0)
actual = (intelligence_execution.ADDRESS_SPACE_BYTES, intelligence_execution.WALL_SECONDS,
          intelligence_execution.RESULT_BYTES, intelligence_execution.CLEANUP_SECONDS)
if actual != expected or pathlib.Path(intelligence_execution.__file__).resolve() != root / 'admin/intelligence_execution.py':
    print(json.dumps({'status': 'not_run', 'call_count': 0, 'reason': 'execution_boundary_identity_mismatch'}))
    raise SystemExit(0)
before = resource.getrusage(resource.RUSAGE_CHILDREN)
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
started = time.monotonic()
panel = intelligence_execution.response('panel', root=root, force=False)
elapsed = time.monotonic() - started
after = resource.getrusage(resource.RUSAGE_CHILDREN)
census = panel.get('census') or {}
engines = panel.get('engines') or []
generated = panel.get('generated') or {}
findings = panel.get('typed_findings') or {}
keys = ['engines', 'canonical_engines', 'noncanonical_output_groups', 'artifacts',
        'outputs_assessed', 'by_state', 'by_assessment_status', 'by_output_class',
        'by_evidence_status', 'by_authority', 'by_storage', 'by_dependency_bound']
selected_census = {key: census.get(key) for key in keys}
checks = {}
if panel.get('ok') is True:
    artifacts = census['artifacts']
    checks = {
        'engine_partition': census['engines'] == census['canonical_engines'] + census['noncanonical_output_groups'],
        'engine_rows_match': len(engines) == census['engines'],
        'engine_artifacts_match': sum(row.get('n_artifacts', 0) for row in engines) == artifacts,
        'assessment_partition': sum(census['by_assessment_status'].values()) == artifacts,
        'assessed_vs_blind': census['outputs_assessed'] == artifacts - census['by_assessment_status'].get('could_not_look', 0),
        'state_partition': sum(census['by_state'].values()) == artifacts,
        'class_partition': sum(census['by_output_class'].values()) == artifacts,
        'canonical_band_partition': sum(census['by_evidence_status'].values()) == census['canonical_engines'],
        'canonical_rows_match': sum(bool(row.get('canonical_t1')) for row in engines) == census['canonical_engines'],
        'trust_mtime_false': generated.get('trust_mtime') is False,
        'named_dependency_key_coherent': (generated.get('source_generation') or {}).get('read_status') == 'coherent',
    }
qualification_keys = {'receipt_status', 'current_source_qualification',
                      'all_inputs_qualification', 'named_generation_match',
                      'named_generation_check', 'qualified_scope', 'portability'}
qualification = {key: collections.Counter() for key in qualification_keys}
def aggregate(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in qualification_keys and isinstance(value, (str, bool)):
                text = str(value)
                if len(text) <= 80 and all(c.isalnum() or c == '_' for c in text):
                    qualification[key][text] += 1
            aggregate(value)
    elif isinstance(node, list):
        for value in node: aggregate(value)
aggregate(engines)
aggregate(findings)
numeric = findings.get('numeric_attribution') if isinstance(findings, dict) else None
typed = {
    'present': bool(findings),
    'status': findings.get('status') if isinstance(findings, dict) else None,
    'numeric_attribution_status': numeric.get('status') if isinstance(numeric, dict) else None,
}
out = {
    'status': 'completed', 'call_count': 1, 'started_at': started_at,
    'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'ok': panel.get('ok') is True, 'error_code': panel.get('error_code'),
    'wall_seconds': round(elapsed, 6),
    'resource': {
        'child_rusage_before_maxrss_kib': before.ru_maxrss,
        'child_rusage_maxrss_kib': after.ru_maxrss,
        'child_user_seconds': round(after.ru_utime - before.ru_utime, 6),
        'child_system_seconds': round(after.ru_stime - before.ru_stime, 6),
        'observer_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'semantics': 'Linux RUSAGE_CHILDREN high-water KiB; not simultaneous process-tree memory',
    },
    'safety_envelope': dict(zip(['address_space_bytes', 'wall_seconds', 'result_bytes', 'cleanup_seconds'], actual)),
    'census': selected_census,
    'generated': {key: generated.get(key) for key in ['observed_at', 'root_mode', 'compute_seconds', 'cache', 'trust_mtime', 'source_generation']},
    'checks': checks,
    'qualification_status_counts': {key: dict(value) for key, value in qualification.items() if value},
    'qualification_counter_unit': 'projection-field occurrences; not unique owner snapshots',
    'typed_findings': typed,
    'serialized_panel_bytes': len(json.dumps(panel, allow_nan=False).encode()),
    'execution_module_from_installed_root': True,
}
print(json.dumps(out, allow_nan=False))
'''


def main():
    result = {'schema': 'eval_os.a1_installed_reader_observation.v1',
              'qualified_source': QUALIFIED, 'started_at': now(),
              'call_count': 0, 'source_scope': '18 named reader and owner dependencies; not complete transitive import closure'}
    before = identity()
    result['before'] = before
    if not all(row.get('matches_qualified') is True for row in before['files'].values()):
        result.update(status='not_run', reason='installed_source_mismatch')
    elif not all(row.get('ActiveState') == 'active' and row.get('LoadState') == 'loaded'
                 and row.get('process_cwd_matches') is True for row in before['services'].values()):
        result.update(status='not_run', reason='runtime_identity_not_confirmed')
    else:
        result['attempted_calls_upper_bound'] = 1
        result['call_count'] = None
        try:
            p = subprocess.Popen([str(ROOT / '.venv/bin/python'), '-B', '-c', OBSERVER],
                                 cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
            stdout, _ = p.communicate(timeout=65)
            if p.returncode == 0:
                result['observation'] = json.loads(stdout)
                result['call_count'] = result['observation'].get('call_count')
                result['status'] = 'completed'
            else:
                result.update(status='observation_failed', observer_exit=p.returncode,
                              raw_stderr_withheld=True, retry=False)
        except subprocess.TimeoutExpired:
            # Preserve the observer that owns response() cleanup. Never kill it
            # or launch a replacement observation after this uncertain return.
            result.update(status='UNKNOWN_TIMEOUT', observer_pid=p.pid, retry=False)
        except (OSError, ValueError):
            result.update(status='observer_result_unavailable', retry=False)
        after = identity()
        result['after'] = after
        result['stable_named_source_files'] = before['files'] == after['files'] and all(row.get('matches_qualified') for row in after['files'].values())
        result['stable_observed_service_epoch'] = before['services'] == after['services'] and all(row.get('command_ok') for row in after['services'].values())
        result['stable_installed_head'] = before['installed_head'] is not None and before['installed_head'] == after['installed_head']
    result['finished_at'] = now()
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
