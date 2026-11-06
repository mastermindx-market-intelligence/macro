"""One exact-date view over existing retained historical artifacts.

Composition only: no additional store, source, inference model, graph, process,
provider or admission authority. Descriptive proxy moves never become a whole-
market breadth measure. Evidence absence stays visible instead of a fabricated
news narrative or imputed historical forecast.
"""
from __future__ import annotations
from pathlib import Path

from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.neuralweb.market_memory_history_archive import read_day
from engine.neuralweb.market_memory_history_macro import read_macro_chronology,select_macro_date,_flags
from engine.neuralweb.market_memory_history_filings import (read_filing_path, MAX_SOURCE_ROWS, SCHEMA as FILING_SCHEMA)

SCHEMA='market_memory.daily_dossier.v1'


def build_daily_dossier(archive: Path, market_date: str, *, expected_manifest_sha256: str,
                        macro_path: Path | None=None, expected_macro_sha256: str | None=None,
                        reveal_outcomes: bool=False, filings_path: Path | None=None,
                        expected_filings_sha256: str | None=None, filings_offset: int=0) -> dict:
    if (macro_path is None) != (expected_macro_sha256 is None):
        raise HistoricalExperienceError('macro path and exact source digest must be supplied together')
    if ((filings_path is None) != (expected_filings_sha256 is None)
            or type(filings_offset) is not int or not 0 <= filings_offset <= MAX_SOURCE_ROWS
            or (filings_path is None and filings_offset != 0)):
        raise HistoricalExperienceError('explicit paired filing source and bounded offset required')
    if filings_path is not None and Path(filings_path).name != 'earnings_8k_dates.parquet':
        raise HistoricalExperienceError('exact earnings filing source filename required')
    market=read_day(archive,market_date,expected_manifest_sha256=expected_manifest_sha256,
                    reveal_outcomes=reveal_outcomes)
    macro=None
    if macro_path is not None:
        chronology=read_macro_chronology(macro_path,expected_sha256=expected_macro_sha256)
        macro=select_macro_date(chronology,market_date)
        macro['status']='OBSERVED' if macro['total_events'] else 'NO_OBSERVATION'
        macro['sha256']=expected_macro_sha256
    filings = None if filings_path is None else read_filing_path(filings_path, market_date,
        expected_sha256=expected_filings_sha256, offset=filings_offset)
    return compose_daily_dossier(market, macro, filings=filings)


def compose_daily_dossier(market: dict, macro: dict | None=None, filings: dict | None=None,
                          transcripts: dict | None=None) -> dict:
    """Shared projection of already-verified market/macro packets; no source I/O."""
    if (type(market) is not dict or market.get('mode')!='RETROSPECTIVE_EXPLORATORY'
            or market.get('pit_backtest_eligible') is not False):
        raise HistoricalExperienceError('verified retrospective market packet required')
    market_date=market['market_date']
    rows=market['rows']
    valid=[r for r in rows if r.get('return_1ob_pct') is not None]
    ordered=sorted(valid,key=lambda r:(r['return_1ob_pct'],r['vendor_symbol']))
    def movers(items):
        return [{'vendor_symbol':r['vendor_symbol'],'return_1ob_pct':r['return_1ob_pct']} for r in items]
    summary={
        'denominator':'selected_proxy_observations_with_valid_1bar_return',
        'observed_proxy_count':len(rows),'valid_return_count':len(valid),
        'positive_proxy_count':sum(r['return_1ob_pct']>0 for r in valid),
        'negative_proxy_count':sum(r['return_1ob_pct']<0 for r in valid),
        'flat_proxy_count':sum(r['return_1ob_pct']==0 for r in valid),
        'missing_return_count':len(rows)-len(valid),
        'largest_declines':movers([r for r in ordered if r['return_1ob_pct']<0][:3]),
        'largest_advances':movers([r for r in reversed(ordered) if r['return_1ob_pct']>0][:3]),
        'interpretation':'Descriptive selected proxies; not whole-market breadth or an alert.',
    }
    macro_selected=macro is not None
    if macro is None:
        macro={'status':'SOURCE_NOT_SELECTED','calendar_date':market_date,'events':[],
               'reason':'No exact first-print chronology reference was selected.'}
    else:
        if (type(macro) is not dict or macro.get('calendar_date')!=market_date
                or macro.get('units_retained') is not False
                or macro.get('date_basis')!='fred_realtime_start_date_only'):
            raise HistoricalExperienceError('verified macro packet must match the exact requested date')
        _flags(macro)
    if filings is not None:
        if (type(filings) is not dict or filings.get('schema') != FILING_SCHEMA
                or filings.get('calendar_date') != market_date
                or filings.get('mode') != 'RETROSPECTIVE_EXPLORATORY'
                or any(filings.get(k) is not False for k in ('point_in_time_eligible',
                    'historical_ticker_identity_proven','intraday_publication_time_verified',
                    'calendar_completeness_proven'))):
            raise HistoricalExperienceError('verified filing context must match date and qualification')
    if transcripts is not None:
        from engine.neuralweb.market_memory_history_transcripts import DATE_SCHEMA
        if (type(transcripts) is not dict or transcripts.get('schema') != DATE_SCHEMA
                or transcripts.get('calendar_date') != market_date
                or transcripts.get('mode') != 'RETROSPECTIVE_EXPLORATORY'
                or transcripts.get('body_columns_read') is not False
                or any(transcripts.get(k) is not False for k in ('point_in_time_eligible',
                    'publication_time_verified','historical_security_identity_proven',
                    'calendar_completeness_proven'))):
            raise HistoricalExperienceError('verified transcript date and qualification required')
    result = {'schema':SCHEMA,'market_date':market_date,'mode':market['mode'],
        'retrospective_only':True,'outcomes_revealed':'outcomes' in market,
        'market':market,'macro':macro,'summary':summary,
        'coverage':{
            'price_proxies':'SELECTED_RETAINED_HISTORY',
            'macro_first_prints':'SELECTED_DATE_ONLY_SOURCE' if macro_selected else 'NOT_SELECTED',
            'full_macro_revision_history':'NOT_INCLUDED',
            'contemporary_consensus':'NOT_INCLUDED',
            'contemporary_news_and_causal_explanations':'NOT_INCLUDED',
            'issuer_filings_and_earnings_context':'NOT_INCLUDED',
            'historical_stock_universe_and_identity':'NOT_INCLUDED',
            'intraday_quotes_and_options':'NOT_INCLUDED',
            'actual_historical_mastermind_alerts':'NOT_INCLUDED',
            'strict_point_in_time_eligibility':'NOT_PROVEN',
        }}
    if filings is not None:
        result['filings'] = filings
        result['coverage']['issuer_filings_and_earnings_context'] = 'SELECTED_ITEM_202_FILING_METADATA_ONLY'
    if transcripts is not None:
        result['transcripts'] = transcripts
        result['coverage']['earnings_call_records'] = 'RETAINED_REPORTED_DATE_METADATA_ONLY'
    return result
