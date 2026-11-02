"""Explicit private staging for a separately authorized retained issuer candidate.

Not called by ordinary selection. Candidate/source qualification is not writer
authority; CLI confirmation records the principal's separate private invocation.
No emit, import, reconciliation or producer. One Press adapter invocation does
not guarantee one upstream CLI request or hard-cap actual provider usage.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from engine.press import desk_planner as P, validators, writer
from scripts.run_press import _annotate, _env_int, _stage_preplanned_slots
from scripts.stage_official_feed_press import (
    _accounting_rows, _brief_attempts_today, _canonical_paths,
)

STAGE_RAIL = 'private_issuer_release'


def _slot_id(plan):
    # Stable across changed retained bytes, reviews and invocation dates.
    return 'press-issuer-' + P.story_key(plan['source_ref'])


def _same_source(row, plan):
    refs = set(row.get('sources', [])) | set(row.get('seed_refs', []))
    slot = row.get('slot') or {}
    if not isinstance(slot, dict) or not isinstance(slot.get('primary_source') or {}, dict):
        raise ValueError('malformed staged source identity')
    primary = slot.get('primary_source') or {}
    return (row['id'] == _slot_id(plan) or plan['source_ref'] in refs
            or primary.get('url') == plan['source_url'])


def stage_issuer_release_candidate(root, cfg, *, document_path, document_sha256,
                                   qualification_path, qualification_sha256,
                                   retrieval_path, retrieval_sha256, now=None):
    """Requalify at real time, then use the incumbent exclusive checkpoint rail.

    Caller must separately hold private staging authority. Tests may inject a
    clock; no CLI clock exists. Public publication stays refused regardless of
    mutable staging approval fields. No automatic fallback or regeneration.
    """
    root = Path(root).resolve()
    desks = cfg.get('desks') if isinstance(cfg, dict) else None
    if not isinstance(desks, dict) or not isinstance(desks.get('brief'), dict):
        raise ValueError('config/press.yml is missing or invalid for the Brief desk')
    paths = _canonical_paths(root, cfg)
    staged, ledger = _accounting_rows(paths)
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError('private staging clock must carry a timezone')
    plan = P.plan_external_candidate(
        source_kind='sec_issuer_release', root=root, cfg=cfg, as_of=moment.isoformat(),
        document_path=document_path, document_sha256=document_sha256,
        qualification_path=qualification_path, qualification_sha256=qualification_sha256,
        retrieval_path=retrieval_path, retrieval_sha256=retrieval_sha256)
    context = plan['validation_context']
    identity = {'candidate_id': plan['candidate_id'], 'staged_slot_id': _slot_id(plan),
                'source_ref': plan['source_ref'], 'source_revisions': plan['source_revisions'],
                'qualification_sha256': qualification_sha256}
    def refuse(reason):
        _annotate('warning', 'press_issuer_stage_refused', f'issuer private staging refused: {reason}')
        return {'staged': False, 'reason': reason, 'rail': STAGE_RAIL,
                'public_article_approved': False, 'allow_emit': False, **identity}
    # Issuer facts/derived quantities NEVER acquire first-party credit. A
    # structurally valid external-only candidate can still fail live admission.
    available = {n for n, tier in validators.fact_tier_index(context)
                 if tier == 'first_party' and math.isfinite(n)}
    minimum = int(context.get('min_anchored_receipts')
                  or (cfg.get('validators') or {}).get('min_anchored_receipts') or 0)
    if len(available) < minimum or not available:
        return refuse('insufficient relevant reviewed first-party context for incumbent own-value/receipt gate')
    # Numeric availability is necessary, never proof of 40% sentence attribution
    # or editorial relevance. The unchanged validators and principal judge both.
    if plan['blocked_by_existing_coverage'] or any(_same_source(r, plan) for r in staged + ledger):
        return refuse('existing source coverage or attempt; replay refused')
    slot_path = paths['staging'] / (_slot_id(plan) + '.json')
    if slot_path.exists():
        return refuse('existing immutable slot checkpoint; replay refused')
    used, ceiling = _brief_attempts_today(staged, ledger, context['as_of'], plan['cadence_per_day'])
    if used >= ceiling:
        return refuse('daily Brief attempt cadence reached')
    slot = dict(context)
    desk = cfg['desks']['brief']
    slot.update(id=_slot_id(plan), cluster=desk.get('cluster', 'market-brief'),
                model_key=desk.get('model_key', 'press_brief'), sources=[plan['source_ref']],
                source_revisions=plan['source_revisions'],
                seed_refs=sorted({f['ref'] for f in context['facts'] if f.get('ref')}),
                story={'kind': 'issuer_release', 'event_date': plan['source_clocks']['event_date']},
                chronicle_context={'lines': [], 'narratives': [], 'budget_used': 0},
                slug_hint='issuer-' + _slot_id(plan).removeprefix('press-issuer-'))
    receipt = {'rail': STAGE_RAIL, 'authorized_by': 'calling_principal',
               'private_staging_only': True, 'public_article_approved': False,
               'source_clocks': plan['source_clocks'], 'rights_basis': plan['rights_basis'],
               'source_url': plan['source_url'], 'planned_at': moment.isoformat(), **identity}
    llm = cfg.get('llm') or {}
    state = writer.RunState(
        token_budget=_env_int('PRESS_RUN_TOKEN_BUDGET', int(llm.get('run_token_budget') or 240_000)),
        breaker_threshold=_env_int('PRESS_CIRCUIT_BREAKER_FAILURES', int(llm.get('circuit_breaker_consecutive_failures') or 3)))
    _, published_slugs = P.published_refs(root, cfg)
    _, staged_slugs = P.staged_refs(root, cfg)
    taken = P.taken_slugs(root) | published_slugs | staged_slugs
    try:
        summary = _stage_preplanned_slots(root, cfg, slots=[slot], staging_dir=paths['staging'],
            run_date=context['as_of'], state=state, max_regenerations=0,
            taken_slugs=taken,
            admission_receipt=receipt, single_provider_attempt=True)
    except Exception as exc:
        # The same exception class can describe a source refusal BEFORE this
        # rail or a provider/validation failure AFTER its exclusive checkpoint.
        # After entering it, report uncertainty on that original identity.
        # A missing/unreadable checkpoint cannot prove no effect. Do not
        # relabel it as refused, edit it, retry or fail over.
        reason = f'{type(exc).__name__} inside original staging rail; reconcile original operation, never replay'
        _annotate('error', 'press_issuer_effect_unknown', f'{slot["id"]}: {reason}')
        return {'staged': None, 'status': 'effect_unknown', 'effect_unknown': True,
                'original_slot_id': slot['id'], 'checkpoint_path': str(slot_path.relative_to(root)),
                'checkpoint_observed': slot_path.exists(),
                'retry_allowed': False, 'reason': reason, 'exception_type': type(exc).__name__,
                'rail': STAGE_RAIL, 'public_article_approved': False, 'allow_emit': False, **identity}
    _annotate('notice', 'press_issuer_staged', f'issuer candidate staged PRIVATELY: {plan["candidate_id"]}; no public approval')
    return {'staged': True, 'rail': STAGE_RAIL, 'public_article_approved': False,
            'allow_emit': False, 'summary': summary, **identity}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('document', 'qualification', 'retrieval'):
        ap.add_argument('--' + name, required=True)
        ap.add_argument('--' + name + '-sha256', required=True)
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument('--confirm-private-staging', action='store_true')
    args = ap.parse_args(argv)
    if not args.confirm_private_staging:
        ap.error('separate calling-principal private staging authorization required')
    root = Path(args.root)
    inputs = {name + suffix: getattr(args, name + suffix) for name in ('document', 'qualification', 'retrieval')
              for suffix in ('_sha256',)}
    inputs.update({name + '_path': getattr(args, name) for name in ('document', 'qualification', 'retrieval')})
    try:
        result = stage_issuer_release_candidate(root, P.load_config(root), **inputs)
    except ValueError as exc:
        _annotate('warning', 'press_issuer_stage_refused', str(exc))
        result = {'staged': False, 'rail': STAGE_RAIL, 'reason': str(exc),
                  'public_article_approved': False, 'allow_emit': False}
    except FileExistsError:
        # Another caller can win the incumbent exclusive checkpoint after the
        # pre-read. It may be live: retain its identity, never retry or alias it.
        reason = 'existing immutable checkpoint; reconcile original operation, never replay'
        _annotate('warning', 'press_issuer_stage_refused', reason)
        result = {'staged': False, 'rail': STAGE_RAIL, 'reason': reason,
                  'public_article_approved': False, 'allow_emit': False}
    print(json.dumps(result, indent=2, default=str))
    return 0 if result['staged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
