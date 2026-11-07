"""Read-only consumer of ALREADY returned native TiingoResearchHistory instances.

This is not a vendor reader, capture service, evaluation engine, experiment entrypoint,
source-licensing grant, PIT reconstruction, or trading signal. It neither opens an
archive nor acquires data. Callers must obtain each native history through the
existing Data OS owner and its applicable rights/admission boundary. It emits a
retrospective-only series with rank/gate/size/trading permission explicitly false.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Any

SECTORS = ('XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY')
INPUTS = SECTORS + ('SPY','BIL')
_SHA = re.compile(r'^[a-f0-9]{64}$')
_VIEW_SCHEMA = 'mastermind.tiingo.research_views.v2'

class Refused(ValueError):
    """Named source/consumer contract rejection, not a retry instruction."""

@dataclass(frozen=True)
class Series:
    symbol: str
    values: tuple[float,...]
    adjustment_vintage_utc: str
    receipt_refs: tuple[tuple[str,str],...]
    input_source_digests: tuple[str,...]

@dataclass(frozen=True)
class ResearchProjection:
    anchor_market_day: str
    capture_cutoff_utc: str
    session_days: tuple[str,...]
    series: tuple[Series,...]
    digest_sha256: str
    evidence_mode: str = 'RETROSPECTIVE_EXPLORATORY_NOT_PIT'
    source_use: str = 'UNQUALIFIED'
    as_known_historically: bool = False
    historical_pit_admitted: bool = False
    may_rank: bool = False
    may_gate: bool = False
    may_size: bool = False
    may_trade: bool = False


def _day(value: object, reason: str) -> date:
    if type(value) is not str:
        raise Refused(reason)
    try:
        day=date.fromisoformat(value)
    except ValueError as exc:
        raise Refused(reason) from exc
    if day.isoformat()!=value:
        raise Refused(reason)
    return day


def _utc(value: object, reason: str) -> datetime:
    if type(value) is not str:
        raise Refused(reason)
    try:
        moment=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise Refused(reason) from exc
    if moment.tzinfo is None or moment.utcoffset()!=timedelta(0):
        raise Refused(reason)
    return moment.astimezone(timezone.utc)


def _finite_positive(value: object) -> bool:
    if type(value) not in (int,float):
        return False
    try:
        return math.isfinite(value) and value>0
    except (OverflowError, ValueError):
        return False


def project_histories(histories: object, *, anchor_market_day: str,
                      capture_cutoff_utc: str) -> ResearchProjection:
    """Check thirteen historical source objects, never authorize a backtest.

    The complete 253-price prefix is anchored to the incumbent NYSE calendar.
    Even a passing result describes values reconstructed from post-origin vendor
    vintages. It MUST NOT be re-labelled as an as-issued forecast or native P1.
    """
    # Exact owner types/calendar are imported from the incumbent source path.
    # No alternate collector, calendar, research database or filesystem read.
    from lib.dataos.tiingo_reader import TiingoResearchHistory
    from lib.nyse_calendar import session_n_back, sessions_between

    if type(histories) is not dict or set(histories)!=set(INPUTS):
        raise Refused('EXACT_13_INPUTS_REQUIRED')
    cutoff=_utc(capture_cutoff_utc,'UTC_CUTOFF_REQUIRED')
    anchor=_day(anchor_market_day,'ANCHOR_SESSION_INVALID')
    start=session_n_back(anchor,252)
    if start is None:
        raise Refused('ANCHOR_SESSION_INVALID')
    sessions=tuple(x.isoformat() for x in sessions_between(start,anchor))
    if len(sessions)!=253 or sessions[-1]!=anchor_market_day:
        raise Refused('CALENDAR_PREFIX_INCOMPLETE')
    all_series=[]
    digest_data=[]
    for symbol in INPUTS:
        history=histories[symbol]
        if type(history) is not TiingoResearchHistory:
            raise Refused(f'{symbol}:NATIVE_HISTORY_REQUIRED')
        if (history.source!='eod-bars' or history.vendor_symbol!=symbol):
            raise Refused(f'{symbol}:NATIVE_EOD_SOURCE_ID')
        if (history.authority!='RESEARCH_ONLY_RETROSPECTIVE'
                or history.pit_backtest_eligible is not False
                or history.redistribution_admitted is not False
                or history.historical_identity_admitted is not False
                or history.market_session_completeness_proven is not False):
            raise Refused(f'{symbol}:NATIVE_AUTHORITY_CONFLICT')
        if _utc(history.observed_before_utc, f'{symbol}:CAPTURE_CUTOFF_INVALID') != cutoff:
            raise Refused(f'{symbol}:CAPTURE_CUTOFF_MISMATCH')
        if (_day(history.start_market_date,f'{symbol}:MARKET_START_INVALID')>start
                or _day(history.end_market_date,f'{symbol}:EXACT_ORIGIN_END_REQUIRED')!=anchor):
            raise Refused(f'{symbol}:EXACT_ORIGIN_END_REQUIRED')
        partitions=history.source_partitions
        if type(partitions) is not tuple or not 1<=len(partitions)<=256:
            raise Refused(f'{symbol}:RECEIPT_REFERENCES_INVALID')
        declared_receipt_days={}
        for item in partitions:
            if (type(item) is not tuple or len(item)!=2
                    or type(item[1]) is not str or not _SHA.fullmatch(item[1])
                    or _day(item[0],f'{symbol}:RECEIPT_DATE_INVALID')>cutoff.date()):
                raise Refused(f'{symbol}:RECEIPT_REFERENCES_INVALID')
            declared_receipt_days.setdefault(item[1],set()).add(item[0])
        if len(partitions)!=len(set(partitions)):
            raise Refused(f'{symbol}:RECEIPT_REFERENCES_INVALID')
        rows=history.rows
        if type(rows) is not tuple or len(rows)>20000:
            raise Refused(f'{symbol}:SOURCE_ROW_BUDGET')
        selected={}
        last_day=None
        for row in rows:
            if type(row) is not dict:
                raise Refused(f'{symbol}:ROW_SCHEMA')
            market_day=_day(row.get('market_date'),f'{symbol}:ROW_MARKET_DATE')
            if last_day is not None and market_day<=last_day:
                raise Refused(f'{symbol}:SESSION_COVERAGE_DUPLICATE_OR_UNORDERED')
            last_day=market_day
            if market_day>anchor:
                raise Refused(f'{symbol}:FUTURE_OUTCOME_ROW')
            if market_day<start:
                continue
            selected[market_day.isoformat()]=row
        if tuple(selected)!=sessions:
            raise Refused(f'{symbol}:SESSION_COVERAGE_INCOMPLETE')
        values=[]
        vintages=set()
        source_digests=set()
        for day,row in selected.items():
            if (row.get('ticker_vendor')!=symbol or row.get('source_vendor')!='tiingo'
                    or row.get('dataset_source')!='eod-bars'
                    or row.get('source_view_schema')!=_VIEW_SCHEMA):
                raise Refused(f'{symbol}:ROW_SOURCE_IDENTITY')
            if (row.get('timestamp_source')!='vendor_market_date_only'
                    or row.get('vendor_historical_availability')!='UNVERIFIED'
                    or row.get('adjustment_basis_detail')!='vendor_adjusted_not_historical_vintage'):
                raise Refused(f'{symbol}:ROW_EVIDENCE_BASIS')
            if (row.get('pit_backtest_eligible') is not False
                    or row.get('dataos_identity_admitted') is not False
                    or row.get('source_rights_admitted') is not False):
                raise Refused(f'{symbol}:ROW_AUTHORITY_CONFLICT')
            # Retained legacy views omit source_receipt_id entirely. The raw
            # hash remains mandatory; a present-but-null/invalid identity is not
            # equivalent to a legitimately absent legacy field.
            identifiers=('source_sha256',) + (('source_receipt_id',)
                if 'source_receipt_id' in row else ())
            for field in identifiers:
                value=row.get(field)
                if type(value) is not str or not _SHA.fullmatch(value):
                    raise Refused(f'{symbol}:ROW_RECEIPT_INVALID')
            # The incumbent reader accepts either an original raw-content hash
            # or an exact receipt identity, and preserves that caller selector
            # in source_partitions. Both remain bound to the original day.
            matched_refs = {
                row[field] for field in identifiers
                if row[field] in declared_receipt_days
            }
            if not matched_refs:
                raise Refused(f'{symbol}:ROW_SOURCE_NOT_REFERENCED')
            observed=_utc(row.get('source_observed_at_utc'),f'{symbol}:ROW_CAPTURE_CLOCK')
            if observed>cutoff:
                raise Refused(f'{symbol}:SOURCE_AFTER_CAPTURE_CUTOFF')
            if not any(observed.date().isoformat() in declared_receipt_days[identifier]
                       for identifier in matched_refs):
                raise Refused(f'{symbol}:ROW_CAPTURE_DAY_NOT_REFERENCED')
            # The original vendor snapshot cannot contain a later EOD market day.
            # This mirrors the incumbent history reader's future-date refusal.
            if day > observed.date().isoformat():
                raise Refused(f'{symbol}:MARKET_AFTER_CAPTURE')
            adjustment=_utc(row.get('adjustment_asof_utc'),f'{symbol}:ADJUSTMENT_VINTAGE')
            if adjustment!=observed:
                raise Refused(f'{symbol}:ADJUSTMENT_CLOCK_CONFLICT')
            vintages.add(adjustment.isoformat())
            source_digests.add(row['source_sha256'])
            if not _finite_positive(row.get('close_tradj')):
                raise Refused(f'{symbol}:INVALID_ADJUSTED_CLOSE')
            if not _finite_positive(row.get('close_raw')):
                raise Refused(f'{symbol}:INVALID_RAW_CLOSE')
            if row.get('split_factor') is not None and not _finite_positive(row['split_factor']):
                raise Refused(f'{symbol}:INVALID_SPLIT')
            if row.get('dividend_cash') is not None and (type(row['dividend_cash']) not in (int,float)
                    or not math.isfinite(row['dividend_cash'])):
                raise Refused(f'{symbol}:INVALID_DISTRIBUTION')
            values.append(float(row['close_tradj']))
        if len(vintages)!=1:
            raise Refused(f'{symbol}:MIXED_ADJUSTMENT_VINTAGE')
        series=Series(symbol,tuple(values),next(iter(vintages)),tuple(partitions),tuple(sorted(source_digests)))
        all_series.append(series)
        digest_data.append((symbol,values,sorted(vintages),partitions,sorted(source_digests)))
    canonical=json.dumps({'capture_cutoff':cutoff.isoformat(),'anchor':anchor.isoformat(),
                          'sessions':sessions,'series':digest_data},sort_keys=True,
                         separators=(',',':'),allow_nan=False).encode('utf-8')
    return ResearchProjection(anchor.isoformat(),cutoff.isoformat(),sessions,
                              tuple(all_series),hashlib.sha256(canonical).hexdigest())


def public_summary(projected: ResearchProjection) -> dict[str, Any]:
    """Safe provenance/coverage summary without any licensed close values."""
    if type(projected) is not ResearchProjection:
        raise Refused('PROJECTION_TYPE')
    # Dataclass identity does not grant authority: reject constructed/replaced
    # objects that claim more than the native retrospective projection provides.
    if (projected.evidence_mode != 'RETROSPECTIVE_EXPLORATORY_NOT_PIT'
            or projected.source_use != 'UNQUALIFIED'
            or any(value is not False for value in (
                projected.as_known_historically, projected.historical_pit_admitted,
                projected.may_rank, projected.may_gate, projected.may_size, projected.may_trade))):
        raise Refused('PROJECTION_AUTHORITY_CONFLICT')
    return dict(anchor_market_day=projected.anchor_market_day,
                capture_cutoff_utc=projected.capture_cutoff_utc,
                sessions=len(projected.session_days),
                symbols=[r.symbol for r in projected.series],
                source_digest=projected.digest_sha256,
                evidence_mode=projected.evidence_mode,
                source_use=projected.source_use,
                historical_pit_admitted=projected.historical_pit_admitted,
                may_rank=False,may_gate=False,may_size=False,may_trade=False)
