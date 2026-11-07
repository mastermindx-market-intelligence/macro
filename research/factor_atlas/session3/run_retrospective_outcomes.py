"""PRIVATE, bounded forward-label study on existing owner-held Greeks/price files.

All source paths are supplied by the operator from existing legal holdings. The
manifest is merely a closed study-input recipe, not a permission, quote-clock,
entitlement, provenance service or options-cache/collector. Never publish its
numeric stdout without a separately qualified use/publication decision.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from lib.us_cash_calendar import is_session, sessions_between
from research.factor_atlas.session3.retrospective_calibration import evaluate
from research.factor_atlas.session3.run_retrospective import (_date, _git_blob, _greeks,
                                                             _json, _GIT, _ROOT, _SHA)

_SCHEMA='factor_atlas.s3.retrospective_outcomes_inputs/v1'
_ALLOWED={'schema','basket_id','membership_blob','anchors','price_column','roots'}


def load_outcomes(*, manifest: dict, source_repository: Path, store_root: Path,
                  captured_at: datetime | None = None) -> dict:
    if not isinstance(manifest,dict) or set(manifest)!=_ALLOWED:
        raise ValueError('exact retrospective outcomes input manifest fields required')
    if manifest['schema']!=_SCHEMA or manifest['basket_id']!='mag7':
        raise ValueError('existing Mag7 research scope only')
    if manifest['price_column'] not in ('close','close_price'):
        raise ValueError('existing close column only')
    tokens=manifest['anchors']
    if not isinstance(tokens,list) or not 1<=len(tokens)<=12:
        raise ValueError('one to twelve predeclared study anchors required')
    anchors=[_date(t) for t in tokens]
    if anchors!=sorted(set(anchors)) or len({d.year for d in anchors})!=1:
        raise ValueError('strict unique increasing same-year study anchors required')
    if any(not is_session(d) for d in anchors):
        raise ValueError('declared anchor must be an incumbent cash session')
    repository=Path(source_repository);store=Path(store_root)
    if not repository.is_dir() or not store.is_dir():
        raise ValueError('original owner source locations required')
    membership_blob=manifest['membership_blob']
    raw_membership=_git_blob(repository,membership_blob)
    registry=_json(raw_membership)
    basket=registry.get('baskets',{}).get('mag7',{})
    if basket.get('weighting')!='equal' or not isinstance(basket.get('members'),list):
        raise ValueError('existing house equal-weight membership required')
    members=[];seen=set()
    for item in basket['members']:
        if not isinstance(item,dict) or not isinstance(item.get('ticker'),str) or not _ROOT.fullmatch(item['ticker']):
            raise ValueError('unrecognized original membership identity')
        root=item['ticker'];added=_date(item.get('added'))
        removed=_date(item['removed']) if item.get('removed') is not None else None
        if root in seen or (removed is not None and removed<=added):
            raise ValueError('duplicate or invalid membership interval')
        seen.add(root)
        if added<=anchors[-1] and (removed is None or anchors[-1]<removed):
            members.append(root)
    if not 3<=len(members)<=10:
        raise ValueError('exact bounded full research roster required')
    roots=sorted(members);rinputs=manifest['roots']
    if not isinstance(rinputs,dict) or not set(rinputs).issubset(roots):
        raise ValueError('input root identity mismatch')
    greeks={d:{} for d in anchors}
    prices={};receipts={}
    for root in roots:
        source=rinputs.get(root)
        if source is None:
            receipts[root]={'state':'ROOT_NOT_SUPPLIED'}
            continue
        if not isinstance(source,dict) or set(source)!={'price_blob','greeks_sha256'}:
            raise ValueError('root source hash fields required')
        if not isinstance(source['greeks_sha256'],str) or _SHA.fullmatch(source['greeks_sha256']) is None:
            raise ValueError('Greek source sha256 identity required')
        price_bytes=_git_blob(repository,source['price_blob'])
        frame=pd.read_parquet(io.BytesIO(price_bytes))
        col=manifest['price_column']
        if not isinstance(frame.index,pd.DatetimeIndex) or col not in frame:
            raise ValueError('original price session/index missing')
        prices[root]=frame[col]
        greek_receipts=[]
        for anchor in anchors:
            frame_g,receipt=_greeks(store,root,source['greeks_sha256'],anchor)
            if frame_g is not None:
                greeks[anchor][root]=frame_g
            greek_receipts.append({'anchor':anchor.isoformat(),**receipt})
        receipts[root]={'price_git_blob':source['price_blob'],
                        'price_sha256':hashlib.sha256(price_bytes).hexdigest(),
                        'price_rows':len(frame),'price_column':col,
                        'greeks':{'state':'READ_VERIFIED' if all(x['state']=='READ_VERIFIED' for x in greek_receipts) else 'PARTIAL',
                                  'expected_sha256':source['greeks_sha256'],'anchor_receipts':greek_receipts},
                        'price_adjustment_vintage':None}
    closes=pd.DataFrame(prices) if prices else pd.DataFrame(index=pd.DatetimeIndex([]))
    end=max([anchors[-1]]+[x.date() for x in closes.index if isinstance(x,pd.Timestamp) and not pd.isna(x)])
    calendar=sessions_between(anchors[0]-timedelta(days=600),end)
    now=captured_at if captured_at is not None else datetime.now(timezone.utc)
    result=evaluate(weights={r:1/len(roots) for r in roots},greeks_by_anchor=greeks,
                    closes=closes,sessions=calendar,anchors=anchors,captured_at=now)
    result['source_receipts']={'source_use_status':'RETROSPECTIVE_UNQUALIFIED',
        'membership_git_blob':membership_blob,
        'membership_sha256':hashlib.sha256(raw_membership).hexdigest(),
        'roots':receipts,'price_basis':'source_close_adjustment_vintage_unverified',
        'rights':'not_source_qualified','historical_report_release_time':None,
        'original_source_files_changed':False}
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
        with args.manifest.open('rb') as file:
            raw=file.read(128*1024+1)
        if not 0<len(raw)<=128*1024:
            raise ValueError('bounded manifest bytes required')
        result=load_outcomes(manifest=_json(raw),source_repository=args.source_repository,
                             store_root=args.store_root)
        print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as err:
        print(f'RETROSPECTIVE_OUTCOMES_REFUSED: {err}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
