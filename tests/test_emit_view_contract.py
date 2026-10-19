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
