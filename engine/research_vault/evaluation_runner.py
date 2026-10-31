"""Execute a frozen, externally composed candidate and use the incumbent scorer.

This module has no storage, authentication, network factory or executor. Inputs
are private labels and canonical UTF-8 sources supplied separately from a trusted
synchronous candidate adapter. The adapter receives only (query, public_params).
It must enforce its transport deadline and raise TimeoutError or return TIMEOUT.
The runner measures elapsed monotonic time; it cannot interrupt an arbitrary
blocking callable and never claims elapsed-after-return is an enforced deadline.
Known async adapters are rejected before calls. An unexpected returned coroutine
is closed without execution; other awaitables are never awaited.

Candidate digest and admitted scope are caller-supplied consistency bindings.
The evaluation owner separately authenticates/freeze-admits that composition,
source provenance and timeout behavior before any real evaluation. This helper
does not grant that authority or establish a cryptographic identity for a callable.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
import inspect
import math
import time
from typing import Any

from engine.research_vault.retrieval_eval import (
    score_full_document,
    validate_full_document_benchmark,
)

_FAILURE_STATUSES = frozenset({'ERROR', 'TIMEOUT', 'MISSING', 'NONANSWER'})
_EVIDENCE_STATES = frozenset({'FOUND', 'PARTIAL', 'NOT_FOUND', 'UNAVAILABLE'})
_PASSAGE_TEXT_FIELDS = frozenset({
    'report_id', 'source_pdf_sha256', 'extracted_text_sha256', 'text',
    'passage_text_sha256', 'evidence_state',
})


def _sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def _public_parameters(value: Any) -> dict[str, int | float]:
    """Allow public quantities only, never arbitrary case/gold/identifier fields."""
    if not isinstance(value, Mapping) or 'timeout_s' not in value:
        raise ValueError('declared adapter timeout_s required')
    if set(value) - {'limit', 'max_passages', 'timeout_s'}:
        raise ValueError('unsupported public request parameter')
    parameters = dict(value)
    for key, ceiling in [('limit', 50), ('max_passages', 20)]:
        if key in parameters and (type(parameters[key]) is not int
                                  or not 1 <= parameters[key] <= ceiling):
            raise ValueError('invalid public request quantity')
    timeout = parameters['timeout_s']
    if (type(timeout) not in (int, float) or not 0 < timeout <= 300
            or not math.isfinite(timeout)):
        raise ValueError('invalid adapter timeout_s')
    return parameters


def _admitted_scope(value: Any) -> frozenset[tuple[str, str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError('nonempty admitted revision scope required')
    identities = []
    for identity in value:
        if (not isinstance(identity, (tuple, list)) or len(identity) != 3
                or not isinstance(identity[0], str) or not identity[0]
                or not _sha256(identity[1]) or not _sha256(identity[2])):
            raise ValueError('invalid admitted revision identity')
        identities.append(tuple(identity))
    if len(identities) != len(set(identities)):
        raise ValueError('duplicate admitted revision identity')
    return frozenset(identities)


def _source_texts(value: Any) -> dict[tuple[str, str, str], str]:
    if not isinstance(value, Mapping):
        raise ValueError('separate canonical source bytes required')
    texts = {}
    for identity, source in value.items():
        if type(source) is bytes:
            try:
                source = source.decode('utf-8', errors='strict')
            except UnicodeDecodeError:
                raise ValueError('canonical source must be strict UTF8') from None
        if not isinstance(source, str):
            raise ValueError('canonical source must be UTF8 bytes or text')
        texts[identity] = source
    return texts


def _failure(status: str) -> dict[str, Any]:
    return {'status': status, 'ranked_report_ids': [], 'abstained': False,
            'evidence': None, 'model_tokens': None}


def _normalize_response(value: Any) -> dict[str, Any]:
    """Copy only the scorer's fields; never retain debug or exception payloads."""
    if inspect.iscoroutine(value):
        value.close()
        return _failure('NONANSWER')
    if inspect.isawaitable(value):
        return _failure('NONANSWER')
    if not isinstance(value, Mapping):
        return _failure('NONANSWER')
    status = value.get('status', 'OK')
    if status in _FAILURE_STATUSES:
        return _failure(status)
    if status != 'OK':
        return _failure('NONANSWER')
    ranked = value.get('ranked_report_ids')
    evidence = value.get('evidence')
    if (not isinstance(ranked, list) or not isinstance(evidence, Mapping)
            or evidence.get('evidence_state') not in _EVIDENCE_STATES
            or not isinstance(evidence.get('passages'), list)
            or type(value.get('abstained', False)) is not bool):
        return _failure('NONANSWER')
    state = evidence['evidence_state']
    passages = []
    for passage in evidence['passages']:
        if not isinstance(passage, Mapping):
            # Preserve a malformed passage in the scorer's precision denominator.
            passages.append({})
            continue
        clean = {key: passage[key] for key in _PASSAGE_TEXT_FIELDS
                 if key in passage and isinstance(passage[key], str)}
        clean.update({key: passage[key] for key in ('start_byte', 'end_byte')
                      if key in passage and type(passage[key]) is int})
        passages.append(clean)
    ids = [report_id for report_id in ranked if isinstance(report_id, str) and report_id]
    if state in {'NOT_FOUND', 'UNAVAILABLE'} and (ids or passages):
        return _failure('NONANSWER')
    if state in {'FOUND', 'PARTIAL'} and not ids and not passages:
        return _failure('NONANSWER')
    tokens = value.get('model_tokens')
    return {'status': 'OK', 'ranked_report_ids': ids,
            'abstained': value.get('abstained', False),
            'evidence': {'evidence_state': state, 'passages': passages},
            'model_tokens': tokens if type(tokens) is int and tokens >= 0 else None}


