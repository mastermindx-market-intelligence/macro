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


def test_partial_append_reports_uncertainty_without_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "datetime", CaptureClock)
    source = tmp_path / "input.jsonl"
    source.write_text(json.dumps(poll_fixture(actual_fixture()[0])) + "\n")
    original = ingestion.append_receipts
    calls = []
    def interrupted(path, rows):
        calls.append(path)
        original(path, rows)
        raise OSError("injected failure after durable append")
    monkeypatch.setattr(ingestion, "append_receipts", interrupted)
    with pytest.raises(ingestion.ConsensusAppendUncertain):
        ingestion.ingest(source, tmp_path, commit=True)
    assert len(calls) == 1
    assert read_jsonl(tmp_path / CONSENSUS_PATH)[1]["rows"] == 1


def test_config_variants_remain_in_same_trial_family(tmp_path):
    path = tmp_path / "trials.jsonl"
    run_study(tmp_path, dataset_fixture(), asof=ASOF, trial_ledger=path,
              symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10)
    changed = run_study(tmp_path, dataset_fixture(), asof=ASOF, trial_ledger=path,
                        symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10,
                        round_trip_cost_bps=5)
    assert changed["matrix"]["configuration_trials_seen"] == 2
    assert TrialLedger(path, family=FAMILY).literal_n() == 2


def test_event_windows_binds_ledger_writes_to_original_producer_root(tmp_path, monkeypatch):
    import pandas as pd
    from engine import event_window as engine
    from lib import config
    from scripts import build_event_windows as producer
    calls = []
    monkeypatch.setattr(producer, "_root", lambda: tmp_path)
    monkeypatch.setattr(producer, "_spy_close", lambda: pd.Series([100., 101.], index=pd.to_datetime(["2026-11-10", "2026-11-11"])))
    monkeypatch.setattr(producer, "_spy_vol_payload", lambda: None)
    monkeypatch.setattr(producer, "_vol_regime_snap", lambda: None)
    monkeypatch.setattr(producer, "_release_forecast_integrity_chip", lambda _: None)
    monkeypatch.setattr(engine, "snapshot", lambda *a, **kw: {"available": True, "asof": ASOF})
    monkeypatch.setattr(engine, "grade_forward_log", lambda **kw: calls.append(("grade", kw["path"])) or 0)
    monkeypatch.setattr(producer, "_stamp_forward_log", lambda *a, **kw: calls.append(("stamp", kw["log_path"])) or 0)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": str(tmp_path / "site")}})
    assert producer.main() == 0
    expected = tmp_path / "data/event_windows/forward_log.jsonl"
    assert calls == [("grade", expected), ("stamp", expected)]
    snapshot = json.loads((tmp_path / "site/event_windows/snapshot.json").read_text())
    assert snapshot["macro_surprise_context"]["authority"] == authority()


@pytest.mark.parametrize("scopes", ["internal_research,display_derived", ["internal_research", "unknown"], None])
def test_dataset_scope_contract_is_typed_before_trial_write(tmp_path, scopes):
    data = dataset_fixture()
    data["use_scopes"] = scopes
    ledger = tmp_path / "trials.jsonl"
    with pytest.raises(EvidenceError, match="dataset_use_scopes_invalid"):
        run_study(tmp_path, data, asof=ASOF, trial_ledger=ledger)
    assert not ledger.exists()


def test_private_archive_permissions_and_publication_boundary(tmp_path, monkeypatch):
    from pathlib import Path
    import stat
    import yaml
    monkeypatch.setattr(ingestion, "datetime", CaptureClock)
    source = tmp_path / "authorized.jsonl"
    source.write_text(json.dumps(poll_fixture(actual_fixture()[0])) + "\n")
    target = tmp_path / CONSENSUS_PATH
    target.parent.mkdir(parents=True)
    target.write_text("")
    target.chmod(0o644)
    ingestion.ingest(source, tmp_path, commit=True)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    root = Path(__file__).resolve().parents[1]
    assert "/" + CONSENSUS_PATH in (root / ".gitignore").read_text().splitlines()
    registry = yaml.safe_load((root / "config/synapse.yml").read_text())
    def entries(value):
        if isinstance(value, dict):
            if value.get("path") == CONSENSUS_PATH:
                yield value
            for nested in value.values():
                yield from entries(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from entries(nested)
    records = list(entries(registry))
    assert len(records) == 1
    assert records[0]["storage"] == "gitignored-local"
    assert records[0]["producer"] == "scripts/ingest_release_consensus.py"


def test_cross_run_trial_multiplier_exposes_monte_carlo_resolution(tmp_path):
    ledger = tmp_path / "trials.jsonl"
    data = dataset_fixture()
    first = run_study(tmp_path, data, asof=ASOF, trial_ledger=ledger,
                      symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10)
    second = run_study(tmp_path, data, asof=ASOF, trial_ledger=ledger,
                       symbols=["SPY"], horizons=[1], draws=100, min_train=8, min_cell_n=10,
                       round_trip_cost_bps=1)
    assert second["matrix"]["configuration_trials_seen"] >= first["matrix"]["configuration_trials_seen"]
    matrix = second["matrix"]
    resolution = matrix["monte_carlo_resolution"]
    assert resolution["cross_run_best_possible_first_p"] == pytest.approx(
        min(1, matrix["declared_hypotheses"] * matrix["configuration_trials_seen"] / 101))
    assert resolution["cross_run_supports_005_first_rejection"] is False
    assert resolution["cross_run_minimum_draws_below_005"] == 20 * matrix["declared_hypotheses"] * matrix["configuration_trials_seen"]
    assert second["prospective_validation_claim"] is False
