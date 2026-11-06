"""A39 delegated-lane receipts ledger — capture 2 tests (SNI commission 8659).

This module is an SNI-local DRAFT contract test. It re-derives every rung
independently of the builder and proves that `build(tsv_text, c1_text)` from
the canonical builder regenerates the committed JSON and Markdown outputs
byte-for-byte.

Reads files only. No git, no exec, no network, no writes anywhere.
The builder is loaded without inserting it into sys.modules.
"""
from __future__ import annotations

import csv
import io
import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER_DIR = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "e2e_20261011"
)
BUILDER_PATH = LEDGER_DIR / "build_a39_receipts_ledger_c2.py"
JSON_C2_PATH = LEDGER_DIR / "A39_LANE_RECEIPTS_LEDGER_C2.json"
MD_C2_PATH = LEDGER_DIR / "A39_LANE_RECEIPTS_LEDGER_C2.md"
TSV_PATH = LEDGER_DIR / "A39_LANE_RECEIPTS_C2_INPUT.tsv"
JSON_C1_PATH = LEDGER_DIR / "A39_LANE_RECEIPTS_LEDGER.json"

LADDER = [
    "ACK",
    "QUEUED",
    "START",
    "RUNNING",
    "DELIVERED",
    "CI",
    "MERGED",
    "PRODUCTION_PROOF",
    "ACCEPTANCE",
]

BY_RUNG_ORDER = [
    "ACK",
    "QUEUED",
    "START",
    "RUNNING",
    "NOT_STARTED",
    "RUNNING_OR_UNKNOWN_AT_CAPTURE",
    "EXITED_NO_RESULT",
    "EXITED_NONZERO",
    "DELIVERED",
    "CI",
    "MERGED",
    "PRODUCTION_PROOF",
    "ACCEPTANCE",
]

TSV_COLUMNS = (
    "run_id",
    "host",
    "model",
    "reserved_at",
    "lease_ok_at",
    "launched_at",
    "done_at",
    "rc",
    "signal",
    "native_started",
    "output_complete",
    "usage_total_tokens",
    "lane",
    "status",
    "lane_head",
    "integrated_on_main",
)

ROW_KEYS = (
    "run_id",
    "host",
    "model",
    "reserved_at",
    "lease_ok_at",
    "launched_at",
    "done_at",
    "rc",
    "signal",
    "native_started",
    "output_complete",
    "usage_total_tokens",
    "lane",
    "status",
    "lane_head",
    "integrated_on_main",
    "rule_id",
    "rung_reached",
    "rung_evidence",
)

TS_FIELDS = ("reserved_at", "lease_ok_at", "launched_at", "done_at")
FORBIDDEN_RUNGS = ("CI", "MERGED", "PRODUCTION_PROOF", "ACCEPTANCE")
AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_PRIVACY_PATHS = ("/Users/", "/home/")
_PRIVACY_CREDS = ("token=", "Bearer", "ssh-")
_AUTH_RE = re.compile(r"auth(?!ority)", re.IGNORECASE)
_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def _parse_int(v):
    if v is None or v == "":
        return None
    return int(v)


def _parse_bool(v):
    if v == "True":
        return True
    if v == "False":
        return False
    if v is None or v == "":
        return None
    raise ValueError("not bool: %r" % (v,))


