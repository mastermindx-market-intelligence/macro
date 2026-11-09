"""CFTC identity, cohort and source-vintage invariants (offline)."""
import copy
import gzip
import json

import pandas as pd
import pytest

from lib.cot_contracts import MARKETS, source_fields, store_name
from lib.cot_data import CotDataError, normalize_frame, normalize_row, preserve_source

NOW = "2026-10-09T20:00:00Z"
LATER = "2026-10-12T20:00:00Z"


def row():
    return {
        "report_date_as_yyyy_mm_dd": "2026-10-06T00:00:00.000",
        "market_and_exchange_names": "NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE",
        "cftc_contract_market_code": "209742", "open_interest_all": "100",
        "comm_positions_long_all": "40", "comm_positions_short_all": "70",
        "noncomm_positions_long_all": "30", "noncomm_positions_short_all": "10",
        "noncomm_postions_spread_all": "10",
        "nonrept_positions_long_all": "20", "nonrept_positions_short_all": "10",
    }


def test_roster_exactly_21_unique_specific_contracts():
    assert len(MARKETS) == len({m.code for m in MARKETS}) == len({m.key for m in MARKETS}) == 21
    assert store_name("020601") == "cot_legacy_020601"
    for code in ["020604", "177742", "239747", "124608", "67651"]:
        with pytest.raises(ValueError):
            store_name(code)


def test_fields_retain_upstream_spelling():
    assert "noncomm_postions_spread_all" in source_fields("legacy")
    assert "swap__positions_short_all" in source_fields("disaggregated")
    assert "asset_mgr_positions_long" in source_fields("tff")


def test_complete_cohorts_and_legacy_compatibility():
    out = normalize_row(row(), "legacy", observed_at=NOW)
    assert out["net_spec"] == 20
    assert out["net_spec_pct_oi"] == 20.0
    assert out["commercial_net"] == -30
    assert out["nonreportable_net"] == 10
    assert out["contract_basis"] == "futures_only"
    assert out["actual_release_at"] is None
    assert out["original_vintage_certified"] is False
    assert len(out["source_record_sha256"]) == 64


@pytest.mark.parametrize("value", [None, True, -1, "NaN", "inf", 1.5, "junk", [], {}])
def test_missing_nonfinite_fractional_and_negative_counts_rejected(value):
    r = row(); r["comm_positions_long_all"] = value
    with pytest.raises(CotDataError):
        normalize_row(r, "legacy", observed_at=NOW)


@pytest.mark.parametrize("field,value", [
    ("open_interest_all", "0"), ("open_interest_all", "101"),
    ("comm_positions_long_all", "101"), ("cftc_contract_market_code", "177742"),
    ("market_and_exchange_names", ""), ("report_date_as_yyyy_mm_dd", "2026-10-13"),
    ("report_date_as_yyyy_mm_dd", "2026-10-06T12:00:00"),
])
def test_malformed_identity_and_oi_reconciliation(field, value):
    r = row(); r[field] = value
    with pytest.raises(CotDataError):
        normalize_row(r, "legacy", observed_at=NOW)


def test_correction_and_identical_refresh_clocks():
    first = normalize_frame([row()], "legacy", code="209742", observed_at=NOW)
    same = normalize_frame([row()], "legacy", code="209742", observed_at=LATER, previous=first)
    assert same.iloc[0]["version_observed_at"] == pd.Timestamp(NOW).isoformat()
    assert same.iloc[0]["revised_at"] is None
    changed = row(); changed["comm_positions_long_all"] = "39"; changed["noncomm_positions_long_all"] = "31"
    second = normalize_frame([changed], "legacy", code="209742", observed_at=LATER, previous=first)
    assert second.iloc[0]["source_record_sha256"] != first.iloc[0]["source_record_sha256"]
    assert second.iloc[0]["first_observed_at"] == pd.Timestamp(NOW).isoformat()
    assert second.iloc[0]["version_observed_at"] == second.iloc[0]["revised_at"] == pd.Timestamp(LATER).isoformat()


def test_duplicate_and_cross_contract_history_rejected():
    with pytest.raises(CotDataError):
        normalize_frame([row(), row()], "legacy", code="209742", observed_at=NOW)
    with pytest.raises(CotDataError):
        normalize_frame([row()], "legacy", code="13874A", observed_at=NOW)


def test_immutable_response_keeps_first_observation_and_detects_corruption(tmp_path):
    digest = preserve_source([row()], "legacy", observed_at=NOW, data_root=tmp_path)
    again = preserve_source([row()], "legacy", observed_at=LATER, data_root=tmp_path)
    assert digest == again
    p = tmp_path / "cot" / "raw" / "legacy" / f"{digest}.json.gz"
    before = p.read_bytes()
    obj = json.loads(gzip.decompress(before))
    assert obj["first_observed_at"] == pd.Timestamp(NOW).isoformat()
    obj["records"][0]["open_interest_all"] = "999"
    p.write_bytes(gzip.compress(json.dumps(obj).encode()))
    with pytest.raises(CotDataError):
        preserve_source([row()], "legacy", observed_at=LATER, data_root=tmp_path)


def test_family_views_cannot_be_conflated():
    with pytest.raises(CotDataError):
        normalize_row(row(), "disaggregated", observed_at=NOW)
    with pytest.raises(CotDataError):
        normalize_row(row(), "combined", observed_at=NOW)
