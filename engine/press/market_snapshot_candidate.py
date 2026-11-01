"""Opt-in, hash-bound native market measurements; never selection or writing.

A reviewed proposition and the incumbent extractor facts are the entire input.
Candidate qualification grants neither an attempt nor publication authority.
"""
from __future__ import annotations

import json
import re
from datetime import date

from engine.press import desk_planner as P
from engine.press.external_candidate import _instant, _reviewed_context
from engine.press.issuer_release_candidate import _bound

_FIELDS = frozenset({
    'schema', 'proposition_id', 'observation_date', 'first_party_context',
    'review_result', 'allow_stage', 'allow_emit', 'publication_approved',
})
_ADJUDICATION = 'historical_context_adjudication'
_CONTEXT_IDS = {
    'artifact:data/market_state/latest.json': frozenset({
        'market_state_score', 'market_state_risk', 'market_state_breadth'}),
    'artifact:site/basketdata/breadth_split.json': frozenset({'breadth_split'}),
    'artifact:site/basketdata/fear_greed.json': frozenset({'fear_greed'}),
}


def _context_adjudication(value, q, facts, revisions):
    """Validate explicit caller-reviewed scope, not a new authority credential.

    The qualification's existing hash/calling-principal custody owns the actual
    decision. This optional record cannot release a primary source, another
    artifact, a later revision or the historical draft itself.
    """
    fields = {'schema', 'decision', 'adjudication_ref', 'exclusions_sha256',
              'proposition_id', 'observation_date', 'purpose', 'historical_stage', 'artifacts'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('historical context adjudication fields mismatch')
    if (value['schema'] != 'press.market_context_hold_adjudication.v1'
            or value['decision'] != 'historical_context_no_replay_only_for_bound_snapshot'
            or value['purpose'] != 'dated_market_participation_analysis'
            or value['proposition_id'] != q['proposition_id']
            or value['proposition_id'] != 'participation-distribution'
            or value['observation_date'] != q['observation_date']):
        raise ValueError('historical context adjudication scope mismatch')
    if (not isinstance(value['adjudication_ref'], str)
            or not value['adjudication_ref'].strip() or len(value['adjudication_ref']) > 2000):
        raise ValueError('explicit context adjudication reference required')
    def digest(v):
        return isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v)
    historical = value['historical_stage']
    if (not digest(value['exclusions_sha256']) or not isinstance(historical, dict)
            or set(historical) != {'id', 'sha256'}
            or historical['id'] != 'press-brief-2026-10-11-6cf53bdfd11a'
            or not digest(historical['sha256'])):
        raise ValueError('exact historical draft and exclusions binding required')
    rows = value['artifacts']
    if not isinstance(rows, list) or len(rows) != len(_CONTEXT_IDS):
        raise ValueError('exact three adjudicated context artifacts required')
    actual = {}
    for fact in facts:
        actual.setdefault(fact['ref'], set()).add(fact['id'])
    if actual != _CONTEXT_IDS:
        raise ValueError('selected context facts differ from adjudicated scope')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'ref', 'sha256', 'fact_ids'}:
            raise ValueError('adjudicated artifact fields mismatch')
        ref = row['ref']
        if not isinstance(ref, str) or ref not in _CONTEXT_IDS or ref in seen:
            raise ValueError('unexpected or duplicate adjudicated artifact')
        ids = row['fact_ids']
        if (not digest(row['sha256']) or revisions.get(ref) != 'sha256:' + row['sha256']
                or not isinstance(ids, list) or any(not isinstance(i, str) for i in ids)
                or len(ids) != len(set(ids)) or set(ids) != _CONTEXT_IDS[ref]):
            raise ValueError('adjudicated revision or fact IDs mismatch')
        seen.add(ref)
    # A detached copy stays metadata, never facts or writer instructions.
    return json.loads(json.dumps(value))


