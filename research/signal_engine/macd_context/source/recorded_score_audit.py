"""Fixed archived-score association; no fitted policy, new grades or live writes."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd

INPUT_SHA256 = '366d94709ea8fef4ac91cc30cf4efd975b26e68a65766082e5ca8feb99aca6db'
STRATA = [('bottoming-alignment', 'adjusted'), ('bottoming-alignment', 'unadjusted'),
          ('bottoming-alignment', 'unverified_pre_20260806'), ('confluence', 'adjusted'),
          ('confluence', 'unadjusted'), ('us_prophet_v1', 'adjusted')]
COLUMNS = ['as_of', 'lane', 'ticker', 'horizon', 'snapshot_rank_by', 'price_basis',
           'recorded_horizon_d21', 'context_status', 'ret']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank_association(x, y):
    x = pd.to_numeric(x, errors='raise').to_numpy(dtype=float)
    y = pd.to_numeric(y, errors='raise').to_numpy(dtype=float)
    if len(x) != len(y):
        raise ValueError('Score and outcome lengths differ')
    valid = np.isfinite(x) & np.isfinite(y)
    result = {'pairs': int(valid.sum()), 'missing_pairs': int((~valid).sum()),
              'rho': np.nan, 'reason': 'fewer_than_two_pairs'}
    if valid.sum() < 2:
        return result
    rx = pd.Series(x[valid]).rank(method='average').to_numpy()
    ry = pd.Series(y[valid]).rank(method='average').to_numpy()
    rx, ry = rx - rx.mean(), ry - ry.mean()
    if not np.any(rx):
        return dict(result, reason='constant_score')
    if not np.any(ry):
        return dict(result, reason='constant_outcome')
    rho = float(np.dot(rx, ry) / np.sqrt(np.dot(rx, rx) * np.dot(ry, ry)))
    return dict(result, rho=rho, reason='defined')


def summarize_archive(frame):
    rows, summaries = [], []
    for ranker, basis in STRATA:
        part = frame[frame.snapshot_rank_by.eq(ranker) & frame.price_basis.eq(basis)]
        date_rows = []
        for date, group in part.groupby('as_of', sort=True, dropna=False):
            entry = dict(ranker=ranker, price_basis=basis, as_of=str(date), rows=len(group))
            entry.update(rank_association(group.recorded_horizon_d21, group.ret))
            rows.append(entry)
            date_rows.append(entry)
        defined = [r['rho'] for r in date_rows if r['reason'] == 'defined']
        summaries.append(dict(ranker=ranker, price_basis=basis, rows=len(part),
            signal_dates=len(date_rows), defined_dates=len(defined),
            undefined_dates=len(date_rows)-len(defined),
            finite_pairs=sum(r['pairs'] for r in date_rows),
            missing_pairs=sum(r['missing_pairs'] for r in date_rows),
            equal_date_mean_spearman=float(np.mean(defined)) if defined else np.nan))
    return pd.DataFrame(rows), pd.DataFrame(summaries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite a research result')
    if digest(args.input) != INPUT_SHA256:
        raise ValueError('Frozen archive identity changed')
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root))
    from engine.trial_ledger import TrialLedger
    ledger = TrialLedger(path=args.ledger, family='macd_context_cycle')
    if ledger.effective_n() < 6502 or ledger.literal_n() < 6:
        raise ValueError('Declared exposure/configuration accounting missing')
    ruling = Path(__file__).resolve().parents[1] / 'RECORDED_SCORE_DESCRIPTIVE_RULING_2026-09-16.md'
    if not ruling.exists():
        raise FileNotFoundError('Archive-only ruling missing')
    frame = pd.read_parquet(args.input, columns=COLUMNS)
    target = frame[frame.context_status.eq('attached') & frame.lane.eq('buy') & frame.horizon.eq(21)].copy()
    if len(target) != 823 or target.as_of.nunique() != 18:
        raise ValueError('Frozen population membership changed')
    if set(zip(target.snapshot_rank_by, target.price_basis)) != set(STRATA):
        raise ValueError('Observed ranker/basis strata changed')
    if target.duplicated(['as_of', 'lane', 'ticker', 'horizon']).any():
        raise ValueError('Repeated observation identity')
    score = pd.to_numeric(target.recorded_horizon_d21, errors='raise')
    if not (np.isfinite(score).all() and score.between(-1, 1).all()):
        raise ValueError('Recorded score coverage/range changed')
    original = target.copy(deep=True)
    dates, summary = summarize_archive(target)
    pd.testing.assert_frame_equal(target, original)
    if digest(args.input) != INPUT_SHA256:
        raise ValueError('Input changed during audit')
    args.output.mkdir(parents=True, exist_ok=False)
    dates.to_csv(args.output / 'date_associations.csv', index=False)
    summary.to_csv(args.output / 'stratum_associations.csv', index=False)
    receipt = dict(status='COMPLETE_FIXED_ARCHIVE_DESCRIPTION', authority='none',
        input_sha256=INPUT_SHA256, input_rows=len(frame), target_rows=len(target),
        target_dates=int(target.as_of.nunique()), strata=len(summary),
        outcome_association_computed=True, strategy_returns_computed=False,
        new_grade_or_live_store_written=False, score_fitted=False,
        out_of_sample_claim=False, independent_review_completed=False,
        historical_publication_verified=False, uncertainty_or_significance_claim=False,
        estimand='equal-date mean within-date Spearman of recorded d21 vs stored H21 ret',
        ledger_sha256=digest(args.ledger), effective_n=ledger.effective_n(),
        default_branch_accounting_merged=False, ruling_sha256=digest(ruling),
        script_sha256=digest(__file__), pandas_version=pd.__version__, numpy_version=np.__version__,
        limitations=['selected archived population', 'overlapping outcome windows',
          'six unpooled ranker/price-basis strata', 'no current-v3 H21',
          'no requested SPY-up RSP-down or SPY-below200 support',
          'publication/input vintages not certified', 'not a cash-profit probability'])
    receipt['output_sha256'] = {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(summary.to_string(index=False), flush=True)
    print(json.dumps({'status': receipt['status'], 'target_rows': len(target),
                      'strata': len(summary), 'predictive_authority': False}), flush=True)


if __name__ == '__main__':
    main()
