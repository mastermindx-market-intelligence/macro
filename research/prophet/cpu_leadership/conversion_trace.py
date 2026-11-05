"""Read-only diagnostic of existing Door sightings and canonical episode retention.

Research output only. Never reconciles, writes, repairs, or originates an episode/plan.
Only the canonical HEAD snapshot validator may supply durable event facts. A same-ticker
plan is not a causal conversion, and a dated research flag is not a tradable entry.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engine.us_candidate_episode import canonical_json, load_candidate_episode_store_snapshot


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('a UTC timestamp ending in Z is required')
    parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    if parsed.tzinfo is None:
        raise ValueError('timestamp must be timezone-aware')
    return parsed.astimezone(timezone.utc)


def trace_sightings(
    flags: Sequence[Mapping[str, Any]], *,
    events: Sequence[Mapping[str, Any]], suppressions: Sequence[Mapping[str, Any]],
    generation_recorded_at: str, as_of: str,
) -> dict[str, Any]:
    """Exact source-key AND payload-receipt join; no ticker-only attribution.

    Absence is scoped to the selected generation. A legacy flag's date alone does
    not prove its first publication time. A recorded observation is not an entry.
    Callers loading durable state must first use the owner's snapshot validator.
    """
    cutoff, generated = _utc(as_of), _utc(generation_recorded_at)
    if generated > cutoff:
        raise ValueError('selected generation was recorded after the requested cutoff')
    by_source: dict[tuple[str, str, str], tuple[str, Mapping[str, Any]]] = {}
    for kind, records in [('event_recorded', events), ('suppression_recorded', suppressions)]:
        for record in records:
            key = tuple(record.get(field) for field in ('source_system', 'source_schema', 'source_event_id'))
            if key[0] != 'doors':
                continue
            if not all(isinstance(part, str) and part for part in key):
                raise ValueError('malformed source key')
            if key in by_source:
                raise ValueError('duplicate source ownership')
            by_source[key] = (kind, record)
    rows = []
    seen: set[tuple[str, str, str]] = set()
    for flag in flags:
        if not isinstance(flag, Mapping) or flag.get('schema') != 'prophet_doors/v1':
            raise ValueError('unsupported sighting schema')
        session = date.fromisoformat(str(flag.get('date')))
        if session.isoformat() != flag.get('date'):
            raise ValueError('invalid sighting date')
        if session > cutoff.date():
            continue
        ticker, door = flag.get('ticker'), flag.get('door')
        if not isinstance(ticker, str) or not ticker or door not in ('T', 'R', 'W'):
            raise ValueError('invalid sighting identity')
        source_id = f'doors:{session.isoformat()}:{door}:{ticker}'
        key = ('doors', 'prophet_doors/v1', source_id)
        if key in seen:
            raise ValueError('duplicate sighting identity')
        seen.add(key)
        receipt = 'sha256:' + sha256(canonical_json(dict(flag)).encode('utf-8')).hexdigest()
        output = dict(ticker=ticker, door=door, observation_session=session.isoformat(),
                      source_event_id=source_id, source_receipt=receipt,
                      status='no_record_in_selected_generation', episode_id=None,
                      reason=None, first_publication_verified=False,
                      live_entry_proven=False)
        found = by_source.get(key)
        if found:
            kind, record = found
            times = [record.get(field) for field in ('known_at', 'recorded_at') if record.get(field)]
            if any(_utc(value) > cutoff for value in times):
                output['status'] = 'record_after_cutoff'
            elif record.get('source_receipt') != receipt:
                output['status'] = 'source_receipt_mismatch'
            else:
                output.update(status=kind, episode_id=record.get('episode_id'),
                              reason=record.get('reason'),
                              known_at=record.get('known_at'), recorded_at=record.get('recorded_at'))
        elif generated.date() < session:
            output['status'] = 'generation_predates_sighting'
        rows.append(output)
    return dict(method='exact source identity and payload receipt against validated episode generation',
                cutoff=as_of, generation_recorded_at=generation_recorded_at,
                counts=dict(Counter(row['status'] for row in rows)), rows=rows,
                trade_conversion_proven=False, entry_authority_changed=False,
                limitations=['Dates on flags do not prove first publication time.',
                             'No record means absent from this generation, not never observed.',
                             'Episode retention is neither plan origination nor trade execution.'])


def published_plan_presence(book: Mapping[str, Any], tickers: Sequence[str]) -> dict[str, Any]:
    """Current published-plan presence only; no historical absence or causal claim."""
    if book.get('schema') != 'prophet.index/v1' or not isinstance(book.get('plans'), list):
        raise ValueError('published plan index unavailable or wrong schema')
    if any(not isinstance(plan, Mapping) or not isinstance(plan.get('asset'), str)
           for plan in book['plans']):
        raise ValueError('malformed published plan population')
    return dict(asof=book.get('asof'), source_asof=book.get('source_asof'),
                recorded_at=book.get('recorded_at'), total=len(book['plans']),
                declared_plan_count=book.get('plan_count'),
                by_ticker={ticker: [plan.get('id') for plan in book['plans']
                                   if plan['asset'] == ticker] for ticker in tickers},
                relation='ticker co-occurrence only; no causal sighting-to-plan link',
                historical_trade_absence_proven=False)


def _read_blob(ref: str, path: str, receipts: list[dict[str, str]]) -> bytes:
    payload = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'])
    receipts.append({'path': path, 'sha256': sha256(payload).hexdigest()})
    return payload


def read_pinned_episode_snapshot(ref: str, receipts: list[dict[str, str]]):
    """Materialize exactly HEAD's generation privately, then invoke its owner reader."""
    store = 'data/us_prophet_rank/episodes'
    head_bytes = _read_blob(ref, store + '/HEAD.json', receipts)
    head = json.loads(head_bytes)
    generation = head.get('generation_id')
    if not isinstance(generation, str) or not re.fullmatch(r'peg:[0-9a-f]{64}', generation):
        raise ValueError('invalid generation identity')
    prefix = store + '/generations/' + generation + '/'
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only',
                                     ref, '--', prefix], text=True).splitlines()
    if not paths or len(paths) > 64:
        raise ValueError('missing generation or generation exceeds diagnostic file bound')
    with tempfile.TemporaryDirectory(prefix='prophet-episode-read-') as scratch:
        root = Path(scratch)
        (root / 'HEAD.json').write_bytes(head_bytes)
        total = 0
        for path in paths:
            if not path.startswith(prefix) or '..' in Path(path).parts:
                raise ValueError('invalid generation member path')
            data = _read_blob(ref, path, receipts)
            total += len(data)
            if total > 128 * 1024 * 1024:
                raise ValueError('generation exceeds diagnostic byte bound')
            destination = root / Path(path).relative_to(store)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        return load_candidate_episode_store_snapshot(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_ref):
        parser.error('source-ref must be an immutable commit')
    start = date.fromisoformat(args.start); cutoff = _utc(args.as_of)
    if start > cutoff.date():
        parser.error('start must not follow cutoff')
    sources: list[dict[str, str]] = []
    for path in ['engine/us_candidate_episode.py', 'engine/us_candidate_episode_intake.py',
                 'engine/stock_identity/fingerprint.py', 'lib/dataos/identity.py']:
        if (ROOT / path).read_bytes() != _read_blob(args.source_ref, path, sources):
            raise ValueError(f'owner code differs from pinned source: {path}')
    flags = [json.loads(line) for line in _read_blob(
        args.source_ref, 'data/prophet_doors/flags.jsonl', sources).splitlines() if line.strip()]
    selected = [flag for flag in flags if flag.get('date', '') >= args.start]
    snapshot = read_pinned_episode_snapshot(args.source_ref, sources)
    generation = snapshot.generation
    report = trace_sightings(selected, events=generation.events, suppressions=generation.suppressions,
                            generation_recorded_at=str(generation.receipt['recorded_at']),
                            as_of=args.as_of)
    report.update(source_ref=args.source_ref, generation_id=snapshot.generation_id,
                  generation_validation='canonical HEAD reader passed', sources=sources,
                  source_scope='listed owner bytes matched; not complete historical-runtime replay',
                  source_counts=generation.receipt.get('source_counts'),
                  episode_counts=dict(Counter(row['episode_state'] for row in generation.episodes)))
    book = json.loads(_read_blob(args.source_ref, 'site/prophet/index.json', sources))
    report['published_plan_presence'] = published_plan_presence(
        book, sorted({flag['ticker'] for flag in selected} | {'AMD', 'INTC', 'ARM', 'MU'}))
    report['published_plan_presence']['scope'] = 'published index at source pin; not a historical plan replay'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: report[key] for key in ['source_ref', 'generation_id',
          'generation_recorded_at', 'counts', 'source_counts', 'episode_counts']}, indent=2))
    print(json.dumps([row for row in report['rows'] if row['ticker'] in ('AMD', 'INTC', 'ARM', 'MU')], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
