"""The view-contract sidecar emitter writes what the Terminal reader admits (C04).

Pins ``agentos/decisions/DEC-DATAOS-VIEW-CONTRACT-SIDECAR-IS-A-NIGHTLY-EMITTER``
(DATA-OS-COMPLETION): ``scripts/emit_view_contract.py`` serialises C01's
``terminal_daily_ohlc_contract_v1`` mapping verbatim, adds counts-only coverage,
listings resolved through ``vendor_aliases`` -> ``security_master`` (exactly one
open security and one open US listing — never a first row) and refusal reasons,
and writes ``_view_contract.json`` atomically and byte-stably.  Every test is
hermetic: ``tmp_path`` only, the store files are ``b"PAR1"`` garbage because the
emitter never opens them, and no run ever touches a real ``data/`` tree.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import emit_view_contract as evc  # noqa: E402
from engine.price_ladder import terminal_daily_ohlc_contract_v1  # noqa: E402

#: The canonical resolvable scenario: three symbols, XNYS / XNAS / ARCX, one open
#: alias and one open US listing each, plus the one extra column per fixture
#: frame (``ingested_at`` / ``issuer_id``) that column projection must tolerate.
_ALIASES = [
    {"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-ZQXA", "valid_to": None},
    {"vendor": "store", "vendor_symbol": "ZQXB", "security_id": "SEC:US-XNAS-ZQXB", "valid_to": None},
    {"vendor": "store", "vendor_symbol": "ZQXC", "security_id": "SEC:US-ARCX-ZQXC", "valid_to": None},
]
_MASTER = [
    {"security_id": "SEC:US-XNYS-ZQXA", "listing_key": "US-XNYS-ZQXA", "country": "US", "mic": "XNYS", "superseded_by": None},
    {"security_id": "SEC:US-XNAS-ZQXB", "listing_key": "US-XNAS-ZQXB", "country": "US", "mic": "XNAS", "superseded_by": None},
    {"security_id": "SEC:US-ARCX-ZQXC", "listing_key": "US-ARCX-ZQXC", "country": "US", "mic": "ARCX", "superseded_by": None},
]
_STORE_LABEL = "data/stocks"


def _store(tmp_path, names):
    store = tmp_path / "stocks"
    store.mkdir(exist_ok=True)
    for name in names:
        (store / f"{name}.parquet").write_bytes(b"PAR1")
    return store


def _reference(tmp_path, aliases, master):
    reference = tmp_path / "reference"
    reference.mkdir(exist_ok=True)
    if aliases is not None:
        rows = [dict(row, ingested_at="2026-01-01") for row in aliases]
        pd.DataFrame(rows).to_parquet(reference / evc.ALIASES_FILE, index=False)
    if master is not None:
        rows = [dict(row, issuer_id="ISS-1") for row in master]
        pd.DataFrame(rows).to_parquet(reference / evc.MASTER_FILE, index=False)
    return reference


def _emit_default(tmp_path, names=("ZQXA", "ZQXB", "ZQXC")):
    store = _store(tmp_path, list(names))
    reference = _reference(tmp_path, _ALIASES, _MASTER)
    return evc.emit(store, reference, store_label=_STORE_LABEL), store / evc.SIDECAR_NAME


def test_C04_happy_path_matches_factory_and_reader_keys(tmp_path):
    result, path = _emit_default(tmp_path)
    assert result["status"] == "written"
    raw = path.read_bytes()
    contract = json.loads(raw)
    for key in evc._REQUIRED_READER_KEYS:
        assert key in contract
    factory = terminal_daily_ohlc_contract_v1()
    for key in factory:
        assert contract[key] == factory[key]
    assert contract["coverage"] == {"store": "data/stocks", "symbols": 3, "listings_resolved": 3, "listings_unresolved": 0}
    assert contract["refusal_reasons"] == []
    assert contract["listings"]["ZQXA"] == {"mic": "XNYS", "listing_key": "US-XNYS-ZQXA", "security_id": "SEC:US-XNYS-ZQXA"}
    assert raw == (json.dumps(contract, sort_keys=True, indent=2) + "\n").encode()


def test_C04_stdout_carries_counts_never_symbols(tmp_path, capsys):
    _emit_default(tmp_path, names=("ZQXA", "ZQXB", "ZQXZ"))
    out = capsys.readouterr().out
    for ticker in ("ZQXA", "ZQXB", "ZQXZ"):
        assert ticker not in out
    assert any(line.startswith("emit_view_contract: ") for line in out.splitlines())


def test_C04_unresolved_symbol_is_omitted_and_counted(tmp_path, capsys):
    result, path = _emit_default(tmp_path, names=("ZQXA", "ZQXZ"))
    contract = json.loads(path.read_bytes())
    assert "ZQXZ" not in contract["listings"]
    assert result["listings_unresolved"] == 1
    assert contract["coverage"]["listings_unresolved"] == 1
    out = capsys.readouterr().out
    assert any(line.startswith("::notice") for line in out.splitlines())


@pytest.mark.parametrize("mode", ["two_open_security_ids", "two_open_us_listings"])
def test_C04_ambiguity_is_omitted_never_first_row(tmp_path, mode):
    if mode == "two_open_security_ids":
        aliases = [
            {"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-ZQXA", "valid_to": None},
            {"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNAS-ZQXA", "valid_to": None},
        ]
        master = [
            {"security_id": "SEC:US-XNYS-ZQXA", "listing_key": "US-XNYS-ZQXA", "country": "US", "mic": "XNYS", "superseded_by": None},
            {"security_id": "SEC:US-XNAS-ZQXA", "listing_key": "US-XNAS-ZQXA", "country": "US", "mic": "XNAS", "superseded_by": None},
        ]
    else:
        aliases = [{"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-ZQXA", "valid_to": None}]
        master = [
            {"security_id": "SEC:US-XNYS-ZQXA", "listing_key": "US-XNYS-ZQXA", "country": "US", "mic": "XNYS", "superseded_by": None},
            {"security_id": "SEC:US-XNYS-ZQXA", "listing_key": "US-XNAS-ZQXA", "country": "US", "mic": "XNAS", "superseded_by": None},
        ]
    store = _store(tmp_path, ["ZQXA"])
    reference = _reference(tmp_path, aliases, master)
    result = evc.emit(store, reference, store_label=_STORE_LABEL)
    contract = json.loads((store / evc.SIDECAR_NAME).read_bytes())
    assert result["status"] == "written"
    assert result["listings_resolved"] == 0 and result["listings_unresolved"] == 1
    assert contract["listings"] == {}


def test_C04_out_of_scope_venue_is_emitted_verbatim(tmp_path):
    aliases = [{"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-BATS-ZQXA", "valid_to": None}]
    master = [{"security_id": "SEC:US-BATS-ZQXA", "listing_key": "US-BATS-ZQXA", "country": "US", "mic": "BATS", "superseded_by": None}]
    store = _store(tmp_path, ["ZQXA"])
    reference = _reference(tmp_path, aliases, master)
    evc.emit(store, reference, store_label=_STORE_LABEL)
    contract = json.loads((store / evc.SIDECAR_NAME).read_bytes())
    assert contract["listings"]["ZQXA"]["mic"] == "BATS"
    assert contract["refusal_reasons"] == []


def test_C04_closed_superseded_and_non_us_rows_are_ignored(tmp_path):
    aliases = [
        {"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-OLD", "valid_to": "2026-08-18"},
        {"vendor": "store", "vendor_symbol": "ZQXA", "security_id": "SEC:US-XNYS-NEW", "valid_to": None},
    ]
    master = [
        {"security_id": "SEC:US-XNYS-OLD", "listing_key": "US-XNYS-OLD", "country": "US", "mic": "XNYS", "superseded_by": "SEC:US-XNYS-NEW"},
        {"security_id": "SEC:US-XNYS-NEW", "listing_key": "US-XTSE-NEW", "country": "CA", "mic": "XTSE", "superseded_by": None},
        {"security_id": "SEC:US-XNYS-NEW", "listing_key": "US-XNYS-NEW", "country": "US", "mic": "XNYS", "superseded_by": None},
    ]
    store = _store(tmp_path, ["ZQXA"])
    reference = _reference(tmp_path, aliases, master)
    result = evc.emit(store, reference, store_label=_STORE_LABEL)
    contract = json.loads((store / evc.SIDECAR_NAME).read_bytes())
    assert result["listings_resolved"] == 1
    assert contract["listings"] == {"ZQXA": {"mic": "XNYS", "listing_key": "US-XNYS-NEW", "security_id": "SEC:US-XNYS-NEW"}}


def test_C04_store_symbols_skip_private_hidden_non_parquet_and_dirs(tmp_path):
    store = tmp_path / "stocks"
    store.mkdir()
    (store / "_view_contract.json").write_text("{}")
    (store / "_manifest.parquet").write_bytes(b"PAR1")
    (store / ".hidden.parquet").write_bytes(b"PAR1")
    (store / "notes.txt").write_text("notes")
    (store / "sub.parquet").mkdir()
    (store / "ZQXA.parquet").write_bytes(b"PAR1")
    assert evc.store_symbols(store) == ["ZQXA"]


@pytest.mark.parametrize("mode", ["aliases_missing", "master_missing", "aliases_corrupt"])
def test_C04_source_unavailable_still_writes(tmp_path, capsys, mode):
    store = _store(tmp_path, ["ZQXA", "ZQXB"])
    if mode == "aliases_missing":
        reference = _reference(tmp_path, None, _MASTER)
    elif mode == "master_missing":
        reference = _reference(tmp_path, _ALIASES, None)
    else:
        reference = _reference(tmp_path, _ALIASES, _MASTER)
        (reference / evc.ALIASES_FILE).write_bytes(b"\x00\xff not parquet garbage \x00\xff")
    result = evc.emit(store, reference, store_label=_STORE_LABEL)
    contract = json.loads((store / evc.SIDECAR_NAME).read_bytes())
    assert result["status"] == "written"
    assert contract["listings"] == {}
    assert contract["refusal_reasons"] == ["LISTINGS_SOURCE_UNAVAILABLE"]
    assert result["refusal_reasons"] == ["LISTINGS_SOURCE_UNAVAILABLE"]
    assert result["listings_unresolved"] == result["symbols"] == 2
    out = capsys.readouterr().out
    assert any(line.startswith("::warning") for line in out.splitlines())


def test_C04_rerun_is_byte_stable_noop(tmp_path):
    first, path = _emit_default(tmp_path)
    raw_one = path.read_bytes()
    mtime_one = path.stat().st_mtime_ns
    store = tmp_path / "stocks"
    reference = tmp_path / "reference"
    second = evc.emit(store, reference, store_label=_STORE_LABEL)
    assert first["status"] == "written" and second["status"] == "unchanged"
    assert path.read_bytes() == raw_one
    assert path.stat().st_mtime_ns == mtime_one
    assert list(store.glob("._view_contract.*")) == []


def test_C04_dry_run_writes_nothing(tmp_path):
    store = _store(tmp_path, ["ZQXA", "ZQXB", "ZQXC"])
    reference = _reference(tmp_path, _ALIASES, _MASTER)
    before = sorted(p.name for p in store.iterdir())
    result = evc.emit(store, reference, store_label=_STORE_LABEL, dry_run=True)
    assert result["status"] == "dry_run"
    assert not (store / evc.SIDECAR_NAME).exists()
    assert sorted(p.name for p in store.iterdir()) == before


def test_C04_reader_round_trip(tmp_path):
    """An inline copy of the Terminal reader's admission rules (U01, PR #996)."""
    _emit_default(tmp_path, names=("ZQXA", "ZQXB", "ZQXZ"))
    doc = json.loads((tmp_path / "stocks" / evc.SIDECAR_NAME).read_bytes())
    assert doc["schema"] == "dataos.view_contract.v1" and doc["purpose"] == "terminal_daily_ohlc"
    assert all(key in doc for key in ("schema", "purpose", "identity_namespace", "field_units",
                                      "adjustment_reference", "evidence_mode", "coverage", "listings",
                                      "refusal_reasons"))
    assert doc["adjustment_reference"]["basis"] == "tradj"
    assert all(listing["mic"] in {"XNYS", "XNAS", "XASE", "ARCX"} for listing in doc["listings"].values()) \
        and "ZQXZ" not in doc["listings"]


