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
