"""Sibling contexts retain their source clock and do not turn into risk votes."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from engine.market_fragility import observe, published_context

NOW = datetime(2026, 11, 13, 14, tzinfo=timezone.utc)


def latest():
    return {
        "date": "2026-11-12",
        "vol_regime": {"available": True, "asof": "2026-11-12", "vix": 20.0, "vvix": 100.0, "ts_slope": 0.95},
        "conditions": {"risk_appetite": {"realized_vol": 22.5}},
        "liquidity_quality": {"asof": "2026-11-12", "label": "contracting", "degraded": False},
    }


def test_incumbent_values_and_dates_are_preserved_without_rescoring():
    context = published_context(latest(), now=NOW)
    assert context["vix"]["value"] == 20.0
    assert context["vvix"]["value"] == 100.0
    assert context["vix_term_ratio"]["value"] == 0.95
    assert context["realized_volatility"]["value"] == 22.5
    assert context["macro_liquidity"]["value"] == "contracting"
    assert context["macro_liquidity"]["is_market_depth"] is False
    assert context["composite_score"] is None
    assert context["market_depth"]["value"] is None
    assert context["gamma_spot_sensitivity"]["value"] is None
    assert context["realized_volatility"]["raw_input_clocks_verified"] is False


def test_stale_vvix_does_not_inherit_fresh_gamma_or_regime_date():
    data = latest()
    data["vol_regime"]["asof"] = "2026-11-10"
    context = published_context(data, now=NOW)
    assert context["vvix"]["source_session"] == "2026-11-10"
    assert context["vvix"]["age_sessions"] == 2
    assert context["vvix"]["status"] == "stale"
    assert context["vvix"]["current_publication"] is False
    assert context["realized_volatility"]["source_session"] == "2026-11-12"


@pytest.mark.parametrize("asof", [None, "bad", "2026-11-16", "2026-11-08"])
def test_invalid_or_future_source_date_not_replaced_with_current_date(asof):
    data = latest()
    data["vol_regime"]["asof"] = asof
    context = published_context(data, now=NOW)
    assert context["vvix"]["status"] == "invalid_source_session"
    assert context["vvix"]["current_publication"] is False


def test_missing_context_is_unknown_not_zero_or_calm():
    context = published_context({}, now=NOW)
    for key in ("vix", "vvix", "realized_volatility", "macro_liquidity"):
        assert context[key]["value"] is None
        assert context[key]["status"] == "unavailable"
        assert context[key]["trade_authority"] is False


def test_low_quality_owner_does_not_get_upgraded_by_projection():
    data = latest()
    data["vol_regime"]["available"] = False
    data["liquidity_quality"]["degraded"] = True
    context = published_context(data, now=NOW)
    assert context["vix"]["status"] == "degraded"
    assert context["macro_liquidity"]["status"] == "degraded"


def test_malformed_nested_values_degrade_without_breaking_regime_build():
    data = {"conditions": [], "vol_regime": [1], "liquidity_quality": {"label": ["bad"]}}
    context = published_context(data, now=NOW)
    assert context["vix"]["value"] is None
    assert context["macro_liquidity"]["value"] is None


def test_numeric_session_indices_are_not_coerced_into_epoch_dates():
    data = pd.DataFrame({"gamma_regime": ["short"]}, index=[np.int64(12345)])
    out = observe(data, now=NOW)
    assert out["state"] == "unknown"
    assert out["clocks"]["source_session"] is None


def test_full_window_streak_discloses_left_censoring():
    data = pd.DataFrame({"gamma_regime": ["short"] * 3},
                        index=pd.to_datetime(["2026-11-10", "2026-11-11", "2026-11-12"]))
    hist = observe(data, now=NOW, window_sessions=3)["history"]
    assert hist["terminal_run_sessions"] == 3
    assert hist["terminal_run_left_censored"] is True


def test_malformed_tier_fails_closed():
    data = pd.DataFrame({"gamma_regime": ["short"], "tier": [["full"]]}, index=pd.to_datetime(["2026-11-12"]))
    assert observe(data, now=NOW)["state"] == "unknown"
