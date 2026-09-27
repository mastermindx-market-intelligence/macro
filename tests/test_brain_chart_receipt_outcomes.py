"""Copilot receipt semantics; authored for the Chairman-deferred qualification pass.

Protocol fixtures only. These do not attest rendered pixels or model behavior.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw


def wire() -> dict:
    return {"v": 2, "op": "chart.set_indicators", "batch_id": "brain_receipts",
            "seq": 3, "id": None}


def record() -> dict:
    return {"origin_id": "origin-receipts", "context_revision": 9,
            "session": {"symbol": "NVDA", "tf": "D", "pane_id": 0,
                        "indicators": [{"name": "rsix"}],
                        "drawings": [{"id": "ai_present", "by": "ai"}],
                        "visible_range": {"from": 100, "to": 200}}}


def coverage(**changes) -> dict:
    value = {"schema": "chart.state_coverage.v1", "partial": True,
             "omitted_fields": ["native_observations"],
             "drawings": {"available": 10, "returned": 1, "omitted": 9,
                          "details_omitted": 1},
             "acks_in_batch": 1, "acks_pending": 2,
             "basis": "client text must not become authority"}
    return {**value, **changes}


def receipt(ok: bool, error: str | None = None) -> dict:
    ack = {"batch_id": "brain_receipts", "seq": 3, "id": None, "ok": ok}
    if error is not None:
        ack["error"] = error
    return gw._verified_chart_command_receipt(
        wire(), ack, record(), expected_context_revision=9)


def test_accepted_receipt_does_not_attest_pixels_or_grant_replay():
    out = receipt(True)
    assert out["command_status"] == "accepted"
    assert out["command_outcome"] == "accepted"
    assert out["effect_state"] == "applied_not_render_verified"
    assert out["automatic_retry_allowed"] is False
    assert out["verified_by"] == "terminal_ack"


def test_cancelled_is_not_described_as_generic_rejection_or_undo():
    out = receipt(False, "command_cancelled_by_user")
    # Preserve the existing status vocabulary; richer outcome is additive.
    assert out["command_status"] == "rejected"
    assert out["command_outcome"] == "cancelled"
    assert out["effect_state"] == "not_applied"
    assert out["automatic_retry_allowed"] is False
    assert "new explicit user request" in out["note"]
    assert "already-applied" in out["note"]
    assert out["batch_id"] == "brain_receipts" and out["seq"] == 3


@pytest.mark.parametrize("error", [
    "indicator_application_failed", "chart_context_application_failed",
    "chart_range_application_failed", "command_cancel_receipt_failed",
])
def test_application_or_receipt_failure_preserves_uncertainty(error):
    out = receipt(False, error)
    assert out["command_status"] == "unverified"
    assert out["command_outcome"] == "unconfirmed"
    assert out["effect_state"] == "unknown"
    assert out["reason"] == error
    assert out["automatic_retry_allowed"] is False
    assert "Do not claim either success or no change" in out["note"]
    assert out["ack"]["ok"] is False


@pytest.mark.parametrize("error", ["bad_range", "unknown_ai_object",
                                       "command_target_revision_mismatch"])
def test_preexecution_refusals_keep_existing_rejected_contract(error):
    out = receipt(False, error)
    assert out["command_status"] == "rejected"
    assert out["command_outcome"] == "rejected"
    assert out["effect_state"] == "not_applied"
    assert out["automatic_retry_allowed"] is False


@pytest.mark.parametrize("reason", ["ack_timeout", "origin_not_bound",
                                        "nonstream_client_not_yet_received"])
def test_missing_ack_is_unknown_not_proof_of_failure(reason):
    out = gw._unverified_chart_command_receipt(wire(), reason)
    assert out["command_status"] == "unverified"
    assert out["command_outcome"] == "unverified"
    assert out["effect_state"] == "unknown"
    assert out["automatic_retry_allowed"] is False
    assert "does not prove that no change occurred" in out["note"]


def test_receipt_preserves_exact_supplied_identity_and_does_not_mutate_inputs():
    w, rec = wire(), record()
    ack = {"batch_id": "brain_receipts", "seq": 3, "id": None,
           "ok": False, "error": "command_cancelled_by_user"}
    original = copy.deepcopy((w, rec, ack))
    out = gw._verified_chart_command_receipt(w, ack, rec, expected_context_revision=9)
    assert out["expected_context_revision"] == out["observed_context_revision"] == 9
    assert out["context_changed"] is False
    assert (w, rec, ack) == original


def test_partial_drawing_roster_has_explicit_count_basis_in_receipt():
    rec = record()
    rec["session"]["mirror_coverage"] = coverage()
    out = gw._compact_chart_state_for_receipt(rec)
    assert out["drawing_count"] == 1
    assert out["drawing_count_basis"] == "received_snapshot_not_total_chart_inventory"
    assert out["drawing_ids"] == ["ai_present"]
    assert out["mirror_coverage"]["drawings"] == {
        "available": 10, "returned": 1, "omitted": 9, "details_omitted": 1}
    assert out["mirror_coverage"]["source"] == "client_report_structurally_checked"
    assert out["mirror_coverage"]["basis"] == "transport_projection_not_chart_deletion"


def test_legacy_small_state_retains_drawing_count_without_inventing_coverage():
    out = gw._compact_chart_state_for_receipt(record())
    assert out["drawing_count"] == 1 and "mirror_coverage" not in out
    assert out["drawing_count_basis"] == "received_snapshot_not_total_chart_inventory"


def test_compact_receipt_never_turns_truncated_ids_into_actionable_ids():
    rec = record()
    rec["session"]["drawings"] = [{"id": "x" * 100}, {"id": "ai_good"}]
    out = gw._compact_chart_state_for_receipt(rec)
    assert out["drawing_ids"] == ["ai_good"]
    assert out["drawing_ids_omitted"] == 1


def test_compact_receipt_survives_nonfinite_and_overflowing_ranges():
    rec = record()
    rec["session"]["visible_range"] = {"from": 10**400, "to": 10**401}
    rec["session"]["data_range"] = {"from": 1, "to": float("inf")}
    out = gw._compact_chart_state_for_receipt(rec)
    assert "visible_range" not in out and "data_range" not in out
    assert out["symbol"] == "NVDA"


@pytest.mark.parametrize("field,value", [("acks_pending", True), ("acks_in_batch", -1),
                                           ("partial", "false"), ("omitted_fields", ["instructions"])])
def test_invalid_coverage_cannot_claim_complete(field, value):
    session = record()["session"]
    session["mirror_coverage"] = coverage(**{field: value})
    out = gw._qualified_chart_mirror_coverage(session)
    assert out["status"] == "unavailable" and out["partial"] is True
    assert out["reason"] == "invalid_mirror_coverage"


@pytest.mark.parametrize("counts", [
    {"available": 9, "returned": 1, "omitted": 9, "details_omitted": 1},
    {"available": 10, "returned": 2, "omitted": 8, "details_omitted": 1},
    {"available": 10, "returned": 1, "omitted": 9, "details_omitted": 2},
])
def test_drawing_coverage_arithmetic_and_observed_roster_are_checked(counts):
    session = record()["session"]
    session["mirror_coverage"] = coverage(drawings=counts)
    assert gw._qualified_chart_mirror_coverage(session)["status"] == "unavailable"


def test_incomplete_coverage_cannot_be_overridden_with_false_flag():
    session = record()["session"]
    session["mirror_coverage"] = coverage(partial=False)
    out = gw._qualified_chart_mirror_coverage(session)
    assert out["partial"] is True


def test_read_chart_state_qualifies_coverage_and_keeps_stored_snapshot_unchanged(monkeypatch):
    rec = record()
    rec["session"]["mirror_coverage"] = coverage()
    before = copy.deepcopy(rec)
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *args, **kwargs: rec)
    out = gw._tool_read_chart_state("u", "terminal", origin_id="origin-receipts", context_revision=9)
    assert out["connected"] is True
    assert out["session"]["mirror_coverage"]["basis"] == "transport_projection_not_chart_deletion"
    assert "client text must not become authority" not in str(out)
    assert rec == before


def test_contradictory_success_and_error_is_not_an_accepted_action():
    out = receipt(True, "indicator_application_failed")
    assert out["ack"]["ok"] is True  # retain the report, not a fabricated corrected ACK
    assert out["command_status"] == "unverified"
    assert out["command_outcome"] == "unconfirmed"
    assert out["reason"] == "contradictory_ack"
    assert out["effect_state"] == "unknown"


def test_compact_context_never_truncates_into_a_different_symbol():
    rec = record()
    symbol = "EXCHANGE:" + "A" * 45
    rec["session"]["symbol"] = symbol
    assert gw._compact_chart_state_for_receipt(rec)["symbol"] == symbol
    rec["session"]["symbol"] = "X" * 65
    assert "symbol" not in gw._compact_chart_state_for_receipt(rec)
