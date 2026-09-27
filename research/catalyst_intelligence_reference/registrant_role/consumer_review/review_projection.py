"""Derived, research-only candidate for existing Special Situations consumers.

Consumes the CURRENT caller-scoped build_situations records after the narrow R15
mitigation. Creates no transaction, relationship identity, stored state or signal.
This is not an authenticated provider or an independently deployable service.
Consumers must preserve their existing entitlement and autoescape source text.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date
from typing import Any
from urllib.parse import urlsplit


class ReviewProjectionError(ValueError):
    """Invalid source/payload composition; never silently mint a relationship."""


def _text(v: Any) -> str | None:
    return v.strip() or None if isinstance(v, str) else None


def _source_url(v: Any) -> str | None:
    value = _text(v)
    if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme not in ('http', 'https') or not parts.hostname
                or parts.username is not None or parts.password is not None):
            return None
        return value
    except ValueError:
        return None


def project_relationship_review(records: Sequence[Mapping[str, Any]], *, as_of: str,
                                limit: int = 100) -> dict[str, Any]:
    """Select unresolved target-role evidence, without asserting it is affected.

    as_of is caller-provided display scope, NOT a historical possession receipt.
    Counts are source RECORDS, never independent transactions or investment bets.
    An unusable/missing source URL removes the link, not the research record.
    """
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ReviewProjectionError('invalid_limit')
    try:
        cutoff = date.fromisoformat(as_of)
    except (TypeError, ValueError):
        raise ReviewProjectionError('invalid_as_of') from None
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ReviewProjectionError('records_required')
    selected = []
    seen = set()
    for r in records:
        if not isinstance(r, Mapping):
            raise ReviewProjectionError('record_mapping_required')
        role = (_text(r.get('llm_role')) or '').lower()
        is_unresolved_gp = (_text(r.get('llm_category')) == 'Going-Private' and role != 'target')
        if is_unresolved_gp and r.get('status') == 'ok':
            raise ReviewProjectionError('classification_guard_required')
        if is_unresolved_gp and r.get('status') == 'defer' and (
                _text(r.get('category')) or _text(r.get('stage'))):
            raise ReviewProjectionError('withheld_direct_fields_not_cleared')
        if (r.get('status') != 'defer'
                or _text(r.get('llm_category')) != 'Going-Private' or role == 'target'):
            continue
        record_id = _text(r.get('id'))
        if not record_id:
            raise ReviewProjectionError('missing_source_record_id')
        if record_id in seen:
            raise ReviewProjectionError('duplicate_source_record_id')
        seen.add(record_id)
        raw_date = _text(r.get('date_filed'))
        if raw_date:
            try:
                source_date = date.fromisoformat(raw_date)
            except ValueError:
                raise ReviewProjectionError('invalid_source_date') from None
            if source_date > cutoff:
                raise ReviewProjectionError('future_source_date')
        selected.append({
            'source_record_id': record_id,
            'display_ticker': _text(r.get('ticker')),
            'display_company': _text(r.get('company')),
            'source_date': raw_date,
            'source_url': _source_url(r.get('source_url')),
            'source_summary': _text(r.get('summary')),
            'source_claim_category': 'Going-Private',
            'source_registrant_role': _text(r.get('llm_role')),
            'reason': 'registrant_target_not_established',
            'relation_status': 'unqualified',
            'direct_target_eligible': False,
            'affected_relationship_confirmed': False,
            'can_rank': False,
        })
    selected.sort(key=lambda r: r['source_record_id'])
    selected.sort(key=lambda r: r['source_date'] or '', reverse=True)
    return {'scope': 'derived_relationship_review_reference', 'as_of': as_of,
            'total_records': len(selected), 'shown_records': min(len(selected), limit),
            'truncated': len(selected) > limit, 'records': selected[:limit],
            'is_context_only': True, 'scored': False,
            'independent_event_count': None, 'relationship_binding': None}


def attach_relationship_review(payload: Mapping[str, Any],
                               records: Sequence[Mapping[str, Any]], *, as_of: str,
                               limit: int = 100) -> dict[str, Any]:
    """Attach to one freshly built snapshot/desk payload; never promote rows.

    The intended integration point is in the EXISTING engine after build_situations,
    before its existing publisher. The reference is not a new production wire schema.
    Never reuse a previously enriched payload or combine another source generation.
    """
    if payload.get('scored') is not False or payload.get('is_context_only') is not True:
        raise ReviewProjectionError('context_only_required')
    coverage = payload.get('coverage')
    if not isinstance(coverage, Mapping):
        raise ReviewProjectionError('coverage_required')
    if 'relationship_review' in payload or 'relationship_review_records' in coverage:
        raise ReviewProjectionError('fresh_payload_required')
    # Build the complete bounded source selection for cross-path leak checks.
    review = project_relationship_review(records, as_of=as_of, limit=limit)
    withheld_ids = {r.get('id') for r in records if r.get('status') == 'defer'
                    and _text(r.get('llm_category')) == 'Going-Private'
                    and (_text(r.get('llm_role')) or '').lower() != 'target'}
    if any(r.get('id') in withheld_ids for r in payload.get('situations', [])):
        raise ReviewProjectionError('direct_target_leak')
    out = deepcopy(dict(payload))
    n = review['total_records']
    if 'deferred_to_text_lane' in coverage:
        old = coverage['deferred_to_text_lane']
        if type(old) is not int or old < n:
            raise ReviewProjectionError('coverage_mismatch')
        out['coverage']['deferred_to_text_lane'] = old - n
    out['coverage']['relationship_review_records'] = n
    out['relationship_review'] = review
    return out
