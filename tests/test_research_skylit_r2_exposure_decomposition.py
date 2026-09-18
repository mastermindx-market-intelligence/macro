from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts import research_skylit_r2_exposure_decomposition as r2


def fake_greeks(spot, strike, time_years, vol, is_call):
    spot = np.asarray(spot, dtype=float)
    strike = np.asarray(strike, dtype=float)
    time_years = np.asarray(time_years, dtype=float)
    vol = np.asarray(vol, dtype=float)
    gamma = (0.01 + vol) * np.sqrt(time_years) / np.maximum(spot, 1.0)
    zero = np.zeros_like(gamma)
    return zero, gamma, zero, zero


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


def _chain(prior=(100, 200)):
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "implied_vol": 0.20,
            "underlying_price": 100.0,
            "open_interest": prior[0],
        },
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "P",
            "implied_vol": 0.22,
            "underlying_price": 100.0,
            "open_interest": prior[1],
        },
    ])


def _oi(pub_session, values=(110, 190)):
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "date": pub_session,
            "open_interest": values[0],
        },
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "P",
            "date": pub_session,
            "open_interest": values[1],
        },
    ])


def test_settled_state_uses_next_session_oi_not_same_day_oi():
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: _chain(prior=(100, 200)),
        oi_for_date=lambda s, root, store=None: _oi(s, values=(110, 190)),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["position_publication_session"] == "2026-09-15"
    assert state["frame"]["position"].tolist() == [110.0, 190.0]
    assert state["target_gate_pass"] is True
    assert state["settled_oi_contract_rate"] == 1.0


def test_missing_next_session_oi_fails_coverage_without_zero_imputation():
    next_oi = _oi("2026-09-15").iloc[:1].copy()
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: _chain(),
        oi_for_date=lambda s, root, store=None: next_oi,
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["settled_oi_contract_rate"] == 0.5
    assert state["target_gate_pass"] is False
    assert len(state["frame"]) == 1


def test_malformed_source_identity_refuses_instead_of_shrinking_board():
    broken = _chain()
    broken.loc[1, "right"] = "UNKNOWN"
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: broken,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    with pytest.raises(r2.R2Refusal, match="malformed contract identity rows"):
        r2.build_settled_state(
            "2026-09-14",
            "SPY",
            store_api=api,
            calendar_api=Calendar,
            greeks_fn=fake_greeks,
        )


def test_missing_iv_cannot_disappear_from_the_coverage_denominator():
    broken = _chain()
    broken.loc[1, "implied_vol"] = np.nan
    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: broken,
        oi_for_date=lambda s, root, store=None: _oi(s),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["unexpired_identity_contracts"] == 2
    assert state["iv_contract_rate"] == 0.5
    assert state["target_gate_pass"] is False


def test_oi_match_rate_uses_full_unexpired_board_even_when_iv_is_missing():
    rows = []
    oi_rows = []
    publication = "2026-09-15"
    for i in range(100):
        right = "C" if i % 2 == 0 else "P"
        strike = 90.0 + i * 0.25
        rows.append({
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": strike,
            "right": right,
            "implied_vol": (np.nan if i < 10 else 0.20),
            "underlying_price": 100.0,
            "open_interest": 100 + i,
        })
        # The ten IV-missing contracts plus one IV-valid contract are absent
        # from settled OI.  A post-IV denominator would incorrectly see 89/90
        # and pass; the full unexpired board must report 89/100 and fail.
        if i >= 10 and i != 10:
            oi_rows.append({
                "root": "SPY",
                "expiration": "2026-10-16",
                "strike": strike,
                "right": right,
                "date": publication,
                "open_interest": 100 + i,
            })

    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=lambda s, root, store=None: pd.DataFrame(rows),
        oi_for_date=lambda s, root, store=None: pd.DataFrame(oi_rows),
    )
    state = r2.build_settled_state(
        "2026-09-14",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert state["unexpired_identity_contracts"] == 100
    assert state["model_input_contract_rate"] == pytest.approx(0.90)
    assert state["settled_oi_contract_rate"] == pytest.approx(0.89)
    assert state["target_gate_pass"] is False


def _state(position, spot=100.0, vol=0.2, time_years=30 / 365):
    exposure = r2._exposure_gex(
        np.array([position]),
        np.array([spot]),
        np.array([vol]),
        np.array([time_years]),
        np.array([100.0]),
        np.array(["C"]),
        greeks_fn=fake_greeks,
    )[0]
    return pd.DataFrame([
        {
            "root": "SPY",
            "expiration": "2026-10-16",
            "strike": 100.0,
            "right": "C",
            "position": position,
            "spot": spot,
            "vol": vol,
            "time_years": time_years,
            "exposure_gex": exposure,
        },
    ])


def test_position_only_change_is_attributed_to_position():
    got = r2.decompose_survivors(
        _state(100),
        _state(120),
        greeks_fn=fake_greeks,
    )
    assert abs(got["component_net"]["position"]) > 0
    assert abs(got["component_net"]["spot"]) < 1e-12
    assert abs(got["component_net"]["vol"]) < 1e-12
    assert abs(got["component_net"]["time"]) < 1e-12
    assert got["max_contract_closure_error_abs"] < 1e-10


def test_mixed_change_shapley_closes_exactly():
    got = r2.decompose_survivors(
        _state(100, spot=100, vol=0.20, time_years=40 / 365),
        _state(130, spot=104, vol=0.27, time_years=39 / 365),
        greeks_fn=fake_greeks,
    )
    assert got["survivor_contracts"] == 1
    assert got["max_contract_closure_error_abs"] < 1e-9
    assert sum(
        value
        for value in got["component_abs_share"].values()
        if value is not None
    ) == pytest.approx(1.0)


def test_analyze_pair_never_opens_outcome_labels_and_requires_consecutive_sessions():
    prior = {
        "2026-09-14": (100, 200),
        "2026-09-15": (110, 190),
    }

    def chain(session, root, store=None):
        return _chain(prior=prior[session])

    def oi_for_date(session, root, store=None):
        values = (110, 190) if session == "2026-09-15" else (120, 180)
        return _oi(session, values=values)

    api = SimpleNamespace(
        resolve_thetadata_store=lambda **kwargs: "/store",
        chain=chain,
        oi_for_date=oi_for_date,
    )
    got = r2.analyze_pair(
        "2026-09-14",
        "2026-09-15",
        "SPY",
        store_api=api,
        calendar_api=Calendar,
        greeks_fn=fake_greeks,
    )
    assert got["status"] == "SURVIVOR_DECOMPOSITION_COMPLETE"
    assert got["decomposition_scope"] == "survivor_contracts_only"
    assert got["pair_decision_eligible_not_before_session"] == "2026-09-16"
    assert got["outcome_labels_opened"] is False
    assert got["decomposition"]["max_contract_closure_error_abs"] < 1e-9

    with pytest.raises(r2.R2Refusal):
        r2.analyze_pair(
            "2026-09-14",
            "2026-09-16",
            "SPY",
            store_api=api,
            calendar_api=Calendar,
            greeks_fn=fake_greeks,
        )