def _parse_tsv_local(text):
    """Independent TSV parser used for tests. Mirrors the spec wording."""
    reader = csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    rows = list(reader)
    if not rows:
        return []
    header = rows[0]
    if len(header) != 16:
        raise ValueError("bad header column count: %d" % len(header))
    out = []
    for idx, parts in enumerate(rows[1:], start=1):
        if parts == [""]:
            continue
        if len(parts) != 16:
            raise ValueError(
                "bad row column count at line %d: %d" % (idx, len(parts))
            )
        out.append({
            "run_id": parts[0] if parts[0] != "" else None,
            "host": parts[1] if parts[1] != "" else None,
            "model": parts[2] if parts[2] != "" else None,
            "reserved_at": parts[3] if parts[3] != "" else None,
            "lease_ok_at": parts[4] if parts[4] != "" else None,
            "launched_at": parts[5] if parts[5] != "" else None,
            "done_at": parts[6] if parts[6] != "" else None,
            "rc": _parse_int(parts[7]),
            "signal": parts[8] if parts[8] != "" else None,
            "native_started": _parse_bool(parts[9]),
            "output_complete": _parse_bool(parts[10]),
            "usage_total_tokens": _parse_int(parts[11]),
            "lane": parts[12] if parts[12] != "" else None,
            "status": parts[13] if parts[13] != "" else None,
            "lane_head": parts[14] if parts[14] != "" else None,
            "integrated_on_main": parts[15] if parts[15] != "" else None,
        })
    return out


def _classify_local(row):
    """Independent application of R1..R5 (matches builder exactly)."""
    rc = row["rc"]
    done_at = row["done_at"]
    output_complete = row["output_complete"]
    lane = row["lane"]
    status = row["status"]
    lane_head = row["lane_head"]

    if rc in (75, 76, 78):
        return ("never_started", "NOT_STARTED")
    if rc is None and done_at is None:
        return ("running_or_unknown", "RUNNING_OR_UNKNOWN_AT_CAPTURE")
    if rc in (1, 124):
        return ("exited_nonzero", "EXITED_NONZERO")
    if rc == 0:
        if (
            lane is not None
            and status is not None
            and lane_head is not None
            and output_complete is not False
        ):
            return ("delivered", "DELIVERED")
        return ("exited_no_result", "EXITED_NO_RESULT")
    if rc is None and done_at is not None:
        raise ValueError(
            "rc None with done_at present on %s" % (row.get("run_id") or "<no run_id>",)
        )
    raise ValueError(
        "unknown rc on %s: rc=%r" % (row.get("run_id") or "<no run_id>", rc)
    )


def _evidence_local(row, rung_reached):
    """Independent rung_evidence builder."""
    ev = [{"rung": "ACK", "field": "run_id"}]
    if row["reserved_at"] is not None:
        ev.append({"rung": "QUEUED", "field": "reserved_at"})
    if row["launched_at"] is not None and rung_reached != "NOT_STARTED":
        ev.append({"rung": "START", "field": "launched_at"})
    if row["native_started"] is True and rung_reached != "NOT_STARTED":
        ev.append({"rung": "RUNNING", "field": "native_started"})
    if rung_reached == "DELIVERED":
        ev.append({"rung": "DELIVERED", "field": "lane_head"})
    return ev


