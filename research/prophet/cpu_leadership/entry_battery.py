"""Time-cut acceptance-case battery over EXISTING Prophet entry constructions.

Research only: no new detector, scorer, entry permission, ledger or market-data read.
The CLI reads immutable Git blobs and writes only the explicitly requested report.
Prices are a pinned adjusted-history vintage, not proof of historical availability.
Each session is evaluated on its own prefix. Mutable contextual washout waivers and
historical event-latch state are deliberately NOT reconstructed from today's files.
Recorded Door sightings stay separate from technical replay and executed entries.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_GATE_FIELDS = ('eligible', 'tier_cascade', 'ticks', 'reason', 'above200',
                'weekly_bull', 'provisional', 'bars_to_cross')


def _day(value: str) -> pd.Timestamp:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError('expected an ISO session date')
    return pd.Timestamp(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if hasattr(value, 'item'):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _technical_gate(ticker: str, prefix: pd.Series) -> dict:
    from engine import signal_gate
    return signal_gate.gate(ticker, prefix, washout_waiver=False)


def _rearm(verdict: dict, prefix: pd.Series) -> dict:
    from engine import prophet_doors
    return prophet_doors.door_r_legs(verdict, prefix)


def evaluate_prefixes(
    ticker: str, prices: pd.Series, *, start: str, as_of: str,
    gate: Callable | None = None, rearm: Callable | None = None,
) -> dict[str, Any]:
    """Expose exact daily technical decisions without pretending they were live picks.

    Injected evaluators are a test seam. Production defaults call the existing
    signal_gate and Door-R owner, never a parallel indicator implementation.
    Unknown/error remains unknown; invalid inputs never become zero-price signals.
    """
    begin, cut = _day(start), _day(as_of)
    if begin > cut:
        raise ValueError('start is after as_of')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,15}', ticker):
        raise ValueError('invalid ticker')
    out: dict[str, Any] = {
        'ticker': ticker, 'start': start, 'as_of': as_of,
        'status': 'unavailable', 'reason': 'invalid_daily_prices', 'rows': [],
        'first_eligible_in_window': None, 'first_rearm_in_window': None,
        'live_decision_replay_verified': False, 'entry_fill_verified': False,
        'contextual_waiver_replayed': False, 'historical_event_latch_replayed': False,
        'price_basis': 'caller supplied pinned adjusted closes; revision-PIT unverified',
    }
    if not isinstance(prices, pd.Series) or not isinstance(prices.index, pd.DatetimeIndex):
        return out
    if prices.index.hasnans or prices.index.tz is not None:
        return out
    close = prices.loc[prices.index <= cut].copy(deep=True)
    if (not close.index.is_unique or not close.index.is_monotonic_increasing
            or not close.index.equals(close.index.normalize())):
        return out
    close = close.dropna()
    if close.empty or close.index[-1] != cut:
        out['reason'] = 'requested_session_close_missing'
        return out
    if pd.api.types.is_bool_dtype(close.dtype) or any(pd.api.types.is_bool(v) for v in close):
        return out
    try:
        close = pd.to_numeric(close, errors='raise').astype(float)
    except (TypeError, ValueError, OverflowError):
        return out
    if not all(math.isfinite(v) and v > 0 for v in close):
        return out
    assess, assess_rearm = gate or _technical_gate, rearm or _rearm
    degraded = False
    for session in close.loc[begin:cut].index:
        prefix = close.loc[:session].copy(deep=True)
        row: dict[str, Any] = {'session': session.date().isoformat(),
                              'close': float(prefix.iloc[-1]), 'gate': {}, 'rearm': {}}
        try:
            verdict = assess(ticker, prefix.copy(deep=True))
            if not isinstance(verdict, Mapping) or type(verdict.get('eligible')) is not bool:
                raise ValueError('gate verdict unavailable')
            row['gate'] = {field: _json_value(verdict.get(field)) for field in _GATE_FIELDS}
        except Exception:
            degraded = True
            row['gate'] = {'eligible': None, 'reason': 'technical_evaluator_unavailable'}
            row['rearm'] = {'fires': None, 'reason': 'technical_evaluator_unavailable'}
            out['rows'].append(row)
            continue
        try:
            rearm_result = assess_rearm(dict(verdict), prefix.copy(deep=True))
            if not isinstance(rearm_result, Mapping) or type(rearm_result.get('fires')) is not bool:
                raise ValueError('rearm verdict unavailable')
            row['rearm'] = _json_value(dict(rearm_result))
        except Exception:
            degraded = True
            row['rearm'] = {'fires': None, 'reason': 'rearm_evaluator_unavailable'}
        if row['gate']['eligible'] and out['first_eligible_in_window'] is None:
            out['first_eligible_in_window'] = row['session']
        if row['rearm'].get('fires') is True and out['first_rearm_in_window'] is None:
            out['first_rearm_in_window'] = row['session']
        out['rows'].append(row)
    out.update(status='degraded' if degraded else 'ready', reason=None)
    return out


def recorded_sightings(records: Sequence[Mapping], ticker: str, *, as_of: str) -> list[dict]:
    """Keep a source observation's date; never rename a shadow sighting a live entry."""
    cut = _day(as_of)
    result = []
    for record in records:
        if not isinstance(record, Mapping) or record.get('ticker') != ticker:
            continue
        try:
            stamp = _day(record.get('date'))
        except (TypeError, ValueError):
            continue
        if stamp > cut:
            continue
        features = record.get('features') if isinstance(record.get('features'), Mapping) else {}
        result.append({'date': record['date'], 'door': record.get('door'),
                       'theme': features.get('theme'), 'themes_hit': deepcopy(features.get('themes_hit')),
                       'tier': features.get('tier'), 'ticks': features.get('ticks'),
                       'live_entry_authority': False, 'historical_availability_verified': False})
    return result


