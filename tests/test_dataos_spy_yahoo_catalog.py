"""Closed SPY Yahoo intake: synthetic sources, real owner guards, isolated outputs."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date

import pandas as pd
import pytest

from scripts import build_security_master as b
from tests.test_dataos_direct_registrant import (
    build_scratch, intake_input, root_master, root_published, synthetic_captures,
)

DAY = date(2026, 10, 15)
NOW = "2026-10-15T12:00:00+00:00"
READ = "2026-10-15T11:59:59.000001+00:00"


def captured(body, url):
    return {"body": body, "capture": {
        "url": url, "final_url": url, "status": 200, "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "request_started_at": "2026-10-15T11:00:00Z",
        "read_completed_at": "2026-10-15T11:00:01Z",
    }}


def change_body(sources, role, body):
    sources[role]["body"] = body
    sources[role]["capture"].update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())


@pytest.fixture
def sources(synthetic_captures):
    listing = intake_input()
    yahoo = json.dumps({"chart": {"result": [{"meta": {
        **b._SPY_YAHOO_META, "firstTradeDate": 728317800,
    }}], "error": None}}).encode()
    issuer = (
        "<h1>SPY State Street® SPDR® S&amp;P 500® ETF Trust</h1>"
        "<section><h2>Listing Information <span>as of Oct 15 2026</span></h2><table>"
        "<tr><th>Exchange</th><th>Listing Date</th><th>Trading Currency</th>"
        "<th>Ticker</th><th>CUSIP</th><th>ISIN</th></tr>"
        "<tr><td>NYSE ARCA</td><td>Jan 22 1993</td><td>USD</td>"
        "<td>SPY</td><td>78462F103</td><td>US78462F1030</td></tr></table></section>"
    ).encode()
    return {"yahoo": captured(yahoo, b._SPY_YAHOO_URL),
            "issuer": captured(issuer, b._SPY_ISSUER_URL),
            "listing_body": listing["listing_body"],
            "listing_receipt_body": listing["listing_receipt_body"]}


def admit(sources, **changes):
    args = dict(reference_read_completed_at=READ, decision_at=NOW)
    args.update(changes)
    return b.admit_spy_yahoo_catalog(sources, [root_master()], **args)


def files(out):
    return {path.name: path.read_bytes() for path in out.iterdir() if path.is_file()}


def aliases(out):
    return b._read_existing(out / b.ALIASES_NAME, b.ALIAS_COLUMNS, b.ALIAS_DTYPES,
                            allow_missing=b.OPTIONAL_ALIAS_COLUMNS)


@pytest.fixture
def catalog_base(root_published, monkeypatch):
    out, original = root_published
    monkeypatch.setattr(b.time, "time_ns", lambda: b._reference_clock_ns(NOW))
    return out, original


def test_exact_sources_prepare_current_relation_without_store_or_historical_admission(sources):
    row, evidence = admit(sources)
    assert (row.vendor, row.vendor_symbol, row.security_id) == (
        "yahoo_fetch", "SPY", "SEC:US-ARCX-SPY")
    assert row.valid_from == DAY and row.valid_to is None
    assert evidence["admitted_at"] == evidence["decision_at"] == NOW
    assert evidence["source_available_at"] == "2026-10-15T11:00:01+00:00"
    assert evidence["reference_read_completed_at"] == READ
    assert evidence["canonical_target"] == {key: root_master().get(key) for key in b.MASTER_COLUMNS}
    assert evidence["yahoo_first_trade_date"] == 728317800
    assert evidence["issuer_listing"]["listing_date"] == "1993-01-22"
    table = b.VendorAliasTable([row])
    assert table.resolve("yahoo_fetch", "SPY", DAY) == row.security_id
    assert table.resolve("yahoo_fetch", "SPY", date(2026, 10, 14)) is None
    assert table.resolve("store", "SPY", DAY) is None
    assert table.resolve("thetadata", "SPY", DAY) is None
    # Pin the incumbent boundary: a consumer MUST NOT use this generic lookup
    # as proof of a pre-admission cutoff, even if it supplies decision_at.
    assert table.resolve("yahoo_fetch", "SPY", DAY,
                         decision_at="2026-10-15T11:59:59Z") == row.security_id


@pytest.mark.parametrize("field,value", [
    ("symbol", "QQQ"), ("currency", "CAD"), ("exchangeName", "NYQ"),
    ("fullExchangeName", "NYSE"), ("instrumentType", "EQUITY"),
    ("exchangeTimezoneName", "UTC"), ("longName", "Other fund"),
    ("firstTradeDate", True), ("firstTradeDate", None), ("firstTradeDate", 99999999999),
])
def test_yahoo_identity_conflicts_refuse_even_with_recomputed_hash(sources, field, value):
    value_json = json.loads(sources["yahoo"]["body"])
    value_json["chart"]["result"][0]["meta"][field] = value
    change_body(sources, "yahoo", json.dumps(value_json).encode())
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("body", [
    b'{"chart":{},"chart":{}}', b'{"chart":{"result":[],"error":null}}',
    b'{"chart":{"result":null,"error":{"code":"Not Found"}}}', b"[]", b"\xff",
    b'{"chart":{"result":[],"error":null},"number":NaN}',
    b'{"chart":{"result":[],"error":null},"number":1e999}',
    b" " * (2 * 1024 * 1024 + 1),
], ids=["duplicate", "empty", "provider_error", "array", "utf8", "nan", "overflow", "oversize"])
def test_bad_yahoo_shapes_are_typed_refusals(sources, body):
    change_body(sources, "yahoo", body)
    with pytest.raises(b.IdentityError):
        admit(sources)


def test_multiple_yahoo_results_are_not_a_single_identity(sources):
    value = json.loads(sources["yahoo"]["body"])
    value["chart"]["result"] *= 2
    change_body(sources, "yahoo", json.dumps(value).encode())
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("field,value", [
    ("status", 403), ("status", True), ("bytes", True), ("sha256", "0" * 64),
    ("url", "https://example.com/SPY"), ("final_url", "https://example.com/SPY"),
    ("request_started_at", "2026-10-14T11:00:00Z"),
    ("read_completed_at", "2026-10-15T10:59:59Z"),
    ("read_completed_at", "2026-10-15T12:00:00.000001Z"),
    ("read_completed_at", "2026-10-15T11:00:01"),
])
@pytest.mark.parametrize("role", ["yahoo", "issuer"])
def test_exact_capture_and_observation_clocks(sources, role, field, value):
    sources[role]["capture"][field] = value
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("old,new", [
    (b"<td>SPY</td>", b"<td>QQQ</td>"),
    (b"<td>USD</td>", b"<td>CAD</td>"),
    (b"<td>NYSE ARCA</td>", b"<td>NYSE</td>"),
    (b"US78462F1030", b"US0000000000"),
    (b"<td>78462F103</td>", b"<td>000000000</td>"),
    (b"Jan 22 1993", b"Jan 29 1993"),
    (b"as of Oct 15 2026", b"as of Oct 14 2026"),
    (b"S&amp;P 500", b"Other Index"),
])
def test_issuer_relation_cannot_be_assembled_from_conflicting_facts(sources, old, new):
    change_body(sources, "issuer", sources["issuer"]["body"].replace(old, new))
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("change", ["duplicate_row", "duplicate_table", "duplicate_heading",
    "different_section", "split_table", "nested_table", "metadata_only", "missing_title"])
def test_issuer_selection_requires_one_coherent_dated_listing(sources, change):
    body = sources["issuer"]["body"]
    if change == "duplicate_row":
        start = body.index(b"<tr><td>NYSE")
        end = body.index(b"</tr>", start) + 5
        body = body[:end] + body[start:end] + body[end:]
    elif change == "duplicate_table":
        start, end = body.index(b"<table>"), body.index(b"</table>") + 8
        body = body[:end] + body[start:end] + body[end:]
    elif change == "duplicate_heading":
        body += b"<h2>Listing Information as of Oct 15 2026</h2>"
    elif change == "different_section":
        body = body.replace(b"<table>", b"<h2>Other fund</h2><table>")
    elif change == "split_table":
        body = body.replace(b"<tr><td>NYSE", b"</table><table><tr><td>NYSE")
    elif change == "nested_table":
        body = body.replace(b"<table>", b"<table><table>")
    elif change == "metadata_only":
        body = b'<meta name="ticker" content="SPY"><meta name="currency" content="USD">'
    else:
        body = body[body.index(b"</h1>") + 5:]
    change_body(sources, "issuer", body)
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("wrapper", [
    ("script", ""), ("style", ""), ("template", ""), ("div", " hidden"),
    ("div", ' aria-hidden="true"'), ("div", ' style="display: none"'),
])
def test_hidden_issuer_evidence_is_not_a_visible_listing(sources, wrapper):
    tag, attrs = wrapper
    body = f"<{tag}{attrs}>".encode() + sources["issuer"]["body"] + f"</{tag}>".encode()
    change_body(sources, "issuer", body)
    with pytest.raises(b.IdentityError):
        admit(sources)


def test_october_15_collector_cannot_be_redated_by_october_19_public_captures(sources):
    for role in ("yahoo", "issuer"):
        for key in ("request_started_at", "read_completed_at"):
            sources[role]["capture"][key] = sources[role]["capture"][key].replace("10-15", "10-19")
    change_body(sources, "issuer", sources["issuer"]["body"].replace(b"Oct 15", b"Oct 19"))
    original_receipt = sources["listing_receipt_body"]
    with pytest.raises(b.IdentityError):
        admit(sources, decision_at="2026-10-19T12:00:00Z",
              reference_read_completed_at="2026-10-19T11:59:59Z")
    assert sources["listing_receipt_body"] == original_receipt


@pytest.mark.parametrize("change", ["receipt_date", "artifact_bytes", "ineligible"])
def test_redated_or_substituted_listing_evidence_refuses(sources, change):
    if change == "artifact_bytes":
        sources["listing_body"] = sources["listing_body"] + b"changed"
    else:
        value = json.loads(sources["listing_receipt_body"])
        if change == "receipt_date":
            value["observation_date"] = "2026-10-19"
        else:
            value["authority"]["listing_identity_observation_eligible"] = False
        sources["listing_receipt_body"] = json.dumps(value).encode()
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("changes", [
    {"decision_at": "2026-10-15T11:00:00.999999Z"},
    {"decision_at": "2026-10-16T12:00:00Z"},
    {"reference_read_completed_at": "2026-10-15T12:00:00.000001Z"},
    {"reference_read_completed_at": "2026-10-15T00:59:59Z"},
    {"reference_read_completed_at": "2026-10-15T11:59:59"},
])
def test_admission_cannot_precede_required_source_or_canonical_reads(sources, changes):
    with pytest.raises(b.IdentityError):
        admit(sources, **changes)


def test_equivalent_offsets_produce_same_decision(sources):
    _, evidence = admit(sources, decision_at="2026-10-15T08:00:00-04:00")
    assert evidence["admitted_at"] == NOW


@pytest.mark.parametrize("field,value", [
    ("security_id", "SEC:US-XNYS-OTHER"), ("security_state", "SUPERSEDED"),
    ("superseded_by", "SEC:US-XNYS-OTHER"), ("listing_key", "US-XNYS-SPY"),
    ("country", "CA"), ("mic", "XNYS"), ("inception_code", "QQQ"),
    ("effective_at", "2026-10-16T00:00:00"), ("ingested_at", "2026-10-15T13:00:00"),
    ("effective_at", None),
])
def test_canonical_identity_must_already_exist_and_be_active(sources, field, value):
    master = root_master()
    master[field] = value
    with pytest.raises(b.IdentityError):
        b.admit_spy_yahoo_catalog(sources, [master],
            reference_read_completed_at=READ, decision_at=NOW)


@pytest.mark.parametrize("masters", [[], [root_master(), root_master()], None, [None]])
def test_missing_or_ambiguous_master_never_mints(sources, masters):
    with pytest.raises(b.IdentityError):
        b.admit_spy_yahoo_catalog(sources, masters,
            reference_read_completed_at=READ, decision_at=NOW)


def test_full_builder_adds_only_one_alias_and_preserves_four_tables_and_prior_evidence(catalog_base, sources):
    out, original = catalog_base
    before, old = files(out), aliases(out)
    previous_receipt = json.loads(before[b.RECEIPT_NAME])
    result = b.build(out, spy_yahoo_catalog_input=sources)
    new = aliases(out)
    assert len(new) == len(old) + 1 and all(row in new for row in old)
    for name, body in before.items():
        if name not in {b.ALIASES_NAME, b.RECEIPT_NAME}:
            assert (out / name).read_bytes() == body
    assert result["prospective_reference"] == original
    assert result["direct_registrant_intake"] == previous_receipt["direct_registrant_intake"]
    assert result["spy_yahoo_catalog"]["canonical_reference_preimage"] == {
        name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        for name, body in before.items()
        if name in (*b._NIGHTLY_ARTIFACT_NAMES, b.RECEIPT_NAME)
    }
    assert b.VendorAliasTable.from_records(new).resolve("store", "SPY", DAY) is None
    saved = files(out)
    again = b.build(out)
    assert again["spy_yahoo_catalog"] == result["spy_yahoo_catalog"]
    assert aliases(out) == new
    with pytest.raises(b.IdentityError, match="no replay"):
        b.build(out, spy_yahoo_catalog_input=sources)
    assert files(out) == saved


def test_dry_run_writes_no_reference_outputs(catalog_base, sources):
    out, _ = catalog_base
    before = files(out)
    result = b.build(out, dry_run=True, spy_yahoo_catalog_input=sources)
    assert result["spy_yahoo_catalog"]["security_id"] == "SEC:US-ARCX-SPY"
    assert files(out) == before


@pytest.mark.parametrize("change", ["missing_target", "retired_target", "current_listing",
    "listing_bytes", "ordinary_alias_change", "existing_relation", "combined"])
def test_full_builder_refuses_scope_escape_before_outputs(catalog_base, sources, monkeypatch, tmp_path, change):
    out, _ = catalog_base
    if change in {"missing_target", "retired_target"}:
        rows = b._read_existing(out / b.MASTER_NAME, b.MASTER_COLUMNS, b.MASTER_DTYPES)
        if change == "missing_target":
            rows = [row for row in rows if row["inception_code"] != "SPY"]
        else:
            next(row for row in rows if row["inception_code"] == "SPY").update(
                security_state="SUPERSEDED", superseded_by="SEC:US-XNYS-OTHER")
        b._write_parquet(rows, b.MASTER_COLUMNS, out / b.MASTER_NAME, b.MASTER_DTYPES)
    elif change in {"current_listing", "listing_bytes"}:
        mapping, flags, day, path = b.load_directory()
        if change == "current_listing":
            mapping = dict(mapping)
            mapping.pop("SPY")
        else:
            path = tmp_path / "different.parquet"
            path.write_bytes(sources["listing_body"] + b"changed")
        monkeypatch.setattr(b, "load_directory", lambda: (mapping, flags, day, path))
    elif change == "ordinary_alias_change":
        owner = b.build_alias_rows
        monkeypatch.setattr(b, "build_alias_rows", lambda *a, **kw:
                            owner(*a, **kw) + [b.AliasRow("yahoo", "EXTRA", "SEC:US-ARCX-SPY")])
    elif change == "existing_relation":
        rows = aliases(out) + [dict(vendor="yahoo_fetch", vendor_symbol="SPY",
            security_id="SEC:US-ARCX-SPY", valid_from=None, valid_to=None,
            ingested_at="2026-10-15T10:00:00", known_at=None, evidence_sha256=None,
            binding_sha256=None, alias_kind=None)]
        b._write_parquet(rows, b.ALIAS_COLUMNS, out / b.ALIASES_NAME, b.ALIAS_DTYPES)
    before = files(out)
    with pytest.raises(b.IdentityError):
        b.build(out, spy_yahoo_catalog_input=sources,
                spy_option_root_input={} if change == "combined" else None)
    assert files(out) == before


@pytest.mark.parametrize("change", ["missing", "null", "altered_clock", "altered_scope", "alias_seal"])
def test_retained_evidence_is_not_silently_dropped_or_refreshed(catalog_base, sources, change):
    out, _ = catalog_base
    b.build(out, spy_yahoo_catalog_input=sources)
    path = out / b.RECEIPT_NAME
    value = json.loads(path.read_bytes())
    if change == "missing":
        del value["spy_yahoo_catalog"]
    elif change == "null":
        value["spy_yahoo_catalog"] = None
    elif change == "altered_clock":
        value["spy_yahoo_catalog"]["admitted_at"] = "2026-10-14T12:00:00Z"
    elif change == "altered_scope":
        value["spy_yahoo_catalog"]["scope"] = "historical"
    else:
        rows = aliases(out)
        next(row for row in rows if row["vendor"] == "yahoo_fetch" and row["vendor_symbol"] == "SPY")[
            "binding_sha256"] = "0" * 64
        b._write_parquet(rows, b.ALIAS_COLUMNS, out / b.ALIASES_NAME, b.ALIAS_DTYPES)
    path.write_text(json.dumps(value))
    before = files(out)
    with pytest.raises(b.IdentityError):
        b.build(out)
    assert files(out) == before


def manifest(tmp_path, sources):
    value = copy.deepcopy(sources)
    for role in ("yahoo", "issuer"):
        name = role + ".dat"
        (tmp_path / name).write_bytes(value[role]["body"])
        value[role]["body"] = name
    for role in ("listing_body", "listing_receipt_body"):
        name = role + ".dat"
        (tmp_path / name).write_bytes(value[role])
        value[role] = name
    path = tmp_path / "spy-yahoo-input.json"
    path.write_text(json.dumps({"schema": "mastermind.spy_yahoo_catalog_input.v1", "sources": value}))
    return path


def test_explicit_cli_and_source_reader(catalog_base, sources, tmp_path):
    out, _ = catalog_base
    path = manifest(tmp_path, sources)
    assert b.main(["--out", str(out), "--spy-yahoo-catalog-evidence", str(path)]) == 0
    assert json.loads((out / b.RECEIPT_NAME).read_bytes())["spy_yahoo_catalog"]["admitted_at"] == NOW


@pytest.mark.parametrize("change", ["duplicate", "wrong_schema", "traversal", "missing", "symlink", "nightly"])
def test_manifest_cannot_fetch_traverse_or_become_a_nightly_intake(sources, tmp_path, change, monkeypatch):
    path = manifest(tmp_path, sources)
    if change == "nightly":
        calls = []
        monkeypatch.setattr(b, "run_nightly_refresh", lambda *a: calls.append(a))
        with pytest.raises(SystemExit) as exc:
            b.main(["--nightly", "--spy-yahoo-catalog-evidence", str(path)])
        assert exc.value.code == 2 and not calls
        return
    if change == "duplicate":
        path.write_text('{"schema":1,"schema":2}')
    elif change == "missing":
        (tmp_path / "issuer.dat").unlink()
    elif change == "symlink":
        source = tmp_path / "issuer.dat"
        source.rename(tmp_path / "original.dat")
        source.symlink_to(tmp_path / "original.dat")
    else:
        value = json.loads(path.read_bytes())
        if change == "wrong_schema":
            value["schema"] = "unknown"
        else:
            value["sources"]["issuer"]["body"] = "../outside.dat"
        path.write_text(json.dumps(value))
    with pytest.raises(b.IdentityError):
        b.read_spy_yahoo_catalog_input(path)


@pytest.mark.parametrize("change", [
    "duplicate_hidden_attribute", "duplicate_attribute_reversed", "hidden_bad_end",
    "detached_archived_section", "detached_unlabelled_section", "intervening_heading",
])
def test_issuer_structure_ambiguity_refuses_after_exact_capture_rebinding(sources, change):
    body = sources["issuer"]["body"]
    if change == "duplicate_hidden_attribute":
        body = b'<div style="display:none" style="">' + body + b"</div>"
    elif change == "duplicate_attribute_reversed":
        body = b'<div style="" style="display:none">' + body + b"</div>"
    elif change == "hidden_bad_end":
        body = b"<div hidden></span>" + body + b"</div>"
    elif change == "intervening_heading":
        body = body.replace(b"<table>", b"<h3>Archived listing</h3><table>")
    else:
        start, end = body.index(b"<table>"), body.index(b"</table>") + len(b"</table>")
        label = b"<h3>Archived listing</h3>" if change == "detached_archived_section" else b""
        body = body[:start] + b"</section><section>" + label + body[start:end] + b"</section>"
    change_body(sources, "issuer", body)
    with pytest.raises(b.IdentityError):
        admit(sources)


@pytest.mark.parametrize("change", [
    "missing_sources", "missing_listing", "missing_issuer_listing", "missing_yahoo_identity",
    "missing_canonical_target", "missing_canonical_reference_preimage", "missing_all_source_blocks",
    "extra_role", "wrong_url", "failed_status", "boolean_bytes", "bad_source_digest",
    "future_source", "submicrosecond_clock", "availability_not_maximum", "future_collector",
    "yahoo_identity", "issuer_isin", "listing_identity", "canonical_identity", "canonical_fields",
    "empty_preimage", "extra_preimage", "zero_preimage_bytes", "bad_preimage_digest",
    "scope", "limits",
])
def test_resealed_unconstructable_retained_evidence_refuses_before_writes(catalog_base, sources, change):
    out, _ = catalog_base
    b.build(out, spy_yahoo_catalog_input=sources)
    path = out / b.RECEIPT_NAME
    receipt = json.loads(path.read_bytes())
    evidence = receipt["spy_yahoo_catalog"]
    if change == "missing_all_source_blocks":
        for name in ("sources", "listing", "issuer_listing", "yahoo_identity",
                     "canonical_target", "canonical_reference_preimage"):
            del evidence[name]
    elif change.startswith("missing_"):
        del evidence[change.removeprefix("missing_")]
    elif change == "extra_role":
        evidence["sources"]["unreviewed"] = copy.deepcopy(evidence["sources"]["issuer"])
    elif change == "wrong_url":
        evidence["sources"]["yahoo"]["url"] = "https://example.invalid/SPY"
    elif change == "failed_status":
        evidence["sources"]["issuer"]["status"] = 403
    elif change == "boolean_bytes":
        evidence["sources"]["yahoo"]["bytes"] = True
    elif change == "bad_source_digest":
        evidence["sources"]["issuer"]["sha256"] = "not-a-digest"
    elif change == "future_source":
        evidence["sources"]["issuer"]["read_completed_at"] = "2026-10-15T12:00:01Z"
    elif change == "submicrosecond_clock":
        evidence["sources"]["issuer"]["read_completed_at"] = "2026-10-15T11:00:01.0000001Z"
    elif change == "availability_not_maximum":
        evidence["source_available_at"] = "2026-10-15T11:00:00+00:00"
    elif change == "future_collector":
        evidence["listing"]["collector_completed_at"] = "2026-10-15T12:00:01Z"
    elif change == "yahoo_identity":
        evidence["yahoo_identity"]["instrumentType"] = "EQUITY"
    elif change == "issuer_isin":
        evidence["issuer_listing"]["isin"] = "US0000000000"
    elif change == "listing_identity":
        evidence["listing"]["listing_key"] = "US-XNAS-SPY"
    elif change == "canonical_identity":
        evidence["canonical_target"]["issuer_id"] = "ISS:UNADMITTED"
    elif change == "canonical_fields":
        del evidence["canonical_target"]["issuer_state"]
    elif change == "empty_preimage":
        evidence["canonical_reference_preimage"] = {}
    elif change == "extra_preimage":
        evidence["canonical_reference_preimage"]["unreviewed.parquet"] = {"bytes": 1, "sha256": "a" * 64}
    elif change == "zero_preimage_bytes":
        evidence["canonical_reference_preimage"][b.MASTER_NAME]["bytes"] = 0
    elif change == "bad_preimage_digest":
        evidence["canonical_reference_preimage"][b.RECEIPT_NAME]["sha256"] = "B" * 64
    elif change == "scope":
        evidence["scope"] = "historical"
    elif change == "limits":
        evidence["limits"] = []
    else:
        raise AssertionError(change)
    # Recompute BOTH checksums. A matching seal must not bypass the semantic owner.
    digest = hashlib.sha256((json.dumps(evidence, indent=2, sort_keys=True,
                                        allow_nan=False) + "\n").encode()).hexdigest()
    rows = aliases(out)
    row = next(r for r in rows if r["vendor"] == "yahoo_fetch" and r["vendor_symbol"] == "SPY")
    row["evidence_sha256"] = digest
    row["binding_sha256"] = b.alias_binding_sha256(
        "yahoo_fetch", "SPY", "SEC:US-ARCX-SPY", DAY, None, row["known_at"], digest)
    b._write_parquet(rows, b.ALIAS_COLUMNS, out / b.ALIASES_NAME, b.ALIAS_DTYPES)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    before = files(out)
    with pytest.raises(b.IdentityError):
        b.build(out)
    assert files(out) == before


@pytest.mark.parametrize("change", ["missing", "duplicate", "retired", "changed"])
def test_retention_requires_the_same_active_current_canonical_target(catalog_base, sources, change):
    out, _ = catalog_base
    result = b.build(out, spy_yahoo_catalog_input=sources)
    records = b._read_existing(out / b.MASTER_NAME, b.MASTER_COLUMNS, b.MASTER_DTYPES)
    target = next(row for row in records if row["security_id"] == "SEC:US-ARCX-SPY")
    if change == "missing":
        records.remove(target)
    elif change == "duplicate":
        records.append(dict(target))
    elif change == "retired":
        target.update(security_state="SUPERSEDED_DUPLICATE_MINT", superseded_by="SEC:US-XNAS-SPY")
    else:
        target["issuer_id"] = "ISS:UNADMITTED"
    with pytest.raises(b.IdentityError):
        b._validate_spy_yahoo_catalog_retention(result["spy_yahoo_catalog"], aliases(out), records)
