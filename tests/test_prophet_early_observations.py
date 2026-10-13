"""B03 must find observations beyond the public deck without granting episode/entry authority."""
from __future__ import annotations

import importlib
import importlib.util
import json
from copy import deepcopy
from datetime import date
from hashlib import sha256

import pandas as pd
import pytest

from engine.us_candidate_episode_intake import load_identity_spine
from scripts.build_turn_watch import write_candidate_episode_input
from scripts import reconcile_us_candidate_episodes as b1_writer


@pytest.fixture
def api():
    assert importlib.util.find_spec("engine.prophet_early_observations"), "B03 read model is absent"
    return importlib.import_module("engine.prophet_early_observations")


def seed(tmp_path, tickers=("AMZN",), *, session="2026-10-08"):
    data = tmp_path / "data"
    ref = data / "reference"
    ref.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"security_id": f"SEC:US-XNAS-{t}", "issuer_id": f"ISS:US-XNAS-{t}",
                   "issuer_state": "ACTIVE", "listing_key": f"US-XNAS-{t}"}
                  for t in tickers]).to_parquet(ref / "security_master.parquet", index=False)
    pd.DataFrame([{"vendor": "membership", "vendor_symbol": t,
                   "security_id": f"SEC:US-XNAS-{t}", "valid_from": date(2020, 1, 1),
                   "valid_to": None} for t in tickers]).to_parquet(ref / "vendor_aliases.parquet", index=False)
    rows = [{"ticker": t, "asof": session, "triggers_fired": ["pre_confluence_2d"],
             "triggers": {"pre_confluence_2d": {"fired": True, "evaluated": True, "last_date": session}},
             "slow_tier": {"evaluated": True, "eligible": False,
                           "blocking": ["macd_below_signal"], "null_legs": {}},
             "reset": {"reset_low": 245.96, "reset_low_date": "2026-09-16"}}
            for t in tickers]
    artifact = {"schema": "us_turn_watch.v1", "data_session": session,
                "selection_era": "anticipation-v1", "anchor_era": "anchor-v1",
                "triggers": {"pre_confluence_2d": {"en": "Pre-confluence 2D"}},
                "deck": rows[:40], "beyond_cap": [{"ticker": r["ticker"]} for r in rows[40:]],
                "coverage": {"triggered": len(rows), "deck": min(40, len(rows)),
                             "beyond_cap": max(0, len(rows) - 40)}}
    path = write_candidate_episode_input(artifact, rows, data)
    from engine.us_turn_watch import write_artifact
    write_artifact(artifact, tmp_path / "site")
    return path, load_identity_spine(data), rows, artifact


def test_featured_counts_require_the_exact_source_artifact_partition(api, tmp_path):
    source, spine, _, _ = seed(tmp_path, tuple(f"N{i:03}" for i in range(60)) + ("AMZN",))
    public = tmp_path / "site/turn_watch/turn_watch.json"
    p = view(api, source, spine, public_artifact_path=public)
    assert p["coverage"]["state"] == "VERIFIED_SOURCE_PARTITION"
    assert [p["coverage"][k] for k in ("total", "featured", "beyond_cap")] == [61, 40, 21]
    assert p["rows"][-1]["source_visibility"] == "BEYOND_CAP"
    public.write_text('{}')
    changed = view(api, source, spine, public_artifact_path=public)
    assert changed["coverage"]["featured"] is None
    assert changed["coverage"]["reason"] == "SOURCE_ARTIFACT_RECEIPT_MISMATCH"
    assert len(changed["rows"]) == 61
    assert changed["snapshot_id"] != p["snapshot_id"]