def test_C04_store_absent_warns_and_writes_nothing(tmp_path, capsys):
    missing = tmp_path / "nowhere"
    reference = _reference(tmp_path, _ALIASES, _MASTER)
    result = evc.emit(missing, reference, store_label=_STORE_LABEL)
    assert result["status"] == "store_absent"
    assert result["path"] is None
    out = capsys.readouterr().out
    assert any(line.startswith("::warning") for line in out.splitlines())
    assert not missing.exists()


def test_C04_alias_space_matches_security_master_vendor_store():
    source = (evc.ROOT / "scripts" / "build_security_master.py").read_text()
    found = None
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "VENDOR_STORE" for target in node.targets
        ):
            if isinstance(node.value, ast.Constant):
                found = node.value.value
    assert found == evc.ALIAS_SPACE


def test_C04_build_contract_refuses_a_factory_that_already_carries_coverage(monkeypatch):
    def diverged_factory():
        contract = terminal_daily_ohlc_contract_v1()
        contract["coverage"] = {"store": "someone", "else": 1}
        return contract

    monkeypatch.setattr(evc, "terminal_daily_ohlc_contract_v1", diverged_factory)
    with pytest.raises(ValueError):
        evc.build_contract(_STORE_LABEL, ["ZQXA"], {}, [])


