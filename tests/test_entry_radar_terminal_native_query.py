"""Synthetic R27 output-version proof; no source admission or market outcomes."""
from __future__ import annotations

import copy
import uuid
from unittest.mock import patch

import pytest

from engine.entry_radar.replay import terminal_minute_observations as bridge
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, build_input_panel
from tests import test_entry_radar_terminal_minute_observations as fixture

OUTPUT_V2 = "mastermind.entry_radar.terminal_minute_observations.v2"
CUTOFF = "2026-10-06T14:16:00Z"
QUERY_KEYS = {"decode_schema", "source_vendor", "source_symbol"}
_DEFAULT = object()

# Measured before R27 on 8a9dd7b52bf67d8a9341c7511dc41a882cac2f1e.
# Decoder SHA256 ecb1c8f4fb58a01467c078b28d8f5a933f15c17bb538b9f0a91ba8ea441f15db.
# The fixture read ID and synthetic clock are fixed, so each digest covers the
# complete old output and every existing row seal without another source module.
V1_OUTPUT_DIGESTS = {
    "v1": "d1d1fdef3f752a87736ec596144ba2686c5e6c46a15e5401579c4c939dd26689",
    "v2": "27221670764ef1f4efa579f2c3d5e4279395664f408128181db42ad7b1b21e08",
    "v3_chart": "1e29603795cbd8b075f0774025932b0e78da221ed1f85c9a63baa1ba68a62369",
    "v3_research": "fc96ac59868a6b536434d862aed005f4054272f82b6ad6f55e88957e1d761d03",
}


def capture(kind):
    if kind == "v1":
        return fixture.append_capture(fixture.envelope())
    if kind == "v2":
        return fixture.v2_capture()
    if kind == "v3_chart":
        return fixture.v3_capture(role="chart_adjusted", state="TRUE")
    assert kind == "v3_research"
    return fixture.v3_capture()


def snapshot_at(path, captured, instant=CUTOFF):
    fixture.atomic_fixture(path, captured)
    with patch.object(bridge.uuid, "uuid4",
                      return_value=uuid.UUID("0123456789abcdef0123456789abcdef")):
        return fixture.read_at(path, instant)


def decode(snapshot, *, receipts=None, cutoff=CUTOFF, stream_metadata=_DEFAULT,
           symbol=fixture.SYMBOL, **kwargs):
    return bridge.decode_terminal_minute_observations(
        snapshot, [snapshot.receipt] if receipts is None else receipts,
        reader_identity=fixture.READER, symbol=symbol, stream="stock",
        stream_metadata=fixture.metadata() if stream_metadata is _DEFAULT else stream_metadata,
        cutoff=cutoff, **kwargs,
    )


@pytest.mark.parametrize("kind", V1_OUTPUT_DIGESTS)
def test_default_v1_exact_prechange_output_and_explicit_v1_agree(tmp_path, kind):
    snapshot = snapshot_at(tmp_path / "capture.json", capture(kind))
    default = decode(snapshot)
    assert fixture.digest(default) == V1_OUTPUT_DIGESTS[kind]
    assert len(default["minutes"]) == 30
    explicit = decode(snapshot, output_schema=bridge.DECODE_SCHEMA)
    assert fixture.canonical(explicit) == fixture.canonical(default)
    assert all(not QUERY_KEYS.intersection(row["source_observation"])
               for row in default["minutes"])


