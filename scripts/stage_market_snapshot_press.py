"""Explicit private staging of one reviewed native market snapshot.

No ordinary selection, producer, reconciliation, emit or new accounting store.
Calling principal owns the separate attempt/allocation decision. One adapter
invocation is not a hard actual-spend cap or one upstream CLI request.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from engine.press import desk_planner as P, writer
from engine.press.issuer_release_candidate import _bound
from engine.press.market_snapshot_candidate import plan_market_snapshot_candidate
from scripts.run_press import _annotate, _env_int, _stage_preplanned_slots
from scripts.stage_official_feed_press import _accounting_rows, _brief_attempts_today, _canonical_paths

STAGE_RAIL = 'private_market_snapshot'


def _exclusions(path, digest):
    """Read the incumbent exclusions snapshot; never create or rewrite it."""
    obj = json.loads(_bound(path, digest, 1_000_000))
    if not isinstance(obj, dict):
        raise ValueError('existing source exclusions object required')
    result = []
    for key in ('held_refs', 'covered_refs_separate_from_holds'):
        rows = obj.get(key)
        if not isinstance(rows, list) or any(not isinstance(r, str) or not r for r in rows):
            raise ValueError('existing source exclusions refs malformed')
        result.append(set(rows))
    return result


def _same_source(row, plan):
    slot = row.get('slot') or {}
    if not isinstance(slot, dict) or not isinstance(slot.get('primary_source') or {}, dict):
        raise ValueError('malformed staged market source identity')
    refs = set(row.get('sources', [])) | set(row.get('seed_refs', []))
    refs.add((slot.get('primary_source') or {}).get('ref'))
    return row['id'] == plan['candidate_id'] or bool(refs & {plan['source_ref'], plan['snapshot_ref']})


def _adjudicated_context_refs(plan, paths, exclusions_sha256):
    """Resolve only exact reviewed historical-context scope; never edit holds."""
    value = plan.get('historical_context_adjudication')
    if value is None:
        return set()
    if value['exclusions_sha256'] != exclusions_sha256:
        raise ValueError('adjudication exclusions snapshot mismatch')
    historical = value['historical_stage']
    # The candidate parser already restricts this to the original safe stage ID.
    path = paths['staging'] / (historical['id'] + '.json')
    obj = json.loads(_bound(path, historical['sha256'], 2_000_000))
    refs = {row['ref'] for row in value['artifacts']}
    if (not isinstance(obj, dict) or obj.get('id') != historical['id']
            or obj.get('sources') != ['chronicle:TTWO-BULL-20261007']
            or not isinstance(obj.get('slot'), dict)
            or not isinstance(obj['slot'].get('primary_source'), dict)
            or obj['slot']['primary_source'].get('ref') != 'chronicle:TTWO-BULL-20261007'
            or not isinstance(obj.get('seed_refs'), list)
            or any(not isinstance(ref, str) for ref in obj['seed_refs'])
            or not refs <= set(obj['seed_refs'])):
        raise ValueError('historical draft identity or context provenance mismatch')
    return refs


def stage_market_snapshot_candidate(root, cfg, *, qualification_path, qualification_sha256,
                                    exclusions_path, exclusions_sha256, now=None):
    """Requalify current sources and all ordinary accounting before one attempt.

    Tests may supply a clock; the CLI cannot. Original peers stay in the normal
    staging tree and existing writer/provider accounting is reused unchanged.
    """
    root = Path(root).resolve()
    if cfg != P.load_config(root):
        raise ValueError('current canonical Press config required')
    paths = _canonical_paths(root, cfg)
    staged, ledger = _accounting_rows(paths)
    moment = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise ValueError('timezone-qualified current staging instant required')
    moment = moment.astimezone(timezone.utc)
    held, covered = _exclusions(exclusions_path, exclusions_sha256)
    plan = plan_market_snapshot_candidate(root=root, cfg=cfg, as_of=moment.isoformat(),
        qualification_path=qualification_path, qualification_sha256=qualification_sha256)
    refs = {plan['source_ref'], plan['snapshot_ref']}
    context_refs = {f['ref'] for f in plan['validation_context']['facts']}
    identity = {'candidate_id': plan['candidate_id'], 'staged_slot_id': plan['candidate_id'],
                'source_ref': plan['source_ref'], 'snapshot_ref': plan['snapshot_ref'],
                'source_revisions': plan['source_revisions']}
    def refuse(reason):
        _annotate('warning', 'press_market_stage_refused', reason)
        return {'staged': False, 'reason': reason, 'rail': STAGE_RAIL,
                'public_article_approved': False, 'allow_emit': False, **identity}
    adjudicated = _adjudicated_context_refs(plan, paths, exclusions_sha256)
    if refs & held or (context_refs & held) - adjudicated or refs & covered:
        return refuse('existing source hold or primary coverage; no alias/replay')
    if plan['blocked_by_existing_coverage'] or any(_same_source(r, plan) for r in staged + ledger):
        return refuse('existing source coverage or original attempt; replay refused')
    checkpoint = paths['staging'] / (plan['candidate_id'] + '.json')
    if checkpoint.exists():
        return refuse('existing immutable checkpoint; reconcile original operation')
    used, ceiling = _brief_attempts_today(staged, ledger, plan['as_of'], plan['cadence_per_day'])
    if used >= ceiling:
        return refuse('daily Brief attempt cadence reached')
    desk = cfg['desks']['brief']
    slot = dict(plan['validation_context'])
    slot.update(id=plan['candidate_id'], cluster=desk.get('cluster', 'market-brief'),
                model_key=desk.get('model_key', 'press_brief'),
                sources=sorted(refs), source_revisions=plan['source_revisions'],
                seed_refs=sorted(context_refs),
                story={'kind': 'native_market_snapshot', 'event_date': plan['observation_date'],
                       'title_hint': 'Dated market measurements', 'tickers': []},
                chronicle_context={'lines': [], 'narratives': [], 'budget_used': 0},
                slug_hint='market-' + plan['candidate_id'].removeprefix('press-market-'))
    receipt = {'rail': STAGE_RAIL, 'authorized_by': 'calling_principal',
               'private_staging_only': True, 'public_article_approved': False,
               'qualification_sha256': qualification_sha256, 'exclusions_sha256': exclusions_sha256,
               'observation_date': plan['observation_date'], 'planned_at': moment.isoformat(), **identity}
    if 'historical_context_adjudication' in plan:
        receipt['historical_context_adjudication'] = plan['historical_context_adjudication']
    llm = cfg.get('llm') or {}
    state = writer.RunState(token_budget=_env_int('PRESS_RUN_TOKEN_BUDGET',
        int(llm.get('run_token_budget') or 240_000)), breaker_threshold=_env_int(
        'PRESS_CIRCUIT_BREAKER_FAILURES', int(llm.get('circuit_breaker_consecutive_failures') or 3)))
    _, published_slugs = P.published_refs(root, cfg)
    _, staged_slugs = P.staged_refs(root, cfg)
    taken = P.taken_slugs(root) | published_slugs | staged_slugs

    def prepare(original):
        # Same reviewed bytes and real clock at the last existing preparation
        # boundary. No new hard token cap or provider retry behavior is added.
        current = now if now is not None else datetime.now(timezone.utc)
        if cfg != P.load_config(root):
            raise ValueError('Press config changed before writer')
        _exclusions(exclusions_path, exclusions_sha256)
        fresh = plan_market_snapshot_candidate(root=root, cfg=cfg, as_of=current.isoformat(),
            qualification_path=qualification_path, qualification_sha256=qualification_sha256)
        _adjudicated_context_refs(fresh, paths, exclusions_sha256)
        if fresh['source_revisions'] != plan['source_revisions'] or fresh['as_of'] != plan['as_of']:
            raise ValueError('market packet changed before writer')
        return original

    try:
        summary = _stage_preplanned_slots(root, cfg, slots=[slot], staging_dir=paths['staging'],
            run_date=plan['as_of'], state=state, max_regenerations=0, taken_slugs=taken,
            admission_receipt=receipt, single_provider_attempt=True, prepare_slot=prepare)
    except Exception as exc:
        _annotate('error', 'press_market_effect_unknown', f'{slot["id"]}: {type(exc).__name__}; never replay')
        return {'staged': None, 'effect_unknown': True, 'status': 'effect_unknown',
                'original_slot_id': slot['id'], 'checkpoint_path': str(checkpoint.relative_to(root)),
                'checkpoint_observed': checkpoint.exists(), 'retry_allowed': False,
                'exception_type': type(exc).__name__, 'rail': STAGE_RAIL,
                'public_article_approved': False, 'allow_emit': False, **identity}
    return {'staged': True, 'summary': summary, 'rail': STAGE_RAIL,
            'public_article_approved': False, 'allow_emit': False, **identity}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('qualification', 'exclusions'):
        ap.add_argument('--' + name, required=True)
        ap.add_argument('--' + name + '-sha256', required=True)
    ap.add_argument('--root', default=str(_REPO))
    ap.add_argument('--confirm-private-staging', action='store_true')
    args = ap.parse_args(argv)
    if not args.confirm_private_staging:
        ap.error('separate calling-principal private staging authorization required')
    root = Path(args.root)
    try:
        result = stage_market_snapshot_candidate(root, P.load_config(root),
            qualification_path=args.qualification, qualification_sha256=args.qualification_sha256,
            exclusions_path=args.exclusions, exclusions_sha256=args.exclusions_sha256)
    except (ValueError, OSError) as exc:
        _annotate('warning', 'press_market_stage_refused', str(exc))
        result = {'staged': False, 'reason': str(exc), 'rail': STAGE_RAIL,
                  'public_article_approved': False, 'allow_emit': False}
    print(json.dumps(result, indent=2, default=str))
    return 0 if result['staged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
