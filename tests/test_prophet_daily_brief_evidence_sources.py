"""Hermetic native tests for the DailyBrief factual evidence sources adapter.

Every test builds a real temporary B1 store through the canonical nightly
writer, binds the store's own candidate source key/digest, and reads the
unchanged Earnings D5 owner through module-level patches of the lawful owner
seams (the reader module functions, the adapter clock, the reference byte
read).  The point-in-time reader proof goes further: a fixed in-memory
transport bound at the reader module's existing ``_fetch_bytes`` seam serves a
real canonical marker, generation manifests and predecessor-chain hashes, so
the UNCHANGED ``find_current_event_id_for_company`` /
``read_event_source_revisions`` execute for real.  No test touches the
protected network, shared data, or any owner bytes outside ``tmp_path``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import prophet_daily_brief_evidence_sources as evidence_sources
from engine.neuralweb import company_intelligence_reader as owner_reader
from engine.neuralweb.company_intelligence_reader import (
    CompanyIntelligenceReadError,
    WorkspaceChainIntegrityError,
)
from engine.prophet_daily_brief import (
    _EVIDENCE_SCHEMA,
    _EVIDENCE_STATES,
    _bound_record,
    _reject_forbidden,
)
from engine.prophet_lab.intelligence_vector import (
    build_earnings_intelligence_vector,
    validate_intelligence_vector,
)
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot,
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from lib.dataos.identity import IssuerMaster
from scripts import reconcile_us_candidate_episodes as writer


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "us_candidate_episode" / "intake"
CANDIDATE_SESSION = "2026-11-27"
SAME_SESSION_CUT = "2026-11-27T18:00:00Z"
EVENT_ID = "evt_cik0000320193_results_1"
WORKSPACE_GENERATION = "a" * 24
READ_NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)
# Real canonical shapes for the fixture transport served at the reader's
# ``_fetch_bytes`` seam: a canonical event id, and a two-generation
# predecessor chain whose manifests carry the exact workspace receipts.
REAL_EVENT_ID = "evt_cik0000320193_2026q3_results"
REAL_BASE_URL = "https://fixture.test/company_intelligence"
REAL_ROOT_GENERATION = "1" * 24
REAL_CURRENT_GENERATION = "2" * 24


def _canonical(value: object) -> str:
    return canonical_json(value)


def _workspace(
    *,
    source_available_at: str,
    observed_at: str,
    generated_at: str,
    generation_id: str = WORKSPACE_GENERATION,
    value: float = 2468.0,
) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": EVENT_ID,
        "generation_id": generation_id,
        "issuer": {"company_id": "cik:0000320193", "display_name": "Apple Inc."},
        "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-09-27"},
        "lifecycle": {
            "state": "complete",
            "source_available_at": source_available_at,
            "observed_at": observed_at,
        },
        "generated_at": generated_at,
        "facts": [{
            "schema": "event_fact.v1", "metric": "revenue", "value": value,
            "unit": "USD", "period": "2026Q3", "basis": "reported",
            "source_span": {"document_id": "doc:issuer-release:1"},
        }],
        "deltas": [{
            "schema": "metric_delta.v1", "metric": "revenue",
            "current": {"value": value, "unit": "USD", "basis": "reported"},
            "prior": {"state": "absent", "reason": "not_available"},
            "consensus": {"state": "absent", "reason": "consensus_unlicensed"},
            "basis_match": False,
        }],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release", "document_id": "doc:issuer-release:1",
            "source_sha256": "c" * 64, "receipt_state": "byte_replayed",
        }],
        "warnings": [],
    }


def _revisions(*workspaces: dict) -> list[dict]:
    receipts = []
    for workspace in workspaces:
        encoded = _canonical(workspace).encode("utf-8")
        receipts.append({
            "generation_id": workspace["generation_id"],
            "source_sha256": workspace["sources"][0]["source_sha256"],
            "source_available_at": workspace["lifecycle"]["source_available_at"],
            "observed_at": workspace["lifecycle"]["observed_at"],
            "lifecycle_state": "complete",
            "form": "8-K",
            "workspace_receipt": {"sha256": sha256(encoded).hexdigest(), "bytes": len(encoded)},
            "workspace": workspace,
        })
    return receipts


def _admissible_revisions() -> list[dict]:
    return _revisions(_workspace(
        source_available_at="2026-11-27T17:00:00Z",
        observed_at="2026-11-27T17:05:00Z",
        generated_at="2026-11-27T17:10:00Z",
    ))


def _patch_reader(monkeypatch, *, revisions=None, event_id=EVENT_ID, find_error=None,
                  read_error=None) -> None:
    def find(company_id):
        if find_error is not None:
            raise find_error
        return event_id

    def read(event_id):
        if read_error is not None:
            raise read_error
        return list(revisions or [])

    monkeypatch.setattr(owner_reader, "find_current_event_id_for_company", find)
    monkeypatch.setattr(owner_reader, "read_event_source_revisions", read)


def _patch_clock(monkeypatch, when: datetime = READ_NOW) -> None:
    monkeypatch.setattr(evidence_sources, "_read_completed_at", lambda: when)


def _security_rows() -> list[dict]:
    rows = json.loads((FIXTURE_ROOT / "security_master.json").read_text())
    for row in rows:
        row["issuer_cik"] = "0000320193"
    return rows


def _turn_document() -> dict:
    return json.loads((FIXTURE_ROOT / "turn_watch.json").read_text())


def _write_turn(data: Path, document: dict) -> None:
    material = {key: value for key, value in document.items() if key != "content_sha256"}
    document["content_sha256"] = sha256(_canonical(material).encode("utf-8")).hexdigest()
    turn = data / "us_prophet_rank" / "episode_inputs" / "turn_watch" / f"{CANDIDATE_SESSION}.json"
    turn.parent.mkdir(parents=True, exist_ok=True)
    turn.write_text(_canonical(document))


def _build_store(
    tmp_path: Path, monkeypatch, *, candidate_rows=(), turn_document=None,
    recorded_at: str = "2026-11-27T18:05:00Z", with_reference: bool = True,
) -> Path:
    repo_root = tmp_path / "repo"
    data = repo_root / "data"
    reference = data / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    if with_reference:
        pd.DataFrame(_security_rows()).to_parquet(reference / "security_master.parquet", index=False)
        pd.DataFrame(json.loads((FIXTURE_ROOT / "vendor_aliases.json").read_text())).to_parquet(
            reference / "vendor_aliases.parquet", index=False)
    _write_turn(data, dict(turn_document or _turn_document()))
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    # Real writer flow, two nightly runs: the TURN WATCH run opens the episode;
    # the candidates run then attaches the candidate source relation to it.
    writer.reconcile(repo_root=repo_root, nightly=True, replay=False,
                     recorded_at=recorded_at, correction_path=None)
    if candidate_rows:
        candidates = data / "us_prophet_rank" / "candidates"
        candidates.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(candidate_rows).to_parquet(candidates / "2026-11.parquet", index=False)
        writer.reconcile(repo_root=repo_root, nightly=True, replay=False,
                         recorded_at="2026-11-27T18:10:00Z", correction_path=None)
    return repo_root


def _snapshot(repo_root: Path) -> CandidateEpisodeStoreSnapshot:
    return load_candidate_episode_store_snapshot(
        repo_root / "data" / "us_prophet_rank" / "episodes",
    )


def _candidate_binding(snapshot: CandidateEpisodeStoreSnapshot) -> tuple[str, str]:
    for raw in snapshot.generation.events:
        if (raw.get("source_system") == "candidate"
                and raw.get("event_type") in {"OPENED", "OBSERVED"}):
            return str(raw["source_event_id"]), str(raw["source_receipt"])
    raise AssertionError("fixture store carries no candidate relation")


def _candidate_row() -> list[dict]:
    return [{"stamp_date": CANDIDATE_SESSION, "ticker": "ALFA",
             "board_definition": "us_prophet_v2", "tier": "curated"}]


def _positive(monkeypatch, tmp_path: Path, *, turn_document=None, when=READ_NOW):
    repo_root = _build_store(
        tmp_path, monkeypatch, candidate_rows=_candidate_row(),
        turn_document=turn_document,
    )
    _patch_clock(monkeypatch, when)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    return repo_root, snapshot, key, receipt


def _retract(repo_root: Path, monkeypatch, *, target_event_id: str, episode_id: str,
             recorded_at: str = "2026-11-27T18:10:00Z") -> None:
    command = {
        "event_type": "RETRACTED",
        "episode_id": episode_id,
        "source_system": "daily_brief_review",
        "source_schema": "daily_brief.retraction/v1",
        "source_event_id": f"daily_brief_review:{target_event_id}",
        "occurred_at": recorded_at,
        "known_at": recorded_at,
        "source_receipt": "sha256:" + "b" * 64,
        "correction_of": target_event_id,
        "payload": {"reason": "daily brief evidence review retraction"},
    }
    correction_path = repo_root / "corrections.jsonl"
    correction_path.write_text(_canonical(command) + "\n")
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    writer.reconcile(repo_root=repo_root, nightly=True, replay=False,
                     recorded_at=recorded_at, correction_path=correction_path)


def _relation_id(snapshot: CandidateEpisodeStoreSnapshot, event_type: str) -> str:
    for raw in snapshot.generation.events:
        if raw.get("event_type") == event_type:
            return str(raw["event_id"])
    raise AssertionError(f"fixture store has no {event_type} relation")


def _read(repo_root, snapshot, key, receipt):
    return evidence_sources.read_native_daily_brief_evidence(
        repo_root, snapshot=snapshot,
        candidate_source_event_id=key, candidate_source_receipt=receipt,
    )


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def test_positive_binding_is_partial_with_literal_observation_and_whole_input_hash(
    tmp_path, monkeypatch,
):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    result = _read(repo_root, snapshot, key, receipt)

    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "PARTIAL"
    evidence = result["evidence_input"]
    assert evidence["schema"] == "prophet.daily_brief_evidence_input/v1"
    assert evidence["state"] == "PARTIAL"
    assert evidence["owner_ref"] == evidence_sources.OWNER_REF
    assert evidence["security_id"] == "SEC:US-XNAS-ALFA"
    assert evidence["candidate_generation_id"] == snapshot.generation_id
    assert evidence["market_session"] == CANDIDATE_SESSION
    # The fact asof is the genuine owner observed clock, not the fresh adapter
    # clock, and the original opened cut is not restamped by the read.
    assert evidence["asof"] == "2026-11-27T17:05:00Z"
    assert evidence["fact_asof_basis"] == "event_workspace.lifecycle.observed_at"
    assert evidence["read_completed_at"] == "2026-12-01T00:00:00Z"

    # Literal observation binding against an independent unchanged-owner build.
    episode = snapshot.generation.episodes[0]
    opened_known_at = next(
        str(raw["known_at"]) for raw in snapshot.generation.events
        if raw.get("event_type") == "OPENED"
    )
    vector = build_earnings_intelligence_vector(
        episode=dict(episode),
        episode_generation_id=snapshot.generation_id,
        episode_known_at=opened_known_at,
        issuer_master=IssuerMaster.from_records(pd.read_parquet(
            repo_root / "data" / "reference" / "security_master.parquet",
        ).to_dict("records")),
        find_event_id=lambda company_id: EVENT_ID,
        read_revisions=lambda event_id: _admissible_revisions(),
    )
    assert vector["assembly_receipt"]["assembled_at"] is None
    supported = evidence["summary"]["supported"]
    assert len(supported) == 1
    row = supported[0]
    assert row["native_metric_id"] == "fact:revenue"
    assert row["value_state"] == "PRESENT"
    assert row["value"] == 2468.0
    assert row["units"] == "USD"
    assert row["value_usd"] == 2468.0
    assert row["observation_ref"] == vector["evidence_families"][0]["observations"][0]["observation_id"]
    assert evidence["summary"]["source_ref_ids"] == sorted(
        ref["source_ref_id"] for ref in vector["evidence_families"][0]["source_refs"]
    )

    provenance = evidence["provenance"]
    assert provenance["owner_projection_id"] == vector["projection_id"]
    assert provenance["owner_subject_event_id"] == EVENT_ID
    assert provenance["earnings_company_id"] == "cik:0000320193"
    assert provenance["owner_assembly_assembled_at"] is None
    assert provenance["episode_original_opened_known_at"] == opened_known_at
    assert provenance["episode_opened_at"] == SAME_SESSION_CUT
    assert provenance["chosen_workspace_receipt"]["bytes"] > 0
    assert len(provenance["owner_lanes"]) == 3
    assert provenance["owner_vector_errors"] == []
    # The whole-input receipt covers the complete closed envelope minus receipt.
    material = {k: v for k, v in evidence.items() if k != "source_receipt"}
    assert evidence["source_receipt"] == "sha256:" + sha256(
        _canonical(material).encode("utf-8"),
    ).hexdigest()
    result_material = {k: v for k, v in result.items() if k != "source_receipt"}
    assert result["source_receipt"] == "sha256:" + sha256(
        _canonical(result_material).encode("utf-8"),
    ).hexdigest()


def test_standing_scope_reasons_stay_visible_and_partial_is_the_ceiling(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    result = _read(repo_root, snapshot, key, receipt)
    assert set(result["reasons"]) == {
        "SCOPE_CURRENT_GENERATION_EVENT_DISCOVERY_ONLY",
        "SCOPE_HISTORICAL_EVENT_SET_INCOMPLETE",
        "SCOPE_IDENTITY_CURRENT_REGISTRANT_ONLY",
        "STATE_CAPPED_PARTIAL_BY_CONTRACT",
    }
    provenance = result["evidence_input"]["provenance"]
    assert provenance["owner_event_discovery_scope"] == "CURRENT_GENERATION_ONLY"
    assert provenance["owner_historical_event_set_reconstruction"] is False
    assert provenance["owner_identity_resolution_scope"] == "CURRENT_REGISTRANT_ONLY"


def test_binding_mismatches_refuse_typed_against_the_actual_store(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    wrong_receipt = "sha256:" + "0" * 64
    wrong_key = "candidate:2099-01-01:NOPE:us_prophet_v2"
    cases = [
        (key, wrong_receipt, "B1_RELATION_RECEIPT_MISMATCH"),
        (wrong_key, receipt, "B1_RELATION_NOT_FOUND"),
        ("candidate:2026-13-40:ALFA:us_prophet_v2", receipt, "B1_BINDING_KEY_MALFORMED"),
        ("turn_watch:2026-11-27:x", receipt, "B1_BINDING_KEY_MALFORMED"),
        ("candidate:2026-11-27:", receipt, "B1_BINDING_KEY_MALFORMED"),
        (key, "sha256:nothex", "B1_BINDING_RECEIPT_MALFORMED"),
        (key, receipt[:-1], "B1_BINDING_RECEIPT_MALFORMED"),
        (None, receipt, "B1_BINDING_KEY_MALFORMED"),
        (key, None, "B1_BINDING_RECEIPT_MALFORMED"),
    ]
    for candidate_key, candidate_receipt, reason in cases:
        result = _read(repo_root, snapshot, candidate_key, candidate_receipt)
        evidence_sources.validate_daily_brief_evidence_result(result)
        assert result["state"] == "UNAVAILABLE"
        assert result["evidence_input"] is None
        assert result["reasons"] == [reason]


def test_forged_snapshots_cannot_bypass_disk_revalidation(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    events = list(snapshot.generation.events)
    mutated = dict(events[-1])
    mutated["known_at"] = "2099-01-01T00:00:00Z"
    tampered = CandidateEpisodeStoreSnapshot(
        generation_id=snapshot.generation_id,
        generation=type(snapshot.generation)(
            path=snapshot.generation.path,
            events=(*events[:-1], mutated),
            suppressions=snapshot.generation.suppressions,
            episodes=snapshot.generation.episodes,
            receipt=snapshot.generation.receipt,
        ),
    )
    result = _read(repo_root, tampered, key, receipt)
    assert result["reasons"] == ["B1_SNAPSHOT_REVALIDATION_FAILED"]

    assert _read(repo_root, {"generation_id": snapshot.generation_id}, key, receipt)[
        "reasons"
    ] == ["B1_SNAPSHOT_INVALID"]
    assert _read(repo_root, None, key, receipt)["reasons"] == ["B1_SNAPSHOT_INVALID"]
    relabeled = CandidateEpisodeStoreSnapshot(
        generation_id="peg:" + "f" * 64, generation=snapshot.generation,
    )
    assert _read(repo_root, relabeled, key, receipt)[
        "reasons"
    ] == ["B1_SNAPSHOT_REVALIDATION_FAILED"]


def test_suppressed_candidate_source_key_refuses(tmp_path, monkeypatch):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=[
        {"stamp_date": CANDIDATE_SESSION, "ticker": "UNKNOWN",
         "board_definition": "us_prophet_v2"},
    ])
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())
    snapshot = _snapshot(repo_root)
    suppressed = next(
        row for row in snapshot.generation.suppressions
        if row.get("source_system") == "candidate"
    )
    result = _read(
        repo_root, snapshot,
        str(suppressed["source_event_id"]), str(suppressed["source_receipt"]),
    )
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["reasons"] == ["B1_RELATION_SUPPRESSED"]


def test_retracted_candidate_relation_refuses(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    observed_id = _relation_id(snapshot, "OBSERVED")
    episode_id = str(snapshot.generation.episodes[0]["episode_id"])
    _retract(repo_root, monkeypatch, target_event_id=observed_id, episode_id=episode_id)
    result = _read(repo_root, _snapshot(repo_root), key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["reasons"] == ["B1_RELATION_RETRACTED"]


def test_retracted_opened_episode_refuses_as_episode_not_found(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    opened_id = _relation_id(snapshot, "OPENED")
    episode_id = str(snapshot.generation.episodes[0]["episode_id"])
    _retract(repo_root, monkeypatch, target_event_id=opened_id, episode_id=episode_id)
    result = _read(repo_root, _snapshot(repo_root), key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["reasons"] == ["B1_EPISODE_NOT_FOUND"]


def test_issuer_master_read_failures_refuse_typed(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    reference = repo_root / "data" / "reference" / "security_master.parquet"

    reference.unlink()
    assert _read(repo_root, snapshot, key, receipt)["reasons"] == ["ISSUER_MASTER_UNREADABLE"]

    reference.write_bytes(b"not a parquet")
    assert _read(repo_root, snapshot, key, receipt)["reasons"] == ["ISSUER_MASTER_UNREADABLE"]

    buffer = io.BytesIO()
    pd.DataFrame(_security_rows()).to_parquet(buffer, index=False)
    real_bytes = buffer.getvalue()
    reference.write_bytes(real_bytes)
    calls = iter([real_bytes, real_bytes + b"tail"])
    monkeypatch.setattr(evidence_sources, "_read_reference_bytes", lambda path: next(calls))
    assert _read(repo_root, snapshot, key, receipt)[
        "reasons"
    ] == ["ISSUER_MASTER_CHANGED_DURING_READ"]


def test_fixed_reference_path_is_the_only_issuer_authority(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    reference = repo_root / "data" / "reference" / "security_master.parquet"
    rows = _security_rows()
    for row in rows:
        row["issuer_cik"] = None
    reference.write_bytes(pd.DataFrame(rows).to_parquet(index=False))
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["reasons"] == ["IDENTITY_UNRESOLVED"]

    with pytest.raises(TypeError):
        evidence_sources.read_native_daily_brief_evidence(
            repo_root, snapshot=snapshot,
            candidate_source_event_id=key, candidate_source_receipt=receipt,
            issuer_master=IssuerMaster.from_records(_security_rows()),
        )
    with pytest.raises(TypeError):
        evidence_sources.read_native_daily_brief_evidence(
            repo_root, snapshot=snapshot,
            candidate_source_event_id=key, candidate_source_receipt=receipt,
            reference_path=reference,
        )


@pytest.mark.parametrize(
    ("patch", "reason"),
    [
        ({"event_id": None}, "OWNER_CURRENT_EVENT_NOT_PUBLISHED"),
        ({"read_error": WorkspaceChainIntegrityError("chain broken")},
         "OWNER_READ_CHAIN_INTEGRITY"),
        ({"read_error": CompanyIntelligenceReadError("source 403")},
         "OWNER_READ_SOURCE_FETCH_FAILED"),
        ({"revisions": []}, "OWNER_REVISION_HISTORY_EMPTY"),
        ({"revisions": None}, None),  # replaced below (future clocks)
    ],
)
def test_owner_read_outcomes_are_typed(tmp_path, monkeypatch, patch, reason):
    if reason is None:  # future owner clocks fail closed after the decision cut
        patch = {"revisions": _revisions(_workspace(
            source_available_at="2026-12-31T20:00:00Z",
            observed_at="2026-12-31T20:05:00Z",
            generated_at="2026-12-31T20:10:00Z",
        ))}
        reason = "OWNER_EVIDENCE_AFTER_DECISION_CUT"
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, **patch)
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["evidence_input"] is None
    assert result["reasons"] == [reason]


def test_missing_owner_clocks_and_clock_ties_are_typed(tmp_path, monkeypatch):
    def _store():
        return _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())

    def _bind(repo_root):
        _patch_clock(monkeypatch)
        snapshot = _snapshot(repo_root)
        key, receipt = _candidate_binding(snapshot)
        return snapshot, key, receipt

    repo_root = _store()
    _patch_reader(monkeypatch, revisions=_revisions(_workspace(
        source_available_at=None, observed_at=None, generated_at=None,
    )))
    snapshot, key, receipt = _bind(repo_root)
    assert _read(repo_root, snapshot, key, receipt)["reasons"] == ["OWNER_MISSING_DECISION_CLOCK"]

    repo_root = _store()
    tied = [
        _workspace(
            source_available_at="2026-11-27T17:00:00Z",
            observed_at="2026-11-27T17:05:00Z",
            generated_at="2026-11-27T17:10:00Z",
            generation_id=generation,
        )
        for generation in ("a" * 24, "b" * 24)
    ]
    _patch_reader(monkeypatch, revisions=_revisions(*tied))
    snapshot, key, receipt = _bind(repo_root)
    assert _read(repo_root, snapshot, key, receipt)["reasons"] == ["OWNER_UNRESOLVED_CLOCK_TIE"]


def test_admissible_packet_without_allowlisted_lanes_stays_partial_absence(
    tmp_path, monkeypatch,
):
    """An admissible owner packet that projects no allowlisted lane stays a
    typed absence with UNKNOWN coverage — never neutral, never negative."""
    workspace = _workspace(
        source_available_at="2026-11-27T17:00:00Z",
        observed_at="2026-11-27T17:05:00Z",
        generated_at="2026-11-27T17:10:00Z",
    )
    workspace["facts"] = []
    workspace["deltas"] = []
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, revisions=_revisions(workspace))
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    evidence = result["evidence_input"]
    assert result["state"] == "PARTIAL"
    assert evidence["summary"]["supported"] == []
    assert evidence["summary"]["source_ref_ids"] == []
    assert [row["absence_reasons"] for row in evidence["summary"]["absent"]] == [["UNKNOWN"]]
    assert evidence["coverage"]["state"] == "UNKNOWN"
    assert evidence["coverage"]["basis"] == "exact_source_lineage_unavailable"


def test_future_clock_fails_closed_and_fresh_read_never_renews_fact_asof(tmp_path, monkeypatch):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())

    _patch_clock(monkeypatch, datetime(2026, 1, 1, tzinfo=timezone.utc))
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["reasons"] == ["OWNER_EVIDENCE_CLOCK_FUTURE"]
    assert result["evidence_input"] is None

    _patch_clock(monkeypatch, READ_NOW)
    result = _read(repo_root, snapshot, key, receipt)
    evidence = result["evidence_input"]
    assert evidence["asof"] == "2026-11-27T17:05:00Z"
    assert evidence["read_completed_at"] == "2026-12-01T00:00:00Z"
    assert evidence["asof"] < evidence["read_completed_at"]
    assert evidence["provenance"]["owner_assembly_assembled_at"] is None


def test_cross_session_source_tuple_stays_visible_and_capped(tmp_path, monkeypatch):
    document = _turn_document()
    document["rows"][0]["triggers"]["dot_1d"]["last_date"] = "2026-11-25"
    document["rows"][0]["reset"]["reset_low_date"] = "2026-11-24"
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row(),
                             turn_document=document)
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, revisions=_revisions(_workspace(
        source_available_at="2026-11-25T20:00:00Z",
        observed_at="2026-11-25T20:05:00Z",
        generated_at="2026-11-25T20:10:00Z",
    )))
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    evidence = result["evidence_input"]
    assert result["state"] == "PARTIAL"
    assert evidence["market_session"] == CANDIDATE_SESSION
    assert evidence["provenance"]["episode_opened_session"] == "2026-11-25"
    assert evidence["provenance"]["episode_opened_at"] == "2026-11-25T21:00:00Z"
    assert evidence["asof"] == "2026-11-25T20:05:00Z"
    assert "SOURCE_TUPLE_SESSION_DIFFERS_FROM_OPENED_SESSION" in result["reasons"]
    assert result["evidence_input"]["coverage"]["notes"] == sorted(set(result["reasons"]))


def test_adapter_call_mutates_no_source_owner_bytes(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    before = _tree_digest(repo_root)
    result = _read(repo_root, snapshot, key, receipt)
    assert result["state"] == "PARTIAL"
    assert _tree_digest(repo_root) == before


def test_no_forbidden_authority_keys_anywhere_including_the_raw_vector(
    tmp_path, monkeypatch,
):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    episode = snapshot.generation.episodes[0]
    opened_known_at = next(
        str(raw["known_at"]) for raw in snapshot.generation.events
        if raw.get("event_type") == "OPENED"
    )
    vector = build_earnings_intelligence_vector(
        episode=dict(episode),
        episode_generation_id=snapshot.generation_id,
        episode_known_at=opened_known_at,
        issuer_master=IssuerMaster.from_records(pd.read_parquet(
            repo_root / "data" / "reference" / "security_master.parquet",
        ).to_dict("records")),
        find_event_id=lambda company_id: EVENT_ID,
        read_revisions=lambda event_id: _admissible_revisions(),
    )
    _reject_forbidden(vector, path="vector")  # the raw owner vector is leak-free

    result = _read(repo_root, snapshot, key, receipt)
    _reject_forbidden(result, path="result")
    _reject_forbidden(result["evidence_input"], path="evidence_input")


def test_dailybrief_compositor_accepts_the_evidence_input_as_a_bound_record(
    tmp_path, monkeypatch,
):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    result = _read(repo_root, snapshot, key, receipt)
    evidence = result["evidence_input"]
    bound = _bound_record(evidence, _EVIDENCE_SCHEMA, "evidence")
    assert bound is not None
    assert bound["state"] in _EVIDENCE_STATES
    assert bound["security_id"] == "SEC:US-XNAS-ALFA"
    assert bound["episode_id"] == snapshot.generation.episodes[0]["episode_id"]
    assert bound["candidate_generation_id"] == snapshot.generation_id
    assert bound["market_session"] == CANDIDATE_SESSION
    assert isinstance(bound["coverage"], dict)


def test_result_envelope_tamper_and_pair_coherence_is_refused(tmp_path, monkeypatch):
    repo_root, snapshot, key, receipt = _positive(monkeypatch, tmp_path)
    result = _read(repo_root, snapshot, key, receipt)

    def _refused(mutated):
        with pytest.raises(evidence_sources.DailyBriefEvidenceContractError):
            evidence_sources.validate_daily_brief_evidence_result(mutated)

    forged = json.loads(_canonical(result))
    forged["state"] = "CURRENT"
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["state"] = "AVAILABLE"
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["reasons"] = sorted(
        set(forged["reasons"]) - {"SCOPE_HISTORICAL_EVENT_SET_INCOMPLETE"}
    )
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["reasons"] = ["NOT_A_REAL_REASON"] + forged["reasons"]
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["evidence_input"] = None
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["evidence_input"]["state"] = "CURRENT"
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["evidence_input"]["summary"]["supported"][0]["value"] = 1.0
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["evidence_input"]["asof"] = "2027-01-01T00:00:00Z"
    _refused(forged)
    forged = json.loads(_canonical(result))
    forged["source_receipt"] = "sha256:" + "9" * 64
    _refused(forged)

    unavailable = json.loads(_canonical(result))
    unavailable["state"] = "UNAVAILABLE"
    unavailable["evidence_input"] = None
    unavailable["reasons"] = ["B1_RELATION_NOT_FOUND"]
    unavailable["source_receipt"] = evidence_sources._receipt_of(unavailable)
    evidence_sources.validate_daily_brief_evidence_result(unavailable)


def _generation_manifest_bytes(
    generation_id: str, workspace: dict, *, schema: str,
    previous: tuple[str, str] | None = None,
) -> bytes:
    body: dict = {
        "schema": schema,
        "generation_id": generation_id,
        "files": {},
    }
    encoded = _canonical(workspace).encode("utf-8")
    body["files"][f"workspaces/{REAL_EVENT_ID}.json"] = {
        "sha256": sha256(encoded).hexdigest(),
        "bytes": len(encoded),
    }
    if previous is not None:
        body["previous_generation_id"] = previous[0]
        body["previous_manifest_sha256"] = previous[1]
    return _canonical(body).encode("utf-8")


def _real_workspace(
    *, generation_id: str, value: float, source_tag: str,
    source_available_at: str, observed_at: str, generated_at: str,
) -> dict:
    workspace = _workspace(
        source_available_at=source_available_at,
        observed_at=observed_at,
        generated_at=generated_at,
        generation_id=generation_id,
        value=value,
    )
    workspace["event_id"] = REAL_EVENT_ID
    workspace["sources"][0]["source_sha256"] = source_tag * 64
    return workspace


def _fixture_transport(monkeypatch) -> dict[str, bytes]:
    """Bind a fixed in-memory transport at the reader module's existing
    ``_fetch_bytes`` seam and serve a real canonical marker plus a
    two-generation predecessor chain (exact manifest bytes, exact workspace
    receipt hashes).  The chain reads themselves stay unchanged; no production
    callback is reachable and real network egress is forbidden outright."""
    root_workspace = _real_workspace(
        generation_id=REAL_ROOT_GENERATION, value=1234.0, source_tag="d",
        source_available_at="2026-11-20T17:00:00Z",
        observed_at="2026-11-20T17:05:00Z",
        generated_at="2026-11-20T17:10:00Z",
    )
    current_workspace = _real_workspace(
        generation_id=REAL_CURRENT_GENERATION, value=2468.0, source_tag="c",
        source_available_at="2026-11-27T17:00:00Z",
        observed_at="2026-11-27T17:05:00Z",
        generated_at="2026-11-27T17:10:00Z",
    )
    root_manifest = _generation_manifest_bytes(
        REAL_ROOT_GENERATION, root_workspace, schema="event_workspace_manifest.v1",
    )
    current_manifest = _generation_manifest_bytes(
        REAL_CURRENT_GENERATION, current_workspace,
        schema="event_workspace_manifest.v2",
        previous=(REAL_ROOT_GENERATION, sha256(root_manifest).hexdigest()),
    )
    objects = {
        owner_reader._workspace_object_url(REAL_BASE_URL, "manifest.json"): _canonical(
            {"generation_id": REAL_CURRENT_GENERATION},
        ).encode("utf-8"),
        owner_reader._workspace_object_url(
            REAL_BASE_URL, f"generations/{REAL_CURRENT_GENERATION}/manifest.json",
        ): current_manifest,
        owner_reader._workspace_object_url(
            REAL_BASE_URL, f"generations/{REAL_ROOT_GENERATION}/manifest.json",
        ): root_manifest,
        owner_reader._workspace_object_url(
            REAL_BASE_URL,
            f"generations/{REAL_CURRENT_GENERATION}/workspaces/{REAL_EVENT_ID}.json",
        ): _canonical(current_workspace).encode("utf-8"),
        owner_reader._workspace_object_url(
            REAL_BASE_URL,
            f"generations/{REAL_ROOT_GENERATION}/workspaces/{REAL_EVENT_ID}.json",
        ): _canonical(root_workspace).encode("utf-8"),
    }

    def forbidden_network(*args, **kwargs):
        raise AssertionError("fixture transport must never touch the real network")

    def fetch(url, *, limit, allow_404=False):
        body = objects.get(url)
        if body is None:
            if allow_404:
                return None
            raise owner_reader.CompanyIntelligenceReadError(
                f"fixture transport miss: {url}"
            )
        if len(body) > limit:
            raise owner_reader.CompanyIntelligenceReadError(
                "fixture transport size bound exceeded"
            )
        return body

    monkeypatch.setenv("COMPANY_INTELLIGENCE_R2_BASE_URL", REAL_BASE_URL)
    monkeypatch.setattr(owner_reader.requests, "get", forbidden_network)
    monkeypatch.setattr(owner_reader, "_fetch_bytes", fetch)
    return objects


def test_completion_clock_is_captured_after_the_actual_owner_read(tmp_path, monkeypatch):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())
    finished = {"value": False}

    def read(event_id):
        finished["value"] = True
        return list(_admissible_revisions())

    monkeypatch.setattr(owner_reader, "read_event_source_revisions", read)

    def completion():
        assert finished["value"], "completion clock captured before the native owner read"
        return READ_NOW

    monkeypatch.setattr(evidence_sources, "_read_completed_at", completion)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "PARTIAL"
    assert result["evidence_input"]["read_completed_at"] == "2026-12-01T00:00:00Z"


def test_issuer_change_during_the_actual_owner_read_refuses(tmp_path, monkeypatch):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    reference = repo_root / "data" / "reference" / "security_master.parquet"

    def read(event_id):
        reference.write_bytes(b"changed issuer bytes during the owner read")
        return list(_admissible_revisions())

    monkeypatch.setattr(owner_reader, "read_event_source_revisions", read)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["evidence_input"] is None
    assert result["reasons"] == ["ISSUER_MASTER_CHANGED_DURING_READ"]


def test_b1_head_change_during_the_actual_owner_read_refuses(tmp_path, monkeypatch):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    _patch_reader(monkeypatch, revisions=_admissible_revisions())
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    victim = sorted(
        path for path in snapshot.generation.path.rglob("*") if path.is_file()
    )[0]
    original = victim.read_bytes()

    def read(event_id):
        victim.write_bytes(original + b" ")
        return list(_admissible_revisions())

    monkeypatch.setattr(owner_reader, "read_event_source_revisions", read)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["evidence_input"] is None
    assert result["reasons"] == ["B1_SNAPSHOT_REVALIDATION_FAILED"]


def test_real_owner_reader_transport_runs_the_unchanged_chain_reads(
    tmp_path, monkeypatch,
):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    _fixture_transport(monkeypatch)
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "PARTIAL"

    # The unchanged owner discovery and revision walk over the same transport:
    # canonical event ids parsed from the real generation manifest, verified
    # manifest receipts, and an oldest-first two-generation chain.
    assert owner_reader.find_current_event_id_for_company("cik:0000320193") == REAL_EVENT_ID
    revisions = owner_reader.read_event_source_revisions(REAL_EVENT_ID)
    assert [row["generation_id"] for row in revisions] == [
        REAL_ROOT_GENERATION, REAL_CURRENT_GENERATION,
    ]
    assert all(
        row["workspace_receipt"]["sha256"]
        == sha256(_canonical(row["workspace"]).encode("utf-8")).hexdigest()
        for row in revisions
    )

    # The adapter evidence is the canonical builder/validator over the SAME
    # unchanged owner reads — no parallel stub path minted the projection.
    episode = snapshot.generation.episodes[0]
    opened_known_at = next(
        str(raw["known_at"]) for raw in snapshot.generation.events
        if raw.get("event_type") == "OPENED"
    )
    vector = build_earnings_intelligence_vector(
        episode=dict(episode),
        episode_generation_id=snapshot.generation_id,
        episode_known_at=opened_known_at,
        issuer_master=IssuerMaster.from_records(pd.read_parquet(
            repo_root / "data" / "reference" / "security_master.parquet",
        ).to_dict("records")),
        find_event_id=owner_reader.find_current_event_id_for_company,
        read_revisions=owner_reader.read_event_source_revisions,
    )
    validate_intelligence_vector(vector)
    evidence = result["evidence_input"]
    assert evidence["provenance"]["owner_projection_id"] == vector["projection_id"]
    assert evidence["provenance"]["owner_subject_event_id"] == REAL_EVENT_ID
    assert evidence["provenance"]["chosen_revision_generation_id"] == REAL_CURRENT_GENERATION
    assert evidence["provenance"]["chosen_workspace_receipt"] == dict(
        revisions[-1]["workspace_receipt"]
    )
    supported = evidence["summary"]["supported"]
    assert [row["value"] for row in supported] == [2468.0]
    assert [row["units"] for row in supported] == ["USD"]
    assert evidence["summary"]["decision_admissibility"] == "ADMISSIBLE"
    assert evidence["summary"]["source_ref_ids"] == sorted(
        ref["source_ref_id"] for ref in vector["evidence_families"][0]["source_refs"]
    )
    assert evidence["summary"]["source_ref_ids"]


def test_real_transport_workspace_byte_drift_refuses_as_chain_integrity(
    tmp_path, monkeypatch,
):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    objects = _fixture_transport(monkeypatch)
    workspace_url = owner_reader._workspace_object_url(
        REAL_BASE_URL,
        f"generations/{REAL_CURRENT_GENERATION}/workspaces/{REAL_EVENT_ID}.json",
    )
    drifted = bytearray(objects[workspace_url])
    drifted[0] ^= 0x20
    objects[workspace_url] = bytes(drifted)
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["evidence_input"] is None
    assert result["reasons"] == ["OWNER_READ_CHAIN_INTEGRITY"]


def test_real_transport_broken_predecessor_link_refuses_as_chain_integrity(
    tmp_path, monkeypatch,
):
    repo_root = _build_store(tmp_path, monkeypatch, candidate_rows=_candidate_row())
    _patch_clock(monkeypatch)
    objects = _fixture_transport(monkeypatch)
    manifest_url = owner_reader._workspace_object_url(
        REAL_BASE_URL, f"generations/{REAL_CURRENT_GENERATION}/manifest.json",
    )
    forged = json.loads(objects[manifest_url])
    forged["previous_manifest_sha256"] = "0" * 64
    objects[manifest_url] = _canonical(forged).encode("utf-8")
    snapshot = _snapshot(repo_root)
    key, receipt = _candidate_binding(snapshot)
    result = _read(repo_root, snapshot, key, receipt)
    evidence_sources.validate_daily_brief_evidence_result(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["evidence_input"] is None
    assert result["reasons"] == ["OWNER_READ_CHAIN_INTEGRITY"]