def test_C04_build_contract_refuses_a_listing_outside_the_store():
    with pytest.raises(ValueError):
        evc.build_contract(_STORE_LABEL, ["ZQXA"], {"ZQXZ": {"mic": "XNYS", "listing_key": "US-XNYS-ZQXZ", "security_id": "SEC:US-XNYS-ZQXZ"}}, [])


def test_C04_cli_dry_run_returns_zero(tmp_path):
    store = _store(tmp_path, ["ZQXA", "ZQXB", "ZQXC"])
    reference = _reference(tmp_path, _ALIASES, _MASTER)
    assert evc.main(["--store", str(store), "--reference", str(reference), "--dry-run"]) == 0
    assert not (store / evc.SIDECAR_NAME).exists()


def test_C04_factory_is_not_mutated_by_emit(tmp_path):
    _emit_default(tmp_path)
    _emit_default(tmp_path)
    fresh = terminal_daily_ohlc_contract_v1()
    assert not any(key in fresh for key in ("coverage", "listings", "refusal_reasons"))


def test_C04_listing_keys_are_sorted_in_the_file(tmp_path):
    _emit_default(tmp_path, names=("ZQXC", "ZQXA", "ZQXB"))
    text = (tmp_path / "stocks" / evc.SIDECAR_NAME).read_text()
    assert -1 < text.find('"ZQXA"') < text.find('"ZQXB"') < text.find('"ZQXC"')


