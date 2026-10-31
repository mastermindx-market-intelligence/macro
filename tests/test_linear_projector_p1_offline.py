"""Hermetic project preflight tests; never authenticate or mutate Linear."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import linear_portfolio_plan as p0
from scripts import linear_projector_p1_offline as p1

WORKSPACE = "workspace-test"
TEAM = "team-test"
SOURCE_BLOCK = p1.P0_BEGIN + "\nCanonical workstream: WS:ALPHA\n" + p1.P0_END


def fixture():
    row = {"workstream_key": "WS:ALPHA",
           "desired_project_name": "WS:ALPHA — Alpha",
           "desired_project_summary": "Alpha",
           "desired_project_status_class": "started",
           "managed_description_block": SOURCE_BLOCK}
    plan = {"schema": p0.PLAN_SCHEMA, "active_projects": [row],
            "review_candidates": [], "excluded_projects": [], "warnings": [], "summary": {}}
    plan["semantic_hash"] = p1.digest(plan)
    project = {"id": "p1", "workstream_key": "WS:ALPHA",
               "workspace_id": WORKSPACE, "team_id": TEAM,
               "name": row["desired_project_name"],
               "summary": row["desired_project_summary"],
               "description": "Human notes  \n" + p1.normalized_managed(SOURCE_BLOCK)
               + "\n\nHandwritten trailing notes.",
               "updatedAt": "2026-10-20T08:00:00Z", "status_class": "started"}
    return plan, {"WS:ALPHA": "p1"}, [project]


def run(plan=None, bindings=None, projects=None, *, source=None):
    default_plan, default_bindings, default_projects = fixture()
    p = default_plan if plan is None else plan
    return p1.plan_offline(
        p, default_bindings if bindings is None else bindings,
        default_projects if projects is None else projects,
        expected_workspace_id=WORKSPACE, expected_team_id=TEAM,
        expected_semantic_hash=p["semantic_hash"] if source is None else source)


def rehash(p):
    p["semantic_hash"] = p1.digest({k: v for k, v in p.items() if k != "semantic_hash"})


def test_zero_effect_noop_and_determinism():
    result = run()
    assert result == run()
    assert result["effects"] == 0
    row = result["results"][0]
    assert row["outcome"] == "dry_run_noop"
    assert row["changed_fields"] == []
    assert len(row["preimage_hash"]) == 64


def test_one_field_change_and_no_private_prose_in_receipt():
    _, _, projects = fixture()
    projects[0]["name"] = "Previous title"
    receipt = run(projects=projects)
    assert receipt["results"][0]["changed_fields"] == ["name"]
    assert "Human notes" not in json.dumps(receipt)


def test_manual_content_preserved_byte_for_byte():
    _, _, projects = fixture()
    before = projects[0]["description"]
    after = p1.replace_managed(before, p1.BEGIN + "\nNEW\n" + p1.END)
    assert after.startswith("Human notes  \n")
    assert after.endswith("\n\nHandwritten trailing notes.")
    assert "Canonical workstream: WS:ALPHA" not in after


@pytest.mark.parametrize("field,want", [
    ("team_id", "team_access_refused"),
    ("workspace_id", "workspace_mismatch"),
    ("workstream_key", "binding_mismatch"),
])
def test_wrong_scope_or_binding_never_updates(field, want):
    _, _, projects = fixture()
    projects[0][field] = "WS:OTHER" if field == "workstream_key" else "different"
    assert run(projects=projects)["results"][0]["outcome"] == want


@pytest.mark.parametrize("field", ["updatedAt", "name", "summary", "description"])
def test_incomplete_preimage_is_not_false_empty(field):
    _, _, projects = fixture()
    del projects[0][field]
    assert run(projects=projects)["results"][0]["outcome"] == "preimage_unavailable"


@pytest.mark.parametrize("marker", [
    "Human notes without marker",
    p1.BEGIN + "unclosed",
    p1.END + p1.BEGIN,
    p1.BEGIN + p1.BEGIN + p1.END,
    p1.BEGIN + p1.END + p1.END,
    p1.P0_BEGIN + "P0 only" + p1.P0_END,
])
def test_existing_description_marker_defect_refuses(marker):
    _, _, projects = fixture()
    projects[0]["description"] = marker
    assert run(projects=projects)["results"][0]["outcome"] == "managed_block_invalid"


@pytest.mark.parametrize("block", [
    "", p1.P0_BEGIN + "unclosed",
    p1.P0_BEGIN + p1.P0_BEGIN + "x" + p1.P0_END,
    p1.P0_BEGIN + "\n" + p1.P0_END,
    p1.P0_BEGIN + p1.BEGIN + p1.P0_END,
])
def test_source_marker_injection_refuses(block):
    with pytest.raises(ValueError):
        p1.normalized_managed(block)


@pytest.mark.parametrize("bad", ["wrong_hash", "wrong_schema", "duplicate", "cross_bucket"])
def test_plan_invalidity_fails_closed(bad):
    plan, _, _ = fixture()
    if bad == "wrong_hash":
        plan["semantic_hash"] = "f" * 64
    elif bad == "wrong_schema":
        plan["schema"] = "wrong"
        rehash(plan)
    elif bad == "duplicate":
        plan["active_projects"].append(copy.deepcopy(plan["active_projects"][0]))
        rehash(plan)
    elif bad == "cross_bucket":
        plan["excluded_projects"].append({"workstream_key": "WS:ALPHA"})
        rehash(plan)
    assert run(plan=plan)["status"] == "refused"


def test_expected_plan_hash_mismatch_refuses():
    assert run(source="f" * 64)["reason"] == "plan_identity_mismatch"


def test_unbound_same_name_never_fuzzy_matches():
    assert run(bindings={})["results"][0]["outcome"] == "unverified_identity_candidate"


def test_exact_binding_missing_refuses():
    assert run(projects=[])["results"][0]["outcome"] == "bound_project_not_observed"


def test_unknown_binding_refuses():
    assert run(bindings={"WS:OTHER": "p1"})["status"] == "refused"


@pytest.mark.parametrize("shape", [
    [{"id": 4}], [{"id": "p1"}, {"id": "p1"}], "wrong_snapshot"
])
def test_invalid_snapshot_identity_refuses(shape):
    assert run(projects=shape)["status"] == "refused"


def test_duplicate_workstream_project_identity_refuses():
    _, _, projects = fixture()
    second = copy.deepcopy(projects[0])
    second["id"] = "p2"
    assert run(projects=projects + [second])["reason"] == "project_identity_ambiguous"


@pytest.mark.parametrize("field,value,expected", [
    ("trashed", True, "binding_inactive"),
    ("archivedAt", "2026-10-01T00:00Z", "binding_inactive"),
])
def test_inactive_projects_are_refused(field, value, expected):
    _, _, projects = fixture()
    projects[0][field] = value
    assert run(projects=projects)["results"][0]["outcome"] == expected


def test_status_drift_is_report_only():
    _, _, projects = fixture()
    projects[0]["status_class"] = "paused"
    row = run(projects=projects)["results"][0]
    assert row["status_drift"] is True
    assert row["status_change_authorized"] is False
    projects[0].pop("status_class")
    assert run(projects=projects)["results"][0]["status_drift"] is None


def test_two_workstreams_bound_to_same_project_refused():
    plan, binding, projects = fixture()
    other = copy.deepcopy(plan["active_projects"][0])
    other["workstream_key"] = "WS:BETA"
    other["desired_project_name"] = "WS:BETA — Beta"
    plan["active_projects"].append(other)
    rehash(plan)
    binding["WS:BETA"] = "p1"
    assert run(plan=plan, bindings=binding, projects=projects)["reason"] == "project_identity_ambiguous"


@pytest.mark.parametrize("valid", [True, False])
def test_cli_round_trip_refuses_invalid_snapshot(tmp_path, valid):
    plan, bindings, projects = fixture()
    snapshot = {"schema": p1.SNAPSHOT_SCHEMA if valid else "other",
                "workspace_id": WORKSPACE, "team_id": TEAM,
                "observed_at": "2026-10-20T08:10:00Z", "projects": projects}
    for name, value in [("plan", plan), ("bindings", bindings), ("snapshot", snapshot)]:
        (tmp_path / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
    cmd = [sys.executable, "-m", "scripts.linear_projector_p1_offline",
           "--plan", str(tmp_path / "plan.json"),
           "--bindings", str(tmp_path / "bindings.json"),
           "--snapshot", str(tmp_path / "snapshot.json"),
           "--expected-semantic-hash", plan["semantic_hash"],
           "--workspace-id", WORKSPACE, "--team-id", TEAM]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=12,
                            cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == (0 if valid else 2), result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["effects"] == 0
    assert receipt["status"] == ("dry_run" if valid else "refused")


@pytest.mark.parametrize("bad", ["garbage", "2026-10-20T20:01:00", "", None])
def test_invalid_observation_version_refuses(bad):
    _, _, projects = fixture()
    projects[0]["updatedAt"] = bad
    assert run(projects=projects)["results"][0]["outcome"] == "preimage_unavailable"


def test_scope_and_status_are_bound_into_preimage_hash():
    first = run()["results"][0]["preimage_hash"]
    _, _, projects = fixture()
    projects[0]["status_class"] = "paused"
    second = run(projects=projects)["results"][0]["preimage_hash"]
    assert first != second


def test_malformed_unicode_in_existing_description_refuses_safely():
    _, _, projects = fixture()
    projects[0]["description"] += "\ud800"
    assert run(projects=projects)["results"][0]["outcome"] == "preimage_unavailable"


@pytest.mark.parametrize("bad", ["not-a-time", "2026-10-20T20:01:00", ""])
def test_snapshot_timestamp_parser_requires_timezone(bad):
    assert not p1._timestamp(bad)
    assert p1._timestamp("2026-10-20T20:01:00-07:00")
    assert p1._timestamp("2026-10-21T03:01:00Z")



def test_unbound_with_no_observed_candidate_never_claims_creation():
    result = run(bindings={}, projects=[])
    assert result["effects"] == 0
    assert result["live_apply_authorized"] is False
    assert result["results"][0]["outcome"] == "unbound_requires_reconciliation"
    assert result["summary"]["unbound_workstreams"] == 1
    assert "would_create" not in json.dumps(result)


def test_unbound_matching_ws_is_only_an_untrusted_candidate():
    result = run(bindings={})
    candidate = result["results"][0]
    assert candidate["outcome"] == "unverified_identity_candidate"
    assert candidate["candidate_project_id"] == "p1"
    assert candidate["candidate_basis"] == "untrusted_snapshot_workstream_key"
    assert result["summary"]["unverified_identity_candidates"] == 1
    assert result["summary"]["bound_ready_for_review"] == 0
    assert result["summary"]["review_required"] == 1
    assert result["summary"]["snapshot_completeness_verified"] is False


def test_bound_project_absence_from_subset_is_not_deletion_proof():
    result = run(projects=[])
    assert result["results"][0]["outcome"] == "bound_project_not_observed"
    assert result["summary"]["bound_projects_not_observed"] == 1
    assert "would_create" not in json.dumps(result)


def test_ready_count_never_authorizes_live_apply():
    result = run()
    assert result["results"][0]["outcome"] == "dry_run_noop"
    assert result["summary"]["bound_ready_for_review"] == 1
    assert result["summary"]["review_required"] == 0
    assert result["live_apply_authorized"] is False


def _excluded_fixture(*, excluded_status="completed", observed_status="started",
                      include_binding=True, include_project=True):
    plan, bindings, projects = fixture()
    plan["excluded_projects"] = [{
        "workstream_key": "WS:DONE-EXAMPLE",
        "canonical_status": "done",
        "desired_project_status_class": excluded_status,
        "reason": "canonical_status_done",
    }]
    if include_binding:
        bindings["WS:DONE-EXAMPLE"] = "p-excluded"
    if include_project:
        excluded = copy.deepcopy(projects[0])
        excluded.update({
            "id": "p-excluded",
            "workstream_key": "WS:DONE-EXAMPLE",
            "name": "WS:DONE-EXAMPLE — Done workstream",
            "status_class": observed_status,
        })
        projects.append(excluded)
    rehash(plan)
    return plan, bindings, projects


def test_excluded_bound_active_status_is_review_only():
    plan, bindings, projects = _excluded_fixture()
    result = run(plan=plan, bindings=bindings, projects=projects)
    row = result["excluded_review"][0]
    assert result["status"] == "dry_run"
    assert result["effects"] == 0
    assert result["live_apply_authorized"] is False
    assert row["outcome"] == "would_deactivate_or_archive"
    assert row["action_authorized"] is False
    assert row["project_id"] == "p-excluded"
    assert row["observed_status_class"] == "started"
    assert result["summary"]["excluded_lifecycle_review_candidates"] == 1
    assert result["summary"]["excluded_workstreams"] == 1


def test_excluded_aligned_status_never_emits_deactivation():
    plan, bindings, projects = _excluded_fixture(observed_status="completed")
    result = run(plan=plan, bindings=bindings, projects=projects)
    assert result["excluded_review"][0]["outcome"] == "excluded_status_already_aligned"
    assert result["summary"]["excluded_lifecycle_review_candidates"] == 0


def test_excluded_unbound_hint_requires_explicit_review():
    plan, _, projects = _excluded_fixture(include_binding=False)
    result = run(plan=plan, bindings={"WS:ALPHA": "p1"}, projects=projects)
    row = result["excluded_review"][0]
    assert row["outcome"] == "excluded_binding_requires_review"
    assert row["candidate_project_id"] == "p-excluded"
    assert row["candidate_basis"] == "untrusted_snapshot_workstream_key"
    assert row["action_authorized"] is False


def test_excluded_unbound_unobserved_does_not_prove_absence():
    plan, _, projects = _excluded_fixture(include_binding=False, include_project=False)
    result = run(plan=plan, bindings={"WS:ALPHA": "p1"}, projects=projects)
    row = result["excluded_review"][0]
    assert row["outcome"] == "excluded_binding_requires_review"
    assert "candidate_project_id" not in row
    assert result["effects"] == 0


def test_excluded_bound_missing_snapshot_is_not_deleted():
    plan, bindings, projects = _excluded_fixture(include_project=False)
    result = run(plan=plan, bindings=bindings, projects=projects)
    assert result["excluded_review"][0]["outcome"] == "excluded_bound_project_not_observed"
    assert result["summary"]["excluded_lifecycle_review_candidates"] == 0


@pytest.mark.parametrize("field, value, want", [
    ("workspace_id", "foreign", "workspace_mismatch"),
    ("team_id", "foreign", "team_access_refused"),
    ("status_class", None, "excluded_status_unknown"),
    ("updatedAt", "no_timezone", "preimage_unavailable"),
    ("archivedAt", "2026-10-20T00:00:00Z", "excluded_inactive_observed"),
    ("workstream_key", "WS:FOREIGN", "excluded_binding_mismatch"),
])
def test_excluded_project_conflict_does_not_offer_lifecycle_mutation(field, value, want):
    plan, bindings, projects = _excluded_fixture()
    projects[1][field] = value
    result = run(plan=plan, bindings=bindings, projects=projects)
    row = result["excluded_review"][0]
    assert row["outcome"] == want
    assert row["action_authorized"] is False
    assert result["summary"]["excluded_lifecycle_review_candidates"] == 0
    assert result["effects"] == 0


def test_excluded_project_identity_cannot_alias_active_project_id():
    plan, bindings, projects = _excluded_fixture()
    bindings["WS:DONE-EXAMPLE"] = bindings["WS:ALPHA"]
    result = run(plan=plan, bindings=bindings, projects=projects)
    assert result["status"] == "refused"
    assert result["reason"] == "project_identity_ambiguous"


def test_invalid_excluded_row_refuses_even_with_rehashed_plan():
    plan, bindings, projects = _excluded_fixture()
    del plan["excluded_projects"][0]["desired_project_status_class"]
    rehash(plan)
    result = run(plan=plan, bindings=bindings, projects=projects)
    assert result["status"] == "refused"
    assert result["reason"] == "plan_rows_invalid_or_duplicate_ws_key"


def test_proposed_candidates_never_create_anything():
    plan, bindings, projects = fixture()
    plan["review_candidates"] = [{"workstream_key": "WS:PROPOSED-EXAMPLE"}]
    rehash(plan)
    result = run(plan=plan, bindings=bindings, projects=projects)
    assert result["status"] == "dry_run"
    assert result["effects"] == 0
    assert result["proposal_review"] == [{
        "workstream_key": "WS:PROPOSED-EXAMPLE",
        "outcome": "proposed_requires_review",
        "action_authorized": False,
    }]
    assert result["summary"]["proposed_workstreams_for_review"] == 1
    assert result["live_apply_authorized"] is False
