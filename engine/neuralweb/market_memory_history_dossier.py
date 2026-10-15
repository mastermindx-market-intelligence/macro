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
from engine.neuralweb.market_memory_history_macro import read_macro_chronology,select_macro_date

SCHEMA='market_memory.daily_dossier.v1'


def build_daily_dossier(archive: Path, market_date: str, *, expected_manifest_sha256: str,
                        macro_path: Path | None=None, expected_macro_sha256: str | None=None,
                        reveal_outcomes: bool=False) -> dict:
    if (macro_path is None) != (expected_macro_sha256 is None):
        raise HistoricalExperienceError('macro path and exact source digest must be supplied together')
    market=read_day(archive,market_date,expected_manifest_sha256=expected_manifest_sha256,
                    reveal_outcomes=reveal_outcomes)
    macro=None
    if macro_path is not None:
        chronology=read_macro_chronology(macro_path,expected_sha256=expected_macro_sha256)
        macro=select_macro_date(chronology,market_date)
        macro['status']='OBSERVED' if macro['total_events'] else 'NO_OBSERVATION'
        macro['sha256']=expected_macro_sha256
    return compose_daily_dossier(market, macro)


def compose_daily_dossier(market: dict, macro: dict | None=None) -> dict:
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
    elif macro.get('calendar_date')!=market_date or macro.get('pit_backtest_eligible') is not False:
        raise HistoricalExperienceError('verified macro packet must match the exact requested date')
    return {'schema':SCHEMA,'market_date':market_date,'mode':market['mode'],
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