def test_C04_written_file_is_world_readable(tmp_path):
    _, path = _emit_default(tmp_path)
    assert path.stat().st_mode & 0o444 == 0o444


def test_C04_emit_reads_no_parquet_in_the_store(tmp_path):
    result, _ = _emit_default(tmp_path)
    assert result["status"] == "written" and result["listings_resolved"] == 3
    store = tmp_path / "stocks"
    for name in ("ZQXA", "ZQXB", "ZQXC"):
        assert (store / f"{name}.parquet").read_bytes() == b"PAR1"


# Direct source materialization is defined by Data OS, not inferred in Terminal.
from copy import deepcopy  # noqa: E402
import hashlib  # noqa: E402
from lib.dataos.identity import VendorAliasTable, parse_listing_key  # noqa: E402
from lib.dataos import terminal_materialization as tdm  # noqa: E402


def _tdm_case(symbol="ZQXA", requested=None):
    requested = requested or symbol
    rows = [["2026-10-15", 100.0, 101.5, 99.5, 101.0, 0],
            ["2026-10-16", 101.0, 103.0, 100.75, 102.125, 12000]]
    document = {
        "t": symbol, "src": "yahoo", "bar_quality": "real_ohlc", "bars": rows,
        "source_observation": {
            "producer": tdm.PRODUCER_PATH, "provider": "yahoo",
            "observed_at": "2026-10-17T00:00:00+00:00",
            "request": {"adapter": "yfinance", "period": "max", "interval": "1d",
                        "auto_adjust": True, "symbol": requested,
                        "session_dates": "exchange_local", "index_timezone": "America/New_York"},
            "adapter_version": "fixture-1",
            "coverage": {"first": rows[0][0], "last": rows[-1][0], "rows": len(rows)},
            "digest_codec": "python.json.compact.v1",
            "bars_sha256": hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
            "qualification": "OBSERVATION_ONLY", "historical_availability": "UNATTESTED",
        },
    }
    listing = "US-XNYS-" + symbol
    security = "SEC:" + listing
    aliases = [{"vendor": vendor, "vendor_symbol": value, "security_id": security}
               for vendor, value in (("store", symbol), ("yahoo_fetch", requested))]
    arguments = {
        "alias_table": VendorAliasTable.from_records(aliases),
        "master_records": [{"security_id": security, "listing_key": listing,
                            "country": "US", "mic": "XNYS", "superseded_by": None}],
        "parse_listing_key": parse_listing_key,
        "producer_version": {"repository": "mastermindx-market-intelligence/mastermind-terminal",
                             "commit": None, "files_sha256": {p: "a"*64 for p in tdm.PRODUCER_FILES}},
        "owner_version": {"repository": "mastermindx-market-intelligence/macro", "commit": "b"*40,
                          "files_sha256": {p: "c"*64 for p in (tdm.OWNER_PATH, tdm.IDENTITY_PATH)}},
        "reference": {"files_sha256": {p: "d"*64 for p in tdm.REFERENCE_FILES},
                      "read_at": "2026-10-17T00:00:01Z",
                      "generation_id": None, "generation_attested": False},
    }
    return document, arguments, aliases


