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


def _qualified_dependency(name, state, asof, critical):
    """Synthetic receipt: labels alone no longer qualify an R26 source."""
    return {"dependency_id": name, "state": state, "asof": asof,
            "critical": critical, "value_kind": "number", "value": 0.0,
            "unit": "test units", "source_observed_at": asof + "T16:00:00Z" if asof else None,
            "source_available_at": asof + "T16:00:02Z" if asof else None,
            "expires_at": "2026-09-28T00:00:00Z" if asof else None}


def _readiness_subject():
    from scripts import build_forex as bf
    assert hasattr(bf, "_r4_readiness"), "R4 readiness composer is not implemented"
    return bf._r4_readiness


def test_readiness_stale_core_preserves_receipts_and_blocks_dependent_action():
    compose = _readiness_subject()
    deps = {
        "price": _qualified_dependency("price", "stale", "2026-09-24", True),
        "short_rates": _qualified_dependency("short_rates", "fresh", "2026-09-26", True),
        "positioning": _qualified_dependency("positioning", "fresh", "2026-09-22", False),
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
    assert "unavailable" in got["banner_message"]["en"]
    assert "不可用" in got["banner_message"]["zh"]


def test_readiness_missing_secondary_feed_degrades_without_blocking_core_actions():
    compose = _readiness_subject()
    deps = {
        "price": _qualified_dependency("price", "fresh", "2026-09-26", True),
        "short_rates": _qualified_dependency("short_rates", "fresh", "2026-09-26", True),
        "positioning": _qualified_dependency("positioning", "missing", None, False),
    }
    got = compose(
        deps,
        asof="2026-09-26",
        checked_at="2026-09-27T00:00:00Z",
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


def test_r4_currency_rows_reject_boolean_and_text_moves():
    strength = _strength_fixture()
    for row in strength["horizons"]["1m"]:
        if row["ccy"] != "USD":
            row["vs_usd_pct"] = True if row["ccy"] == "JPY" else "0"
    got = _subject()(strength)
    assert got["n_available"] == 0
    assert all(row["move_pct"] is None and row["bar_frac"] is None for row in got["rows"])


# --------------------------------------------------------------------------- #
# R4 currency rows: malformed source rows and a duplicated currency identity
# --------------------------------------------------------------------------- #

def _horizon_fixture(rows):
    return {"default": "1m", "order": ["1m"], "horizons": {"1m": list(rows)}}


def test_currency_rows_drop_a_none_row_without_crashing_or_inventing_a_zero():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "ccy_zh": "欧元", "strength": 0.85, "vs_usd_pct": 0.4, "em": False},
        None,
        {"ccy": "JPY", "ccy_zh": "日元", "strength": -0.20, "vs_usd_pct": 1.9, "em": False},
    ]), horizon="1m")

    # The malformed row is neither ranked nor turned into a zero-valued currency.
    assert [r["ccy"] for r in got["rows"]] == ["JPY", "EUR"]
    assert got["n_available"] == 2
    assert got["n_above_usd"] == 2
    assert got["n_below_usd"] == 0
    assert got["domain_abs_pct"] == 1.9
    assert got["leader"]["ccy"] == "JPY"
    # It is disclosed rather than silently dropped.
    assert got["malformed_rows"] == [{"index": 1, "reason": "not_a_mapping"}]


def test_currency_rows_drop_a_non_mapping_row_without_crashing():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "ccy_zh": "欧元", "strength": 0.85, "vs_usd_pct": 0.4, "em": False},
        "JPY",
        {"ccy": "MXN", "ccy_zh": "墨西哥比索", "strength": 0.10, "vs_usd_pct": 0.3, "em": True},
    ]), horizon="1m")

    assert [r["ccy"] for r in got["rows"]] == ["EUR", "MXN"]
    assert got["n_available"] == 2
    assert got["n_above_usd"] == 2
    assert got["domain_abs_pct"] == 0.4
    assert got["leader"]["ccy"] == "EUR"
    assert got["malformed_rows"] == [{"index": 1, "reason": "not_a_mapping"}]


def test_currency_rows_disclose_a_row_without_a_currency_identity():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "ccy_zh": "欧元", "vs_usd_pct": 0.4},
        {"vs_usd_pct": 0.9},
    ]), horizon="1m")

    assert [r["ccy"] for r in got["rows"]] == ["EUR"]
    assert got["n_available"] == 1
    assert got["malformed_rows"] == [{"index": 1, "reason": "missing_currency_identity"}]


def test_currency_rows_reject_a_non_string_currency_identity_instead_of_ranking_it():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "ccy_zh": "欧元", "vs_usd_pct": 0.4},
        {"ccy": float("nan"), "vs_usd_pct": 1.9},
    ]), horizon="1m")

    # A non-string identity is not a currency, so it cannot be ranked or lead.
    assert [r["ccy"] for r in got["rows"]] == ["EUR"]
    assert got["n_available"] == 1
    assert got["leader"]["ccy"] == "EUR"
    assert got["domain_abs_pct"] == 0.4
    assert got["malformed_rows"] == [{"index": 1, "reason": "missing_currency_identity"}]


