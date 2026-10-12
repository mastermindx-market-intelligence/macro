"""B1 Task 2 — canonical candidate-episode intake boundaries."""
from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from engine.stock_identity.fingerprint import spec_hash
from engine import us_turn_watch as turn_watch
from engine.us_candidate_episode import canonical_json, reconcile_observations
from engine.us_candidate_episode_intake import (
    candidate_observations,
    door_observations,
    load_identity_spine,
    radar_observations,
    turn_watch_observations,
)
from engine.us_candidate_episode import EpisodeContractError
from scripts.build_turn_watch import write_candidate_episode_input


def _identity_spine(root: Path, *, issuer: str | None = "ISS:US-XNAS-ALFA") -> None:
    reference = root / "reference"
    reference.mkdir(parents=True)
    pd.DataFrame([{
        "security_id": "SEC:US-XNAS-ALFA", "issuer_id": issuer,
        "issuer_state": "ACTIVE", "listing_key": "US-XNAS-ALFA",
    }]).to_parquet(reference / "security_master.parquet", index=False)
    pd.DataFrame([{
        "vendor": "membership", "vendor_symbol": "ALFA",
        "security_id": "SEC:US-XNAS-ALFA", "valid_from": date(2020, 1, 1),
        "valid_to": None,
    }]).to_parquet(reference / "vendor_aliases.parquet", index=False)


def _turn_artifact() -> dict:
    return {
        "schema": "us_turn_watch.v1", "data_session": "2026-11-27",
        "selection_era": "anticipation-v1", "anchor_era": "anchor-v1",
        "triggers": {"dot_1d": {"en": "Daily turn dot"}},
    }


def _turn_row(**overrides) -> dict:
    row = {
        "ticker": "ALFA", "asof": "2026-11-27", "triggers_fired": ["dot_1d"],
        "triggers": {"dot_1d": {"fired": True, "evaluated": True,
                                 "last_date": "2026-11-27"}},
        "reset": {"reset_low": 42.1, "reset_low_date": "2026-11-27"},
    }
    row.update(overrides)
    return row


def _ids(batch) -> set[str]:
    return {str(row["source_event_id"]) for row in batch.observations} | {
        str(row["source_event_id"]) for row in batch.suppressions
    }


def test_turn_watch_sidecar_and_identity_spine_open_at_the_nyse_early_close(tmp_path: Path):
    """Changing the session clock or bypassing Data OS identity breaks this contract."""
    data = tmp_path / "data"
    _identity_spine(data)
    out = write_candidate_episode_input(_turn_artifact(), [_turn_row()], data)
    document = json.loads(out.read_text())
    assert out == data / "us_prophet_rank" / "episode_inputs" / "turn_watch" / "2026-11-27.json"
    assert document["schema"] == "prophet.candidate_episode_input.turn_watch/v1"
    assert document["known_at"] == "2026-11-27T18:00:00Z"  # Thanksgiving Friday, 13:00 ET.
    assert len(document["rows"]) == 1
    assert document["content_sha256"]

    batch = turn_watch_observations(out, load_identity_spine(data))
    assert len(batch.observations) == 1
    observed = batch.observations[0]
    assert observed["security_id"] == "SEC:US-XNAS-ALFA"
    assert observed["company_id"] == "ISS:US-XNAS-ALFA"
    assert observed["identity_epoch"] == "epoch_0"
    assert observed["identity_epoch_state"] == "provisional"
    assert observed["identity_spec_schema"] == "stock_identity.fingerprint_spec.v1"
    assert observed["identity_spec_hash"] == spec_hash()
    assert observed["anchor"]["time"] == "2026-11-27T18:00:00Z"
    result = reconcile_observations([], batch.observations,
                                    recorded_at="2026-11-27T18:00:00Z",
                                    definition_era="candidate-episode-v1-2026-08-25")
    assert result.episodes[0]["opened_at"] == "2026-11-27T18:00:00Z"