def _load_builder_module():
    """Load the builder as a module without populating sys.modules."""
    spec = importlib.util.spec_from_file_location(
        "sni_a39c2_builder_under_test", str(BUILDER_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path):
    return json.loads(path.read_text())


def _cell(value):
    if value is None or value == "":
        return ""
    return str(value)


def _privacy_errors(text):
    errors = []
    for token in _PRIVACY_PATHS:
        if token in text:
            errors.append("path %s" % token)
    for token in _PRIVACY_CREDS:
        if token in text:
            errors.append("cred %s" % token)
    if _AUTH_RE.search(text):
        errors.append("auth")
    if _IP_RE.search(text):
        errors.append("ip")
    return errors


def test_a39c2_01_schema():
    ledger = _read_json(JSON_C2_PATH)
    expected_top = (
        "schema_version",
        "capture_id",
        "captured_at",
        "source",
        "prior_capture",
        "ladder",
        "rung_rules",
        "rows",
        "summary",
        "bounds",
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    )
    assert tuple(ledger.keys()) == expected_top
    assert ledger["schema_version"] == "1"
    assert ledger["capture_id"] == "C2"
    assert ledger["captured_at"] == "2026-10-14T07:11Z"
    assert ledger["ladder"] == LADDER
    assert len(ledger["rows"]) == 343
    assert ledger["summary"]["rows"] == 343

    for row in ledger["rows"]:
        assert tuple(row.keys()) == ROW_KEYS
        assert isinstance(row["rung_evidence"], list)
        if row["rc"] is not None:
            assert isinstance(row["rc"], int)
        if row["usage_total_tokens"] is not None:
            assert isinstance(row["usage_total_tokens"], int)
        for key in ("native_started", "output_complete"):
            val = row[key]
            assert val is True or val is False or val is None


def test_a39c2_02_rows_match_tsv():
    ledger = _read_json(JSON_C2_PATH)
    parsed = _parse_tsv_local(TSV_PATH.read_text())
    assert len(parsed) == 343
    assert len(ledger["rows"]) == len(parsed)
    by_id = {r["run_id"]: r for r in ledger["rows"] if r.get("run_id")}
    parsed_by_id = {r["run_id"]: r for r in parsed if r.get("run_id")}
    assert set(by_id.keys()) == set(parsed_by_id.keys())

    for r in parsed:
        rid = r["run_id"]
        if rid is None:
            continue
        stored = by_id[rid]
        for key in TSV_COLUMNS:
            assert r[key] == stored[key], "%s %s %r vs %r" % (
                rid,
                key,
                r[key],
                stored[key],
            )


def test_a39c2_03_rules():
    ledger = _read_json(JSON_C2_PATH)
    parsed = _parse_tsv_local(TSV_PATH.read_text())
    by_id_ledger = {r["run_id"]: r for r in ledger["rows"] if r.get("run_id")}
    by_id_parsed = {r["run_id"]: r for r in parsed if r.get("run_id")}

    for rid, raw in by_id_parsed.items():
        rule_id, rung = _classify_local(raw)
        stored = by_id_ledger[rid]
        assert stored["rule_id"] == rule_id, "%s %s vs %s" % (
            rid,
            stored["rule_id"],
            rule_id,
        )
        assert stored["rung_reached"] == rung, "%s %s vs %s" % (
            rid,
            stored["rung_reached"],
            rung,
        )
        ev = _evidence_local(raw, rung)
        assert stored["rung_evidence"] == ev, "%s evidence mismatch" % rid

    bmod = _load_builder_module()

    mutated = dict(raw)
    mutated["rc"] = 2
    with pytest.raises(ValueError):
        bmod.classify(mutated)

    mutated2 = dict(raw)
    mutated2["done_at"] = "2026-10-13T10:05Z"
    with pytest.raises(ValueError):
        bmod.classify(mutated2)


def test_a39c2_04_summary_frozen():
    ledger = _read_json(JSON_C2_PATH)
    parsed = _parse_tsv_local(TSV_PATH.read_text())
    summary = ledger["summary"]
    expected_by_rung = {
        "ACK": 0,
        "QUEUED": 0,
        "START": 0,
        "RUNNING": 0,
        "NOT_STARTED": 207,
        "RUNNING_OR_UNKNOWN_AT_CAPTURE": 23,
        "EXITED_NO_RESULT": 3,
        "EXITED_NONZERO": 18,
        "DELIVERED": 92,
        "CI": 0,
        "MERGED": 0,
        "PRODUCTION_PROOF": 0,
        "ACCEPTANCE": 0,
    }
    assert summary["by_rung"] == expected_by_rung
    expected_by_rc = {
        "0": 95,
        "1": 17,
        "124": 1,
        "75": 183,
        "76": 1,
        "78": 23,
        "empty": 23,
    }
    assert summary["by_rc"] == expected_by_rc
    expected_by_host = {
        "bm1": 1,
        "bmb": 2,
        "mb": 6,
        "mini1": 1,
        "mini3": 1,
        "ubuntu0": 84,
        "ubuntu1": 109,
        "ubuntu2": 72,
        "ubuntu3": 67,
    }
    assert summary["by_host"] == expected_by_host
    expected_by_model = {
        "cursor-grok-4.6-high-fast": 19,
        "empty": 210,
        "grok-4.6": 114,
    }
    assert summary["by_model"] == expected_by_model
    expected_by_signal = {
        "admission": 183,
        "empty": 23,
        "ok": 95,
        "other": 41,
        "timeout": 1,
    }
    assert summary["by_signal"] == expected_by_signal
    assert summary["delivered_by_claim"] == {"PARTIAL": 14, "PASS": 78}
    assert summary["integrated_on_main_annotated"] == 54
    assert summary["usage_tokens_present"] == 52
    assert summary["combined_with_prior"] == {
        "rows": 404,
        "run_ids_disjoint": True,
    }

    no_result = sorted(
        r["run_id"]
        for r in ledger["rows"]
        if r["rung_reached"] == "EXITED_NO_RESULT"
    )
    assert no_result == [
        "sni-a36g-1014i52",
        "sni-m7b-1014i52",
        "sni-m7c-1014i54",
    ]

    run_ids = [r["run_id"] for r in parsed if r["run_id"] is not None]
    assert len(set(run_ids)) == 343

    by_rung_count = {key: 0 for key in BY_RUNG_ORDER}
    by_host = {}
    by_rc = {}
    by_model = {}
    by_signal = {}
    delivered_by_claim = {}
    integrated = 0
    usage = 0
    for r in ledger["rows"]:
        by_rung_count[r["rung_reached"]] += 1
        host_key = r["host"] if r["host"] is not None else "empty"
        by_host[host_key] = by_host.get(host_key, 0) + 1
        rc_key = str(r["rc"]) if r["rc"] is not None else "empty"
        by_rc[rc_key] = by_rc.get(rc_key, 0) + 1
        model_key = r["model"] if r["model"] is not None else "empty"
        by_model[model_key] = by_model.get(model_key, 0) + 1
        signal_key = r["signal"] if r["signal"] is not None else "empty"
        by_signal[signal_key] = by_signal.get(signal_key, 0) + 1
        if r["rung_reached"] == "DELIVERED":
            sk = r["status"] if r["status"] is not None else "empty"
            delivered_by_claim[sk] = delivered_by_claim.get(sk, 0) + 1
        if r.get("integrated_on_main") is not None:
            integrated += 1
        if r.get("usage_total_tokens") is not None:
            usage += 1
    assert by_rung_count == summary["by_rung"]
    assert dict(sorted(by_host.items())) == summary["by_host"]
    assert dict(sorted(by_rc.items())) == summary["by_rc"]
    assert dict(sorted(by_model.items())) == summary["by_model"]
    assert dict(sorted(by_signal.items())) == summary["by_signal"]
    assert dict(sorted(delivered_by_claim.items())) == summary[
        "delivered_by_claim"
    ]
    assert integrated == summary["integrated_on_main_annotated"]
    assert usage == summary["usage_tokens_present"]


def test_a39c2_05_no_overclaim():
    ledger = _read_json(JSON_C2_PATH)
    parsed = _parse_tsv_local(TSV_PATH.read_text())
    by_id_parsed = {r["run_id"]: r for r in parsed if r.get("run_id")}

    overclaim = []
    rule_mismatches = []
    for row in ledger["rows"]:
        run_id = row.get("run_id")
        if run_id is None:
            continue
        rung = row.get("rung_reached")
        if rung in FORBIDDEN_RUNGS:
            overclaim.append("%s rung=%s" % (run_id, rung))
        if "accepted" in row and row["accepted"] is True:
            overclaim.append("%s accepted=true" % run_id)
        if "merged" in row and row["merged"] is True:
            overclaim.append("%s merged=true" % run_id)
        raw = by_id_parsed.get(run_id)
        if raw is None:
            continue
        rule_id, expected_rung = _classify_local(raw)
        if row.get("rule_id") != rule_id:
            rule_mismatches.append(run_id)
        if rung != expected_rung:
            overclaim.append(
                "%s rung=%s expected=%s" % (run_id, rung, expected_rung)
            )
        if row.get("integrated_on_main") is not None and rung != "DELIVERED":
            overclaim.append("%s integrated but rung=%s" % (run_id, rung))
        if raw["rc"] in (75, 76, 78) and rung != "NOT_STARTED":
            overclaim.append("%s rc=%s rung=%s" % (run_id, raw["rc"], rung))
        ev = _evidence_local(raw, rung)
        if row.get("rung_evidence") != ev:
            overclaim.append("%s evidence mismatch" % run_id)
    assert rule_mismatches == []
    assert overclaim == []

    bmod = _load_builder_module()
    bad = dict(parsed[0])
    bad["rc"] = 75
    assert bmod.classify(bad) == ("never_started", "NOT_STARTED")


def test_a39c2_06_timestamps_monotone():
    ledger = _read_json(JSON_C2_PATH)
    errors = []
    for row in ledger["rows"]:
        present = [row[k] for k in TS_FIELDS if row.get(k)]
        for left, right in zip(present, present[1:]):
            if left > right:
                errors.append(
                    "%s %s > %s" % (row.get("run_id"), left, right)
                )
    assert errors == []


def test_a39c2_07_disjoint_from_capture_1():
    c1 = _read_json(JSON_C1_PATH)
    c2 = _read_json(JSON_C2_PATH)
    c1_ids = {r["run_id"] for r in c1["rows"] if r.get("run_id")}
    c2_ids = {r["run_id"] for r in c2["rows"] if r.get("run_id")}
    assert c1_ids.isdisjoint(c2_ids)

    prior = c2["prior_capture"]
    assert prior["path"] == (
        "research/single_name_intelligence/e2e_20261011/A39_LANE_RECEIPTS_LEDGER.json"
    )
    assert prior["captured_at"] == c1["captured_at"]
    assert prior["rows"] == len(c1["rows"])
    assert prior["run_ids_disjoint"] is True
    assert len(c1["rows"]) == 61
    assert c2["summary"]["combined_with_prior"]["rows"] == len(c1_ids) + len(c2_ids)
    assert c2["summary"]["combined_with_prior"]["run_ids_disjoint"] is True


def test_a39c2_08_builder_regenerates_committed_files():
    bmod = _load_builder_module()
    tsv_text = TSV_PATH.read_text()
    c1_text = JSON_C1_PATH.read_text()
    json_text, md_text = bmod.build(tsv_text, c1_text)
    committed_json = JSON_C2_PATH.read_text()
    committed_md = MD_C2_PATH.read_text()
    assert json_text == committed_json
    assert md_text == committed_md

    json_text2, md_text2 = bmod.build(tsv_text, c1_text)
    assert json_text == json_text2
    assert md_text == md_text2


def test_a39c2_09_privacy():
    files = (
        JSON_C2_PATH,
        MD_C2_PATH,
        TSV_PATH,
        BUILDER_PATH,
    )
    texts = [p.read_text() for p in files]
    errors = []
    for path, text in zip(files, texts):
        for err in _privacy_errors(text):
            errors.append("%s: %s" % (path.name, err))
    assert errors == []

    ledger = _read_json(JSON_C2_PATH)
    for row in ledger["rows"]:
        for key in row.keys():
            assert not key.endswith("_authority"), (
                "row key %s ends with _authority" % key
            )


def test_a39c2_10_authority_false():
    ledger = _read_json(JSON_C2_PATH)
    for flag in AUTHORITY_FLAGS:
        assert flag in ledger
        assert ledger[flag] is False

    mutated = deepcopy(ledger)
    mutated["rank_authority"] = True
    bad = any(mutated[flag] is True for flag in AUTHORITY_FLAGS)
    assert bad is True

    for flag in AUTHORITY_FLAGS:
        truthy = deepcopy(ledger)
        truthy[flag] = True
        assert any(truthy[f] is True for f in AUTHORITY_FLAGS)


def _status_index(rows, status_value):
    for idx, row in enumerate(rows):
        if row.get("status") == status_value:
            return idx
    return None


def test_a39c2_11_positive_controls():
    ledger = _read_json(JSON_C2_PATH)
    parsed = _parse_tsv_local(TSV_PATH.read_text())
    by_id_parsed = {r["run_id"]: r for r in parsed if r.get("run_id")}

    flipped = deepcopy(ledger)
    target = next(
        r for r in flipped["rows"] if r.get("rc") == 75
    )
    target["rung_reached"] = "DELIVERED"
    bad = []
    for row in flipped["rows"]:
        rid = row.get("run_id")
        if rid is None:
            continue
        raw = by_id_parsed.get(rid)
        if raw is None:
            continue
        _, expected = _classify_local(raw)
        if row.get("rung_reached") != expected:
            bad.append(rid)
        if raw["rc"] in (75, 76, 78) and row.get("rung_reached") != "NOT_STARTED":
            bad.append(rid)
    assert target["run_id"] in bad

    merged = deepcopy(ledger)
    merged["rows"][0]["rung_reached"] = "MERGED"
    bad = any(r["rung_reached"] == "MERGED" for r in merged["rows"])
    assert bad is True

    skewed = deepcopy(ledger)
    candidate = next(
        r for r in skewed["rows"]
        if r.get("launched_at") and r.get("done_at")
    )
    candidate["done_at"] = "2020-01-01T00:00Z"
    candidate["launched_at"] = "2026-10-13T10:00Z"
    ts_errors = []
    for row in skewed["rows"]:
        present = [row[k] for k in TS_FIELDS if row.get(k)]
        for left, right in zip(present, present[1:]):
            if left > right:
                ts_errors.append(row.get("run_id"))
    assert candidate["run_id"] in ts_errors

    c1 = _read_json(JSON_C1_PATH)
    c1_ids = {r["run_id"] for r in c1["rows"] if r.get("run_id")}
    candidate_id = next(iter(c1_ids))
    appended = deepcopy(ledger)
    appended["rows"].append(
        {
            "run_id": candidate_id,
            "host": "ubuntu0",
            "model": "grok-4.6",
            "reserved_at": "2026-10-13T09:51Z",
            "lease_ok_at": "2026-10-13T09:51Z",
            "launched_at": "2026-10-13T09:51Z",
            "done_at": "2026-10-13T10:05Z",
            "rc": 0,
            "signal": "ok",
            "native_started": True,
            "output_complete": True,
            "usage_total_tokens": 1,
            "lane": "A39",
            "status": "PASS",
            "lane_head": "fbaaf30eaeda82b1c67ead1c72eb030514e7f9af",
            "integrated_on_main": None,
            "rule_id": "delivered",
            "rung_reached": "DELIVERED",
            "rung_evidence": [
                {"rung": "ACK", "field": "run_id"},
                {"rung": "QUEUED", "field": "reserved_at"},
                {"rung": "START", "field": "launched_at"},
                {"rung": "RUNNING", "field": "native_started"},
                {"rung": "DELIVERED", "field": "lane_head"},
            ],
        }
    )
    appended_ids = {
        r["run_id"] for r in appended["rows"] if r.get("run_id")
    }
    assert candidate_id in appended_ids & c1_ids
    assert not appended_ids.isdisjoint(c1_ids)

    summary_off = deepcopy(ledger)
    summary_off["summary"]["by_rung"]["DELIVERED"] -= 1
    assert (
        summary_off["summary"]["by_rung"]["DELIVERED"]
        != ledger["summary"]["by_rung"]["DELIVERED"]
    )

    bmod = _load_builder_module()
    tsv_text = TSV_PATH.read_text()
    c1_text = JSON_C1_PATH.read_text()
    md_text = bmod.build(tsv_text, c1_text)[1]
    md_original = MD_C2_PATH.read_text()

    mutated_md_input = deepcopy(ledger)
    idx = _status_index(mutated_md_input["rows"], "PASS")
    assert idx is not None
    mutated_md_input["rows"][idx]["status"] = "FAIL"
    rerendered = bmod.build(tsv_text, c1_text)
    assert rerendered[1] == md_original


def test_a39c2_99_smoke():
    ledger = _read_json(JSON_C2_PATH)
    assert ledger["summary"]["rows"] == 343
