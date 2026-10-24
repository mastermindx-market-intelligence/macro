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
    if not isinstance(q, dict) or set(q) != _FIELDS:
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
    source_ref = f'market_snapshot:{observed}:{prop}'
    selection_key = json.dumps(sorted((f['ref'], f['id']) for f in facts), separators=(',', ':'))
    snapshot_ref = f'market_snapshot_inputs:{observed}:{P.story_key(selection_key)}'
    refs = {source_ref, snapshot_ref}
    published, _ = P.published_refs(root, cfg)
    staged, _ = P.staged_refs(root, cfg)
    revisions = dict(revisions)
    revisions[source_ref] = 'sha256:' + qualification_sha256
    return {
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
