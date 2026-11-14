"""Private original-byte longitudinal 35-calendar-day factor options research.

Read only incumbent house registry, original local Git price objects, and the
original ThetaData year-Parquet archive. One 35-day precommitted schedule per
source sample; no source mutation, job, provider call, new store or published
options-market signal. Old EOD data do NOT prove what an investor knew then.
"""
from __future__ import annotations

import argparse
from datetime import date,datetime,timedelta,timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

from lib.us_cash_calendar import expected_last_session,sessions_between
from research.factor_atlas.session3.extended_backtest import (build_fixed_schedule,summarize_paired_cases,
     summarize_by_calendar_year,summarize_volatility_scoring)
from research.factor_atlas.session3.retrospective import _COLUMNS
from research.factor_atlas.session3.retrospective_calibration import evaluate
from research.factor_atlas.session3.run_retrospective import _date,_git_blob,_json,_ROOT,_SHA,_stat,_MAX_GREEK_BYTES

_SCHEMA='factor_atlas.s3.extended_35day_inputs/v1'
_KEYS={'schema','basket_id','membership_blob','start_anchor','last_nominal',
       'source_price_column','roots'}
_PRICE_COLUMNS={'close','close_price'}
_YEAR_ROWS_LIMIT=1_200_000
_ROOT_LIMIT=10
_EPISODE_LIMIT=48


def _read_anchors(*,store:Path,root:str,year:int,expected:str,anchors:list[date])->tuple[dict,dict]:
    if not isinstance(expected,str) or _SHA.fullmatch(expected) is None:
        raise ValueError('exact original Greek-year digest required')
    tier=(store/'greeks').resolve()
    file=store/'greeks'/root/f'{year}.parquet'
    if not file.exists():
        return {},{'year':year,'status':'ORIGINAL_YEAR_ABSENT','expected_sha256':expected}
    if not file.resolve().is_relative_to(tier):
        raise ValueError('Greek year file escapes original owner Greek tier')
    if any(a.year!=year for a in anchors):
        raise ValueError('cross-year anchor passed to original yearly source')
    with file.open('rb') as f:
        before=_stat(os.fstat(f.fileno()))
        if not 0<before[2]<=_MAX_GREEK_BYTES:
            raise ValueError('original archive exceeds bounded Greek year byte policy')
        h=hashlib.sha256()
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
        if h.hexdigest()!=expected:
            raise ValueError('original Greek-year source digest mismatch')
        f.seek(0)
        table=pq.read_table(f,columns=sorted(_COLUMNS),
                     filters=[('date','in',[pd.Timestamp(a) for a in anchors])])
        after=_stat(os.fstat(f.fileno()))
        if before!=after or before!=_stat(file.stat()):
            raise ValueError('original Greek-year mutated during read')
    if table.num_rows>_YEAR_ROWS_LIMIT:
        raise ValueError('precommitted anchor rows exceed bounded cohort')
    frame=table.to_pandas()
    if frame.empty:
        return {},{'year':year,'status':'READ_VERIFIED_NO_DATE_ROWS','sha256':expected,
                    'anchor_rows':0,'anchor_days':0}
    if frame.columns.duplicated().any() or not _COLUMNS.issubset(frame.columns):
        raise ValueError('original Greek-year column shape invalid')
    labels=pd.to_datetime(frame['date'],errors='coerce')
    if labels.isna().any() or labels.dt.tz is not None:
        raise ValueError('Greek-year source has invalid session clock')
    if not set(labels.dt.date).issubset(anchors):
        raise ValueError('Greek source date outside precommitted anchors')
    obs={}
    for day,g in frame.groupby(labels.dt.date,sort=True):
        if not g['root'].eq(root).fillna(False).all():
            raise ValueError('Greek root identity mismatch in original archive')
        obs[day]=g.copy(deep=True)
    return obs,{'year':year,'status':'READ_VERIFIED','sha256':expected,
                'anchor_rows':len(frame),'anchor_days':len(obs)}


