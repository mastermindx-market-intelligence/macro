"""Real B1 compatibility proof for the prospective optional receipt column."""
import json
from hashlib import sha256
from pathlib import Path
import shutil
import pandas as pd
import pytest
from engine import us_candidate_episode_intake as intake
from engine.us_candidate_episode import EpisodeContractError
from engine.us_candidate_episode import canonical_json, load_candidate_episode_store_snapshot
from engine.us_candidate_episode_intake import candidate_source_row
from scripts import reconcile_us_candidate_episodes as writer

FIXTURE_ROOT = Path(__file__).parent / "fixtures/us_candidate_episode/intake"


def test_null_schema_union_retains_real_native_source_key(tmp_path, monkeypatch):
    data = tmp_path / "data"
    reference = data / "reference"
    reference.mkdir(parents=True)
    for name in ("security_master", "vendor_aliases"):
        pd.DataFrame(json.loads((FIXTURE_ROOT / (name + ".json")).read_text())).to_parquet(reference / (name + ".parquet"), index=False)
    turn = data / "us_prophet_rank/episode_inputs/turn_watch/2026-11-27.json"
    turn.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_ROOT / "turn_watch.json", turn)
    candidate = data / "us_prophet_rank/candidates/2026-11.parquet"
    candidate.parent.mkdir(parents=True)
    row = {"stamp_date": "2026-11-27", "ticker": "ALFA", "board_definition": "us_prophet_v3", "tier": "curated"}
    pd.DataFrame([row]).to_parquet(candidate, index=False)
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:05:00Z", correction_path=None)
    episode_root = data / "us_prophet_rank/episodes"
    before = load_candidate_episode_store_snapshot(episode_root)
    pd.DataFrame([{**row, "today_selection_row_receipt": None}]).to_parquet(candidate, index=False)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    after = load_candidate_episode_store_snapshot(episode_root)
    assert after.generation.events == before.generation.events
    assert after.generation.suppressions == before.generation.suppressions
    assert after.generation.episodes == before.generation.episodes
    assert candidate_source_row({**row, "today_selection_row_receipt": None}) == row
    # Reverting the reader after schema union is unsafe even with emission off.
    retained_head = (episode_root / "HEAD.json").read_bytes()
    with monkeypatch.context() as legacy:
        legacy.setattr(intake, "candidate_source_row", intake._plain_row)
        with pytest.raises(EpisodeContractError, match="ordinary source key reused"):
            writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:07:00Z", correction_path=None)
    assert (episode_root / "HEAD.json").read_bytes() == retained_head
    # A functional rollback with the compatibility reader retained is safe.
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:08:00Z", correction_path=None)
    rolled_back = load_candidate_episode_store_snapshot(episode_root)
    assert rolled_back.generation.events == before.generation.events
    assert rolled_back.generation.suppressions == before.generation.suppressions


def test_candidate_wrapper_preserves_other_nulls_and_malformed_receipt():
    row = {"ticker": "ALFA", "unknown_field": None}
    assert candidate_source_row(row) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": pd.NA}) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": float("nan")}) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": None}) == row
    malformed = {**row, "today_selection_row_receipt": "malformed"}
    assert candidate_source_row(malformed) == malformed
    assert sha256(canonical_json(candidate_source_row(malformed)).encode()).digest() != sha256(canonical_json(row).encode()).digest()
