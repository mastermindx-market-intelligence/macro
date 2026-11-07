"""Real reference capture -> configured association -> native transport/page.

All identities and files here are controlled fixtures, not provider or live
classification evidence. Existing immutable breadth encoders supply the member
population; a complete five-file legacy reference supplies the native readers.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lib import sector_input_capture as capture
from engine.sector_native_view import _classification_context, SectorViewUnavailable, project_sector_view
from tests.test_sector_captured_input_assembly import (
    captured_inputs, sources, original, dependency, _aux, CAPTURED)


def write_classification_reference(repo, symbols=("T0000", "T0001", "T0002")):
    from engine.entry_radar.replay.identity_observation_snapshot import REFERENCE_ARTIFACTS
    root = repo / "data" / "reference"
    root.mkdir(parents=True, exist_ok=True)
    aliases = [{"vendor": "membership", "vendor_symbol": t, "security_id": "SEC:US-XNAS-" + t}
               for t in symbols]
    master = [{"security_id": "SEC:US-XNAS-" + t, "issuer_id": "ISS:US-XNAS-" + t,
               "issuer_state": "RESOLVED", "listing_key": "US-XNAS-" + t,
               "security_state": None, "superseded_by": None} for t in symbols]
    for name in REFERENCE_ARTIFACTS:
        rows = aliases if name == "vendor_aliases.parquet" else master if name == "security_master.parquet" else []
        table = pa.Table.from_pylist(rows) if rows else pa.table({"empty": pa.array([], type=pa.string())})
        pq.write_table(table, root / name)
    (root / "_receipt.json").write_text('{"fixture":"complete legacy reference; no native receipt"}')
    return root


def classification_case(captured_inputs, tmp_path, *, roster=None):
    args, _ = captured_inputs
    cfg = args["auxiliary"].document("config")
    cfg["themes"] = {"memory_storage": {"name": "Memory, HBM & Storage",
        "tickers": roster if roster is not None else ["T0000", "T0001", "T0002", "T9999", "T8888"]}}
    root = write_classification_reference(tmp_path)
    packet = capture.read_sector_classification_context(repository_root=tmp_path,
        config_document=cfg, breadth=args["prices"].breadth,
        lookup_on=args["evaluation_date"], clock=lambda: CAPTURED)
    return packet, dict(args, auxiliary=_aux(config=cfg), classification_context=packet), root


def test_complete_reference_capture_keeps_exact_roster_sources_and_unknown_clocks(captured_inputs, tmp_path):
    packet, args, root = classification_case(captured_inputs, tmp_path)
    assert packet["status"] == "partial"
    assert packet["membership_roster"] == ["T0000", "T0001", "T0002"]
    assert packet["missing_roster"] == ["T9999", "T8888"]
    assert _classification_context(packet) == packet
    association = packet["association"]
    assert association["coverage"] == {"requested_n": 3, "associated_n": 3,
        "unavailable_n": 0, "conflict_n": 0, "duplicate_requests_n": 0}
    assert all(r["sector"] == "Industrials" and r["sector_etf_proxy"] == "XLI"
               and r["etf_security_id"] is None for r in association["associations"])
    assert all(v is False for v in association["limitations"].values())
    assert all(v is False for v in association["authority"].values())
    for source in association["source_attribution"]:
        assert source["captured_at"] == CAPTURED.isoformat()
        assert source["source_available_at"] is None and source["source_effective_on"] is None
        assert source["read_receipt_sha256"] is None
    assert packet["capture"]["producer_receipt_sha256"] == hashlib.sha256((root / "_receipt.json").read_bytes()).hexdigest()
    actual = capture.assemble_sector_inputs(**args)
    assert actual.context.classification_context == packet
    actual.context.classification_context["configured_roster"].clear()
    assert len(packet["configured_roster"]) == 5


@pytest.mark.parametrize("case", ["blank_name_conflict", "missing_sector", "blank_sector", "valid_conflict"])
def test_native_encoded_incomplete_or_conflicting_population_cannot_assert_a_positive_sector(sources, tmp_path, monkeypatch, case):
    from lib import breadth_member_generation_contract as contract
    from engine.entry_radar.replay import identity_observation_snapshot as reference_owner
    from tests.test_breadth_member_generation_contract import _owner, PUBLISHED, REVISION
    from tests.test_sector_central_measured_panel import _native_wire_fixture, _run_native
    values = dict(sources)
    groups = dict(values["groups"])
    members = groups["midcap_breadth"].members.copy(deep=True)
    chosen = members["symbol"] == "T0000"
    members.loc[chosen, "sector"] = None if case == "missing_sector" else "" if case == "blank_sector" else "Financials"
    if case == "blank_name_conflict": members.loc[chosen, "name"] = ""
    groups["midcap_breadth"] = replace(groups["midcap_breadth"], members=members)
    values["groups"] = groups
    encoded = contract.encode_breadth_member_acquisitions(**values)
    owner = _owner(tmp_path / "generation", PUBLISHED)
    result = owner.publish_breadth_member_inputs(encoded, generation_id="classification-countercase",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    breadth = contract.read_verified_breadth_member_inputs(
        generations_root=owner.state_dir / "generations", now=CAPTURED, yahoo=values["yahoo"])
    observed_sector = breadth.inputs.constituents["midcap_breadth"].iloc[0]["sector"]
    if case == "missing_sector":
        assert pd.isna(observed_sector) and pd.isna(members.iloc[0]["sector"])
    else:
        assert observed_sector == members.iloc[0]["sector"]
    repo = tmp_path / "repo"
    write_classification_reference(repo)
    if case != "valid_conflict":
        def forbidden(*args, **kwargs): raise AssertionError("incomplete source rows attempted reference I/O")
        monkeypatch.setattr(reference_owner, "read_reference_generation", forbidden)
    packet = capture.read_sector_classification_context(repository_root=repo,
        config_document={"themes": {"memory_storage": {"tickers": ["T0000"]}}},
        breadth=breadth, lookup_on=CAPTURED.date(), clock=lambda: CAPTURED)
    assert _classification_context(packet) == packet
    if case == "valid_conflict":
        assert packet["status"] == "conflict"
        row = packet["association"]["associations"][0]
        assert row["status"] == "conflict" and row["sector"] is None and row["sector_etf_proxy"] is None
        assert {r["native_sector"] for r in row["source_observations"]} == {"Industrials", "Financials"}
    else:
        assert packet["status"] == "unavailable" and packet["association"] is None
        assert packet["capture"]["status"] == "not_attempted"
        assert packet["capture"]["reason"] == "captured_classification_rows_incomplete"
        assert packet["unclassified_rows_n"] == 1 and packet["membership_roster"] == ["T0000"]
    wire = _native_wire_fixture(classification=packet, published_at=(CAPTURED + timedelta(seconds=1)).isoformat())
    out = _run_native(wire=wire)
    assert out["nativeState"] == "ready"
    assert "Sector ETF proxy:" not in out["classification"]
    assert "Conflicting source classifications" in out["classification"] if case == "valid_conflict" else "Incomplete population rows; classifications withheld" in out["classification"]


@pytest.mark.parametrize("defect,reason", [
    ("absent", "reference_capture_unavailable"),
    ("native_layout", "native_reference_requires_native_reader"),
    ("native_receipt", "native_reference_requires_native_reader"),
    ("oversize", "reference_resource_bound"),
    ("writer", "reference_writer_busy"),
    ("malformed_alias", "reference_capture_unavailable"),
])
def test_optional_reference_failure_has_no_fallback_or_prior_positive(captured_inputs, tmp_path, defect, reason):
    import fcntl
    import os
    packet, args, root = classification_case(captured_inputs, tmp_path)
    assert packet["association"] is not None
    fd = None
    if defect == "absent": (root / "security_master.parquet").unlink()
    elif defect == "native_layout": (root / ".identity").mkdir()
    elif defect == "native_receipt": (root / "_receipt.json").write_text('{"publication":{}}')
    elif defect == "oversize": (root / "security_master.parquet").write_bytes(b"x" * (4 * 1024**2 + 1))
    elif defect == "malformed_alias": pq.write_table(pa.table({"bad": ["value"]}), root / "vendor_aliases.parquet")
    elif defect == "writer":
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        failed = capture.read_sector_classification_context(repository_root=tmp_path,
            config_document=args["auxiliary"].document("config"), breadth=args["prices"].breadth,
            lookup_on=args["evaluation_date"], clock=lambda: CAPTURED)
    finally:
        if fd is not None: os.close(fd)
    assert failed["association"] is None and failed["status"] == "unavailable"
    assert failed["capture"]["reason"] == reason
    assert _classification_context(failed) == failed
    assert capture.assemble_sector_inputs(**dict(args, classification_context=failed)).context.classification_context == failed


@pytest.mark.parametrize("roster", [[], ["T0000"] * 2, ["T0000"] * 6, [" T0000"], ["ABSENT"]])
def test_no_eligible_labels_does_not_open_reference(captured_inputs, tmp_path, monkeypatch, roster):
    from engine.entry_radar.replay import identity_observation_snapshot as owner
    def forbidden(*args, **kwargs): raise AssertionError("ineligible roster attempted reference I/O")
    monkeypatch.setattr(owner, "read_reference_generation", forbidden)
    packet, _, _ = classification_case(captured_inputs, tmp_path, roster=roster)
    assert packet["capture"]["status"] == "not_attempted"
    assert _classification_context(packet) == packet


@pytest.mark.parametrize("defect", ["roster", "generation", "hash", "lookup", "clock", "observation", "omission", "unclassified"])
def test_assembly_binds_classification_to_the_actual_config_and_price_capture(captured_inputs, tmp_path, defect):
    packet, args, _ = classification_case(captured_inputs, tmp_path)
    if defect == "roster":
        cfg = args["auxiliary"].document("config")
        cfg["themes"]["memory_storage"]["tickers"].reverse()
        args["auxiliary"] = _aux(config=cfg)
    elif defect in ("generation", "hash"):
        for source in packet["association"]["source_attribution"]:
            if source["kind"] == "constituents":
                source["generation_id" if defect == "generation" else "raw_sha256"] = "other-generation" if defect == "generation" else "a" * 64
    elif defect == "lookup":
        packet["association"]["lookup_on"] = (args["evaluation_date"] - timedelta(days=1)).isoformat()
    elif defect == "observation":
        packet["association"]["associations"][0]["source_observations"][0]["native_name"] = "Substituted company"
    elif defect == "omission":
        row = packet["association"]["associations"][0]
        row["source_observations"] = []
        row.update(status="unavailable", sector=None, sector_etf_proxy=None, reason_codes=["NO_CAPTURED_CLASSIFICATION"])
        packet["association"]["status"] = "partial"
        packet["association"]["coverage"].update(associated_n=2, unavailable_n=1)
    elif defect == "unclassified":
        packet["unclassified_rows_n"] = 1
    else:
        args["built_at"] = CAPTURED - timedelta(seconds=1)
    with pytest.raises((capture.SectorInputCaptureError, SectorViewUnavailable), match="classification"):
        capture.assemble_sector_inputs(**args)


def test_native_projection_preserves_capture_and_withdraws_next_generation(captured_inputs, tmp_path):
    from tests.test_sector_native_view import specimen
    packet, args, _ = classification_case(captured_inputs, tmp_path)
    inputs, receipt = specimen.__wrapped__()
    receipt = replace(receipt, published_at=(CAPTURED + timedelta(seconds=1)).isoformat())
    inputs.central["captured_classification"] = packet
    for audience in ("preview", "entitled"):
        out = project_sector_view(inputs, receipt, audience=audience)
        assert out["data"]["core"]["captured_classification"] == packet
        assert out["data"]["core"]["captured_classification"] is not packet
    with pytest.raises(SectorViewUnavailable, match="classification_capture_after_publication"):
        project_sector_view(inputs, replace(receipt, published_at=(CAPTURED - timedelta(seconds=1)).isoformat()), audience="preview")
    del inputs.central["captured_classification"]
    assert "captured_classification" not in project_sector_view(inputs, receipt, audience="preview")["data"]["core"]


@pytest.mark.parametrize("defect", ["authority", "false_as_zero", "sector", "proxy", "etf_identity", "coverage",
    "duplicate_subject", "unknown_key", "extra_path", "digest", "fake_read_receipt", "mixed_generation",
    "future_clock", "effective_date", "symbol", "native_receipt", "status", "unhashable", "oversize", "cycle"])
def test_native_transport_rejects_false_identity_authority_or_provenance(captured_inputs, tmp_path, defect):
    packet, _, _ = classification_case(captured_inputs, tmp_path)
    a = packet["association"]
    r = a["associations"][0]
    if defect == "authority": a["authority"]["may_publish"] = True
    elif defect == "false_as_zero": a["limitations"]["causal_claim"] = 0
    elif defect == "sector": r["sector"] = "Information Technology"
    elif defect == "proxy": r["sector_etf_proxy"] = "XLK"
    elif defect == "etf_identity": r["etf_security_id"] = "SEC:US-ARCX-XLI"
    elif defect == "coverage": a["coverage"]["associated_n"] = 5
    elif defect == "duplicate_subject": a["associations"][1]["subject"] = dict(r["subject"])
    elif defect == "unknown_key": packet["private_source_root"] = "/private/company"
    elif defect == "extra_path": a["source_attribution"][0]["source_ref"] = "/private/reference"
    elif defect == "digest": packet["capture"]["artifact_sha256"]["security_master.parquet"] = "f" * 64
    elif defect == "fake_read_receipt": a["source_attribution"][0]["read_receipt_sha256"] = "f" * 64
    elif defect == "mixed_generation": a["source_attribution"][0]["generation_id"] = "mixed"
    elif defect == "future_clock": a["source_attribution"][0]["captured_at"] = (CAPTURED + timedelta(days=1)).isoformat()
    elif defect == "effective_date": a["source_attribution"][0]["source_effective_on"] = "2026-01-01"
    elif defect == "symbol": r["source_observations"][0]["native_symbol"] = "MU"
    elif defect == "native_receipt": packet["capture"]["mode"] = "NATIVE"
    elif defect == "status": packet["status"] = "available"
    elif defect == "unhashable": r["status"] = []
    elif defect == "oversize": r["source_observations"][0]["native_name"] = "x" * 32769
    elif defect == "cycle": packet["association"] = packet
    with pytest.raises(SectorViewUnavailable, match="invalid_sector_classification_context"):
        _classification_context(packet)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_shipped_native_page_classification_disclosure_and_signout(captured_inputs, tmp_path, lang):
    from tests.test_sector_central_measured_panel import _native_wire_fixture, _run_native
    packet, _, _ = classification_case(captured_inputs, tmp_path)
    wire = _native_wire_fixture(classification=packet, published_at=(CAPTURED + timedelta(seconds=1)).isoformat())
    out = _run_native("""
      await drainNative();var first=nativeCollect();
      dispatchEl('toggle',{target:{className:'mr-cl-det',open:true}});
      __docEl.attrs['data-lang']=__docEl.attrs['data-lang']==='zh'?'en':'zh';dispatchDoc('langchange');
      var translated=html('mr-classification');nativeAuth('SIGNED_OUT',null);await drainNative();
      show({first:first,translated:translated,last:nativeCollect()});
    """, wire=wire, lang=lang, has_session=True)
    assert out["first"]["nativeState"] == "ready"
    assert out["first"]["classification"].count("data-classification-member=") == 5
    assert "3 / 5" in out["first"]["classification"]
    assert '<details class="mr-cl-det" open>' in out["translated"]
    assert out["last"]["classification"] == "" and out["last"]["nativeState"] == "unauthorized"
    assert len(out["last"]["calls"]) == 1


@pytest.mark.parametrize("defect", ["authority", "hash", "sector", "coverage", "clock"])
def test_shipped_page_withdraws_all_native_data_when_classification_is_malformed(captured_inputs, tmp_path, defect):
    from tests.test_sector_central_measured_panel import _native_wire_fixture, _run_native
    packet, _, _ = classification_case(captured_inputs, tmp_path)
    wire = _native_wire_fixture(classification=packet, published_at=(CAPTURED + timedelta(seconds=1)).isoformat())
    d = wire["projection"]["data"]["core"]["captured_classification"]
    if defect == "authority": d["association"]["authority"]["may_trade"] = True
    elif defect == "hash": d["capture"]["artifact_sha256"]["security_master.parquet"] = "f" * 64
    elif defect == "sector": d["association"]["associations"][0]["sector_etf_proxy"] = "XLK"
    elif defect == "coverage": d["association"]["coverage"]["associated_n"] = 4
    else: d["capture"]["captured_at"] = (CAPTURED + timedelta(days=1)).isoformat()
    out = _run_native(wire=wire)
    assert out["nativeState"] == "invalid" and out["rows"] == [] and out["classification"] == ""


def test_new_generation_absence_withdraws_classification_without_disturbing_selected_sector(captured_inputs, tmp_path):
    from tests.test_sector_central_measured_panel import _native_wire_fixture, _run_native
    packet, _, _ = classification_case(captured_inputs, tmp_path)
    published = (CAPTURED + timedelta(seconds=1)).isoformat()
    first = _native_wire_fixture(classification=packet, published_at=published)
    second = _native_wire_fixture(generation="new-generation-without-classification", published_at=published)
    out = _run_native("""
      await drainNative();dispatchEl('toggle',{target:{className:'mr-cl-det',open:true}});
      nativeRetry();await drainNative();show(nativeCollect());
    """, native_responses=[{"body": first}, {"body": second}])
    assert out["nativeState"] == "ready" and out["classification"] == ""
    assert ["XLK", "true"] in out["rows"] and len(out["calls"]) == 2
