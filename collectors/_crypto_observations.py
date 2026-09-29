"""Public crypto-response evidence through the existing keep-first store owner.

No HTTP requests, credentials, strategy authority or source-qualification inference.
One receipt per response occurrence preserves A -> B -> A revisions. A receive
clock is a conservative local knowledge bound, never provider first publication.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
import fcntl
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd
from collectors import _first_seen_store as fss
from lib import config

log = logging.getLogger(__name__)
SCHEMA = 'crypto.public_response_observation.v1'
MAX_ROWS = 10000
MAX_JSON_BYTES = 2_000_000
SOURCES = {
    'okx_funding': ('okx', 'https://www.okx.com/api/v5/public/funding-rate-history'),
    'okx_taker': ('okx', 'https://www.okx.com/api/v5/rubik/stat/taker-volume'),
    'bgeo_funding': ('bgeo', 'https://bitcoin-data.com/v1/funding-rate'),
}
PARAMS = {'instId','ccy','instType','period','before','after','limit','startday','endday','day','size','page'}
FUNDING_FIELDS = {'instId','instType','fundingTime','fundingRate','realizedRate','formulaType','method','nextFundingTime','fundingInterval'}
BGEO_FIELDS = {'d','unixTs','fundingRate','markPrice','delayed','message','funding_rate'}
COLUMNS = ('capture_id','schema','source_id','endpoint','params_json','payload_json','payload_sha256',
           'body_sha256','received_at','first_seen','fetched_at','http_status','row_count',
           'provider_first_published_at','unit','timestamp_role','finality')


def utc(value: Any) -> pd.Timestamp:
    if value is None: raise ValueError('UTC receive/as-of timestamp required')
    try: stamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc: raise ValueError('Invalid UTC timestamp') from exc
    if pd.isna(stamp) or stamp.tz is None: raise ValueError('Timezone-aware timestamp required')
    return stamp.tz_convert('UTC')


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _safe_payload(source: str, payload: Any) -> tuple[Any, int]:
    if source == 'bgeo_funding':
        if not isinstance(payload,list): raise ValueError('Expected public list payload')
        rows = payload
        if any(not isinstance(x,dict) for x in rows): raise ValueError('Expected metric records')
        safe = [{k:v for k,v in x.items() if k in BGEO_FIELDS} for x in rows]
    else:
        if not isinstance(payload,dict) or not isinstance(payload.get('data'),list): raise ValueError('Expected public data envelope')
        rows = payload['data']
        if source == 'okx_funding':
            if any(not isinstance(x,dict) for x in rows): raise ValueError('Expected funding records')
            values = [{k:v for k,v in x.items() if k in FUNDING_FIELDS} for x in rows]
        else:
            if any(not isinstance(x,(list,tuple)) or len(x)!=3 for x in rows): raise ValueError('Expected ts,sell,buy triplets')
            values = [list(x) for x in rows]
        safe = {'code':payload.get('code'), 'data':values}
    if len(rows)>MAX_ROWS: raise ValueError('Public response row bound exceeded')
    if len(canonical(safe).encode())>MAX_JSON_BYTES: raise ValueError('Public response byte bound exceeded')
    return safe,len(rows)


def build_capture(source_id: str, params: dict, payload: Any, received_at: Any,
                  *, body: bytes | None = None, http_status: int = 200) -> dict:
    if source_id not in SOURCES: raise ValueError('Unregistered public response scope')
    if not isinstance(params,dict): raise ValueError('Request parameters required')
    safe_params = {k:v for k,v in params.items() if k in PARAMS}
    if any(not isinstance(v,(str,int,float,bool,type(None))) for v in safe_params.values()):
        raise ValueError('Non-scalar request scope')
    safe,n = _safe_payload(source_id,payload);stamp=utc(received_at).isoformat()
    value={'schema':SCHEMA,'source_id':source_id,'endpoint':SOURCES[source_id][1],
           'params_json':canonical(safe_params),'payload_json':canonical(safe),'payload_sha256':digest(canonical(safe)),
           'body_sha256':digest(body) if isinstance(body,bytes) else None,
           'received_at':stamp,'first_seen':stamp,'fetched_at':stamp,'http_status':int(http_status),'row_count':n,
           'provider_first_published_at':None,'unit':None,'timestamp_role':None,'finality':None}
    value['capture_id']=digest(canonical(value))
    return value


def checked(capture: dict) -> dict:
    c={k:(None if capture.get(k) is None or (isinstance(capture.get(k),float) and math.isnan(capture[k])) else capture.get(k)) for k in COLUMNS}
    c['row_count']=int(c['row_count']);c['http_status']=int(c['http_status'])
    if c['schema']!=SCHEMA or c['source_id'] not in SOURCES or c['endpoint']!=SOURCES[c['source_id']][1]:
        raise ValueError('Capture schema/scope mismatch')
    if c['first_seen']!=c['received_at'] or c['fetched_at']!=c['received_at']: raise ValueError('Receive-clock mismatch')
    utc(c['received_at'])
    safe,n=_safe_payload(c['source_id'],json.loads(c['payload_json']))
    if canonical(safe)!=c['payload_json'] or n!=c['row_count'] or digest(c['payload_json'])!=c['payload_sha256']:
        raise ValueError('Payload identity mismatch')
    params=json.loads(c['params_json'])
    if set(params)-PARAMS or canonical(params)!=c['params_json']: raise ValueError('Unexpected request parameters')
    if any(c[k] is not None for k in ['provider_first_published_at','unit','timestamp_role','finality']):
        raise ValueError('Capture must not self-certify missing semantics')
    material={k:v for k,v in c.items() if k!='capture_id'}
    if digest(canonical(material))!=c['capture_id']: raise ValueError('Capture identity mismatch')
    return c


def capture_path(source_id: str, *, root: Path | None = None) -> Path:
    if source_id not in SOURCES: raise ValueError('Unknown source')
    return Path(root if root is not None else config.data_dir())/SOURCES[source_id][0]/'source_observations.parquet'


def persist_capture(capture: dict, *, root: Path | None = None) -> dict:
    """Nonblocking per-file exclusion around the incumbent first-seen writer."""
    try:
        c=checked(capture);path=capture_path(c['source_id'],root=root);path.parent.mkdir(parents=True,exist_ok=True)
        with path.with_suffix('.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            existing=fss.read_store(path,COLUMNS)
            if existing is None: raise ValueError('Present evidence store is unreadable')
            if existing.capture_id.duplicated().any(): raise ValueError('Duplicate stored capture identity')
            for previous in existing.to_dict('records'):
                previous = checked(previous)
                if SOURCES[previous['source_id']][0] != SOURCES[c['source_id']][0]:
                    raise ValueError('Stored provider scope mismatch')
            old=existing.loc[existing.capture_id==c['capture_id']]
            if not old.empty:
                if len(old)!=1 or checked(old.iloc[0].to_dict())!=c: raise ValueError('Conflicting capture identity')
                return {'status':'already_present','capture_id':c['capture_id']}
            fss.accrue_keep_first(path,[c],columns=COLUMNS,key=['capture_id'],sort_by=['received_at','capture_id'])
            stored=fss.read_store(path,COLUMNS)
            if stored is None: raise ValueError('Capture persistence readback unavailable')
            match=stored.loc[stored.capture_id==c['capture_id']]
            if len(match)!=1 or checked(match.iloc[0].to_dict())!=c: raise ValueError('Capture persistence not proven')
        return {'status':'stored','capture_id':c['capture_id']}
    except Exception as exc:
        # No provider payload, URL, headers or credential-bearing error string.
        log.warning('Crypto source evidence unavailable (%s)',type(exc).__name__)
        return {'status':'unavailable','error_type':type(exc).__name__}


def load_asof(source_id: str, as_of: Any, *, root: Path | None = None) -> pd.DataFrame:
    stamp=utc(as_of);f=fss.read_store(capture_path(source_id,root=root),COLUMNS)
    if f is None: raise ValueError('Evidence store unreadable; not an empty history')
    if f.empty:return f
    rows=[checked(x) for x in f.to_dict('records')]
    f=pd.DataFrame(rows)
    if f.capture_id.duplicated().any(): raise ValueError('Duplicate capture identity')
    return f.loc[(f.source_id==source_id)&(pd.to_datetime(f.received_at,utc=True)<=stamp)].copy()


def _rate(value: Any) -> float | None:
    if isinstance(value,bool):return None
    try:n=float(value)
    except (ValueError,TypeError,OverflowError):return None
    return n if math.isfinite(n) else None


def funding_asof(captures: pd.DataFrame, as_of: Any, *, inst_id: str = 'BTC-USDT-SWAP') -> list[dict]:
    """Known captured revisions, not reconstructed original publication history."""
    at=utc(as_of);events={}
    for raw in captures.to_dict('records'):
        c=checked(raw);rec=utc(c['received_at'])
        if c['source_id']!='okx_funding' or rec>at or c['http_status']!=200:continue
        payload=json.loads(c['payload_json'])
        if json.loads(c['params_json']).get('instId') != inst_id:continue
        if str(payload.get('code'))!='0':continue
        for row in payload['data']:
            if row.get('instId')!=inst_id:continue
            try:t=pd.to_datetime(int(row['fundingTime']),unit='ms',utc=True)
            except (ValueError,TypeError,KeyError,OverflowError):continue
            if pd.isna(t):continue
            key=(inst_id,t.isoformat());fingerprint=canonical(row);old=events.get(key)
            e={'instrument':inst_id,'settlement_at':t.isoformat(),'received_at':rec.isoformat(),
               'predicted_rate':_rate(row.get('fundingRate')),'settled_rate':_rate(row.get('realizedRate')),
               'formula_type':row.get('formulaType'),'method':row.get('method'),'interval_hours':None,
               'annualized_settled_pct':None,'provider_first_published_at':None,'capture_id':c['capture_id'],
               'status':'observed','_raw':fingerprint}
            if t>rec:e.update(status='receipt_before_settlement',settled_rate=None)
            if old is None or rec>utc(old['received_at']):events[key]=e
            elif rec==utc(old['received_at']) and old['_raw']!=fingerprint:
                old.update(status='conflicting_capture',predicted_rate=None,settled_rate=None)
    return [{k:v for k,v in e.items() if k!='_raw'} for _,e in sorted(events.items())]


def recording_run(method):
    """Capture only during existing public fetch; private parser tests stay pure."""
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        self._crypto_capture_active=True;self.source_capture_status=[]
        try:return method(self,*args,**kwargs)
        finally:self._crypto_capture_active=False
    return wrapped


def record_response(adapter, source_id, params, response, payload, received_at, *, endpoint=None):
    if not getattr(adapter,'_crypto_capture_active',False):return {'status':'inactive'}
    try:
        expected = SOURCES[source_id][1]
        if endpoint != expected: raise ValueError('Configured endpoint does not match evidence source')
        actual = getattr(response, 'url', None)
        if isinstance(actual, str):
            parsed = urlsplit(actual)
            base = parsed._replace(query='', fragment='').geturl()
            if parsed.username or parsed.password or base != expected:
                raise ValueError('Response endpoint does not match request evidence')
        capture=build_capture(source_id,params,payload,received_at,
                              body=getattr(response,'content',None),http_status=getattr(response,'status_code',200))
        result=persist_capture(capture)
    except Exception as exc:result={'status':'unavailable','error_type':type(exc).__name__}
    adapter.source_capture_status.append(dict(result,source_id=source_id))
    return result


def fetch_result_status(adapter,frames):
    return 'stale' if any(x['status']=='unavailable' for x in getattr(adapter,'source_capture_status',[])) else None
