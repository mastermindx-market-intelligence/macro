"""Synthetic owner-read integration; no market admission, publication, or outcomes."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engine.entry_radar.replay import identity_observation_snapshot as identity_reader
from engine.entry_radar.replay import rs_pullback_launch_data as panel
from engine.entry_radar.replay import rs_pullback_native_identity as native
from engine.entry_radar.replay import terminal_minute_observations as terminal
from lib.dataos.identity import IdentityError
from tests import test_entry_radar_identity_observation_snapshot as identity_fixture
from tests import test_entry_radar_terminal_minute_observations as minute_fixture

SYMBOLS = {"stock": "MU", "spy": "SPY", "qqq": "QQQ", "sector": "SMH"}
CUTOFF = "2026-10-07T14:16:00Z"
ANCHOR = "2026-10-07T14:00:00Z"
SECURITY = "SEC:US-XNAS-MU"


def identity_read(root, *, completed=CUTOFF, state=None):
    identity_fixture.generation(root, state=state)
    end = minute_fixture.ns(completed) if isinstance(completed, str) else completed
    with patch.object(identity_reader.time, "time_ns", side_effect=[end - 1, end]):
        return identity_reader.read_identity_snapshot(root)


def minute_read(path, symbol, *, completed=CUTOFF, rows=None, status="complete",
                prior=None, source_at="2026-10-07T14:15:00Z"):
    if rows is None:
        rows = minute_fixture.raw_rows()
        for row in rows:
            row["t"] += 86_400_000
    with patch.object(minute_fixture, "SYMBOL", symbol):
        capture = minute_fixture.v3_capture(
            prior=prior, rows=rows, status=status, source_at=source_at)
        payload = capture["captures"][-1]["payload"]
        payload["request"].update(from_date="2026-10-07", to_date="2026-10-07")
        minute_fixture.reseal(capture)
        minute_fixture.atomic_fixture(path, capture)
        observed = minute_fixture.read_at(path, completed)
    return observed, capture


def input_bundle(*, cutoffs=(CUTOFF,), symbols=None):
    result = minute_fixture.bundle([])
    result = json.loads(json.dumps(result).replace("2026-10-06", "2026-10-07")
                        .replace("2026-10-05", "2026-10-06"))
    result.pop("minutes")
    result.pop("terminal_minute_read_receipts")
    result.update(schema=native.INPUT_SCHEMA, window_policy_schema=panel.INPUT_V2_SCHEMA,
                  required_symbols=dict(SYMBOLS if symbols is None else symbols))
    for meta in result["streams"].values():
        meta.pop("identity")
        meta.pop("security_id")
    for record in result["contexts"]:
        record["security_id"] = SECURITY
    result["candidates"] = [
        {"candidate_id": f"candidate-{index}", "session": "2026-10-07",
         "decision_at": cutoff, "event_anchor_at": ANCHOR,
         "max_feature_age_seconds": 1800,
         "streams": {role: role for role in panel.ROLES}}
        for index, cutoff in enumerate(cutoffs)
    ]
    return result


@pytest.fixture
def observed(tmp_path):
    identity = identity_read(tmp_path / "reference")
    roles = {}
    for role, symbol in SYMBOLS.items():
        read, _ = minute_read(tmp_path / f"{symbol}.json", symbol)
        roles[role] = native.NativeRoleReads(read, (read,), identity)
    return input_bundle(), {"candidate-0": roles}


def build(bundle, reads):
    return native.build_input_panel_from_owner_reads(
        bundle, owner_reads=reads, reader_identity=minute_fixture.READER)


def binding(result, role="stock", index=0):
    return result["frames"][index]["stream_bindings"][role]["native_identity_binding"]


def stock_only(reads):
    return {"candidate-0": {"stock": reads["candidate-0"]["stock"]}}


def test_native_owner_join_preserves_refusals_and_provenance(observed):
    bundle, reads = observed
    original = copy.deepcopy(bundle)
    result = build(bundle, reads)
    assert bundle == original
    assert result["schema"] == native.PANEL_SCHEMA
    assert result["window_policy_schema"] == panel.INPUT_V2_SCHEMA
    assert result["population_count"] == result["retained_count"] == 1
    assert result["available_count"] == 0
    assert result["status"] == "SYNTHETIC_CONFORMANCE_ONLY"
    assert not any(result["authority"].values())
    assert result["detector_registered"] is result["outcomes_computed"] is False
    for role, symbol in SYMBOLS.items():
        report = binding(result, role)
        read = reads["candidate-0"][role]
        resolution = read.identity_read.alias_table().resolve_binding(
            "polygon", symbol, date(2026, 10, 7), decision_at=CUTOFF,
            snapshot_receipts=(read.identity_read.receipt,))
        assert report["identity_resolution"] == asdict(resolution)
        assert report["identity_read_receipt"] == read.identity_read.receipt.as_record()
        assert report["query"] == {"vendor": "polygon", "vendor_symbol": symbol,
                                   "event_session_date": "2026-10-07"}
        assert report["status"] == ("BOUND" if role == "stock" else "REFUSED")
        assert report["binding_sha256"] == panel.digest(
            {key: value for key, value in report.items() if key != "binding_sha256"})
        aggregate = result["frames"][0]["bars"][role]["30"]
        assert "TERMINAL_BASIS_UNPROVEN" in aggregate["refusals"]
        assert aggregate["ohlcv"] is None and aggregate["availability"] == "unavailable"
    assert binding(result, "spy")["identity_resolution"]["vendor_symbol"] is None
    assert binding(result, "spy")["identity_resolution"]["security_id"] is None
    assert result["frames"][0]["daily_context"]["security_id"] == SECURITY
    assert result["frames"][0]["eligible"] is None


def test_original_minute_rows_and_seals_reach_existing_aggregator_unchanged(observed):
    bundle, reads = observed
    seen = []
    original = panel._aggregate

    def inspect(rows, stream, meta, *args, **kwargs):
        if stream == "stock":
            seen.append(copy.deepcopy(rows))
            assert meta["security_id"] == SECURITY
        return original(rows, stream, meta, *args, **kwargs)

    with patch.object(panel, "_aggregate", side_effect=inspect):
        result = build(bundle, reads)
    read = reads["candidate-0"]["stock"]
    expected = terminal.decode_terminal_minute_observations(
        read.terminal_read, [read.terminal_read.receipt],
        reader_identity=minute_fixture.READER, symbol="MU", stream="stock",
        stream_metadata=None, cutoff=CUTOFF, output_schema=terminal.DECODE_SCHEMA_V2)["minutes"]
    assert len(seen) == 2 and all(rows == expected for rows in seen)
    assert all(row["security_id"] is None and row["basis_id"] is None for row in expected)
    assert all(row["receipt_sha256"] == panel.digest(
        {key: value for key, value in row.items() if key != "receipt_sha256"}) for row in expected)
    report = binding(result)
    assert report["terminal_rows_sha256"] == panel.digest(expected)
    assert [item["receipt_sha256"] for item in report["terminal_observations"]] == [
        row["receipt_sha256"] for row in expected]
    assert [item["revision_id"] for item in report["terminal_observations"]] == [
        row["revision_id"] for row in expected]
    assert report["terminal_read_receipts"] == [read.terminal_read.receipt]
    assert "MINUTE_IDENTITY_MISMATCH" not in result["frames"][0]["bars"]["stock"]["30"]["refusals"]


@pytest.mark.parametrize("field", ["identity", "security_id"])
def test_legacy_identity_metadata_cannot_enter_native_path(observed, field):
    bundle, reads = observed
    bundle["streams"]["stock"][field] = {"receipt_sha256": "a" * 64}
    with pytest.raises(panel.InputContractError, match="legacy identity"):
        build(bundle, reads)


@pytest.mark.parametrize("field", ["minutes", "terminal_minute_read_receipts"])
def test_caller_json_observations_cannot_enter_native_path(observed, field):
    bundle, reads = observed
    bundle[field] = []
    with pytest.raises(panel.InputContractError, match="owner-read"):
        build(bundle, reads)


def test_json_hashes_are_not_native_read_objects(observed):
    bundle, reads = observed
    read = reads["candidate-0"]["stock"]
    reads["candidate-0"]["stock"] = {
        "terminal_read": read.terminal_read.receipt,
        "identity_read": read.identity_read.receipt.as_record()}
    with pytest.raises(panel.InputContractError, match="NativeRoleReads"):
        build(bundle, reads)


def test_no_implicit_terminal_enrollment_or_identity_query(observed):
    bundle, reads = observed
    for role, read in reads["candidate-0"].items():
        reads["candidate-0"][role] = replace(read, enrolled_terminal_reads=())
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("no visible source query")):
        result = build(bundle, reads)
    for role in panel.ROLES:
        report = binding(result, role)
        assert report["status"] == "UNAVAILABLE" and report["query"] is None
        assert report["identity_resolution"] is None
        assert "identity_read_receipt" not in report


@pytest.mark.parametrize("status", ["complete", "partial", "failed"])
def test_empty_or_incomplete_capture_cannot_supply_a_query(tmp_path, observed, status):
    bundle, reads = observed
    read, _ = minute_read(tmp_path / "empty.json", "MU", rows=[], status=status)
    own = replace(reads["candidate-0"]["stock"], terminal_read=read,
                  enrolled_terminal_reads=(read,))
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("no source rows")):
        result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["query"] is None
    assert binding(result)["reason"] == "TERMINAL_MINUTES_UNAVAILABLE"
    assert result["retained_count"] == 1


def test_source_query_must_match_frozen_role_without_metadata_fallback(tmp_path, observed):
    bundle, reads = observed
    wrong, _ = minute_read(tmp_path / "wrong.json", "AAPL")
    own = replace(reads["candidate-0"]["stock"], terminal_read=wrong,
                  enrolled_terminal_reads=(wrong,))
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("invalid source cannot query")):
        result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["status"] == "REFUSED"
    assert binding(result)["reason"] == "TERMINAL_INPUT_INVALID"
    assert binding(result)["query"] is None
    assert result["retained_count"] == 1


def test_visible_rows_outside_owner_session_cannot_query_identity(tmp_path, observed):
    bundle, reads = observed
    previous, _ = minute_read(tmp_path / "previous.json", "MU",
                              rows=minute_fixture.raw_rows())
    own = replace(reads["candidate-0"]["stock"], terminal_read=previous,
                  enrolled_terminal_reads=(previous,))
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("no in-session source rows")):
        result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["query"] is None
    assert binding(result)["terminal_observations"] == []


def test_future_identity_payload_and_receipt_semantics_do_not_change_earlier_frame(tmp_path, observed):
    bundle, reads = observed
    future = identity_read(tmp_path / "future", completed="2026-10-07T14:17:00Z")
    roles = stock_only(reads)
    roles["candidate-0"]["stock"] = replace(roles["candidate-0"]["stock"], identity_read=future)
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("future identity semantics are invisible")):
        before = build(bundle, roles)
        bad_snapshot = replace(future.snapshot, receipt_bytes=b"{not JSON",
                               alias_json=b"{malformed future aliases")
        bad_receipt = replace(future.receipt, generation_id="malformed future generation",
                              artifact_sha256=(("malformed", "future"),))
        roles["candidate-0"]["stock"] = replace(
            roles["candidate-0"]["stock"],
            identity_read=replace(future, snapshot=bad_snapshot, receipt=bad_receipt))
        after = build(bundle, roles)
    assert before["frames"] == after["frames"]
    assert before["input_bundle_sha256"] != after["input_bundle_sha256"]
    report = binding(after)
    assert report["reason"] == "IDENTITY_NOT_KNOWN_AT_DECISION"
    assert report["identity_resolution"] is None
    assert "identity_read_receipt" not in report
    assert "malformed" not in panel.canonical(report)
    assert future.receipt.receipt_sha256 not in panel.canonical(report)


@pytest.mark.parametrize("clock", [None, 0, "0", "01", "nan", str(2**63)])
def test_invalid_completion_clock_is_not_misclassified_as_future(observed, clock):
    bundle, reads = observed
    roles = stock_only(reads)
    own = roles["candidate-0"]["stock"]
    receipt = replace(own.identity_read.receipt, read_completed_at_utc_ns=clock)
    roles["candidate-0"]["stock"] = replace(
        own, identity_read=replace(own.identity_read, receipt=receipt))
    result = build(bundle, roles)
    assert binding(result)["status"] == "REFUSED"
    assert binding(result)["reason"] == "IDENTITY_INPUT_INVALID"
    assert result["retained_count"] == 1


def test_eligible_native_owner_error_keeps_candidate_and_has_no_fallback(observed):
    bundle, reads = observed
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=IdentityError("visible native refusal")):
        result = build(bundle, reads)
    assert result["retained_count"] == 1
    assert all(binding(result, role)["reason"] == "IDENTITY_INPUT_INVALID" for role in panel.ROLES)
    assert all(binding(result, role)["identity_resolution"] is None for role in panel.ROLES)


def test_unexpected_implementation_error_is_not_disguised_as_source_unavailability(observed):
    bundle, reads = observed
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=RuntimeError("implementation defect")):
        with pytest.raises(RuntimeError, match="implementation defect"):
            build(bundle, reads)


def test_eligible_no_binding_retains_actual_native_receipt(tmp_path, observed):
    bundle, reads = observed
    bundle["required_symbols"]["stock"] = "UNBOUND"
    read, _ = minute_read(tmp_path / "unbound.json", "UNBOUND")
    own = replace(reads["candidate-0"]["stock"], terminal_read=read,
                  enrolled_terminal_reads=(read,))
    result = build(bundle, {"candidate-0": {"stock": own}})
    report = binding(result)
    assert report["status"] == "UNAVAILABLE"
    assert report["identity_resolution"]["reason"] == "NO_BINDING_AT_EVENT_DATE"
    assert report["identity_read_receipt"] == own.identity_read.receipt.as_record()


def test_identity_and_terminal_use_actual_decision_not_event_anchor(observed):
    bundle, reads = observed
    result = build(bundle, reads)
    report = binding(result)
    assert minute_fixture.ns(ANCHOR) < int(report["identity_read_receipt"]["read_completed_at_utc_ns"])
    assert report["status"] == "BOUND" and report["decision_at"] == CUTOFF
    assert result["frames"][0]["event_anchor_at"] == ANCHOR
    assert result["frames"][0]["bars"]["stock"]["30"]["end"] == ANCHOR


def test_each_candidate_retains_its_own_actual_read_and_full_population(tmp_path, observed):
    bundle, reads = observed
    bundle = input_bundle(cutoffs=(CUTOFF, "2026-10-07T14:18:00Z"))
    first = copy.copy(reads["candidate-0"])
    refused = identity_read(tmp_path / "refused", completed="2026-10-07T14:17:00Z", state="REFUSED")
    later = {role: replace(read, identity_read=refused) for role, read in first.items()}
    result = build(bundle, {"candidate-0": first, "candidate-1": later})
    baseline = build(input_bundle(), {"candidate-0": first})
    assert result["frames"][0] == baseline["frames"][0]
    assert binding(result, index=0)["status"] == "BOUND"
    assert binding(result, index=1)["status"] == "REFUSED"
    assert result["retained_count"] == result["population_count"] == 2


def test_same_clock_revision_conflict_survives_native_binding(tmp_path, observed):
    bundle, reads = observed
    bundle["candidates"][0]["decision_at"] = "2026-10-07T14:18:00Z"
    _, first_capture = minute_read(tmp_path / "revisions.json", "MU")
    rows = minute_fixture.raw_rows()
    for row in rows:
        row["t"] += 86_400_000
        row["c"] = 100.5
    second, _ = minute_read(
        tmp_path / "revisions.json", "MU", completed="2026-10-07T14:18:00Z",
        prior=first_capture, rows=rows, source_at="2026-10-07T14:16:00Z")
    own = replace(reads["candidate-0"]["stock"], terminal_read=second,
                  enrolled_terminal_reads=(second,))
    result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["status"] == "BOUND"
    assert len(binding(result)["terminal_observations"]) == 60
    assert "CONFLICTING_MINUTE_REVISION" in result["frames"][0]["bars"]["stock"]["30"]["refusals"]
    assert result["frames"][0]["bars"]["stock"]["30"]["ohlcv"] is None


@pytest.mark.parametrize("condition", ["outside_rth", "missing_session", "bad_anchor"])
def test_calendar_and_window_guards_run_before_owner_queries(observed, condition):
    bundle, reads = observed
    if condition == "outside_rth":
        bundle["candidates"][0]["decision_at"] = "2026-10-07T20:01:00Z"
    elif condition == "missing_session":
        bundle["calendar"]["sessions"].pop("2026-10-07")
    else:
        bundle["candidates"][0]["event_anchor_at"] = "2026-10-07T14:01:00Z"
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("calendar/window guard must run first")):
        result = build(bundle, reads)
    assert result["retained_count"] == 1
    assert result["frames"][0]["stream_bindings"] == {}
    assert result["frames"][0]["availability"] == "unavailable"


def test_missing_owner_reads_preserve_all_candidates(observed):
    bundle, _ = observed
    result = build(bundle, {})
    assert result["retained_count"] == result["population_count"] == 1
    assert all(binding(result, role)["status"] == "UNAVAILABLE" for role in panel.ROLES)
    assert result["frames"][0]["eligible"] is None


@pytest.mark.parametrize(("schema", "expected"), [
    (panel.INPUT_SCHEMA, "8967d0ca98e523f8c0cbe43a5d14bee624a215ac19a0a850fc04bc927825ebf4"),
    (panel.INPUT_V2_SCHEMA, "a108bf04770bf028a3f9fbec71848da32fb405864cf2d96a6d98bea52be2e242"),
])
def test_legacy_public_panels_match_retained_prechange_goldens(tmp_path, schema, expected):
    path = tmp_path / "legacy.json"
    minute_fixture.atomic_fixture(path, minute_fixture.v3_capture())
    with patch.object(terminal.uuid, "uuid4", return_value=SimpleNamespace(
            hex="0123456789abcdef0123456789abcdef")):
        read = minute_fixture.read_at(path, "2026-10-06T14:16:00Z")
    decoded = minute_fixture.decode(read, [read.receipt], cutoff="2026-10-06T14:16:00Z")
    bundle = minute_fixture.bundle(decoded["minutes"])
    bundle["schema"] = schema
    if schema == panel.INPUT_V2_SCHEMA:
        bundle["candidates"][0].update(event_anchor_at="2026-10-06T14:00:00Z",
                                       max_feature_age_seconds=1200)
    assert panel.digest(panel.build_input_panel(bundle)) == expected



def test_future_terminal_capture_diagnostics_do_not_change_earlier_native_frame(tmp_path, observed):
    bundle, reads = observed
    first, capture = minute_read(tmp_path / "prefix.json", "MU")
    own = replace(reads["candidate-0"]["stock"], terminal_read=first,
                  enrolled_terminal_reads=(first,))
    before = build(bundle, {"candidate-0": {"stock": own}})
    _, later_capture = minute_read(
        tmp_path / "prefix.json", "MU", prior=capture,
        source_at="2026-10-07T14:17:00Z", completed="2026-10-07T14:19:00Z")
    later_capture["captures"][-1]["payload"].update(
        schema="unsupported.future.payload", source="not-a-provider", symbol={"future": "invalid"})
    minute_fixture.reseal(later_capture)
    minute_fixture.atomic_fixture(tmp_path / "prefix.json", later_capture)
    future = minute_fixture.read_at(tmp_path / "prefix.json", "2026-10-07T14:19:00Z")
    combined = replace(own, terminal_read=future, enrolled_terminal_reads=(first, future))
    after = build(
        input_bundle(cutoffs=(CUTOFF, "2026-10-07T14:20:00Z")),
        {"candidate-0": {"stock": combined}, "candidate-1": {"stock": combined}})
    assert after["frames"][0] == before["frames"][0]
    assert after["input_bundle_sha256"] != before["input_bundle_sha256"]
    assert binding(after, index=1)["reason"] == "TERMINAL_INPUT_INVALID"
    assert after["retained_count"] == after["population_count"] == 2


def test_identity_read_one_nanosecond_after_decision_is_not_backdated(tmp_path, observed):
    bundle, reads = observed
    later = identity_read(tmp_path / "nanosecond", completed=minute_fixture.ns(CUTOFF) + 1)
    own = replace(reads["candidate-0"]["stock"], identity_read=later)
    with patch.object(identity_reader.IdentitySnapshotRead, "alias_table",
                      side_effect=AssertionError("read is strictly future")):
        result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["reason"] == "IDENTITY_NOT_KNOWN_AT_DECISION"
    assert "identity_read_receipt" not in binding(result)


@pytest.mark.parametrize(("mutation", "refusal"), [
    ("missing_basis", "BASIS_NOT_BOUND_AT_DECISION"),
    ("future_basis", "BASIS_NOT_BOUND_AT_DECISION"),
    ("retrospective_availability", "FIRST_SEEN_NOT_OBSERVED"),
])
def test_native_bound_identity_cannot_remove_existing_metadata_guards(observed, mutation, refusal):
    bundle, reads = observed
    meta = bundle["streams"]["stock"]
    if mutation == "missing_basis":
        meta.pop("basis")
    elif mutation == "future_basis":
        meta["basis"]["known_at"] = "2026-10-07T14:17:00Z"
    else:
        meta["availability_basis"] = "retrospective"
    result = build(bundle, reads)
    assert binding(result)["status"] == "BOUND"
    assert refusal in result["frames"][0]["bars"]["stock"]["30"]["refusals"]
    assert result["frames"][0]["bars"]["stock"]["30"]["ohlcv"] is None


def test_native_v1_keeps_original_newest_completed_window_geometry(observed):
    bundle, reads = observed
    bundle["window_policy_schema"] = panel.INPUT_SCHEMA
    result = build(bundle, reads)
    frame = result["frames"][0]
    assert "event_anchor_at" not in frame
    assert frame["bars"]["stock"]["15"]["end"] == "2026-10-07T14:15:00Z"
    assert frame["bars"]["stock"]["30"]["end"] == ANCHOR
    assert binding(result)["decision_at"] == CUTOFF


def test_visible_receipt_snapshot_mismatch_reaches_native_owner_validation(observed):
    bundle, reads = observed
    own = reads["candidate-0"]["stock"]
    wrong = replace(own.identity_read.receipt, generation_id="f" * 64)
    own = replace(own, identity_read=replace(own.identity_read, receipt=wrong))
    result = build(bundle, {"candidate-0": {"stock": own}})
    assert binding(result)["status"] == "REFUSED"
    assert binding(result)["reason"] == "IDENTITY_INPUT_INVALID"
    assert binding(result)["identity_resolution"] is None
    assert "identity_read_receipt" not in binding(result)



@pytest.mark.parametrize("bad_bytes", [b"{malformed source JSON", b"\xff"])
def test_visible_malformed_identity_bytes_keep_earlier_frame_and_later_refusal(
    tmp_path, observed, bad_bytes
):
    bundle, reads = observed
    future = identity_read(tmp_path / "later_bad", completed="2026-10-07T14:17:00Z")
    own = replace(reads["candidate-0"]["stock"], identity_read=future)
    baseline = build(bundle, {"candidate-0": {"stock": own}})
    malformed = replace(future, snapshot=replace(future.snapshot, receipt_bytes=bad_bytes))
    own = replace(own, identity_read=malformed)
    result = build(input_bundle(cutoffs=(CUTOFF, "2026-10-07T14:18:00Z")),
                   {"candidate-0": {"stock": own}, "candidate-1": {"stock": own}})
    assert result["frames"][0] == baseline["frames"][0]
    assert binding(result, index=1)["status"] == "REFUSED"
    assert binding(result, index=1)["reason"] == "IDENTITY_INPUT_INVALID"
    assert result["retained_count"] == result["population_count"] == 2
