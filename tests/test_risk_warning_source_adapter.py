"""Actual filesystem -> additive existing-banner payload contract tests.

Fixtures are synthetic; these do not claim production publication or market
forecast validation. Paths and JSON pointers match audited existing producers.
"""
from copy import deepcopy
import importlib
import json

import pytest

SESSION = "2026-09-25"


def radar(state="caution", score=80, market="us", session=SESSION):
    """Native-shaped synthetic source; no dependency on another test module."""
    out = {"schema": "risk_radar.v2" if market == "us" else "risk_radar_intl.v1",
           "asof": session, "state": state, "top_score": score,
           "dominant_label_en": "Rates / inflation shock"}
    if market != "us":
        out["market"] = market
    return out


def adapter():
    return importlib.import_module("scripts.risk_warning_source_adapter")


def write(root, relative, value):
    p = root / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value), encoding="utf-8")


def legacy():
    return {"schema": "rr_banner.v1", "asof": SESSION,
            "generated_at": "2026-09-28T00:18:32+00:00", "alert": None}


def test_existing_us_and_three_country_producers_are_read_without_recomputation(tmp_path):
    for market, directory in [("us", "regime"), ("cn", "china_regime"),
                              ("hk", "hk_regime"), ("ca", "canada_regime")]:
        write(tmp_path, directory + "/latest.json",
              {"risk_radar": radar("risk-off" if market == "cn" else "caution", market=market)})
    original = legacy()
    result = adapter().augment_banner_payload(original, data_root=tmp_path,
                                              expected_sessions={k: SESSION for k in ("us", "cn", "hk", "ca")})
    assert result["warning_projection"]["coverage"]["current"] == 4
    assert result["warning_projection"]["rows"][0]["market"] == "cn"
    assert original == legacy()
    for key, value in original.items():
        assert result[key] == value  # legacy meaning and bytes-as-values preserved


def test_seven_international_records_use_their_native_market_scope(tmp_path):
    markets = ["jp", "kr", "au", "br", "ez", "gb", "in"]
    write(tmp_path, "intl/latest.json", {"records": [
        {"cc": market.upper(), "risk_radar": radar("elevated", market=market)} for market in markets
    ]})
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={k: SESSION for k in markets})
    assert result["warning_projection"]["coverage"]["current"] == 7
    assert result["warning_projection"]["current_attention_counts"]["high"] == 7
    assert all(len(item["sha256"]) == 64 for item in result["warning_projection_sources"].values())


def test_missing_region_remains_in_expected_coverage(tmp_path):
    write(tmp_path, "regime/latest.json", {"risk_radar": radar()})
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={"us": SESSION, "cn": SESSION})
    assert result["warning_projection"]["coverage"]["unavailable_markets"] == ["cn"]
    assert result["warning_projection_sources"]["cn"]["status"] == "missing_file"


def test_malformed_country_file_does_not_hide_other_markets(tmp_path):
    write(tmp_path, "regime/latest.json", {"risk_radar": radar()})
    (tmp_path / "china_regime").mkdir()
    (tmp_path / "china_regime/latest.json").write_text("{broken", encoding="utf-8")
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={"us": SESSION, "cn": SESSION})
    assert result["warning_projection"]["coverage"]["current"] == 1
    assert result["warning_projection_sources"]["cn"]["status"] == "invalid_json"


def test_duplicate_international_country_is_not_last_writer_wins(tmp_path):
    write(tmp_path, "intl/latest.json", {"records": [
        {"cc": "JP", "risk_radar": radar("risk-off", market="jp")},
        {"cc": "JP", "risk_radar": radar("calm", market="jp")},
    ]})
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={"jp": SESSION})
    assert result["warning_projection"]["coverage"]["current"] == 0
    assert result["warning_projection_sources"]["jp"]["status"] == "duplicate_market_records"


def test_international_record_cannot_supply_another_markets_state(tmp_path):
    write(tmp_path, "intl/latest.json", {"records": [
        {"cc": "JP", "risk_radar": radar("risk-off", market="kr")}
    ]})
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={"jp": SESSION})
    assert result["warning_projection"]["coverage"]["current"] == 0
    assert "source_market_mismatch" in result["warning_projection"]["rows"][0]["reason_codes"]


def test_failed_next_build_retains_previous_severe_without_advancing_legacy_alert(tmp_path):
    write(tmp_path, "china_regime/latest.json", {"risk_radar": radar("risk-off", 99, "cn")})
    first = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                             expected_sessions={"cn": SESSION})
    (tmp_path / "china_regime/latest.json").unlink()
    second = adapter().augment_banner_payload(first, data_root=tmp_path,
                                              expected_sessions={"cn": SESSION})
    assert second["alert"] is None
    assert second["warning_projection"]["rows"][0]["status"] == "unverified"
    assert second["warning_projection"]["last_known_severe_markets"] == ["cn"]


def test_same_day_file_with_old_radar_is_not_refreshed_by_wrapper_date(tmp_path):
    write(tmp_path, "regime/latest.json", {"asof": SESSION, "risk_radar": radar(session="2026-09-24")})
    result = adapter().augment_banner_payload(legacy(), data_root=tmp_path,
                                              expected_sessions={"us": SESSION})
    assert result["warning_projection"]["coverage"]["current"] == 0


def test_legacy_extreme_alert_payload_is_not_reinterpreted(tmp_path):
    payload = legacy()
    payload["alert"] = {"id": "rr-old-id", "odds_pct": 41, "score": 92}
    frozen = deepcopy(payload)
    result = adapter().augment_banner_payload(payload, data_root=tmp_path,
                                              expected_sessions={"us": SESSION})
    assert result["alert"] == frozen["alert"]
    assert result["schema"] == "rr_banner.v1"
    assert payload == frozen


def test_wrong_target_artifact_and_missing_manifest_are_refused(tmp_path):
    with pytest.raises(ValueError):
        adapter().augment_banner_payload({"schema": "wh_banner.v1"}, data_root=tmp_path,
                                          expected_sessions={"us": SESSION})
    with pytest.raises(ValueError):
        adapter().augment_banner_payload(legacy(), data_root=tmp_path, expected_sessions={})
