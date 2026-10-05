from __future__ import annotations

import math


def _subject():
    from scripts import build_forex as bf
    assert hasattr(bf, "_r4_currency_rows"), "R4 currency-row composer is not implemented"
    return bf._r4_currency_rows


def _strength_fixture():
    return {
        "default": "1m",
        "order": ["1w", "1m", "3m"],
        "horizons": {
            "1m": [
                {"ccy": "USD", "ccy_zh": "美元", "strength": 0.95, "vs_usd_pct": 0.0, "em": False},
                # Deliberately make strength order disagree with vs-USD order.
                {"ccy": "EUR", "ccy_zh": "欧元", "strength": 0.85, "vs_usd_pct": 0.4, "em": False},
                {"ccy": "JPY", "ccy_zh": "日元", "strength": -0.20, "vs_usd_pct": 1.9, "em": False},
                {"ccy": "GBP", "ccy_zh": "英镑", "strength": 0.60, "vs_usd_pct": -0.8, "em": False},
                {"ccy": "AUD", "ccy_zh": "澳元", "strength": -0.90, "vs_usd_pct": None, "em": False},
            ]
        },
    }


def test_currency_rows_use_one_month_vs_usd_for_rank_value_and_bar():
    compose = _subject()
    got = compose(_strength_fixture(), horizon="1m")

    assert got["basis"] == "vs_usd"
    assert got["horizon"] == "1m"
    assert [r["ccy"] for r in got["rows"]] == ["JPY", "EUR", "GBP", "AUD"]

    jpy, eur, gbp, _aud = got["rows"]
    assert jpy["move_pct"] == 1.9
    assert eur["move_pct"] == 0.4
    assert gbp["move_pct"] == -0.8

    # Same vs-USD quantity controls the zero-anchored bar.
    assert got["domain_abs_pct"] == 1.9
    assert jpy["bar_frac"] == 1.0
    assert math.isclose(eur["bar_frac"], 0.4 / 1.9)
    assert math.isclose(gbp["bar_frac"], -0.8 / 1.9)

    assert got["leader"]["ccy"] == "JPY"
    assert got["n_available"] == 3
    assert got["n_below_usd"] == 1


def test_currency_rows_keep_missing_move_unavailable_not_zero():
    compose = _subject()
    got = compose(_strength_fixture(), horizon="1m")
    aud = next(r for r in got["rows"] if r["ccy"] == "AUD")

    assert aud["available"] is False
    assert aud["move_pct"] is None
    assert aud["bar_frac"] is None
    assert got["n_available"] == 3
    assert got["n_below_usd"] == 1


def _readiness_subject():
    from scripts import build_forex as bf
    assert hasattr(bf, "_r4_readiness"), "R4 readiness composer is not implemented"
    return bf._r4_readiness


def test_readiness_stale_core_preserves_receipts_and_blocks_dependent_action():
    compose = _readiness_subject()
    deps = {
        "price": {"state": "stale", "asof": "2026-09-24", "critical": True},
        "short_rates": {"state": "fresh", "asof": "2026-09-26", "critical": True},
        "positioning": {"state": "fresh", "asof": "2026-09-22", "critical": False},
    }
    got = compose(
        deps,
        asof="2026-09-24",
        checked_at="2026-09-27T00:00:00Z",
        action_requirements={
            "open_detail": ["price"],
            "prepare_watch": ["price", "short_rates"],
            "read_positioning": ["positioning"],
        },
    )

    assert got["verdict"] == "stale"
    assert got["dependencies"]["price"]["asof"] == "2026-09-24"
    assert got["actions"]["open_detail"]["allowed"] is False
    assert got["actions"]["prepare_watch"]["allowed"] is False
    assert got["actions"]["read_positioning"]["allowed"] is True
    assert "Older" in got["banner_message"]["en"]
    assert "较早" in got["banner_message"]["zh"]


def test_readiness_missing_secondary_feed_degrades_without_blocking_core_actions():
    compose = _readiness_subject()
    deps = {
        "price": {"state": "fresh", "asof": "2026-09-26", "critical": True},
        "short_rates": {"state": "fresh", "asof": "2026-09-26", "critical": True},
        "positioning": {"state": "missing", "asof": None, "critical": False},
    }
    got = compose(
        deps,
        asof="2026-09-26",
        action_requirements={
            "open_detail": ["price"],
            "prepare_watch": ["price", "short_rates"],
            "read_positioning": ["positioning"],
        },
    )

    assert got["verdict"] == "degraded"
    assert got["actions"]["open_detail"]["allowed"] is True
    assert got["actions"]["prepare_watch"]["allowed"] is True
    assert got["actions"]["read_positioning"]["allowed"] is False
    assert got["dependencies"]["positioning"]["state"] == "missing"
    assert "unavailable" in got["banner_message"]["en"].lower()
