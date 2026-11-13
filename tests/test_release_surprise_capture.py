"""Synthetic forward-capture contract tests; never production performance proof."""
from __future__ import annotations

import copy
import fcntl
import json
from datetime import datetime, timezone

import pytest

from engine.release_surprise_confirmation import EvidenceError, digest, read_jsonl
from engine.release_surprise_study import (
    evaluate_shadow_captures, forecast_at, prepare_shadow_proposals,
)
from scripts import build_release_forecast as producer
from tests.test_release_surprise_study import SESSIONS, event, study_rows


class WriterClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 11, 13, 14, 5, tzinfo=timezone.utc)


class LateClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 11, 13, 21, 5, tzinfo=timezone.utc)


def proposals(evidence_class="retrospective_pit"):
    # The declaration exercises the qualified-data branch on synthetic fixtures.
    # It is not a claim that these generated prices are historical observations.
    return prepare_shadow_proposals(study_rows(), [event("2026-11-13T13:31:00Z")], SESSIONS,
        symbols=["SPY"], horizons=[20], asof="2026-11-13T14:00:00Z",
        protocol_receipt=digest({"synthetic_test_protocol": True}), min_train=8,
        evidence_class=evidence_class)["proposals"]


def test_unlabelled_target_can_be_forecast_without_fake_zero_outcome():
    result = proposals()
    assert len(result) == 1
    prediction = result[0]["prediction"]
    assert prediction["n_train"] == 80
    assert "realized_pct" not in prediction
    assert result[0]["entry_at"] == "2026-11-13T21:00:00Z"
    assert len(prediction["training_receipt"]) == 64


def test_duplicate_training_period_is_not_an_extra_observation():
    rows = study_rows()
    duplicate = {**rows[0], "event_id": "another-id-same-period"}
    target = {**event(), "signal_known_at": "2026-11-13T13:31:00Z", "symbol": "SPY", "horizon": 20}
    with pytest.raises(EvidenceError, match="duplicate_forecast_training_period"):
        forecast_at(rows + [duplicate], target, min_train=8)


def test_original_writer_records_and_reads_back_separate_capture_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", WriterClock)
    path = tmp_path / "forward_ledger.jsonl"
    result = producer.capture_macro_shadow(path, proposals())
    rows, meta = read_jsonl(path)
    assert meta["rows"] == 2
    assert [r["row_type"] for r in rows] == ["macro_return_forecast", "macro_return_capture"]
    assert rows[0]["captured_at"] == rows[1]["capture_observed_at"] == "2026-11-13T14:05:00Z"
    assert result["results"][0]["capture_eligible"] is True
    assert result["prospective_validation_claim"] is False
    before = path.read_bytes()
    repeated = producer.capture_macro_shadow(path, proposals())
    assert repeated["results"][0]["capture_eligible"] is True
    assert path.read_bytes() == before


def test_late_capture_cannot_backdate_to_prepared_asof(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", LateClock)
    path = tmp_path / "forward_ledger.jsonl"
    result = producer.capture_macro_shadow(path, proposals())
    assert result["results"][0]["status"] == "capture_window_missed"
    assert not path.exists()


def test_synthetic_capture_is_not_eligible_forward_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", WriterClock)
    result = producer.capture_macro_shadow(tmp_path / "ledger.jsonl", proposals("synthetic"))
    assert result["results"][0]["capture_eligible"] is False


def test_readback_interruption_preserves_unqualified_original_without_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", WriterClock)
    path = tmp_path / "forward_ledger.jsonl"
    original = producer._append_ledger_rows
    calls = []
    def interrupted(target, rows):
        calls.append(rows[0]["row_type"])
        original(target, rows)
        raise producer.ForwardLedgerAppendUncertain("injected after original append")
    monkeypatch.setattr(producer, "_append_ledger_rows", interrupted)
    with pytest.raises(producer.MacroShadowCaptureUncertain):
        producer.capture_macro_shadow(path, proposals())
    assert calls == ["macro_return_forecast"]
    assert read_jsonl(path)[1]["rows"] == 1
    monkeypatch.setattr(producer, "_append_ledger_rows", original)
    reconciled = producer.capture_macro_shadow(path, proposals())
    assert reconciled["results"][0]["status"] == "existing_capture_unqualified"
    assert read_jsonl(path)[1]["rows"] == 1


def test_original_append_lock_blocks_overlap_without_new_rows(tmp_path):
    path = tmp_path / "forward_ledger.jsonl"
    path.touch()
    with path.open("a") as owner:
        fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            producer._append_ledger_rows(path, [{"release": "cpi", "period": "test", "row_type": "projection"}])
    assert path.read_bytes() == b""


def test_duplicate_batch_and_conflicting_shadow_identity(tmp_path):
    path = tmp_path / "forward_ledger.jsonl"
    proposal = proposals()[0]
    producer._append_ledger_rows(path, [proposal, proposal])
    assert read_jsonl(path)[1]["rows"] == 1
    different = {**proposal, "prepared_asof": "2026-11-13T14:01:00Z"}
    with pytest.raises(ValueError, match="immutable_macro_return_receipt_conflict"):
        producer._append_ledger_rows(path, [different])
    assert read_jsonl(path)[0] == [proposal]


def test_shadow_grading_requires_original_linked_preentry_capture(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", WriterClock)
    path = tmp_path / "forward_ledger.jsonl"
    prepared = proposals()
    producer.capture_macro_shadow(path, prepared)
    rows, _ = read_jsonl(path)
    prediction = prepared[0]["prediction"]
    label = {"event_id": prediction["event_id"], "symbol": "SPY", "horizon": 20,
             "entry_at": prepared[0]["entry_at"], "outcome_known_at": "2026-12-14T21:01:00Z",
             "net_return_pct": 1.0, "round_trip_cost_bps": 0.0}
    immature = evaluate_shadow_captures(rows, [label], asof="2026-11-14T00:00:00Z")
    assert immature["graded"] == []
    assert immature["exclusions"] == {"label_not_yet_available": 1}
    result = evaluate_shadow_captures(rows, [label], asof="2026-12-15T00:00:00Z")
    assert len(result["graded"]) == 1
    assert result["independent_timestamp_attestation"] is False
    changed = copy.deepcopy(rows)
    changed[1]["capture_observed_at"] = "2026-11-14T00:00:00Z"
    changed[1]["receipt_digest"] = digest({k: v for k, v in changed[1].items() if k != "receipt_digest"})
    assert not evaluate_shadow_captures(changed, [label], asof="2026-12-15T00:00:00Z")["graded"]


def test_capture_never_rewrites_existing_forecast_on_model_change(tmp_path, monkeypatch):
    monkeypatch.setattr(producer, "datetime", WriterClock)
    path = tmp_path / "forward_ledger.jsonl"
    prepared = proposals()
    producer.capture_macro_shadow(path, prepared)
    before = path.read_bytes()
    changed = copy.deepcopy(prepared)
    changed[0]["prediction"]["forecast_pct"] += 10
    changed[0]["proposal_digest"] = digest({k: v for k, v in changed[0].items() if k != "proposal_digest"})
    result = producer.capture_macro_shadow(path, changed)
    assert result["results"][0]["proposal_changed"] is True
    assert path.read_bytes() == before