@pytest.mark.parametrize(
    ("row", "issuer", "reason"),
    [
        (_turn_row(triggers={}), "ISS:US-XNAS-ALFA", "MISSING_TRIGGER"),
        (_turn_row(triggers={"dot_1d": {"fired": True, "evaluated": False}}),
         "ISS:US-XNAS-ALFA", "UNEVALUATED_TRIGGER"),
        (_turn_row(triggers={"dot_1d": {"fired": True, "evaluated": True}}),
         "ISS:US-XNAS-ALFA", "MALFORMED_RECEIPT"),
        (_turn_row(reset={"reset_low": None, "reset_low_date": None}),
         "ISS:US-XNAS-ALFA", "MISSING_RESET_LOW"),
        (_turn_row(ticker="UNKNOWN"), "ISS:US-XNAS-ALFA", "IDENTITY_UNRESOLVED"),
        (_turn_row(), None, "ISSUER_UNRESOLVED"),
    ],
)
def test_turn_watch_invalid_structural_inputs_suppress_once(tmp_path: Path, row: dict,
                                                            issuer: str | None, reason: str):
    data = tmp_path / "data"
    _identity_spine(data, issuer=issuer)
    path = write_candidate_episode_input(_turn_artifact(), [row], data)
    batch = turn_watch_observations(path, load_identity_spine(data))
    assert batch.observations == ()
    assert [entry["reason"] for entry in batch.suppressions] == [reason]
    assert _ids(batch) == {batch.suppressions[0]["source_event_id"]}


def test_turn_watch_content_hash_mismatch_is_a_per_row_malformed_receipt(tmp_path: Path):
    data = tmp_path / "data"
    _identity_spine(data)
    path = write_candidate_episode_input(_turn_artifact(), [_turn_row()], data)
    document = json.loads(path.read_text())
    document["rows"][0]["ticker"] = "TAMPERED"
    path.write_text(json.dumps(document))
    batch = turn_watch_observations(path, load_identity_spine(data))
    assert batch.observations == ()
    assert [entry["reason"] for entry in batch.suppressions] == ["MALFORMED_RECEIPT"]


