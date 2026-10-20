"""Closed SPY consumer boundaries with synthetic facts and real owner semantics.

Intended location: Macro tests/test_terminal_spy_yahoo_materialization.py.
These tests use the shared helper, canonical alias reader, and canonical seal.
They make no source capture or publication claim and write no reference data.
The stock golden remains the existing tests/terminal_materialization_golden.json.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.dataos import _spy_yahoo_catalog as spy  # noqa: E402
from lib.dataos import terminal_materialization as tdm  # noqa: E402
from lib.dataos.identity import (  # noqa: E402
    VendorAliasTable, alias_binding_sha256, parse_listing_key,
)

GOLDEN_PATH = ROOT / "tests" / "terminal_materialization_golden.json"
DAY = date(2026, 10, 19)
OBSERVED = "2026-10-19T03:59:59.999999+00:00"  # Oct 18, just before NY midnight.
ADMITTED = "2026-10-19T04:00:00.000001+00:00"
CURRENT_READ = "2026-10-19T04:00:00.000002+00:00"
MATERIALIZED = "2026-10-19T04:00:00.000003+00:00"
SPY_ID = "SEC:US-ARCX-SPY"
SPY_OWNER_FILES = (
    "lib/dataos/terminal_materialization.py", "lib/dataos/identity.py", "lib/dataos/_spy_yahoo_catalog.py",
)
ADMISSION_FILES = (
    "security_master.parquet", "vendor_aliases.parquet", "issuer_master.parquet",
    "issuer_migrations.parquet", "security_migrations.parquet", "_receipt.json",
)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _document(symbol="SPY", requested="SPY", *, observed=OBSERVED, last="2026-10-16"):
    rows = [["2026-10-15", 100.0, 101.5, 99.5, 101.0, 0],
            [last, 101.0, 103.0, 100.75, 102.125, 12000]]
    return {
        "t": symbol, "src": "yahoo", "bar_quality": "real_ohlc", "bars": rows,
        "source_observation": {
            "producer": tdm.PRODUCER_PATH, "provider": "yahoo", "observed_at": observed,
            "request": {"adapter": "yfinance", "period": "max", "interval": "1d",
                        "auto_adjust": True, "symbol": requested,
                        "session_dates": "exchange_local", "index_timezone": "America/New_York"},
            "adapter_version": "fixture-1",
            "coverage": {"first": rows[0][0], "last": rows[-1][0], "rows": len(rows)},
            "digest_codec": "python.json.compact.v1",
            "bars_sha256": _digest(json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()),
            "qualification": "OBSERVATION_ONLY", "historical_availability": "UNATTESTED",
        },
    }


def _catalog():
    master = {key: None for key in spy.MASTER_COLUMNS}
    master.update(security_id=SPY_ID, listing_key="US-ARCX-SPY", country="US", mic="ARCX",
                  inception_code="SPY", effective_at="2026-10-19T01:00:00",
                  ingested_at="2026-10-19T01:00:00")
    evidence = {
        "schema": spy._SPY_YAHOO_SCHEMA, "vendor": "yahoo_fetch", "symbol": "SPY",
        "security_id": SPY_ID, "valid_from": DAY.isoformat(), "valid_to": None,
        "known_at": ADMITTED, "decision_at": ADMITTED, "admitted_at": ADMITTED,
        "source_available_at": "2026-10-19T02:00:02+00:00",
        "reference_read_completed_at": "2026-10-19T03:00:00.000001+00:00",
        "sources": {}, "yahoo_identity": dict(spy._SPY_YAHOO_META),
        "yahoo_first_trade_date": 728317800,
        "issuer_listing": {
            "fund_name": spy._SPY_YAHOO_META["longName"], "observed_on": DAY.isoformat(),
            "exchange": "NYSE ARCA", "currency": "USD", "symbol": "SPY",
            "listing_date": "1993-01-22", "cusip": "78462F103", "isin": "US78462F1030",
        },
        "listing": {
            "symbol": "SPY", "listing_key": "US-ARCX-SPY", "observed_on": DAY.isoformat(),
            "listing_snapshot_sha256": _digest(b"synthetic listing capture"),
            "listing_receipt_sha256": _digest(b"synthetic listing receipt"),
            "collector_completed_at": "2026-10-19T02:00:02+00:00",
        },
        "canonical_target": master, "scope": spy._SPY_YAHOO_SCOPE,
        "limits": list(spy._SPY_YAHOO_LIMITS),
        "canonical_reference_preimage": {
            name: {"bytes": len("before admission " + name),
                   "sha256": _digest(("before admission " + name).encode())}
            for name in ADMISSION_FILES
        },
    }
    for role, url in (("yahoo", spy._SPY_YAHOO_URL), ("issuer", spy._SPY_ISSUER_URL)):
        body = ("synthetic " + role + " capture").encode()
        evidence["sources"][role] = {
            "url": url, "final_url": url, "status": 200, "bytes": len(body), "sha256": _digest(body),
            "request_started_at": "2026-10-19T02:00:00+00:00",
            "read_completed_at": "2026-10-19T02:00:01+00:00",
        }
    return evidence


def _reseal(case):
    """Use the real canonical seal, including when a test corrupts source facts."""
    evidence = case["catalog_evidence"]
    digest = spy.evidence_sha256(evidence)
    start = date.fromisoformat(evidence["valid_from"])
    row = {
        "vendor": "yahoo_fetch", "vendor_symbol": "SPY", "security_id": SPY_ID,
        "valid_from": start.isoformat(), "valid_to": None, "known_at": evidence["known_at"],
        "evidence_sha256": digest,
        "binding_sha256": alias_binding_sha256(
            "yahoo_fetch", "SPY", SPY_ID, start, None, evidence["known_at"], digest),
        "alias_kind": None,
    }
    case["alias_records"] = [row]
    receipt = {"spy_yahoo_catalog": evidence, "fixture_prior_family": {"preserved": True}}
    case["reference"]["files_sha256"]["_receipt.json"] = _digest(
        json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False).encode())


@pytest.fixture
def case():
    evidence = _catalog()
    result = {
        "document": _document(), "catalog_evidence": evidence,
        "master_records": [deepcopy(evidence["canonical_target"])], "alias_records": [],
        "producer_version": {
            "repository": "mastermindx-market-intelligence/mastermind-terminal", "commit": None,
            "files_sha256": {path: "a" * 64 for path in tdm.PRODUCER_FILES},
        },
        "owner_version": {
            "repository": "mastermindx-market-intelligence/macro", "commit": None,
            "files_sha256": {path: "c" * 64 for path in SPY_OWNER_FILES},
        },
        "reference": {
            "files_sha256": {name: _digest(("current " + name).encode())
                             for name in tdm.SPY_REFERENCE_FILES},
            "read_at": CURRENT_READ, "generation_id": None, "generation_attested": False,
        },
        "materialized_at": MATERIALIZED,
    }
    _reseal(result)
    return result


def _bind(case, **overrides):
    args = {key: case[key] for key in (
        "alias_records", "master_records", "producer_version", "owner_version",
        "reference", "catalog_evidence", "materialized_at")}
    args.update(alias_table=VendorAliasTable.from_records(case["alias_records"]),
                parse_listing_key=parse_listing_key, alias_binding_sha256=alias_binding_sha256,
                spy_catalog=spy)
    args.update(overrides)
    return tdm.bind_terminal_spy_yahoo_materialization(case["document"], **args)


def _stock_arguments(aliases, master):
    return {
        "alias_table": VendorAliasTable.from_records(aliases), "master_records": master,
        "parse_listing_key": parse_listing_key,
        "producer_version": {"repository": "mastermindx-market-intelligence/mastermind-terminal",
                             "commit": None, "files_sha256": {p: "a" * 64 for p in tdm.PRODUCER_FILES}},
        "owner_version": {"repository": "mastermindx-market-intelligence/macro", "commit": "b" * 40,
                          "files_sha256": {p: "c" * 64 for p in (tdm.OWNER_PATH, tdm.IDENTITY_PATH)}},
        "reference": {"files_sha256": {p: "d" * 64 for p in tdm.REFERENCE_FILES},
                      "read_at": "2026-10-17T00:00:01Z", "generation_id": None,
                      "generation_attested": False},
    }


def _refused(result, code):
    assert result == {"status": "refused", "view": None, "refusal_reasons": [code]}


def test_spy_later_qualification_uses_complete_admission_and_current_triplet(case):
    before = deepcopy(case)
    table = VendorAliasTable.from_records(case["alias_records"])
    assert table.resolve("store", "SPY", DAY) is None
    assert table.resolve("yahoo_fetch", "SPY", date(2026, 10, 18)) is None
    assert table.resolve("yahoo_fetch", "SPY", DAY) == SPY_ID
    result = _bind(case)
    assert result["status"] == "bound", result
    assert case == before
    contract = result["view"]["contract"]
    materialization = contract["materialization"]
    assert materialization["schema"] == "dataos.terminal_spy_yahoo_materialization.v1"
    assert materialization["observed_at"] == OBSERVED
    assert materialization["materialized_at"] == MATERIALIZED
    assert contract["evidence_mode"]["clock"] == "materialized_at"
    assert contract["evidence_mode"]["mode"] == "CURRENT"
    assert materialization["historical_availability"] == "UNATTESTED"
    assert contract["evidence_mode"]["generation_attested"] is False
    assert contract["evidence_mode"]["dependency_generation_ids"] == []
    assert contract["adjustment_reference"]["executable"] is False
    assert contract["adjustment_reference"]["action_revision_set_id"] is None
    assert result["view"]["listing"] == {
        "security_id": SPY_ID, "listing_key": "US-ARCX-SPY", "mic": "ARCX"}
    summary = {key: case["catalog_evidence"][key] for key in (
        "schema", "vendor", "symbol", "security_id", "valid_from", "valid_to", "known_at",
        "admitted_at", "source_available_at", "reference_read_completed_at")}
    summary.update(evidence_sha256=spy.evidence_sha256(case["catalog_evidence"]),
                   binding_sha256=case["alias_records"][0]["binding_sha256"])
    assert materialization["catalog_admission"] == summary
    preimage = case["catalog_evidence"]["canonical_reference_preimage"]
    current = materialization["identity_reference"]
    assert set(preimage) == set(ADMISSION_FILES)
    assert set(current["files_sha256"]) == {"security_master.parquet", "vendor_aliases.parquet", "_receipt.json"}
    assert current["files_sha256"] == case["reference"]["files_sha256"]
    assert all(preimage[name]["sha256"] != current["files_sha256"][name]
               for name in tdm.SPY_REFERENCE_FILES)
    assert current["read_at"] == CURRENT_READ
    assert current["read_at"] != summary["reference_read_completed_at"]


@pytest.mark.parametrize("read_clock", [
    "2026-10-19T04:00:00.000001001+00:00",
    "2026-10-19T04:00:00,000001001+00:00",
])
def test_shared_retention_cannot_floor_reference_read_past_admission(case, read_clock):
    # Both clocks are one nanosecond after admission. Resealing must not turn
    # impossible ordering into admissible retained evidence through truncation.
    case["catalog_evidence"]["reference_read_completed_at"] = read_clock
    _reseal(case)
    with pytest.raises(spy.SpyCatalogError):
        spy.validate_retained(
            case["catalog_evidence"], case["alias_records"], case["master_records"],
            alias_binding_sha256=alias_binding_sha256, latest_at=CURRENT_READ,
        )
    # The shared catalog validator now rejects the malformed retained evidence
    # before the named materializer reaches its separate publication-clock checks.
    result = _bind(case)
    assert result["status"] == "refused"
    assert result["refusal_reasons"] == ["MATERIALIZATION_SPY_CATALOG_INVALID"]


def test_shared_retention_allows_exact_microsecond_admission_read_boundary(case):
    case["catalog_evidence"]["reference_read_completed_at"] = ADMITTED
    _reseal(case)
    spy.validate_retained(
        case["catalog_evidence"], case["alias_records"], case["master_records"],
        alias_binding_sha256=alias_binding_sha256, latest_at=CURRENT_READ,
    )
    assert _bind(case)["status"] == "bound"


def test_spy_exact_admission_read_and_materialization_boundary_is_valid(case):
    case["reference"]["read_at"] = ADMITTED
    case["materialized_at"] = ADMITTED
    assert _bind(case)["status"] == "bound"


@pytest.mark.parametrize("fault,code", [
    ("read_before_admission", "MATERIALIZATION_SPY_CATALOG_INVALID"),
    ("materialized_before_read", "MATERIALIZATION_CLOCK_INVALID"),
    ("observed_after_materialized", "MATERIALIZATION_CLOCK_INVALID"),
    ("submicrosecond_read", "MATERIALIZATION_CLOCK_INVALID"),
    ("submicrosecond_observation", "MATERIALIZATION_CLOCK_INVALID"),
    ("submicrosecond_materialization", "MATERIALIZATION_CLOCK_INVALID"),
])
def test_spy_critical_clock_boundaries_cannot_be_advanced_or_floored(case, fault, code):
    if fault == "read_before_admission":
        case["reference"]["read_at"] = "2026-10-19T04:00:00+00:00"
    elif fault == "materialized_before_read":
        case["materialized_at"] = ADMITTED
    elif fault == "observed_after_materialized":
        case["document"]["source_observation"]["observed_at"] = "2026-10-19T04:00:00.000004+00:00"
    elif fault == "submicrosecond_read":
        case["reference"]["read_at"] = "2026-10-19T04:00:00.000003001+00:00"
    elif fault == "submicrosecond_observation":
        case["document"]["source_observation"]["observed_at"] = "2026-10-19T04:00:00.000003001+00:00"
    else:
        case["materialized_at"] = "2026-10-19T04:00:00.000003001+00:00"
    _refused(_bind(case), code)


def test_spy_later_admission_cannot_excuse_a_bar_future_dated_at_observation(case):
    case["document"] = _document(last="2026-10-19")
    _refused(_bind(case), "MATERIALIZATION_CLOCK_INVALID")
    case["document"] = _document(observed="2026-10-19T04:00:00+00:00", last="2026-10-19")
    assert _bind(case)["status"] == "bound"


def test_spy_catalog_day_uses_utc_even_when_materialization_offset_names_prior_local_day(case):
    # This is the same valid instant as MATERIALIZED, represented west of UTC.
    case["materialized_at"] = "2026-10-18T23:00:00.000003-05:00"
    assert _bind(case)["status"] == "bound"


@pytest.mark.parametrize("missing", ["none", "empty", "no_catalog_and_no_alias"])
def test_spy_needs_positive_catalog_evidence_even_when_builder_absence_would_be_valid(case, missing):
    case["catalog_evidence"] = {} if missing == "empty" else None
    if missing == "no_catalog_and_no_alias":
        case["alias_records"] = []
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")


@pytest.mark.parametrize("fault", ["missing_sources", "wrong_instrument", "missing_preimage", "three_file_preimage"])
def test_spy_resealed_catalog_still_requires_all_reviewed_source_semantics(case, fault):
    evidence = case["catalog_evidence"]
    if fault == "missing_sources":
        del evidence["sources"]
    elif fault == "wrong_instrument":
        evidence["yahoo_identity"]["instrumentType"] = "EQUITY"
    elif fault == "missing_preimage":
        del evidence["canonical_reference_preimage"]
    else:
        evidence["canonical_reference_preimage"] = {
            name: evidence["canonical_reference_preimage"][name] for name in tdm.SPY_REFERENCE_FILES}
    _reseal(case)
    # The real current-catalog reader alone still resolves this fully resealed row.
    assert VendorAliasTable.from_records(case["alias_records"]).resolve("yahoo_fetch", "SPY", DAY) == SPY_ID
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")


@pytest.mark.parametrize("field", ["evidence_sha256", "binding_sha256"])
def test_spy_generic_resolver_success_does_not_replace_the_catalog_seal(case, field):
    case["alias_records"][0][field] = "0" * 64
    assert VendorAliasTable.from_records(case["alias_records"]).resolve("yahoo_fetch", "SPY", DAY) == SPY_ID
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")


@pytest.mark.parametrize("fault", ["missing", "changed", "retired"])
def test_spy_current_canonical_target_must_remain_the_admitted_target(case, fault):
    if fault == "missing":
        case["master_records"] = []
    elif fault == "changed":
        case["master_records"][0]["issuer_id"] = "ISS:DIFFERENT"
    else:
        case["master_records"][0]["security_state"] = "SUPERSEDED_DUPLICATE_MINT"
        case["master_records"][0]["superseded_by"] = "SEC:US-ARCX-OTHER"
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")


@pytest.mark.parametrize("fault", ["ingested_after_original_read", "effective_after_ingested"])
def test_spy_resealed_canonical_nanoseconds_cannot_cross_an_availability_cutoff(case, fault):
    target = case["catalog_evidence"]["canonical_target"]
    if fault == "ingested_after_original_read":
        target["ingested_at"] = "2026-10-19T03:00:00.000001001"
    else:
        target["effective_at"] = "2026-10-19T01:00:00.000000001"
    case["master_records"] = [deepcopy(target)]
    _reseal(case)
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")


@pytest.mark.parametrize("symbol,requested", [("ETFPROXY", "SPY"), ("SPY", "ETFPROXY"), ("ETFPROXY", "ETFPROXY")])
def test_named_spy_leaf_cannot_relabel_another_output_or_request(case, symbol, requested):
    case["document"] = _document(symbol, requested)
    _refused(_bind(case), "MATERIALIZATION_IDENTITY_UNRESOLVED")


@pytest.mark.parametrize("fault,code", [
    ("owner_without_helper", "MATERIALIZATION_CODE_UNATTESTED"),
    ("owner_with_extra_source", "MATERIALIZATION_CODE_UNATTESTED"),
    ("producer_without_adapter", "MATERIALIZATION_CODE_UNATTESTED"),
    ("current_pair_only", "MATERIALIZATION_REFERENCE_UNAVAILABLE"),
    ("preimage_as_current_reference", "MATERIALIZATION_REFERENCE_UNAVAILABLE"),
    ("invented_generation", "MATERIALIZATION_REFERENCE_UNAVAILABLE"),
])
def test_spy_requires_its_exact_owner_source_and_current_reference_profiles(case, fault, code):
    if fault == "owner_without_helper":
        del case["owner_version"]["files_sha256"][tdm.SPY_HELPER_PATH]
    elif fault == "owner_with_extra_source":
        case["owner_version"]["files_sha256"]["scripts/unreviewed_owner.py"] = "e" * 64
    elif fault == "producer_without_adapter":
        del case["producer_version"]["files_sha256"]["ingest/dataos_materialization.py"]
    elif fault == "current_pair_only":
        del case["reference"]["files_sha256"]["_receipt.json"]
    elif fault == "preimage_as_current_reference":
        case["reference"]["files_sha256"] = {
            name: record["sha256"] for name, record in case["catalog_evidence"]["canonical_reference_preimage"].items()}
    else:
        case["reference"].update(generation_id="invented-generation", generation_attested=True)
    _refused(_bind(case), code)


def test_spy_owner_code_version_includes_helper_bytes(case):
    first = _bind(case)["view"]["contract"]["materialization"]
    assert set(first["owner"]["files_sha256"]) == set(SPY_OWNER_FILES)
    assert set(first["producer"]["files_sha256"]) == set(tdm.PRODUCER_FILES)
    case["owner_version"]["files_sha256"][tdm.SPY_HELPER_PATH] = "e" * 64
    second = _bind(case)["view"]["contract"]["materialization"]
    expected = "sha256:" + _digest(json.dumps(
        case["owner_version"]["files_sha256"], sort_keys=True, separators=(",", ":")).encode())
    assert second["owner"]["code_version"] == expected
    assert second["owner"]["code_version"] != first["owner"]["code_version"]


@pytest.mark.parametrize("symbol,requested,security,listing", [
    ("SPY", "SPY", "SEC:US-ARCX-SPY", "US-ARCX-SPY"),
    ("ETFPROXY", "SPY", "SEC:US-ARCX-SPY", "US-ARCX-SPY"),
    ("SPY", "ETFPROXY", "SEC:US-ARCX-SPY", "US-ARCX-SPY"),
    ("ETFPROXY", "ETFPROXY", "SEC:US-ARCX-SPY", "US-ARCX-SPY"),
    ("ETFPROXY", "ETFPROXY", "SEC:US-ARCX-OTHER", "US-ARCX-SPY"),
    ("ETFPROXY", "ETFPROXY", "SEC:US-XNYS-SPY", "US-XNYS-SPY"),
])
def test_stock_cannot_qualify_spy_through_a_forged_store_alias(symbol, requested, security, listing):
    document = _document(symbol, requested)
    aliases = [{"vendor": vendor, "vendor_symbol": token, "security_id": security}
               for vendor, token in (("store", symbol), ("yahoo_fetch", requested))]
    master = [{"security_id": security, "listing_key": listing,
               "country": "US", "mic": parse_listing_key(listing).mic,
               "inception_code": "SPY", "superseded_by": None}]
    arguments = _stock_arguments(aliases, master)
    assert arguments["alias_table"].resolve("store", symbol, DAY) == security
    assert arguments["alias_table"].resolve("yahoo_fetch", requested, DAY) == security
    _refused(tdm.bind_terminal_yahoo_materialization(document, **arguments), "MATERIALIZATION_SPY_PROFILE_REQUIRED")


def test_resealed_invalid_spy_cannot_fall_back_to_stock_even_with_both_aliases(case):
    case["catalog_evidence"]["yahoo_identity"]["instrumentType"] = "EQUITY"
    _reseal(case)
    case["alias_records"].append({"vendor": "store", "vendor_symbol": "SPY", "security_id": SPY_ID})
    _refused(_bind(case), "MATERIALIZATION_SPY_CATALOG_INVALID")
    arguments = _stock_arguments(case["alias_records"], case["master_records"])
    _refused(tdm.bind_terminal_yahoo_materialization(case["document"], **arguments), "MATERIALIZATION_SPY_PROFILE_REQUIRED")


def test_stock_golden_and_legacy_owner_reference_profiles_remain_unchanged():
    golden = json.loads(GOLDEN_PATH.read_bytes())
    document = deepcopy(golden["document"])
    expected = document.pop("view")
    aliases = [{"vendor": vendor, "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-ZQXA"}
               for vendor in ("store", "yahoo_fetch")]
    master = [{"security_id": "SEC:US-XNYS-ZQXA", "listing_key": "US-XNYS-ZQXA",
               "country": "US", "mic": "XNYS", "superseded_by": None}]
    arguments = _stock_arguments(aliases, master)
    before = deepcopy(document)
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result["status"] == "bound", result
    assert result["view"] == expected
    assert document == before
    assert tdm.encode_terminal_rows(document["bars"]).hex() == golden["encoded_hex"]
    assert tdm.terminal_rows_sha256(document["bars"]) == golden["bars_sha256"]
    materialization = result["view"]["contract"]["materialization"]
    assert materialization["schema"] == tdm.API_VERSION
    assert "materialized_at" not in materialization and "catalog_admission" not in materialization
    assert set(materialization["owner"]["files_sha256"]) == {tdm.OWNER_PATH, tdm.IDENTITY_PATH}
    assert set(materialization["identity_reference"]["files_sha256"]) == set(tdm.REFERENCE_FILES)
    arguments["owner_version"]["files_sha256"][tdm.SPY_HELPER_PATH] = "c" * 64
    _refused(tdm.bind_terminal_yahoo_materialization(document, **arguments), "MATERIALIZATION_CODE_UNATTESTED")


@pytest.mark.parametrize("reuse", ["prior_view", "explicit_reuse"])
def test_spy_prior_qualification_cannot_be_recycled_as_a_fresh_materialization(case, reuse):
    if reuse == "prior_view":
        case["document"]["view"] = _bind(case)["view"]
        result = _bind(case)
    else:
        result = _bind(case, reused=True)
    _refused(result, "MATERIALIZATION_REUSE_NOT_FRESH")
