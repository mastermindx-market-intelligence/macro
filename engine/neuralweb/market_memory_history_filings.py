"""Exact-date Item 2.02 filing metadata from the existing retained EDGAR store.

No source acquisition, storage, event identity, causal inference or access plane.
Bytes are supplied by the incumbent DataWorkspace descriptor-confined reader.
Filing date, period of report and source-claimed acceptance time stay distinct.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from engine.earnings_release.filing_key import filing_key_from_8k_row, FilingIdentityError
from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.neuralweb.market_memory_history_archive import _date
from lib.dataos.temporal import utc

SCHEMA = 'market_memory.historical_filing_context.v1'
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_DECODED_BYTES = 32 * 1024 * 1024
MAX_SOURCE_ROWS = 250_000
PAGE_SIZE = 50
_HEX = re.compile(r'[a-f0-9]{64}\Z')
_LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}\Z')
FIELDS = frozenset({'ticker', 'cik', 'accession', 'form', 'filing_date',
                    'acceptance_datetime', 'report_date', 'items'})


def _event(row: dict) -> dict:
    """Validate one source row; no historical label-to-issuer inference."""
    if set(row) != FIELDS:
        raise HistoricalExperienceError('exact earnings filing source fields required')
    label = row['ticker']
    if type(label) is not str or not _LABEL.fullmatch(label):
        raise HistoricalExperienceError('invalid source ticker label')
    if row['form'] not in ('8-K', '8-K/A'):
        raise HistoricalExperienceError('only retained earnings-related current reports are supported')
    items = row['items']
    if type(items) is not str or len(items) > 256 or '2.02' not in {x.strip() for x in items.split(',')}:
        raise HistoricalExperienceError('exact Item 2.02 source token required')
    try:
        key = filing_key_from_8k_row(row)
    except FilingIdentityError as exc:
        raise HistoricalExperienceError('invalid canonical filing identity') from exc
    filed = _date(row['filing_date'])
    report = None if row['report_date'] in ('', None) else _date(row['report_date'])
    clock = row['acceptance_datetime']
    normalized = None
    if clock not in ('', None):
        if type(clock) is not str or len(clock) > 64:
            raise HistoricalExperienceError('invalid recorded acceptance clock')
        try:
            normalized = utc(clock).isoformat()
        except (ValueError, TypeError) as exc:
            raise HistoricalExperienceError('recorded acceptance clock requires an explicit timezone') from exc
    return {**key.to_dict(), 'ticker_source_label': label, 'form': row['form'],
        'filing_date': filed, 'report_date': report,
        'acceptance_datetime_source': clock or None,
        'acceptance_datetime_utc': normalized, 'items_source': items,
        'context_kind': 'SEC_ITEM_202_FILING_METADATA'}


def _scan_source(raw: bytes, expected_sha256: str, consume) -> dict:
    """One bounded validator for both date lookup and offline calendar export.

    consume is application code, not a JSON or user-supplied callable. Both
    projections validate every source row; neither opens an outcome partition.
    """
    if type(expected_sha256) is not str or not _HEX.fullmatch(expected_sha256):
        raise HistoricalExperienceError('exact retained filing source SHA-256 required')
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_SOURCE_BYTES:
        raise HistoricalExperienceError('filing source byte budget exceeded')
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise HistoricalExperienceError('filing source digest mismatch')
    import pyarrow as pa
    import pyarrow.parquet as pq
    try:
        pf = pq.ParquetFile(pa.BufferReader(raw), pre_buffer=False)
        try:
            count = pf.metadata.num_rows
            decoded = sum(pf.metadata.row_group(i).total_byte_size
                          for i in range(pf.metadata.num_row_groups))
            if not 0 <= count <= MAX_SOURCE_ROWS:
                raise HistoricalExperienceError('filing source row budget exceeded')
            if decoded > MAX_DECODED_BYTES:
                raise HistoricalExperienceError('filing decoded source exceeds budget')
            if len(pf.schema_arrow.names) != len(FIELDS) or set(pf.schema_arrow.names) != FIELDS:
                raise HistoricalExperienceError('exact earnings filing source schema required')
            seen = set()
            first = last = None
            logical_bytes = observed_rows = 0
            for batch in pf.iter_batches(batch_size=2048, use_threads=False):
                logical_bytes += batch.nbytes
                observed_rows += batch.num_rows
                if logical_bytes > MAX_DECODED_BYTES:
                    raise HistoricalExperienceError('filing logical decoded source exceeds budget')
                if observed_rows > count or observed_rows > MAX_SOURCE_ROWS:
                    raise HistoricalExperienceError('filing decoded source row count mismatch')
                for row in batch.to_pylist():
                    event = _event(row)
                    key = event['filing_key']
                    if key in seen:
                        raise HistoricalExperienceError('duplicate canonical filing key in retained source')
                    seen.add(key)
                    filed = event['filing_date']
                    first = filed if first is None or filed < first else first
                    last = filed if last is None or filed > last else last
                    consume(event)
            if observed_rows != count:
                raise HistoricalExperienceError('filing decoded source row count mismatch')
        finally:
            pf.close()
    except HistoricalExperienceError:
        raise
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        raise HistoricalExperienceError('invalid retained filing source') from exc
    return {'schema': SCHEMA, 'date_basis': 'stored_SEC_filing_date',
        'source_rows': count, 'source_sha256': expected_sha256,
        'source_date_range': {'first': first, 'last': last},
        'logical_decoded_source_bytes': logical_bytes,
        'calendar_completeness_proven': False, 'historical_ticker_identity_proven': False,
        'intraday_publication_time_verified': False, 'point_in_time_eligible': False,
        'mode': 'RETROSPECTIVE_EXPLORATORY',
        'coverage_scope': 'all retained Item 2.02 filings on the date, not the selected price-proxy universe',
        'limitations': [
            'Source is a later retained EDGAR metadata snapshot, not an original-time system observation.',
            'Filing date is not the earnings report period or proven original press-release time.',
            'Acceptance timestamps are source-claimed; no intraday trading availability is established.',
            'Ticker labels do not establish historical security membership or identifier continuity.',
            'No earnings values, consensus, surprise, full filing text or market-move cause is inferred.',
            'An empty response is not proof that no corporate or market event occurred.',
        ]}


def read_filing_date(raw: bytes, calendar_date: str, *, expected_sha256: str,
                     offset: int = 0) -> dict:
    """One exact filing-date page; offsets count matches, not source positions."""
    day = _date(calendar_date)
    if type(offset) is not int or not 0 <= offset <= MAX_SOURCE_ROWS:
        raise HistoricalExperienceError('bounded filing-date page offset required')
    matches = []
    def collect(event):
        if event['filing_date'] == day:
            matches.append(event)
    metadata = _scan_source(raw, expected_sha256, collect)
    matches.sort(key=lambda r: r['filing_key'])
    page = matches[offset:offset + PAGE_SIZE]
    next_offset = offset + len(page) if offset + len(page) < len(matches) else None
    first, last = (metadata['source_date_range'][k] for k in ('first', 'last'))
    return {**metadata, 'calendar_date': day,
        'status': 'OBSERVED' if matches else 'NO_RETAINED_FILING', 'events': page,
        'total_events': len(matches), 'offset': offset, 'next_offset': next_offset,
        'remaining_events': max(0, len(matches) - offset - len(page)),
        'pagination_basis': 'matched_filing_records_not_source_positions',
        'missing_acceptance_count': sum(e['acceptance_datetime_utc'] is None for e in matches),
        'missing_acceptance_count_scope': 'all_matching_records_for_selected_date',
        'within_observed_source_range': first is not None and first <= day <= last}


def read_filing_timeline(raw: bytes, *, expected_sha256: str) -> dict:
    """Columnar projection for one explicitly selected private browser export."""
    columns = ['filing_date', 'filing_key', 'cik', 'accession', 'ticker_source_label',
               'form', 'report_date', 'acceptance_datetime_source',
               'acceptance_datetime_utc', 'items_source']
    rows = []
    metadata = _scan_source(raw, expected_sha256,
                           lambda event: rows.append([event[c] for c in columns]))
    rows.sort(key=lambda r: (r[0], r[1]))
    return {'schema': SCHEMA, 'mode': metadata['mode'], 'columns': columns,
            'rows': rows, 'metadata': metadata}


def _filing_file_bytes(path: Path, expected_sha256: str) -> bytes:
    from engine.neuralweb.market_memory_history_archive import _regular_file
    path = Path(path)
    if path.name != 'earnings_8k_dates.parquet':
        raise HistoricalExperienceError('exact earnings filing source filename required')
    if type(expected_sha256) is not str or not _HEX.fullmatch(expected_sha256):
        raise HistoricalExperienceError('exact retained filing source SHA-256 required')
    return _regular_file(path.parent, path.name, MAX_SOURCE_BYTES)


def read_filing_path(path: Path, calendar_date: str, *, expected_sha256: str,
                     offset: int = 0) -> dict:
    return read_filing_date(_filing_file_bytes(path, expected_sha256), calendar_date,
                            expected_sha256=expected_sha256, offset=offset)


def read_filing_timeline_path(path: Path, *, expected_sha256: str) -> dict:
    return read_filing_timeline(_filing_file_bytes(path, expected_sha256), expected_sha256=expected_sha256)