def test_TDM_fresh_observation_binds_real_output_without_macro_store_lineage():
    document, arguments, _ = _tdm_case()
    before = deepcopy(document)
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result["status"] == "bound", result
    assert document == before
    view = result["view"]
    contract = view["contract"]
    assert contract["evidence_mode"]["registry_row"] is None
    assert contract["evidence_mode"]["output_registry_row"] == "terminal.bars.daily.ohlc_json"
    assert contract["materialization"]["bars_sha256"] == tdm.terminal_rows_sha256(document["bars"])
    assert contract["materialization"]["symbol"] == document["t"]
    assert contract["materialization"]["historical_availability"] == "UNATTESTED"
    assert contract["evidence_mode"]["generation_attested"] is False
    assert contract["adjustment_reference"]["action_revision_set_id"] is None
    assert contract["adjustment_reference"]["executable"] is False
    assert contract["adjustment_reference"]["basis"] == "tradj"
    assert view["listing"]["security_id"] == "SEC:US-XNYS-ZQXA"
    # A caller mutation must not leak into the next binding.
    view["contract"]["coverage"]["rows"] = 999
    again = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert again["view"]["contract"]["coverage"]["rows"] == 2
    assert "materialization" not in terminal_daily_ohlc_contract_v1()


def test_TDM_class_share_request_uses_both_canonical_namespaces():
    document, arguments, _ = _tdm_case("BRK.B", "BRK-B")
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result["status"] == "bound", result
    assert result["view"]["contract"]["materialization"]["requested_symbol"] == "BRK-B"


