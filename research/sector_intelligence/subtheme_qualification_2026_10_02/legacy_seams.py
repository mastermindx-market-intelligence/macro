"""Faithful isolated reproductions of retrieved legacy source expressions.

Source: macro@e4910184b25c27eda95f81a09d3ce4a6f5d8535d
engine/subsector_track_record.py blob a6f9c2c5ae8511eefa8e7b721820f040d6cf59ce.
These are semantic extracts, NOT a byte-identical/full-application import.
Synthetic inputs establish failure modes, never actual investment performance.
"""
from datetime import date, timedelta


def calendar_endpoint(start: str, horizon: int) -> str:
    # Original expression uses pandas.Timestamp + pandas.Timedelta(days=horizon_d).
    # date + timedelta is equivalent for these ISO day-only test inputs.
    return (date.fromisoformat(start) + timedelta(days=horizon)).isoformat()


def headline_leader(out_h: dict) -> str | None:
    lead = None
    for h, e in out_h.items():
        v2 = e.get('v2') or {}
        a, b = e.get('score_ic'), v2.get('score_ic')
        if (v2.get('n_matured') or 0) >= 40 and b is not None and a is not None:
            lead = 'v2' if b > a else 'incumbent'
    return lead


def coverage_renormalized(observed_returns: list[float | None]) -> float | None:
    # The original _fwd_basket averages every non-null _member_ret, once >=3 exist.
    available = [r for r in observed_returns if r is not None]
    return sum(available) / len(available) if len(available) >= 3 else None


def reproduce() -> dict:
    horizons = {
        '5': {'score_ic': 0.20, 'v2': {'score_ic':0.10, 'n_matured':100}},
        '21': {'score_ic':0.05, 'v2': {'score_ic':0.15, 'n_matured':100}},
    }
    full = [0.02,0.02,0.02,-0.20]
    missing = [0.02,0.02,0.02,None]
    return {
        'data_kind':'SYNTHETIC_DISCRIMINATORS_NOT_MARKET_BACKTEST',
        'source_blob':'a6f9c2c5ae8511eefa8e7b721820f040d6cf59ce',
        'calendar_endpoint':calendar_endpoint('2026-09-25',5),
        'explicit_five_session_endpoint':'2026-10-02',
        'leader_5_then_21':headline_leader(horizons),
        'leader_21_then_5':headline_leader(dict(reversed(list(horizons.items())))),
        'full_population_mean':coverage_renormalized(full),
        'missing_loser_legacy_mean':coverage_renormalized(missing),
    }


if __name__ == '__main__':
    import json
    print(json.dumps(reproduce(),indent=2))
