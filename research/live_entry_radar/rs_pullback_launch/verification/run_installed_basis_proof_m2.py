#!/usr/bin/env python3
"""Verify both positive M2 lineages, then make one reviewed installed-v2 proof call.

Preparation is not execution authority. Root must review these exact bytes and
separately authorize later M2 execution. Only unique private receipts are written;
there is no fetch, repository mutation, retry, deployment or provider acquisition.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time
import uuid

REPOS = {
    'macro': Path('/Users/chriswong/Documents/GitHub/macro'),
    'terminal': Path('/Users/chriswong/Documents/GitHub/mastermind-terminal'),
}
ACCEPTED = {
    'macro': '14bcb0989399ad138d82f5f72108cdd74ea0a391',
    'terminal': '642fa4cd3d0340ad90952588ac48ca2d4f3e0d8b',
}
RELEASES = {
    'macro': '67c1d8155d9194825f6cb301967d6b1c1f91b433',
    'terminal': 'e963eefb3ac1984008caae922d6f43bfafa9d827',
}
TERMINAL_RELEASE_PARENT = '2cb3e1648332953ddc4e4d023ba419fee462440c'
TERMINAL_RELEASE_TREE = 'f88ffbcc7f11cdc3947ea5ee5544e497fda14474'
# Exact prepared bytes; this binding does not assert independent acceptance.
REMOTE_SCRIPT_SHA256 = 'b1881376715132785dbbe21e1f0f12bdb4fa3dabe03d88970f0da4fd8c682227'
REMOTE_SCRIPT_BYTES = 13581
MAX_SCRIPT_BYTES = 64 * 1024
MAX_RECEIPT_BYTES = 512 * 1024
SSH_TIMEOUT_SECONDS = 120
SSH_STDOUT_BYTES = 256 * 1024
SSH_STDERR_BYTES = 64 * 1024
GIT_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'GIT_OPTIONAL_LOCKS': '0',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}


class GateFailure(RuntimeError):
    pass

def require(condition, name):
    if not condition:
        raise GateFailure(name)

def digest(body):
    return hashlib.sha256(body).hexdigest()

def git_blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode('ascii') + b'\0' + body).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')

def write_once(path, body):
    require(len(body) <= MAX_RECEIPT_BYTES, 'receipt_capacity')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {'path': str(path), 'bytes': len(body), 'sha256': digest(body)}

def bounded_command(argv, *, input_bytes=None, timeout=30, stdout_limit=65536,
                    stderr_limit=65536, env=None):
    """One process, bounded pipes, no retry; preserve prefixes on cap/timeout.

    A terminated local SSH process does not establish remote cancellation. The
    receipt explicitly leaves the remote outcome ambiguous in that case.
    """
    started_ns = time.time_ns()
    start = time.monotonic()
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    observed = {'stdout': 0, 'stderr': 0}
    limits = {'stdout': stdout_limit, 'stderr': stderr_limit}
    sent = 0
    stopped = None
    stop_at = None
    forced_pipe_close = False
    proc = None
    spawn_error = None
    execution_error = None
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE if input_bytes is not None else None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    except OSError as exc:
        spawn_error = type(exc).__name__
    if proc is not None:
        selector = selectors.DefaultSelector()
        for name, stream in [('stdout', proc.stdout), ('stderr', proc.stderr)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if input_bytes is not None:
            os.set_blocking(proc.stdin.fileno(), False)
            if input_bytes:
                selector.register(proc.stdin, selectors.EVENT_WRITE, 'stdin')
            else:
                proc.stdin.close()
        try:
            while selector.get_map() or proc.poll() is None:
                now = time.monotonic()
                if stopped is None and now - start >= timeout:
                    stopped, stop_at = 'TIMEOUT', now
                if stopped is not None:
                    if proc.poll() is None:
                        try:
                            proc.kill() if now - stop_at >= 2 else proc.terminate()
                        except ProcessLookupError:
                            pass
                    if now - stop_at >= 5:
                        forced_pipe_close = bool(selector.get_map())
                        break
                for key, _events in selector.select(0.1):
                    stream, name = key.fileobj, key.data
                    if name == 'stdin':
                        if stopped is not None:
                            selector.unregister(stream)
                            stream.close()
                            continue
                        try:
                            count = os.write(stream.fileno(), input_bytes[sent:sent + 65536])
                            sent += count
                        except BrokenPipeError:
                            selector.unregister(stream)
                            stream.close()
                            continue
                        except BlockingIOError:
                            continue
                        if sent == len(input_bytes):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    try:
                        chunk = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    observed[name] += len(chunk)
                    room = max(0, limits[name] - len(output[name]))
                    output[name].extend(chunk[:room])
                    if len(chunk) > room and stopped is None:
                        stopped, stop_at = 'OUTPUT_CAPACITY', time.monotonic()
        except Exception as exc:
            execution_error = type(exc).__name__
        finally:
            for key in list(selector.get_map().values()):
                selector.unregister(key.fileobj)
                key.fileobj.close()
            selector.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
    return {'argv': list(argv), 'started_utc_ns': str(started_ns),
            'completed_utc_ns': str(time.time_ns()), 'returncode': proc.returncode if proc else None,
            'spawn_error_type': spawn_error, 'stop_reason': stopped,
            'execution_error_type': execution_error,
            'stdin_bytes_sent': sent, 'stdout': bytes(output['stdout']), 'stderr': bytes(output['stderr']),
            'observed_pipe_bytes': observed, 'forced_pipe_close': forced_pipe_close,
            'raw_output_complete': stopped is None and not forced_pipe_close and spawn_error is None and execution_error is None}

def command_summary(result):
    return {k: v for k, v in result.items() if k not in {'stdout', 'stderr'}} | {
        'stdout_bytes': len(result['stdout']), 'stdout_sha256': digest(result['stdout']),
        'stderr_bytes': len(result['stderr']), 'stderr_sha256': digest(result['stderr'])}

def git_call(repo, log, *args, input_bytes=None, stdout_limit=65536, allowed_codes=(0,)):
    argv = ['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'log.showSignature=false',
            '-c', 'protocol.allow=never', '-C', str(REPOS[repo]), *args]
    result = bounded_command(argv, input_bytes=input_bytes, timeout=30,
                             stdout_limit=stdout_limit, stderr_limit=16384, env=GIT_ENV)
    log.append(command_summary(result))
    require(result['raw_output_complete'] and result['returncode'] in allowed_codes,
            'git_read_unavailable_' + repo + '_' + args[0])
    return result


def read_script(path):
    require(not path.is_symlink(), 'remote_script_symlink')
    before_ns = time.time_ns()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        body = stream.read(MAX_SCRIPT_BYTES + 1)
        after = os.fstat(stream.fileno())
    after_ns = time.time_ns()
    require(stat.S_ISREG(before.st_mode) and before.st_size == len(body) <= MAX_SCRIPT_BYTES,
            'remote_script_size_or_type')
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'remote_script_changed_during_read')
    require(len(body) == REMOTE_SCRIPT_BYTES and digest(body) == REMOTE_SCRIPT_SHA256, 'reviewed_remote_script_digest')
    constants = {}
    for node in ast.parse(body).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'EXPECTED', 'MACRO_MERGE', 'TERMINAL_MERGE'}:
                require(name not in constants, 'duplicate_remote_constant')
                constants[name] = ast.literal_eval(node.value)
    require(set(constants) == {'EXPECTED', 'MACRO_MERGE', 'TERMINAL_MERGE'}
            and constants['MACRO_MERGE'] == RELEASES['macro']
            and constants['TERMINAL_MERGE'] == RELEASES['terminal']
            and type(constants['EXPECTED']) is dict and len(constants['EXPECTED']) == 11,
            'reviewed_remote_source_closure')
    grouped = {'macro': {}, 'terminal': {}}
    for absolute, expected_sha in constants['EXPECTED'].items():
        require(type(absolute) is str and type(expected_sha) is str
                and re.fullmatch('[a-f0-9]{64}', expected_sha) is not None, 'remote_source_binding_shape')
        matches = [name for name in REPOS if absolute.startswith('/opt/' + name + '/')]
        require(len(matches) == 1, 'remote_source_owner')
        owner = matches[0]
        relative = absolute[len('/opt/' + owner + '/'):]
        require(relative and str(Path(relative)) == relative and '..' not in Path(relative).parts,
                'remote_source_path')
        grouped[owner][relative] = expected_sha
    require(len(grouped['macro']) == 9 and len(grouped['terminal']) == 2, 'remote_owner_source_counts')
    return body, constants, grouped, {'path': str(path), 'bytes': len(body), 'sha256': digest(body),
                                    'read_started_utc_ns': str(before_ns), 'read_completed_utc_ns': str(after_ns)}


def tree_map(repo, log, ref, paths):
    raw = git_call(repo, log, 'ls-tree', '-rz', ref, '--', *sorted(paths))['stdout']
    result = {}
    for item in raw.split(b'\0'):
        if not item:
            continue
        header, path = item.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        name = path.decode('utf-8')
        require(name not in result and mode in {'100644', '100755'} and kind == 'blob', 'source_tree_entry')
        result[name] = oid
    require(set(result) == set(paths), 'source_tree_complete')
    return result

def blob_batch(repo, log, oids):
    ordered = sorted(set(oids))
    raw = git_call(repo, log, 'cat-file', '--batch', input_bytes=('\n'.join(ordered) + '\n').encode('ascii'),
                   stdout_limit=2 * 1024 * 1024)['stdout']
    result, cursor = {}, 0
    for expected in ordered:
        end = raw.find(b'\n', cursor)
        require(end >= cursor, 'git_batch_header')
        fields = raw[cursor:end].decode('ascii').split()
        require(len(fields) == 3 and fields[0] == expected and fields[1] == 'blob' and fields[2].isdigit(),
                'git_batch_blob_type')
        count = int(fields[2])
        require(count <= 1024 * 1024, 'git_blob_capacity')
        start = end + 1
        body = raw[start:start + count]
        require(len(body) == count and raw[start + count:start + count + 1] == b'\n'
                and git_blob(body) == expected, 'git_batch_exact_object')
        result[expected] = body
        cursor = start + count + 1
    require(cursor == len(raw), 'git_batch_no_extra_output')
    return result

def preflight(expected_heads, grouped, record):
    for owner in ('macro', 'terminal'):
        state = {'repository': str(REPOS[owner]), 'accepted_candidate': ACCEPTED[owner],
                 'merged_release': RELEASES[owner], 'expected_installed_head': expected_heads[owner],
                 'positive_release_ancestry': False, 'git_commands': []}
        record['repositories'][owner] = state
        log = state['git_commands']
        shallow = git_call(owner, log, 'rev-parse', '--is-shallow-repository')['stdout'].strip()
        require(shallow in (b'true', b'false'), 'local_shallow_state_' + owner)
        state['local_repository_shallow'] = shallow == b'true'
        release = git_call(owner, log, 'show', '-s', '--format=%H%n%P%n%T', RELEASES[owner])['stdout'].decode('ascii').splitlines()
        require(len(release) == 3 and release[0] == RELEASES[owner]
                and re.fullmatch('[a-f0-9]{40}', release[2]) is not None, 'actual_release_identity_' + owner)
        if owner == 'terminal':
            require(release == [RELEASES[owner], TERMINAL_RELEASE_PARENT, TERMINAL_RELEASE_TREE],
                    'actual_terminal_release_identity')
        state['merged_release_identity'] = {'commit': release[0], 'parents': release[1].split(), 'tree': release[2]}
        ancestry = git_call(owner, log, 'merge-base', '--is-ancestor', RELEASES[owner], expected_heads[owner],
                            allowed_codes=(0, 1))
        require(ancestry['returncode'] == 0, 'positive_release_ancestry_unavailable_' + owner)
        state['positive_release_ancestry'] = True
        state['ancestry_method'] = 'Actual merge-base --is-ancestor exit 0. Shallow=true is allowed; negative or unavailable blocks SSH.'
        refs = {'accepted_candidate': ACCEPTED[owner], 'merged_release': RELEASES[owner],
                'expected_installed_head': expected_heads[owner]}
        paths = set(grouped[owner])
        for ref in dict.fromkeys(refs.values()):
            actual = git_call(owner, log, 'rev-parse', '--verify', ref + '^{commit}')['stdout'].decode('ascii').strip()
            require(actual == ref, 'actual_commit_object_' + owner)
        maps = {ref: tree_map(owner, log, ref, paths) for ref in dict.fromkeys(refs.values())}
        bodies = blob_batch(owner, log, [oid for entries in maps.values() for oid in entries.values()])
        state['verified_refs'] = {}
        for label, ref in refs.items():
            protected = {}
            for path, expected_sha in grouped[owner].items():
                oid = maps[ref][path]
                body = bodies[oid]
                require(digest(body) == expected_sha, 'bound_source_drift_' + owner + '_' + label + '_' + path)
                protected[path] = {'blob': oid, 'sha256': digest(body), 'bytes': len(body)}
            state['verified_refs'][label] = {'commit': ref, 'protected_sources': protected}
    return record['repositories']


def strict_json(body):
    def pairs(items):
        value = {}
        for k, v in items:
            require(k not in value, 'duplicate_remote_json_key')
            value[k] = v
        return value
    def nonfinite(_value):
        raise GateFailure('nonfinite_remote_json')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=nonfinite)

def validate_proof(body, expected_heads, constants):
    proof = strict_json(body)
    require(type(proof) is dict and proof.get('schema') == 'mastermind.rs_pullback_launch.installed_basis_conformance.v1'
            and proof.get('result') == 'PASS', 'remote_scoped_proof_pass')
    require(proof['macro_merge_commit'] == RELEASES['macro'] and proof['terminal_merge_commit'] == RELEASES['terminal'],
            'remote_release_identity')
    require(proof['expected_installed_heads'] == expected_heads
            and proof['installed_heads_before'] == expected_heads and proof['installed_heads_after'] == expected_heads,
            'remote_actual_installed_heads')
    for key in ('installed_shallow_before', 'installed_shallow_after'):
        require(type(proof[key]) is dict and set(proof[key]) == set(REPOS)
                and all(type(v) is bool for v in proof[key].values()), 'remote_actual_shallow_state')
    require(proof['host_release_ancestry'] == {
        'status': 'UNAVAILABLE_NOT_CHECKED', 'positive_ancestry_claimed': False,
        'required_external_evidence': 'POSITIVE_M2_LINEAGE_BEFORE_SINGLE_SSH'}, 'remote_no_invented_ancestry')
    require(proof['installed_sha256'] == constants['EXPECTED']
            and proof['exact_installed_source_hashes_unchanged'] is True, 'remote_exact_bound_sources')
    require(proof['overall_panel'] == 'NOT_ADMITTED'
            and all(proof[name] == 'NOT_TESTED' for name in ('H1', 'H2', 'H3'))
            and proof['provider_calls'] == 0 and proof['runtime_data_writes'] == 0
            and proof['market_inputs'] == 'SYNTHETIC_CONFORMANCE', 'remote_scope_and_admission_limits')
    harness = proof['proof']
    require(harness['result'] == 'PASS' and type(harness['checks']) is dict and len(harness['checks']) == 19
            and all(value is True for value in harness['checks'].values()), 'remote_all_19_owner_controls')
    expected = {
        'complete_length': (0, 1, 'complete', None, 1, 1, True, 0, None, None),
        'short_first_page': (1, 5, 'failed', 'transport_exhausted', 0, 0, False, 10, None, None),
        'short_later_page': (1, 6, 'partial', 'transport_exhausted', 1, 1, False, 10, True, True),
    }
    fields = ('exit', 'requests', 'capture_status', 'failure_kind', 'pages', 'observations', 'chart_eligible',
              'declared_remaining_bytes', 'prior_capture_and_chart_preserved',
              'exact_first_complete_page_and_observation_preserved')
    framing = proof['installed_http_framing_controls']
    require(type(framing) is dict and set(framing) == set(expected), 'remote_framing_control_closure')
    for case, values in expected.items():
        require(framing[case]['result'] == 'PASS' and tuple(framing[case][key] for key in fields) == values,
                'remote_framing_control_' + case)
    def clocks(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('_ns') and child is not None:
                    require(type(child) is str and re.fullmatch('[0-9]+', child) is not None,
                            'remote_exact_nanosecond_string')
                clocks(child)
        elif isinstance(value, list):
            for child in value:
                clocks(child)
    clocks(proof)
    started, completed = (int(proof[key]) for key in ('execution_started_at_utc_ns', 'execution_completed_at_utc_ns'))
    require(0 < started <= completed, 'remote_execution_clock_order')
    return {'status': 'PASS', 'installed_heads': expected_heads, 'owner_controls': 19, 'framing_controls': 3,
            'execution_started_at_utc_ns': str(started), 'execution_completed_at_utc_ns': str(completed),
            'scope': 'Installed v2 owner functions and HTTP framing with synthetic inputs; no live acquisition or basis admission.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--expected-macro-head', required=True)
    parser.add_argument('--expected-terminal-head', required=True)
    args = parser.parse_args()
    expected_heads = {'macro': args.expected_macro_head, 'terminal': args.expected_terminal_head}
    started_ns = time.time_ns()
    attempt_id = uuid.uuid4().hex
    directory = Path('/private/tmp') / ('rs-pullback-installed-basis-' + str(started_ns) + '-' + attempt_id)
    os.mkdir(directory, 0o700)
    lineage = {'schema': 'mastermind.installed_basis_release_lineage.v1', 'attempt_id': attempt_id,
               'status': 'FAIL_OR_UNAVAILABLE', 'started_utc_ns': str(started_ns),
               'expected_installed_heads': expected_heads, 'accepted_candidates': ACCEPTED, 'merged_releases': RELEASES,
               'script_sha256': REMOTE_SCRIPT_SHA256, 'repositories': {},
               'scope': 'Local Git object lineage and exact source bindings, not remote installation or authenticity.'}
    delivery = {'schema': 'mastermind.installed_basis_delivery_receipt.v1', 'attempt_id': attempt_id,
                'result': 'FAIL_OR_UNAVAILABLE', 'started_utc_ns': str(started_ns),
                'expected_installed_heads': expected_heads, 'merged_releases': RELEASES,
                'script_sha256': REMOTE_SCRIPT_SHA256, 'ssh_attempt_count': 0, 'automatic_retry': False,
                'phase1': 'NOT_ADMITTED', 'hypotheses': {'H1': 'NOT_TESTED', 'H2': 'NOT_TESTED', 'H3': 'NOT_TESTED'},
                'basis_id': None, 'basis_admitted': False}
    ready = False
    try:
        require(sys.flags.dont_write_bytecode, 'python_B_flag_required')
        require(all(re.fullmatch('[a-f0-9]{40}', value) is not None for value in expected_heads.values()),
                'exact_root_commit_arguments')
        require(str(args.script.resolve()).startswith('/private/tmp/'), 'reviewed_script_private_temporary_path')
        script, constants, grouped, script_record = read_script(args.script)
        lineage['script_read'] = script_record
        preflight(expected_heads, grouped, lineage)
        lineage['status'] = 'PASS_BOTH_POSITIVE_ANCESTRIES_AND_11_BOUND_SOURCES'
        ready = True
    except Exception as exc:
        lineage['failure'] = {'type': type(exc).__name__, 'control': str(exc) if isinstance(exc, GateFailure) else 'preflight_exception'}
    lineage['completed_utc_ns'] = str(time.time_ns())
    delivery['lineage'] = write_once(directory / 'lineage.json', encoded(lineage))
    if ready:
        ssh = ['/usr/bin/ssh', '-T', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
               '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
               '-o', 'ConnectTimeout=20', '-o', 'ConnectionAttempts=1',
               '-i', '/Users/chriswong/.ssh/macro_dashboard_deploy_v2', 'root@146.190.142.17',
               '/opt/macro-api/.venv/bin/python', '-I', '-B', '-',
               '--expected-macro-head', expected_heads['macro'], '--expected-terminal-head', expected_heads['terminal']]
        delivery['ssh_attempt_count'] = 1
        delivery['ssh_intent'] = write_once(directory / 'ssh-intent.json', encoded({
            'schema': 'mastermind.installed_basis_ssh_intent.v1', 'attempt_id': attempt_id,
            'recorded_before_ssh_utc_ns': str(time.time_ns()), 'argv': ssh,
            'script_bytes': len(script), 'script_sha256': digest(script), 'lineage': delivery['lineage'],
            'retry_permitted': False, 'limits': {'timeout_seconds': SSH_TIMEOUT_SECONDS,
                                               'stdout_bytes': SSH_STDOUT_BYTES, 'stderr_bytes': SSH_STDERR_BYTES}}))
        result = bounded_command(ssh, input_bytes=script, timeout=SSH_TIMEOUT_SECONDS,
                                 stdout_limit=SSH_STDOUT_BYTES, stderr_limit=SSH_STDERR_BYTES,
                                 env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
        delivery['raw_stdout'] = write_once(directory / 'stdout.raw', result['stdout'])
        delivery['raw_stderr'] = write_once(directory / 'stderr.raw', result['stderr'])
        delivery['ssh'] = command_summary(result)
        delivery['remote_completion'] = 'UNCONFIRMED_RECONCILE_THIS_ATTEMPT'
        try:
            require(result['raw_output_complete'] and result['returncode'] == 0
                    and result['stdin_bytes_sent'] == len(script), 'single_ssh_execution_not_successful')
            delivery['remote_proof'] = validate_proof(result['stdout'], expected_heads, constants)
            delivery['result'] = 'PASS_SCOPED_INSTALLED_V2_PROOF'
            delivery['remote_completion'] = 'REMOTE_SCOPED_PROOF_PASS_OBSERVED'
        except Exception as exc:
            delivery['failure'] = {'type': type(exc).__name__, 'control': str(exc) if isinstance(exc, GateFailure) else 'remote_output_contract'}
    else:
        delivery['failure'] = lineage['failure']
        delivery['remote_completion'] = 'NOT_ATTEMPTED'
    delivery['completed_utc_ns'] = str(time.time_ns())
    receipt = write_once(directory / 'delivery.json', encoded(delivery))
    print(json.dumps({'receipt': receipt, **delivery}, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if delivery['result'] == 'PASS_SCOPED_INSTALLED_V2_PROOF' else 1


if __name__ == '__main__':
    raise SystemExit(main())
