from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil

import pandas as pd
import pytest

from engine import prophet_candidate_state as b3_owner
from engine.prophet_candidate_state import (
    ASSESSMENT_OWNER_REF,
    CandidateStateContractError,
    build_native_factual_assessment,
    project_candidate_states,
    validate_candidate_state_projection,
    validate_native_factual_assessment,
)
from engine.prophet_daily_brief import _FORBIDDEN_KEYS
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot,
    ValidatedCandidateEpisodeGeneration,
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from scripts import reconcile_us_candidate_episodes as writer

GEN = "peg:" + "a" * 64


def cid(label, identity_epoch="epoch_0"):
    token = label.removeprefix("pe:")
    digest = token.encode("utf-8").hex().ljust(24, "0")[:24]
    return f"pe:SEC:US-XNAS-AAPL:{identity_epoch}:sa:{digest}:1"


@dataclass(frozen=True)
class Gen:
    episodes: tuple


@dataclass(frozen=True)
class Snap:
    generation_id: str
    generation: Gen


def ep(
    eid,
    state="ACTIVE",
    terminal_reason=None,
    superseded_by=None,
    identity_epoch="epoch_0",
):
    if not str(eid).startswith("pe:SEC:"):
        eid = cid(str(eid), identity_epoch)
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "identity_epoch": identity_epoch,
        "episode_state": state,
        "terminal_reason": terminal_reason,
        "superseded_by": superseded_by,
        "opened_at": "2026-09-17T20:00:00Z",
        "opened_session": "2026-09-17",
        "correction_state": "current",
    }


