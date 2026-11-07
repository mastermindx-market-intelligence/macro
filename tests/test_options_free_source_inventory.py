"""Offline research-inventory semantic tests; no disk/credentials/network."""
from __future__ import annotations

import pytest

from collectors.options_free_samples import SourceRejected
from scripts.options_free_source_inventory import build_receipt


def _inputs():
    eod = {
        "schema": "options.free_cboe_eval/v1",
        "effective_trade_session": "2025-03-28",
        "rights": "internal_evaluation_only_pending_commercial_rights",
        "publish": False, "signal_authority": False,
        "rows_total": 10, "rows_standard": 9, "underlyings_standard": 3,
        "observed_sample_only": {
            "XLK": {"C": {"standard_series_rows": 3}, "P": {"standard_series_rows": 2}},
        },
    }
    tbt = {
        "schema": "options.free_cboe_tbt_eval/v1",
        "effective_trade_session": "2025-03-28",
        "rights": "internal_evaluation_only_pending_commercial_rights",
        "publish": False, "signal_authority": False,
        "rows_total": 30, "rows_fully_classified_with_economics": 18,
        "underlyings": 3, "unknown_reasons": {"open_close_unknown": 12},
        "participant_side_by_underlying": {
            "XLK": {"participant_side_rows": 4, "classifiable_rows": 3},
        },
    }
    return eod, tbt


def _receipt():
    eod, tbt = _inputs()
    return build_receipt(
        eod, tbt, volume_uuid="testvol",
        source_sha={"c1_eod_demo": "1" * 64, "c1_tbt_demo": "2" * 64},
        cutover_at="2026-10-08T23:00:00+00:00",
    )


def test_private_receipt_is_never_a_live_options_feed():
    x = _receipt()
    assert x["sources"][0]["rows"] == 10
    assert x["sources"][1]["participant_side_rows"] == 30
    assert x["sources"][1]["field_classifiable_rows"] == 18
    assert x["publish"] is False
    assert x["signal_authority"] is False
    assert x["trading_authority"] is False
    assert x["live_consumers_enabled"] == []
    assert x["sources"][0]["quote_age_eligible"] is False
    assert x["sources"][1]["original_historical_available_at"] is None


def test_silent_sample_absence_is_not_zero_options_volume():
    x = _receipt()
    assert x["illustrative_fixed_etf_sample_coverage"]["technology"]["XLK"][
        "eod_sample_series_rows"] == 5
    assert x["illustrative_fixed_etf_sample_coverage"]["defensives"]["XLP"][
        "tbt_sample_participant_side_rows"] is None
    assert x["illustrative_fixed_etf_sample_coverage"]["defensives"]["XLP"][
        "missing_means_sample_not_selected_not_zero_market_volume"] is True


def test_eod_and_tbt_populations_are_never_summed():
    x = _receipt()
    assert x["sources"][0]["rows"] == 10
    assert x["sources"][1]["participant_side_rows"] == 30
    assert "total_market_contracts" not in x
    assert "market_share" not in x


@pytest.mark.parametrize("source,field,value", [
    ("eod", "rights", "commercial_allowed"),
    ("tbt", "publish", True),
    ("eod", "signal_authority", True),
    ("tbt", "effective_trade_session", "2026-10-08"),
])
def test_authority_or_chronology_escalation_refused(source, field, value):
    eod, tbt = _inputs()
    obj = eod if source == "eod" else tbt
    obj[field] = value
    with pytest.raises(SourceRejected):
        build_receipt(eod, tbt, volume_uuid="testvol", source_sha={},
                      cutover_at="2026-10-08T23:00:00+00:00")
