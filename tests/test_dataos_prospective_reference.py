"""Prospective reference evidence: source observation, never consumer read custody."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from lib.dataos.identity import AliasRow, IdentityError, VendorAliasTable, alias_binding_sha256
from scripts import build_security_master as b

DAY = date(2026, 10, 7)
CLOCK = datetime(2026, 10, 7, 10, tzinfo=timezone.utc)
CLOCK_NS = b._reference_clock_ns(CLOCK.isoformat())


def native_row(**changes):
    values = dict(vendor="polygon", vendor_symbol="MU", security_id="SEC:US-XNAS-MU",
                  valid_from=DAY, valid_to=None, known_at=CLOCK,
                  evidence_sha256="a" * 64)
    values.update(changes)
    values["binding_sha256"] = alias_binding_sha256(
        values["vendor"], values["vendor_symbol"], values["security_id"],
        values["valid_from"], values["valid_to"], values["known_at"], values["evidence_sha256"])
    return AliasRow(**values)


@pytest.mark.parametrize("rows", [[], [native_row()]])
@pytest.mark.parametrize("decision", [None, "2026-10-07T10:00:00", datetime(2026, 10, 7, 10)])
def test_native_cutoff_required_even_for_empty_or_unknown(rows, decision):
    table = VendorAliasTable(rows)
    for method, value in [(table.resolve, "UNKNOWN"), (table.vendor_symbol_for, "SEC:US-XNAS-UNKNOWN")]:
        with pytest.raises(IdentityError):
            method("polygon", value, DAY, decision_at=decision)
        with pytest.raises(IdentityError):
            method("polygon", value, DAY)


def test_same_day_evidence_is_not_available_earlier_and_offsets_are_instants():
    row = native_row()
    table = VendorAliasTable([row])
    earlier = CLOCK - timedelta(microseconds=1)
    assert table.resolve("polygon", "MU", DAY, decision_at=earlier) is None
    assert table.vendor_symbol_for("polygon", row.security_id, DAY, decision_at=earlier) is None
    assert table.resolve("polygon", "MU", DAY, decision_at="2026-10-07T06:00:00-04:00") == row.security_id
    assert table.vendor_symbol_for("polygon", row.security_id, DAY, decision_at=CLOCK) == "MU"
    with pytest.raises(IdentityError):
        row.covers(DAY)


def test_event_bounds_and_observation_are_separate():
    row = native_row(valid_to=DAY + timedelta(days=1))
    table = VendorAliasTable([row])
    assert table.resolve("polygon", "MU", DAY - timedelta(days=1), decision_at=CLOCK) is None
    assert table.resolve("polygon", "MU", DAY + timedelta(days=1), decision_at=CLOCK + timedelta(days=1)) is None
    assert table.resolve("polygon", "MU", DAY, decision_at=CLOCK) == row.security_id


@pytest.mark.parametrize("field,value", [("known_at", None), ("known_at", "2026-10-07T10:00:00"),
                                           ("known_at", "2026-10-07T09:59:59Z"),
                                           ("security_id", "SEC:US-XNAS-OTHER"),
                                           ("evidence_sha256", "b" * 64), ("binding_sha256", None)])
def test_native_missing_clock_or_tampered_binding_refused(field, value):
    row = native_row()
    record = {name: getattr(row, name) for name in b.ALIAS_COLUMNS if name != "ingested_at"}
    record[field] = value
    with pytest.raises(IdentityError):
        VendorAliasTable.from_records([record])


def test_legacy_rows_still_allow_date_only_resolution():
    table = VendorAliasTable([AliasRow("membership", "MU", "SEC:US-XNAS-MU")])
    assert table.resolve("membership", "MU", DAY) == "SEC:US-XNAS-MU"


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    snapshots = tmp_path / "symbol_directory" / "snapshots"
    receipts = snapshots.parent / "receipts" / "snapshots"
    snapshots.mkdir(parents=True)
    receipts.mkdir(parents=True)
    rows = [dict(date=DAY.isoformat(), symbol=symbol, security_name=symbol,
                 exchange=exchange, etf=etf, test_issue=False, is_preferred=False,
                 source="otherlisted" if exchange == "P" else "nasdaqlisted")
            for symbol, (exchange, _, _, etf) in b.REFERENCE_PROBES.items()]
    snapshot = snapshots / f"{DAY}.parquet"
    pd.DataFrame(rows).to_parquet(snapshot, index=False)
    receipt = dict(artifact=dict(sha256=b._sha256(snapshot), bytes=snapshot.stat().st_size,
                                key=f"snapshots/{DAY}.parquet", rows=len(rows)),
                   observation_date=DAY.isoformat(),
                   completeness=dict(status="complete", duplicate_key_count=0),
                   authority=dict(listing_identity_observation_eligible=True),
                   clocks=dict(collector_started_at="2026-10-07T02:00:00Z",
                               collector_completed_at="2026-10-07T02:01:00Z"))
    (receipts / f"{DAY}.json").write_text(json.dumps(receipt))
    mic = dict(http_status=200, source_url="https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv",
               response_sha256="c" * 64, request_started_at_utc="2026-10-07T06:00:00Z",
               response_read_completed_at_utc="2026-10-07T06:00:25Z",
               selected_row={"MIC": "ARCX", "OPERATING MIC": "XNYS", "STATUS": "ACTIVE",
                             "OPRT/SGMT": "SGMT", "ISO COUNTRY CODE (ISO 3166)": "US"})
    probes = {}
    for symbol, (_, mic_code, kind, _) in b.REFERENCE_PROBES.items():
        payload = dict(status="OK", results=dict(ticker=symbol, market="stocks", locale="us",
                       primary_exchange=mic_code, type=kind, active=True, composite_figi="BBG000C5Z1S3",
                       unused_vendor_field="retained but never used as an identity input"))
        probes[symbol] = dict(requested_date=str(DAY), request_path=f"/v3/reference/tickers/{symbol}",
                             request_params={"date": str(DAY)}, request_started_at_utc_ns=CLOCK_NS - 1000000000,
                             decoded_payload_observed_at_utc_ns=CLOCK_NS - 999,
                             decoded_payload=payload, decoded_payload_sha256=b._reference_digest(payload))
    bundle = dict(schema=b.REFERENCE_SCHEMA, probes=probes, mic_evidence=mic)
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(bundle))
    monkeypatch.setattr(b, "SYMBOL_DIR_SNAPSHOTS", snapshots)
    monkeypatch.setattr(b.time, "time_ns", lambda: CLOCK_NS + 1)
    return path, bundle, rows


def test_intake_preserves_decoded_bytes_semantics_and_ns_ceiling(evidence, tmp_path):
    path, bundle, _ = evidence
    state = b._load_reference_input(tmp_path / "out", path)
    assert state["input"] == bundle
    assert state["probes"]["MU"]["known_at"] == "2026-10-07T10:00:00.000001+00:00"
    assert state["source_read_completed_at_utc_ns"] == CLOCK_NS + 1
    assert "not publication or Radar read" in state["clock_semantics"]
    assert state["authority"] == {"research_admitted": False, "trading_authority": False}


@pytest.mark.parametrize("change", ["hash", "clock", "request", "mic", "missing_probe"])
def test_bad_evidence_refuses_before_generation(evidence, tmp_path, change):
    path, bundle, _ = evidence
    if change == "hash": bundle["probes"]["MU"]["decoded_payload_sha256"] = "d" * 64
    elif change == "clock": bundle["probes"]["MU"]["decoded_payload_observed_at_utc_ns"] = CLOCK_NS + 2
    elif change == "request": bundle["probes"]["MU"]["request_params"] = {"date": "2026-10-06"}
    elif change == "mic": bundle["mic_evidence"]["selected_row"]["MIC"] = "XNYS"
    else: bundle["probes"].pop("MU")
    path.write_text(json.dumps(bundle))
    with pytest.raises(IdentityError):
        b._load_reference_input(tmp_path / "out", path)


@pytest.mark.parametrize("payload,reason", [(None, "native_reference_unavailable"),
                                            ({"status": "NOT_AUTHORIZED"}, "native_reference_unavailable"),
                                            ({"status": "OK", "results": {}}, "native_reference_identity_conflict")])
def test_one_probe_failure_is_typed_and_isolated(evidence, tmp_path, payload, reason):
    path, bundle, _ = evidence
    bundle["probes"]["MU"].update(decoded_payload=payload, decoded_payload_sha256=b._reference_digest(payload))
    path.write_text(json.dumps(bundle))
    state = b._load_reference_input(tmp_path / "out", path)
    assert state["probes"]["MU"]["code"] == reason
    assert all(state["probes"][s]["status"] == "EVIDENCE_READY" for s in ("SPY", "QQQ", "SMH"))


def setup_builder(monkeypatch, tmp_path, rows):
    monkeypatch.setattr(b, "load_universe", lambda: {"MU": {"sources": ["fixture"], "first_seen": DAY}})
    monkeypatch.setattr(b, "load_delisted", lambda: {})
    monkeypatch.setattr(b, "load_directory", lambda: ({r["symbol"]: r["exchange"] for r in rows},
        {r["symbol"]: {k: r[k] for k in ("etf", "test_issue", "is_preferred")} for r in rows},
        str(DAY), b.SYMBOL_DIR_SNAPSHOTS / f"{DAY}.parquet"))
    monkeypatch.setattr(b, "load_cik_map", lambda: ({}, str(DAY), tmp_path / "cik.parquet", frozenset()))
    monkeypatch.setattr(b, "load_config_maps", lambda: ({}, {}))
    monkeypatch.setattr(b, "load_gmi_us_seeds", lambda: [{"symbol": s, "node_id": f"co:us:{s}"} for s in b.REFERENCE_PROBES])
    monkeypatch.setattr(b, "load_cn_hk_seeds", lambda: [])
    monkeypatch.setattr(b, "load_cninfo_evidence", lambda: ({}, None))
    monkeypatch.setattr(b, "load_hk_shorts_evidence", lambda: ({}, None))


def test_first_mint_stored_rerun_and_gmi_exclusion(evidence, tmp_path, monkeypatch):
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)  # ordinary baseline: MU only, ETFs fail the common-equity gate
    original = pd.read_parquet(out / b.MASTER_NAME)
    first = b.build(out, reference_evidence_path=path)
    assert all(r["status"] == "BOUND" for r in first["prospective_reference"]["probes"].values())
    master = pd.read_parquet(out / b.MASTER_NAME)
    assert len(master) == len(original) + 3
    etfs = master[master.inception_code.isin(["SPY", "QQQ", "SMH"])]
    assert etfs.issuer_id.isna().all() and etfs.issuer_cik.isna().all()
    assert set(etfs.issuer_state) == {"NO_ISSUER_EVIDENCE"}
    aliases = (out / b.ALIASES_NAME).read_bytes()
    monkeypatch.setattr(b.time, "time_ns", lambda: CLOCK_NS + 60000000000)
    second = b.build(out)
    assert first["prospective_reference"] == second["prospective_reference"]
    assert (out / b.ALIASES_NAME).read_bytes() == aliases
    for result in (first, second):
        gmi = result["us_gmi_admission"]
        assert gmi["resolved_total"] == 1
        assert {r["symbol"] for r in gmi["refusals_this_run"]} == {"SPY", "QQQ", "SMH"}
        assert all(r["code"] == "structural_etf" for r in gmi["refusals_this_run"])


def test_arca_mapping_is_not_widened_for_ordinary_universe():
    universe = {"SPY": {"sources": [], "first_seen": DAY}, "OTHER": {"sources": [], "first_seen": DAY}}
    ordinary = b.resolve_universe(universe, {}, {"SPY": "P", "OTHER": "P"}, str(DAY))
    assert all(r.listing_key is None for r in ordinary)
    scoped = b.resolve_universe(universe, {}, {"SPY": "P", "OTHER": "P"}, str(DAY), reference_probe_keys=frozenset({"SPY"}))
    assert {r.key: r.listing_key is not None for r in scoped} == {"SPY": True, "OTHER": False}


def test_native_submicrosecond_source_clock_cannot_admit_earlier():
    row = native_row(known_at="2026-10-07T10:00:00.000000001Z")
    assert row.known_at == CLOCK + timedelta(microseconds=1)
    table = VendorAliasTable([row])
    assert table.resolve("polygon", "MU", DAY, decision_at=CLOCK) is None
    assert table.resolve("polygon", "MU", DAY, decision_at=CLOCK + timedelta(microseconds=1)) == row.security_id


def test_pending_transition_refusal_is_retained_and_no_fence_is_bypassed(evidence, tmp_path, monkeypatch):
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)
    masters = b._read_existing(out / b.MASTER_NAME, b.MASTER_COLUMNS, b.MASTER_DTYPES)
    lost = dict(masters[0], security_id="SEC:US-XNAS-LOST", listing_key="US-XNAS-LOST", inception_code="LOST")
    b._write_parquet(masters + [lost], b.MASTER_COLUMNS, out / b.MASTER_NAME, b.MASTER_DTYPES)
    result = b.build(out, reference_evidence_path=path)
    probes = result["prospective_reference"]["probes"]
    assert probes["MU"]["status"] == "BOUND"
    for symbol in ("SPY", "QQQ", "SMH"):
        assert probes[symbol]["code"] == "canonical_identity_refused"
        assert probes[symbol]["owner_refusals"][0]["lost_rows"] == [lost["security_id"]]
    assert len(pd.read_parquet(out / b.MASTER_NAME)) == 2
    assert result["pending_transition_refusals"]
    again = b.build(out)
    assert again["prospective_reference"] == result["prospective_reference"]


def test_conflicting_intake_cannot_replace_existing_observation(evidence, tmp_path, monkeypatch):
    path, bundle, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)
    b.build(out, reference_evidence_path=path)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    bundle["probes"]["MU"]["decoded_payload"]["results"]["composite_figi"] = "BBG000BSWKH7"
    bundle["probes"]["MU"]["decoded_payload_sha256"] = b._reference_digest(bundle["probes"]["MU"]["decoded_payload"])
    path.write_text(json.dumps(bundle))
    with pytest.raises(IdentityError, match="conflicting prospective reference"):
        b.build(out, reference_evidence_path=path)
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}


def test_nonprobe_mint_aborts_before_any_artifact_write(evidence, tmp_path, monkeypatch):
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    rows.append(dict(symbol="UNRELATED", exchange="NASDAQ", etf=False, test_issue=False, is_preferred=False))
    monkeypatch.setattr(b, "load_universe", lambda: {s: {"sources": ["fixture"], "first_seen": DAY}
                                                   for s in ("MU", "UNRELATED")})
    with pytest.raises(IdentityError, match="non-probe"):
        b.build(out, reference_evidence_path=path)
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}


def test_theme_graph_projection_preserves_native_fields_without_enabling_lookup(evidence, tmp_path, monkeypatch):
    from engine.theme_graph.identity_resolution import load_master_inputs
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    root = tmp_path / "data"
    out = root / "reference"
    b.build(out)
    b.build(out, reference_evidence_path=path)
    spine = load_master_inputs(root)
    assert spine is not None
    with pytest.raises(IdentityError):
        spine.alias_table.resolve("polygon", "MU", DAY)
    assert spine.alias_table.resolve("polygon", "MU", DAY,
                                     decision_at=CLOCK + timedelta(microseconds=1)) == "SEC:US-XNAS-MU"


def test_theme_graph_date_only_fallback_does_not_enable_native_namespace(evidence, tmp_path, monkeypatch):
    from engine.theme_graph.identity_resolution import load_master_inputs, _resolve_node_row
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    root = tmp_path / "data"
    out = root / "reference"
    b.build(out)
    b.build(out, reference_evidence_path=path)
    spine = load_master_inputs(root)
    assert "polygon" in spine.vendors
    for historical in (False, True):
        result = _resolve_node_row(node_id="co:us:UNKNOWN", resolution_asof=str(DAY),
            inputs=spine, etf_symbols=frozenset(), computed_at=CLOCK.isoformat(),
            engine_version="fixture", historical=historical)
        assert result.get("security_id") is None
        assert "polygon" not in json.loads(result["source_receipts"])["checked_vendors"]


@pytest.mark.parametrize("clock", [
    "2026-10-07 10:00:00.000000001Z", "20261007T100000.000000001Z",
    "2026-10-07T10:00:00,000000001Z", "2026-10-07T10:00:00.000000001+0000",
    "2026-10-07T10:00:00.0000000001Z", "2026-10-07t10:00:00.000000001Z",
])
def test_noncanonical_native_clock_grammars_are_explicitly_refused(clock):
    with pytest.raises(IdentityError, match="known_at"):
        native_row(known_at=clock)
    table = VendorAliasTable([native_row()])
    with pytest.raises(IdentityError, match="decision_at"):
        table.resolve("polygon", "MU", DAY, decision_at=clock)
    with pytest.raises(IdentityError, match="decision_at"):
        table.vendor_symbol_for("polygon", "SEC:US-XNAS-MU", DAY, decision_at=clock)


def test_offset_nanoseconds_ceil_evidence_and_floor_decision():
    row = native_row(known_at="2026-10-07T15:30:00.000000001+05:30")
    table = VendorAliasTable([row])
    assert row.known_at == CLOCK + timedelta(microseconds=1)
    assert table.resolve("polygon", "MU", DAY,
                         decision_at="2026-10-07T15:30:00.000000999+05:30") is None
    assert table.resolve("polygon", "MU", DAY,
                         decision_at="2026-10-07T15:30:00.000001000+05:30") == row.security_id


@pytest.mark.parametrize("failure", ["null", "missing", "denied", "empty_identity", "missing_figi"])
def test_ineligible_native_etfs_cannot_use_gmi_seed_to_mint(evidence, tmp_path, monkeypatch, failure):
    path, bundle, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)
    for symbol in ("SPY", "QQQ", "SMH"):
        record = bundle["probes"][symbol]
        payload = record["decoded_payload"]
        if failure in {"null", "missing"}: payload = None
        elif failure == "denied": payload = {"status": "NOT_AUTHORIZED"}
        elif failure == "empty_identity": payload = {"status": "OK", "results": {}}
        else: payload["results"].pop("composite_figi")
        record.update(decoded_payload=payload, decoded_payload_sha256=b._reference_digest(payload))
        if failure == "missing": record.pop("decoded_payload")
    path.write_text(json.dumps(bundle))
    first = b.build(out, reference_evidence_path=path)
    again = b.build(out)
    assert again["prospective_reference"] == first["prospective_reference"]
    for result in (first, again):
        assert result["prospective_reference"]["probes"]["MU"]["status"] == "BOUND"
        assert all(result["prospective_reference"]["probes"][s]["status"] == "REFUSED"
                   for s in ("SPY", "QQQ", "SMH"))
        assert {r["symbol"] for r in result["us_gmi_admission"]["refusals_this_run"]} == {"SPY", "QQQ", "SMH"}
        assert {r["symbol"]: r["code"] for r in result["us_gmi_admission"]["refusals_this_run"]} == {
            "SPY": "structural_etf", "QQQ": "not_common_equity_etf", "SMH": "not_common_equity_etf"}
    assert set(pd.read_parquet(out / b.MASTER_NAME).inception_code) == {"MU"}
    native = pd.read_parquet(out / b.ALIASES_NAME).query("vendor == 'polygon'")
    assert set(native.vendor_symbol) == {"MU"}


def test_later_owner_fence_clearance_cannot_backdate_a_refused_probe(evidence, tmp_path, monkeypatch):
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    out = tmp_path / "out"
    b.build(out)
    masters = b._read_existing(out / b.MASTER_NAME, b.MASTER_COLUMNS, b.MASTER_DTYPES)
    lost = dict(masters[0], security_id="SEC:US-XNAS-LOST", listing_key="US-XNAS-LOST", inception_code="LOST")
    b._write_parquet(masters + [lost], b.MASTER_COLUMNS, out / b.MASTER_NAME, b.MASTER_DTYPES)
    first = b.build(out, reference_evidence_path=path)
    old = first["prospective_reference"]["probes"]["QQQ"]
    assert old["code"] == "canonical_identity_refused"
    # Later owner evidence re-derives LOST, clearing the original pending fence.
    monkeypatch.setattr(b, "load_universe", lambda: {
        s: {"sources": ["fixture"], "first_seen": DAY} for s in ("MU", "LOST")})
    directory = {r["symbol"]: r["exchange"] for r in rows} | {"LOST": "NASDAQ"}
    flags = {s: {"etf": s in {"SPY", "QQQ", "SMH"}, "test_issue": False, "is_preferred": False}
             for s in directory}
    monkeypatch.setattr(b, "load_directory", lambda: (directory, flags, "2026-10-08", None))
    monkeypatch.setattr(b.time, "time_ns", lambda: CLOCK_NS + 86400 * 1000000000)
    again = b.build(out)
    assert again["pending_transition_refusals"] == []
    assert again["prospective_reference"] == first["prospective_reference"]
    assert set(pd.read_parquet(out / b.MASTER_NAME).inception_code) == {"MU", "LOST"}
    table = VendorAliasTable.from_records(pd.read_parquet(out / b.ALIASES_NAME).where(
        lambda df: df.notna(), None).to_dict("records"))
    assert table.resolve("polygon", "QQQ", DAY, decision_at=old["known_at"]) is None


def test_native_listing_cannot_bind_conflicting_canonical_exit_venue(evidence, tmp_path, monkeypatch):
    path, _, rows = evidence
    setup_builder(monkeypatch, tmp_path, rows)
    monkeypatch.setattr(b, "load_delisted", lambda: {"MU": {"exchange": "NYSE", "last_session": "2026-10-06"}})
    out = tmp_path / "out"
    b.build(out)
    before = pd.read_parquet(out / b.MASTER_NAME)
    assert before.loc[before.inception_code.eq("MU"), "mic"].item() == "XNYS"
    result = b.build(out, reference_evidence_path=path)
    probe = result["prospective_reference"]["probes"]["MU"]
    assert probe["code"] == "canonical_listing_identity_conflict"
    assert probe["canonical_listing_identity"]["mic"] == "XNYS"
    after = pd.read_parquet(out / b.MASTER_NAME)
    pd.testing.assert_frame_equal(before[before.inception_code.eq("MU")].reset_index(drop=True),
                                  after[after.inception_code.eq("MU")].reset_index(drop=True))
    assert "MU" not in set(pd.read_parquet(out / b.ALIASES_NAME).query("vendor == 'polygon'").vendor_symbol)
    assert b.build(out)["prospective_reference"] == result["prospective_reference"]


def test_native_agreement_uses_owner_listing_fields_not_immutable_id_prefix(evidence, tmp_path):
    path, _, _ = evidence
    state = b._load_reference_input(tmp_path / "out", path)
    stable = "SEC:US-XNYS-OLDMU"
    row = dict(security_id=stable, country="US", mic="XNAS", listing_key="US-XNAS-MU",
               inception_code="MU", security_state=None)
    aliases = b._reference_aliases(state, {"MU": stable}, [row], [], [])
    assert [(r.vendor_symbol, r.security_id) for r in aliases] == [("MU", stable)]
    assert state["probes"]["MU"]["status"] == "BOUND"


# R24 — native-generation preservation guard for the EXISTING legacy writer.
# Source-only tests. The old writer must refuse native publication/history
# until its canonical owner can append genuine observation revisions.
@pytest.mark.parametrize("native", [
    {"publication": {"schema": "mastermind.identity_publication.v1", "generation_id": "a" * 64},
     "identity_observations": {"schema": "mastermind.identity_observations.v1", "attempts": []}},
    {"publication": {"schema": "mastermind.identity_publication.v1"}},
    {"identity_observations": {"schema": "mastermind.identity_observations.v1"}},
    {"publication": None, "identity_observations": None},
    {"publication": {}, "identity_observations": {"anchor": None}},
])
def test_r24_existing_native_generation_refuses_before_any_source_write(
        tmp_path, monkeypatch, native):
    out = tmp_path / "canonical-reference"
    out.mkdir()
    original = {"prospective_reference": {"schema": "legacy-retain"},
                "generated_at": "2026-10-15T13:32:43", **native}
    receipt = out / b.RECEIPT_NAME
    receipt.write_text(json.dumps(original, sort_keys=True) + "\n")
    artifacts = {}
    for name in b._NIGHTLY_ARTIFACT_NAMES:
        p = out / name
        p.write_bytes(("preserve original bytes: " + name).encode())
        artifacts[name] = p.read_bytes()
    original_receipt = receipt.read_bytes()
    def forbidden(*_a, **_kw):
        raise AssertionError("builder touched identity input or output before publication-history refusal")
    monkeypatch.setattr(b, "_iso_now", forbidden)
    monkeypatch.setattr(b, "_write_parquet", forbidden)
    with pytest.raises(IdentityError, match="native identity publication"):
        b.build(out)
    assert receipt.read_bytes() == original_receipt
    assert all((out / name).read_bytes() == data for name, data in artifacts.items())


def test_r24_legacy_only_receipt_does_not_trigger_native_guard(tmp_path):
    out = tmp_path / "reference"
    out.mkdir()
    receipt = out / b.RECEIPT_NAME
    receipt.write_text(json.dumps({"prospective_reference": {"schema": "legacy"},
                                   "generated_at": "2026-10-15T13:32:43"}) + "\n")
    before = receipt.read_bytes()
    b._assert_no_unpreserved_native_generation(out)
    assert receipt.read_bytes() == before


def test_r24_nightly_fails_closed_and_preserves_complete_native_history(
        tmp_path, monkeypatch, capsys):
    out = tmp_path / "canonical-reference"
    out.mkdir()
    original_receipt = out / b.RECEIPT_NAME
    original_receipt.write_text(json.dumps({
        "prospective_reference": {"schema": "legacy"},
        "publication": {"schema": "mastermind.identity_publication.v1", "generation_id": "b" * 64},
        "identity_observations": {"schema": "mastermind.identity_observations.v1", "attempts": []},
        "generated_at": "2026-10-15T13:32:43"}, sort_keys=True) + "\n")
    prior = {b.RECEIPT_NAME: original_receipt.read_bytes()}
    for name in b._NIGHTLY_ARTIFACT_NAMES:
        p = out / name
        p.write_bytes(("native-generation:" + name).encode())
        prior[name] = p.read_bytes()
    monkeypatch.setattr(b, "_identity_rail_unreadable", lambda *_args: False)
    # Sparse test checkout may omit unrelated breadth and membership inputs.
    # Bind those preflight existence checks to this deliberately existing file;
    # no collector, production read, or real identity regeneration is allowed.
    for key in ("CONSTITUENTS", "MIDCAP_CONSTITUENTS", "SMALLCAP_CONSTITUENTS",
                "MEMBERSHIP", "DELISTED_LEDGER", "CONFIG_YML", "TICKER_ALIASES_PY"):
        monkeypatch.setattr(b, key, original_receipt)
    # Failure must be specifically typed as native-publication refusal,
    # not just some unrelated missing input, and cannot change prior bytes.
    assert b.run_nightly_refresh(out) == 0
    output = capsys.readouterr().out
    assert "native identity publication" in output
    assert "refusing stale legacy rollback" in output
    assert all((out / name).read_bytes() == data for name, data in prior.items())


def test_r24_new_native_publication_arriving_during_legacy_rebuild_refuses_before_any_write(
        evidence, tmp_path, monkeypatch):
    """A read at function entry alone is insufficient while build computes."""
    _path, _bundle, listing_rows = evidence
    setup_builder(monkeypatch, tmp_path, listing_rows)
    out = tmp_path / "out"
    b.build(out)  # Establish ordinary legacy artifact baseline on temporary files.
    originals = {name: (out / name).read_bytes() for name in b._NIGHTLY_ARTIFACT_NAMES}
    receipt_file = out / b.RECEIPT_NAME
    baseline = json.loads(receipt_file.read_text())
    assert "publication" not in baseline and "identity_observations" not in baseline
    native = dict(
        publication={"schema": "mastermind.identity_publication.v1", "generation_id": "c" * 64},
        identity_observations={"schema": "mastermind.identity_observations.v1", "attempts": []},
    )
    original_iso = b._iso_now
    calls = []
    def concurrent_native_owner_receipt():
        calls.append(True)
        if len(calls) == 1:
            receipt_file.write_text(json.dumps({**baseline, **native}, sort_keys=True) + "\n")
        return original_iso()
    monkeypatch.setattr(b, "_iso_now", concurrent_native_owner_receipt)
    with pytest.raises(IdentityError, match="native identity publication"):
        b.build(out)
    assert calls, "test must inject after entry guard and before output writes"
    assert {name: (out / name).read_bytes() for name in b._NIGHTLY_ARTIFACT_NAMES} == originals
    retained = json.loads(receipt_file.read_text())
    assert retained["publication"] == native["publication"]
    assert retained["identity_observations"] == native["identity_observations"]


@pytest.mark.parametrize("mode", ["raised_refusal", "receipt_notes", "unchanged_inputs"])
def test_r24_nightly_never_restores_over_concurrent_native_generation(
        tmp_path, monkeypatch, capsys, mode):
    """A newer native receipt wins even when the old nightly must abort.

    The native write here is a controlled temporary fixture, never an actual
    publisher; the existing nightly must not remove it by restoring its stale
    pre-build receipt. All three existing branches historically risked this.
    """
    out = tmp_path / "reference"
    out.mkdir()
    receipt_file = out / b.RECEIPT_NAME
    legacy = {"prospective_reference": {"schema": "legacy"},
              "generated_at": "2026-10-15T13:32:43"}
    receipt_file.write_text(json.dumps(legacy, sort_keys=True) + "\n")
    older_bytes = receipt_file.read_bytes()
    prior_artifacts = {}
    for name in b._NIGHTLY_ARTIFACT_NAMES:
        f = out / name
        f.write_bytes(("old-generation:" + name).encode())
        prior_artifacts[name] = f.read_bytes()

    # Keep the existing nightly input-preflight untouched in real operation;
    # these synthetic fixtures bind mandatory existence paths to a known file
    # so the test actually exercises the later recovery/rollback branches.
    for key in ("CONSTITUENTS", "MIDCAP_CONSTITUENTS", "SMALLCAP_CONSTITUENTS",
                "MEMBERSHIP", "DELISTED_LEDGER", "CONFIG_YML", "TICKER_ALIASES_PY"):
        monkeypatch.setattr(b, key, receipt_file)
    monkeypatch.setattr(b, "_identity_rail_unreadable", lambda *_: False)

    newer = {**legacy,
             "publication": {"schema": "mastermind.identity_publication.v1",
                             "generation_id": "a" * 64},
             "identity_observations": {
                 "schema": "mastermind.identity_observations.v1",
                 "attempts": []}}
    newer_bytes = (json.dumps(newer, sort_keys=True) + "\n").encode()
    called = []

    def native_arrives_during_legacy_refresh(_out_dir, **_kwargs):
        called.append(True)
        receipt_file.write_bytes(newer_bytes)
        if mode == "raised_refusal":
            (out / b._NIGHTLY_ARTIFACT_NAMES[0]).write_bytes(b"native-newer-artifact")
            raise IdentityError("native identity publication/history arrived after older snapshot")
        return {"notes": ["legacy owner cannot classify this"]} if mode == "receipt_notes" else {"notes": []}

    monkeypatch.setattr(b, "build", native_arrives_during_legacy_refresh)
    assert b.run_nightly_refresh(out) == 0
    logs = capsys.readouterr().out
    assert len(called) == 1, "The simulated newer publication must actually occur"
    assert receipt_file.read_bytes() == newer_bytes, (
        "nightly rolled back a newer source-owned native receipt to legacy"
    )
    assert "security-master-native-history-race" in logs
    if mode == "raised_refusal":
        assert (out / b._NIGHTLY_ARTIFACT_NAMES[0]).read_bytes() == b"native-newer-artifact"
    assert receipt_file.read_bytes() != older_bytes


def test_r24_original_legacy_error_still_restores_last_good_bytes(
        tmp_path, monkeypatch, capsys):
    """Ordinary failed legacy rebuild retains its pre-existing rollback law."""
    out = tmp_path / "reference"
    out.mkdir()
    receipt_file = out / b.RECEIPT_NAME
    receipt_file.write_text(json.dumps({"prospective_reference": {"schema": "legacy"}}) + "\n")
    original_receipt = receipt_file.read_bytes()
    originals = {}
    for name in b._NIGHTLY_ARTIFACT_NAMES:
        f = out / name
        f.write_bytes(("old:" + name).encode())
        originals[name] = f.read_bytes()
    for key in ("CONSTITUENTS", "MIDCAP_CONSTITUENTS", "SMALLCAP_CONSTITUENTS",
                "MEMBERSHIP", "DELISTED_LEDGER", "CONFIG_YML", "TICKER_ALIASES_PY"):
        monkeypatch.setattr(b, key, receipt_file)
    monkeypatch.setattr(b, "_identity_rail_unreadable", lambda *_: False)

    def invalid_legacy_write(_out_dir, **_kwargs):
        (out / b._NIGHTLY_ARTIFACT_NAMES[0]).write_bytes(b"partial-invalid-legacy")
        raise ValueError("synthetic original legacy failure")

    monkeypatch.setattr(b, "build", invalid_legacy_write)
    assert b.run_nightly_refresh(out) == 0
    assert "keeping last-good artifacts" in capsys.readouterr().out
    assert receipt_file.read_bytes() == original_receipt
    assert all((out / name).read_bytes() == data for name, data in originals.items())


# R25 Pro audit: one cooperative, OS-backed writer boundary for the existing
# manual build AND its outer nightly snapshot/rollback transaction.
def test_r25_directory_writer_scope_is_reentrant_and_has_no_lockfile(tmp_path):
    out = tmp_path / "reference"
    with b._reference_writer_scope(out):
        with b._reference_writer_scope(out):
            assert out.is_dir()
            assert list(out.iterdir()) == []
    assert list(out.iterdir()) == []


def _r25_probe_other_process(out):
    import os
    import subprocess
    import sys
    script = '''from pathlib import Path
from scripts import build_security_master as b
import sys
try:
    with b._reference_writer_scope(Path(sys.argv[1])):
        print("ACQUIRED")
except b.IdentityError:
    print("BUSY")
'''
    p = subprocess.run([sys.executable, "-c", script, str(out)], cwd=b.ROOT,
                       capture_output=True, text=True, timeout=8,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def test_r25_actual_other_process_cannot_enter_until_release(tmp_path):
    out = tmp_path / "reference"
    with b._reference_writer_scope(out):
        assert _r25_probe_other_process(out) == "BUSY"
    assert _r25_probe_other_process(out) == "ACQUIRED"


def test_r25_exception_releases_writer_scope(tmp_path):
    out = tmp_path / "reference"
    with pytest.raises(ValueError, match="test failure"):
        with b._reference_writer_scope(out):
            raise ValueError("test failure")
    assert _r25_probe_other_process(out) == "ACQUIRED"


def test_r25_another_thread_cannot_inherit_reentrancy(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    out = tmp_path / "reference"
    def competing():
        try:
            with b._reference_writer_scope(out):
                return "ACQUIRED"
        except IdentityError:
            return "BUSY"
    with b._reference_writer_scope(out):
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(competing).result(timeout=5) == "BUSY"
    assert competing() == "ACQUIRED"


def test_r25_manual_entrypoint_holds_the_same_os_lock(tmp_path, monkeypatch):
    out = tmp_path / "reference"
    def body(*args, **kwargs):
        assert _r25_probe_other_process(out) == "BUSY"
        return {"verified": "manual"}
    monkeypatch.setattr(b, "_build_reference_unlocked", body)
    assert b.build(out) == {"verified": "manual"}


def test_r25_nightly_holds_lock_across_entire_body(tmp_path, monkeypatch):
    out = tmp_path / "reference"
    def body(*args, **kwargs):
        assert _r25_probe_other_process(out) == "BUSY"
        # Native nightly invokes public build while already inside its scope.
        monkeypatch.setattr(b, "_build_reference_unlocked", lambda *a, **k: {"ok": True})
        assert b.build(out) == {"ok": True}
        return 0
    monkeypatch.setattr(b, "_run_nightly_reference_unlocked", body)
    assert b.run_nightly_refresh(out) == 0
    assert _r25_probe_other_process(out) == "ACQUIRED"


def test_r25_dry_run_stays_read_only_on_nonexistent_output(tmp_path, monkeypatch):
    out = tmp_path / "not-created"
    monkeypatch.setattr(b, "_build_reference_unlocked", lambda *a, **k: {"dry_run": k["dry_run"]})
    assert b.build(out, dry_run=True) == {"dry_run": True}
    assert not out.exists()


def test_r25_symlink_writer_target_refuses(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(IdentityError, match="writer"):
        with b._reference_writer_scope(alias):
            pytest.fail("symlink acquired")
    assert list(real.iterdir()) == []


def test_r25_replaced_directory_cannot_receive_legacy_writes(tmp_path):
    out = tmp_path / "reference"
    old = tmp_path / "renamed"
    with b._reference_writer_scope(out):
        out.rename(old)
        out.mkdir()
        with pytest.raises(IdentityError, match="writer.*changed"):
            b._assert_reference_writer_target(out)
    assert not list(old.iterdir()) and not list(out.iterdir())


def test_r25_nightly_busy_is_fail_closed_not_success(tmp_path, monkeypatch, capsys):
    from contextlib import contextmanager
    @contextmanager
    def busy(_):
        raise IdentityError("reference writer busy")
        yield
    monkeypatch.setattr(b, "_reference_writer_scope", busy)
    monkeypatch.setattr(b, "_run_nightly_reference_unlocked",
                        lambda *_: pytest.fail("busy writer reached body"))
    assert b.run_nightly_refresh(tmp_path / "reference") == 0
    assert "reference writer busy" in capsys.readouterr().out


def test_r25_writer_body_oserror_preserves_legacy_exception_type(tmp_path):
    error = OSError("fixture I/O failure inside actual builder")
    with pytest.raises(OSError) as caught:
        with b._reference_writer_scope(tmp_path / "reference"):
            raise error
    assert caught.value is error


def test_r25_independent_directories_do_not_share_a_global_lock(tmp_path):
    with b._reference_writer_scope(tmp_path / "one"):
        assert _r25_probe_other_process(tmp_path / "two") == "ACQUIRED"


def test_r25_fork_cannot_inherit_parent_reentrancy(tmp_path):
    import os
    import subprocess
    import sys
    import textwrap
    if not hasattr(os, "fork"):
        pytest.skip("POSIX-only file-lock contract")
    # Pytest/pandas can already own native threads. Exec a fresh interpreter
    # before importing the writer, and make a fork safety warning fail the test.
    script = textwrap.dedent('''
        import os
        import select
        import signal
        import subprocess
        import sys
        import threading
        import time
        import traceback
        from pathlib import Path
        from scripts import build_security_master as b

        out = Path(sys.argv[1])
        probe_script = """from pathlib import Path
        from scripts import build_security_master as b
        import sys
        try:
            with b._reference_writer_scope(Path(sys.argv[1])):
                print("ACQUIRED")
        except b.IdentityError:
            print("BUSY")
        """
        def probe():
            result = subprocess.run(
                [sys.executable, "-c", probe_script, str(out)], cwd=b.ROOT,
                capture_output=True, text=True, timeout=8)
            assert result.returncode == 0, result.stderr
            return result.stdout.strip()

        with b._reference_writer_scope(out):
            assert threading.active_count() == 1, "fork harness must be single-threaded"
            read_fd, write_fd = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.close(read_fd)
                exit_code = 1
                try:
                    try:
                        with b._reference_writer_scope(out):
                            result = b"ACQUIRED"
                    except b.IdentityError:
                        result = b"BUSY"
                    os.write(write_fd, result)
                    exit_code = 0
                except BaseException:
                    traceback.print_exc()
                finally:
                    os.close(write_fd)
                    os._exit(exit_code)
            os.close(write_fd)
            reaped = False
            try:
                assert select.select([read_fd], [], [], 5)[0], "child deadlocked"
                assert os.read(read_fd, 64) == b"BUSY"
                deadline = time.monotonic() + 5
                while True:
                    waited, status = os.waitpid(pid, os.WNOHANG)
                    if waited == pid:
                        reaped = True
                        assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
                        break
                    assert time.monotonic() < deadline, "child did not exit"
                    time.sleep(0.01)
            finally:
                os.close(read_fd)
                if not reaped:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    os.waitpid(pid, 0)
            assert probe() == "BUSY", "child must not release the parent's lock"
        assert probe() == "ACQUIRED", "parent must release its lock on exit"
    ''')
    # Bound any numerical-library pools inherited through the environment, too.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
           "NUMEXPR_NUM_THREADS": "1"}
    result = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", script,
         str(tmp_path / "reference")],
        cwd=b.ROOT, capture_output=True, text=True, timeout=30, env=env)
    assert result.returncode == 0, result.stdout + result.stderr


def _r25_inject_cleanup_errors(monkeypatch, failures):
    import errno
    import fcntl
    import os

    real_flock, real_close = fcntl.flock, os.close
    held = {"fd": None}
    errors = {name: OSError(errno.EIO, "injected " + name + " failure")
              for name in failures}

    def flock(fd, operation):
        if operation & fcntl.LOCK_EX and held["fd"] is None:
            held["fd"] = fd
        if fd == held["fd"] and operation == fcntl.LOCK_UN and "unlock" in errors:
            raise errors["unlock"]
        return real_flock(fd, operation)

    def close(fd):
        real_close(fd)
        # Model an error reported after closing. Never retry a possibly reused fd.
        if fd == held["fd"] and "close" in errors:
            raise errors["close"]

    monkeypatch.setattr(fcntl, "flock", flock)
    monkeypatch.setattr(os, "close", close)
    return errors


@pytest.mark.parametrize("failures", [("unlock",), ("close",), ("unlock", "close")])
def test_r25_cleanup_error_keeps_original_builder_exception(tmp_path, monkeypatch, failures):
    import errno
    out = tmp_path / "reference"
    original = OSError(errno.ENOSPC, "injected builder disk-full failure")
    with monkeypatch.context() as patch:
        errors = _r25_inject_cleanup_errors(patch, failures)
        with pytest.raises(OSError) as caught:
            with b._reference_writer_scope(out):
                raise original
    assert caught.value is original
    notes = "\n".join(getattr(original, "__notes__", ()))
    assert all(str(error) in notes for error in errors.values())
    assert _r25_probe_other_process(out) == "ACQUIRED"


@pytest.mark.parametrize("failures", [("unlock",), ("close",), ("unlock", "close")])
def test_r25_cleanup_error_without_builder_failure_is_reported(tmp_path, monkeypatch, failures):
    out = tmp_path / "reference"
    with monkeypatch.context() as patch:
        errors = _r25_inject_cleanup_errors(patch, failures)
        with pytest.raises(OSError) as caught:
            with b._reference_writer_scope(out):
                pass
    assert caught.value is errors[failures[0]]
    if len(failures) > 1:
        assert str(errors[failures[1]]) in "\n".join(caught.value.__notes__)
    assert _r25_probe_other_process(out) == "ACQUIRED"


def test_r25_unrelated_outer_exception_does_not_hide_cleanup_failure(tmp_path, monkeypatch):
    # An exception handled by the caller is not a failure of this writer scope.
    # Looking at sys.exception() in finally would conflate those two cases.
    try:
        raise LookupError("already being handled by caller")
    except LookupError:
        with monkeypatch.context() as patch:
            errors = _r25_inject_cleanup_errors(patch, ("unlock",))
            with pytest.raises(OSError) as caught:
                with b._reference_writer_scope(tmp_path / "reference"):
                    pass
    assert caught.value is errors["unlock"]