def test_lifecycle_mapping_preserves_source_truth_and_supersession_precedence():
    rows = (
        ep("pe:3", state="RESOLVED", terminal_reason="target"),
        ep("pe:1", state="ACTIVE", superseded_by="pe:9"),
        ep("pe:2", state="RETRACTED", terminal_reason="source retracted"),
        ep("pe:4", state="EXPIRED", terminal_reason="expired"),
    )
    out = project_candidate_states(
        Snap(GEN, Gen(rows)),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    got = {r["episode_id"]: r["episode_lifecycle"] for r in out["rows"]}
    assert got[cid("1")]["state"] == "SUPERSEDED"
    assert got[cid("1")]["source_state"] == "ACTIVE"
    assert got[cid("1")]["superseded_by"] == "pe:9"
    assert got[cid("2")]["state"] == "RETRACTED"
    assert got[cid("3")]["state"] == "CLOSED" and got[cid("3")]["source_state"] == "RESOLVED"
    assert got[cid("4")]["state"] == "CLOSED" and got[cid("4")]["source_state"] == "EXPIRED"


def test_maturity_maps_only_explicit_incumbent_stage_words():
    snapshot = Snap(
        GEN,
        Gen((ep("pe:1"), ep("pe:2"), ep("pe:3"), ep("pe:4"))),
    )
    out = project_candidate_states(
        snapshot,
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        maturity_stage_by_episode={
            cid("1"): "EARLY",
            cid("2"): "CONFIRMING",
            cid("3"): "CONFIRMED",
            cid("4"): "topping",
        },
    )
    got = {r["episode_id"]: r["maturity_state"] for r in out["rows"]}
    assert got[cid("1")]["state"] == "PRE_CONFIRMATION"
    assert got[cid("2")]["state"] == "EARLY_CONFIRMATION"
    assert got[cid("3")]["state"] == "CONFIRMED"
    assert got[cid("4")]["state"] == "UNESTIMABLE"
    assert got[cid("4")]["source_token"] == "topping"


def test_legacy_live_forming_does_not_manufacture_b3_emergence():
    snapshot = Snap(GEN, Gen((ep("pe:1"),)))
    out = project_candidate_states(
        snapshot,
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        emergence_by_episode={
            cid("1"): {
                "state": "UNESTIMABLE",
                "source_system": "prophet_live",
                "source_token": "forming",
                "source_ref": "pl:1",
            }
        },
    )
    row = out["rows"][0]
    assert row["emergence_state"]["state"] == "UNESTIMABLE"
    assert row["emergence_state"]["source_token"] == "forming"


def test_b4_slot_is_unavailable_even_when_legacy_entry_status_looks_actionable():
    episode = ep("pe:1")
    episode["entry_status"] = "buy_now"
    episode["plan_lifecycle"] = "active"
    out = project_candidate_states(
        Snap(GEN, Gen((episode,))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    row = out["rows"][0]
    assert row["entry_availability"] == {
        "state": "UNAVAILABLE_DATA",
        "reason": "B4_NOT_AVAILABLE",
    }
    assert "entry_status" not in row and "plan_lifecycle" not in row


def test_projection_is_deterministic_sorted_and_has_no_authority():
    a, b = ep("pe:z"), ep("pe:a")
    one = project_candidate_states(
        Snap(GEN, Gen((a, b))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    two = project_candidate_states(
        Snap(GEN, Gen((b, a))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    assert one == two
    assert [r["episode_id"] for r in one["rows"]] == [cid("a"), cid("z")]
    assert not any(one["authority"].values())
    assert all(not any(r["authority"].values()) for r in one["rows"])
    validate_candidate_state_projection(one)

def _rehash_projection(payload):
    material = {key: value for key, value in payload.items() if key != "projection_id"}
    canonical = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    payload["projection_id"] = "pcs:" + sha256(canonical.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("generated_at", "garbageZ"),
        ("generated_at", "2026-99-99T25:61:61Z"),
        ("market_session", "2026-99-99"),
        ("market_session", "2026-02-31"),
    ],
)
def test_projection_rejects_impossible_decision_clocks(field, bad_value):
    kwargs = {
        "market_session": "2026-09-17",
        "generated_at": "2026-09-18T01:00:00Z",
    }
    kwargs[field] = bad_value
    with pytest.raises(CandidateStateContractError):
        project_candidate_states(Snap(GEN, Gen((ep("pe:1"),))), **kwargs)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("generated_at", "garbageZ"),
        ("generated_at", "2026-99-99T25:61:61Z"),
        ("market_session", "2026-99-99"),
        ("market_session", "2026-02-31"),
    ],
)
def test_validator_rejects_rehashed_impossible_decision_clocks(field, bad_value):
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    tampered = deepcopy(out)
    tampered[field] = bad_value
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_trigger_without_source_provenance():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        emergence_by_episode={
            cid("1"): {
                "state": "TRIGGERED",
                "reason": None,
                "source_system": "turn_watch",
                "source_token": "OPENED",
                "source_ref": "tw:1",
            }
        },
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["emergence_state"] = {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": None,
        "source_token": None,
        "source_ref": None,
    }
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_incoherent_lifecycle():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["episode_lifecycle"]["state"] = "CLOSED"
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_validator_rejects_rehashed_incoherent_maturity():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
        maturity_stage_by_episode={cid("1"): "EARLY"},
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["maturity_state"]["state"] = "MATURE"
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


def test_projection_preserves_b1_identity_epoch_for_b4_keying():
    out = project_candidate_states(
        Snap(
            GEN,
            Gen(
                (
                    ep("pe:epoch0", identity_epoch="epoch_0"),
                    ep("pe:epoch1", identity_epoch="epoch_1"),
                )
            ),
        ),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    got = {row["episode_id"]: row["identity_epoch"] for row in out["rows"]}
    assert got == {cid("epoch0", "epoch_0"): "epoch_0", cid("epoch1", "epoch_1"): "epoch_1"}


def test_validator_rejects_rehashed_missing_or_empty_identity_epoch():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1", identity_epoch="epoch_0"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )

    missing = deepcopy(out)
    missing["rows"][0].pop("identity_epoch")
    _rehash_projection(missing)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(missing)

    empty = deepcopy(out)
    empty["rows"][0]["identity_epoch"] = ""
    _rehash_projection(empty)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(empty)

def test_validator_rejects_rehashed_identity_epoch_mismatch_with_b1_episode_id():
    out = project_candidate_states(
        Snap(GEN, Gen((ep("pe:1", identity_epoch="epoch_0"),))),
        market_session="2026-09-17",
        generated_at="2026-09-18T01:00:00Z",
    )
    tampered = deepcopy(out)
    tampered["rows"][0]["identity_epoch"] = "epoch_999"
    _rehash_projection(tampered)
    with pytest.raises(CandidateStateContractError):
        validate_candidate_state_projection(tampered)


# ---------------------------------------------------------------------------
# Prospective native factual observation assessment over a real B1 store.
#
# These tests drive the real nightly writer/reconcile over the shared intake
# fixtures, load the actual disk snapshot through the B1 owner loader, and bind
# a candidate source key to the native ledger. The module assembly clock is the
# only monkeypatched owner seam.
# ---------------------------------------------------------------------------

FIXTURE_ROOT = Path(__file__).parent / "fixtures/us_candidate_episode/intake"
ASSEMBLY_NOW = datetime(2026, 11, 29, 0, 0, 0, tzinfo=timezone.utc)
CANDIDATE_KEY = "candidate:2026-11-27:ALFA:us_prophet_v3"
CANDIDATE_ROW = {
    "stamp_date": "2026-11-27",
    "ticker": "ALFA",
    "board_definition": "us_prophet_v3",
    "tier": "curated",
}
_NEXT_SESSION_KEY = "candidate:2026-11-28:ALFA:us_prophet_v3"


def _set_assembly_clock(monkeypatch, now=ASSEMBLY_NOW):
    monkeypatch.setattr(b3_owner, "_assembly_now", lambda: now)


def _turn_watch_document(session, *, reset_date="2026-11-27", reset_low=42.1):
    document = {
        "schema": "prophet.candidate_episode_input.turn_watch/v1",
        "anchor_era": "anchor-v1",
        "selection_era": "anticipation-v1",
        "data_session": session,
        "known_at": session + "T18:00:00Z",
        "rows": [
            {
                "asof": session,
                "ticker": "ALFA",
                "reset": {"reset_low": reset_low, "reset_low_date": reset_date},
                "triggers": {
                    "dot_1d": {"evaluated": True, "fired": True, "last_date": session}
                },
            }
        ],
    }
    document["content_sha256"] = sha256(
        canonical_json(
            {key: value for key, value in document.items() if key != "content_sha256"}
        ).encode("utf-8")
    ).hexdigest()
    return document


def _identity_spine(data):
    reference = data / "reference"
    reference.mkdir(parents=True)
    for name in ("security_master", "vendor_aliases"):
        rows = json.loads((FIXTURE_ROOT / f"{name}.json").read_text())
        pd.DataFrame(rows).to_parquet(reference / f"{name}.parquet", index=False)


def _write_candidates(data, rows):
    candidate_dir = data / "us_prophet_rank/candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows)).to_parquet(candidate_dir / "2026-11.parquet", index=False)


def _run_reconcile(root, recorded_at, corrections=None):
    original = writer.nightly_advance_enabled
    writer.nightly_advance_enabled = lambda: True
    try:
        return writer.reconcile(
            repo_root=root, nightly=True, replay=False,
            recorded_at=recorded_at, correction_path=corrections,
        )
    finally:
        writer.nightly_advance_enabled = original


def _build_native_store(
    root,
    *,
    run1_candidates=(),
    run2_candidates=None,
    refresh_turn_watch=False,
):
    """Reconcile TURN WATCH first, then append NEW source keys for run two."""
    data = root / "data"
    _identity_spine(data)
    turn_dir = data / "us_prophet_rank/episode_inputs/turn_watch"
    turn_dir.mkdir(parents=True)
    (turn_dir / "2026-11-27.json").write_text(
        canonical_json(_turn_watch_document("2026-11-27")) + "\n"
    )
    if run1_candidates:
        _write_candidates(data, run1_candidates)
    _run_reconcile(root, "2026-11-27T18:05:00Z")
    if refresh_turn_watch:
        (turn_dir / "2026-11-28.json").write_text(
            canonical_json(_turn_watch_document("2026-11-28")) + "\n"
        )
    if run2_candidates is not None:
        _write_candidates(data, run2_candidates)
    _run_reconcile(root, "2026-11-28T22:00:00Z")


def _episode_root(root):
    return root / "data/us_prophet_rank/episodes"


def _load_snapshot(root):
    return load_candidate_episode_store_snapshot(_episode_root(root))


def _candidate_relation(snapshot, source_event_id=CANDIDATE_KEY):
    for event in snapshot.generation.events:
        if event.get("source_event_id") == source_event_id:
            return event
    raise AssertionError(f"no native relation for {source_event_id}")


def _native_assessment(snapshot, source_event_id=CANDIDATE_KEY):
    return build_native_factual_assessment(
        snapshot,
        candidate_source_event_id=source_event_id,
        candidate_source_receipt=_candidate_relation(snapshot, source_event_id)[
            "source_receipt"
        ],
    )


@pytest.fixture(scope="module")
def native_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("native_b3_store")
    _build_native_store(root, run2_candidates=[CANDIDATE_ROW])
    return root


@pytest.fixture(scope="module")
def refreshed_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("native_b3_refreshed_store")
    _build_native_store(
        root, run2_candidates=[CANDIDATE_ROW], refresh_turn_watch=True
    )
    return root


@pytest.fixture(scope="module")
def next_session_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("native_b3_next_session_store")
    _build_native_store(
        root,
        run2_candidates=[{**CANDIDATE_ROW, "stamp_date": "2026-11-28"}],
        refresh_turn_watch=True,
    )
    return root


@pytest.fixture(scope="module")
def suppressed_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("native_b3_suppressed_store")
    _build_native_store(
        root, run1_candidates=[CANDIDATE_ROW], run2_candidates=[CANDIDATE_ROW]
    )
    return root


def _copy_store(root, tmp_path):
    target = tmp_path / "store"
    shutil.copytree(root, target)
    return target


def _write_corrections(root, commands):
    path = root / "corrections.jsonl"
    path.write_text(
        "".join(canonical_json(command) + "\n" for command in commands)
    )
    return path


def test_native_assessment_binds_new_candidate_source_key_from_real_store(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    assessment = _native_assessment(snapshot)
    validate_native_factual_assessment(assessment)

    assert assessment["schema"] == "prophet.daily_brief_assessment_input/v1"
    assert assessment["owner_ref"] == ASSESSMENT_OWNER_REF
    assert assessment["state"] == "REVIEW_REQUIRED"
    assert assessment["security_id"] == "SEC:US-XNAS-ALFA"
    assert assessment["market_session"] == "2026-11-27"
    assert assessment["candidate_generation_id"] == snapshot.generation_id
    assert assessment["episode_id"] == _candidate_relation(snapshot)["episode_id"]

    summary = assessment["summary"]
    assert summary["method"] == "deterministic_native_factual_observation"
    assert summary["assessment_state"] == "REVIEW_REQUIRED"
    # The run-one TURN WATCH relation is not generation-local in generation
    # two, so the native owner semantics yield no estimable emergence.
    assert summary["emergence_state"] == "UNESTIMABLE"
    assert summary["emergence_reason"] == "SOURCE_NOT_SUPPLIED"
    assert summary["emergence_source_ref"] is None
    assert summary["episode_lifecycle_state"] == "ACTIVE"
    assert summary["maturity_state"] == "UNESTIMABLE"
    assert summary["entry_availability_state"] == "UNAVAILABLE_DATA"
    assert summary["b4_native_owner_read"] == "B4_NATIVE_OWNER_READ_UNAVAILABLE"
    assert summary["model_thesis"] == "UNAVAILABLE"
    assert summary["review_lineage"] == "UNAVAILABLE"
    assert summary["review_ref"] is None
    assert summary["source_freshness"] == "NOT_RENEWED_BY_ASOF"

    provenance = assessment["provenance"]
    assert provenance["episode_opened_at"] == "2026-11-27T18:00:00Z"
    assert provenance["episode_opened_session"] == "2026-11-27"
    assert provenance["generation_recorded_at"] == "2026-11-28T22:00:00Z"
    assert provenance["turn_watch"]["facts"] == 0
    relation = provenance["matched_relation"]
    assert relation["relation_event_type"] == "OBSERVED"
    assert relation["relation_source_schema"] == "us_prophet_rank.candidates/v1"
    assert relation["relation_source_event_id"] == CANDIDATE_KEY
    assert relation["relation_occurred_at"] == "2026-11-27T18:00:00Z"
    assert relation["relation_known_at"] == "2026-11-27T18:00:00Z"
    assert relation["relation_recorded_at"] == "2026-11-28T22:00:00Z"
    assert provenance["input_binding"] == {
        "candidate_source_event_id": CANDIDATE_KEY,
        "candidate_source_receipt": _candidate_relation(snapshot)["source_receipt"],
    }
    assert provenance["b3_projection_id"].startswith("pcs:")
    assert assessment["source_receipt"].startswith("sha256:")


def test_native_assessment_derives_triggered_only_from_generation_local_turn_watch(
    refreshed_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(refreshed_store)
    assessment = _native_assessment(snapshot)
    summary = assessment["summary"]
    assert summary["emergence_state"] == "TRIGGERED"
    assert summary["emergence_source_system"] == "turn_watch"
    assert summary["emergence_source_token"] == "B1_OBSERVED"
    relation_event_id = summary["emergence_source_ref"]
    selected = next(
        event
        for event in snapshot.generation.events
        if event.get("event_id") == relation_event_id
    )
    assert selected["source_system"] == "turn_watch"
    assert selected["source_schema"] == "prophet.candidate_episode_input.turn_watch/v1"
    assert selected["recorded_at"] == "2026-11-28T22:00:00Z"
    turn_watch = assessment["provenance"]["turn_watch"]
    assert turn_watch["facts"] == 1
    assert turn_watch["selected_relation_event_id"] == relation_event_id
    assert turn_watch["selected_known_at"] == selected["known_at"]


def test_native_assessment_market_session_comes_from_source_key_only(
    next_session_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(next_session_store)
    assessment = _native_assessment(snapshot, _NEXT_SESSION_KEY)
    assert assessment["market_session"] == "2026-11-28"
    provenance = assessment["provenance"]
    # The source-key session, the episode open session and the generation
    # recorded_at stay separate: market_session is never inferred from them.
    assert provenance["episode_opened_session"] == "2026-11-27"
    assert provenance["episode_opened_at"] == "2026-11-27T18:00:00Z"
    assert provenance["generation_recorded_at"] == "2026-11-28T22:00:00Z"
    assert provenance["matched_relation"]["relation_occurred_at"][:10] == "2026-11-28"
    assert assessment["market_session"] != provenance["episode_opened_session"]


def test_native_assessment_rejects_duck_typed_snapshot(monkeypatch):
    _set_assembly_clock(monkeypatch)
    with pytest.raises(CandidateStateContractError, match="CandidateEpisodeStoreSnapshot"):
        build_native_factual_assessment(
            Snap(GEN, Gen((ep("pe:1"),))),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="sha256:" + "0" * 64,
        )


def test_native_assessment_rejects_snapshot_that_disagrees_with_disk(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    generation = snapshot.generation
    receipt = _candidate_relation(snapshot)["source_receipt"]

    def tampered(**changes):
        fields = {
            "path": generation.path,
            "events": generation.events,
            "suppressions": generation.suppressions,
            "episodes": generation.episodes,
            "receipt": generation.receipt,
        }
        fields.update(changes)
        return CandidateEpisodeStoreSnapshot(
            snapshot.generation_id,
            ValidatedCandidateEpisodeGeneration(**fields),
        )

    with pytest.raises(CandidateStateContractError, match="disagrees"):
        build_native_factual_assessment(
            tampered(events=generation.events[:-1]),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=receipt,
        )
    mutated_rows = tuple(
        {**row, "identity_epoch": "epoch_9"}
        if row["episode_id"] == _candidate_relation(snapshot)["episode_id"]
        else row
        for row in generation.episodes
    )
    with pytest.raises(CandidateStateContractError, match="disagrees"):
        build_native_factual_assessment(
            tampered(episodes=mutated_rows),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=receipt,
        )
    with pytest.raises(CandidateStateContractError, match="disagrees"):
        build_native_factual_assessment(
            tampered(
                receipt={
                    **generation.receipt,
                    "recorded_at": "2026-11-28T23:59:59Z",
                }
            ),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=receipt,
        )


def test_native_assessment_rejects_generation_identity_mismatch(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    forged = CandidateEpisodeStoreSnapshot("peg:" + "b" * 64, snapshot.generation)
    with pytest.raises(CandidateStateContractError, match="disk validation"):
        build_native_factual_assessment(
            forged,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"],
        )


def test_native_assessment_rejects_unknown_candidate_source_key(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    with pytest.raises(CandidateStateContractError, match="no OPENED/OBSERVED relation"):
        build_native_factual_assessment(
            snapshot,
            candidate_source_event_id="candidate:2026-11-27:MISSING:us_prophet_v3",
            candidate_source_receipt="sha256:" + "0" * 64,
        )


def test_native_assessment_rejects_wrong_source_digest(native_store, monkeypatch):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    with pytest.raises(CandidateStateContractError, match="source receipt"):
        build_native_factual_assessment(
            snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="sha256:" + "f" * 64,
        )
    with pytest.raises(CandidateStateContractError, match="sha256 receipt"):
        build_native_factual_assessment(
            snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="deadbeef",
        )


def test_candidate_relation_matcher_rejects_ambiguous_suppressed_and_bad_keys():
    relation = {
        "schema": "prophet.candidate_episode_event/v1",
        "event_id": "pee:" + "1" * 64,
        "event_type": "OBSERVED",
        "episode_id": "pe:x",
        "source_system": "candidate",
        "source_schema": "us_prophet_rank.candidates/v1",
        "source_event_id": CANDIDATE_KEY,
        "source_receipt": "sha256:" + "2" * 64,
    }
    twin = {**relation, "event_id": "pee:" + "3" * 64}
    with pytest.raises(CandidateStateContractError, match="ambiguous"):
        b3_owner._match_candidate_relation(
            (relation, twin),
            (),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="sha256:" + "2" * 64,
        )
    suppression = {
        "source_system": "candidate",
        "source_schema": "us_prophet_rank.candidates/v1",
        "source_event_id": CANDIDATE_KEY,
    }
    with pytest.raises(CandidateStateContractError, match="suppressed"):
        b3_owner._match_candidate_relation(
            (),
            (suppression,),
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="sha256:" + "2" * 64,
        )
    with pytest.raises(CandidateStateContractError, match="real calendar date"):
        b3_owner._match_candidate_relation(
            (),
            (),
            candidate_source_event_id="candidate:2026-02-31:ALFA:us_prophet_v3",
            candidate_source_receipt="sha256:" + "2" * 64,
        )
    with pytest.raises(CandidateStateContractError, match="canonical"):
        b3_owner._match_candidate_relation(
            (),
            (),
            candidate_source_event_id="ALFA:2026-11-27",
            candidate_source_receipt="sha256:" + "2" * 64,
        )


def test_suppressed_candidate_source_key_cannot_be_reopened(suppressed_store, monkeypatch):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(suppressed_store)
    # Run one suppressed the candidate row (no structural anchor existed yet).
    # The turn-watch open exists, but the immutable source key stayed with the
    # suppression and can never be reopened as a relation in a later run.
    assert not any(
        event.get("source_event_id") == CANDIDATE_KEY
        for event in snapshot.generation.events
    )
    assert any(
        row.get("source_event_id") == CANDIDATE_KEY
        for row in snapshot.generation.suppressions
    )
    with pytest.raises(CandidateStateContractError, match="suppressed"):
        build_native_factual_assessment(
            snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt="sha256:" + "7" * 64,
        )


def test_native_assessment_rejects_retracted_candidate_relation(
    native_store, tmp_path, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    copied = _copy_store(native_store, tmp_path)
    snapshot = _load_snapshot(copied)
    relation = _candidate_relation(snapshot)
    corrections = _write_corrections(
        copied,
        [
            {
                "event_type": "RETRACTED",
                "episode_id": relation["episode_id"],
                "source_system": "candidate_governance",
                "source_schema": "prophet_candidate_governance/v1",
                "source_event_id": "candidate_retraction:2026-11-28:ALFA:us_prophet_v3",
                "occurred_at": "2026-11-28T23:00:00Z",
                "known_at": "2026-11-28T23:00:00Z",
                "source_receipt": "sha256:" + "b" * 64,
                "correction_of": relation["event_id"],
                "payload": {"reason": "duplicate candidate source row"},
            }
        ],
    )
    _run_reconcile(copied, "2026-11-28T23:30:00Z", corrections=corrections)
    retracted_snapshot = _load_snapshot(copied)
    with pytest.raises(CandidateStateContractError, match="retracted"):
        build_native_factual_assessment(
            retracted_snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=relation["source_receipt"],
        )


def test_native_assessment_preserves_terminal_truth_without_supersession(
    native_store, tmp_path, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    copied = _copy_store(native_store, tmp_path)
    snapshot = _load_snapshot(copied)
    relation = _candidate_relation(snapshot)
    corrections = _write_corrections(
        copied,
        [
            {
                "event_type": "STATE_TRANSITIONED",
                "episode_id": relation["episode_id"],
                "source_system": "candidate_governance",
                "source_schema": "prophet_candidate_governance/v1",
                "source_event_id": "candidate_resolution:2026-11-28:ALFA:us_prophet_v3",
                "occurred_at": "2026-11-28T23:00:00Z",
                "known_at": "2026-11-28T23:00:00Z",
                "source_receipt": "sha256:" + "c" * 64,
                "payload": {
                    "episode_state": "RESOLVED",
                    "terminal_reason": "thesis resolved at target",
                },
            }
        ],
    )
    _run_reconcile(copied, "2026-11-28T23:30:00Z", corrections=corrections)
    terminal = _load_snapshot(copied)
    assessment = build_native_factual_assessment(
        terminal,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=relation["source_receipt"],
    )
    # Terminal B1 truth is preserved literally; a resolution never implies
    # SUPERSEDED without an actual superseded_by, and the assembly stays a
    # factual REVIEW_REQUIRED observation.
    assert assessment["summary"]["episode_lifecycle_state"] == "CLOSED"
    assert assessment["provenance"]["episode_lifecycle_state"] == "CLOSED"
    assert assessment["summary"]["episode_lifecycle_state"] != "SUPERSEDED"
    assert assessment["state"] == "REVIEW_REQUIRED"


def test_native_assessment_fails_closed_when_source_clocks_are_future(
    native_store, monkeypatch
):
    monkeypatch.setattr(
        b3_owner,
        "_assembly_now",
        lambda: datetime(2026, 11, 27, 17, 59, 59, tzinfo=timezone.utc),
    )
    snapshot = _load_snapshot(native_store)
    with pytest.raises(CandidateStateContractError, match="future"):
        build_native_factual_assessment(
            snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"],
        )


def test_native_chronology_fails_closed_on_malformed_or_inconsistent_clocks():
    relation = {
        "event_type": "OBSERVED",
        "occurred_at": "2026-11-27T18:00:00Z",
        "known_at": "2026-11-27T18:00:00Z",
        "recorded_at": "2026-11-28T22:00:00Z",
    }

    def chronology(**overrides):
        values = {
            "opened_at": "2026-11-27T18:00:00Z",
            "opened_session": "2026-11-27",
            "relation": relation,
            "generation_recorded_at": "2026-11-28T22:00:00Z",
            "turn_fact": None,
            "now": ASSEMBLY_NOW,
        }
        values.update(overrides)
        b3_owner._validate_native_chronology(**values)

    chronology()
    with pytest.raises(CandidateStateContractError, match="opened_at"):
        chronology(opened_at=None)
    with pytest.raises(CandidateStateContractError, match="opened_at"):
        chronology(opened_at="not-a-clock")
    with pytest.raises(CandidateStateContractError, match="opened_session"):
        chronology(opened_session="2026-11-28")
    with pytest.raises(CandidateStateContractError, match="chronological"):
        chronology(
            relation={**relation, "occurred_at": "2026-11-28T23:00:00Z"}
        )
    with pytest.raises(CandidateStateContractError, match="occurred_at"):
        chronology(
            opened_at="2026-11-28T20:00:00Z",
            opened_session="2026-11-28",
            relation={**relation, "occurred_at": "2026-11-27T18:00:00Z"},
        )
    with pytest.raises(CandidateStateContractError, match="generation\n? recorded_at|recorded_at is after"):
        chronology(generation_recorded_at="2026-11-27T19:00:00Z")
    with pytest.raises(CandidateStateContractError, match="future"):
        chronology(now=datetime(2026, 11, 20, tzinfo=timezone.utc))
    with pytest.raises(CandidateStateContractError, match="turn_watch"):
        chronology(
            turn_fact={
                "occurred_at": "2026-11-28T22:00:00Z",
                "known_at": "2026-11-28T21:00:00Z",
            }
        )
    with pytest.raises(CandidateStateContractError, match="turn_watch"):
        chronology(
            turn_fact={
                "occurred_at": "2026-11-28T21:00:00Z",
                "known_at": "2026-12-01T00:00:00Z",
            }
        )


def test_native_assessment_is_deterministic_and_leaves_inputs_immutable(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    before = {
        field: canonical_json(getattr(snapshot.generation, field))
        for field in ("events", "suppressions", "episodes", "receipt")
    }
    receipt = _candidate_relation(snapshot)["source_receipt"]
    first = build_native_factual_assessment(
        snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=receipt,
    )
    second = build_native_factual_assessment(
        snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=receipt,
    )
    assert first == second
    mutated = deepcopy(first)
    mutated["summary"]["model_thesis"] = "fabricated"
    assert build_native_factual_assessment(
        snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=receipt,
    ) == first
    for field, frozen in before.items():
        assert canonical_json(getattr(snapshot.generation, field)) == frozen
    # The envelope carries its own receipted material and never aliases the
    # native owner objects it read from.
    assert first["provenance"]["matched_relation"] is not first["receipt_material"]["matched_relation"]
    validate_native_factual_assessment(first)


def test_native_assessment_validator_rejects_tampered_envelopes(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    assessment = _native_assessment(snapshot)
    validate_native_factual_assessment(assessment)

    promoted = deepcopy(assessment)
    promoted["state"] = "CURRENT"
    with pytest.raises(CandidateStateContractError, match="REVIEW_REQUIRED"):
        validate_native_factual_assessment(promoted)

    reidentified = deepcopy(assessment)
    reidentified["security_id"] = "SEC:US-XNAS-MSFT"
    with pytest.raises(CandidateStateContractError, match="receipted material"):
        validate_native_factual_assessment(reidentified)

    rebinding = deepcopy(assessment)
    rebinding["provenance"]["input_binding"]["candidate_source_receipt"] = (
        "sha256:" + "0" * 64
    )
    with pytest.raises(CandidateStateContractError):
        validate_native_factual_assessment(rebinding)

    relabeled = deepcopy(assessment)
    relabeled["market_session"] = "2026-11-28"
    with pytest.raises(CandidateStateContractError):
        validate_native_factual_assessment(relabeled)


def test_native_assessment_old_observation_never_becomes_current(
    native_store, monkeypatch
):
    monkeypatch.setattr(
        b3_owner, "_assembly_now", lambda: datetime(2027, 6, 1, tzinfo=timezone.utc)
    )
    snapshot = _load_snapshot(native_store)
    assessment = _native_assessment(snapshot)
    assert assessment["asof"].startswith("2027-06-01T")
    assert assessment["state"] == "REVIEW_REQUIRED"
    assert assessment["summary"]["assessment_state"] == "REVIEW_REQUIRED"
    assert assessment["summary"]["source_freshness"] == "NOT_RENEWED_BY_ASOF"
    # Source clocks stay at their literal native values in provenance.
    assert assessment["provenance"]["generation_recorded_at"] == "2026-11-28T22:00:00Z"


def test_native_assessment_carries_no_model_authority_or_forbidden_keys(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    assessment = _native_assessment(snapshot)
    assert "authority" not in assessment

    def walk(value, path="assessment"):
        if isinstance(value, Mapping):
            for key, nested in value.items():
                assert str(key).lower() not in _FORBIDDEN_KEYS, (
                    f"forbidden authority key at {path}.{key}"
                )
                walk(nested, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")

    walk(assessment)
    assert assessment["summary"]["model_thesis"] == "UNAVAILABLE"
    assert assessment["summary"]["b4_native_owner_read"] == (
        "B4_NATIVE_OWNER_READ_UNAVAILABLE"
    )
    assert assessment["summary"]["review_ref"] is None


def test_native_assessment_is_a_valid_daily_brief_assessment_input(
    native_store, monkeypatch
):
    from engine.prophet_daily_brief import compose_daily_brief

    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    assessment = _native_assessment(snapshot)
    identity = {
        field: assessment[field]
        for field in (
            "security_id",
            "episode_id",
            "candidate_generation_id",
            "market_session",
        )
    }
    candidate_input = {
        **identity,
        "schema": "prophet.daily_brief_candidate_input/v1",
        "owner_ref": "engine/test_candidate_owner.py",
        "asof": assessment["asof"],
        "source_receipt": "sha256:" + "1" * 64,
        "state": "SELECTED",
        "selection_receipt": "sha256:" + "2" * 64,
        "display": {"ticker": "ALFA"},
    }
    plan_input = {
        **identity,
        "schema": "prophet.daily_brief_plan_input/v1",
        "owner_ref": "engine/test_plan_owner.py",
        "asof": assessment["asof"],
        "source_receipt": "sha256:" + "3" * 64,
        "state": "UNAVAILABLE",
        "relation_state": "unavailable",
        "exact_relation": "unavailable",
        "plan_ids": [],
    }
    evidence_input = {
        **identity,
        "schema": "prophet.daily_brief_evidence_input/v1",
        "owner_ref": "engine/test_evidence_owner.py",
        "asof": assessment["asof"],
        "source_receipt": "sha256:" + "4" * 64,
        "state": "PARTIAL",
        "coverage": {},
    }
    assembly_input = {
        "schema": "prophet.daily_brief_assembly_input/v1",
        "owner_ref": "engine/test_assembly_owner.py",
        "state": "OK",
        "assembled_at": assessment["asof"],
        "source_receipts": ["sha256:" + "5" * 64],
    }
    view = compose_daily_brief(
        candidate=candidate_input,
        entry_availability=None,
        plan=plan_input,
        assessment=assessment,
        evidence=evidence_input,
        assembly=assembly_input,
        recovery=None,
        previous=None,
        now=assessment["asof"],
    )
    assert view["owners"]["assessment"]["owner_ref"] == ASSESSMENT_OWNER_REF
    assert view["owners"]["assessment"]["state"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# Parent red probes: the presented envelope is receipt-bound - no display fact
# may travel under a genuine source_receipt digest.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tamper", [
    "emergence", "lifecycle", "assembly_clock",
    "source_binding", "native_provenance", "invalid_lifecycle",
])
def test_native_presented_assessment_is_receipt_bound(native_store, monkeypatch, tamper):
    _set_assembly_clock(monkeypatch)
    original = _native_assessment(_load_snapshot(native_store))
    forged = deepcopy(original)
    if tamper == "emergence":
        forged["summary"].update(emergence_state="TRIGGERED", emergence_reason=None,
            emergence_source_system="turn_watch", emergence_source_token="B1_OBSERVED",
            emergence_source_ref="pee:" + "d" * 64)
    elif tamper == "lifecycle":
        forged["summary"]["episode_lifecycle_state"] = "CLOSED"
        forged["provenance"]["episode_lifecycle_state"] = "CLOSED"
    elif tamper == "assembly_clock":
        forged["asof"] = "2026-11-29T22:01:00Z"
    elif tamper == "source_binding":
        forged["provenance"]["input_binding"].update(
            candidate_source_event_id="candidate:2026-11-27:BETA:governed-v1",
            candidate_source_receipt="sha256:" + "e" * 64)
        forged["provenance"]["matched_relation"].update(
            relation_source_event_id="candidate:2026-11-27:BETA:governed-v1",
            relation_source_receipt="sha256:" + "e" * 64)
    elif tamper == "native_provenance":
        forged["provenance"].update(episode_opened_at=None, generation_recorded_at=None,
            b3_projection_id="pcs:" + "f" * 64)
    elif tamper == "invalid_lifecycle":
        forged["provenance"]["episode_lifecycle_state"] = "BANANA"
    assert forged["source_receipt"] == original["source_receipt"]
    with pytest.raises(CandidateStateContractError):
        validate_native_factual_assessment(forged)


def test_native_result_binds_one_assembly_projection_to_the_assessment(native_store, monkeypatch):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    receipt = _candidate_relation(snapshot)["source_receipt"]
    calls = {"index": 0, "project": 0}
    real_index = b3_owner.index_turn_watch_events
    real_project = b3_owner.project_candidate_states

    def counted_index(snap):
        calls["index"] += 1
        return real_index(snap)

    def counted_project(snap, **kwargs):
        calls["project"] += 1
        return real_project(snap, **kwargs)

    monkeypatch.setattr(b3_owner, "index_turn_watch_events", counted_index)
    monkeypatch.setattr(b3_owner, "project_candidate_states", counted_project)
    result = b3_owner.build_native_factual_assessment_result(
        snapshot, candidate_source_event_id=CANDIDATE_KEY, candidate_source_receipt=receipt)
    # One owner read derives exactly one TURN WATCH index and one projection,
    # and that same internally derived projection is what the receipt binds.
    assert calls == {"index": 1, "project": 1}
    assert result.assessment["asof"] == result.projection["generated_at"]
    assert result.assessment["market_session"] == result.projection["market_session"]
    provenance = result.assessment["provenance"]
    assert provenance["b3_projection_id"] == result.projection["projection_id"]
    assert provenance["b3_projection_sha256"] == (
        "sha256:" + sha256(canonical_json(result.projection).encode("utf-8")).hexdigest())
    assert result.assessment["receipt_material"]["b3_projection_sha256"] == (
        provenance["b3_projection_sha256"])
    validate_candidate_state_projection(result.projection)
    validate_native_factual_assessment(result.assessment)
    # The fixed read result is stable for the same read, and the historical
    # entry point stays a compatible assessment-only wrapper over it.
    again = b3_owner.build_native_factual_assessment_result(
        snapshot, candidate_source_event_id=CANDIDATE_KEY, candidate_source_receipt=receipt)
    assert again.assessment == result.assessment
    assert again.projection == result.projection
    assert build_native_factual_assessment(
        snapshot, candidate_source_event_id=CANDIDATE_KEY, candidate_source_receipt=receipt,
    ) == result.assessment


def test_native_result_is_frozen_and_rejects_unreceipted_pairs(native_store, monkeypatch):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    result = b3_owner.build_native_factual_assessment_result(
        snapshot, candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"])
    with pytest.raises(AttributeError):
        result.assessment = {}
    # A caller cannot rebind the result onto a fabricated envelope...
    forged = deepcopy(result.assessment)
    forged["provenance"]["b3_projection_id"] = "pcs:" + "0" * 64
    with pytest.raises(CandidateStateContractError):
        b3_owner.NativeFactualAssessmentResult(forged, deepcopy(result.projection))
    # ...nor onto a reprojected decision-session projection the receipt never covered.
    reprojected = deepcopy(result.projection)
    reprojected["generated_at"] = "2027-01-01T00:00:00Z"
    _rehash_projection(reprojected)
    with pytest.raises(CandidateStateContractError):
        b3_owner.NativeFactualAssessmentResult(deepcopy(result.assessment), reprojected)


# ---------------------------------------------------------------------------
# Verified-use probes: the fixed read result must refuse drifted nested maps
# and cross-read pairs, and the closed validator must refuse structurally
# incoherent envelopes. Rehashing a forged payload or re-issuing its keyless
# envelope receipt is a structural-coherence probe only — it is never proof
# of external authentication.
# ---------------------------------------------------------------------------


def _reforge_source_receipt(forged):
    forged["source_receipt"] = b3_owner._envelope_receipt(forged)
    return forged


def _repointed_projection_digest(assessment, projection):
    assessment["provenance"]["b3_projection_id"] = projection["projection_id"]
    assessment["provenance"]["b3_projection_sha256"] = (
        "sha256:"
        + sha256(canonical_json(projection).encode("utf-8")).hexdigest()
    )
    assessment["receipt_material"]["b3_projection_sha256"] = assessment[
        "provenance"
    ]["b3_projection_sha256"]
    return assessment


def test_native_result_verified_pair_returns_detached_validated_documents(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    result = b3_owner.build_native_factual_assessment_result(
        snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"],
    )
    assessment, projection = result.verified_pair()
    validate_native_factual_assessment(assessment)
    validate_candidate_state_projection(projection)
    assert assessment == result.assessment
    assert projection == result.projection
    # The consumed pair is detached: later mutation of it can never alter
    # the stored read result or another consumer's pair.
    assert assessment is not result.assessment
    assert assessment["provenance"] is not result.assessment["provenance"]
    assert projection["rows"] is not result.projection["rows"]
    assessment["summary"]["emergence_state"] = "TRIGGERED"
    projection["generated_at"] = "2027-01-01T00:00:00Z"
    projection["rows"][0]["security_id"] = "SEC:US-XNAS-MSFT"
    assert result.assessment["summary"]["emergence_state"] == "UNESTIMABLE"
    assert result.projection["generated_at"] != "2027-01-01T00:00:00Z"
    again_assessment, again_projection = result.verified_pair()
    assert again_projection["rows"][0]["security_id"] == "SEC:US-XNAS-ALFA"
    assert again_assessment == result.assessment


def test_native_result_refuses_nested_drift_at_verified_use(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(native_store)
    receipt = _candidate_relation(snapshot)["source_receipt"]

    def build():
        return b3_owner.build_native_factual_assessment_result(
            snapshot,
            candidate_source_event_id=CANDIDATE_KEY,
            candidate_source_receipt=receipt,
        )

    # Stored nested maps stay plain mappings, but the documented verified
    # accessor must refuse drifted bytes instead of silently serving them.
    result = build()
    result.projection["generated_at"] = "2027-01-01T00:00:00Z"
    with pytest.raises(CandidateStateContractError):
        result.verified_pair()
    # Rehashing the drifted projection cannot smuggle it past the receipted
    # projection digest (structural coherence, not external authentication).
    _rehash_projection(result.projection)
    with pytest.raises(CandidateStateContractError):
        result.verified_pair()

    result = build()
    result.assessment["summary"]["model_thesis"] = "fabricated"
    with pytest.raises(CandidateStateContractError):
        result.verified_pair()

    # A re-receipted asof drift is envelope-valid on its own but no longer
    # pairs with the one projection this read actually assembled.
    result = build()
    result.assessment["asof"] = "2026-11-30T00:00:00Z"
    _reforge_source_receipt(result.assessment)
    with pytest.raises(CandidateStateContractError, match="asof"):
        result.verified_pair()


def test_native_result_rejects_cross_assembly_and_cross_generation_pairs(
    native_store, refreshed_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    first = b3_owner.build_native_factual_assessment_result(
        _load_snapshot(native_store),
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(
            _load_snapshot(native_store)
        )["source_receipt"],
    )
    # A second native read of the same generation assembles a different
    # projection (different asof). Re-pointing provenance and re-issuing the
    # keyless receipt must still not pair them.
    _set_assembly_clock(
        monkeypatch, datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    second = b3_owner.build_native_factual_assessment_result(
        _load_snapshot(native_store),
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(
            _load_snapshot(native_store)
        )["source_receipt"],
    )
    assert first.projection["generated_at"] != second.projection["generated_at"]
    cross_assembly = _reforge_source_receipt(
        _repointed_projection_digest(
            deepcopy(first.assessment), second.projection
        )
    )
    validate_native_factual_assessment(cross_assembly)
    with pytest.raises(CandidateStateContractError, match="asof"):
        b3_owner.NativeFactualAssessmentResult(
            cross_assembly, deepcopy(second.projection)
        )

    # A projection from a different native read/generation never pairs either.
    other_snapshot = _load_snapshot(refreshed_store)
    other = b3_owner.build_native_factual_assessment_result(
        other_snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(other_snapshot)[
            "source_receipt"
        ],
    )
    assert other.assessment["candidate_generation_id"] != (
        first.assessment["candidate_generation_id"]
    )
    cross_generation = _reforge_source_receipt(
        _repointed_projection_digest(
            deepcopy(other.assessment), first.projection
        )
    )
    validate_native_factual_assessment(cross_generation)
    with pytest.raises(CandidateStateContractError, match="assessed native read"):
        b3_owner.NativeFactualAssessmentResult(
            cross_generation, deepcopy(first.projection)
        )


def test_native_result_rejects_projection_row_contradicting_summary(
    refreshed_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    snapshot = _load_snapshot(refreshed_store)
    result = b3_owner.build_native_factual_assessment_result(
        snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"],
    )
    assert result.assessment["summary"]["emergence_state"] == "TRIGGERED"
    reprojection = deepcopy(result.projection)
    row = next(
        candidate
        for candidate in reprojection["rows"]
        if candidate["episode_id"] == result.assessment["episode_id"]
    )
    row["emergence_state"] = {
        "state": "UNESTIMABLE",
        "reason": "SOURCE_NOT_SUPPLIED",
        "source_system": None,
        "source_token": None,
        "source_ref": None,
    }
    _rehash_projection(reprojection)
    forged = _reforge_source_receipt(
        _repointed_projection_digest(deepcopy(result.assessment), reprojection)
    )
    # Both documents are individually valid and receipted; the refusal is the
    # one-read identity between the summary and its bound projection row.
    validate_candidate_state_projection(reprojection)
    validate_native_factual_assessment(forged)
    with pytest.raises(CandidateStateContractError, match="bound projection"):
        b3_owner.NativeFactualAssessmentResult(forged, reprojection)


def test_native_validator_requires_canonical_sha256_receipt_digests(
    refreshed_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    assessment = _native_assessment(_load_snapshot(refreshed_store))
    for field in ("generation_receipt_sha256", "b3_projection_sha256"):
        for malformed in (
            "sha256:NOT-HEX",
            "deadbeef",
            "sha256:" + "g" * 64,
        ):
            forged = deepcopy(assessment)
            forged["provenance"][field] = malformed
            forged["receipt_material"][field] = malformed
            _reforge_source_receipt(forged)
            with pytest.raises(CandidateStateContractError):
                validate_native_factual_assessment(forged)


def test_native_validator_requires_real_selected_known_at_instant(
    refreshed_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    assessment = _native_assessment(_load_snapshot(refreshed_store))
    turn_watch = assessment["provenance"]["turn_watch"]
    assert turn_watch["selected_relation_event_id"] is not None

    malformed = deepcopy(assessment)
    malformed["provenance"]["turn_watch"]["selected_known_at"] = "not-a-clock"
    malformed["receipt_material"]["turn_watch"]["selected_known_at"] = "not-a-clock"
    _reforge_source_receipt(malformed)
    with pytest.raises(CandidateStateContractError, match="selected_known_at"):
        validate_native_factual_assessment(malformed)

    missing = deepcopy(assessment)
    missing["provenance"]["turn_watch"]["selected_known_at"] = None
    missing["receipt_material"]["turn_watch"]["selected_known_at"] = None
    _reforge_source_receipt(missing)
    with pytest.raises(CandidateStateContractError, match="coherent"):
        validate_native_factual_assessment(missing)


def test_native_validator_refuses_selected_clock_without_selection(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    assessment = _native_assessment(_load_snapshot(native_store))
    assert (
        assessment["provenance"]["turn_watch"]["selected_relation_event_id"]
        is None
    )
    forged = deepcopy(assessment)
    forged["provenance"]["turn_watch"]["selected_known_at"] = (
        "2026-11-28T18:00:00Z"
    )
    forged["receipt_material"]["turn_watch"]["selected_known_at"] = (
        "2026-11-28T18:00:00Z"
    )
    _reforge_source_receipt(forged)
    with pytest.raises(CandidateStateContractError, match="coherent"):
        validate_native_factual_assessment(forged)


def test_native_validator_refuses_selection_with_zero_receipted_facts(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    assessment = _native_assessment(_load_snapshot(native_store))
    assert assessment["provenance"]["turn_watch"]["facts"] == 0
    fabricated = "pee:" + "d" * 64
    forged = deepcopy(assessment)
    forged["provenance"]["turn_watch"].update(
        selected_relation_event_id=fabricated,
        selected_known_at="2026-11-28T18:00:00Z",
    )
    forged["receipt_material"]["turn_watch"].update(
        selected_relation_event_id=fabricated,
        selected_known_at="2026-11-28T18:00:00Z",
    )
    forged["summary"].update(
        emergence_state="TRIGGERED",
        emergence_reason=None,
        emergence_source_system="turn_watch",
        emergence_source_token="B1_OBSERVED",
        emergence_source_ref=fabricated,
    )
    _reforge_source_receipt(forged)
    with pytest.raises(CandidateStateContractError, match="zero receipted facts"):
        validate_native_factual_assessment(forged)


def test_native_validator_refuses_emergence_token_without_selection(
    native_store, monkeypatch
):
    _set_assembly_clock(monkeypatch)
    assessment = _native_assessment(_load_snapshot(native_store))
    assert assessment["summary"]["emergence_source_token"] is None
    forged = deepcopy(assessment)
    forged["summary"]["emergence_source_token"] = "B1_FABRICATED"
    _reforge_source_receipt(forged)
    with pytest.raises(CandidateStateContractError, match="emergence"):
        validate_native_factual_assessment(forged)


@pytest.mark.parametrize("payload", [
    None, 7, "prophet.daily_brief_assessment_input/v1", [], {},
    {"schema": "prophet.daily_brief_assessment_input/v1"},
    {"schema": "prophet.daily_brief_assessment_input/v1", "state": "CURRENT"},
])
def test_native_validator_rejects_arbitrary_json(payload):
    with pytest.raises(CandidateStateContractError):
        validate_native_factual_assessment(payload)


def test_native_assessment_normalizes_owner_failures_to_contract_error(native_store, monkeypatch):
    from engine.prophet_candidate_state_sources import CandidateStateSourceError

    snapshot = _load_snapshot(native_store)
    receipt = _candidate_relation(snapshot)["source_receipt"]

    def build():
        return build_native_factual_assessment(
            snapshot, candidate_source_event_id=CANDIDATE_KEY, candidate_source_receipt=receipt)

    # A naive owner assembly clock is typed, never silently localized or leaked
    # as TypeError from the chronology comparison.
    monkeypatch.setattr(b3_owner, "_assembly_now", lambda: datetime(2026, 11, 29, 0, 0, 0))
    with pytest.raises(CandidateStateContractError, match="assembly clock"):
        build()

    # A failing native TURN WATCH index stays inside the typed contract error.
    def broken_index(snap):
        raise CandidateStateSourceError("index refused")

    monkeypatch.setattr(b3_owner, "index_turn_watch_events", broken_index)
    monkeypatch.setattr(b3_owner, "_assembly_now", lambda: ASSEMBLY_NOW)
    with pytest.raises(CandidateStateContractError, match="TURN WATCH"):
        build()

    # A non-canonical snapshot ledger is typed, never leaked as
    # EpisodeContractError from the disk-validation compare.
    generation = snapshot.generation
    non_json = CandidateEpisodeStoreSnapshot(
        snapshot.generation_id,
        ValidatedCandidateEpisodeGeneration(
            path=generation.path,
            events=({"bad": object()},) + generation.events[1:],
            suppressions=generation.suppressions,
            episodes=generation.episodes,
            receipt=generation.receipt,
        ),
    )
    with pytest.raises(CandidateStateContractError, match="canonical native B1"):
        build_native_factual_assessment(
            non_json, candidate_source_event_id=CANDIDATE_KEY, candidate_source_receipt=receipt)


# Parent copy-boundary race: schema-valid copies must retain their shared binding.
def test_verified_pair_checks_cross_binding_after_copy(native_store, monkeypatch):
    owner=b3_owner
    _set_assembly_clock(monkeypatch)
    snapshot=_load_snapshot(native_store)
    result=owner.build_native_factual_assessment_result(snapshot,
        candidate_source_event_id=CANDIDATE_KEY,
        candidate_source_receipt=_candidate_relation(snapshot)["source_receipt"])
    real_copy=owner.deepcopy
    def racing_copy(value, *args, **kwargs):
        copied=real_copy(value, *args, **kwargs)
        if value is result.assessment:
            result.projection["market_session"]="2026-11-30"
            _rehash_projection(result.projection)
            owner.validate_candidate_state_projection(result.projection)
        return copied
    monkeypatch.setattr(owner,"deepcopy",racing_copy)
    with pytest.raises(owner.CandidateStateContractError):
        result.verified_pair()
