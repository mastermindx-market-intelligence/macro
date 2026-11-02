#!/usr/bin/env python3
"""Prepare positive M2 lineage, then make exactly one reviewed Split proof call.

Root must review this wrapper and independently authorize its later M2 execution.
Only unique /private/tmp receipts are written. No fetch, deploy, restart, provider
acquisition, repository mutation, fallback carrier, or automatic retry exists.
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


REPO = Path('/Users/chriswong/Documents/GitHub/macro')
ACCEPTED_SOURCE = 'd657ab26781e87a19d9c8705d5ac293c816acbb5'
RELEASE = 'f2c33b5e1373a344fde232a6750ef479ccfd6331'
RELEASE_PARENT = '70d2bef9662618d9209aad40b534e2fb8ef10864'
RELEASE_TREE = '2ce5b02de07fbb1a8ba4c8211b403e7d013fa256'
# Root supplied these exact bytes after independent delta review. Wrapper review
# and a separate root execution decision are still required.
REMOTE_SCRIPT_SHA256 = '62ab08fb2b08687176a90356352f115915b25987ed2210351ef72f2db8192483'
REMOTE_SCRIPT_BYTES = 39404
REMOTE_DIGEST_FINAL = True
REGISTRY = 'config/dataset_registry.yml'
ACCEPTED_REGISTRY_BLOB = 'ce4e46f1cf9d6d4f9e513cef00f08091209113b8'
ACCEPTED_REGISTRY_SHA256 = 'dd17affb0d76187aea6e49096212b6d1916c10887c929603741003f1fb074453'
SPLIT_DATASET = 'reference.corporate_actions.massive_split_evidence'
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


def git_call(log, *args, input_bytes=None, stdout_limit=65536, allowed_codes=(0,)):
    argv = ['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'log.showSignature=false',
            '-c', 'protocol.allow=never', '-C', str(REPO), *args]
    result = bounded_command(argv, input_bytes=input_bytes, timeout=30,
                             stdout_limit=stdout_limit, stderr_limit=16384, env=GIT_ENV)
    log.append(command_summary(result))
    require(result['raw_output_complete'] and result['returncode'] in allowed_codes,
            'git_read_unavailable_' + args[0])
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
            if name in {'BINDINGS', 'REGISTRY_BLOCKS', 'PREFIX_SHA', 'SOURCE_HEAD', 'AUTHORITY'}:
                require(name not in constants, 'duplicate_remote_constant')
                constants[name] = ast.literal_eval(node.value)
    require(set(constants) == {'BINDINGS', 'REGISTRY_BLOCKS', 'PREFIX_SHA', 'SOURCE_HEAD', 'AUTHORITY'}
            and constants['SOURCE_HEAD'] == ACCEPTED_SOURCE and len(constants['BINDINGS']) == 12
            and set(constants['REGISTRY_BLOCKS']) == {SPLIT_DATASET, 'reference.vendor_aliases'},
            'reviewed_remote_source_closure')
    for name, pair in constants['BINDINGS'].items():
        require(isinstance(name, str) and not name.startswith('/') and '..' not in Path(name).parts
                and isinstance(pair, tuple) and len(pair) == 2
                and re.fullmatch('[a-f0-9]{40}', pair[0]) and re.fullmatch('[a-f0-9]{64}', pair[1]),
                'remote_source_binding_shape')
    return body, constants, {'path': str(path), 'bytes': len(body), 'sha256': digest(body),
                             'read_started_utc_ns': str(before_ns), 'read_completed_utc_ns': str(after_ns)}


def tree_map(log, ref, paths):
    raw = git_call(log, 'ls-tree', '-rz', ref, '--', *sorted(paths))['stdout']
    result = {}
    for item in raw.split(b'\0'):
        if not item:
            continue
        header, path = item.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        name = path.decode('utf-8')
        require(name not in result and mode == '100644' and kind == 'blob', 'source_tree_entry')
        result[name] = oid
    require(set(result) == set(paths), 'source_tree_complete')
    return result


def blob_batch(log, oids):
    ordered = sorted(set(oids))
    raw = git_call(log, 'cat-file', '--batch', input_bytes=('\n'.join(ordered) + '\n').encode('ascii'),
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


def projection(body, dataset):
    lines = body.splitlines(keepends=True)
    marker = ('  - dataset_id: ' + dataset + '\n').encode('ascii')
    starts = [i for i, line in enumerate(lines) if line == marker]
    require(len(starts) == 1, 'registry_projection_occurrence_' + dataset)
    begin = starts[0]
    end = next((i for i in range(begin + 1, len(lines)) if lines[i].startswith(b'  - dataset_id:')), len(lines))
    block = b''.join(lines[begin:end])
    return {'bytes': len(block), 'sha256': digest(block)}


def preflight(expected_head, constants, record):
    log = record['git_commands']
    shallow = git_call(log, 'rev-parse', '--is-shallow-repository')['stdout'].strip()
    require(shallow in (b'true', b'false'), 'local_shallow_state')
    record['local_repository_shallow'] = shallow == b'true'
    release = git_call(log, 'show', '-s', '--format=%H%n%P%n%T', RELEASE)['stdout'].decode('ascii').splitlines()
    require(release == [RELEASE, RELEASE_PARENT, RELEASE_TREE], 'actual_split_release_identity')
    record['merged_release_identity'] = {'commit': release[0], 'parent': release[1], 'tree': release[2]}
    ancestry = git_call(log, 'merge-base', '--is-ancestor', RELEASE, expected_head, allowed_codes=(0, 1))
    require(ancestry['returncode'] == 0, 'positive_release_ancestry_unavailable')
    record['positive_release_ancestry'] = True
    record['ancestry_method'] = 'Exact git merge-base --is-ancestor exit 0; shallow=true is allowed. Nonzero or unavailable never proves ancestry.'
    paths = set(constants['BINDINGS']) | {REGISTRY}
    refs = {'accepted_source': ACCEPTED_SOURCE, 'merged_release': RELEASE, 'expected_installed_head': expected_head}
    maps = {ref: tree_map(log, ref, paths) for ref in dict.fromkeys(refs.values())}
    bodies = blob_batch(log, [oid for values in maps.values() for oid in values.values()])
    verified = {}
    for label, ref in refs.items():
        entries = maps[ref]
        protected = {}
        for path, (expected_blob, expected_sha) in constants['BINDINGS'].items():
            body = bodies[entries[path]]
            require(entries[path] == expected_blob and digest(body) == expected_sha, 'bound_source_drift_' + label + '_' + path)
            protected[path] = {'blob': entries[path], 'sha256': digest(body), 'bytes': len(body)}
        wrapper = bodies[entries['engine/close_pass/massive_close.py']]
        require(digest(wrapper[:28996]) == constants['PREFIX_SHA'], 'legacy_wrapper_prefix_' + label)
        registry = bodies[entries[REGISTRY]]
        registry_record = {'blob': entries[REGISTRY], 'sha256': digest(registry), 'bytes': len(registry), 'exact_lexical_projections': {}}
        for dataset, (count, expected_sha) in constants['REGISTRY_BLOCKS'].items():
            actual = projection(registry, dataset)
            registry_record['exact_lexical_projections'][dataset] = actual
            if label != 'accepted_source' or dataset == SPLIT_DATASET:
                require(actual == {'bytes': count, 'sha256': expected_sha}, 'registry_projection_drift_' + label + '_' + dataset)
        if label == 'accepted_source':
            require(entries[REGISTRY] == ACCEPTED_REGISTRY_BLOB and digest(registry) == ACCEPTED_REGISTRY_SHA256,
                    'accepted_registry_exact')
            registry_record['native_projection_scope'] = 'Historical candidate predates Native registry union; release and installed projections must equal the reviewed union.'
        protected[REGISTRY] = registry_record
        verified[label] = {'commit': ref, 'protected_sources': protected}
    record['verified_refs'] = verified
    return verified['expected_installed_head']['protected_sources']


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


def validate_proof(body, expected_head, expected_sources, constants):
    proof = strict_json(body)
    require(isinstance(proof, dict) and proof.get('schema') == 'mastermind.installed_split_function_conformance.v1'
            and proof.get('status') == 'PASS', 'remote_scoped_proof_pass')
    require(proof['accepted_source_head'] == ACCEPTED_SOURCE and proof['expected_installed_head'] == expected_head
            and proof['merged_release'] == RELEASE and proof['release_relation']['installed_head'] == expected_head,
            'remote_actual_source_identity')
    require(proof['phase1'] == 'NOT_ADMITTED' and proof['hypotheses'] == {'H1': 'NOT_TESTED', 'H2': 'NOT_TESTED', 'H3': 'NOT_TESTED'}
            and proof['basis_id'] is None and proof['factor_applicability'] is None and proof['factor_basis_admitted'] is False
            and proof['authority'] == constants['AUTHORITY'], 'remote_authority_and_admission_limits')
    require(proof['claims'] == {'installed_functions_with_synthetic_inputs': True, 'normal_package_initialization': False,
            'live_market_acquisition': False, 'live_http_api': False, 'source_authenticity': False,
            'price_or_volume_reconstruction': False, 'production_cadence': False}, 'remote_claim_scope')
    require(proof['temporary_cleanup'] == 'OWN_DIRECTORY_REMOVED' and proof['effect_guard']['blocked_operations'] == 0
            and proof['effect_guard']['network_permitted'] is False and proof['effect_guard']['real_provider_calls'] == 0,
            'remote_effect_and_cleanup_scope')
    for phase in ('installed_source_before', 'installed_source_after'):
        actual = proof[phase]
        require(set(actual) == set(expected_sources), 'remote_source_closure_' + phase)
        for path, expected in expected_sources.items():
            for field in ('blob', 'sha256', 'bytes'):
                require(actual[path][field] == expected[field], 'remote_source_binding_' + phase + '_' + path)
            if path == REGISTRY:
                require(actual[path]['exact_lexical_projections'] == expected['exact_lexical_projections'], 'remote_registry_projection_' + phase)
    def clocks(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('_ns') and child is not None:
                    require(isinstance(child, str) and re.fullmatch('[0-9]+', child) is not None and int(child) > 0,
                            'remote_exact_nanosecond_string')
                clocks(child)
        elif isinstance(value, list):
            for child in value:
                clocks(child)
    clocks(proof)
    require(int(proof['started_utc_ns']) <= int(proof['completed_utc_ns']), 'remote_outer_clock_order')
    return {'status': proof['status'], 'proof_id': proof['proof_id'],
            'started_utc_ns': proof['started_utc_ns'], 'completed_utc_ns': proof['completed_utc_ns'],
            'receipt_count': proof['temporary_store']['receipt_count'], 'scope': 'installed_owner_functions_with_synthetic_inputs'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--merged-release', required=True)
    args = parser.parse_args()
    started_ns = time.time_ns()
    attempt_id = uuid.uuid4().hex
    directory = Path('/private/tmp') / ('rs-pullback-installed-split-' + str(started_ns) + '-' + attempt_id)
    os.mkdir(directory, 0o700)
    lineage = {'schema': 'mastermind.installed_split_release_lineage.v1', 'attempt_id': attempt_id,
               'status': 'FAIL_OR_UNAVAILABLE', 'started_utc_ns': str(started_ns),
               'repository': str(REPO), 'accepted_source': ACCEPTED_SOURCE, 'merged_release': RELEASE,
               'expected_installed_head': args.expected_head, 'script_sha256': REMOTE_SCRIPT_SHA256,
               'git_commands': [], 'positive_release_ancestry': False,
               'scope': 'Local Git object lineage and exact source bindings, not remote installation or authenticity.'}
    delivery = {'schema': 'mastermind.installed_split_delivery_receipt.v1', 'attempt_id': attempt_id,
                'result': 'FAIL_OR_UNAVAILABLE', 'started_utc_ns': str(started_ns),
                'expected_installed_head': args.expected_head, 'merged_release': RELEASE,
                'script_sha256': REMOTE_SCRIPT_SHA256, 'ssh_attempt_count': 0,
                'automatic_retry': False, 'phase1': 'NOT_ADMITTED',
                'hypotheses': {'H1': 'NOT_TESTED', 'H2': 'NOT_TESTED', 'H3': 'NOT_TESTED'},
                'basis_id': None, 'basis_admitted': False}
    ready = False
    try:
        require(sys.flags.dont_write_bytecode, 'python_B_flag_required')
        require(REMOTE_DIGEST_FINAL, 'remote_digest_awaiting_final_independent_review')
        require(re.fullmatch('[a-f0-9]{40}', args.expected_head) is not None
                and args.merged_release == RELEASE, 'exact_root_commit_arguments')
        require(str(args.script.resolve()).startswith('/private/tmp/'), 'reviewed_script_private_temporary_path')
        script, constants, script_record = read_script(args.script)
        lineage['script_read'] = script_record
        expected_sources = preflight(args.expected_head, constants, lineage)
        lineage['status'] = 'PASS_POSITIVE_ANCESTRY_AND_BOUND_SOURCES'
        ready = True
    except Exception as exc:
        lineage['failure'] = {'type': type(exc).__name__, 'control': str(exc) if isinstance(exc, GateFailure) else 'preflight_exception'}
    lineage['completed_utc_ns'] = str(time.time_ns())
    # This durable immutable receipt precedes the sole SSH invocation.
    delivery['lineage'] = write_once(directory / 'lineage.json', encoded(lineage))
    if ready:
        ssh = ['/usr/bin/ssh', '-T', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
               '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
               '-o', 'ConnectTimeout=20', '-o', 'ConnectionAttempts=1',
               '-i', '/Users/chriswong/.ssh/macro_dashboard_deploy_v2', 'root@146.190.142.17',
               '/opt/macro-api/.venv/bin/python', '-I', '-B', '-', '--expected-head', args.expected_head,
               '--merged-release', RELEASE]
        delivery['ssh_attempt_count'] = 1
        delivery['ssh_intent'] = write_once(directory / 'ssh-intent.json', encoded({
            'schema': 'mastermind.installed_split_ssh_intent.v1', 'attempt_id': attempt_id,
            'recorded_before_ssh_utc_ns': str(time.time_ns()), 'argv': ssh,
            'script_bytes': len(script), 'script_sha256': digest(script), 'lineage': delivery['lineage'],
            'retry_permitted': False, 'limits': {'timeout_seconds': SSH_TIMEOUT_SECONDS,
                                               'stdout_bytes': SSH_STDOUT_BYTES, 'stderr_bytes': SSH_STDERR_BYTES}}))
        result = bounded_command(ssh, input_bytes=script, timeout=SSH_TIMEOUT_SECONDS,
                                 stdout_limit=SSH_STDOUT_BYTES, stderr_limit=SSH_STDERR_BYTES,
                                 env={'PATH': '/usr/bin:/bin', 'LANG': 'C'})
        # Persist raw bytes, including empty or malformed output, before parsing.
        delivery['raw_stdout'] = write_once(directory / 'stdout.raw', result['stdout'])
        delivery['raw_stderr'] = write_once(directory / 'stderr.raw', result['stderr'])
        delivery['ssh'] = command_summary(result)
        delivery['remote_completion'] = 'UNCONFIRMED_RECONCILE_THIS_ATTEMPT'
        try:
            require(result['raw_output_complete'] and result['returncode'] == 0
                    and result['stdin_bytes_sent'] == len(script), 'single_ssh_execution_not_successful')
            delivery['remote_proof'] = validate_proof(result['stdout'], args.expected_head, expected_sources, constants)
            delivery['result'] = 'PASS_SCOPED_INSTALLED_FUNCTION_PROOF'
            delivery['remote_completion'] = 'REMOTE_SCOPED_PROOF_PASS_OBSERVED'
        except Exception as exc:
            delivery['failure'] = {'type': type(exc).__name__, 'control': str(exc) if isinstance(exc, GateFailure) else 'remote_output_contract'}
    else:
        delivery['failure'] = lineage['failure']
        delivery['remote_completion'] = 'NOT_ATTEMPTED'
    delivery['completed_utc_ns'] = str(time.time_ns())
    receipt = write_once(directory / 'delivery.json', encoded(delivery))
    print(json.dumps({'receipt': receipt, **delivery}, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if delivery['result'] == 'PASS_SCOPED_INSTALLED_FUNCTION_PROOF' else 1


if __name__ == '__main__':
    raise SystemExit(main())
