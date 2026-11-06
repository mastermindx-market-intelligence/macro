"""Deterministic tests for the pure BOATS delivery assembly step.

No network, no provider, no filesystem: every case drives
``assemble_delivery`` on in-memory manifests only. Coverage follows the
assembly contract: normal replacement preserving other symbols, zero-bar
cancellation (file and no-file dispositions), malformed symbols, paths,
counts, hashes and bools, incomplete or partial refresh refusal,
held-vendor-unavailable mutation refusal, exact symbol partition, and
deterministic repeats.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from scripts.boats_history_delivery import SCHEMA, assemble_delivery  # noqa: E402

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def _file(symbol, *, sha, bars, nbytes=None):
    return {
        "name": f"{symbol}.json",
        "bytes": nbytes if nbytes is not None else 100 * bars + 2,
        "sha256": sha,
        "bars": bars,
    }


def _baseline():
    return {
        "schema": SCHEMA,
        "requested_symbols": ["AAA", "BBB", "CCC", "DDD", "EEE"],
        "vendor_empty_symbols": ["DDD"],
        "vendor_unavailable_symbols": [
            {"symbol": "CCC", "reason": "input: upstream returned 404"}
        ],
        "files": [
            _file("AAA", sha=SHA_A, bars=10),
            _file("BBB", sha=SHA_B, bars=0, nbytes=2),
            _file("EEE", sha=SHA_C, bars=5),
        ],
        "bars": 15,
        "bytes": 1002 + 2 + 502,
        "complete_history": False,
    }


def _refresh(symbols, outputs):
    return {
        "schema": "terminal.private_boats_refresh.v1",
        "session": "2026-10-16",
        "status": "complete",
        "symbols": list(symbols),
        "outputs": copy.deepcopy(outputs),
        "unavailable": [],
        "not_requested": [],
    }


def _file_output(symbol, *, sha, bars, nbytes=None, receipt=SHA_D):
    return {
        "symbol": symbol,
        "file": f"{symbol}.json",
        "bytes": nbytes if nbytes is not None else 100 * bars + 2,
        "sha256": sha,
        "bars": bars,
        "new_receipt": receipt,
    }


def _empty_output(symbol, receipt=SHA_D):
    return {"symbol": symbol, "status": "vendor_empty", "bars": 0,
            "new_receipt": receipt}


# --------------------------------------------------------------------------
# normal replacement preserving other symbols
# --------------------------------------------------------------------------

def test_normal_replacement_preserves_other_symbols():
    baseline = _baseline()
    refresh = _refresh(["AAA", "EEE"], [
        _file_output("AAA", sha=SHA_B, bars=20),
        _file_output("EEE", sha=SHA_D, bars=6),
    ])
    out = assemble_delivery(baseline, refresh)

    assert out["schema"] == SCHEMA
    assert out["requested_symbols"] == baseline["requested_symbols"]
    assert out["complete_history"] is False
    assert out["vendor_empty_symbols"] == ["DDD"]
    assert out["vendor_unavailable_symbols"] == [
        {"symbol": "CCC", "reason": "input: upstream returned 404"}
    ]
    assert [(f["name"], f["bars"], f["sha256"], f["origin"]) for f in out["files"]] == [
        ("AAA.json", 20, SHA_B, "refresh"),
        ("BBB.json", 0, SHA_B, "baseline"),
        ("EEE.json", 6, SHA_D, "refresh"),
    ]
    assert out["bars"] == 26
    assert out["bytes"] == 2002 + 2 + 602
    assert out["selected_symbols"] == 2
    assert out["preserved_symbols"] == 3


def test_file_output_replaces_authoritative_zero_bar_file():
    refresh = _refresh(["BBB"], [_file_output("BBB", sha=SHA_C, bars=1, nbytes=102)])
    out = assemble_delivery(_baseline(), refresh)
    bbb = next(f for f in out["files"] if f["name"] == "BBB.json")
    assert (bbb["bars"], bbb["sha256"], bbb["origin"]) == (1, SHA_C, "refresh")
    assert out["vendor_empty_symbols"] == ["DDD"]


def test_symbol_moves_from_vendor_empty_to_file():
    refresh = _refresh(["DDD"], [_file_output("DDD", sha=SHA_A, bars=3)])
    out = assemble_delivery(_baseline(), refresh)
    assert out["vendor_empty_symbols"] == []
    assert [(f["name"], f["bars"], f["origin"]) for f in out["files"]] == [
        ("AAA.json", 10, "baseline"),
        ("BBB.json", 0, "baseline"),
        ("DDD.json", 3, "refresh"),
        ("EEE.json", 5, "baseline"),
    ]
    assert out["selected_symbols"] == 1
    assert out["preserved_symbols"] == 4


# --------------------------------------------------------------------------
# zero-bar cancellation: file removal and no-file empty disposition
# --------------------------------------------------------------------------

def test_vendor_empty_output_cancels_zero_bar_file():
    refresh = _refresh(["BBB"], [_empty_output("BBB")])
    out = assemble_delivery(_baseline(), refresh)
    assert [f["name"] for f in out["files"]] == ["AAA.json", "EEE.json"]
    assert out["vendor_empty_symbols"] == ["BBB", "DDD"]
    assert out["bars"] == 15
    assert out["bytes"] == 1002 + 502
    assert out["selected_symbols"] == 1
    assert out["preserved_symbols"] == 4


def test_vendor_empty_output_keeps_already_empty_symbol():
    refresh = _refresh(["DDD"], [_empty_output("DDD")])
    out = assemble_delivery(_baseline(), refresh)
    assert out["vendor_empty_symbols"] == ["DDD"]
    assert [f["name"] for f in out["files"]] == ["AAA.json", "BBB.json", "EEE.json"]
    assert out["bars"] == 15 and out["bytes"] == 1506


def test_vendor_empty_output_refused_against_nonempty_prior_history():
    refresh = _refresh(["AAA"], [_empty_output("AAA")])
    with pytest.raises(ValueError, match="nonempty prior history"):
        assemble_delivery(_baseline(), refresh)


def test_vendor_empty_output_with_nonzero_bars_refused():
    entry = _empty_output("BBB")
    entry["bars"] = 7
    with pytest.raises(ValueError, match="exactly 0 bars"):
        assemble_delivery(_baseline(), _refresh(["BBB"], [entry]))


def test_vendor_empty_output_with_file_refused():
    entry = _empty_output("BBB")
    entry["file"] = "BBB.json"
    with pytest.raises(ValueError, match="must not carry a file"):
        assemble_delivery(_baseline(), _refresh(["BBB"], [entry]))


# --------------------------------------------------------------------------
# malformed baseline: symbols, paths, counts, hashes, bools
# --------------------------------------------------------------------------

def _rebuild_totals(doc):
    doc["bars"] = sum(f["bars"] for f in doc["files"])
    doc["bytes"] = sum(f["bytes"] for f in doc["files"])
    return doc


@pytest.mark.parametrize("mutation,fragment", [
    (lambda b: b["requested_symbols"].append("AAA"), "duplicate"),
    (lambda b: b["files"][0].update(name="AAA/../../etc.json"), "valid BOATS symbol"),
    (lambda b: b["files"][0].update(name="../AAA.json"), "valid BOATS symbol"),
    (lambda b: b["files"][0].update(name="AAA.txt"), ".json"),
    (lambda b: b["files"][0].update(name="aaa.json"), "valid BOATS symbol"),
    (lambda b: b["requested_symbols"].__setitem__(0, "aaa"), "valid BOATS symbol"),
    (lambda b: b["requested_symbols"].__setitem__(0, "A" * 33), "valid BOATS symbol"),
    (lambda b: b["requested_symbols"].__setitem__(0, "1A"), "valid BOATS symbol"),
    (lambda b: b["files"][0].__setitem__("bars", True), "must be an int"),
    (lambda b: b["files"][0].__setitem__("bytes", 10.0), "must be an int"),
    (lambda b: b["files"][0].__setitem__("bars", -1), "nonnegative"),
    (lambda b: b["files"][0].__setitem__("bars", 100_001), "exceeds limit"),
    (lambda b: b["files"][0].__setitem__("bytes", 32 * 1024 * 1024 + 1), "exceeds limit"),
    (lambda b: b["files"][0].__setitem__("sha256", "A" * 64), "lowercase 64-hex"),
    (lambda b: b["files"][0].__setitem__("sha256", SHA_A[:-1]), "lowercase 64-hex"),
    (lambda b: b["files"][0].__setitem__("sha256", "g" * 64), "lowercase 64-hex"),
    (lambda b: b["files"][0].pop("sha256"), "missing"),
    (lambda b: b["files"].append(dict(b["files"][0])), "duplicate file name"),
    (lambda b: b.__setitem__("bars", b["bars"] + 1), "must equal the file sum"),
    (lambda b: b.__setitem__("bytes", 0), "must equal the file sum"),
    (lambda b: b.__setitem__("complete_history", True), "complete_history"),
    (lambda b: b.__setitem__("schema", "other.v1"), "schema"),
    (lambda b: b["vendor_empty_symbols"].append("AAA"), "not unique"),
    (lambda b: b["vendor_unavailable_symbols"].append(
        {"symbol": "AAA", "reason": "x"}), "not unique"),
    (lambda b: b["vendor_unavailable_symbols"][0].__setitem__("reason", ""),
     "nonempty string"),
    (lambda b: b["files"][0].__setitem__("note", "extra"), "unexpected keys"),
    (lambda b: b.__setitem__("files", "nope"), "must be a list"),
])
def test_malformed_baseline_refused(mutation, fragment):
    baseline = _baseline()
    mutation(baseline)
    with pytest.raises(ValueError, match=fragment):
        assemble_delivery(baseline, _refresh(["DDD"], [_empty_output("DDD")]))


def test_too_many_requested_symbols_refused():
    baseline = _baseline()
    baseline["requested_symbols"] = [f"S{i:05d}" for i in range(20_001)]
    with pytest.raises(ValueError, match="exceeds 20000"):
        assemble_delivery(baseline, _refresh([], []))


def test_boundary_counts_accepted():
    symbol = "Z" * 32
    baseline = _baseline()
    baseline["requested_symbols"] = ["A" * 32, symbol]
    baseline["vendor_empty_symbols"] = []
    baseline["vendor_unavailable_symbols"] = []
    baseline["files"] = [
        _file("A" * 32, sha=SHA_A, bars=100_000, nbytes=32 * 1024 * 1024),
        _file(symbol, sha=SHA_B, bars=1, nbytes=102),
    ]
    _rebuild_totals(baseline)
    refresh = _refresh([symbol], [
        _file_output(symbol, sha=SHA_C, bars=100_000,
                     nbytes=32 * 1024 * 1024),
    ])
    out = assemble_delivery(baseline, refresh)
    assert [(f["name"], f["bars"], f["bytes"], f["origin"]) for f in out["files"]] == [
        ("A" * 32 + ".json", 100_000, 32 * 1024 * 1024, "baseline"),
        (symbol + ".json", 100_000, 32 * 1024 * 1024, "refresh"),
    ]


# --------------------------------------------------------------------------
# incomplete / partial refresh refusal
# --------------------------------------------------------------------------

def test_partial_status_refused():
    refresh = _refresh(["AAA"], [_file_output("AAA", sha=SHA_B, bars=11)])
    refresh["status"] = "partial"
    refresh["unavailable"] = [{"symbol": "EEE", "reason": "timeout", "stage": "fetch"}]
    with pytest.raises(ValueError, match="not complete"):
        assemble_delivery(_baseline(), refresh)


def test_nonempty_unavailable_refused():
    refresh = _refresh(["AAA"], [_file_output("AAA", sha=SHA_B, bars=11)])
    refresh["unavailable"] = [{"symbol": "EEE", "reason": "timeout"}]
    with pytest.raises(ValueError, match="unavailable"):
        assemble_delivery(_baseline(), refresh)


def test_nonempty_not_requested_refused():
    refresh = _refresh(["AAA"], [_file_output("AAA", sha=SHA_B, bars=11)])
    refresh["not_requested"] = ["EEE"]
    with pytest.raises(ValueError, match="not_requested"):
        assemble_delivery(_baseline(), refresh)


def test_missing_symbol_output_refused():
    refresh = _refresh(["AAA", "EEE"], [_file_output("AAA", sha=SHA_B, bars=11)])
    with pytest.raises(ValueError, match="EEE has no output"):
        assemble_delivery(_baseline(), refresh)


def test_duplicate_outputs_refused():
    refresh = _refresh(["AAA"], [
        _file_output("AAA", sha=SHA_B, bars=11),
        _file_output("AAA", sha=SHA_C, bars=12),
    ])
    with pytest.raises(ValueError, match="duplicate outputs"):
        assemble_delivery(_baseline(), refresh)


def test_orphan_output_refused():
    refresh = _refresh(["AAA"], [
        _file_output("AAA", sha=SHA_B, bars=11),
        _file_output("EEE", sha=SHA_C, bars=6),
    ])
    refresh["symbols"] = ["AAA"]
    with pytest.raises(ValueError, match="not a refreshed symbol"):
        assemble_delivery(_baseline(), refresh)


def test_malformed_refresh_output_refused():
    cases = [
        _file_output("AAA", sha="ZZ", bars=1),
        _file_output("AAA", sha=SHA_B, bars=-1),
        _file_output("AAA", sha=SHA_B, bars=11, receipt="short"),
        _file_output("AAA", sha=SHA_B, bars=11) | {"file": "EEE.json"},
        _file_output("AAA", sha=SHA_B, bars=11) | {"new_receipt": None},
        {"symbol": "AAA", "bars": 0, "new_receipt": SHA_D},
    ]
    for entry in cases:
        with pytest.raises(ValueError):
            assemble_delivery(_baseline(), _refresh(["AAA"], [entry]))


# --------------------------------------------------------------------------
# held-vendor-unavailable (404) mutation refusal
# --------------------------------------------------------------------------

def test_held_unavailable_symbol_mutation_refused():
    refresh = _refresh(["CCC"], [_file_output("CCC", sha=SHA_B, bars=4)])
    with pytest.raises(ValueError, match="held vendor_unavailable"):
        assemble_delivery(_baseline(), refresh)


def test_refresh_symbol_absent_from_baseline_refused():
    refresh = _refresh(["FFF"], [_file_output("FFF", sha=SHA_B, bars=4)])
    with pytest.raises(ValueError, match="absent from the baseline"):
        assemble_delivery(_baseline(), refresh)


def test_unavailable_disposition_unchanged_when_others_refresh():
    refresh = _refresh(["AAA"], [_file_output("AAA", sha=SHA_B, bars=11)])
    out = assemble_delivery(_baseline(), refresh)
    assert out["vendor_unavailable_symbols"] == \
        _baseline()["vendor_unavailable_symbols"]


# --------------------------------------------------------------------------
# exact partition
# --------------------------------------------------------------------------

def test_exact_partition_enforced_both_ways():
    baseline = _baseline()
    baseline["requested_symbols"] = ["AAA", "BBB", "CCC", "DDD"]  # EEE missing
    with pytest.raises(ValueError, match="partition does not match"):
        assemble_delivery(baseline, _refresh(["DDD"], [_empty_output("DDD")]))

    baseline = _baseline()
    baseline["requested_symbols"] = ["AAA", "BBB", "CCC", "DDD", "EEE", "ZZZ"]
    with pytest.raises(ValueError, match="partition does not match"):
        assemble_delivery(baseline, _refresh(["DDD"], [_empty_output("DDD")]))

    baseline = _baseline()
    baseline["vendor_empty_symbols"] = ["AAA"]  # AAA both file and vendor_empty
    with pytest.raises(ValueError, match="not unique"):
        assemble_delivery(baseline, _refresh(["DDD"], [_empty_output("DDD")]))


def test_output_is_again_a_valid_baseline_with_origin_ignored():
    refresh1 = _refresh(["AAA"], [_file_output("AAA", sha=SHA_B, bars=20)])
    once = assemble_delivery(_baseline(), refresh1)
    assert all("origin" in f for f in once["files"])
    refresh2 = _refresh(["BBB"], [_empty_output("BBB")])
    twice = assemble_delivery(once, refresh2)
    assert [f["name"] for f in twice["files"]] == ["AAA.json", "EEE.json"]
    assert twice["vendor_empty_symbols"] == ["BBB", "DDD"]
    assert twice["bars"] == 25 and twice["bytes"] == 2504
    assert twice["complete_history"] is False


# --------------------------------------------------------------------------
# determinism / purity
# --------------------------------------------------------------------------

def test_deterministic_repeat_and_purity():
    baseline = _baseline()
    snapshot = copy.deepcopy(baseline)
    refresh = _refresh(["AAA", "BBB"], [
        _file_output("AAA", sha=SHA_B, bars=20),
        _empty_output("BBB"),
    ])
    refresh_snapshot = copy.deepcopy(refresh)

    first = assemble_delivery(baseline, refresh)
    second = assemble_delivery(baseline, refresh)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert baseline == snapshot, "baseline must not be mutated"
    assert refresh == refresh_snapshot, "refresh must not be mutated"
    assert set(first) == {
        "schema", "requested_symbols", "vendor_empty_symbols",
        "vendor_unavailable_symbols", "files", "bars", "bytes",
        "complete_history", "selected_symbols", "preserved_symbols",
    }


def test_files_sorted_and_no_filesystem_or_clock_access():
    baseline = _baseline()
    baseline["requested_symbols"] = ["ZZZ", "AAA", "MMM"]
    baseline["vendor_empty_symbols"] = []
    baseline["vendor_unavailable_symbols"] = []
    baseline["files"] = [
        _file("ZZZ", sha=SHA_A, bars=1),
        _file("AAA", sha=SHA_B, bars=2),
        _file("MMM", sha=SHA_C, bars=3),
    ]
    _rebuild_totals(baseline)
    refresh = _refresh(["MMM"], [_file_output("MMM", sha=SHA_D, bars=9)])
    out = assemble_delivery(baseline, refresh)
    assert [f["name"] for f in out["files"]] == ["AAA.json", "MMM.json", "ZZZ.json"]
    assert out["vendor_empty_symbols"] == []


@pytest.mark.parametrize("status", ["rebuilt", "refreshed_empty_window"])
def test_actual_refresh_file_status_and_count_manifest(status):
    baseline = _baseline()
    baseline["requested_symbols"] = 5
    entry = _file_output("AAA", sha=SHA_D, bars=0, nbytes=512)
    entry["status"] = status
    result = assemble_delivery(baseline, _refresh(["AAA"], [entry]))
    assert result["requested_symbols"] == 5
    assert result["selected_symbols"] == 1 and result["preserved_symbols"] == 4
    assert next(x for x in result["files"] if x["name"] == "AAA.json")["bars"] == 0
    assert "AAA" not in result["vendor_empty_symbols"]
    assert assemble_delivery(result, _refresh([], []))["bars"] == result["bars"]


@pytest.mark.parametrize("count", [True, -1, 4, 6, 20001])
def test_invalid_count_partition_rejected(count):
    baseline = _baseline()
    baseline["requested_symbols"] = count
    with pytest.raises(ValueError):
        assemble_delivery(baseline, _refresh([], []))


def test_full_coverage_limit_counts_empty_symbols_once():
    baseline = _baseline()
    baseline["requested_symbols"] = 20000
    baseline["vendor_empty_symbols"] = ["D"+str(i) for i in range(19996)]
    result = assemble_delivery(baseline, _refresh([], []))
    assert result["preserved_symbols"] == 20000