@pytest.mark.parametrize("fault,code", [
    ("old_vendor_label", "MATERIALIZATION_OBSERVATION_ABSENT"),
    ("prior_view", "MATERIALIZATION_REUSE_NOT_FRESH"),
    ("reused", "MATERIALIZATION_REUSE_NOT_FRESH"),
    ("different_source", "MATERIALIZATION_SOURCE_UNSUPPORTED"),
    ("unadjusted", "MATERIALIZATION_SOURCE_UNSUPPORTED"),
    ("wrong_interval", "MATERIALIZATION_SOURCE_UNSUPPORTED"),
    ("no_timezone", "MATERIALIZATION_SOURCE_UNSUPPORTED"),
    ("no_adapter_version", "MATERIALIZATION_SOURCE_UNSUPPORTED"),
    ("bad_digest", "MATERIALIZATION_OBSERVATION_MISMATCH"),
    ("changed_open", "MATERIALIZATION_OBSERVATION_MISMATCH"),
    ("append", "MATERIALIZATION_OBSERVATION_MISMATCH"),
    ("coverage", "MATERIALIZATION_OBSERVATION_MISMATCH"),
    ("future_bars", "MATERIALIZATION_CLOCK_INVALID"),
    ("unaware_clock", "MATERIALIZATION_CLOCK_INVALID"),
    ("wrong_namespace", "MATERIALIZATION_IDENTITY_UNRESOLVED"),
    ("wrong_security", "MATERIALIZATION_IDENTITY_MISMATCH"),
    ("missing_alias", "MATERIALIZATION_IDENTITY_UNRESOLVED"),
    ("ambiguous_listing", "MATERIALIZATION_LISTING_AMBIGUOUS"),
    ("superseded_listing", "MATERIALIZATION_LISTING_AMBIGUOUS"),
    ("wrong_mic", "VENUE_OUT_OF_SCOPE"),
    ("unattested_code", "MATERIALIZATION_CODE_UNATTESTED"),
    ("missing_reference", "MATERIALIZATION_REFERENCE_UNAVAILABLE"),
    ("invented_generation", "MATERIALIZATION_REFERENCE_UNAVAILABLE"),
])
def test_TDM_refusal_matrix(fault, code):
    document, arguments, aliases = _tdm_case()
    observation = document["source_observation"]
    if fault == "old_vendor_label": del document["source_observation"]
    elif fault == "prior_view": document["view"] = {"contract": {"basis": "tradj"}}
    elif fault == "reused": arguments["reused"] = True
    elif fault == "different_source": document["src"] = "polygon"
    elif fault == "unadjusted": observation["request"]["auto_adjust"] = False
    elif fault == "wrong_interval": observation["request"]["interval"] = "1h"
    elif fault == "no_timezone": observation["request"]["index_timezone"] = None
    elif fault == "no_adapter_version": observation["adapter_version"] = None
    elif fault == "bad_digest": observation["bars_sha256"] = "0"*64
    elif fault == "changed_open": document["bars"][0][1] += 0.125
    elif fault == "append":
        document["bars"].append(["2026-10-19", 102, 104, 101, 103, 50])
        observation["observed_at"] = "2026-10-20T00:00:00Z"
    elif fault == "coverage": observation["coverage"]["rows"] = 3
    elif fault == "future_bars": observation["observed_at"] = "2026-10-15T01:00:00Z"
    elif fault == "unaware_clock": observation["observed_at"] = "2026-10-17T00:00:00"
    elif fault == "wrong_namespace": aliases[1]["vendor"] = "yahoo"
    elif fault == "wrong_security": aliases[1]["security_id"] = "SEC:US-XNYS-ZQXB"
    elif fault == "missing_alias": aliases.pop()
    elif fault == "ambiguous_listing": arguments["master_records"] *= 2
    elif fault == "superseded_listing": arguments["master_records"][0]["superseded_by"] = "SEC:US-XNYS-OLD"
    elif fault == "wrong_mic": arguments["master_records"][0]["mic"] = "XNAS"
    elif fault == "unattested_code": arguments["producer_version"]["files_sha256"] = {}
    elif fault == "missing_reference": arguments["reference"]["files_sha256"] = {}
    elif fault == "invented_generation": arguments["reference"]["generation_attested"] = True
    arguments["alias_table"] = VendorAliasTable.from_records(aliases)
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result == {"status": "refused", "view": None, "refusal_reasons": [code]}