def evaluate_full_document(
    benchmark: dict[str, Any],
    candidate: Callable[[str, dict[str, int | float]], Any],
    *,
    candidate_sha256: str,
    candidate_scope: Sequence[tuple[str, str, str]],
    source_texts: Mapping[tuple[str, str, str], str | bytes],
    request_parameters: Mapping[str, int | float],
    k: int = 10,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run READY queries only after whole-batch pin/scope/gold preflight.

    candidate_scope is the exact admitted revision cohort of the externally
    composed candidate; it must equal every READY case's searched_scope. Different
    case cohorts need separately admitted candidate evaluations. The scope is
    checked here, never passed as query parameters or gold-guided candidate IDs.
    request_parameters permits only limit, max_passages and required timeout_s;
    a new public parameter needs an explicitly reviewed allowlist extension.

    READY adapter failures/malformed/nonanswers remain in the existing scorer's
    denominator. Successful UNAVAILABLE/NOT_FOUND are retained so only correctly
    labelled, truthful negatives can earn abstention. Returned metrics contain no
    bodies, query strings, arbitrary candidate extras or exception details.
    """
    frozen = deepcopy(benchmark)
    validate_full_document_benchmark(frozen)
    if (not _sha256(candidate_sha256)
            or candidate_sha256 != frozen['candidate_frozen_sha256']):
        raise ValueError('candidate frozen digest mismatch')
    if (not callable(candidate) or inspect.iscoroutinefunction(candidate)
            or inspect.iscoroutinefunction(getattr(candidate, '__call__', None))):
        raise ValueError('trusted synchronous candidate adapter required')
    scope = _admitted_scope(candidate_scope)
    parameters = _public_parameters(request_parameters)
    ready = [case for case in frozen['cases'] if case['fill_state'] == 'READY']
    for case in ready:
        declared = frozenset((s['report_id'], s['source_pdf_sha256'], s['extracted_text_sha256'])
                             for s in case['searched_scope'])
        if declared != scope:
            raise ValueError('candidate admitted revision scope mismatch')
    canonical = _source_texts(source_texts)
    # Sole scorer validates the actual private gold literals before any query.
    score_full_document(frozen, {}, source_texts=canonical, k=k)
    results = {}
    for case in ready:
        start = clock()
        try:
            result = _normalize_response(candidate(case['query'], dict(parameters)))
        except TimeoutError:
            result = _failure('TIMEOUT')
        except Exception:
            result = _failure('ERROR')
        elapsed = (clock() - start) * 1000.0
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('invalid monotonic latency measurement')
        result['latency_ms'] = elapsed
        results[case['id']] = result
    report = score_full_document(frozen, results, source_texts=canonical, k=k)
    report['execution'] = {
        'candidate_frozen_sha256': candidate_sha256,
        'protocol_sha256': frozen['protocol_sha256'],
        'admitted_revision_count': len(scope),
        'request_parameters': dict(parameters),
        'timeout_owner': 'external_candidate_adapter_transport',
        'candidate_binding': 'caller_supplied_digest_and_scope_consistency',
        'attempted_ready': len(results),
    }
    return report