def test_nonobject_turn_watch_json_is_named_degraded_source(tmp_path: Path):
    data = tmp_path / "data"
    _identity_spine(data)
    path = tmp_path / "sidecar.json"
    path.write_text("[]")
    batch = turn_watch_observations(path, load_identity_spine(data))
    assert batch.source_receipts == ({
        "source": "turn_watch", "status": "degraded", "reason": "MALFORMED_SOURCE",
        "files": [{"path": str(path), "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest()}],
    },)


def test_turn_watch_open_time_uses_the_later_of_reset_and_earliest_trigger_close(tmp_path: Path):
    """A current sidecar session must not move a prior trigger's episode clock forward."""
    data = tmp_path / "data"
    _identity_spine(data)
    artifact = {**_turn_artifact(), "data_session": "2026-11-28"}
    row = _turn_row(
        triggers={"dot_1d": {"fired": True, "evaluated": True, "last_date": "2026-11-25"}},
        reset={"reset_low": 42.1, "reset_low_date": "2026-11-24"},
    )
    batch = turn_watch_observations(write_candidate_episode_input(artifact, [row], data),
                                    load_identity_spine(data))
    observed = batch.observations[0]
    assert observed["occurred_at"] == "2026-11-25T21:00:00Z"
    assert observed["known_at"] == "2026-11-25T21:00:00Z"
    result = reconcile_observations([], batch.observations,
                                    recorded_at="2026-11-28T18:00:00Z",
                                    definition_era="candidate-episode-v1-2026-08-25")
    assert result.episodes[0]["opened_at"] == "2026-11-25T21:00:00Z"


def test_sidecar_source_artifact_hashes_the_exact_public_file_bytes(tmp_path: Path):
    artifact = _turn_artifact()
    public = turn_watch.write_artifact(artifact, tmp_path / "site")
    sidecar = write_candidate_episode_input(artifact, [], tmp_path / "data")
    document = json.loads(sidecar.read_text())
    assert document["source_artifact_sha256"] == "sha256:" + sha256(public.read_bytes()).hexdigest()


def test_non_anchor_sources_attach_or_suppress_and_preserve_exact_radar_event_id(tmp_path: Path):
    """Only TURN WATCH may open; all other rows retain one unambiguous disposition."""
    data = tmp_path / "data"
    _identity_spine(data)
    spine = load_identity_spine(data)
    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    pd.DataFrame([{
        "stamp_date": "2026-11-27", "ticker": "ALFA", "board_definition": "us_prophet_v2",
        "tier": "curated", "pool_lane": None, "prophet_score": float("nan"),
    }]).to_parquet(
        candidates / "2026-11.parquet", index=False)
    doors = data / "prophet_doors" / "flags.jsonl"
    doors.parent.mkdir(parents=True)
    doors.write_text(json.dumps({"schema": "prophet_doors/v1", "date": "2026-11-27",
                                 "door": "T", "ticker": "ALFA", "features": {}}) + "\n")
    radar = data / "entry_radar" / "forward.parquet"
    radar.parent.mkdir(parents=True)
    pd.DataFrame([{
        "episode_address": "radar-expert-17", "ticker": "ALFA", "detector_id": "G0_GREY_DOT@1",
        "family": "g0_grey_dot", "subtype": "g0", "decision_session": "2026-11-27",
        "signal_ts": "2026-11-27T17:01:00+00:00",
        "signal_known_ts": "2026-11-27T17:02:00+00:00",
        "observed_at": "2026-11-27T17:03:00+00:00", "state": "LIVE_FORWARD",
    }]).to_parquet(radar, index=False)

    candidate_batch = candidate_observations(data, spine)
    door_batch = door_observations(doors, spine)
    radar_batch = radar_observations(radar, spine)
    assert len(candidate_batch.observations) == len(door_batch.observations) == 1
    assert candidate_batch.observations[0]["anchor"] is None
    assert door_batch.observations[0]["anchor"] is None
    assert radar_batch.observations[0]["source_event_id"] == "radar-expert-17"
    assert radar_batch.observations[0]["expert_event_id"] == "radar-expert-17"
    assert radar_batch.observations[0]["occurred_at"] == "2026-11-27T17:01:00Z"
    assert radar_batch.observations[0]["known_at"] == "2026-11-27T17:02:00Z"
    assert radar_batch.observations[0]["anchor"] is None
    assert reconcile_observations([], [*candidate_batch.observations, *door_batch.observations,
                                       *radar_batch.observations],
                                  recorded_at="2026-11-27T18:00:00Z",
                                  definition_era="candidate-episode-v1-2026-08-25").suppressions
    assert _ids(candidate_batch) == {candidate_batch.observations[0]["source_event_id"]}
    assert _ids(door_batch) == {door_batch.observations[0]["source_event_id"]}
    assert _ids(radar_batch) == {"radar-expert-17"}


def test_candidate_nested_parquet_records_are_canonical_json_safe(tmp_path: Path):
    """A list-of-struct Parquet cell must remain receipt-hashable after read-back."""
    data = tmp_path / "data"
    _identity_spine(data)
    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    pd.DataFrame([{
        "stamp_date": "2026-11-27",
        "ticker": "ALFA",
        "board_definition": "us_prophet_v2",
        "spine__records": [{"signal_id": "qledger:test", "score": 1.0}],
    }]).to_parquet(candidates / "2026-11.parquet", index=False)

    batch = candidate_observations(data, load_identity_spine(data))

    assert len(batch.observations) == 1
    assert batch.suppressions == ()
    assert batch.observations[0]["source_event_id"] == (
        "candidate:2026-11-27:ALFA:us_prophet_v2"
    )
    expected_row = {
        "stamp_date": "2026-11-27",
        "ticker": "ALFA",
        "board_definition": "us_prophet_v2",
        "spine__records": [{"signal_id": "qledger:test", "score": 1.0}],
    }
    assert batch.observations[0]["source_receipt"] == (
        "sha256:" + sha256(canonical_json(expected_row).encode("utf-8")).hexdigest()
    )


def test_canonical_source_keys_and_multirow_accounting_are_stable(tmp_path: Path):
    """Mutable feature/null changes cannot mint a second source identity or drop a row."""
    data = tmp_path / "data"
    _identity_spine(data)
    spine = load_identity_spine(data)
    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    pd.DataFrame([
        {"stamp_date": "2026-11-27", "ticker": "ALFA", "board_definition": "us_prophet_v2",
         "prophet_score": float("nan"), "pool_lane": None},
        {"stamp_date": "2026-11-27", "ticker": "UNKNOWN", "board_definition": "us_prophet_v2",
         "prophet_score": 77.0, "pool_lane": "featured"},
    ]).to_parquet(candidates / "2026-11.parquet", index=False)
    doors = data / "prophet_doors" / "flags.jsonl"
    doors.parent.mkdir(parents=True)
    doors.write_text("\n".join(json.dumps(row) for row in [
        {"schema": "prophet_doors/v1", "date": "2026-11-27", "door": "T", "ticker": "ALFA", "features": {"x": 1}},
        {"schema": "prophet_doors/v1", "date": "2026-11-27", "door": "R", "ticker": "UNKNOWN", "features": {"x": 2}},
    ]) + "\n")
    radar = data / "entry_radar" / "forward.parquet"
    radar.parent.mkdir(parents=True)
    pd.DataFrame([
        {"episode_address": "radar-a", "ticker": "ALFA", "decision_session": "2026-11-27",
         "signal_ts": "2026-11-27T17:00:00+00:00", "signal_known_ts": "2026-11-27T17:01:00+00:00"},
        {"episode_address": "radar-b", "ticker": "UNKNOWN", "decision_session": "2026-11-27",
         "signal_ts": "2026-11-27T17:00:00+00:00", "signal_known_ts": "2026-11-27T17:01:00+00:00"},
    ]).to_parquet(radar, index=False)
    candidate_batch = candidate_observations(data, spine)
    door_batch = door_observations(doors, spine)
    radar_batch = radar_observations(radar, spine)
    assert len(candidate_batch.observations) + len(candidate_batch.suppressions) == 2
    assert len(door_batch.observations) + len(door_batch.suppressions) == 2
    assert len(radar_batch.observations) + len(radar_batch.suppressions) == 2
    assert candidate_batch.observations[0]["source_event_id"] == "candidate:2026-11-27:ALFA:us_prophet_v2"
    assert door_batch.observations[0]["source_event_id"] == "doors:2026-11-27:T:ALFA"


def test_turn_watch_multirow_accounting_covers_observation_and_suppression(tmp_path: Path):
    data = tmp_path / "data"
    _identity_spine(data)
    batch = turn_watch_observations(
        write_candidate_episode_input(_turn_artifact(), [_turn_row(), _turn_row(ticker="UNKNOWN")], data),
        load_identity_spine(data),
    )
    assert len(batch.observations) + len(batch.suppressions) == 2


def test_historical_candidate_without_pinned_identity_suppresses(tmp_path: Path):
    data = tmp_path / "data"
    _identity_spine(data)
    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    pd.DataFrame([{"stamp_date": "2026-11-27", "ticker": "ALFA",
                   "board_definition": "us_prophet_v2", "replay": True}]).to_parquet(
        candidates / "2026-11.parquet", index=False)
    batch = candidate_observations(data, load_identity_spine(data))
    assert [row["reason"] for row in batch.suppressions] == ["HISTORICAL_IDENTITY_UNPROVEN"]


def test_missing_optional_source_is_named_degraded_receipt(tmp_path: Path):
    data = tmp_path / "data"
    _identity_spine(data)
    batch = candidate_observations(data, load_identity_spine(data))
    assert batch.observations == batch.suppressions == ()
    assert batch.source_receipts == ({"source": "candidate", "status": "degraded",
                                      "reason": "MISSING_SOURCE_FILE"},)


def test_identity_and_intake_receipts_attest_the_exact_once_read_file_bytes(tmp_path: Path):
    """Reopening a mutable source later must not change the bytes named by its receipt."""
    data = tmp_path / "data"
    _identity_spine(data)
    alias_path = data / "reference" / "vendor_aliases.parquet"
    security_path = data / "reference" / "security_master.parquet"
    alias_hash = "sha256:" + sha256(alias_path.read_bytes()).hexdigest()
    security_hash = "sha256:" + sha256(security_path.read_bytes()).hexdigest()
    spine = load_identity_spine(data)
    assert spine.source_receipts == (
        {"source": "identity", "path": str(alias_path), "sha256": alias_hash},
        {"source": "identity", "path": str(security_path), "sha256": security_hash},
    )

    turn_path = write_candidate_episode_input(_turn_artifact(), [_turn_row()], data)
    turn_hash = "sha256:" + sha256(turn_path.read_bytes()).hexdigest()
    turn_batch = turn_watch_observations(turn_path, spine)
    assert turn_batch.source_receipts[0]["files"] == [
        {"path": str(turn_path), "sha256": turn_hash}
    ]

    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    candidate_path = candidates / "2026-11.parquet"
    pd.DataFrame([{
        "stamp_date": "2026-11-27", "ticker": "ALFA",
        "board_definition": "us_prophet_v2",
    }]).to_parquet(candidate_path, index=False)
    candidate_hash = "sha256:" + sha256(candidate_path.read_bytes()).hexdigest()
    candidate_batch = candidate_observations(data, spine)
    assert candidate_batch.source_receipts[0]["files"] == [
        {"path": str(candidate_path), "sha256": candidate_hash}
    ]


def test_parquet_numpy_dressed_rows_intake_cleanly(tmp_path: Path):
    """B1's first natural scheduled run (33036497832, 2026-08-27T14:40Z) died with
    'Object of type ndarray is not JSON serializable' and aborted the ledgers job
    before its commit: parquet round-trips list-typed cells back as numpy arrays,
    and the receipt hash's canonical_json is deliberately fail-closed. Rows are
    normalized to plain Python before hashing (_plain_row); this pins the numpy
    dress never crashing intake again."""
    import numpy as np  # noqa: PLC0415 — the dress under test

    data = tmp_path / "data"
    _identity_spine(data)
    spine = load_identity_spine(data)
    candidates = data / "us_prophet_rank" / "candidates"
    candidates.mkdir(parents=True)
    pd.DataFrame([{
        "stamp_date": "2026-11-27", "ticker": "ALFA", "board_definition": "us_prophet_v2",
        "tier": "curated", "pool_lane": None, "prophet_score": np.float64(0.5),
        "confluence_tags": np.array(["a", "b"]),
    }]).to_parquet(candidates / "2026-11.parquet", index=False)

    batch = candidate_observations(data, spine)
    assert len(batch.observations) + len(batch.suppressions) >= 1


# Private, explicit future-schema prototype. V1 remains the deployed default.
_V2 = "prophet.candidate_episode_input.turn_watch/v2"


def _v2_roundtrip(root, artifact, rows):
    path = write_candidate_episode_input(artifact, rows, root, input_schema=_V2)
    return path, turn_watch_observations(path, load_identity_spine(root))


def _reconcile_fixture(events, observations, clock="2026-11-27T18:02:00Z"):
    return reconcile_observations(events, observations, recorded_at=clock,
                                  definition_era="candidate-episode-v1-2026-08-25")


@pytest.mark.parametrize("blocked_session", ("2026-11-26", "2026-11-28"))
def test_v2_non_session_transition_keeps_public_and_private_artifacts_unchanged(
        tmp_path, monkeypatch, blocked_session):
    from scripts import build_turn_watch as builder

    data, site = tmp_path / "data", tmp_path / "site"
    _identity_spine(data)
    artifact = {**_turn_artifact(), "data_session": "2026-11-25", "runtime_seconds": 10.0,
                "coverage": {"graded": 1, "triggered": 1, "deck": 1, "beyond_cap": 0,
                             "deck_by_trigger": {"dot_1d": 1}, "source_contract": {"pass": True}}}
    monkeypatch.setattr(builder.config, "data_dir", lambda: data)
    monkeypatch.setattr(builder.config, "site_dir", lambda: site)
    monkeypatch.setattr(builder.turn_watch, "compute_deck_with_candidates",
                        lambda *a, **k: (dict(artifact), [_turn_row()]))

    assert builder.build([]) == 0
    public = site / "turn_watch/turn_watch.json"
    sidecar_root = data / "us_prophet_rank/episode_inputs/turn_watch"
    public_before = public.read_bytes()
    private_before = {path.name: path.read_bytes() for path in sidecar_root.glob("*.json")}

    artifact["data_session"] = blocked_session
    assert builder.build(["--episode-input-schema", "v2"]) == 1
    assert public.read_bytes() == public_before
    assert {path.name: path.read_bytes() for path in sidecar_root.glob("*.json")} == private_before


@pytest.mark.parametrize("blocked_session", ("2026-11-26", "2026-11-28"))
def test_v2_intake_rejects_non_session_even_with_matching_document_hash(tmp_path, blocked_session):
    _identity_spine(tmp_path)
    path, _ = _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    document = json.loads(path.read_bytes())
    document["data_session"] = blocked_session
    document["known_at"] = blocked_session + "T21:00:00Z"
    document["content_sha256"] = sha256(canonical_json({
        key: value for key, value in document.items() if key != "content_sha256"
    }).encode("utf-8")).hexdigest()
    malformed = path.with_name(blocked_session + ".json")
    malformed.write_text(canonical_json(document) + "\n")

    batch = turn_watch_observations(malformed, load_identity_spine(tmp_path))
    assert not batch.observations
    assert not batch.suppressions
    assert batch.source_receipts[0]["status"] == "degraded"
    assert batch.source_receipts[0]["reason"] == "MALFORMED_SOURCE"


def test_v2_real_early_close_session_remains_accepted(tmp_path):
    _identity_spine(tmp_path)
    path, batch = _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    document = json.loads(path.read_bytes())
    assert document["known_at"] == "2026-11-27T18:00:00Z"
    assert len(batch.observations) == 1


def test_v2_receipts_ignore_build_runtime_but_keep_exact_file_provenance(tmp_path):
    _identity_spine(tmp_path)
    artifact = {**_turn_artifact(), "runtime_seconds": 10.0}
    path, initial = _v2_roundtrip(tmp_path, artifact, [_turn_row()])
    before = path.read_bytes()
    accepted = _reconcile_fixture([], initial.observations)
    artifact["runtime_seconds"] = 11.0
    path, retry = _v2_roundtrip(tmp_path, artifact, [_turn_row()])
    assert before != path.read_bytes()
    assert initial.observations == retry.observations
    assert initial.source_receipts != retry.source_receipts
    repeated = _reconcile_fixture(accepted.events, retry.observations)
    assert repeated.events == accepted.events
    assert len(repeated.episodes) == 1
    assert retry.source_receipts[0]["files"][0]["sha256"] == "sha256:" + sha256(path.read_bytes()).hexdigest()


def test_v2_sibling_changes_do_not_rewrite_an_unchanged_rows_receipt(tmp_path):
    _identity_spine(tmp_path)
    artifact = _turn_artifact()
    _, first = _v2_roundtrip(tmp_path, artifact, [_turn_row()])
    accepted = _reconcile_fixture([], first.observations)
    unknown = _turn_row(ticker="OTHER")
    _, second = _v2_roundtrip(tmp_path, artifact, [unknown, _turn_row()])
    assert len(second.observations) == 1 and len(second.suppressions) == 1
    assert first.observations == second.observations
    assert _reconcile_fixture(accepted.events, second.observations).events == accepted.events


@pytest.mark.parametrize("field, value", (
    ("selection_era", "different-selection"),
    ("anchor_era", "different-anchor"),
    ("triggers", {"dot_1d": {"en": "Different semantics"}}),
))
def test_v2_semantic_definition_drift_is_still_a_conflicting_retry(tmp_path, field, value):
    _identity_spine(tmp_path)
    artifact = _turn_artifact()
    _, first = _v2_roundtrip(tmp_path, artifact, [_turn_row()])
    accepted = _reconcile_fixture([], first.observations)
    artifact[field] = value
    _, second = _v2_roundtrip(tmp_path, artifact, [_turn_row()])
    assert first.observations[0]["source_event_id"] == second.observations[0]["source_event_id"]
    with pytest.raises(EpisodeContractError, match="different committed bytes"):
        _reconcile_fixture(accepted.events, second.observations)


def test_v2_transition_requires_a_new_session_and_preserves_prior_input(tmp_path):
    _identity_spine(tmp_path)
    old_path = write_candidate_episode_input(_turn_artifact(), [_turn_row()], tmp_path)
    old_bytes = old_path.read_bytes()
    with pytest.raises(ValueError, match="new session"):
        _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    assert old_path.read_bytes() == old_bytes


def test_v2_new_session_attaches_without_rewriting_the_legacy_episode(tmp_path):
    _identity_spine(tmp_path)
    old_path = write_candidate_episode_input(_turn_artifact(), [_turn_row()], tmp_path)
    old_bytes = old_path.read_bytes()
    first = turn_watch_observations(old_path, load_identity_spine(tmp_path))
    accepted = _reconcile_fixture([], first.observations)
    artifact = {**_turn_artifact(), "data_session": "2026-11-30", "runtime_seconds": 10.0}
    row = _turn_row(asof="2026-11-30", triggers={"dot_1d": {
        "fired": True, "evaluated": True, "last_date": "2026-11-30"}})
    _, batch = _v2_roundtrip(tmp_path, artifact, [row])
    new = _reconcile_fixture(accepted.events, batch.observations, "2026-11-30T21:01:00Z")
    assert len(new.episodes) == 1
    assert new.episodes[0]["episode_id"] == accepted.episodes[0]["episode_id"]
    assert new.events[0] == accepted.events[0]
    assert len(new.events) == len(accepted.events) + 1
    assert new.events[-1]["event_type"] == "OBSERVED"
    assert old_path.read_bytes() == old_bytes
    artifact["runtime_seconds"] = 12.0
    _, same = _v2_roundtrip(tmp_path, artifact, [row])
    assert _reconcile_fixture(new.events, same.observations, "2026-11-30T21:02:00Z").events == new.events


def test_v2_tampered_document_is_not_trusted_just_because_row_receipts_are_stable(tmp_path):
    _identity_spine(tmp_path)
    path, _ = _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    document = json.loads(path.read_text())
    document["rows"][0]["reset"]["reset_low"] = 999.0
    path.write_text(json.dumps(document))
    batch = turn_watch_observations(path, load_identity_spine(tmp_path))
    assert not batch.observations
    assert len(batch.suppressions) == 1
    assert batch.suppressions[0]["reason"] == "MALFORMED_RECEIPT"


def test_v2_full_generation_preserves_event_history_on_a_harmless_rebuild(tmp_path, monkeypatch):
    from scripts import reconcile_us_candidate_episodes as writer
    data = tmp_path / "data"
    _identity_spine(data)
    artifact = {**_turn_artifact(), "runtime_seconds": 10.0}
    _v2_roundtrip(data, artifact, [_turn_row()])
    # Only this temporary fixture is admitted; no live lane or environment is changed.
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    first = writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                             recorded_at="2026-11-27T18:01:00Z", correction_path=None)
    head_path = data / "us_prophet_rank/episodes/HEAD.json"
    head1 = json.loads(head_path.read_text())
    generation = head_path.parent / "generations" / head1["generation_id"]
    frozen = {str(p.relative_to(generation)): p.read_bytes() for p in generation.rglob("*") if p.is_file()}
    artifact["runtime_seconds"] = 11.0
    _v2_roundtrip(data, artifact, [_turn_row()])
    second = writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                              recorded_at="2026-11-27T18:02:00Z", correction_path=None)
    assert first["counts"]["appended_events"] == 1
    assert second["counts"]["appended_events"] == 0
    assert first["ledger_sha256"] == second["ledger_sha256"]
    assert first["projection_hashes"] == second["projection_hashes"]
    assert first["source_hashes"] != second["source_hashes"]
    assert {str(p.relative_to(generation)): p.read_bytes() for p in generation.rglob("*") if p.is_file()} == frozen
    assert json.loads(head_path.read_text())["generation_id"] != head1["generation_id"]