@pytest.mark.parametrize("fault", ["empty", "duplicate", "reverse", "bad_date", "string",
                                  "boolean", "nan", "infinity", "bad_bounds", "negative",
                                  "fractional_volume", "unsafe_volume", "extra_column"])
def test_TDM_row_codec_rejects_ambiguous_or_invalid_values(fault):
    document, _, _ = _tdm_case()
    rows = document["bars"]
    if fault == "empty": rows.clear()
    elif fault == "duplicate": rows.append(deepcopy(rows[-1]))
    elif fault == "reverse": rows.reverse()
    elif fault == "bad_date": rows[0][0] = "2026-02-30"
    elif fault == "string": rows[0][4] = "101"
    elif fault == "boolean": rows[0][5] = True
    elif fault == "nan": rows[0][4] = float("nan")
    elif fault == "infinity": rows[0][4] = float("inf")
    elif fault == "bad_bounds": rows[0][2] = 90
    elif fault == "negative": rows[0][4] = -1
    elif fault == "fractional_volume": rows[0][5] = 1.5
    elif fault == "unsafe_volume": rows[0][5] = 2**53
    elif fault == "extra_column": rows[0].append(0)
    with pytest.raises(tdm.MaterializationRefusal, match="MATERIALIZATION_ROWS_INVALID"):
        tdm.encode_terminal_rows(rows)


def test_TDM_codec_numeric_equivalence_and_non_close_mutation():
    document, _, _ = _tdm_case()
    rows = document["bars"]
    digest = tdm.terminal_rows_sha256(rows)
    rows[0][1] = 100
    rows[0][5] = -0.0
    assert tdm.terminal_rows_sha256(rows) == digest
    rows[0][2] += 0.125
    assert tdm.terminal_rows_sha256(rows) != digest


def test_TDM_portable_golden_values_and_owner_contract():
    golden = json.loads((ROOT / "tests/terminal_materialization_golden.json").read_text())
    assert golden["fixture"] is True
    for rows, encoded, digest in [
        (golden["document"]["bars"], golden["encoded_hex"], golden["bars_sha256"]),
        (golden["portable_rows"], golden["portable_encoded_hex"], golden["portable_sha256"]),
    ]:
        assert tdm.encode_terminal_rows(rows).hex() == encoded
        assert tdm.terminal_rows_sha256(rows) == digest
    document, arguments, _ = _tdm_case()
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result["view"] == golden["document"]["view"]


# Bounded C2 follow-up: lazy NY resolution, parser-attribute guard, read_at passthrough,
# and the owner agreement test against engine.price_ladder.terminal_daily_ohlc_contract_v1().


