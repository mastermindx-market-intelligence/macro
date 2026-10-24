"""REVIEW ONLY: explicit source discovery -> existing source-bound passage selector.

This is an integration proposal for the existing Brain/Vault owners, not a new
service, entitlement store, or runtime tool. Scope, connections, source bytes and
accounting are injected owner interfaces; tests use controlled stand-ins.
"""
from __future__ import annotations
import hashlib
import re

_SHA = re.compile(r'[0-9a-f]{64}\Z')
_QUERY_MAX = 256
_LIMIT_MAX = 8
_SOURCE_BYTE_MAX = 30_000_000


def _error(status):
    return {'status': status, 'items': [], 'passages': []}


def _scope(provider, purpose, corpus):
    """Validate shape, not entitlement. Only the owning adapter decides access."""
    try:
        value = provider(purpose)
    except Exception:
        return None, 'scope_unavailable'
    if not isinstance(value, dict):
        return None, 'scope_unavailable'
    if value.get('decision') == 'denied':
        return None, 'denied'
    if value.get('decision') != 'allowed':
        return None, 'scope_unavailable'
    if not isinstance(value.get('generation'), str) or not value['generation']:
        return None, 'scope_unavailable'
    items = value.get('items')
    if not isinstance(items, dict):
        return None, 'scope_unavailable'
    for rid, row in items.items():
        if not corpus.valid_doc_id(rid) or not isinstance(row, dict):
            return None, 'scope_unavailable'
        if not all(isinstance(row.get(k), str) and _SHA.fullmatch(row[k])
                   for k in ('pdf_sha256', 'body_sha256')):
            return None, 'scope_unavailable'
        cat = row.get('catalog')
        if not isinstance(cat, dict) or cat.get('id') != rid:
            return None, 'scope_unavailable'
    return value, None


def _row(conn, rid, corpus):
    columns = corpus._existing_columns(conn)
    selected = [f for f in corpus.EVIDENCE_DOCUMENT_FIELDS if f in columns]
    if not {'doc_id', 'body', 'content_sha256'}.issubset(selected):
        raise ValueError('Required source projection unavailable')
    row = conn.execute(f"SELECT {','.join(selected)} FROM documents WHERE doc_id=?", (rid,)).fetchone()
    return dict(row) if row else None


def _matches(row, expected):
    return (isinstance(row, dict) and isinstance(row.get('body'), str)
            and row.get('content_sha256') == expected['pdf_sha256']
            and hashlib.sha256(row['body'].encode('utf-8')).hexdigest() == expected['body_sha256'])


def _ticket_valid(ticket, corpus):
    return (isinstance(ticket, dict) and corpus.valid_doc_id(ticket.get('id'))
            and isinstance(ticket.get('query'), str) and 0 < len(ticket['query']) <= _QUERY_MAX
            and isinstance(ticket.get('generation'), str) and bool(ticket['generation'])
            and all(isinstance(ticket.get(k), str) and _SHA.fullmatch(ticket[k])
                    for k in ('pdf_sha256', 'body_sha256')))


def _current(ticket, scope):
    expected = scope['items'].get(ticket['id'])
    return (scope['generation'] == ticket['generation'] and expected is not None
            and all(expected[k] == ticket[k] for k in ('pdf_sha256', 'body_sha256')))


