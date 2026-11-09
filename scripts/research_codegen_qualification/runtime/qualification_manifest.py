"""Pure installer-result -> fixed-smoke manifest projection.

Caller identity, the externally reviewed commission, exact source hashes and
process observation remain outside this data conversion. No input grants effect
permission. This module performs no file, process, network or runtime action.
"""
from __future__ import annotations
import hashlib
import json
import re

ROOT = '01a1333c-a475-7052-95a8-72a88eb8c17b'
ARCHIVE = 'bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede'
RUNSC = '210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a'
PIN_RECEIPT = 'd470b91e5699529ccca008beb3d1b174c344f9c2762b3fc9316c80f84ce6e6f6'
CONSUMER = '/usr/local/lib/mastermind/research-factory/runsc/20261005.0/runsc'
ARGS = ['--platform=systrap', '--network=none', '--oci-seccomp']
SIZES = {'runsc': 109966750, 'gvisor-bin/checkpointgofer': 69128994,
         'gvisor-bin/gvisor-sentry-prewarmer': 1416,
         'gvisor-bin/gvisor_sentry': 52149808,
         'gvisor-bin/runsc-fd-parking': 1320,
         'gvisor-bin/runsc-metric-server': 53222722}
ENDPOINT = 'unix:///var/run/docker.sock'
HEX = re.compile(r'[0-9a-f]{64}\Z')


class ProjectionRefused(ValueError):
    pass


def _check(ok, field):
    if not ok:
        raise ProjectionRefused(field)


def _digest(value):
    return type(value) is str and HEX.fullmatch(value) is not None and value != '0' * 64


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _check(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def project_installer_result(raw: bytes, *, expected_sha256: str,
                             expected_operation: str, expected_hostname: str,
                             expected_daemon_id: str) -> dict:
    """Validate one exact completed result. Expected values are caller facts.

    In particular, a matching digest is integrity evidence, never authentication.
    All errors expose only fixed field names; private config values are omitted.
    """
    _check(type(raw) is bytes and 0 < len(raw) <= 262144, 'raw result bound')
    _check(_digest(expected_sha256) and hashlib.sha256(raw).hexdigest() == expected_sha256,
           'raw result digest')
    for value in (expected_operation, expected_hostname, expected_daemon_id):
        _check(type(value) is str and 0 < len(value) <= 128 and
               all(32 <= ord(c) <= 126 for c in value), 'expected identity')
    try:
        doc = json.loads(raw, object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ProjectionRefused('nonfinite JSON')))
        _check(type(doc) is dict and doc['schema'] == 'mastermind.rf_runsc_install_receipt.v2', 'schema')
        _check(doc['root_id'] == ROOT and doc['operation_id'] == expected_operation, 'root/operation')
        _check(doc['status'] in ('OK_INSTALLED', 'OK_REUSE_EXISTING') and
               type(doc['exit_code']) is int and doc['exit_code'] == 0 and
               doc['receipt_write_failed'] is False and doc['unknowns'] == [] and doc['rollback'] == {},
               'settled successful result')
        host = doc['host']; docker = doc['docker']; bundle = doc['bundle']; config = doc['config']
        _check(host['hostname'] == expected_hostname and type(host['uid']) is int and host['uid'] == 0
               and host['platform'] == ['Linux', 'x86_64'], 'host')
        _check(doc['docker_endpoint'] == ENDPOINT and docker['daemon_id'] == expected_daemon_id and
               docker['client_version'] == docker['server_version'] == '29.1.3', 'daemon')
        _check(all(type(docker[k]) is int and docker[k] == 0 for k in ('container_total', 'container_running')),
               'container census')
        settle = doc['settlement']
        _check(settle['confirmed'] is True and settle['verified'] is True and settle['outcome'] == 'VERIFIED'
               and settle['default_runtime'] == docker['default_runtime'] and 'rf-runsc' in settle['runtime_names'],
               'reload settlement')
        _check(doc['archive']['sha256'] == ARCHIVE and type(doc['archive']['size_bytes']) is int
               and doc['archive']['size_bytes'] == 166822039, 'archive')
        _check(bundle['version_dir'] == CONSUMER.rsplit('/', 1)[0]
               and bundle['runtime_entry'] == {'path': CONSUMER, 'runtimeArgs': ARGS}
               and bundle['shim_installed'] is False and
               all(type(bundle[k]) is bool for k in ('created', 'reused')) and
               (bundle['created'] != bundle['reused']), 'bundle')
        sizes = bundle['member_sizes']; pins = bundle['member_sha256']
        _check(type(sizes) is dict and sizes == SIZES and all(type(v) is int for v in sizes.values())
               and type(pins) is dict and set(pins) == set(SIZES)
               and all(_digest(v) for v in pins.values()) and pins['runsc'] == RUNSC, 'member pins')
        _check(doc['binding']['root_id'] == ROOT and doc['binding']['operation_id'] == expected_operation
               and doc['binding']['member_sha256'] == pins, 'binding')
        _check(config['path'] == '/etc/docker/daemon.json' and config['commit_uncertain'] is False,
               'configuration')
        if doc['status'] == 'OK_INSTALLED':
            _check(config['committed'] is True and config['additive_diff_asserted'] is True,
                   'config commit')
            config_digest = config['postimage_sha256']
        else:
            _check(bundle['reused'] is True and config['committed'] is False, 'reuse')
            config_digest = config['preimage_sha256']
        _check(_digest(config_digest), 'config digest')
        _check(type(doc['commands']) is list and 0 < len(doc['commands']) <= 256, 'command observations')
        for command in doc['commands']:
            _check(type(command['rc']) is int and command['rc'] == 0
                   and command['timed_out'] is False and command['truncated'] is False
                   and command['refused'] is False, 'command completion')
    except ProjectionRefused:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise ProjectionRefused('malformed installer result') from None
    return {'manifest_schema': 'rf.qualification_runsc.installer_receipt.v1', 'root': ROOT,
            'installer_operation': expected_operation, 'archive_sha256': ARCHIVE,
            'consumer_path': CONSUMER, 'runtime_name': 'rf-runsc', 'runtime_args': list(ARGS),
            'config_path': '/etc/docker/daemon.json', 'config_sha256': config_digest,
            'actual_hostname': expected_hostname, 'status': 'installed',
            'members': {name: {'size': SIZES[name], 'sha256': pins[name]} for name in SIZES},
            'pin_adjudication_sha256': PIN_RECEIPT}