def load_extended_backtest(*,manifest:dict,source_repository:Path,store_root:Path,
                           captured_at:datetime|None=None,
                           research_iv_error_abs_max:float=0.)->dict:
    if type(research_iv_error_abs_max) not in (int,float) or research_iv_error_abs_max not in (0.,5e-5,1e-4,5e-4):
        raise ValueError('explicit bounded research iv_error threshold required')
    if not isinstance(manifest,dict) or set(manifest)!=_KEYS:
        raise ValueError('exact precommitted extended-study manifest fields required')
    if manifest['schema']!=_SCHEMA or manifest['basket_id']!='mag7':
        raise ValueError('this original research runner serves only current Mag7')
    if manifest['source_price_column'] not in _PRICE_COLUMNS:
        raise ValueError('explicit historical price-column basis required')
    start=_date(manifest['start_anchor'])
    end=_date(manifest['last_nominal'])
    now=captured_at if captured_at is not None else datetime.now(timezone.utc)
    if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('aware actual retrospective capture time required')
    latest=expected_last_session(now)
    if end>=latest:
        raise ValueError('study final anchor lacks completed forward observation horizon')
    source_repo,store=Path(source_repository),Path(store_root)
    if not source_repo.is_dir() or not store.is_dir():
        raise ValueError('already-held original repository and original store required')
    lock=store/'_writer.lock'
    if not lock.is_file():
        raise ValueError('original owner writer lock is unavailable')
    start_history=start-timedelta(days=900)
    source_calendar=sessions_between(start_history,min(latest,end+timedelta(days=90)))
    anchors=build_fixed_schedule(start=start,last_nominal=end,sessions=source_calendar)
    if not 1<=len(anchors)<=_EPISODE_LIMIT:
        raise ValueError('bounded precommitted sample required')
    raw=_git_blob(source_repo,manifest['membership_blob'])
    registry=_json(raw)
    basket=registry.get('baskets',{}).get('mag7',{})
    if basket.get('weighting')!='equal' or not isinstance(basket.get('members'),list):
        raise ValueError('immutable original house equal membership required')
    original_roots=[];seen=set()
    for row in basket['members']:
        if not isinstance(row,dict) or not isinstance(row.get('ticker'),str) or _ROOT.fullmatch(row['ticker']) is None:
            raise ValueError('invalid original basket root identity')
        root=row['ticker']
        added=_date(row.get('added'))
        removed=_date(row['removed']) if row.get('removed') is not None else None
        if root in seen or (removed is not None and removed<=added):
            raise ValueError('ambiguous source membership interval')
        seen.add(root)
        if added<=anchors[-1] and (removed is None or removed>anchors[-1]):
            if added>anchors[0]:
                raise ValueError('basket became effective after first fixed episode')
            original_roots.append(root)
    if not 3<=len(original_roots)<=_ROOT_LIMIT:
        raise ValueError('bounded original house roots required')
    roots=sorted(original_roots)
    input_roots=manifest['roots']
    if not isinstance(input_roots,dict) or not set(input_roots).issubset(roots):
        raise ValueError('unrecognized original input root identity')
    needed_years=sorted({a.year for a in anchors})
    greeks={a:{} for a in anchors}
    prices={}
    receipts={}
    with lock.open('rb') as ownerlock:
        try:fcntl.flock(ownerlock.fileno(),fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('original writer lock busy; read refused') from error
        try:
            for root in roots:
                item=input_roots.get(root)
                if item is None:
                    receipts[root]={'status':'ROOT_SOURCE_NOT_DECLARED'}
                    continue
                if not isinstance(item,dict) or set(item)!={'price_blob','years'} or not isinstance(item['years'],dict):
                    raise ValueError('exact original root source hash fields required')
                if set(item['years'])-set(map(str,needed_years)):
                    raise ValueError('source Greek year outside predeclared episode population')
                rawprice=_git_blob(source_repo,item['price_blob'])
                df=pd.read_parquet(io.BytesIO(rawprice))
                col=manifest['source_price_column']
                if col not in df or df.columns.duplicated().any() or not isinstance(df.index,pd.DatetimeIndex):
                    raise ValueError('original source price column/session identity absent')
                prices[root]=df[col]
                years_receipt={}
                for year in needed_years:
                    yearanchors=[a for a in anchors if a.year==year]
                    sha=item['years'].get(str(year))
                    if sha is None:
                        years_receipt[str(year)]={'status':'NOT_DECLARED','year':year}
                        continue
                    v,proof=_read_anchors(store=store,root=root,year=year,expected=sha,anchors=yearanchors)
                    years_receipt[str(year)]=proof
                    for date_,actual_rows in v.items():
                        # Pure incumbent selector will revalidate these actual
                        # original date-slice quote rows; no fabricated IV/clock.
                        greeks[date_][root]=actual_rows
                receipts[root]={'price_git_blob':item['price_blob'],
                                'price_sha256':hashlib.sha256(rawprice).hexdigest(),
                                'price_rows':len(df),'price_column':col,
                                'price_adjustment_vintage':None,
                                'years':years_receipt}
        finally:fcntl.flock(ownerlock.fileno(),fcntl.LOCK_UN)
    prices_panel=pd.DataFrame(prices) if prices else pd.DataFrame(index=pd.DatetimeIndex([]))
    baseline=evaluate(weights={root:1/len(roots) for root in roots},
                      greeks_by_anchor=greeks,
                      closes=prices_panel,sessions=source_calendar,
                      anchors=anchors,captured_at=now,
                      research_iv_error_abs_max=research_iv_error_abs_max)
    baseline['preregistered_schedule']={
        'start_anchor':start.isoformat(),'last_nominal':end.isoformat(),
        'step_calendar_days':35,'declared_anchor_count':len(anchors),
        'anchors':[a.isoformat() for a in anchors],
        'anchor_selection':'first cash session on/after nominal every 35 calendar days',
        'null_case_retention_required':True,
        'source_quality_blind_selection':True,
    }
    baseline['longitudinal_summary']=summarize_paired_cases(baseline['cases'])
    baseline['strata_by_year']=summarize_by_calendar_year(baseline['cases'])
    baseline['volatility_scoring']=summarize_volatility_scoring(baseline['cases'])
    if research_iv_error_abs_max>0:
        baseline['research_sensitivity']={
            'iv_error_abs_max':float(research_iv_error_abs_max),
            'only_research':True,
            'original_strict_baseline_unchanged':True,
            'historical_quote_quality_certified':False,
            'publication_eligible':False,
        }
    baseline['source_receipts']={
        'membership_git_blob':manifest['membership_blob'],
        'membership_sha256':hashlib.sha256(raw).hexdigest(),
        'greeks_year_file_count_verified':sum(
            int(proof.get('status') in ('READ_VERIFIED','READ_VERIFIED_NO_DATE_ROWS'))
            for item in receipts.values() for proof in item.get('years',{}).values()),
        'source_rights':'NOT_CERTIFIED',
        'historical_known_at':'UNPROVEN',
        'market_quote_timestamps':'NOT_PRESENT_IN_LEGACY_GREEKS',
        'price_adjustment_vintage':'NOT_CERTIFIED',
        'source_quote_method':'NOT_CERTIFIED',
        'precommitted_quote_filter':'legacy_iv_error_exact_zero' if research_iv_error_abs_max==0 else 'experimental_bounded_solver_residual_sensitivity',
        'original_source_data_mutated':False,
        'roots':receipts
    }
    baseline['published']=False
    baseline['classification']='PRIVATE_MULTIYEAR_RETROSPECTIVE_NONLIVE'
    canonical={k:v for k,v in baseline.items() if k!='captured_at'}
    baseline['measurement_sha256']=hashlib.sha256(json.dumps(
        canonical,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return baseline


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--source-repository',type=Path,required=True)
    parser.add_argument('--store-root',type=Path,required=True)
    parser.add_argument('--research-iv-error-abs-max',type=float,default=0.,choices=(0.,5e-5,1e-4,5e-4),
                        help='PRIVATE exploratory solver residual sensitivity; not production qualification')
    args=parser.parse_args(argv)
    try:
        with args.manifest.open('rb') as f:raw=f.read(128*1024+1)
        if not 0<len(raw)<=128*1024:
            raise ValueError('bounded original study manifest bytes required')
        result=load_extended_backtest(manifest=_json(raw),source_repository=args.source_repository,
                                      store_root=args.store_root,
                                      research_iv_error_abs_max=args.research_iv_error_abs_max)
        print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as error:
        print('EXTENDED_S3_RESEARCH_REFUSED: '+str(error),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
