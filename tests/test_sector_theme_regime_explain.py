"""Verify deterministic, bilingual, numerically grounded research-only text."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from engine.sector_theme_regime_explain import explain_regime_preview
from engine.sector_theme_regime_fingerprint import compose_regime_fingerprint
from engine.sector_theme_owner_bridge import preview_us_theme_packet
from tests.test_sector_theme_regime_fingerprint import (
    fp, fact, row, END,
)
from tests.test_sector_theme_owner_bridge import fixture


def cards(out, family="group_cards"):
    return {c["tag"]: c for c in out[family]}


def test_p2c_01_empty_facet_readout_is_not_false_neutral():
    p = fp(rows={"AAA": row(ret=.02), "BBB": row(ret=-.02)})
    out = explain_regime_preview(p)
    assert out["status"] == "RESEARCH_PREVIEW_ONLY"
    assert out["group_cards"] == [] and out["single_name_cards"] == []
    assert "evidence_quality" in out["source_unmeasured_axes"]
    assert out["eligible_for_customer_publication"] is False
    assert out["predictive_or_trading_authority"] is False
    assert "概率" in out["message_zh"]


def test_p2c_02_valid_paired_narrowing_is_quantitative_and_bilingual():
    old = END - timedelta(days=7)
    p = fp(
        rows={
            "AAA": row(ret=-.1, close=85, ma20=90,
                       ma50=95, ma200=100, prev_ma50=96),
            "BBB": row(ret=.2),
        },
        previous_member_ids=("AAA", "BBB"),
        previous_measurements={"AAA": row(end=old), "BBB": row(end=old)},
        previous_period_end=old,
        previous_decision_at=old + timedelta(minutes=4),
        previous_membership_known_at=old - timedelta(days=2),
    )
    out = explain_regime_preview(p)
    c = cards(out)["positive_parent_rs_narrowing_same_member_breadth"]
    assert "+5.00%" in c["en"]
    assert "-50.0 pp" in c["en"]
    assert "见顶" in c["zh"]
    assert abs(c["metrics"]["rs_parent_frac"] - .05) < 1e-12
    assert c["metrics"]["uptrend_breadth_delta_frac"] == -.5
    assert c["forecast_probability"] is None and c["trade_recommendation"] is None


def test_p2c_03_flat_stocks_are_not_described_as_decliners():
    p = fp(members=("AAA", "BBB", "CCC"),
           rows={"AAA": row(ret=1.0), "BBB": row(ret=0.0),
                 "CCC": row(ret=0.0)})
    out = explain_regime_preview(p)
    c = cards(out)
    assert "majority_nonpositive_participation_proven_by_bounds" in c
    assert "positive_group_return_but_majority_nonpositive" in c
    assert "flat or negative" in c[
        "majority_nonpositive_participation_proven_by_bounds"]["en"]
    assert "decliners" not in c[
        "majority_nonpositive_participation_proven_by_bounds"]["en"]


def test_p2c_04_missing_quotes_do_not_become_claimed_majority():
    p = fp(members=("AAA", "BBB", "CCC", "DDD", "EEE"),
           rows={"AAA": row(ret=.01), "BBB": row(ret=.02),
                 "CCC": row(ret=-.02)})
    out = explain_regime_preview(p)
    assert not any("majority_" in c["tag"] for c in out["group_cards"])


def test_p2c_05_one_stock_can_outperform_parent_and_decline_absolutely():
    p = fp(rows={"AAA": row(ret=-.04), "BBB": row(ret=-.02)},
           parent_return=-.08, benchmark_return=0.0)
    out = explain_regime_preview(p)
    name_tags = cards(out, "single_name_cards")
    assert "name_relative_leadership_despite_absolute_decline" in name_tags
    card = name_tags["name_relative_leadership_despite_absolute_decline"]
    assert "absolute return -4.00%" in card["en"] or "absolute return -2.00%" in card["en"]
    assert "not an uptrend" in card["en"]
    assert "跑赢" in cards(out, "single_name_cards")[
        "name_outperforming_parent_while_group_lags_market"]["zh"]


def test_p2c_06_above_ma50_does_not_claim_peers_are_below_when_equal():
    p = fp(members=("AAA", "BBB", "CCC"), rows={
        "AAA": row(ret=.02),
        "BBB": row(ret=0, close=108, ma20=108, ma50=108,
                   ma200=95, prev_ma50=106),
        "CCC": row(ret=-.03, close=85, ma20=90, ma50=95,
                   ma200=100, prev_ma50=96),
    })
    out = explain_regime_preview(p)
    c = cards(out, "single_name_cards")[
        "name_above_ma50_while_group_majority_not_above"]
    assert "on, not below" in c["en"]
    assert "33.3%" in c["en"]


def test_p2c_07_cross_horizon_conflicts_not_averaged():
    a = fact(rows={"AAA": row(ret=-.03), "BBB": row(ret=-.01)})
    b = fact(horizon="20d", rows={
        "AAA": row(ret=.20, horizon="20d"),
        "BBB": row(ret=.15, horizon="20d"),
    }, parent_return=.10)
    p = compose_regime_fingerprint({"5d": a, "20d": b})
    out = explain_regime_preview(p)
    c = cards(out)["cross_horizon_parent_rs_sign_conflict"]
    assert "20d" in c["en"] and "5d" in c["en"]
    assert "not averaged" in c["en"]


def test_p2c_08_forged_group_tags_rechecked_against_numbers():
    p = fp(rows={"AAA": row(ret=.02), "BBB": row(ret=-.02)})
    p["facets"].append({
        "id": "majority_nonpositive_participation_proven_by_bounds",
        "horizon": "5d",
    })
    out = explain_regime_preview(p)
    assert not out["group_cards"]
    assert "majority_nonpositive_participation_proven_by_bounds" in out[
        "withheld_unverified_facets"]


def test_p2c_09_forged_ticker_tag_does_not_become_entry_signal():
    p = fp()
    p["single_names"]["AAA"]["facets"].append({
        "id": "name_relative_leadership_despite_absolute_decline",
        "horizon": "5d",
    })
    out = explain_regime_preview(p)
    assert out["single_name_cards"] == []
    assert "name_relative_leadership_despite_absolute_decline" in out[
        "withheld_unverified_facets"]


def test_p2c_10_forged_publishing_or_predictive_authority_refuses():
    p = fp()
    p["authority"]["eligible_for_customer_publication"] = True
    out = explain_regime_preview(p)
    assert out["status"] == "HELD"
    assert out["reason"] == "unqualified_publication_or_trading_authority"
    p = fp()
    p["authority"]["predictive_promoted"] = True
    assert explain_regime_preview(p)["status"] == "HELD"


def test_p2c_11_wrong_schema_or_structure_holds():
    assert explain_regime_preview(None)["status"] == "HELD"
    p = fp()
    p["horizons"] = None
    assert explain_regime_preview(p)["reason"] == "invalid_fingerprint_structure"


def test_p2c_12_no_mutations_and_deterministic_bilingual_cards():
    p = fp(members=("AAA", "BBB", "CCC"),
           rows={"AAA": row(ret=1.0),
                 "BBB": row(ret=0.0), "CCC": row(ret=0.0)})
    before = deepcopy(p)
    a = explain_regime_preview(p)
    b = explain_regime_preview(p)
    assert p == before and a == b
    assert a["group_cards"][0]["en"] and a["group_cards"][0]["zh"]
    assert all(c["source_status"] == "unqualified_descriptive_preview"
               for c in a["group_cards"])


def test_p2c_13_integration_preview_includes_explanation_without_rights_grant():
    out = preview_us_theme_packet(fixture())
    assert out["status"] == "RESEARCH_PREVIEW_ONLY"
    e = out["explanation"]
    assert e["schema"] == "sector_theme_regime_explanation/v1"
    assert e["status"] == "RESEARCH_PREVIEW_ONLY"
    assert e["eligible_for_customer_publication"] is False


def test_p2c_14_zero_member_group_does_not_generate_fiction():
    out = explain_regime_preview(fp(members=(), rows={}))
    assert out["group_cards"] == [] and out["single_name_cards"] == []
    assert out["eligible_for_customer_publication"] is False


def test_p2c_15_ma_explanation_preserves_intraday_bar_basis():
    items = {
        "AAA": row(ret=.02),
        "BBB": row(ret=0, close=108, ma20=108, ma50=108,
                   ma200=95, prev_ma50=106),
        "CCC": row(ret=-.03, close=85, ma20=90, ma50=95,
                   ma200=100, prev_ma50=96),
    }
    for item in items.values():
        item["ma_basis"] = "1m_bars"
    p = fp(members=("AAA", "BBB", "CCC"), rows=items, ma_basis="1m_bars")
    out = explain_regime_preview(p)
    card = cards(out, "single_name_cards")[
        "name_above_ma50_while_group_majority_not_above"]
    assert "one-minute bars" in card["en"]
    assert "1分钟K线" in card["zh"]
    assert card["metrics"]["ma_basis"] == "1m_bars"
    p["single_names"]["AAA"]["horizons"]["5d"]["ma_basis"] = "daily_sessions"
    out = explain_regime_preview(p)
    assert "name_above_ma50_while_group_majority_not_above" not in cards(
        out, "single_name_cards")
    assert "name_above_ma50_while_group_majority_not_above" in out[
        "withheld_unverified_facets"]


def test_p2c_16_malformed_extreme_bound_cannot_crash_or_invent_majority():
    p = fp(members=("AAA", "BBB", "CCC"),
           rows={"AAA": row(ret=1.0), "BBB": row(ret=0),
                 "CCC": row(ret=0)})
    p["horizons"]["5d"]["participation"][
        "positive_return_breadth"]["identification_bounds"] = [10**400, 1]
    out = explain_regime_preview(p)
    assert not any("majority_" in c["tag"] for c in out["group_cards"])
    assert "majority_nonpositive_participation_proven_by_bounds" in out[
        "withheld_unverified_facets"]
