"""ECB admission: actual stored observation, synthetic publication decisions."""

import copy
import json
import math

import numpy as np
import pandas as pd
import pytest

from engine import intl_inputs


# Copied from the existing official store on 2026-10-07, not a live ECB query.
IDENTITY = {
    "artifact_sha256": "d5ce385fa74960c5449f4d06ec807f889e6833053b02a2d90fda5cb5f8f0bce8",
    "provenance_sha256": "9b12934a0d5d6f9da843a01066b6701e5fc238ac2567fc5de22328636e52af2f",
    "column": "ez_depo_rate",
}
PROVENANCE = {
    "last_observation": "2026-10-06", "provider": "ecb",
    "release_period_semantics": "Daily effective policy-rate observation",
    "requested_at": "2026-10-06T03:10:11.694643+00:00",
    "source_id": "D.U2.EUR.4F.KR.DFR.LEV", "source_updated": "2026-10-06",
    "source_url": "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=1999-01-01",
    "status": "official", "unit": "PCPA",
}


def inputs(value=2.5):
    series = pd.Series([2.5, 2.5, value], index=pd.date_range("2026-10-04", periods=3), name="ez_depo_rate")
    binding = {
        "market_id": "EZ", "field": "policy_rate", "instrument_id": "deposit_facility",
        "source_id": PROVENANCE["source_id"],
        "artifact_sha256": IDENTITY["artifact_sha256"],
        "provenance_sha256": IDENTITY["provenance_sha256"],
        "observation_at": "2026-10-06", "value": value, "unit": "percent",
    }
    # These are test decisions, not receipts from the production publication flow.
    return {
        "series": series, "provenance": copy.deepcopy(PROVENANCE),
        "materialized_identity": dict(IDENTITY), "evaluated_at": "2026-10-07T10:00:00Z",
        "publication_decision": {
            "owner_ref": "scripts/build_intl.py",
            "policy_ref": "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-ecb-deposit-level-admission",
            "decision_ref": "fixture:ecb-publication-1", "metadata": "allowed",
            "value_permission": "allowed", "binding": binding,
        },
    }


def admit(packet):
    return intl_inputs.admit_ecb_deposit_field(**packet)


def test_stored_positive_preserves_value_identity_and_unknown_clocks():
    packet = inputs()
    before = copy.deepcopy(packet)
    result = admit(packet)
    assert result["quality"] == "qualified" and result["reason"] is None
    assert result["value"] == 2.5 and type(result["value"]) is float
    assert result["unit"] == "percent" and result["observation_at"] == "2026-10-06"
    assert result["instrument"] == {"kind": "official_policy", "id": "deposit_facility", "market_id": "EZ"}
    assert result["period"] is None and result["calculation_at"] is None
    assert IDENTITY["artifact_sha256"] in result["source_reference"]
    json.dumps(result, allow_nan=False)
    pd.testing.assert_series_equal(packet.pop("series"), before.pop("series"))
    assert packet == before
    result["instrument"]["id"] = "changed"
    assert admit(inputs())["instrument"]["id"] == "deposit_facility"


@pytest.mark.parametrize("value", [0.0, -0.0, -2.5, 3])
def test_numeric_identity(value):
    packet = inputs(value)
    packet["series"] = packet["series"].astype(object)
    packet["series"].iloc[-1] = value
    result = admit(packet)
    assert result["quality"] == "qualified"
    assert type(result["value"]) is type(value) and result["value"] == value
    if type(value) is float:
        assert math.copysign(1, result["value"]) == math.copysign(1, value)


@pytest.mark.parametrize("clock,quality", [
    ("2026-10-18T23:59:59Z", "qualified"), ("2026-10-19T00:00:00Z", "stale"),
    ("2026-10-19T00:30:00+01:00", "qualified"),
    ("2026-10-05T23:59:59Z", "failed"),
    ("2026-10-07T10:00:00", "failed"), ("2026-13-07T10:00:00Z", "failed"),
    ("2026-10-07T10:00:00+00:99", "failed"), (None, "failed"),
])
def test_supplied_evaluation_and_existing_freshness(clock, quality):
    packet = inputs(); packet["evaluated_at"] = clock
    result = admit(packet)
    assert result["quality"] == quality
    if quality == "stale":
        assert result["value"] == 2.5 and result["reason"] == "source_stale"


def test_threshold_is_owned_by_existing_cb_policy(monkeypatch):
    from engine import cb_desk
    monkeypatch.setitem(cb_desk._STALE_DAYS, "daily", 0)
    assert admit(inputs())["quality"] == "stale"


