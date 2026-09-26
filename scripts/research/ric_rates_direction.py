#!/usr/bin/env python3
"""Run the frozen RIC experiment against incumbent FRED store snapshots.

Research artifact only. No network, scheduling, live publication or trade effects.
All generated configurations enter the existing TrialLedger before source reads.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

# Direct file invocation must resolve this checkout before any repository import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.inputs import flatten_fred_aliases
from engine.rates_direction_research import (
    FEATURES, MODELS, TENORS, ForecastSpec, prepare_panel, summarize, walk_forward,
)
from engine.trial_ledger import TrialLedger
from lib import config, store

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / 'research/rates_direction/prereg_v1.json'
FREEZE = ROOT / 'research/rates_direction/FREEZE_RECEIPT.json'
SOURCES = {'2y': 'DGS2', '5y': 'DGS5', '10y': 'DGS10',
           '30y': 'DGS30', 'real10y': 'DFII10'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_prereg(path: Path = PREREG) -> dict:
    value = json.loads(path.read_text())
    if (value.get('schema') != 'ric.rates_direction.prereg.v1'
            or tuple(value.get('models', [])) != MODELS
            or tuple(value.get('tenors', [])) != TENORS
            or tuple(value.get('features', [])) != FEATURES
            or value.get('horizons') != [1, 5, 20]
            or value.get('config_count') != 48
            or value.get('interval_coverage') != 0.8
            or value.get('jump_alert_probability') != 0.5):
        raise ValueError('preregistration does not match this frozen implementation')
    for key, expected in asdict(ForecastSpec()).items():
        name = {'refit_every': 'refit_every_observations',
                'max_gap_days': 'max_adjacent_calendar_gap_days'}.get(key, key)
        if value.get(name) != expected:
            raise ValueError(f'preregistration mismatch: {name}')
    return value


def register_before_data(prereg: dict, ledger_path: Path) -> dict:
    if not ledger_path.is_file():
        raise ValueError('materialize the existing canonical TrialLedger; no empty substitute')
    freeze = json.loads(FREEZE.read_text())
    for relative, expected in freeze['sha256'].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f'frozen candidate changed: {relative}')
    ledger = TrialLedger(path=ledger_path, family=prereg['family'])
    configurations = [
        {'prereg_sha256': digest(PREREG), 'freeze_sha256': digest(FREEZE),
         'tenor': tenor, 'horizon': horizon, 'model': model}
        for tenor in TENORS for horizon in prereg['horizons'] for model in MODELS
    ]
    before = digest(ledger_path)
    added = ledger.log_grid(configurations, info_cutoff='2026-09-24',
                            source='ric_rates_direction_preregistered',
                            note='Corrected-history diagnostics; prospective/trade authority withheld.')
    return {'family': prereg['family'], 'generated_configs': len(configurations),
            'new_configs': added, 'literal_n': ledger.literal_n(),
            'ledger_before_sha256': before, 'ledger_after_sha256': digest(ledger_path),
            'freeze_sha256': digest(FREEZE)}


def read_sources(source_root: Path) -> tuple[dict, dict]:
    """Read the existing store; bind each read to unchanged bytes and Git source."""
    original_root = config.ROOT
    sources, receipts = {}, {}
    try:
        config.ROOT = source_root.resolve()
        aliases = flatten_fred_aliases(config.load()['fred']['series'])
        source_commit = subprocess.check_output(
            ['git', '-C', str(config.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        for key, sid in SOURCES.items():
            path = config.data_dir() / 'fred' / f'{sid}.parquet'
            if not path.is_file():
                receipts[key] = {'source_id': sid, 'status': 'missing'}
                continue
            before = digest(path)
            frame = store.read('fred', sid)
            if digest(path) != before:
                raise ValueError(f'source changed during read: {sid}')
            column = aliases.get(sid)
            if frame is None or column not in frame:
                raise ValueError(f'configured source column is unavailable: {sid}:{column}')
            sources[key] = frame[column]
            relative = str(path.relative_to(config.ROOT))
            tracked = subprocess.run(['git', '-C', str(config.ROOT), 'rev-parse',
                                      f'{source_commit}:{relative}'], capture_output=True, text=True)
            working_blob = subprocess.check_output(
                ['git', '-C', str(config.ROOT), 'hash-object', str(path)], text=True).strip()
            receipts[key] = {
                'source_id': sid, 'column': column, 'sha256': before,
                'source_commit': source_commit, 'relative_path': relative,
                'matches_committed_blob': tracked.returncode == 0 and tracked.stdout.strip() == working_blob,
                'git_blob': working_blob, 'rows': len(frame),
                'first_date': str(frame.index.min().date()),
                'last_date': str(frame.index.max().date()),
                'historical_availability_qualified': False,
            }
    finally:
        config.ROOT = original_root
    return sources, receipts


def run(source_root: Path, output: Path, all_cells: bool = False) -> dict:
    prereg = load_prereg()
    registration = register_before_data(prereg, ROOT / 'data/trial_ledger.jsonl')
    sources, receipts = read_sources(source_root)
    panel = prepare_panel(sources).loc['2005-01-01':prereg['motivating_case_end']]
    cells = [(t, h) for t in TENORS for h in prereg['horizons']] if all_cells else [('10y', 5)]
    periods = {'development': ('2010-01-01', '2020-12-31'),
               'primary_holdout': (prereg['primary_start'], prereg['primary_end']),
               'motivating_case_audit': (prereg['motivating_case_start'], prereg['motivating_case_end'])}
    report = {'schema': 'ric.rates_direction.experiment.v1',
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'registration': registration, 'sources': receipts, 'cells': {},
              'evidence_tier': prereg['evidence_tier'], 'authority': False,
              'promotion': 'withheld_pending_independent_review_and_prospective_evidence'}
    output.mkdir(parents=True, exist_ok=True)
    # New immutable experiment output only; a rerun must use a new evidence directory.
    with (output / 'predictions.jsonl').open('x') as sink:
        for tenor, horizon in cells:
            result = walk_forward(panel, tenor, horizon)
            for row in result['rows']:
                sink.write(json.dumps(row, allow_nan=False) + '\n')
            # Scoring consumes these exact forecasts, never a second fit.
            report['cells'][f'{tenor}_{horizon}'] = {
                'coverage': result['coverage'], 'limitations': result['limitations'],
                'periods': {name: summarize(result, start=lo, end=hi)
                            for name, (lo, hi) in periods.items()},
                'primary_years': {str(year): summarize(result, start=f'{year}-01-01',
                                                      end=f'{year}-12-31')
                                  for year in range(2021, 2026)},
            }
            report['status'] = 'partial'
            temporary = output / 'summary.json.tmp'
            temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            temporary.replace(output / 'summary.json')
            print(f'{tenor}/{horizon}: {result["coverage"]["forecast_origins"]} origins', flush=True)
    report['status'] = 'research_run_complete_not_accepted'
    report['predictions_sha256'] = digest(output / 'predictions.jsonl')
    temporary = output / 'summary.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    temporary.replace(output / 'summary.json')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--all-cells', action='store_true')
    parser.add_argument('--register-and-run', action='store_true',
                        help='Append frozen configurations to the existing TrialLedger before reading data.')
    args = parser.parse_args()
    if not args.register_and_run:
        parser.error('--register-and-run is required; no silent trial accounting')
    report = run(args.source_root, args.output, args.all_cells)
    print(json.dumps({'status': report['status'], 'cells': list(report['cells']),
                      'summary': str(args.output / 'summary.json'), 'authority': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
