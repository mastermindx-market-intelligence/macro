"""Real local producer/reader contracts over synthetic evidence, no live writes."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from engine.release_surprise_confirmation import (
    CONSENSUS_PATH, EvidenceError, authority, build_confirmation_artifact,
    read_consumer_context, read_jsonl,
)
from engine.trial_ledger import TrialLedger
from scripts import ingest_release_consensus as ingestion
from scripts.research_release_surprise import FAMILY, run_study
from tests.test_release_surprise_confirmation import (
    ASOF, actual_fixture, poll_fixture, publish, write_inputs,
)
from tests.test_release_surprise_study import SESSIONS, bars


class CaptureClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 11, 10, 12, 5, tzinfo=timezone.utc)


def test_ingestion_owns_capture_clock_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "datetime", CaptureClock)
    source = tmp_path / "authorized-input.jsonl"
    poll = poll_fixture(actual_fixture()[0])
    poll["recorded_at"] = "2008-01-01T00:00:00Z"  # untrusted backdating request
    source.write_text(json.dumps(poll) + "\n")
    dry = ingestion.ingest(source, tmp_path)
    assert not (tmp_path / CONSENSUS_PATH).exists()
    assert not dry["committed"] and dry["novel_rows"] == 1
    first = ingestion.ingest(source, tmp_path, commit=True)
    second = ingestion.ingest(source, tmp_path, commit=True)
    assert first["appended"] == 1 and second["appended"] == 0
    rows, meta = read_jsonl(tmp_path / CONSENSUS_PATH)
    assert meta["rows"] == 1
    assert rows[0]["observed_at"] == rows[0]["recorded_at"] == "2026-11-10T12:05:00Z"
    assert rows[0]["receipt_id"] == first["receipt_ids"][0]


def test_corrupt_consensus_ledger_is_not_rewritten(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "datetime", CaptureClock)
    source = tmp_path / "input.jsonl"
    source.write_text(json.dumps(poll_fixture(actual_fixture()[0])) + "\n")
    target = tmp_path / CONSENSUS_PATH
    target.parent.mkdir(parents=True)
    target.write_text("corrupt evidence\n")
    with pytest.raises(EvidenceError, match="ledger_invalid"):
        ingestion.ingest(source, tmp_path, commit=True)
    assert target.read_text() == "corrupt evidence\n"


def test_ingestion_does_not_follow_output_symlink(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "datetime", CaptureClock)
    source = tmp_path / "input.jsonl"
    source.write_text(json.dumps(poll_fixture(actual_fixture()[0])) + "\n")
    target = tmp_path / CONSENSUS_PATH
    target.parent.mkdir(parents=True)
    victim = tmp_path / "other-owner.jsonl"
    victim.write_text("unchanged")
    target.symlink_to(victim)
    with pytest.raises(OSError):
        ingestion.ingest(source, tmp_path, commit=True)
    assert victim.read_text() == "unchanged"


def test_mri_real_writer_publishes_byte_identical_context(tmp_path, monkeypatch):
    from scripts import build_release_forecast as producer
    monkeypatch.setattr(producer, "_find_upcoming_releases", lambda *a, **k: [])
    monkeypatch.setattr(producer, "_read_policy_backdrop", lambda *a, **k: {})
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13")
    write_inputs(tmp_path, actuals, [poll_fixture(a) for a in actuals])
    result = producer.build(tmp_path, dry_run=False)
    original = (tmp_path / "data/release_forecast/latest.json").read_bytes()
    display = (tmp_path / "site/macrodata/release_forecast.json").read_bytes()
    assert original == display
    assert result["surprise_confirmation"]["authority"] == authority()
    for consumer in ("prophet", "sector_intelligence", "event_windows", "release_radar"):
        context = read_consumer_context(tmp_path, consumer=consumer, asof=result["asof"])
        assert context["source_digest"] == result["surprise_confirmation"]["evidence_digest"]
        assert context["authority"] == authority()
    assert (tmp_path / "data/release_forecast/latest.json").read_bytes() == original


def test_prophet_opt_in_changes_context_only_not_bound_candidates(tmp_path, monkeypatch):
    from tests import test_prophet_today_provenance as native
    source, _ = native._native_today_multi(tmp_path, monkeypatch)
    default = native._read_today(tmp_path, source)
    source_bytes = source.read_bytes()
    envelope = json.loads(source_bytes)
    binding = native.producer.today_selection_source_binding(source_bytes)
    enriched = native.producer.read_today_candidate_projection(
        tmp_path, expected_source_sha256=binding["source_sha256"],
        expected_pair_id=binding["pair_id"], expected_selection_receipt=binding["selection_receipt"],
        include_macro_context=True)
    assert "macro_surprise_context" not in default
    assert enriched["macro_surprise_context"]["authority"] == authority()
    assert enriched["candidates"] == default["candidates"]
    assert enriched["status"] == default["status"]
    assert source.read_bytes() == source_bytes


def dataset_fixture():
    return {"schema": "release_surprise_dataset.v1", "calendar_source_ref": "synthetic-calendar",
            "price_source_ref": "synthetic-prices", "rights_ref": "synthetic-tests-only",
            "use_scopes": ["internal_research"], "evidence_class": "synthetic",
            "session_closes": SESSIONS, "bars": bars()}


def test_research_pipeline_registers_family_and_keeps_missing_data_visible(tmp_path):
    ledger = tmp_path / "test-trials.jsonl"
    report = run_study(tmp_path, dataset_fixture(), asof=ASOF, trial_ledger=ledger,
                       symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10)
    assert report["status"] == "insufficient_data"
    assert report["matrix"]["declared_hypotheses"] == 14
    assert report["prospective_validation_claim"] is False
    assert TrialLedger(ledger, family=FAMILY).literal_n() == 1
    again = run_study(tmp_path, dataset_fixture(), asof=ASOF, trial_ledger=ledger,
                      symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10)
    assert TrialLedger(ledger, family=FAMILY).literal_n() == 1
    assert again == report


def test_research_pipeline_uses_real_join_and_individual_clocks(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13", headline=0.1)
    write_inputs(tmp_path, actuals, [poll_fixture(a) for a in actuals])
    report = run_study(tmp_path, dataset_fixture(), asof="2026-11-19T00:00:00Z",
                       trial_ledger=tmp_path / "trials.jsonl", symbols=["SPY"], horizons=[1],
                       draws=100, min_train=8, min_cell_n=10)
    assert report["status"] == "evaluated_exploratory"
    assert len(report["paired_outcomes"]["rows"]) == 2
    assert report["paired_outcomes"]["rows"][0]["entry_at"] == "2026-11-13T21:00:00Z"
    assert report["individual_outcomes_descriptive_only"]["rows"][0]["entry_at"] == "2026-11-10T21:00:00Z"
    assert report["walk_forward"]["predictions"] == []
    assert report["authority"] == authority()


def test_dataset_rights_and_calendar_refs_are_required_before_trials(tmp_path):
    dataset = dataset_fixture()
    dataset["rights_ref"] = None
    target = tmp_path / "not-created.jsonl"
    with pytest.raises(EvidenceError):
        run_study(tmp_path, dataset, asof=ASOF, trial_ledger=target)
    assert not target.exists()