@pytest.mark.parametrize("malformation", ["overlap", "wrong_count", "wrong_session"])
def test_matching_receipt_does_not_certify_a_broken_partition(api, tmp_path, malformation):
    from engine.us_turn_watch import write_artifact
    source, spine, rows, artifact = seed(tmp_path, ("AMZN", "MSFT"))
    if malformation == "overlap":
        artifact["beyond_cap"] = [{"ticker": "AMZN"}]
    elif malformation == "wrong_count":
        artifact["coverage"]["deck"] = 40
    else:
        artifact["data_session"] = "2026-10-07"
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    write_artifact(artifact, tmp_path / "site")
    if malformation == "wrong_session":
        # The dated private source has its original session; bind only its
        # artifact receipt to the mismatched-session public artifact.
        doc = json.loads(source.read_text())
        raw = (tmp_path / "site/turn_watch/turn_watch.json").read_bytes()
        doc["source_artifact_sha256"] = "sha256:" + sha256(raw).hexdigest()
        doc.pop("content_sha256")
        from engine.us_candidate_episode import canonical_json
        doc["content_sha256"] = sha256(canonical_json(doc).encode()).hexdigest()
        source.write_text(json.dumps(doc))
    p = view(api, source, spine, public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json")
    assert p["coverage"]["state"] == "UNAVAILABLE"
    assert p["coverage"]["reason"] == "SOURCE_ARTIFACT_PARTITION_UNAVAILABLE"
    assert p["coverage"]["featured"] is None
    assert len(p["rows"]) == 2


def test_counterevidence_and_correction_limits_preserve_source_meaning(api, tmp_path):
    source, spine, _, _ = seed(tmp_path)
    row = view(api, source, spine)["rows"][0]
    assert row["source_evidence"]["counterevidence"] == ["macd_below_signal"]
    assert row["source_evidence"]["triggers"]["pre_confluence_2d"]["fired"] is True
    assert row["lineage"]["state"] == "CURRENT_RECEIPT_ONLY"
    assert row["lineage"]["prior_receipt"] is None
    assert row["lineage"]["current_receipt"] == row["source_receipt"]
    assert view(api, source, spine)["clocks"]["first_available_at"] is None


def test_missing_counterevidence_is_not_an_all_clear(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    rows[0].pop("slow_tier")
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    row = view(api, source, spine)["rows"][0]
    assert row["source_evidence"]["counterevidence"] is None
    assert row["source_evidence"]["counterevidence_state"] == "UNAVAILABLE_FIELD"


def view(api, source, spine, **kwargs):
    return api.load_observations(source, spine=spine, reference_session="2026-10-08", **kwargs)


def test_exact_security_search_precedes_pagination_and_never_takes_public_top40(tmp_path):
    assert importlib.util.find_spec("engine.prophet_early_observations"), "B03 read model is absent"
    api = importlib.import_module("engine.prophet_early_observations")
    source, spine, _, _ = seed(tmp_path, tuple(f"N{i:03}" for i in range(60)) + ("AMZN",))
    projection = view(api, source, spine)
    page = api.query_observations(projection, security_id="SEC:US-XNAS-AMZN", limit=10)
    assert page["counts"] == {"source": 61, "matched": 1, "returned": 1}
    assert [r["ticker"] for r in page["rows"]] == ["AMZN"]
    assert api.query_observations(projection, offset=50, limit=10)["counts"]["returned"] == 10
    assert len(projection["rows"]) == 61


def test_no_b1_receipt_is_unavailable_relation_not_unanchored_or_new_episode(api, tmp_path):
    source, spine, _, _ = seed(tmp_path)
    before = source.read_bytes()
    result = view(api, source, spine)
    row = result["rows"][0]
    assert row["episode_relation"]["state"] == "EPISODE_JOIN_UNAVAILABLE"
    assert row["episode_relation"]["episode_id"] is None
    assert all(value is False for value in row["authority"].values())
    assert row["identity_basis"] == "CURRENT_REFERENCE_ONLY"
    assert source.read_bytes() == before


def test_logical_close_is_not_actual_availability_observation_or_publication(api, tmp_path):
    source, spine, _, _ = seed(tmp_path)
    clocks = view(api, source, spine)["clocks"]
    assert clocks["source_session"] == "2026-10-08"
    assert clocks["logical_known_at"] == "2026-10-08T20:00:00Z"
    assert clocks["source_available_at"] is None
    assert clocks["observed_at"] is None
    assert clocks["published_at"] is None
    assert clocks["actual_clock_state"] == "NOT_RECORDED"


def test_valid_quiet_source_differs_from_outage_and_tampered_receipt(api, tmp_path):
    source, spine, _, artifact = seed(tmp_path)
    write_candidate_episode_input(artifact, [], tmp_path / "data")
    quiet = view(api, source, spine)
    assert quiet["status"] == "CURRENT_SESSION"
    assert api.query_observations(quiet)["counts"]["source"] == 0
    source.unlink()
    absent = view(api, source, spine)
    assert absent["status"] == "UNAVAILABLE"
    assert api.query_observations(absent)["counts"]["source"] is None
    write_candidate_episode_input(artifact, [], tmp_path / "data")
    doc = json.loads(source.read_text())
    doc["rows"] = [{"ticker": "FORGED"}]
    source.write_text(json.dumps(doc))
    corrupt = view(api, source, spine)
    assert corrupt["status"] == "UNAVAILABLE"
    assert corrupt["reason"] == "SOURCE_RECEIPT_INVALID"
    assert corrupt["rows"] == []


def test_prior_session_is_retained_and_not_promoted_to_current(api, tmp_path):
    source, spine, _, _ = seed(tmp_path, session="2026-10-06")
    result = view(api, source, spine)
    assert result["status"] == "RETAINED_PREVIOUS_SESSION"
    assert result["clocks"]["source_session"] == "2026-10-06"
    assert result["rows"][0]["ticker"] == "AMZN"


def test_unresolved_identity_keeps_observation_searchable_but_cannot_match_security(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    rows.append({**deepcopy(rows[0]), "ticker": "UNKNOWN"})
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    result = view(api, source, spine)
    row = api.query_observations(result, ticker="UNKNOWN")["rows"][0]
    assert row["security_id"] is None
    assert row["episode_relation"]["state"] == "IDENTITY_UNRESOLVED"
    assert api.query_observations(result, security_id="SEC:US-XNAS-UNKNOWN")["rows"] == []


def test_changed_source_cannot_continue_old_pagination_generation(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    first = view(api, source, spine)
    old = first["snapshot_id"]
    rows[0]["reset"]["reset_low"] = 246.0
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    changed = view(api, source, spine)
    assert changed["snapshot_id"] != old
    with pytest.raises(api.ObservationQueryError, match="SNAPSHOT_CHANGED"):
        api.query_observations(changed, expected_snapshot=old)


def test_real_b1_join_uses_exact_receipt_and_keeps_old_active_anchor_immutable(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T21:00:00Z")
    root = tmp_path / "data/us_prophet_rank/episodes"
    before = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    exact = view(api, source, spine, episode_root=root)["rows"][0]
    assert exact["episode_relation"]["state"] == "EXACT_EPISODE"
    original_id = exact["episode_relation"]["episode_id"]
    rows[0]["reset"] = {"reset_low": 250.0, "reset_low_date": "2026-10-07"}
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    missing = view(api, source, spine, episode_root=root)["rows"][0]
    assert missing["episode_relation"]["state"] == "EPISODE_JOIN_UNAVAILABLE"
    assert missing["episode_relation"]["episode_id"] is None
    assert before == {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T22:00:00Z")
    blocked = view(api, source, spine, episode_root=root)["rows"][0]
    assert blocked["episode_relation"]["state"] == "BLOCKED_BY_ACTIVE_EPISODE"
    assert blocked["episode_relation"]["reason"] == "ACTIVE_EPISODE_DIFFERENT_ANCHOR"
    assert blocked["episode_relation"]["episode_id"] is None
    from engine.us_candidate_episode import load_candidate_episode_store
    assert [r["episode_id"] for r in load_candidate_episode_store(root)] == [original_id]


@pytest.mark.parametrize("query", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": True},
                                  {"security_id": "../AMZN"}, {"ticker": "AMZN*"}])
def test_query_rejects_unbounded_or_nonexact_requests(api, tmp_path, query):
    source, spine, _, _ = seed(tmp_path)
    with pytest.raises(api.ObservationQueryError):
        api.query_observations(view(api, source, spine), **query)


def test_missing_anchor_keeps_the_real_b1_suppression_without_inventing_episode(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    rows[0]["reset"] = {}
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    assert view(api, source, spine)["rows"][0]["episode_relation"]["state"] == "EPISODE_JOIN_UNAVAILABLE"
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T21:00:00Z")
    result = view(api, source, spine, episode_root=tmp_path / "data/us_prophet_rank/episodes")
    # The current B1 writer normalizes missing reset-low to INVALID_STRUCTURAL_ANCHOR,
    # before canonical identity binding. Preserve that exact source refusal; do
    # not relabel it as the different MISSING_STRUCTURAL_ANCHOR state.
    assert result["rows"][0]["episode_relation"]["state"] == "SOURCE_SUPPRESSED"
    assert result["rows"][0]["episode_relation"]["reason"] == "INVALID_STRUCTURAL_ANCHOR"
    assert result["rows"][0]["episode_relation"]["episode_id"] is None


def test_bad_trigger_flags_fail_as_unavailable_instead_of_quiet_data(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    rows[0]["triggers"]["pre_confluence_2d"]["fired"] = "true"
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    result = view(api, source, spine)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_MALFORMED"


def relation_snapshot(api, rows, *, events=None, suppressions=None, episodes=None, generation="peg:test"):
    """A declared post-validation snapshot double for relation-only assertions."""
    from types import SimpleNamespace
    normal_events = [{"source_system": "turn_watch", "source_schema": api.TURN_WATCH_SCHEMA,
                      "source_event_id": row["source_event_id"], "source_receipt": row["source_receipt"],
                      "episode_id": f"episode:{row['ticker']}"} for row in rows]
    normal_episodes = [{"episode_id": f"episode:{row['ticker']}",
                        "security_id": row["security_id"]} for row in rows]
    return SimpleNamespace(generation_id=generation, generation=SimpleNamespace(
        events=normal_events if events is None else events,
        suppressions=[] if suppressions is None else suppressions,
        episodes=normal_episodes if episodes is None else episodes))


def stub_byte_attestation(api, monkeypatch, snapshot):
    """Explicit byte-owner double for relation-only unit tests, not storage proof."""
    from engine.us_candidate_episode import CandidateEpisodeByteToken
    token = CandidateEpisodeByteToken(snapshot.generation_id, "fixture-manifest", "fixture-head")
    monkeypatch.setattr(api, "attest_candidate_episode_store_bytes", lambda _: token)


@pytest.mark.parametrize("case,expected", [
    ("exact", "EXACT_EPISODE"),
    ("duplicate_event", "EPISODE_JOIN_UNAVAILABLE"),
    ("event_and_suppression", "EPISODE_JOIN_UNAVAILABLE"),
    ("duplicate_suppression", "EPISODE_JOIN_UNAVAILABLE"),
    ("wrong_security", "EPISODE_JOIN_UNAVAILABLE"),
    ("missing_episode", "EPISODE_JOIN_UNAVAILABLE"),
    ("wrong_system", "EPISODE_JOIN_UNAVAILABLE"),
    ("wrong_schema", "EPISODE_JOIN_UNAVAILABLE"),
    ("wrong_receipt", "EPISODE_JOIN_UNAVAILABLE"),
    ("active_anchor", "BLOCKED_BY_ACTIVE_EPISODE"),
    ("unbound_suppression", "NOT_YET_ANCHORED"),
    ("wrong_suppression_security", "EPISODE_JOIN_UNAVAILABLE"),
])
def test_relation_cardinality_and_exact_source_binding(api, tmp_path, monkeypatch, case, expected):
    source, spine, _, _ = seed(tmp_path)
    row = view(api, source, spine)["rows"][0]
    snapshot = relation_snapshot(api, [row])
    generation = snapshot.generation
    event = generation.events[0]
    suppression = {**event, "security_id": row["security_id"],
                   "reason": "ACTIVE_EPISODE_DIFFERENT_ANCHOR"}
    if case == "duplicate_event":
        generation.events.append(dict(event))
    elif case == "event_and_suppression":
        generation.suppressions.append(suppression)
    elif case == "duplicate_suppression":
        generation.events = []
        generation.suppressions = [suppression, dict(suppression)]
    elif case == "wrong_security":
        generation.episodes[0]["security_id"] = "SEC:US-XNAS-OTHER"
    elif case == "missing_episode":
        generation.episodes = []
    elif case in {"wrong_system", "wrong_schema", "wrong_receipt"}:
        event[{"wrong_system": "source_system", "wrong_schema": "source_schema",
               "wrong_receipt": "source_receipt"}[case]] = "other"
    elif case in {"active_anchor", "unbound_suppression", "wrong_suppression_security"}:
        generation.events = []
        if case == "unbound_suppression":
            suppression.update(security_id=None, reason="MISSING_STRUCTURAL_ANCHOR")
        elif case == "wrong_suppression_security":
            suppression["security_id"] = "SEC:US-XNAS-OTHER"
        generation.suppressions = [suppression]
    # Same ticker/security and same event ID are insufficient when provenance differs.
    generation.events.extend([{**event, "source_system": "another_producer"},
                              {**event, "source_schema": "another_schema"},
                              {**event, "source_receipt": "another_receipt"}])
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: snapshot)
    stub_byte_attestation(api, monkeypatch, snapshot)
    result = view(api, source, spine, episode_root=tmp_path)["rows"][0]["episode_relation"]
    assert result["state"] == expected
    assert result["generation_id"] == "peg:test"
    assert result["episode_id"] == ("episode:AMZN" if expected == "EXACT_EPISODE" else None)


def test_relation_population_scans_each_validated_collection_once(api, tmp_path, monkeypatch):
    class CountedRows(list):
        yielded = 0

        def __iter__(self):
            for row in super().__iter__():
                self.yielded += 1
                yield row

    source, spine, _, _ = seed(tmp_path, tuple(f"N{i:03}" for i in range(48)))
    rows = view(api, source, spine)["rows"]
    snapshot = relation_snapshot(api, rows)
    gen = snapshot.generation
    gen.events = CountedRows(gen.events)
    gen.episodes = CountedRows(gen.episodes)
    gen.suppressions = CountedRows([{**row, "source_receipt": "unrelated", "reason": "OTHER"}
                                   for row in list.__iter__(gen.events)])
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: snapshot)
    stub_byte_attestation(api, monkeypatch, snapshot)
    result = view(api, source, spine, episode_root=tmp_path)
    assert len(result["rows"]) == 48
    assert all(row["episode_relation"]["state"] == "EXACT_EPISODE" for row in result["rows"])
    assert {name: getattr(gen, name).yielded for name in ("events", "suppressions", "episodes")} == {
        "events": 48, "suppressions": 48, "episodes": 48}


def test_same_head_corruption_after_a_successful_read_does_not_reuse_relation(api, tmp_path):
    source, spine, _, _ = seed(tmp_path)
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T21:00:00Z")
    root = tmp_path / "data/us_prophet_rank/episodes"
    head_bytes = (root / "HEAD.json").read_bytes()
    first = view(api, source, spine, episode_root=root)
    gid = json.loads(head_bytes)["generation_id"]
    payload = root / "generations" / gid / "all_candidates.json"
    original = payload.read_bytes()
    payload.write_bytes(original + b" ")
    changed = view(api, source, spine, episode_root=root)
    assert (root / "HEAD.json").read_bytes() == head_bytes
    assert changed["status"] == "CURRENT_SESSION" and len(changed["rows"]) == 1
    assert changed["rows"][0]["episode_relation"]["reason"] == "B1_SNAPSHOT_UNAVAILABLE"
    assert changed["snapshot_id"] != first["snapshot_id"]
    with pytest.raises(api.ObservationQueryError, match="SNAPSHOT_CHANGED"):
        api.query_observations(changed, expected_snapshot=first["snapshot_id"])
    payload.write_bytes(original)
    assert view(api, source, spine, episode_root=root)["snapshot_id"] == first["snapshot_id"]


def _seed_episode_store(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T21:00:00Z")
    return source, spine, rows, artifact, tmp_path / "data/us_prophet_rank/episodes"


def test_repeated_pages_reuse_only_byte_reattested_relations(api, tmp_path, monkeypatch):
    source, spine, _, _, root = _seed_episode_store(api, tmp_path)
    original = api.load_candidate_episode_store_snapshot
    reads = []
    original_attest = api.attest_candidate_episode_store_bytes
    attestations = []
    def counted_attestation(path):
        attestations.append(path)
        return original_attest(path)
    def counted(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", counted)
    monkeypatch.setattr(api, "attest_candidate_episode_store_bytes", counted_attestation)
    first = view(api, source, spine, episode_root=root)
    assert len(attestations) == 2, "cold construction must attest before and after validation"
    second = view(api, source, spine, episode_root=root)
    assert len(attestations) == 3, "every warm read must freshly attest every file"
    assert first == second
    assert first["rows"][0]["episode_relation"]["state"] == "EXACT_EPISODE"
    assert len(reads) == 1, "unchanged paging must not repeat semantic replay"
    # Returning mutable dictionaries to callers must not expose cached storage.
    first["rows"][0]["episode_relation"]["episode_id"] = "forged"
    assert view(api, source, spine, episode_root=root) == second


@pytest.mark.parametrize("artifact", ["HEAD.json", "manifest.json", "all_candidates.json",
    "current.parquet", "latest_receipt.json", "event", "added", "removed"])
def test_warm_relations_fail_closed_on_every_actual_byte_or_file_set_change(api, tmp_path, artifact):
    source, spine, _, _, root = _seed_episode_store(api, tmp_path)
    first = view(api, source, spine, episode_root=root)
    gid = json.loads((root / "HEAD.json").read_text())["generation_id"]
    generation = root / "generations" / gid
    if artifact == "HEAD.json":
        target = root / artifact
    elif artifact in {"event", "removed"}:
        target = next((generation / "events").glob("*.jsonl"))
    elif artifact == "added":
        target = generation / "unexpected.json"
    else:
        target = generation / artifact
    original = target.read_bytes() if target.exists() else None
    if artifact == "removed":
        target.unlink()
    else:
        # Keep size and mtime for existing files: metadata is not integrity.
        import os
        stat = target.stat() if target.exists() else None
        changed = (b"!" + original[1:]) if original else b"{}"
        target.write_bytes(changed)
        if stat:
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    changed = view(api, source, spine, episode_root=root)
    assert changed["rows"][0]["episode_relation"]["reason"] == "B1_SNAPSHOT_UNAVAILABLE"
    assert changed["snapshot_id"] != first["snapshot_id"]


def test_warm_relations_revalidate_new_generation_and_current_identity(api, tmp_path, monkeypatch):
    source, spine, rows, artifact, root = _seed_episode_store(api, tmp_path)
    original = api.load_candidate_episode_store_snapshot
    reads = []
    def counted(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", counted)
    first = view(api, source, spine, episode_root=root)
    no_identity = view(api, source, None, episode_root=root)
    assert no_identity["rows"][0]["episode_relation"]["state"] == "IDENTITY_UNRESOLVED"
    assert no_identity["snapshot_id"] != first["snapshot_id"]
    assert len(reads) == 1
    rows[0]["reset"] = {"reset_low": 250.0, "reset_low_date": "2026-10-07"}
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T22:00:00Z")
    changed = view(api, source, spine, episode_root=root)
    assert changed["rows"][0]["episode_relation"]["state"] == "BLOCKED_BY_ACTIVE_EPISODE"
    assert len(reads) == 2
    assert view(api, source, spine, episode_root=root) == changed
    assert len(reads) == 2


def test_suppression_bytes_are_reattested_after_success(api, tmp_path):
    source, spine, rows, artifact = seed(tmp_path)
    rows[0]["reset"] = {}
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    b1_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, correction_path=None,
                        recorded_at="2026-10-08T21:00:00Z")
    root = tmp_path / "data/us_prophet_rank/episodes"
    first = view(api, source, spine, episode_root=root)
    assert first["rows"][0]["episode_relation"]["state"] == "SOURCE_SUPPRESSED"
    gid = json.loads((root / "HEAD.json").read_text())["generation_id"]
    path = next((root / "generations" / gid / "suppressions").glob("*.jsonl"))
    path.write_bytes(path.read_bytes() + b" ")
    assert view(api, source, spine, episode_root=root)["rows"][0]["episode_relation"]["reason"] == "B1_SNAPSHOT_UNAVAILABLE"


def test_byte_attestation_never_replaces_public_semantic_validation(api, tmp_path, monkeypatch):
    from engine import us_candidate_episode as core
    _, _, _, _, root = _seed_episode_store(api, tmp_path)
    def refuse_semantics(_):
        raise core.EpisodeContractError("semantic validation is still mandatory")
    monkeypatch.setattr(core, "validate_candidate_episode_generation_payload", refuse_semantics)
    token = core.attest_candidate_episode_store_bytes(root)
    assert token.generation_id.startswith("peg:")
    with pytest.raises(core.EpisodeContractError, match="still mandatory"):
        core.load_candidate_episode_store_snapshot(root)


def test_concurrent_relations_construct_once_and_never_alias_or_exceed_bound(api, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    source, spine, _, _, root = _seed_episode_store(api, tmp_path)
    receipt = view(api, source, spine)["source_receipt"]
    original = api.load_candidate_episode_store_snapshot
    reads = []
    def counted(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", counted)
    cache = api._AttestedRelationCache()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: cache.read(root, receipt), range(8)))
    assert len(reads) == 1
    assert all(result == results[0] for result in results)
    index = results[0]
    with pytest.raises(TypeError):
        index[1][("forged", receipt)] = ()
    with pytest.raises(TypeError):
        next(iter(index[1].values()))[0]["episode_id"] = "forged"
    assert api._relation_index_bytes(index) <= cache.max_bytes
    cache = api._AttestedRelationCache()
    cache.max_bytes = 1
    assert cache.read(root, receipt) == index
    assert cache.read(root, receipt) == index
    assert cache._entry is None and len(reads) == 3


def test_cold_relation_construction_cannot_publish_a_changed_token(api, tmp_path, monkeypatch):
    from dataclasses import replace
    source, spine, _, _, root = _seed_episode_store(api, tmp_path)
    original = api.attest_candidate_episode_store_bytes
    token = original(root)
    calls = []
    def changes_during_read(path):
        calls.append(path)
        return token if len(calls) == 1 else replace(token, head_sha256="changed")
    monkeypatch.setattr(api, "attest_candidate_episode_store_bytes", changes_during_read)
    cache = api._AttestedRelationCache()
    with pytest.raises(api.EpisodeContractError, match="changed during"):
        cache.read(root, view(api, source, spine)["source_receipt"])
    assert cache._entry is None


def test_coherently_readdressed_corruption_cannot_seed_a_new_relation_entry(api, tmp_path):
    from tests.test_us_candidate_episode_reconciler import _readdress_current_generation
    source, spine, _, _, root = _seed_episode_store(api, tmp_path)
    first = view(api, source, spine, episode_root=root)
    gid = json.loads((root / "HEAD.json").read_text())["generation_id"]
    path = next((root / "generations" / gid / "events").glob("*.jsonl"))
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[0]["content_sha256"] = "0" * 64
    path.write_text("".join(api.canonical_json(event) + "\n" for event in events))
    _readdress_current_generation(tmp_path)
    # Byte attestation succeeds, but new semantic validation must still refuse.
    assert api.attest_candidate_episode_store_bytes(root).generation_id != gid
    changed = view(api, source, spine, episode_root=root)
    assert changed["rows"][0]["episode_relation"]["reason"] == "B1_SNAPSHOT_UNAVAILABLE"
    assert changed["snapshot_id"] != first["snapshot_id"]
