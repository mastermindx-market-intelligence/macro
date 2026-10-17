"""Date-only first-print chronology projected from the existing Data OS reader.

The house FRED output_type=4 store contains initial releases, not every revised
as-of value. A realtime_start date is NOT an intraday publication timestamp. This
module preserves both limitations and never invents forecasts, surprise, units,
release-time precision, or strategy eligibility from the first-print snapshot.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.neuralweb.market_memory_history_archive import _bytes, _regular_file, _write_exclusive

SCHEMA='market_memory.first_print_chronology.v1'
MAX_ROWS=50_000
MAX_BYTES=32*1024*1024
_HEX=re.compile(r'[a-f0-9]{64}\Z')
_SERIES=re.compile(r'[A-Za-z0-9_]{1,80}\Z')
SOURCE_FIELDS=frozenset({'schema','profile','source','query_receipts','rows_sha256','rows',
    'pit_backtest_eligible','intraday_publication_time_known','full_revision_history'})


def _day(value: str) -> str:
    if type(value) is not str:
        raise HistoricalExperienceError('explicit calendar date required')
    candidate=value.removesuffix('T00:00:00')
    try:
        if date.fromisoformat(candidate).isoformat()!=candidate: raise ValueError()
    except ValueError as exc:
        raise HistoricalExperienceError('date-only source must not invent or discard an intraday clock') from exc
    return candidate


def _flags(value: dict) -> None:
    if any(value.get(k) is not False for k in
           ('pit_backtest_eligible','intraday_publication_time_known','full_revision_history')):
        raise HistoricalExperienceError('first-print chronology cannot upgrade source qualification')


def build_macro_chronology(source_packet: dict, *, start: str, end: str) -> dict:
    start,end=_day(start),_day(end)
    if start>end: raise HistoricalExperienceError('reversed chronology dates')
    if type(source_packet) is not dict or set(source_packet)!=SOURCE_FIELDS:
        raise HistoricalExperienceError('exact retained macro source packet required')
    if source_packet['schema']!='market_memory.macro_source_selection.v1' or source_packet['profile']!='FRED_INITIAL_RELEASE_ONLY':
        raise HistoricalExperienceError('unsupported macro source profile')
    _flags(source_packet)
    source=source_packet['source']
    if (type(source) is not dict or source.get('ref')!='macro_snapshot:fred_vintage/vintages.parquet'
            or type(source.get('file_version')) is not str or not source['file_version'].startswith('statv1:')
            or source.get('evidence_kind')!='unqualified_snapshot'):
        raise HistoricalExperienceError('existing snapshot source binding required')
    receipts=source_packet['query_receipts']
    if type(receipts) is not list or not 1<=len(receipts)<=250 or any(type(x) is not str or not _HEX.fullmatch(x) for x in receipts):
        raise HistoricalExperienceError('bounded Data OS query receipts required')
    rows=source_packet['rows']
    if type(rows) is not list or not 1<=len(rows)<=MAX_ROWS:
        raise HistoricalExperienceError('bounded macro source rows required')
    raw=_bytes(rows)
    if len(raw)>MAX_BYTES or hashlib.sha256(raw).hexdigest()!=source_packet['rows_sha256']:
        raise HistoricalExperienceError('macro source rows digest mismatch or budget exceeded')
    events=[];seen=set()
    for row in rows:
        if type(row) is not dict or set(row)!={'series','period','value','realtime_start','realtime_end'}:
            raise HistoricalExperienceError('exact existing FRED source columns required')
        series=row['series']
        if type(series) is not str or not _SERIES.fullmatch(series):
            raise HistoricalExperienceError('invalid FRED series identifier')
        period,released=_day(row['period']),_day(row['realtime_start'])
        superseded=_day(row['realtime_end']) if row['realtime_end'] is not None else None
        if superseded is not None and superseded<released:
            raise HistoricalExperienceError('reversed source real-time interval')
        key=series,period
        if key in seen: raise HistoricalExperienceError('duplicate period cannot masquerade as one initial release')
        seen.add(key)
        value=row['value']
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
            raise HistoricalExperienceError('finite initial-print value or null required')
        if start<=released<=end:
            events.append({'calendar_date':released,'series':series,'period':period,'value':value,
                'first_vintage_valid_through':superseded,'date_basis':'fred_realtime_start_date_only',
                'source_units':'NOT_RETAINED','period_after_vintage_date':period>released})
    events.sort(key=lambda x:(x['calendar_date'],x['series'],x['period']))
    result={'schema':SCHEMA,'profile':'FRED_INITIAL_RELEASE_ONLY','mode':'RETROSPECTIVE_EXPLORATORY',
        'start':start,'end':end,'events':events,'source':dict(source),
        'source_rows_sha256':source_packet['rows_sha256'],'query_receipts':list(receipts),
        'pit_backtest_eligible':False,'intraday_publication_time_known':False,
        'full_revision_history':False,'units_retained':False,
        'date_basis':'fred_realtime_start_date_only',
        'coverage':{'input_rows':len(rows),'events':len(events),'series':dict(sorted(Counter(e['series'] for e in events).items())),
                    'calendar_dates':len({e['calendar_date'] for e in events})},
        'limitations':['First prints are not the full evolving vintage matrix.',
            'The source date is not an authenticated intraday release time.',
            'Source units and contemporaneous consensus are absent from this retained snapshot.',
            'Later first prints do not replace earlier period records.',
            'This is a projection of a local source snapshot, not fresh provider authentication.']}
    result['chronology_id']='mmfirst_'+hashlib.sha256(_bytes(result)).hexdigest()
    return result


def select_macro_date(chronology: dict, calendar_date: str, *, limit: int=100) -> dict:
    day=_day(calendar_date)
    _validate(chronology)
    if type(limit) is not int or not 1<=limit<=200:
        raise HistoricalExperienceError('one to 200 first-print rows per date response')
    # Revision-end metadata is only learned later. Omit it uniformly (rather
    # than mask conditionally, which would still reveal that a revision exists).
    # The exact retained chronology is unchanged and remains inspectable.
    selected=[{k:v for k,v in r.items() if k!='first_vintage_valid_through'}
              for r in chronology['events'] if r['calendar_date']==day]
    return {'schema':SCHEMA,'chronology_id':chronology['chronology_id'],'calendar_date':day,
        'events':selected[:limit],'total_events':len(selected),'remaining_events':max(0,len(selected)-limit),
        'date_basis':'fred_realtime_start_date_only','pit_backtest_eligible':False,
        'intraday_publication_time_known':False,'full_revision_history':False,'units_retained':False,
        'source_rows_sha256':chronology['source_rows_sha256'],
        'revision_end_metadata':'withheld_from_daily_projection',
        'declared_archive_window':{'start':chronology['start'],'end':chronology['end']},
        'within_declared_archive_window':chronology['start']<=day<=chronology['end'],
        'calendar_completeness_proven':False}


def _validate(chronology: dict) -> None:
    if (type(chronology) is not dict or chronology.get('schema')!=SCHEMA
            or chronology.get('mode')!='RETROSPECTIVE_EXPLORATORY'
            or chronology.get('units_retained') is not False):
        raise HistoricalExperienceError('invalid first-print chronology contract')
    _flags(chronology)
    if _day(chronology.get('start'))>_day(chronology.get('end')):
        raise HistoricalExperienceError('reversed chronology dates')
    if type(chronology.get('events')) is not list or len(chronology['events'])>MAX_ROWS:
        raise HistoricalExperienceError('first-print chronology row budget exceeded')
    identity={k:v for k,v in chronology.items() if k!='chronology_id'}
    if chronology.get('chronology_id')!='mmfirst_'+hashlib.sha256(_bytes(identity)).hexdigest():
        raise HistoricalExperienceError('first-print chronology identity mismatch')


def write_macro_chronology(chronology: dict, destination: Path) -> dict:
    _validate(chronology)
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise HistoricalExperienceError('macro evidence path cannot traverse symlinks')
    raw=_bytes(chronology)
    if len(raw)>MAX_BYTES:raise HistoricalExperienceError('macro evidence byte budget exceeded')
    _write_exclusive(destination,raw)
    return {'chronology_id':chronology['chronology_id'],'sha256':hashlib.sha256(raw).hexdigest(),
            'bytes':len(raw),'events':len(chronology['events'])}


def read_macro_chronology(path: Path, *, expected_sha256: str) -> dict:
    if type(expected_sha256) is not str or not _HEX.fullmatch(expected_sha256):
        raise HistoricalExperienceError('exact first-print chronology digest required')
    path=Path(path);raw=_regular_file(path.parent,path.name,MAX_BYTES)
    return read_macro_chronology_bytes(raw, expected_sha256=expected_sha256)


def read_macro_chronology_bytes(raw: bytes, *, expected_sha256: str) -> dict:
    """Decode evidence already read by an admitted source owner with one validator."""
    if type(expected_sha256) is not str or not _HEX.fullmatch(expected_sha256):
        raise HistoricalExperienceError('exact first-print chronology digest required')
    if type(raw) is not bytes or len(raw)>MAX_BYTES:
        raise HistoricalExperienceError('first-print chronology bytes exceed budget')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise HistoricalExperienceError('first-print chronology digest mismatch')
    try:result=json.loads(raw)
    except (ValueError,UnicodeError) as exc:raise HistoricalExperienceError('invalid chronology JSON') from exc
    _validate(result)
    return result
