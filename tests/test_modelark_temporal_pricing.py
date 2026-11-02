"""Official current commercial BytePlus ModelArk pricing, deterministic only.

Source (2026-10-30): https://console.byteplus.com/ark/region:ap-southeast-1/docs/model-pricing
The existing ai_costs owner prices current invoices approximately; never
promotes a price estimate into issuer/Worker/Capacity authority.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from lib import ai_costs


def _instant(y, mon, d, h, minute=0):
    """Local Asia/Shanghai time converted explicitly to UTC."""
    # China Standard Time is UTC+08 in the currently reviewed window.
    return datetime(y, mon, d, h, minute, tzinfo=timezone(timedelta(hours=8)))


def test_glm_exact_version_standard_rate_and_cache_ratio():
    assert ai_costs.estimate_cost_usd("glm-5-3-flash-260828", 1_000_000, 1_000_000) == pytest.approx(.65)
    assert ai_costs.estimate_cost_usd(
        "glm-5-3-flash-260828", 0, 0, cache_read_tokens=1_000_000
    ) == pytest.approx(.03)
    # Storage/hour price cannot be coerced into write-token price.
    assert ai_costs.estimate_cost_usd(
        "glm-5-3-flash-260828", 0, 0, cache_creation_tokens=5
    ) is None


def test_dola_versioned_family_rate_is_labeled_estimate_only():
    assert ai_costs.estimate_cost_usd("dola-seed-2-1-turbo-260628", 1_000_000, 1_000_000) == pytest.approx(3.0)
    assert ai_costs.estimate_cost_usd(
        "dola-seed-2-1-turbo-260628", 0, 0, cache_read_tokens=1_000_000
    ) == pytest.approx(.1)


@pytest.mark.parametrize("local_instant,expected_in,expected_out", [
    (_instant(2026, 11, 2, 8, 59), .15, .60),
    (_instant(2026, 11, 2, 9), .30, 1.20),
    (_instant(2026, 11, 2, 11, 59), .30, 1.20),
    (_instant(2026, 11, 2, 12), .15, .60),
    (_instant(2026, 11, 2, 13, 59), .15, .60),
    (_instant(2026, 11, 2, 14), .30, 1.20),
    (_instant(2026, 11, 2, 17, 59), .30, 1.20),
    (_instant(2026, 11, 2, 18), .15, .60),
    (_instant(2026, 11, 1, 10), .15, .60),  # Sunday stays OFF
    (_instant(2026, 11, 7, 16), .15, .60),  # Saturday stays OFF
])
def test_deepseek_v41_exact_peak_offpeak_asia_shanghai(
    local_instant, expected_in, expected_out,
):
    # One million each demonstrates the exact per-MTok rate pair.
    rate = ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017", 1_000_000, 1_000_000,
        as_of_utc=local_instant.astimezone(timezone.utc),
    )
    assert rate == pytest.approx(expected_in + expected_out)
    # Verified cached-input price is $0.006/M peak or $0.003/M offpeak.
    cache = ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017", 0, 0, cache_read_tokens=1_000_000,
        as_of_utc=local_instant,
    )
    assert cache == pytest.approx(expected_in * 0.02)


@pytest.mark.parametrize("as_of", [None, datetime(2026, 11, 2), "2026-11-02T10:00Z", True])
def test_variable_rate_never_guesses_clock(as_of):
    assert ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017", 100, 100, as_of_utc=as_of,
    ) is None


def test_deepseek_exact_model_only_and_creation_unknown():
    assert ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017-X", 10, 10,
        as_of_utc=_instant(2026, 11, 2, 10),
    ) is None
    assert ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017", 100, 10,
        as_of_utc=_instant(2026, 11, 2, 10),
        cache_creation_tokens=1,
    ) is None


def test_current_standard_rate_estimate_cannot_enable_provider():
    from engine import provider_production_modes as ppm

    for name in ppm.MODELARK_MODELS:
        mode = ppm.load_modes()[name]
        assert mode.enabled is False
        assert ppm.MODELARK_RESPONSES_PROFILES[name].qualification == ppm.PROFILE_UNQUALIFIED_PENDING_CANARY


def test_legacy_prefix_pricing_remains_compatible():
    assert ai_costs.estimate_cost_usd("claude-haiku-4-5-20251001", 1_000_000, 0) == pytest.approx(1.0)


def test_invalid_temporal_rate_schema_refuses(monkeypatch):
    pricing = ai_costs._load_pricing()
    pricing["temporal_per_mtok"]["deepseek-v4-1-flash-261017"]["schedule"] = "fake"
    monkeypatch.setattr(ai_costs, "_load_pricing", lambda *a: pricing)
    assert ai_costs.estimate_cost_usd(
        "deepseek-v4-1-flash-261017", 100, 100,
        as_of_utc=_instant(2026, 11, 2, 10),
    ) is None
