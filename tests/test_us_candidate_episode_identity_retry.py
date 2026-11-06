"""A consumed unresolved TURN WATCH input cannot become a historical opening."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from engine import us_candidate_episode as core
from engine.us_candidate_episode_intake import load_identity_spine, turn_watch_observations
from scripts import reconcile_us_candidate_episodes as writer
from tests.test_us_candidate_episode_reconciler import (
    _episode_root, _event_rows, _head, _rehash_turn_watch, _run_nightly,
    _seed_sources, _snapshot, _suppression_rows, _turn_path,
)


def _seed_unresolved_turn(root, monkeypatch, *, earlier_trigger=True):
    _seed_sources(root)
    path = _turn_path(root)
    doc = json.loads(path.read_text())
    if earlier_trigger:
        doc["rows"][0]["triggers"]["dot_1d"]["last_date"] = "2026-11-25"
    path.write_text(core.canonical_json(_rehash_turn_watch(doc)) + "\n")
    aliases = root / "data/reference/vendor_aliases.parquet"
    original_aliases = aliases.read_bytes()
    frame = pd.read_parquet(aliases)
    frame["vendor_symbol"] = "OTHER"
    frame.to_parquet(aliases, index=False)
    _run_nightly(root, monkeypatch)
    prior = _suppression_rows(root)
    assert len(prior) == 1 and prior[0]["reason"] == "IDENTITY_UNRESOLVED"
    assert prior[0]["security_id"] is None
    assert _event_rows(root) == []
    aliases.write_bytes(original_aliases)
    batch = turn_watch_observations(path, load_identity_spine(root / "data"))
    assert len(batch.observations) == 1
    obs = batch.observations[0]
    assert obs["source_receipt"] == prior[0]["source_receipt"]
    assert obs["source_event_id"] == prior[0]["source_event_id"]
    return prior[0], obs


@pytest.mark.parametrize("earlier_trigger", [True, False])
def test_native_identity_resolution_retains_suppression_and_retry_generation(
    tmp_path, monkeypatch, earlier_trigger
):
    prior, obs = _seed_unresolved_turn(tmp_path, monkeypatch, earlier_trigger=earlier_trigger)
    source_before = _turn_path(tmp_path).read_bytes()
    receipt = _run_nightly(tmp_path, monkeypatch, recorded_at="2026-11-30T21:05:00Z")
    assert _event_rows(tmp_path) == []
    assert _suppression_rows(tmp_path) == [prior]
    assert core.load_candidate_episode_store(_episode_root(tmp_path)) == []
    assert _turn_path(tmp_path).read_bytes() == source_before
    assert receipt["source_counts"]["turn_watch"]["input"] == 1
    stable_head, stable_bytes = _head(tmp_path), _snapshot(_episode_root(tmp_path))
    _run_nightly(tmp_path, monkeypatch, recorded_at="2026-12-01T21:05:00Z")
    assert _head(tmp_path) == stable_head
    assert _snapshot(_episode_root(tmp_path)) == stable_bytes
    assert obs["security_id"] is not None  # Resolution never promotes the consumed row.


def test_core_returns_original_suppression_once_without_mutating_inputs(tmp_path, monkeypatch):
    prior, obs = _seed_unresolved_turn(tmp_path, monkeypatch)
    before = deepcopy((prior, obs))
    result = core.reconcile_observations(
        [], [obs, deepcopy(obs)], existing_suppressions=[prior],
        recorded_at="2026-11-30T21:05:00Z", definition_era=core.DEFAULT_DEFINITION_ERA,
    )
    assert result.suppressions == (prior,)
    assert result.events == result.new_events == result.episodes == ()
    assert (prior, obs) == before


@pytest.mark.parametrize("field,value", [
    ("source_receipt", "sha256:" + "f" * 64),
    ("ticker_at_observation", "OTHER"),
])
def test_resolved_identity_does_not_hide_changed_source_facts(tmp_path, monkeypatch, field, value):
    prior, obs = _seed_unresolved_turn(tmp_path, monkeypatch)
    old = deepcopy(prior)
    changed = {**obs, field: value}
    with pytest.raises(core.EpisodeContractError, match="different committed bytes"):
        core.reconcile_observations(
            [], [changed], existing_suppressions=[prior],
            recorded_at="2026-11-30T21:05:00Z", definition_era=core.DEFAULT_DEFINITION_ERA,
        )
    assert prior == old


def test_native_same_key_changed_document_receipt_refuses_before_write(tmp_path, monkeypatch):
    prior, _ = _seed_unresolved_turn(tmp_path, monkeypatch)
    before = _snapshot(_episode_root(tmp_path))
    path = _turn_path(tmp_path)
    doc = json.loads(path.read_text())
    doc["selection_era"] = "changed-document-evidence"
    path.write_text(core.canonical_json(_rehash_turn_watch(doc)) + "\n")
    batch = turn_watch_observations(path, load_identity_spine(tmp_path / "data"))
    assert batch.observations[0]["source_event_id"] == prior["source_event_id"]
    assert batch.observations[0]["source_receipt"] != prior["source_receipt"]
    with pytest.raises(core.EpisodeContractError, match="different committed bytes"):
        _run_nightly(tmp_path, monkeypatch, recorded_at="2026-11-30T21:05:00Z")
    assert _snapshot(_episode_root(tmp_path)) == before


@pytest.mark.parametrize("changes", [
    {"reason": "MISSING_STRUCTURAL_ANCHOR"},
    {"security_id": "SEC:US-XNAS-OTHER"},
    {"source_system": "candidate"},
    {"source_schema": "different-source/v1"},
    {"source_event_id": "turn_watch:natural-key"},
])
def test_exception_does_not_widen_to_other_suppression_contracts(tmp_path, monkeypatch, changes):
    prior, obs = _seed_unresolved_turn(tmp_path, monkeypatch)
    prior = writer._normalize_suppression({**prior, **changes}, recorded_at=prior["recorded_at"])
    obs = {**obs, **{k: v for k, v in changes.items() if k.startswith("source_")}}
    before = deepcopy((prior, obs))
    with pytest.raises(core.EpisodeContractError, match="different committed bytes"):
        core.reconcile_observations(
            [], [obs], existing_suppressions=[prior],
            recorded_at="2026-11-30T21:05:00Z", definition_era=core.DEFAULT_DEFINITION_ERA,
        )
    assert (prior, obs) == before
