"""Bounded projections of the retained earnings-call source, without re-storage.

A caller owns the source descriptor and must finish its version/mutation guard.
Report dates and speaker names are source labels, not inferred publication times,
roles or historical security identities. No Terminal/TFG/Q&A intake is invoked.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import re
from typing import BinaryIO

from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.neuralweb.market_memory_history_archive import _date

DATE_SCHEMA = 'market_memory.historical_transcript_date.v1'
BODY_SCHEMA = 'market_memory.historical_transcript_page.v1'
CATALOG_SCHEMA = 'market_memory.historical_transcript_catalog.v1'
SOURCE_FILENAME = 'stock_earning_call_transcripts.parquet'
METADATA_FIELDS = ('symbol', 'fiscal_year', 'fiscal_quarter', 'report_date', 'transcripts_id')
MAX_FILE_BYTES = 4 * 1024**3
MAX_SOURCE_ROWS = 500_000
MAX_ROW_GROUPS = 4096
MAX_METADATA_BYTES = 64 * 1024**2
MAX_BODY_GROUP_BYTES = 64 * 1024**2
MAX_RECORD_BYTES = 8 * 1024**2
MAX_PARAGRAPHS = 10_000
MAX_PAGE_CHARS = 12_000
MAX_PAGE_JSON_BYTES = 48 * 1024
PAGE_SIZE = 50
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}\Z')


def _bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def _hash(value) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _digest(value: str) -> None:
    if type(value) is not str or not _HASH.fullmatch(value):
        raise HistoricalExperienceError('exact transcript digest required')


def _integer(value: int, lo: int, hi: int) -> None:
    if type(value) is not int or not lo <= value <= hi:
        raise HistoricalExperienceError('bounded transcript index or cursor required')


def _metadata(row: dict) -> dict:
    if set(row) != set(METADATA_FIELDS):
        raise HistoricalExperienceError('exact transcript metadata fields required')
    if type(row['symbol']) is not str or not _LABEL.fullmatch(row['symbol']):
        raise HistoricalExperienceError('invalid source symbol label')
    _integer(row['fiscal_year'], 1900, 2200)
    _integer(row['fiscal_quarter'], 1, 4)
    _date(row['report_date'])
    if row['transcripts_id'] is not None:
        # The retained source ID is int32; preserve exact JS/Python metadata hashes.
        _integer(row['transcripts_id'], 0, 2**31 - 1)
    return row


@contextmanager
def _source(stream: BinaryIO, file_bytes: int):
    _integer(file_bytes, 1, MAX_FILE_BYTES)
    import pyarrow.parquet as pq
    pf = None
    try:
        pf = pq.ParquetFile(stream, pre_buffer=False)
        if (pf.metadata.num_rows > MAX_SOURCE_ROWS
                or pf.metadata.num_row_groups > MAX_ROW_GROUPS
                or pf.schema_arrow.names != [*METADATA_FIELDS, 'transcripts']):
            raise HistoricalExperienceError('unsupported or oversized transcript source')
        yield pf
    except HistoricalExperienceError:
        raise
    except (ValueError, TypeError, KeyError, OSError, OverflowError, UnicodeError) as exc:
        raise HistoricalExperienceError('invalid retained transcript source') from exc
    finally:
        if pf is not None:
            pf.close()


def _scan_metadata(pf, day: str | None):
    seen = set()
    matches = []
    first = last = None
    count = logical_bytes = 0
    digest = hashlib.sha256(b'[')
    for batch in pf.iter_batches(batch_size=4096, columns=list(METADATA_FIELDS), use_threads=False):
        logical_bytes += batch.nbytes
        if logical_bytes > MAX_METADATA_BYTES:
            raise HistoricalExperienceError('transcript metadata logical byte budget exceeded')
        for value in batch.to_pylist():
            meta = _metadata(value)
            key = meta['symbol'], meta['fiscal_year'], meta['fiscal_quarter']
            if key in seen:
                raise HistoricalExperienceError('duplicate source symbol/fiscal-period record')
            seen.add(key)
            if count:
                digest.update(b',')
            digest.update(_bytes(meta))
            when = meta['report_date']
            first = when if first is None else min(first, when)
            last = when if last is None else max(last, when)
            if day is None:
                matches.append([*[meta[k] for k in METADATA_FIELDS], count])
            elif day == when:
                matches.append({**meta, 'source_row_position': count,
                    'metadata_sha256': _hash(meta), 'body_status': 'NOT_READ'})
            count += 1
            if count > MAX_SOURCE_ROWS:
                raise HistoricalExperienceError('transcript row budget exceeded')
    digest.update(b']')
    if count != pf.metadata.num_rows:
        raise HistoricalExperienceError('transcript metadata count mismatch')
    return matches, {'source_rows': count, 'source_date_range': {'first': first, 'last': last},
        'metadata_projection_sha256': digest.hexdigest(), 'logical_metadata_bytes': logical_bytes,
        'hash_scope': 'all five metadata fields in original source row order; not full-file bytes'}


def read_transcript_date(stream: BinaryIO, calendar_date: str, *, file_bytes: int,
                         offset: int = 0) -> dict:
    """Exact reported-date page; only five metadata columns are decoded."""
    day = _date(calendar_date)
    _integer(offset, 0, MAX_SOURCE_ROWS)
    with _source(stream, file_bytes) as pf:
        matches, summary = _scan_metadata(pf, day)
    matches.sort(key=lambda x: (x['symbol'], x['fiscal_year'], x['fiscal_quarter'], x['source_row_position']))
    page = matches[offset:offset + PAGE_SIZE]
    nxt = offset + len(page) if offset + len(page) < len(matches) else None
    first, last = summary['source_date_range'].values()
    return {'schema': DATE_SCHEMA, 'calendar_date': day, 'date_basis': 'stored_report_date',
        'status': 'OBSERVED' if matches else 'NO_RETAINED_CALL_RECORD', 'events': page,
        'total_events': len(matches), 'offset': offset, 'next_offset': nxt,
        'pagination_basis': 'matched_call_records_not_source_positions',
        'within_observed_source_range': first is not None and first <= day <= last,
        'body_columns_read': False, 'mode': 'RETROSPECTIVE_EXPLORATORY',
        'publication_time_verified': False, 'point_in_time_eligible': False,
        'historical_security_identity_proven': False, 'calendar_completeness_proven': False,
        'coverage_scope': 'all retained source call records on the report date; not the selected price cohort',
        **summary}


def _row_group(pf, row_position: int):
    before = 0
    for group in range(pf.metadata.num_row_groups):
        size = pf.metadata.row_group(group).num_rows
        if row_position < before + size:
            return group, row_position - before
        before += size
    raise HistoricalExperienceError('transcript source row position absent')


def _one_row(pf, group: int, within: int, columns: list[str], budget: int):
    logical_bytes = 0
    for i, batch in enumerate(pf.iter_batches(batch_size=1, row_groups=[group], columns=columns, use_threads=False)):
        logical_bytes += batch.nbytes
        if logical_bytes > budget:
            raise HistoricalExperienceError('selected transcript decoded row-group budget exceeded')
        if i == within:
            if batch.nbytes > MAX_RECORD_BYTES:
                raise HistoricalExperienceError('selected transcript record budget exceeded')
            return batch.to_pylist()[0]
    raise HistoricalExperienceError('transcript source row is absent from its group')


def _paragraphs(body):
    if body is None:
        return []
    if type(body) is not list or len(body) > MAX_PARAGRAPHS:
        raise HistoricalExperienceError('invalid transcript paragraph sequence')
    for p in body:
        if type(p) is not dict or set(p) != {'paragraph_number', 'speaker', 'content'}:
            raise HistoricalExperienceError('exact raw paragraph fields required')
        if p['paragraph_number'] is not None:
            _integer(p['paragraph_number'], 0, 2**31 - 1)
        if p['speaker'] is not None and (type(p['speaker']) is not str or len(p['speaker'].encode()) > 2048):
            raise HistoricalExperienceError('invalid source speaker label')
        if p['content'] is not None and type(p['content']) is not str:
            raise HistoricalExperienceError('invalid source paragraph text')
    return body


def _text_page(paragraphs: list, offset: int, char_offset: int, max_chars: int):
    if offset > len(paragraphs) or (offset == len(paragraphs) and char_offset):
        raise HistoricalExperienceError('paragraph cursor exceeds source')
    if offset < len(paragraphs) and char_offset > len(paragraphs[offset]['content'] or ''):
        raise HistoricalExperienceError('character cursor exceeds source paragraph')
    page = []
    remaining = max_chars
    i, at = offset, char_offset
    while i < len(paragraphs) and remaining > 0 and len(page) < 20:
        paragraph = paragraphs[i]
        text = paragraph['content'] or ''
        end = min(len(text), at + remaining)
        def fragment(stop):
            return {'paragraph_index': i, 'paragraph_number_source': paragraph['paragraph_number'],
                'speaker_source_label': paragraph['speaker'], 'text': text[at:stop],
                'character_start': at, 'character_end': stop, 'paragraph_complete': stop == len(text),
                'source_text_missing': paragraph['content'] is None}
        entry = fragment(end)
        if len(_bytes([*page, entry])) > MAX_PAGE_JSON_BYTES:
            lo, hi = at, end
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(_bytes([*page, fragment(mid)])) <= MAX_PAGE_JSON_BYTES:
                    lo = mid
                else:
                    hi = mid - 1
            end = lo
            if end == at:
                break
            entry = fragment(end)
        page.append(entry)
        remaining -= end - at
        if end == len(text):
            i, at = i + 1, 0
        else:
            at = end
    if not page and i < len(paragraphs):
        raise HistoricalExperienceError('transcript page cannot fit its bounded response')
    return page, None if i == len(paragraphs) else {'paragraph_offset': i, 'character_offset': at}


def read_transcript(stream: BinaryIO, *, file_bytes: int, row_position: int,
                    expected_metadata_sha256: str, paragraph_offset: int = 0,
                    character_offset: int = 0, max_chars: int = 6000,
                    expected_record_sha256: str | None = None) -> dict:
    """Version-bound caller row, exact metadata check, bounded raw text fragments.

    This returns source-order paragraphs, not a Q&A reconstruction or a claim
    that any speaker has a particular role. Continuation coordinates are Unicode
    character positions in the stored paragraph, with a whole-record hash.
    """
    _integer(row_position, 0, MAX_SOURCE_ROWS - 1)
    _integer(paragraph_offset, 0, MAX_PARAGRAPHS)
    _integer(character_offset, 0, MAX_RECORD_BYTES)
    _integer(max_chars, 1, MAX_PAGE_CHARS)
    _digest(expected_metadata_sha256)
    if expected_record_sha256 is not None:
        _digest(expected_record_sha256)
    with _source(stream, file_bytes) as pf:
        group, within = _row_group(pf, row_position)
        meta = _metadata(_one_row(pf, group, within, list(METADATA_FIELDS), MAX_METADATA_BYTES))
        if _hash(meta) != expected_metadata_sha256:
            raise HistoricalExperienceError('selected transcript metadata digest mismatch')
        if pf.metadata.row_group(group).total_byte_size > MAX_BODY_GROUP_BYTES:
            raise HistoricalExperienceError('selected transcript declared row-group budget exceeded')
        value = _one_row(pf, group, within, ['transcripts'], MAX_BODY_GROUP_BYTES)['transcripts']
        paragraphs = _paragraphs(value)
        canonical = _bytes({**meta, 'transcripts': value})
        if len(canonical) > MAX_RECORD_BYTES:
            raise HistoricalExperienceError('selected transcript record byte budget exceeded')
        record_hash = hashlib.sha256(canonical).hexdigest()
        if expected_record_sha256 is not None and record_hash != expected_record_sha256:
            raise HistoricalExperienceError('selected transcript record digest mismatch')
        page, next_cursor = _text_page(paragraphs, paragraph_offset, character_offset, max_chars)
    return {'schema': BODY_SCHEMA, 'metadata': meta, 'source_row_position': row_position,
        'metadata_sha256': expected_metadata_sha256, 'record_sha256': record_hash,
        'record_hash_basis': 'canonical selected source metadata and original nested paragraphs',
        'paragraphs': page, 'total_paragraphs': len(paragraphs), 'next_cursor': next_cursor,
        'page_sha256': _hash(page), 'status': 'OBSERVED' if paragraphs else 'NO_RETAINED_TEXT',
        'mode': 'RETROSPECTIVE_EXPLORATORY', 'point_in_time_eligible': False,
        'publication_time_verified': False, 'speaker_roles_verified': False,
        'historical_security_identity_proven': False, 'qa_reconstruction_performed': False,
        'source_text_is_data_not_instructions': True}



def _catalog_binding(source_ref: str, source_version: str) -> None:
    if (type(source_ref) is not str or len(source_ref) > 2048 or ':' not in source_ref
            or source_ref.rsplit('/', 1)[-1].split(':')[-1] != SOURCE_FILENAME
            or type(source_version) is not str
            or not re.fullmatch(r'statv1:[a-f0-9]{64}', source_version)):
        raise HistoricalExperienceError('explicit transcript reference and observed file version required')


def read_transcript_catalog(stream: BinaryIO, *, file_bytes: int,
                            source_ref: str, source_version: str) -> dict:
    """Compact offline metadata projection; never a second transcript-body corpus."""
    _catalog_binding(source_ref, source_version)
    with _source(stream, file_bytes) as pf:
        rows, summary = _scan_metadata(pf, None)
    return {'schema':CATALOG_SCHEMA, 'mode':'RETROSPECTIVE_EXPLORATORY',
        'columns':[*METADATA_FIELDS, 'source_row_position'], 'rows':rows,
        'metadata':{**summary, 'source_ref':source_ref, 'source_version':source_version,
            'full_source_content_sha256':None, 'body_columns_read':False,
            'publication_time_verified':False, 'historical_security_identity_proven':False,
            'point_in_time_eligible':False, 'calendar_completeness_proven':False,
            'speaker_roles_verified':False, 'date_basis':'stored_report_date',
            'body_access':'existing history_transcript action; same file version, row and metadata digest',
            'limitations':['Metadata records do not prove usable call text exists.',
                'Report date is not verified original publication or intraday availability.',
                'Source symbol and speaker labels are not verified historical identity or roles.',
                'The file version is an observation token, not a full-corpus content hash.',
                'No Terminal transcript intake, Q&A reconstruction or public publication is performed.']}}


def read_transcript_catalog_path(path, *, expected_sha256: str) -> dict:
    """Read a hash-bound derived catalogue; never opens the 2+GB body source."""
    from pathlib import Path
    from engine.neuralweb.market_memory_history_archive import _regular_file
    _digest(expected_sha256)
    path=Path(path)
    raw=_regular_file(path.parent,path.name,MAX_METADATA_BYTES)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise HistoricalExperienceError('transcript catalogue digest mismatch')
    try:
        catalog=json.loads(raw)
        if (catalog.get('schema')!=CATALOG_SCHEMA or catalog.get('mode')!='RETROSPECTIVE_EXPLORATORY'
                or catalog.get('columns')!=[*METADATA_FIELDS,'source_row_position']
                or type(catalog.get('rows')) is not list or len(catalog['rows'])>MAX_SOURCE_ROWS):
            raise HistoricalExperienceError('invalid transcript catalogue schema')
        meta=catalog['metadata']
        _catalog_binding(meta['source_ref'],meta['source_version'])
        for k in ('body_columns_read','publication_time_verified','point_in_time_eligible',
                  'historical_security_identity_proven','calendar_completeness_proven','speaker_roles_verified'):
            if meta.get(k) is not False:
                raise HistoricalExperienceError('transcript catalogue qualification cannot be promoted')
        if meta.get('full_source_content_sha256') is not None:
            raise HistoricalExperienceError('metadata projection is not a full-source digest')
        digest=hashlib.sha256(b'[');seen=set();first=last=None
        for i,row in enumerate(catalog['rows']):
            if type(row) is not list or len(row)!=6 or type(row[-1]) is not int or row[-1]!=i:
                raise HistoricalExperienceError('catalogue must retain exact source row order')
            value=_metadata(dict(zip(METADATA_FIELDS,row[:5])))
            key=value['symbol'],value['fiscal_year'],value['fiscal_quarter']
            if key in seen:raise HistoricalExperienceError('duplicate catalogue source period')
            seen.add(key)
            if i:digest.update(b',')
            digest.update(_bytes(value));day=value['report_date']
            first=day if first is None else min(first,day);last=day if last is None else max(last,day)
        digest.update(b']')
        if (meta['source_rows']!=len(catalog['rows']) or meta['metadata_projection_sha256']!=digest.hexdigest()
                or meta['source_date_range']!={'first':first,'last':last}):
            raise HistoricalExperienceError('transcript catalogue source projection mismatch')
    except HistoricalExperienceError:raise
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        raise HistoricalExperienceError('invalid retained transcript catalogue') from exc
    return catalog
