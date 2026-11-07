"""Internal native participant RPC adapter for the existing Investigation owner.

Source only: this does not install SQL/grants, enroll an issuer or attest runtime
credentials. Generation identifies the original execution; it is not authority.
Only the configured server role may invoke the proposed fixed RPCs. Callers must
first obtain the actual accepted-token principal/issuer/session and current
rights. record_retained belongs AFTER the original producer's guaranteed
no-more-retention-writes boundary with known outgoing store outcomes. Lost or
partial effects/receipt persistence stay UNKNOWN; neither method retries.
No public route, user-token fallback, new credential or persistent store exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
import re
from typing import Callable
from urllib.parse import urlsplit
from urllib.request import Request
import uuid

_SCHEMA = 'investigation.native_capture.v1'
_MAX_REPLY = 8192
_TIMEOUT = 6
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')


class NativeCaptureUnavailable(ValueError):
    """Bounded failure; never carries upstream bodies, credentials or errors."""


def _uuid(value):
    if type(value) is not str:
        raise NativeCaptureUnavailable('native_binding_invalid')
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except ValueError:
        raise NativeCaptureUnavailable('native_binding_invalid') from None
    return value


def _origin(value):
    if type(value) is not str or not 1 <= len(value) <= 240 or not value.isprintable() or any(c.isspace() for c in value):
        raise NativeCaptureUnavailable('native_project_invalid')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or parsed.netloc != parsed.hostname:
        raise NativeCaptureUnavailable('native_project_invalid')
    return value


@dataclass(frozen=True)
class CaptureBinding:
    actor: str
    operation_id: str
    issuer: str
    auth_epoch: str
    request_sha256: str
    source_binding_sha256: str

    def __post_init__(self):
        for value in (self.actor, self.operation_id, self.auth_epoch):
            _uuid(value)
        if type(self.issuer) is not str or not self.issuer.endswith('/auth/v1'):
            raise NativeCaptureUnavailable('native_project_invalid')
        _origin(self.issuer[:-8])
        for value in (self.request_sha256, self.source_binding_sha256):
            if type(value) is not str or not _DIGEST.fullmatch(value):
                raise NativeCaptureUnavailable('native_binding_invalid')


@dataclass(frozen=True)
class ClaimObservation:
    status: str
    generation: str
    binding: CaptureBinding


@dataclass(frozen=True)
class CompletionObservation:
    generation: str
    binding: CaptureBinding
    native_phase: str


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_number(_value):
    raise ValueError


@dataclass(frozen=True)
class NativeCaptureAuthority:
    _project: str
    _service_key: str = field(repr=False)
    _open: Callable = field(repr=False, compare=False)

    def __post_init__(self):
        _origin(self._project)
        if type(self._service_key) is not str or not 1 <= len(self._service_key) <= 4096 or any(c.isspace() for c in self._service_key) or not callable(self._open):
            raise NativeCaptureUnavailable('native_server_binding_unavailable')

    def _rpc(self, function, payload):
        # function is selected exclusively by the two methods below, never a
        # public/caller URL, role or bearer override. One no-redirect send.
        request = Request(self._project + '/rest/v1/rpc/' + function,
            data=json.dumps(payload, separators=(',', ':'), allow_nan=False).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + self._service_key,
                     'apikey': self._service_key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with self._open(request, _TIMEOUT) as response:
                if response.status != 200:
                    raise ValueError
                raw = response.read(_MAX_REPLY + 1)
                if type(raw) is not bytes or not 0 < len(raw) <= _MAX_REPLY:
                    raise ValueError
            return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_reject_number)
        except Exception:
            raise NativeCaptureUnavailable('native_rpc_unavailable') from None

    def _validate_binding(self, binding):
        if type(binding) is not CaptureBinding or binding.issuer != self._project + '/auth/v1':
            raise NativeCaptureUnavailable('native_project_invalid')

    def _decode(self, raw, binding, complete=False):
        keys = {'schema', 'status', 'generation', 'binding'} | ({'native_phase'} if complete else set())
        if type(raw) is not dict or set(raw) != keys or raw['schema'] != _SCHEMA:
            raise NativeCaptureUnavailable('native_receipt_invalid')
        if type(raw['binding']) is not dict or raw['binding'] != asdict(binding):
            raise NativeCaptureUnavailable('native_receipt_binding_mismatch')
        generation = _uuid(raw['generation'])
        if complete:
            if raw['status'] != 'recorded' or raw['native_phase'] != 'retained':
                raise NativeCaptureUnavailable('native_receipt_invalid')
            return CompletionObservation(generation, binding, 'retained')
        if raw['status'] not in ('claimed', 'existing'):
            raise NativeCaptureUnavailable('native_receipt_invalid')
        return ClaimObservation(raw['status'], generation, binding)

    def claim(self, binding: CaptureBinding, canonical_request: dict):
        self._validate_binding(binding)
        _canonical_request(canonical_request, binding.actor)
        raw = self._rpc('claim_investigation_native_capture_v1',
                        {'p_binding': asdict(binding), 'p_request': canonical_request})
        return self._decode(raw, binding)

    def record_retained(self, claim: ClaimObservation):
        if type(claim) is not ClaimObservation or claim.status != 'claimed':
            raise NativeCaptureUnavailable('native_original_claim_unavailable')
        self._validate_binding(claim.binding)
        _uuid(claim.generation)
        raw = self._rpc('complete_investigation_native_capture_v1',
            {'p_binding': asdict(claim.binding), 'p_generation': claim.generation, 'p_native_phase': 'retained'})
        observed = self._decode(raw, claim.binding, True)
        if observed.generation != claim.generation:
            raise NativeCaptureUnavailable('native_receipt_generation_mismatch')
        return observed


def from_server_runtime():
    """Existing server-only credential/project references, evaluated only on use.

    The SQL owner must separately enforce service_role. This constructor does
    not decode/trust a browser JWT, provision a key, inspect its value or claim
    that current grants/credentials exist. No IO happens during construction.
    """
    from app.main import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY
    from app.options_scenarios import _rest_origin, _open_rpc
    try:
        project = _rest_origin()
        if not SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY == SUPABASE_ANON_KEY:
            raise ValueError
        return NativeCaptureAuthority(project, SUPABASE_SERVICE_ROLE_KEY, _open_rpc)
    except Exception:
        raise NativeCaptureUnavailable('native_server_binding_unavailable') from None


def _canonical_request(request, actor):
    # This is the existing typed DB request, compared as JSONB by its owner.
    # The native SHA remains a separate correlation field; no cross-language
    # serialization or digest equivalence is assumed.
    if (type(request) is not dict or set(request) != {'principal', 'action', 'target', 'expected_revision', 'manifest', 'layout_capture'}
            or request.get('principal') != actor or request.get('action') not in ('create', 'revise')
            or type(request.get('manifest')) is not dict):
        raise NativeCaptureUnavailable('native_canonical_request_invalid')
    layout = request['layout_capture']
    if layout is not None:
        if (type(layout) is not dict or set(layout) != {'layout_id', 'expected_revision', 'revision_id'}
                or type(layout.get('expected_revision')) is not int
                or not 1 <= layout['expected_revision'] <= 999999999
                or request['manifest'].get('layout_refs') != []):
            raise NativeCaptureUnavailable('native_canonical_request_invalid')
        _uuid(layout['layout_id'])
        _uuid(layout['revision_id'])
    return request


def _same_json(left, right):
    # JSONB treats numerical 1 and 1.0 alike, but a boolean is never a number.
    if type(left) is dict or type(right) is dict:
        return (type(left) is dict and type(right) is dict and left.keys() == right.keys()
                and all(_same_json(left[key], right[key]) for key in left))
    if type(left) is list or type(right) is list:
        return (type(left) is list and type(right) is list and len(left) == len(right)
                and all(_same_json(a, b) for a, b in zip(left, right)))
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    return type(left) is type(right) and left == right


def binding_for(principal, *, investigation_id, revision, expected_revision, operation_id, capture, canonical_request):
    """Bind the complete existing native request and exact source reference.

    This native-request hash is not a cross-language canonical DB manifest
    digest. The schema owner must keep native and canonical request bindings
    separate when extending its existing original-operation row.
    """
    _uuid(investigation_id)
    _uuid(operation_id)
    if type(revision) is not int or type(expected_revision) is not int or not 0 <= expected_revision < 2147483647 or revision != expected_revision + 1:
        raise NativeCaptureUnavailable('native_binding_invalid')
    if type(capture) is not dict or type(capture.get('source')) is not dict:
        raise NativeCaptureUnavailable('native_binding_invalid')
    _canonical_request(canonical_request, principal.principal_id)
    if (canonical_request['target'] != investigation_id
            or type(canonical_request['expected_revision']) is not int
            or canonical_request['expected_revision'] != expected_revision
            or canonical_request['action'] != ('create' if expected_revision == 0 else 'revise')
            or not _same_json(canonical_request['manifest'].get('scenario_capture'), capture)):
        raise NativeCaptureUnavailable('native_canonical_request_invalid')
    import hashlib
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                       separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    request = {'mode': 'capture', 'investigation_id': investigation_id, 'revision': revision,
               'expected_revision': expected_revision, 'grant_id': None,
               'operation_id': operation_id, 'capture': capture, 'canonical_request': canonical_request}
    return CaptureBinding(principal.principal_id, operation_id, principal.principal_issuer,
                          principal.auth_epoch, digest(request), digest(capture['source']))