def test_v2_full_generation_rejects_definition_drift_without_changing_head(tmp_path, monkeypatch):
    from scripts import reconcile_us_candidate_episodes as writer
    data = tmp_path / "data"
    _identity_spine(data)
    artifact = _turn_artifact()
    _v2_roundtrip(data, artifact, [_turn_row()])
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:01:00Z", correction_path=None)
    root = data / "us_prophet_rank/episodes"
    frozen = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    artifact["selection_era"] = "not-the-accepted-definition"
    _v2_roundtrip(data, artifact, [_turn_row()])
    with pytest.raises(EpisodeContractError, match="different committed bytes"):
        writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                         recorded_at="2026-11-27T18:02:00Z", correction_path=None)
    assert {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()} == frozen


def test_v2_cannot_be_downgraded_in_place_by_a_legacy_same_session_writer(tmp_path):
    _identity_spine(tmp_path)
    path, _ = _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    before = path.read_bytes()
    with pytest.raises(ValueError, match="new session"):
        write_candidate_episode_input(_turn_artifact(), [_turn_row()], tmp_path)
    assert path.read_bytes() == before


def test_v2_rejected_row_receipt_is_stable_when_only_build_runtime_changes(tmp_path):
    _identity_spine(tmp_path)
    artifact = {**_turn_artifact(), "runtime_seconds": 1.0}
    _, first = _v2_roundtrip(tmp_path, artifact, [_turn_row(triggers={})])
    artifact["runtime_seconds"] = 2.0
    _, second = _v2_roundtrip(tmp_path, artifact, [_turn_row(triggers={})])
    assert not first.observations and not second.observations
    assert first.suppressions == second.suppressions
    assert first.source_receipts != second.source_receipts


