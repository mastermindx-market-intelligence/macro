from datetime import timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import research_skylit_r8_daily_position_evidence as r8


class Calendar:
    @staticmethod
    def is_session(d):
        return d.weekday() < 5

    @staticmethod
    def session_n_forward(d, n):
        cur = d
        for _ in range(n):
            cur += timedelta(days=1)
            while cur.weekday() >= 5:
                cur += timedelta(days=1)
        return cur

    @staticmethod
    def session_n_back(d, n):
        cur = d
        for _ in range(n):
            cur -= timedelta(days=1)
            while cur.weekday() >= 5:
                cur -= timedelta(days=1)
        return cur


def _eod(volume):
    return pd.DataFrame([{
        "root": "SPY",
        "expiration": "2026-10-16",
        "strike": 100.0,
        "right": "C",
        "date": "2026-09-14",
        "volume": volume,
        "close": 5.0,
    }])


def _oi(pub_session, value):
    return pd.DataFrame([{
        "root": "SPY",
        "expiration": "2026-10-16",
        "strike": 100.0,
        "right": "C",
        "date": pub_session,
        "open_interest": value,
    }])


def _api(eod, prior, later):
    return SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        eod_matrix_for_date=lambda session, root, store=None: eod.copy(),
        oi_for_date=lambda session, root, store=None: (
            prior.copy() if session == "2026-09-14"
            else later.copy() if session == "2026-09-15"
            else pd.DataFrame()
        ),
    )


def test_r8_trade_only_bounds_respect_whole_contract_parity():
    got = r8.analyze_session(
        "2026-09-14",
        "SPY",
        store_api=_api(_eod(1), _oi("2026-09-14", 100), _oi("2026-09-15", 100)),
        calendar_api=Calendar,
    )
    bounds = got["conditional_trade_only_bounds"]
    assert bounds["whole_contract_integer_bounds"] is True
    assert bounds["min_open_open_volume"] == pytest.approx(0)
    assert bounds["max_open_open_volume"] == pytest.approx(0)
    assert bounds["min_close_close_volume"] == pytest.approx(0)
    assert bounds["max_close_close_volume"] == pytest.approx(0)
    assert bounds["max_mixed_open_close_volume"] == pytest.approx(1)


def test_r8_noninteger_contract_volume_refuses_fractional_bounds():
    with pytest.raises(r8.R8Refusal, match="non-integer option contract volume"):
        r8.analyze_session(
            "2026-09-14",
            "SPY",
            store_api=_api(_eod(1.5), _oi("2026-09-14", 100), _oi("2026-09-15", 100)),
            calendar_api=Calendar,
        )


def test_r8_noninteger_or_boolean_oi_refuses_malformed_count_state():
    with pytest.raises(r8.R8Refusal, match="non-integer option contract OI"):
        r8.analyze_session(
            "2026-09-14",
            "SPY",
            store_api=_api(_eod(10), _oi("2026-09-14", 100.5), _oi("2026-09-15", 101)),
            calendar_api=Calendar,
        )

    prior = _oi("2026-09-14", 100)
    prior.loc[0, "open_interest"] = True
    with pytest.raises(r8.R8Refusal, match="Boolean option contract OI"):
        r8.analyze_session(
            "2026-09-14",
            "SPY",
            store_api=_api(_eod(10), prior, _oi("2026-09-15", 101)),
            calendar_api=Calendar,
        )


def test_r8_boolean_volume_refuses_instead_of_becoming_one_contract():
    eod = _eod(1)
    eod.loc[0, "volume"] = True
    with pytest.raises(r8.R8Refusal, match="Boolean option contract volume"):
        r8.analyze_session(
            "2026-09-14",
            "SPY",
            store_api=_api(eod, _oi("2026-09-14", 100), _oi("2026-09-15", 100)),
            calendar_api=Calendar,
        )
