"""Source-bound research view of existing Prophet records; no grader or store writes."""
from pathlib import Path
import argparse, hashlib, importlib.util, io, json, subprocess, sys
import numpy as np
import pandas as pd
sys.dont_write_bytecode = True
KEY = ['as_of','lane','ticker']
GRADE_BLOB = '67e2541add91fa335918c95e098d9aec0fcf7030'
SNAPSHOT_BLOB = '8e39dcc977931a3900c1a63e81a31eddd039fb05'
OWNER_BLOB = '68ef9eb7620f0592e3cd02d66a3eae2ab0998dce'

def git_blob(b):
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def attach_context(grades, context, history_from):
    if grades.duplicated(KEY+['horizon']).any(): raise ValueError('Duplicate grade keys')
    if context.duplicated(KEY).any(): raise ValueError('Duplicate context keys')
    collisions = (set(grades)&set(context))-set(KEY)
    if collisions: raise ValueError('Ambiguous columns: '+str(sorted(collisions)))
    out = grades.merge(context,on=KEY,how='left',sort=False,validate='many_to_one',indicator='_context_join')
    before = out.as_of.astype(str).str[:10] < history_from
    found = out['_context_join'].eq('both')
    out['context_status'] = np.select([before,found],['pre_selection_era','attached'],default='missing_snapshot')
    return out.drop(columns=['_context_join'])

def attach_market_context(frame, states):
    if not states.index.is_unique: raise ValueError('Duplicate market dates')
    out = frame.copy()
    idx = pd.to_datetime(out.as_of)
    for col in states:
        if col in out: raise ValueError('Market context would overwrite '+col)
        out[col] = states[col].reindex(idx).to_numpy()
    return out

def read_object(repo, sha):
    p = subprocess.run(['git','-C',str(repo),'cat-file','blob',sha],capture_output=True,timeout=30)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace')[:300])
    if git_blob(p.stdout)!=sha: raise ValueError('Object identity mismatch')
    return p.stdout