def test_v2_real_builder_cli_requires_an_explicit_schema_choice(tmp_path, monkeypatch):
    from scripts import build_turn_watch as builder
    data, site = tmp_path / "data", tmp_path / "site"
    _identity_spine(data)
    artifact = {**_turn_artifact(), "runtime_seconds": 1.0, "coverage": {
        "graded": 1, "triggered": 1, "deck": 1, "beyond_cap": 0,
        "deck_by_trigger": {"dot_1d": 1}, "source_contract": {"pass": True}}}
    monkeypatch.setattr(builder.config, "data_dir", lambda: data)
    monkeypatch.setattr(builder.config, "site_dir", lambda: site)
    monkeypatch.setattr(builder.turn_watch, "compute_deck_with_candidates",
                        lambda *a, **k: (artifact, [_turn_row()]))
    assert builder.build(["--episode-input-schema", "v2"]) == 0
    sidecar = data / "us_prophet_rank/episode_inputs/turn_watch/2026-11-27.json"
    assert json.loads(sidecar.read_text())["schema"] == _V2
    assert len(turn_watch_observations(sidecar, load_identity_spine(data)).observations) == 1
    frozen = sidecar.read_bytes()
    # A default legacy invocation must not overwrite the selected v2 session.
    assert builder.build([]) == 1
    assert sidecar.read_bytes() == frozen


