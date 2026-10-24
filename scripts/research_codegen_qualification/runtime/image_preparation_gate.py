"""Pure, fixed-image gate for the one unissued engineering qualification.

This module launches nothing. The admitted caller must establish the current
daemon/client/operation binding and supply a bounded, ordered combined channel
from the exact plain `image inspect <IMAGE>` command. It cannot authenticate that
caller. Only a settled exact absence permits the separately commissioned pull.
"""
import json

IMAGE = 'docker.io/library/python@sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed'
IMAGE_ID = IMAGE.split('@')[1]
ABSENCE = ('Error response from daemon: No such image: python@' + IMAGE_ID + '\n').encode()
ENV = [
    'PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    'LANG=C.UTF-8', 'GPG_KEY=A035C8C19219BA821ECEA86B64E628F8D684696D',
    'PYTHON_VERSION=3.11.17',
    'PYTHON_SHA256=bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599',
]
CAP = 16384


class ImageGateRefused(ValueError):
    pass


def _check(value, reason):
    if not value:
        raise ImageGateRefused(reason)


def _pairs(pairs):
    doc = {}
    for key, value in pairs:
        _check(key not in doc, 'duplicate_json_key')
        doc[key] = value
    return doc


def _nonfinite(_):
    raise ImageGateRefused('nonfinite_json')


def classify_inspection(*, rc, raw, timed_out, truncated, collector_error,
                        permission_refused, client_version, server_version):
    """Return PRESENT or EXACT_ABSENCE; every other observation raises.

    An EXACT_ABSENCE value is an observation, not a dispatch/pull permission.
    PRESENT verifies the fixed image's inspect-level configuration. It does not
    independently fetch/verify the OCI configuration blob or prove containment.
    """
    _check(type(rc) is int, 'exit_status_type')
    _check(type(raw) is bytes and 0 < len(raw) <= CAP, 'raw_bound')
    _check(all(type(v) is bool and v is False for v in
               (timed_out, truncated, collector_error, permission_refused)),
           'incomplete_or_refused')
    _check(type(client_version) is str and type(server_version) is str and
           client_version == server_version == '29.1.3', 'version')
    if rc == 1:
        _check(raw in (ABSENCE, b'[]\n' + ABSENCE), 'absence_channel')
        return 'EXACT_ABSENCE'
    _check(rc == 0, 'unsettled_inspection')
    try:
        rows = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ImageGateRefused('inspection_json') from None
    _check(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict,
           'inspection_shape')
    image = rows[0]
    cfg = image.get('Config')
    digests = image.get('RepoDigests')
    _check(type(digests) is list and all(type(v) is str for v in digests)
           and IMAGE in digests, 'image_reference')
    _check(image.get('Id') == IMAGE_ID and image.get('Os') == 'linux'
           and image.get('Architecture') == 'amd64', 'image_identity')
    _check(type(cfg) is dict, 'image_config')
    required = {'Entrypoint': None, 'Cmd': ['python3'], 'User': '',
                'WorkingDir': '/', 'Volumes': None, 'Env': ENV}
    _check(all(key in cfg and cfg[key] == value for key, value in required.items()),
           'image_configuration')
    _check(cfg.get('Healthcheck') in (None, {}), 'image_healthcheck')
    _check(cfg.get('OnBuild') in (None, []), 'image_onbuild')
    return 'PRESENT'
