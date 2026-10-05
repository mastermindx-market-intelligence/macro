"""Bridge existing parquet owners to the economy contract; never load demo data.

Each value requires an attributable publication receipt. Existing columns without
that receipt remain unavailable in this lens; they are not relabeled as current.
Collectors can use `frames_from_receipt` and their NORMAL upsert owner to enrich
those same tables. This module never writes to the store or creates a collector.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import hashlib,json,re
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from engine.china_economy import month_index,month_from_index,month_end,timestamp,build_economy,number


def binding(path):
    if '/' not in path or '.' not in path:raise ValueError('owner binding must be group/table.column')
    group,tail=path.split('/',1);table,column=tail.split('.',1)
    if not all(x and all(c.isalnum() or c=='_' for c in x) for x in (group,table,column)):
        raise ValueError('unsafe store binding')
    return group,table,column


def _text(value):
    return value if isinstance(value,str) and value.strip() else None


def value_receipt_digest(column, period, value, receipt):
    """Bind the stored number to its period/definition/source, not just a URL.

    Corruption detection, not a signature or proof of source authenticity.
    Float normalization tolerates parquet int-to-float round trips.
    """
    month_index(period)
    n = number(value)
    if value is not None and not pd.isna(value) and n is None:
        raise ValueError('invalid_receipt_value')
    normalized = None if n is None else format(0.0 if n == 0 else n, '.17g')
    payload = [column, period, normalized] + [receipt.get(k) for k in
        ('source_url','published_at','response_sha256','definition_id','observed_at')]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def document_from_store(read,catalog,as_of=None,reference_period=None):
    now=timestamp(as_of) if as_of else datetime.now(timezone.utc)
    now=now.astimezone(ZoneInfo('Asia/Shanghai'))
    # Previous completed calendar month; do not substitute an older complete
    # snapshot merely to make a missing release look healthy.
    reference_period=reference_period or month_from_index(now.year*12+now.month-2)
    month_index(reference_period)
    cache={};errors={};sources={};observations=[]
    for ident,meta in catalog.items():
        group,table,col=binding(meta['owner_path']);key=group+'/'+table
        if key not in cache:
            try:
                frame=read(group,table)
                if frame is not None and not frame.empty:
                    frame=frame.copy();frame.index=pd.to_datetime(frame.index,errors='raise')
                    if frame.index.has_duplicates or frame.index.to_period('M').has_duplicates:raise ValueError('duplicate store dates')
                    if frame.columns.has_duplicates:raise ValueError('duplicate store columns')
                    frame=frame.sort_index()
                cache[key]=frame
            except Exception as exc:
                errors[key]=type(exc).__name__+': '+str(exc)[:120];cache[key]=None
        f=cache[key]
        if f is None or f.empty or col not in f:continue
        required=[col+'__source_url',col+'__published_at',col+'__response_sha256',col+'__definition_id',col+'__observed_at']
        if not all(c in f for c in required):
            errors[key+'.'+col]='publication_receipt_missing; not replaced with a modeled release time';continue
        for date,row in f.iterrows():
            url,pub,sha,definition,observed=(_text(row.get(c)) for c in required)
            if not all([url,pub,sha,definition,observed]) or not re.fullmatch(r'[0-9a-fA-F]{64}',sha or ''):
                errors[key+'.'+col]='incomplete_publication_receipt';continue
            try:
                published_at=timestamp(pub);observed_at=timestamp(observed)
                if published_at>observed_at:
                    raise ValueError('publication_after_acquisition')
                if observed_at>now:
                    # It was not acquired by the requested cutoff. A past release
                    # date cannot make a subsequently acquired revision available.
                    errors[key+'.'+col]='acquisition_after_cutoff';continue
            except (ValueError,TypeError) as exc:
                errors[key+'.'+col]='invalid_receipt_chronology: '+str(exc);continue
            digest = row.get(col+'__value_sha256')
            try:
                bound = value_receipt_digest(col, date.strftime('%Y-%m'), row[col],
                    dict(source_url=url,published_at=pub,response_sha256=sha,definition_id=definition,observed_at=observed))
            except (ValueError,TypeError):
                bound = None
            if not isinstance(digest,str) or digest != bound:
                errors[key+'.'+col]='value_receipt_mismatch; stored number is not verified by attached metadata'
                continue
            sid=hashlib.sha256((url+'|'+pub+'|'+sha+'|'+observed).encode()).hexdigest()[:24]
            sources[sid]={'id':sid,'publisher':url.split('/')[2],'title':meta['label_en'],
                'url':url,'published_at':pub,'observed_at':observed,'response_sha256':sha,
                'history_vintage':'observed published revision','access_proof':'existing collector receipt',
                'publication_precision':row.get(col+'__publication_precision','unknown'),
                'parser_version':row.get(col+'__parser_version','unknown'),'value_receipt_verified':True,
                'receipt_metadata_present':True,'runtime_acceptance_verified':False,'commercial_redistribution_review':'must be checked by release owner'}
            value=row[col]
            observations.append({'metric_id':ident,'period':date.strftime('%Y-%m'),'value':None if pd.isna(value) else value,
                'source_id':sid,'published_at':pub,'vintage_id':sha,'definition_id':definition,
                'observed_at':observed,'raw_response_sha256':sha,'ingestion_class':'existing_collector_http_receipt'})
    return {'schema':'mastermind.china_economy_store_input.v1','as_of':now.isoformat(),
        'display_reference_period':reference_period,'input_class':'existing_parquet_owners_with_publication_receipts',
        'catalog':catalog,'sources':sources,'observations':observations,'source_errors':errors}


def build_from_store(read=None,catalog=None,as_of=None,reference_period=None):
    if read is None:
        from lib import store
        read=store.read
    if catalog is None:
        p=Path(__file__).resolve().parents[1]/'config/china_economy_catalog.json'
        catalog=json.loads(p.read_text())['metrics']
    document=document_from_store(read,catalog,as_of,reference_period)
    result=build_economy(document)
    result['source_errors']=document['source_errors']
    # This is a build-time snapshot of published statistics, not a live feed.
    result['is_live_feed']=False
    return result


def frames_from_receipt(points,receipt,catalog):
    """Return {existing_group/table: wide DataFrame}; caller owns every upsert.

    A date index remains unique, matching lib.store's contract. Never use a
    date-only long table that would overwrite other indicators on the same date.
    """
    data=defaultdict(dict)
    for point in points:
        ident=point['metric_id'];meta=catalog[ident];group,table,col=binding(meta['owner_path'])
        date=point['period']+'-01';month_index(point['period'])
        row=data[group+'/'+table].setdefault(date,{})
        if col in row:raise ValueError('duplicate column/period in one acquisition')
        value=number(point['value'])
        if point['value'] is not None and value is None:raise ValueError('invalid point value')
        published,observed=timestamp(receipt['published_at']),timestamp(receipt['observed_at'])
        if published>observed:raise ValueError('publication_after_acquisition')
        if not re.fullmatch(r'[0-9a-f]{64}',receipt['response_sha256']):raise ValueError('invalid response digest')
        if not isinstance(receipt['url'],str) or not receipt['url'].startswith('https://'):raise ValueError('invalid source URL')
        row[col]=value
        fields={'source_url':receipt['url'],'published_at':receipt['published_at'],
            'response_sha256':receipt['response_sha256'],'definition_id':meta['definition_id'],
            'observed_at':receipt['observed_at']}
        row.update({col+'__'+k:v for k,v in fields.items()})
        row[col+'__value_sha256']=value_receipt_digest(col,point['period'],value,fields)
        row[col+'__publication_precision']=receipt.get('publication_precision','unknown')
        row[col+'__parser_version']=receipt.get('parser_version','unspecified')
    result={}
    for key,rows in data.items():
        f=pd.DataFrame.from_dict(rows,orient='index');f.index=pd.to_datetime(f.index);f.index.name='date';result[key]=f.sort_index()
    return result


def read_metric_from_store(ident, read, as_of=None, reference_period=None):
    """Read one catalog measure through the SAME admission used by the overview.

    This is a caller convenience, not another validator or publication owner.
    It prevents a detailed dialog from bypassing the receipt/definition checks.
    """
    from engine.china_economy import metric_view
    catalog = json.loads((Path(__file__).resolve().parents[1] /
                          'config/china_economy_catalog.json').read_text())['metrics']
    meta = catalog[ident]
    doc = document_from_store(read, {ident: meta}, as_of, reference_period)
    result = metric_view(meta, doc['observations'], doc['sources'],
                         timestamp(doc['as_of']), doc['display_reference_period'])
    result['source_errors'] = doc['source_errors']
    return result