def test_v2_new_schema_cannot_be_backdated_into_the_legacy_timeline(tmp_path):
    _identity_spine(tmp_path)
    later = {**_turn_artifact(), "data_session": "2026-11-30"}
    old = write_candidate_episode_input(later, [_turn_row()], tmp_path)
    old_bytes = old.read_bytes()
    with pytest.raises(ValueError, match="new session"):
        _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    assert old.read_bytes() == old_bytes
    assert not (old.parent / "2026-11-27.json").exists()


@pytest.mark.parametrize("defect", ("missing_selection_era", "empty_anchor_era", "false_known_at", "unknown_field"))
def test_v2_semantic_envelope_is_closed_even_with_a_recomputed_document_hash(tmp_path, defect):
    from engine.us_candidate_episode import canonical_json
    _identity_spine(tmp_path)
    path, _ = _v2_roundtrip(tmp_path, _turn_artifact(), [_turn_row()])
    doc = json.loads(path.read_bytes())
    if defect == "missing_selection_era":
        doc.pop("selection_era")
    elif defect == "empty_anchor_era":
        doc["anchor_era"] = ""
    elif defect == "false_known_at":
        doc["known_at"] = "2026-11-27T12:00:00Z"
    else:
        doc["unregistered_semantic_fact"] = "cannot-be-silently-ignored"
    doc["content_sha256"] = sha256(canonical_json({k: v for k, v in doc.items()
                                                  if k != "content_sha256"}).encode()).hexdigest()
    path.write_text(canonical_json(doc) + "\n")
    batch = turn_watch_observations(path, load_identity_spine(tmp_path))
    assert not batch.observations
    assert batch.source_receipts[0]["status"] == "degraded"
    assert batch.source_receipts[0]["reason"] == "MALFORMED_SOURCE"


