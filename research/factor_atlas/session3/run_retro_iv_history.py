"""Private 252-cash-session IV history over original source hashes, no publication.

One full-year Greek file is validated and read once per root/year. Date-only
legacy data cannot certify NBBO quote age, EOD mark, historical publication,
corporate actions or redistribution. This intentionally cannot authorize the
source-qualified options_basket_history producer and never calls live providers.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

from lib.us_cash_calendar import is_session, sessions_between
from research.factor_atlas.session3.retrospective import select_iv30, _COLUMNS
from research.factor_atlas.session3.retrospective_iv_history import summarize_private_history
from research.factor_atlas.session3.run_retrospective import (_git_blob,_json,_date,_SHA,_ROOT,_stat,
                                                              _MAX_GREEK_BYTES)

_SCHEMA = 'factor_atlas.s3.private_iv_history_inputs/v1'
_ALLOWED = {'schema','basket_id','anchor','membership_blob','roots'}
_MAX_ANNUAL_SELECTED_ROWS = 2_000_000


def _read_year(*,store:Path,root:str,year:int,expected:str,
               first:date,last:date) -> tuple[dict,dict]:
    """Verify original held source file digest and read only declared date range."""
    if not isinstance(expected,str) or _SHA.fullmatch(expected) is None:
        raise ValueError('exact Greek year digest required')
    tier=(store/'greeks').resolve()
    source=store/'greeks'/root/f'{year}.parquet'
    if not source.exists():
        return {},{'status':'SOURCE_YEAR_FILE_MISSING','year':year,'expected_sha256':expected}
    if not source.resolve().is_relative_to(tier):
        raise ValueError('year file escapes incumbent original Greek tier')
    with source.open('rb') as f:
        before=_stat(os.fstat(f.fileno()))
        if not 0<before[2]<=_MAX_GREEK_BYTES:
            raise ValueError('Greek year file exceeds original bounded read policy')
        digest=hashlib.sha256()
        for piece in iter(lambda:f.read(1024*1024),b''):
            digest.update(piece)
        if digest.hexdigest()!=expected:
            raise ValueError('original Greek year source digest mismatch')
        f.seek(0)
        table=pq.read_table(f,columns=sorted(_COLUMNS),
              filters=[('date','>=',pd.Timestamp(first)),('date','<=',pd.Timestamp(last))])
        after=_stat(os.fstat(f.fileno()))
        if before!=after or before!=_stat(source.stat()):
            raise ValueError('original Greek year changed during read')
    if table.num_rows>_MAX_ANNUAL_SELECTED_ROWS:
        raise ValueError('Greek year cohort row bound exceeded')
    frame=table.to_pandas()
    if frame.empty:
        return {},{'status':'READ_VERIFIED_NO_ELIGIBLE_ROWS','year':year,'sha256':expected,'rows':0}
    if not _COLUMNS.issubset(frame.columns):
        raise ValueError('original Greek source columns missing')
    if frame.columns.duplicated().any():
        raise ValueError('ambiguous original Greek columns')
    dt=pd.to_datetime(frame['date'],errors='coerce')
    if dt.isna().any() or dt.dt.tz is not None:
        raise ValueError('unexpected source session date field')
    frame=frame.loc[dt.dt.normalize().between(pd.Timestamp(first),pd.Timestamp(last))].copy()
    grouped={}
    for day,g in frame.groupby(frame.date.dt.date,sort=True):
        if day < first or day > last:
            raise ValueError('source read includes out-of-window day')
        grouped[day]=select_iv30(g,root=root,anchor=day)
    return grouped,{'status':'READ_VERIFIED','year':year,'sha256':expected,
                    'selected_rows':len(frame),'date_groups':len(grouped)}


def load_private_iv_history(*,manifest:dict,source_repository:Path,
                            store_root:Path,captured_at:datetime|None=None) -> dict:
    """Research current-roster history with exact original Git and parquet bytes."""
    if not isinstance(manifest,dict) or set(manifest)!=_ALLOWED:
        raise ValueError('exact private historical IV study manifest fields required')
    if manifest['schema']!=_SCHEMA or manifest['basket_id']!='mag7':
        raise ValueError('current Mag7 study only; no new basket writer')
    anchor=_date(manifest['anchor'])
    if not is_session(anchor):
        raise ValueError('declared anchor is not incumbent cash session')
    sessions=sessions_between(anchor-timedelta(days=400),anchor)[-252:]
    if len(sessions)!=252 or sessions[-1]!=anchor:
        raise ValueError('insufficient incumbent 252-session historical grid')
    now=captured_at if captured_at is not None else datetime.now(timezone.utc)
    if (not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None
        or now.date()<anchor):
        raise ValueError('aware research capture must be after source anchor')
    repo=Path(source_repository);store=Path(store_root)
    if not repo.is_dir() or not store.is_dir():
        raise ValueError('already-existing source paths required')
    raw=_git_blob(repo,manifest['membership_blob'])
    document=_json(raw)
    basket=document.get('baskets',{}).get('mag7',{})
    if basket.get('weighting')!='equal' or not isinstance(basket.get('members'),list):
        raise ValueError('original equal-weight registry required')
    roots=[];seen=set()
    for item in basket['members']:
        if not isinstance(item,dict) or not isinstance(item.get('ticker'),str) or _ROOT.fullmatch(item['ticker']) is None:
            raise ValueError('malformed original root identity')
        root=item['ticker'];added=_date(item.get('added'))
        removed=_date(item['removed']) if item.get('removed') is not None else None
        if root in seen or (removed is not None and removed<=added):
            raise ValueError('duplicate or invalid original root effective interval')
        seen.add(root)
        if added<=anchor and (removed is None or anchor<removed):
            roots.append(root)
    if not 3<=len(roots)<=10:
        raise ValueError('bounded exact Mag7 root population required')
    roots=sorted(roots)
    sources=manifest['roots']
    if not isinstance(sources,dict) or not set(sources).issubset(roots):
        raise ValueError('source root identity outside original registry')
    years=sorted({day.year for day in sessions})
    observed={day:{} for day in sessions}
    receipts={}
    for root in roots:
        specification=sources.get(root)
        if specification is None:
            receipts[root]={'status':'ROOT_NOT_SUPPLIED'}
            continue
        if not isinstance(specification,dict) or set(specification)!={'years'} or not isinstance(specification['years'],dict):
            raise ValueError('exact original Greek year source contract required')
        if set(specification['years'])-set(map(str,years)):
            raise ValueError('source years outside requested cash calendar')
        year_receipts={}
        for year in years:
            expected=specification['years'].get(str(year))
            if expected is None:
                year_receipts[str(year)]={'status':'SOURCE_YEAR_NOT_DECLARED'}
                continue
            days=[d for d in sessions if d.year==year]
            data,receipt=_read_year(store=store,root=root,year=year,expected=expected,first=days[0],last=days[-1])
            year_receipts[str(year)]=receipt
            for day,selection in data.items():
                if day not in observed:
                    raise ValueError('source day outside original calendar')
                observed[day][root]=selection
        receipts[root]={'status':'SOURCE_YEARS_READ','years':year_receipts}
    result=summarize_private_history(sessions=sessions,
             weights={root:1/len(roots) for root in roots},observed=observed,captured_at=now)
    result['source_receipts']={'membership_git_blob':manifest['membership_blob'],
          'membership_sha256':hashlib.sha256(raw).hexdigest(),
          'source_use_status':'RETROSPECTIVE_UNQUALIFIED',
          'original_source_files_modified':False,'roots':receipts}
    canonical={k:v for k,v in result.items() if k!='captured_at'}
    result['measurement_sha256']=hashlib.sha256(json.dumps(canonical,sort_keys=True,
                                              separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--source-repository',type=Path,required=True)
    parser.add_argument('--store-root',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        with args.manifest.open('rb') as f:
            raw=f.read(128*1024+1)
        if not 0<len(raw)<=128*1024:
            raise ValueError('bounded source recipe required')
        result=load_private_iv_history(manifest=_json(raw),
            source_repository=args.source_repository,store_root=args.store_root)
        print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as error:
        print('PRIVATE_IV_HISTORY_REFUSED: '+str(error),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