def test_currency_rows_quarantine_a_duplicate_currency_identity_instead_of_picking_a_winner():
    compose = _subject()
    jpy = {"ccy": "JPY", "ccy_zh": "日元", "strength": -0.20, "em": False}
    mxn = {"ccy": "MXN", "ccy_zh": "墨西哥比索", "strength": 0.10, "vs_usd_pct": 0.3, "em": True}

    agreeing = compose(_horizon_fixture([
        {**jpy, "vs_usd_pct": 1.2}, {**jpy, "vs_usd_pct": 1.2}, mxn,
    ]), horizon="1m")
    contradictory = compose(_horizon_fixture([
        {**jpy, "vs_usd_pct": 1.2}, {**jpy, "vs_usd_pct": -0.5}, mxn,
    ]), horizon="1m")

    # Quarantine means no observation wins the identity: a duplicate that agrees
    # with itself and a duplicate that contradicts itself cannot be told apart.
    assert agreeing == contradictory

    assert [r["ccy"] for r in agreeing["rows"]] == ["MXN", "JPY"]
    quarantined = agreeing["rows"][1]
    assert quarantined["available"] is False
    assert quarantined["move_pct"] is None
    assert quarantined["bar_frac"] is None
    assert quarantined["unavailable_reason"] == "duplicate_currency_identity"

    # The duplicated identity is counted once, cannot be ranked and cannot lead.
    assert agreeing["n_available"] == 1
    assert agreeing["n_above_usd"] == 1
    assert agreeing["n_below_usd"] == 0
    assert agreeing["domain_abs_pct"] == 0.3
    assert agreeing["leader"]["ccy"] == "MXN"


def test_currency_rows_valid_control_keeps_the_ranked_result_unchanged():
    compose = _subject()
    got = compose(_strength_fixture(), horizon="1m")

    assert got["basis"] == "vs_usd"
    assert got["horizon"] == "1m"
    assert got["malformed_rows"] == []
    assert [r["ccy"] for r in got["rows"]] == ["JPY", "EUR", "GBP", "AUD"]
    assert got["domain_abs_pct"] == 1.9
    assert got["n_available"] == 3
    assert got["n_above_usd"] == 2
    assert got["n_below_usd"] == 1
    assert got["leader"]["ccy"] == "JPY"
    assert got["rows"][0]["bar_frac"] == 1.0
    assert got["rows"][0]["unavailable_reason"] is None
    aud = got["rows"][3]
    assert aud["available"] is False
    assert aud["move_pct"] is None
    assert aud["bar_frac"] is None
    assert aud["unavailable_reason"] == "missing_or_invalid_move"


def test_currency_rows_treat_a_zero_move_as_valid_and_a_missing_move_as_unavailable():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "ccy_zh": "欧元", "strength": 0.85, "vs_usd_pct": 0.0, "em": False},
        {"ccy": "JPY", "ccy_zh": "日元", "strength": -0.20, "vs_usd_pct": None, "em": False},
        {"ccy": "MXN", "ccy_zh": "墨西哥比索", "strength": 0.10, "vs_usd_pct": 0.5, "em": True},
    ]), horizon="1m")

    assert [r["ccy"] for r in got["rows"]] == ["MXN", "EUR", "JPY"]
    eur, jpy = got["rows"][1], got["rows"][2]
    # Zero is a valid observation, not a missing one.
    assert eur["available"] is True
    assert eur["move_pct"] == 0.0
    assert eur["bar_frac"] == 0.0
    assert eur["unavailable_reason"] is None
    # Missing stays unavailable and never becomes a neutral zero.
    assert jpy["available"] is False
    assert jpy["move_pct"] is None
    assert jpy["bar_frac"] is None
    assert jpy["unavailable_reason"] == "missing_or_invalid_move"

    assert got["n_available"] == 2
    assert got["n_above_usd"] == 1
    assert got["n_below_usd"] == 0
    assert got["domain_abs_pct"] == 0.5
    assert got["leader"]["ccy"] == "MXN"


def test_currency_rows_all_zero_moves_keep_a_usable_zero_scale():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "EUR", "vs_usd_pct": 0.0},
        {"ccy": "JPY", "vs_usd_pct": 0.0},
    ]), horizon="1m")

    assert got["domain_abs_pct"] == 0.0
    assert got["n_available"] == 2
    assert got["n_above_usd"] == 0
    assert got["n_below_usd"] == 0
    assert all(row["bar_frac"] == 0.0 for row in got["rows"])
    assert got["leader"]["ccy"] == "EUR"


def test_currency_rows_exclude_the_usd_reference_whatever_its_case():
    compose = _subject()
    got = compose(_horizon_fixture([
        {"ccy": "USD", "vs_usd_pct": 0.0},
        {"ccy": "usd", "vs_usd_pct": 0.0},
        {"ccy": "EUR", "vs_usd_pct": 0.4},
    ]), horizon="1m")

    # USD is the zero reference, never a ranked currency.
    assert [r["ccy"] for r in got["rows"]] == ["EUR"]
    assert got["n_available"] == 1
    assert got["leader"]["ccy"] == "EUR"


def test_currency_rows_reject_a_malformed_horizon_list_without_crashing():
    compose = _subject()
    got = compose({"horizons": {"1m": 7}}, horizon="1m")

    assert got["rows"] == []
    assert got["n_available"] == 0
    assert got["leader"] is None
    assert got["domain_abs_pct"] == 0.0
    assert got["malformed_rows"] == [{"index": None, "reason": "malformed_horizon_rows"}]


def test_currency_rows_reject_a_malformed_strength_payload_without_crashing():
    compose = _subject()
    got = compose(["EUR"], horizon="1m")

    assert got["rows"] == []
    assert got["n_available"] == 0
    assert got["leader"] is None
    assert got["malformed_rows"] == [{"index": None, "reason": "malformed_strength"}]


def test_currency_rows_an_absent_horizon_has_nothing_to_compare():
    compose = _subject()
    got = compose({"horizons": {"3m": []}}, horizon="1m")

    assert got["rows"] == []
    assert got["n_available"] == 0
    assert got["leader"] is None
    # An absent horizon is not a malformed one, so there is nothing to disclose.
    assert got["malformed_rows"] == []