def _blob(repo: Path, source: str, path: str) -> tuple[bytes, dict]:
    body = subprocess.check_output(['git', '-C', str(repo), 'show', f'{source}:{path}'])
    return body, {'path': path, 'sha256': hashlib.sha256(body).hexdigest(),
                  'blob': subprocess.check_output(['git', '-C', str(repo), 'rev-parse',
                                                   f'{source}:{path}'], text=True).strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--tickers', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_ref):
        parser.error('source-ref must be an immutable 40-character commit')
    tickers = list(dict.fromkeys(t.strip().upper() for t in args.tickers.split(',') if t.strip()))
    if not tickers or len(tickers) > 100:
        parser.error('choose 1 to 100 explicit diagnostic tickers')
    if any(not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,15}', t) for t in tickers):
        parser.error('invalid ticker')
    _day(args.start); _day(args.as_of)
    # The current checkout's engine code must match the named source, not just its data.
    owners = ['engine/signal_gate.py', 'engine/signal_quality.py', 'engine/confluence_tiers.py',
              'engine/prophet_doors.py', 'engine/session_anchor.py']
    engine_sources = []
    for path in owners:
        body, receipt = _blob(ROOT, args.source_ref, path)
        if (ROOT / path).read_bytes() != body:
            raise RuntimeError(f'code/source mismatch for {path}; use a matching source checkout')
        engine_sources.append(receipt)
    sources = []
    def read(path):
        body, receipt = _blob(ROOT, args.source_ref, path); sources.append(receipt); return body
    board = json.loads(read('site/factordata/us_standouts.json'))
    gates = json.loads(read('site/factordata/signal_gate.json'))
    leaders = json.loads(read('site/anticipationdata/us_leader_pullback.json'))
    flags = [json.loads(line) for line in read('data/prophet_doors/flags.jsonl').splitlines() if line.strip()]
    report = {
        'source_ref': args.source_ref, 'cutoff': args.as_of,
        'method': 'existing technical gate and Door-R on each close prefix; mutable waiver disabled',
        'cohort': 'explicit motivating cases, not a representative or outcome-selected validation sample',
        'entry_authority_changed': False, 'performance_validation': False,
        'premarket_prices_used': False, 'cases': {}, 'sources': sources,
        'engine_sources': engine_sources,
        'source_scope': 'listed core owner bytes matched; immutable data vintage; not a full archived runtime replay',
    }
    for ticker in tickers:
        prices = pd.read_parquet(io.BytesIO(read(f'data/yahoo/{ticker}.parquet')))['close']
        case = evaluate_prefixes(ticker, prices, start=args.start, as_of=args.as_of)
        case['published_gate'] = {'as_of': gates.get('as_of'),
                                  'value': (gates.get('verdicts') or {}).get(ticker)}
        case['published_leadership'] = {'as_of': leaders.get('data_session') or leaders.get('as_of'),
                                        'value': (leaders.get('states') or {}).get(ticker)}
        case['published_pool'] = {'as_of': board.get('as_of'), 'value': next((
            r for r in (board.get('candidate_pool') or {}).get('rows', []) if r.get('ticker') == ticker), None)}
        case['recorded_shadow_sightings'] = recorded_sightings(flags, ticker, as_of=args.as_of)
        report['cases'][ticker] = case
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({t: {'first_eligible': c['first_eligible_in_window'],
                          'first_rearm': c['first_rearm_in_window'],
                          'last_gate': c['rows'][-1]['gate'] if c['rows'] else None,
                          'shadow_sightings': c['recorded_shadow_sightings']}
                      for t, c in report['cases'].items()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