@pytest.mark.parametrize("case", ("upgrade", "downgrade", "backdate"))
def test_rejected_schema_change_keeps_public_deck_unchanged(tmp_path, monkeypatch, case):
    from scripts import build_turn_watch as builder

    data, site = tmp_path / "data", tmp_path / "site"
    _identity_spine(data)
    artifact = {**_turn_artifact(), "runtime_seconds": 10.0, "coverage": {
        "graded": 1, "triggered": 1, "deck": 1, "beyond_cap": 0,
        "deck_by_trigger": {"dot_1d": 1}, "source_contract": {"pass": True}}}
    monkeypatch.setattr(builder.config, "data_dir", lambda: data)
    monkeypatch.setattr(builder.config, "site_dir", lambda: site)
    monkeypatch.setattr(builder.turn_watch, "compute_deck_with_candidates",
                        lambda *a, **k: (dict(artifact), [_turn_row()]))
    first_args = ["--episode-input-schema", "v2"] if case == "downgrade" else []
    assert builder.build(first_args) == 0
    public = site / "turn_watch/turn_watch.json"
    sidecar_root = data / "us_prophet_rank/episode_inputs/turn_watch"
    public_before = public.read_bytes()
    inputs_before = {p.name: p.read_bytes() for p in sidecar_root.glob("*.json")}
    artifact["runtime_seconds"] = 11.0
    if case == "backdate":
        artifact["data_session"] = "2026-11-25"
    blocked_args = [] if case == "downgrade" else ["--episode-input-schema", "v2"]
    assert builder.build(blocked_args) == 1
    assert public.read_bytes() == public_before, "a refused transition must not replace the public deck"
    assert {p.name: p.read_bytes() for p in sidecar_root.glob("*.json")} == inputs_before
