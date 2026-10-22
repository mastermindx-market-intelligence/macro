"""Request-bound public projection, not an endpoint, identity or authorization owner."""
from __future__ import annotations
import json
import re
from hashlib import sha256
from typing import Mapping
from engine.market_navigator import ContractError, HORIZONS, _clock, _ref, public_projection

SCHEMA='market_navigator.response/v2'
_REQUEST_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z')
MAX_BYTES=80*1024


def bind_response(packet: Mapping, *, request_id: str, expected_subject: str,
                  expected_horizon: str, requested_as_of: str) -> dict:
    """Bind one source result to the existing route's exact request.

    Correlation IDs are not auth tokens. The route must still enforce rights,
    identity and source admission. The public packet omits internal subject/source
    references; this seam checks subject BEFORE projecting it out. Keep the supplied
    cutoff spelling in the echo so clients need not round microsecond timestamps.
    """
    if not isinstance(request_id,str) or not _REQUEST_ID.fullmatch(request_id):
        raise ContractError('bounded request correlation ID required')
    _ref(expected_subject)
    if expected_horizon not in HORIZONS:raise ContractError('unsupported request horizon')
    cutoff=_clock(requested_as_of)
    if not isinstance(packet,Mapping):raise ContractError('context packet required')
    if (packet.get('subject')!=expected_subject or packet.get('horizon')!=expected_horizon
            or _clock(packet.get('as_of'))!=cutoff):
        raise ContractError('context does not match exact requested subject/horizon/cutoff')
    # Non-authoritative subject correlation: the public packet strips raw
    # internal subject IDs, while the client must still reject wrong-subject
    # cache reuse even when horizon, cutoff and an epoch-local ID coincide.
    # The digest is NOT a source receipt, credential or permission grant.
    out={'schema':SCHEMA,'request_id':request_id,'requested_as_of':requested_as_of,
         'subject_binding_sha256':sha256(expected_subject.encode('utf-8')).hexdigest(),
         'horizon':expected_horizon,'data':public_projection(packet)}
    if len(json.dumps(out,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>MAX_BYTES:
        raise ContractError('public response exceeds its consumer byte budget')
    return out
