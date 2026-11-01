"""Bound owner-calendar tests; synthetic decisions never imply market admission."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.entry_radar.replay.rs_pullback_launch_data import (
    CALENDAR_MAX_BYTES, CALENDAR_PROJECTION_SHA256, InputContractError,
    _calendar_at, bind_calendar_projection, build_input_panel, digest,
)
from scripts.entry_radar_rs_pullback_phase1 import main, read_calendar_projection
from tests.test_entry_radar_rs_pullback_phase1 import candidate, fixture

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "research/live_entry_radar/rs_pullback_launch/CALENDAR_ADMISSION_2026-10-07.json"


def actual_snapshot():
    return json.loads(PROOF.read_text())["calendar_source_snapshot"]


def ns(instant):
    return int(datetime.fromisoformat(instant.replace("Z", "+00:00")).timestamp()) * 10**9


def synthetic_snapshot(known="2015-12-01T00:00:00Z"):
    # Deliberate synthetic clock only in tests. Production CLI accepts no override.
    snapshot = actual_snapshot()
    receipt = snapshot["read_receipt"]
    receipt["read_started_at_utc_ns"] = ns(known)
    receipt["read_completed_at_utc_ns"] = ns(known)
    reseal(snapshot)
    return snapshot


def reseal(snapshot):
    receipt = snapshot["read_receipt"]
    receipt["receipt_sha256"] = digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})


def replace_payload(snapshot, text):
    snapshot["projection_json"] = text
    receipt = snapshot["read_receipt"]
    receipt["byte_length"] = len(text.encode())
    receipt["byte_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    reseal(snapshot)


def panel_frame(snapshot=None, decision="2026-10-06T14:00:00Z", session="2026-10-06"):
    bundle = fixture(candidates=[candidate(decision=decision, session=session)])
    bundle["calendar"] = snapshot if snapshot is not None else synthetic_snapshot()
    return build_input_panel(bundle)["frames"][0]


def visible(snapshot):
    return _calendar_at(snapshot, datetime(2030, 1, 1, tzinfo=timezone.utc))


def test_real_retained_evidence_is_exact_and_never_grants_authority():
    proof = json.loads(PROOF.read_text())
    assert proof["proof_sha256"] == digest({k: v for k, v in proof.items() if k != "proof_sha256"})
    snapshot = proof["calendar_source_snapshot"]
    payload = snapshot["projection_json"].encode()
    assert len(payload) == 75778
    assert hashlib.sha256(payload).hexdigest() == CALENDAR_PROJECTION_SHA256
    assert len(visible(snapshot)["sessions"]) == 3267
    assert proof["overall_panel"] == "NOT_ADMITTED"
    assert set(proof["scientific_claims"].values()) == {"NOT_TESTED"}
    assert not any(proof["authority"].values())
    assert proof["provider_calls"] == 0 and proof["market_outcomes_read"] is False


@pytest.mark.parametrize("day,opening,closing,previous", [
    ("2026-03-06", "2026-03-06T14:30:00Z", "2026-03-06T21:00:00Z", "2026-03-05"),
    ("2026-03-09", "2026-03-09T13:30:00Z", "2026-03-09T20:00:00Z", "2026-03-06"),
    ("2026-10-30", "2026-10-30T13:30:00Z", "2026-10-30T20:00:00Z", "2026-10-29"),
    ("2026-11-02", "2026-11-02T14:30:00Z", "2026-11-02T21:00:00Z", "2026-10-30"),
    ("2026-11-27", "2026-11-27T14:30:00Z", "2026-11-27T18:00:00Z", "2026-11-25"),
    ("2026-12-24", "2026-12-24T14:30:00Z", "2026-12-24T18:00:00Z", "2026-12-23"),
    ("2018-12-06", "2018-12-06T14:30:00Z", "2018-12-06T21:00:00Z", "2018-12-04"),
    ("2025-01-10", "2025-01-10T14:30:00Z", "2025-01-10T21:00:00Z", "2025-01-08"),
])
def test_owner_utc_windows_dst_early_close_and_exceptional_predecessor(day, opening, closing, previous):
    window = visible(synthetic_snapshot())["sessions"][day]
    assert window == {"open": opening, "close": closing, "previous_session": previous}


@pytest.mark.parametrize("day", ["2018-12-05", "2025-01-09", "2026-07-03", "2026-10-10"])
def test_closed_dates_refuse_without_inventing_session(day):
    result = panel_frame(decision=day + "T16:00:00Z", session=day)
    assert result["refusals"] == ["SESSION_NOT_IN_OWNER_CALENDAR"]
    assert result["label_endpoint"] is None and not result["bars"]


@pytest.mark.parametrize("day,reason", [
    ("2015-12-31", "CALENDAR_COVERAGE_UNKNOWN"),
    ("2029-01-02", "CALENDAR_COVERAGE_UNKNOWN"),
    ("2016-01-04", "CALENDAR_PREDECESSOR_UNKNOWN"),
])
def test_unknown_coverage_or_predecessor_refuses(day, reason):
    result = panel_frame(decision=day + "T16:00:00Z", session=day)
    assert result["refusals"] == [reason]
    assert result["eligible"] is None and result["availability"] == "unavailable"


def test_full_panel_regular_window_and_early_close_endpoint():
    frame = panel_frame()
    assert frame["availability"] == "available"
    assert frame["bars"]["stock"]["30"]["start"] == "2026-10-06T13:30:00Z"
    assert not any(frame["authority"].values())
    early = panel_frame(decision="2026-11-27T17:00:00Z", session="2026-11-27")
    assert early["label_endpoint"] == "2026-11-27T18:00:00Z"
    assert early["label_status"] == "CENSORED_SESSION_END"
    after_close = panel_frame(decision="2026-11-27T18:01:00Z", session="2026-11-27")
    assert after_close["refusals"] == ["DECISION_OUTSIDE_RTH"]


def test_read_visibility_precedes_even_malformed_future_semantics_and_seal():
    future = synthetic_snapshot("2026-10-07T00:00:00Z")
    original = panel_frame(future)
    assert original["refusals"] == ["CALENDAR_NOT_KNOWN_AT_DECISION"]
    assert original["calendar_receipt_sha256"] is None
    future["projection_json"] = '{"sessions": invalid and unfinished'
    future["read_receipt"]["source_files"] = None
    future["read_receipt"]["receipt_sha256"] = "broken"
    assert panel_frame(future) == original
    future["read_receipt"]["read_completed_at_utc_ns"] += 1
    assert panel_frame(future) == original


def test_nanosecond_completion_cannot_be_rounded_back_into_decision():
    snapshot = synthetic_snapshot("2026-10-06T14:00:00Z")
    assert panel_frame(snapshot)["availability"] == "available"
    snapshot["read_receipt"]["read_completed_at_utc_ns"] += 1
    reseal(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_NOT_KNOWN_AT_DECISION"]


@pytest.mark.parametrize("mutation", [
    "bytes", "length", "hash", "seal", "revision", "source_file",
    "artifact", "clock_order", "bool_clock", "missing_clock",
])
def test_visible_mismatch_cannot_enter_panel(mutation):
    snapshot = synthetic_snapshot()
    receipt = snapshot["read_receipt"]
    if mutation == "bytes":
        snapshot["projection_json"] += "\n"
    elif mutation == "length":
        receipt["byte_length"] += 1
    elif mutation == "hash":
        receipt["byte_sha256"] = "0" * 64
    elif mutation == "seal":
        receipt["receipt_sha256"] = "0" * 64
    elif mutation == "revision":
        receipt["source_revision"] = "0" * 40
    elif mutation == "source_file":
        receipt["source_files"]["lib/__init__.py"] = "0" * 64
    elif mutation == "artifact":
        receipt["artifact_ref"] = "https://example.invalid/calendar"
    elif mutation == "clock_order":
        receipt["read_started_at_utc_ns"] = receipt["read_completed_at_utc_ns"] + 1
    elif mutation == "bool_clock":
        receipt["read_completed_at_utc_ns"] = True
    elif mutation == "missing_clock":
        del receipt["read_completed_at_utc_ns"]
    if mutation != "seal":
        reseal(snapshot)
    with pytest.raises(InputContractError):
        visible(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_INPUT_INVALID"]


@pytest.mark.parametrize("text", [
    "{", '{"schema":1,"schema":2}', '{"source":[]}', 'null', 'NaN',
])
def test_visible_malformed_projection_refuses_even_with_resealed_receipt(text):
    snapshot = synthetic_snapshot()
    replace_payload(snapshot, text)
    with pytest.raises(InputContractError):
        visible(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_INPUT_INVALID"]


def test_self_consistent_altered_owner_projection_is_still_unreviewed():
    snapshot = synthetic_snapshot()
    projection = json.loads(snapshot["projection_json"])
    projection["sessions"]["2026-10-06"][1] = 780
    replace_payload(snapshot, json.dumps(projection))
    with pytest.raises(InputContractError, match="unreviewed"):
        visible(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_INPUT_INVALID"]


def mixed_bundle(reverse=False):
    bundle = fixture(candidates=[
        candidate("before_read", "2026-10-06T14:00:00Z", "2026-10-06"),
        candidate("after_read", "2026-10-08T14:00:00Z", "2026-10-08"),
    ])
    bundle["calendar"] = actual_snapshot()
    if reverse:
        bundle["candidates"].reverse()
    return bundle


def assert_mixed_refusals(original, changed):
    assert changed["retained_count"] == changed["population_count"] == 2
    assert [f["candidate_id"] for f in changed["frames"]] == [
        f["candidate_id"] for f in original["frames"]]
    before = next(f for f in original["frames"] if f["candidate_id"] == "before_read")
    after_before = next(f for f in changed["frames"] if f["candidate_id"] == "before_read")
    assert json.dumps(after_before, sort_keys=True).encode() == json.dumps(before, sort_keys=True).encode()
    assert after_before["refusals"] == ["CALENDAR_NOT_KNOWN_AT_DECISION"]
    invalid = next(f for f in changed["frames"] if f["candidate_id"] == "after_read")
    assert invalid["refusals"] == ["CALENDAR_INPUT_INVALID"]
    assert invalid["availability"] == "unavailable"
    assert invalid["eligible"] is None and invalid["condition_met"] is None
    assert invalid["calendar_receipt_sha256"] is None
    assert not invalid["bars"] and not any(invalid["authority"].values())


def corrupt_projection(snapshot, kind):
    if kind == "surrogate":
        # Valid ASCII replay JSON can decode to a string that is not UTF-8.
        snapshot["projection_json"] = "\ud800"
    else:
        replace_payload(snapshot, "{")


@pytest.mark.parametrize("kind", ["malformed_json", "surrogate"])
@pytest.mark.parametrize("reverse", [False, True])
def test_mixed_panel_retains_population_when_visible_projection_is_malformed(reverse, kind):
    bundle = mixed_bundle(reverse)
    original = build_input_panel(bundle)
    assert next(f for f in original["frames"] if f["candidate_id"] == "after_read")[
        "calendar_receipt_sha256"] is not None
    corrupt_projection(bundle["calendar"], kind)
    replay_json = json.dumps(bundle, ensure_ascii=True)
    assert replay_json.isascii()
    changed = build_input_panel(json.loads(replay_json))
    assert_mixed_refusals(original, changed)


@pytest.mark.parametrize("kind", ["malformed_json", "surrogate"])
@pytest.mark.parametrize("reverse", [False, True])
def test_actual_cli_retains_mixed_panel_when_visible_projection_is_malformed(tmp_path, reverse, kind):
    source = tmp_path / "mixed-input.json"
    bundle = mixed_bundle(reverse)
    source.write_text(json.dumps(bundle))

    def run():
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/entry_radar_rs_pullback_phase1.py"),
             "--input-panel", str(source)],
            capture_output=True, text=True, check=False)

    control = run()
    assert control.returncode == 0, control.stderr
    original = json.loads(control.stdout)
    corrupt_projection(bundle["calendar"], kind)
    replay_json = json.dumps(bundle, ensure_ascii=True)
    assert replay_json.isascii()
    source.write_text(replay_json, encoding="ascii")
    repaired = run()
    assert repaired.returncode == 0, repaired.stderr
    assert not repaired.stderr
    assert_mixed_refusals(original, json.loads(repaired.stdout))


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_calendar_implementation_errors_are_not_converted_to_input_refusals(monkeypatch, error_type):
    def broken_resolver(*args):
        raise error_type("implementation failure")

    monkeypatch.setattr(
        "engine.entry_radar.replay.rs_pullback_launch_data._calendar_at", broken_resolver)
    with pytest.raises(error_type, match="implementation failure"):
        build_input_panel(mixed_bundle())


def test_snapshot_does_not_alias_receipt_and_preserved_original_replays():
    original = synthetic_snapshot()
    receipt = copy.deepcopy(original["read_receipt"])
    retained = bind_calendar_projection(original["projection_json"].encode(), receipt)
    before = panel_frame(retained)
    receipt["source_files"].clear()
    receipt["read_completed_at_utc_ns"] = ns("2027-01-01T00:00:00Z")
    assert panel_frame(retained) == before
    later = synthetic_snapshot("2026-10-07T00:00:00Z")
    assert panel_frame(later)["availability"] == "unavailable"
    assert panel_frame(retained) == before


def test_cli_real_single_read_receipt_and_snapshot_recovery(tmp_path, capsys, monkeypatch):
    projection = tmp_path / "calendar.json"
    projection.write_bytes(actual_snapshot()["projection_json"].encode())
    bundle = fixture()
    source = tmp_path / "input.json"
    source.write_text(json.dumps(bundle))
    original_open = Path.open
    reads = []

    def observed_open(path, *args, **kwargs):
        if path == projection and args and args[0] == "rb":
            reads.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observed_open)
    before = time.time_ns()
    assert main(["--input-panel", str(source), "--calendar-projection", str(projection)]) == 0
    after = time.time_ns()
    result = json.loads(capsys.readouterr().out)
    snapshot = result["calendar_source_snapshot"]
    receipt = snapshot["read_receipt"]
    assert len(reads) == 1
    assert before <= receipt["read_started_at_utc_ns"] <= receipt["read_completed_at_utc_ns"] <= after
    assert receipt["source_ref"] == str(projection.resolve())
    assert result["frames"][0]["refusals"] == ["CALENDAR_NOT_KNOWN_AT_DECISION"]
    # A replacement of the path does not change the retained original bytes.
    projection.write_text("{malformed replacement")
    bundle["calendar"] = snapshot
    assert build_input_panel(bundle) == result
    source.write_text(json.dumps(bundle))
    assert main(["--input-panel", str(source)]) == 0
    assert json.loads(capsys.readouterr().out) == result
    assert main(["--input-panel", str(source), "--calendar-projection", str(projection)]) == 0
    replaced = json.loads(capsys.readouterr().out)
    assert replaced["frames"] == result["frames"]
    assert replaced["input_bundle_sha256"] != result["input_bundle_sha256"]


def test_malformed_receipt_shape_refuses():
    snapshot = synthetic_snapshot()
    snapshot["read_receipt"] = []
    with pytest.raises(InputContractError, match="object"):
        visible(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_INPUT_INVALID"]
    snapshot = synthetic_snapshot()
    snapshot["read_receipt"]["source_ref"] = True
    reseal(snapshot)
    with pytest.raises(InputContractError, match="receipt"):
        visible(snapshot)
    assert panel_frame(snapshot)["refusals"] == ["CALENDAR_INPUT_INVALID"]


def test_cli_has_no_known_at_override_and_companion_requires_panel(tmp_path):
    with pytest.raises(SystemExit):
        main(["--input-panel", str(tmp_path / "x"), "--calendar-known-at", "2000-01-01"])
    with pytest.raises(SystemExit):
        main(["--census", str(tmp_path / "x"), "--calendar-projection", str(tmp_path / "y")])


@pytest.mark.parametrize("payload", [b"", b"x" * (CALENDAR_MAX_BYTES + 1), b"\xff"])
def test_actual_reader_refuses_empty_oversize_or_invalid_utf8(tmp_path, payload):
    source = tmp_path / "calendar.json"
    source.write_bytes(payload)
    with pytest.raises(InputContractError):
        read_calendar_projection(source)


def test_actual_reader_refuses_backward_clock(tmp_path, monkeypatch):
    source = tmp_path / "calendar.json"
    source.write_bytes(actual_snapshot()["projection_json"].encode())
    clocks = iter([2, 1])
    monkeypatch.setattr("scripts.entry_radar_rs_pullback_phase1.time.time_ns", lambda: next(clocks))
    with pytest.raises(InputContractError, match="backwards"):
        read_calendar_projection(source)