def snapshot_context(raw, owner):
    rows, seen = [], set()
    for ordinal,line in enumerate(raw.splitlines(),1):
        if not line.strip(): continue
        d = json.loads(line)
        b = owner._board_to_record(d)
        if b is None: raise ValueError('Ungradeable snapshot record')
        date = str(b['as_of'])[:10]
        if date in seen: raise ValueError('Duplicate snapshot date')
        seen.add(date)
        original = {}
        for lane in owner.LANES:
            canon = 'laggards' if lane=='laggard' else lane
            for r in d.get(lane) or []:
                if not isinstance(r,dict): continue
                ticker = owner._row_features(r).get('ticker')
                if not ticker: continue
                k = (canon,ticker)
                if k in original: raise ValueError('Duplicate raw snapshot candidate')
                original[k] = r
        record_hash = hashlib.sha256(line).hexdigest()
        for parsed in b['rows']:
            r = original[(parsed['lane'],parsed['ticker'])]
            entry = r.get('entry_signal') or {}
            horizon = entry.get('horizon') or {}
            item = dict(as_of=date,lane=parsed['lane'],ticker=parsed['ticker'],
                        snapshot_rank_by=b.get('rank_by'),snapshot_ordinal=ordinal,
                        snapshot_record_sha256=record_hash,
                        snapshot_candidate_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            for name in ('position','entry_status','sector','align_tier','state','score','act_level'):
                item['snapshot_'+name] = parsed.get(name)
            for h in ('d3','d21','d63'):
                item['recorded_horizon_'+h] = horizon.get(h)
            item['recorded_confidence'] = entry.get('confidence')
            item['recorded_entry_grade'] = entry.get('entry_grade')
            item['recorded_confluence_gated'] = entry.get('confluence_gated')
            for name in ('board_definition','candidate_id','event_id','policy_version','anchor_era','signal_maturity','model_version'):
                item['recorded_'+name] = r.get(name,d.get(name))
            rows.append(item)
    result = pd.DataFrame(rows)
    if result.empty: raise ValueError('No candidate context')
    if result.duplicated(KEY).any(): raise ValueError('Duplicate extracted candidate')
    return result


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--pin',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Evidence output already exists')
    owner_path = args.repo/'scripts/grade_us_board.py'
    if git_blob(owner_path.read_bytes())!=OWNER_BLOB: raise ValueError('Parser source changed')
    expected = {'data/us_board_ledger/retro_grades.parquet':GRADE_BLOB,
                'data/us_board_ledger/snapshots.jsonl':SNAPSHOT_BLOB,
                'scripts/grade_us_board.py':OWNER_BLOB}
    for path,sha in expected.items():
        r = subprocess.run(['git','-C',str(args.repo),'rev-parse',args.pin+':'+path],capture_output=True,text=True,timeout=10)
        if r.returncode or r.stdout.strip()!=sha: raise ValueError('Pinned source changed: '+path)
    sys.path.insert(0,str(args.repo))
    owner = load_module(owner_path,'recorded_context_owner')
    raw_grade,raw_snapshot = read_object(args.repo,GRADE_BLOB),read_object(args.repo,SNAPSHOT_BLOB)
    grades = pd.read_parquet(io.BytesIO(raw_grade))
    context = snapshot_context(raw_snapshot,owner)
    joined = attach_context(grades,context,owner.LEDGER_HISTORY_FROM)
    pd.testing.assert_frame_equal(joined[grades.columns],grades)
    metadata = {}
    for name in ('position','entry_status','sector','align_tier','state','score','act_level'):
        a,b = joined[name],joined['snapshot_'+name]
        valid = a.notna()&b.notna()
        if name in ('position','score','act_level'):
            a,b = pd.to_numeric(a,errors='raise'),pd.to_numeric(b,errors='raise')
            equal = np.isclose(a[valid],b[valid],rtol=0,atol=1e-12)
        else: equal = a[valid].eq(b[valid]).to_numpy()
        metadata[name] = dict(both_known=int(valid.sum()),unequal=int((~equal).sum()))
    overlay_path = Path(__file__).with_name('benchmark_overlay.py')
    overlay_hash = hashlib.sha256(overlay_path.read_bytes()).hexdigest()
    if overlay_hash!='aa5ea72082e34270f36fa0021547ec213669dbfb140e8824fa07fa486f5ca60f':
        raise ValueError('Declared market-state source changed')
    overlay_module = load_module(overlay_path,'recorded_context_market_owner')
    market_series,market_inputs = {},{}
    for ticker in ('SPY','RSP'):
        path = args.repo/'data/yahoo'/(ticker+'.parquet')
        raw = path.read_bytes()
        frame = pd.read_parquet(io.BytesIO(raw))
        if not frame.index.is_unique: raise ValueError('Duplicate market sessions')
        market_series[ticker] = frame['close'].sort_index()
        market_inputs[ticker] = dict(sha256=hashlib.sha256(raw).hexdigest(),source=str(path),last=str(frame.index.max().date()))
    prices = pd.DataFrame(market_series).reindex(market_series['SPY'].index)
    states = overlay_module.market_states(prices)
    states['context_price_asof'] = states.index.astype(str)
    joined = attach_market_context(joined,states)
    pd.testing.assert_frame_equal(joined[grades.columns],grades)
    attached = joined[joined.context_status.eq('attached')].copy()
    if attached.empty: raise ValueError('No attached post-cutoff rows')
    base = attached[attached.horizon.eq(21)&attached.lane.eq('buy')].copy()
    base['has_d21'] = base.recorded_horizon_d21.notna()
    base['price_basis_group'] = base.price_basis.fillna('__NULL__')
    coverage = base.groupby(['snapshot_rank_by','price_basis_group'],dropna=False).agg(
        rows=('ticker','size'),dates=('as_of','nunique'),tickers=('ticker','nunique'),
        score_known=('has_d21','sum'),score_distinct=('recorded_horizon_d21','nunique'),
        first=('as_of','min'),last=('as_of','max')).reset_index()
    market_coverage = base.groupby(['snapshot_rank_by','market200','market21'],dropna=False).agg(
        rows=('ticker','size'),dates=('as_of','nunique'),score_known=('has_d21','sum')).reset_index()
    args.output.mkdir(parents=True,exist_ok=False)
    context.to_parquet(args.output/'snapshot_context.parquet',index=False)
    joined.to_parquet(args.output/'joined_grades.parquet',index=False)
    prices.to_parquet(args.output/'market_context_prices.parquet')
    coverage.to_csv(args.output/'d21_coverage.csv',index=False)
    market_coverage.to_csv(args.output/'d21_market_coverage.csv',index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(args.output/'joined_grades.parquet')[grades.columns],grades)
    receipt = dict(status='PASS_RECORDED_CONTEXT_VIEW',authority='none',source_pin=args.pin,
                   input_blobs=expected,grade_sha256=hashlib.sha256(raw_grade).hexdigest(),
                   snapshot_sha256=hashlib.sha256(raw_snapshot).hexdigest(),
                   raw_rows=len(grades),context_candidates=len(context),joined_rows=len(joined),
                   context_status=joined.context_status.value_counts().to_dict(),
                   attached_dates=int(attached.as_of.nunique()),metadata_parity=metadata)
    receipt.update(original_grade_columns_unchanged=True,parquet_roundtrip_verified=True,
        market_state_source_sha256=overlay_hash,market_inputs=market_inputs,
        market_missing_rows=int(joined.market21.isna().sum()),
        market_unknown_rows=int(joined.market21.eq('unknown').sum()),
        buy_h21_rows=len(base),buy_h21_dates=int(base.as_of.nunique()),
        buy_h21_d21_known=int(base.has_d21.sum()),
        score_semantics='Recorded signed entry-quality scores; NOT probabilities',
        performance_statistics_computed=False,canonical_stores_modified=False,
        historical_publication_times_verified=False,exact_producer_versions_verified=False,
        retrospective_market_context=True,scientific_admission='PARTIAL_NOT_PROMOTION_ADMITTED',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        amendment_sha256=hashlib.sha256(Path(__file__).with_name('CONTEXT_JOIN_AMENDMENT_20260915.md').read_bytes()).hexdigest())
    receipt['output_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:receipt[k] for k in ['status','raw_rows','context_candidates','context_status','metadata_parity','buy_h21_rows','buy_h21_d21_known','market_missing_rows']}),flush=True)

if __name__ == '__main__': main()