def plan_market_snapshot_candidate(*, qualification_path, qualification_sha256,
                                   root, as_of, cfg=None):
    """Qualify selected existing measurements at the supplied UTC cutoff.

    No producer, ordinary planner, rank, pool or cadence mutation. Proposition
    identity is stable across invocation dates and input revisions. A second
    identity binds the dated measurement selection so renaming a proposition
    cannot replay the same snapshot under another label.
    """
    cfg = cfg if cfg is not None else P.load_config(root)
    if (not isinstance(cfg, dict) or not isinstance(cfg.get('desks'), dict)
            or not isinstance(cfg['desks'].get('brief'), dict)):
        raise ValueError('valid Brief config required')
    desk = cfg['desks']['brief']
    if not isinstance(as_of, str):
        raise ValueError('timezone-qualified current instant required')
    moment = _instant(as_of)
    q = json.loads(_bound(qualification_path, qualification_sha256, 100_000))
    if not isinstance(q, dict) or set(q) not in (_FIELDS, _FIELDS | {_ADJUDICATION}):
        raise ValueError('market qualification fields mismatch')
    if (q['schema'] != 'press.market_snapshot_qualification.v1'
            or q['review_result'] != 'accepted_as_market_candidate_only'
            or any(q[k] is not False for k in ('allow_stage', 'allow_emit', 'publication_approved'))):
        raise ValueError('market qualification is candidate-only')
    prop = q['proposition_id']
    if not isinstance(prop, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', prop) or len(prop) > 64:
        raise ValueError('safe proposition identity required')
    observed = q['observation_date']
    if not isinstance(observed, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', observed):
        raise ValueError('calendar observation date required')
    date.fromisoformat(observed)
    facts, revisions = _reviewed_context(q['first_party_context'], root=root,
        as_of=moment.date(), window_days=int(desk.get('window_days') or 3))
    if observed != max(f['dated'] for f in facts):
        raise ValueError('observation date must equal latest selected fact date')
    adjudication = (_context_adjudication(q[_ADJUDICATION], q, facts, revisions)
                    if _ADJUDICATION in q else None)
    source_ref = f'market_snapshot:{observed}:{prop}'
    selection_key = json.dumps(sorted((f['ref'], f['id']) for f in facts), separators=(',', ':'))
    snapshot_ref = f'market_snapshot_inputs:{observed}:{P.story_key(selection_key)}'
    refs = {source_ref, snapshot_ref}
    published, _ = P.published_refs(root, cfg)
    staged, _ = P.staged_refs(root, cfg)
    revisions = dict(revisions)
    revisions[source_ref] = 'sha256:' + qualification_sha256
    result = {
        'operation': 'planning_only', 'candidate_id': 'press-market-' + P.story_key(source_ref),
        'source_ref': source_ref, 'snapshot_ref': snapshot_ref,
        'observation_date': observed, 'as_of': moment.date().isoformat(),
        'source_revisions': revisions,
        'blocked_by_existing_coverage': bool(refs & (published | staged)),
        'cadence_per_day': int(desk.get('cadence_per_day') or 1),
        'allow_stage': False, 'allow_emit': False, 'publication_approved': False,
        'cadence_consumed': False,
        'validation_context': {
            'desk': 'brief', 'publication': desk.get('publication', 'flagship'),
            'byline': desk.get('byline', 'The Brief'), 'as_of': moment.date().isoformat(),
            'min_words': int(desk.get('min_words') or 300),
            'max_words': int(desk.get('max_words') or 600),
            'min_anchored_receipts': int(desk.get('min_anchored_receipts') or 0),
            'facts': facts,
            'primary_source': {'kind': 'first_party', 'name': 'Mastermind market measurements',
                               'url': None, 'ref': source_ref},
            'allowed_links': [],
            'raw_documents': [{'ref': f['ref'], 'text': f['text']} for f in facts],
        },
    }
    if adjudication is not None:
        result[_ADJUDICATION] = adjudication
    return result