def test_TDM_codec_imports_and_runs_without_tzdata_in_isolated_subprocess(tmp_path):
    """tzdata absent must not block the import or the codec helpers; only the binder's
    America/New_York resolution needs the system catalog."""
    golden_path = ROOT / "tests" / "terminal_materialization_golden.json"
    golden = json.loads(golden_path.read_text())
    probe = tmp_path / "probe_no_tzdata.py"
    probe.write_text(
        "import sys, json, pathlib\n"
        "from zoneinfo import ZoneInfoNotFoundError\n"
        "import zoneinfo as _z\n"
        "_z.ZoneInfo = lambda key: (_ for _ in ()).throw(ZoneInfoNotFoundError(key))\n"
        "import lib.dataos.terminal_materialization as tdm\n"
        f"golden = json.loads(pathlib.Path({str(golden_path)!r}).read_text())\n"
        "out = []\n"
        "for rows, encoded, digest in [\n"
        "    (golden['document']['bars'], golden['encoded_hex'], golden['bars_sha256']),\n"
        "    (golden['portable_rows'], golden['portable_encoded_hex'], golden['portable_sha256'])]:\n"
        "    got = tdm.encode_terminal_rows(rows)\n"
        "    assert got.hex() == encoded, (got.hex(), encoded)\n"
        "    assert tdm.terminal_rows_sha256(rows) == digest\n"
        "out.append('OK')\n"
        "sys.stdout.write('\\n'.join(out))\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run([sys.executable, str(probe)], cwd=str(ROOT),
                               env=env, capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert "OK" in completed.stdout


def test_TDM_binder_refuses_clock_when_tzdata_unavailable(monkeypatch):
    """A missing NY catalog must surface as typed MATERIALIZATION_CLOCK_INVALID, not escape."""
    from zoneinfo import ZoneInfoNotFoundError

    def missing_zone(key):
        raise ZoneInfoNotFoundError(key)

    monkeypatch.setattr(tdm, "ZoneInfo", missing_zone)
    document, arguments, _ = _tdm_case()
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result == {"status": "refused", "view": None,
                      "refusal_reasons": ["MATERIALIZATION_CLOCK_INVALID"]}


@pytest.mark.parametrize("bad_return", [
    {"country": "US", "mic": "XNYS"},
    "US-XNYS-ZQXA",
    None,
    42,
    object(),
])
def test_TDM_binder_refuses_identity_for_malformed_parser_return(bad_return):
    """A non-ListingKey parser return must refuse typed, never leak an AttributeError."""
    document, arguments, _ = _tdm_case()
    arguments["parse_listing_key"] = lambda _: bad_return
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result == {"status": "refused", "view": None,
                      "refusal_reasons": ["MATERIALIZATION_IDENTITY_UNRESOLVED"]}


def test_TDM_binder_passes_read_at_verbatim_and_invents_no_clock_field():
    """The leaf records the adapter's read_at byte-for-byte and never derives an age."""
    document, arguments, _ = _tdm_case()
    original_read_at = arguments["reference"]["read_at"]
    before_reference = deepcopy(arguments["reference"])
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    assert result["status"] == "bound"
    identity_reference = result["view"]["contract"]["materialization"]["identity_reference"]
    assert identity_reference["read_at"] == original_read_at
    assert arguments["reference"] == before_reference
    assert set(identity_reference) == {"files_sha256", "read_at", "generation_id",
                                       "generation_attested", "historical_availability"}
    for node in (identity_reference, result["view"]["contract"]["materialization"],
                 result["view"]["contract"]["evidence_mode"]):
        for forbidden in ("observed_age_seconds", "reference_age_seconds",
                          "stale", "is_fresh", "upstream_freshness",
                          "publication_generation_clock", "stale_after_seconds"):
            assert forbidden not in node


def test_TDM_binder_agrees_with_engine_factory_on_shared_invariants():
    """Direct-Yahoo contract shares the documented invariants and declares its divergences."""
    document, arguments, _ = _tdm_case()
    result = tdm.bind_terminal_yahoo_materialization(document, **arguments)
    contract = result["view"]["contract"]
    factory = terminal_daily_ohlc_contract_v1()
    # Identical invariants
    for key in ("schema", "purpose", "identity_namespace", "venues",
                "field_units", "store_vendor"):
        assert contract[key] == factory[key], (key, contract[key], factory[key])
    # adjustment_reference: same except the deliberately specific readout
    for key in ("basis", "action_revision_set_id", "as_at", "vintage", "executable"):
        assert contract["adjustment_reference"][key] == factory["adjustment_reference"][key]
    assert contract["adjustment_reference"]["readout"] != factory["adjustment_reference"]["readout"]
    assert contract["adjustment_reference"]["readout"] == "vendor total-return proxy — not a printed price"
    # evidence_mode: shared keys; documented differences
    for key in ("mode", "output_registry_row", "dependency_generation_ids",
                "generation_attested"):
        assert contract["evidence_mode"][key] == factory["evidence_mode"][key]
    assert contract["evidence_mode"]["clock"] != factory["evidence_mode"]["clock"]
    assert contract["evidence_mode"]["registry_row"] != factory["evidence_mode"]["registry_row"]
    assert contract["evidence_mode"]["code_version"] != factory["evidence_mode"]["code_version"]
