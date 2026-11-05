"""Post-store original CSV evidence for exact ECB historical policy points.

The existing current-field pair stays intact. This additional native source
receipt authenticates original per-row status/confidentiality for the existing
policy comparator; it mints no disclosure or historical-availability grant.
"""
from pathlib import Path
from io import BytesIO
import json
import math
import pandas as pd
from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys, _reject_nonstandard_constant, _observe_native_path
from lib.intl_boe_publication import _sha, _json, _utc, _put, _publish

COLUMN = 'ez_depo_rate'
SCHEMA = 'intl.ecb_policy_points_materialization.v1'
DIRECTORY = Path('intl_macro/publication/ez_depo_rate_policy')
SOURCE_URL = 'https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=1999-01-01'
SOURCE_ID = 'D.U2.EUR.4F.KR.DFR.LEV'
LIMIT = 8 * 1024 * 1024
ARTIFACT_LIMIT = 16 * 1024 * 1024
_KEYS = {'schema','column','source_id','source_url','source_sha256','artifact_sha256',
         'requested_at','response_received_at','input_verified_at','committed_at',
         'provider_published_at','revision_vintage','rows','first_observation','last_observation'}


def _parse(raw):
    from lib.intl_ecb_policy_source import parse_ecb_policy_csv
    return parse_ecb_policy_csv(raw)


def _series(frame):
    if type(frame) is not pd.DataFrame or frame.columns.tolist() != [COLUMN]:
        raise ValueError('invalid ECB stored column')
    s=frame[COLUMN]
    if (not isinstance(s.index,pd.DatetimeIndex) or s.index.tz is not None or s.index.hasnans
            or s.index.has_duplicates or not s.index.is_monotonic_increasing
            or not s.index.equals(s.index.normalize()) or s.empty
            or not pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_bool_dtype(s.dtype)
            or not all(math.isfinite(float(v))for v in s.dropna())):
        raise ValueError('invalid ECB stored geometry')
    return s


def _coverage(parsed,series):
    values={stamp.date().isoformat():float(v)for stamp,v in series.items()if pd.notna(v)}
    observed=[r for r in parsed['observations']if r['status']=='observed']
    if not observed or any(r['date']not in values or values[r['date']]!=r['value']for r in observed):
        raise ValueError('ECB original observations differ from committed bytes')
    # Explicitly withheld rows are never read from this cache map by a policy
    # consumer; it receives the original parsed rows, not extra stored history.


def _receipt(receipt):
    if (type(receipt)is not dict or set(receipt)!=_KEYS or receipt['schema']!=SCHEMA
            or receipt['column']!=COLUMN or receipt['source_id']!=SOURCE_ID or receipt['source_url']!=SOURCE_URL
            or receipt['provider_published_at']is not None or receipt['revision_vintage']is not None
            or type(receipt['rows'])is not int or not 0<receipt['rows']<=32000):
        raise ValueError('invalid ECB capture')
    for key in ('source_sha256','artifact_sha256'):
        digest=receipt[key]
        if type(digest)is not str or len(digest)!=64 or any(c not in '0123456789abcdef'for c in digest):
            raise ValueError('invalid ECB capture digest')
    if not (_utc(receipt['requested_at'])<=_utc(receipt['response_received_at'])
            <=_utc(receipt['input_verified_at'])<=_utc(receipt['committed_at'])):
        raise ValueError('invalid ECB capture chronology')


def capture_ecb_policy_commit(*,data_root,returned,response_bytes,source_url,
                              requested_at,response_received_at,input_verified_at,committed_at):
    if source_url!=SOURCE_URL or type(response_bytes)is not bytes or not 0<len(response_bytes)<=LIMIT:
        raise ValueError('unrecognized ECB original source')
    parsed=_parse(response_bytes);rows=parsed['observations'];root=Path(data_root)
    _coverage(parsed,_series(returned))
    artifact=_read_stable_once(root/'intl_macro'/f'{COLUMN}.parquet',ARTIFACT_LIMIT)
    _coverage(parsed,_series(pd.read_parquet(BytesIO(artifact))))
    receipt={'schema':SCHEMA,'column':COLUMN,'source_id':SOURCE_ID,'source_url':source_url,
        'source_sha256':_sha(response_bytes),'artifact_sha256':_sha(artifact),
        'requested_at':requested_at,'response_received_at':response_received_at,
        'input_verified_at':input_verified_at,'committed_at':committed_at,
        'provider_published_at':None,'revision_vintage':None,'rows':len(rows),
        'first_observation':rows[0]['date'],'last_observation':rows[-1]['date']}
    _receipt(receipt);raw=_json(receipt);directory=root/DIRECTORY
    _put(directory/(receipt['source_sha256']+'.csv'),response_bytes,LIMIT)
    _put(directory/(_sha(raw)+'.json'),raw,LIMIT)
    _publish(directory,raw)
    return receipt


def read_ecb_policy_materialization(*,data_root):
    root=Path(data_root);directory=root/DIRECTORY;pointer=directory/'current.json';digest=None
    try:
        _observe_native_path(pointer)
        pointer.lstat()
    except FileNotFoundError:return {'status':'missing','receipt':None,'receipt_sha256':None,'parsed':None}
    except OSError:return {'status':'failed','receipt':None,'receipt_sha256':None,'parsed':None}
    try:
        raw=_read_stable_once(pointer,LIMIT)
        if _read_stable_once(directory/(_sha(raw)+'.json'),LIMIT)!=raw:raise ValueError('ECB selector changed')
        receipt=json.loads(raw,object_pairs_hook=_reject_duplicate_keys,parse_constant=_reject_nonstandard_constant)
        _receipt(receipt);digest=_sha(raw)
        source=_read_stable_once(directory/(receipt['source_sha256']+'.csv'),LIMIT)
        artifact=_read_stable_once(root/'intl_macro'/f'{COLUMN}.parquet',ARTIFACT_LIMIT)
        if _sha(source)!=receipt['source_sha256']or _sha(artifact)!=receipt['artifact_sha256']:
            raise ValueError('ECB capture source/store identity changed')
        parsed=_parse(source);rows=parsed['observations']
        if (len(rows)!=receipt['rows']or rows[0]['date']!=receipt['first_observation']
                or rows[-1]['date']!=receipt['last_observation']):raise ValueError('ECB capture row domain changed')
        _coverage(parsed,_series(pd.read_parquet(BytesIO(artifact))))
        return {'status':'ready','receipt':receipt,'receipt_sha256':digest,'parsed':parsed,'source_bytes':source}
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        return {'status':'failed','receipt':None,'receipt_sha256':digest,'parsed':None}
