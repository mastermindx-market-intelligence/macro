from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


passports = _load("toi_w1_passports", "scripts/research/validate_toi_w1_passports.py")
equiv = _load("toi_w1_equiv", "scripts/research/validate_toi_w1_equivalence.py")
sources = _load("toi_w1_sources", "scripts/research/validate_toi_w1_sources.py")


def _rows():
    return passports._load_jsonl(passports.PASSPORTS)


def _source_map():
    payload = json.loads(sources.SOURCES.read_text(encoding="utf-8"))
    return sources.validate_sources(payload)


def test_current_p0_passports_validate():
    result = passports.validate_rows(_rows(), passports._source_ids())
    assert result["status"] == "valid"
    assert result["count"] >= 12
    assert result["priority_counts"]["P0"] >= 12


def test_unknown_passport_key_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["mystery"] = "not in schema"
    with pytest.raises(ValueError, match="schema mismatch"):
        passports.validate_rows(rows, passports._source_ids())


def test_duplicate_method_id_fails_closed():
    rows = copy.deepcopy(_rows())
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError, match="duplicate method_id"):
        passports.validate_rows(rows, passports._source_ids())


def test_invalid_dnr_identifier_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["dnd_keys"] = ["KILL-OUTCOME-AUDITION"]
    with pytest.raises(ValueError, match="stable DNR"):
        passports.validate_rows(rows, passports._source_ids())


def test_exact_local_without_signal_ids_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["local_implementation"]["signal_ids"] = []
    with pytest.raises(ValueError, match="requires paths and signal_ids"):
        passports.validate_rows(rows, passports._source_ids())


def test_p0_unreceipted_source_fails_closed():
    rows = copy.deepcopy(_rows())
    rows[0]["source_refs"] = ["SRC-NOT-REAL"]
    rows[0]["rights_ref"] = "SRC-NOT-REAL"
    with pytest.raises(ValueError, match="requires a receipted source"):
        passports.validate_rows(rows, passports._source_ids())


def test_current_equivalence_map_validates():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    result = equiv.validate(payload, ids, alias_map)
    assert result["status"] == "valid"
    assert result["method_count"] == len(ids)


def test_equivalence_duplicate_membership_fails_closed():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    duplicate = copy.deepcopy(bad["classes"][0]["members"][0])
    bad["classes"][1]["members"].append(duplicate)
    with pytest.raises(ValueError, match="membership mismatch"):
        equiv.validate(bad, ids, alias_map)


def test_alias_misresolution_fails_closed():
    ids, alias_map = equiv._methods()
    payload = json.loads(equiv.EQUIV.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    bad["alias_index"]["BB Width"] = "toi.bb_kc_squeeze"
    with pytest.raises(ValueError, match="misresolved"):
        equiv.validate(bad, ids, alias_map)


def test_current_source_receipts_validate():
    source_map = _source_map()
    result = sources.validate_passport_bindings(source_map)
    assert result["status"] == "valid"
    assert result["p0_p1_count"] >= 12


def test_duplicate_source_receipt_fails_closed():
    payload = json.loads(sources.SOURCES.read_text(encoding="utf-8"))
    bad = copy.deepcopy(payload)
    bad["receipts"].append(copy.deepcopy(bad["receipts"][0]))
    with pytest.raises(ValueError, match="duplicate source_ref"):
        sources.validate_sources(bad)


def test_opaque_source_cannot_receive_active_owner():
    rows = copy.deepcopy(_rows())
    rows[0]["rights_class"] = "opaque"
    rows[0]["owner_disposition"] = "toi_w3_candidate"
    with pytest.raises(ValueError, match="opaque/blocked"):
        passports.validate_rows(rows, passports._source_ids())