def discover(*, query, scope, limit=3, corpus, scope_provider, connection_factory):
    """Discover IDs in an explicitly admitted source-text scope; expose no body.

    A returned selection is a versioned reference, NEVER permission. Real Brain
    metadata mode stays with its existing owner; this function cannot widen it.
    """
    if scope != 'source_text':
        return _error('scope_not_selected')
    if (not isinstance(query, str) or len(query) > _QUERY_MAX or type(limit) is not int
            or not 1 <= limit <= _LIMIT_MAX):
        return _error('invalid_request')
    if not corpus.evidence_query_is_meaningful(query):
        return _error('query_too_short')
    admitted, error = _scope(scope_provider, 'discover_source_text', corpus)
    if error:
        return _error(error)
    base = {'status': 'ready', 'items': [], 'has_more': False,
            'search_surface': 'stored_corpus_text', 'complete_original_search': False,
            'generation': admitted['generation']}
    if not admitted['items']:
        return base
    conn = None
    try:
        conn = connection_factory()
        if conn is None or conn.in_transaction:
            return _error('search_unavailable')
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        # Existing R9 proposal: use the current owner-supplied set before LIMIT.
        hits = corpus.search(conn, query, limit=limit + 1,
                             eligible_ids=frozenset(admitted['items']), raise_on_error=True)
        base['has_more'] = len(hits) > limit
        for hit in hits[:limit]:
            rid = hit['id']; expected = admitted['items'][rid]
            row = _row(conn, rid, corpus)
            if not _matches(row, expected):
                return _error('source_mismatch')
            # Discovery is a candidate selection, not proof the question is answered.
            cat = expected['catalog']
            selection = {'id': rid, 'query': query, 'generation': admitted['generation'],
                         'pdf_sha256': expected['pdf_sha256'], 'body_sha256': expected['body_sha256']}
            base['items'].append({'id': rid, 'title': str(cat.get('title') or '')[:240],
                                  'institution': str(cat.get('institution') or '')[:160],
                                  'selection': selection})
        return base
    except Exception:
        return _error('search_unavailable')
    finally:
        if conn is not None:
            conn.close()


def read_selected(*, selection, corpus, scope_provider, connection_factory, source_reader, meter):
    """Revalidate a selected version, then reuse incumbent passage selection.

    The accounting callback is NOT implemented here. False means denied; an
    exception has unknown effect and is neither retried nor treated as free use.
    A production adapter must preserve the existing ledger's accepted policy.
    """
    if not _ticket_valid(selection, corpus):
        return _error('selection_invalid')
    admitted, error = _scope(scope_provider, 'read_source_evidence', corpus)
    if error:
        return _error(error)
    if not _current(selection, admitted):
        return _error('selection_stale')
    conn = None
    try:
        conn = connection_factory()
        if conn is None or conn.in_transaction:
            return _error('source_unavailable')
        conn.execute('PRAGMA query_only=ON');conn.execute('BEGIN')
        row = _row(conn, selection['id'], corpus)
        if not _matches(row, selection):
            return _error('source_mismatch')
        try:
            original = source_reader(selection['id'])
        except Exception:
            return _error('source_unavailable')
        if (not isinstance(original, bytes) or len(original) > _SOURCE_BYTE_MAX
                or not original.startswith(b'%PDF-')
                or hashlib.sha256(original).hexdigest() != selection['pdf_sha256']):
            return _error('source_mismatch')
        evidence = corpus.find_evidence_passages(row, selection['query'])
        if evidence['status'] != 'matched' or not evidence['passages']:
            return {'status': evidence['status'], 'passages': [],
                    'coverage': evidence['source_binding']['coverage'],
                    'complete_original_search': False}
        current, error = _scope(scope_provider, 'read_source_evidence', corpus)
        if error:
            return _error(error)
        if not _current(selection, current):
            return _error('selection_stale')
        try:
            allowed = meter(selection['id'])
        except Exception:
            # The callback might have debited. Keep uncertain; never repeat it.
            return _error('accounting_unknown')
        if allowed is not True:
            return _error('view_denied')
        # Accounting may have completed while access changed. Do not serve or
        # invent a refund; the real owner must reconcile any consumed allowance.
        final_scope, final_error = _scope(scope_provider, 'read_source_evidence', corpus)
        if final_error or not _current(selection, final_scope):
            return _error('access_changed_after_accounting')
        return {'status': 'matched', 'report_id': selection['id'],
                'source_binding': evidence['source_binding'], 'passages': evidence['passages'],
                'note': 'Literal support in the captured text layer, not proof of a financial thesis or full visual coverage.'}
    except Exception:
        return _error('source_unavailable')
    finally:
        if conn is not None:
            conn.close()