@pytest.mark.parametrize("section,key,bad", [
    ("provenance", "provider", "fred"), ("provenance", "unit", "index"),
    ("provenance", "status", "fallback"), ("provenance", "last_observation", "2026-10-05"),
    ("provenance", "source_id", "ECBDFR"), ("provenance", "source_url", "https://private.example/secret"),
    ("provenance", "source_updated", "2026-10-07"),
    ("materialized_identity", "artifact_sha256", "wrong"),
    ("materialized_identity", "provenance_sha256", "A" * 64),
    ("materialized_identity", "column", "ez_short"),
])
def test_invalid_source_never_borrows_permission(section, key, bad):
    packet = inputs(); packet[section][key] = bad
    result = admit(packet)
    assert result["quality"] == "failed" and result["value"] is None
    assert "secret" not in json.dumps(result) and result["source_reference"] is None


@pytest.mark.parametrize("key,bad", [
    ("market_id", "XM"), ("field", "policy_proxy"), ("instrument_id", "DFF"),
    ("source_id", "ECBDFR"), ("artifact_sha256", "a" * 64),
    ("provenance_sha256", "b" * 64), ("observation_at", "2026-10-05"),
    ("value", 2.6), ("value", True), ("value", "2.5"), ("unit", "bp"),
])
def test_binding_mismatch_withholds(key, bad):
    packet = inputs(); packet["publication_decision"]["binding"][key] = bad
    result = admit(packet)
    assert result["quality"] == "unknown" and result["reason"] == "disclosure_unknown"
    assert result["source_reference"] is None and result["value"] is None


@pytest.mark.parametrize("metadata", ["denied", "unknown"])
def test_metadata_redaction(metadata):
    packet = inputs(); packet["publication_decision"]["metadata"] = metadata
    result = admit(packet)
    for key in ["value", "unit", "instrument", "period", "observation_at", "calculation_at", "source_reference", "evidence_key"]:
        assert result[key] is None
    public = json.dumps(result)
    assert "2.5" not in public and "2026" not in public and "ecb" not in public.lower()


@pytest.mark.parametrize("permission", ["denied", "unknown"])
def test_value_denial_keeps_only_bound_metadata(permission):
    packet = inputs(); packet["publication_decision"]["value_permission"] = permission
    result = admit(packet)
    assert result["value"] is None and result["observation_at"] == "2026-10-06"
    assert result["source_reference"] is not None


@pytest.mark.parametrize("value", [True, "2.5", float("nan"), float("inf"), None, pd.NA])
def test_bad_endpoint_never_falls_back(value):
    packet = inputs(); packet["series"] = packet["series"].astype(object)
    packet["series"].iloc[-1] = value
    assert admit(packet)["quality"] == "failed"


@pytest.mark.parametrize("case", ["duplicate", "reversed", "nat", "wrong_name", "intraday", "empty", "none"])
def test_bad_geometry_or_missing_artifact(case):
    packet = inputs(); series = packet["series"]
    if case == "duplicate": series.index = pd.DatetimeIndex(["2026-10-04", "2026-10-06", "2026-10-06"])
    if case == "reversed": series = series.iloc[::-1]
    if case == "nat": series.index = pd.DatetimeIndex(["2026-10-04", "2026-10-05", pd.NaT])
    if case == "wrong_name": series.name = "ez_short"
    if case == "intraday": series.index = series.index + pd.Timedelta(hours=1)
    if case == "empty": series = series.iloc[:0]
    if case == "none": series = None
    packet["series"] = series
    result = admit(packet)
    assert result["quality"] == ("missing" if case in {"empty", "none"} else "failed")
    assert result["value"] is None


def test_missing_and_malformed_decisions():
    for decision in [None, {}, {"metadata": "allowed"}, dict(inputs()["publication_decision"], secret="private")]:
        packet = inputs(); packet["publication_decision"] = decision
        assert admit(packet)["quality"] == "unknown"
    for field in ["owner_ref", "policy_ref"]:
        packet = inputs(); packet["publication_decision"][field] = "untrusted"
        assert admit(packet)["quality"] == "unknown"


def test_no_custom_container_or_numeric_coercion():
    class Custom(dict):
        def items(self):
            raise AssertionError("custom accessor must not run")
    packet = inputs(); packet["publication_decision"] = Custom(packet["publication_decision"])
    assert admit(packet)["quality"] == "unknown"
    packet = inputs(); packet["provenance"] = Custom(packet["provenance"])
    assert admit(packet)["quality"] == "failed"


def test_no_source_or_clock_io(monkeypatch):
    from engine import cb_desk
    import builtins
    import socket
    packet = inputs()
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected I/O")
    monkeypatch.setattr(intl_inputs.store, "read", forbidden)
    monkeypatch.setattr(intl_inputs.config, "load", forbidden)
    monkeypatch.setattr(cb_desk, "snapshot", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    assert admit(packet)["quality"] == "qualified"


@pytest.mark.parametrize("key,quality", [("publication_decision", "unknown"), ("provenance", "failed")])
def test_cyclic_container_is_withheld(key, quality):
    packet = inputs()
    packet[key]["cycle"] = packet[key]
    result = admit(packet)
    assert result["quality"] == quality and result["value"] is None
    json.dumps(result, allow_nan=False)