@pytest.mark.parametrize("kind", V1_OUTPUT_DIGESTS)
def test_v2_projects_validated_payload_and_preserves_every_old_field(tmp_path, kind):
    retained = capture(kind)
    snapshot = snapshot_at(tmp_path / "capture.json", retained)
    impostor = fixture.metadata("SEC:DO-NOT-SPLIT-THIS")
    impostor.update(source_vendor="thetadata", source_symbol="SPY",
                    decode_schema="caller", source_query_attested=True)
    original = decode(snapshot, stream_metadata=impostor)
    result = decode(snapshot, stream_metadata=impostor, output_schema=OUTPUT_V2)
    assert bridge.DECODE_SCHEMA_V2 == OUTPUT_V2
    assert result["schema"] == OUTPUT_V2
    assert len(result["minutes"]) == 30
    restored = copy.deepcopy(result)
    restored["schema"] = bridge.DECODE_SCHEMA
    for new, old, stripped in zip(result["minutes"], original["minutes"], restored["minutes"]):
        source = new["source_observation"]
        assert {key: source[key] for key in QUERY_KEYS} == {
            "decode_schema": OUTPUT_V2, "source_vendor": "polygon",
            "source_symbol": retained["captures"][0]["payload"]["symbol"],
        }
        assert new["receipt_sha256"] == fixture.digest(
            {key: value for key, value in new.items() if key != "receipt_sha256"})
        assert new["receipt_sha256"] != old["receipt_sha256"]
        for key in QUERY_KEYS:
            del stripped["source_observation"][key]
        fixture.reseal_receipt(stripped)
        assert stripped == old
        forged = copy.deepcopy(new)
        forged["source_observation"]["source_symbol"] = "SPY"
        assert fixture.digest({key: value for key, value in forged.items()
                               if key != "receipt_sha256"}) != new["receipt_sha256"]
    assert restored == original
    assert not any(result["authority"].values())
    assert result["scientific_claims"] == {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"}


@pytest.mark.parametrize("symbol", ("MU", "SPY", "QQQ", "SMH"))
def test_query_is_exact_source_symbol_without_inferring_security_identity(tmp_path, symbol):
    retained = capture("v3_research")
    retained["captures"][0]["payload"]["symbol"] = symbol
    fixture.reseal(retained)
    snapshot = snapshot_at(tmp_path / "capture.json", retained)
    result = decode(snapshot, symbol=symbol, stream_metadata=None, output_schema=OUTPUT_V2)
    assert {row["source_observation"]["source_symbol"] for row in result["minutes"]} == {symbol}
    assert {row["source_observation"]["source_vendor"] for row in result["minutes"]} == {"polygon"}
    assert all(row["security_id"] is None and row["basis_id"] is None
               and row["basis_refusals"] == ["TERMINAL_BASIS_UNPROVEN"]
               for row in result["minutes"])
    assert "stable_security_identity" in result["unproven_owner_requirements"]


@pytest.mark.parametrize("mode", (None, True, 0, "", [], {}, b"v2", "future-v3"))
def test_malformed_or_unknown_output_version_has_typed_refusal(tmp_path, mode):
    snapshot = snapshot_at(tmp_path / "capture.json", capture("v1"))
    with pytest.raises(InputContractError, match="output schema"):
        decode(snapshot, output_schema=mode)


@pytest.mark.parametrize("field,value", (("source", "thetadata"), ("symbol", "SPY"),
                                         ("source", {}), ("symbol", None)))
def test_metadata_cannot_replace_a_mismatched_visible_payload_query(tmp_path, field, value):
    retained = capture("v3_research")
    retained["captures"][0]["payload"][field] = value
    fixture.reseal(retained)
    snapshot = snapshot_at(tmp_path / "capture.json", retained)
    with pytest.raises(InputContractError, match="symbol/source/timeframe mismatch"):
        decode(snapshot, output_schema=OUTPUT_V2,
               stream_metadata={**fixture.metadata(), "source_vendor": "polygon",
                                "source_symbol": fixture.SYMBOL, "source_query_attested": True})


@pytest.mark.parametrize("field,value", (("source", "invalid-provider"), ("symbol", "QQQ")))
def test_future_or_unenrolled_query_semantics_wait_for_actual_owner_visibility(tmp_path, field, value):
    path = tmp_path / "capture.json"
    retained = capture("v3_research")
    first = snapshot_at(path, retained)
    before = decode(first, output_schema=OUTPUT_V2)
    future = fixture.v3_capture(retained, source_at="2026-10-06T14:17:00Z")
    future["captures"][-1]["payload"][field] = value
    fixture.reseal(future)
    # Use a distinct actual synthetic reader ID for the later prefix.
    fixture.atomic_fixture(path, future)
    later = fixture.read_at(path, "2026-10-06T14:18:00Z")
    earlier = decode(later, receipts=[first.receipt, later.receipt], output_schema=OUTPUT_V2)
    unenrolled = decode(later, receipts=[first.receipt], cutoff="2026-10-06T14:18:00Z",
                        output_schema=OUTPUT_V2)
    assert earlier["minutes"] == unenrolled["minutes"] == before["minutes"]
    assert earlier["diagnostics"]["captures_without_visible_owner_receipt"] == 1
    assert unenrolled["diagnostics"]["captures_without_visible_owner_receipt"] == 1
    with pytest.raises(InputContractError, match="symbol/source/timeframe mismatch"):
        decode(later, receipts=[first.receipt, later.receipt],
               cutoff="2026-10-06T14:18:00Z", output_schema=OUTPUT_V2)


@pytest.mark.parametrize("outcome", ("partial", "failed", "empty", "suppressed"))
def test_no_retained_observation_cannot_manufacture_a_source_query(tmp_path, outcome):
    retained = fixture.v3_capture(
        rows=[] if outcome in ("empty", "suppressed") else None,
        status=outcome if outcome in ("partial", "failed") else "complete")
    if outcome == "suppressed":
        payload = retained["captures"][-1]["payload"]
        payload["counts"].update(rows_received=30, finalized_rows=30, unchanged_suppressed=30)
        payload["pages"][0].update(rows_received=30, finalized_rows=30)
        fixture.reseal(retained)
    snapshot = snapshot_at(tmp_path / "capture.json", retained)
    result = decode(snapshot, output_schema=OUTPUT_V2)
    assert result["schema"] == OUTPUT_V2
    assert result["status"] == "UNAVAILABLE" and result["minutes"] == []
    assert "source_vendor" not in fixture.canonical(result)
    assert "source_symbol" not in fixture.canonical(result)


def test_query_availability_uses_original_read_ns_and_explicit_enrollment(tmp_path):
    instant = fixture.ns(CUTOFF) + 1
    snapshot = snapshot_at(tmp_path / "capture.json", capture("v3_research"), instant)
    before = decode(snapshot, output_schema=OUTPUT_V2)
    unenrolled = decode(snapshot, receipts=[], cutoff="2026-10-06T14:16:00.000001Z",
                        output_schema=OUTPUT_V2)
    assert before["minutes"] == unenrolled["minutes"] == []
    after = decode(snapshot, cutoff="2026-10-06T14:16:00.000001Z", output_schema=OUTPUT_V2)
    assert len(after["minutes"]) == 30
    assert {row["known_at"] for row in after["minutes"]} == {"2026-10-06T14:16:00.000001Z"}
    assert {row["source_observation"]["owner_read_completed_at_utc_ns"]
            for row in after["minutes"]} == {instant}
    assert {row["source_observation"]["owner_read_receipt_sha256"]
            for row in after["minutes"]} == {snapshot.receipt["receipt_sha256"]}


def test_format_upgrade_keeps_revision_identity_and_mixed_formats_conflict(tmp_path):
    snapshot = snapshot_at(tmp_path / "capture.json", capture("v3_research"))
    legacy = decode(snapshot)["minutes"]
    versioned = decode(snapshot, output_schema=OUTPUT_V2)["minutes"]
    assert [row["revision_id"] for row in versioned] == [row["revision_id"] for row in legacy]
    assert [row["known_at"] for row in versioned] == [row["known_at"] for row in legacy]
    panel = build_input_panel(fixture.bundle([*legacy, *versioned]))
    bar = panel["frames"][0]["bars"]["stock"]["30"]
    assert "CONFLICTING_MINUTE_REVISION" in bar["refusals"]
    assert bar["availability"] == "unavailable" and bar["ohlcv"] is None


def test_v2_query_cannot_remove_basis_refusal_or_selected_population(tmp_path):
    snapshot = snapshot_at(tmp_path / "capture.json", capture("v3_research"))
    rows = decode(snapshot, output_schema=OUTPUT_V2)["minutes"]
    for row in rows:
        row["basis_id"] = "synthetic-basis"
        row.pop("basis_refusals")
        fixture.reseal_receipt(row)
    panel = build_input_panel(fixture.bundle(
        rows, cutoffs=("2026-10-06T14:15:00Z", CUTOFF)))
    assert panel["retained_count"] == panel["population_count"] == 2
    for frame in panel["frames"]:
        assert frame["bars"]["stock"]["30"]["ohlcv"] is None
    assert "TERMINAL_BASIS_UNPROVEN" in panel["frames"][1]["bars"]["stock"]["30"]["refusals"]
    assert not any(panel["authority"].values())
