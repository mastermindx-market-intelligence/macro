"""Exact one-operation pinned image preparation for the unissued canary.

No CLI/default execution. An admitted caller supplies the accepted installer
instance, the hash-verified transport module, an existing absolute deadline,
and its durable before-pull receipt sink. No tag/host/config/command override.
"""
import hashlib
import base64
import json
import time

import image_preparation_gate as gate
import qualification_smoke as smoke

INFO_FORMAT = ('{"ID":{{json .ID}},"Name":{{json .Name}},'
               '"KernelVersion":{{json .KernelVersion}},'
               '"OperatingSystem":{{json .OperatingSystem}},'
               '"OSType":{{json .OSType}},"Architecture":{{json .Architecture}},'
               '"ServerVersion":{{json .ServerVersion}},'
               '"Containers":{{json .Containers}},"ContainersRunning":{{json .ContainersRunning}}}')


class ImagePhaseRefused(ValueError):
    pass


def _check(value, reason):
    if not value:
        raise ImagePhaseRefused(reason)


def _json(raw):
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=gate._pairs,
                            parse_constant=gate._nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise ImagePhaseRefused('control_json') from None
    _check(type(result) is dict, 'control_shape')
    return result


def prepare(installer, transport, *, deadline, raw_cap, before_pull, observe,
            clock=time.monotonic):
    """Return qualified inspect facts, never a runtime/containment grant.

    One call only; the enclosing original operation owns replay prevention.
    An incomplete pull is retained as unconfirmed; no retry or image removal.
    The callback must durably record intent before returning. Its failure stops
    before pull. The observer receives each captured record before validation,
    including incomplete captures. An observer failure stops all later calls.
    The caller accounts raw bytes and returned metadata globally.
    """
    _check(type(raw_cap) is int and 0 < raw_cap <= 16384, 'output_envelope')
    _check(callable(observe), 'observation_sink')
    _check(installer.status in ('OK_INSTALLED', 'OK_REUSE_EXISTING')
           and not installer.frozen, 'installer_unsettled')
    _check(installer.binding is not None and
           installer.binding.operation_id == 'rf-fixed-smoke-runsc-01a1333c-v4', 'operation')
    prefix = (smoke.DOCKER_BINARY, '--host', smoke.DOCKER_ENDPOINT,
              '--config', installer.docker_config_path)
    records, used = [], 0

    def check():
        _check(0 < deadline - clock() <= 240, 'phase_deadline')
        _check(not installer.frozen, 'effect_frozen')
        installer._verify_client_config()
        facts = installer.socket_inspector(installer.layout.docker_socket, installer.root_uid)
        _check(facts == installer.socket_facts, 'socket_identity')

    def call(name, args, maximum, reserve=0, reserve_bytes=0):
        nonlocal used
        check()
        left = deadline - clock() - reserve
        room = raw_cap - used - reserve_bytes
        _check(left > 0 and room > 0, 'phase_budget')
        result = transport.collect_process(prefix + tuple(args),
                    deadline_seconds=min(maximum, left), output_cap_bytes=room)
        _check(type(result.output) is bytes, 'collector_output')
        used += len(result.output)
        records.append({'name': name, 'rc': result.returncode,
                        'raw_bytes': len(result.output),
                        'raw_sha256': hashlib.sha256(result.output).hexdigest(),
                        'raw_b64': base64.b64encode(result.output).decode('ascii'),
                        'timed_out': result.timed_out, 'truncated': result.output_truncated,
                        'error_type': result.error_type})
        observe(dict(records[-1]))
        _check(used <= raw_cap and type(result.returncode) is int
               and result.timed_out is False and result.output_truncated is False
               and result.error_type is None, 'collector_incomplete')
        # This is trusted control output only, never candidate/workload output.
        denial = transport.control_permission_refusal('inspect', result.returncode, result.output)
        denial = denial or any(line.startswith(b'Error response from daemon: ')
            and any(marker in line.lower() for marker in
                    (b'permission denied', b'access denied', b'authorization denied',
                     b'unauthorized', b'forbidden', b'not authorized'))
            for line in result.output.split(b'\n'))
        _check(not denial, 'control_refused')
        check()
        return result

    def identity():
        version = call('version', ('version','--format',smoke._VERSION_FORMAT),10)
        _check(version.returncode == 0, 'version_unconfirmed')
        _check(_json(version.output) == {'Client':'29.1.3','Server':'29.1.3'}, 'version')
        result = call('daemon', ('info','--format',INFO_FORMAT),10)
        _check(result.returncode == 0, 'daemon_unconfirmed')
        doc = _json(result.output)
        _check(doc.get('ID') == installer.daemon_id and doc.get('Name') == installer.host_id
               and doc.get('ServerVersion') == '29.1.3' and doc.get('OSType') == 'linux'
               and doc.get('Architecture') == 'x86_64', 'daemon_identity')
        _check(all(type(doc.get(k)) is int and doc[k] == 0 for k in
                   ('Containers','ContainersRunning')), 'container_census')
        _check(all(type(doc.get(k)) is str and 0 < len(doc[k]) <= 128 and
                   all(32 <= ord(c) <= 126 for c in doc[k])
                   for k in ('KernelVersion','OperatingSystem')), 'host_facts')
        return doc

    def inspect():
        r = call('image_inspect', ('image','inspect',gate.IMAGE),10)
        decision = gate.classify_inspection(rc=r.returncode, raw=r.output,
            timed_out=False,truncated=False,collector_error=False,permission_refused=False,
            client_version='29.1.3',server_version='29.1.3')
        return decision

    host = identity()
    first = inspect()
    pulled = False
    if first == 'EXACT_ABSENCE':
        host = identity()
        check()
        intent = {'phase':'before_exact_image_pull',
                     'operation':installer.binding.operation_id,'root':smoke.ROOT_ID,
                     'hostname':installer.host_id,'daemon_id':installer.daemon_id,
                     'image':gate.IMAGE,'precheck':'EXACT_ABSENCE',
                     'precheck_raw_sha256':records[2]['raw_sha256']}
        digest = before_pull(intent)
        _check(type(digest) is str and digest == hashlib.sha256(
            json.dumps(intent, sort_keys=True, separators=(',',':')).encode()).hexdigest(),
            'pull_intent_receipt')
        check()
        # Keep readback time inside this phase, not as a fresh 240-second grant.
        result = call('image_pull', ('image','pull',gate.IMAGE),210,
                      reserve=40, reserve_bytes=8192)
        _check(result.returncode == 0, 'pull_unconfirmed_no_retry')
        pulled = True
        host = identity()
        _check(inspect() == 'PRESENT', 'postpull_image_missing')
    check()
    return {'schema':'rf.fixed_image_preparation.v1','status':'PRESENT',
            'root':smoke.ROOT_ID,'operation':installer.binding.operation_id,
            'hostname':installer.host_id,'daemon_id':installer.daemon_id,
            'image':gate.IMAGE,'image_id':gate.IMAGE_ID,
            'oci_config_digest':smoke.OCI_CONFIG_DIGEST,
            'oci_config_blob_independently_read':False,
            'pull_count':1 if pulled else 0,'raw_bytes':used,
            'host':host,'observations':records,'candidate_admission':False}
