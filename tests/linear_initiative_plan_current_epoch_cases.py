"""Current-epoch Linear Initiative contract tests.

Imported by ``tests/test_agentos_compile.py`` so the existing Agent OS/self-mod
CI lane executes the protected 7/63/2 contract without adding another workflow
or job.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from scripts import linear_initiative_plan as lip
from scripts import linear_initiative_plan_legacy as _lip_legacy
from scripts import linear_portfolio_plan as lpp

REPO = Path(__file__).resolve().parents[1]
STRATEGY = REPO / "config" / "linear_initiative_portfolio.v1.json"
TEMPORAL_GRAIN = "WS:TEMPORAL-GRAIN-INTELLIGENCE"
TEMPORAL_GRAIN_INITIATIVE = "legendary-alpha-discovery-timing"
EXPECTED_SOURCE = {
    "repository": "mastermindx-market-intelligence/Mastermind",
    "path": (
        "docs/superpowers/specs/"
        "2026-09-03-linear-initiative-portfolio-v1-temporal-grain-current-epoch-amendment.md"
    ),
    "protected_revision": "6c5c2a6225a3fa2c2ec3e3398dcc8b8629b3a988",
}
EXPECTED_GROUP_COUNTS = {
    "autonomous-ai-organization": 7,
    "canonical-intelligence-substrate-learning": 10,
    "global-markets-regimes-risk-command": 6,
    "institutional-company-event-intelligence": 11,
    "legendary-alpha-discovery-timing": 17,
    "personal-institutional-desk": 4,
    "trusted-production-customer-platform": 8,
}
REQUIRED_CURRENT = {
    "WS:AGENT-EVAL-FABRIC": "autonomous-ai-organization",
    "WS:CODE-INTELLIGENCE-FABRIC": "autonomous-ai-organization",
    "WS:CROSS-REPO-CONTRACT-GOVERNANCE": "canonical-intelligence-substrate-learning",
    "WS:EXECUTIVE-ATTENTION-ECONOMICS": "autonomous-ai-organization",
    "WS:EXECUTIVE-OS-DISASTER-RECOVERY": "trusted-production-customer-platform",
    "WS:FLOW-OBSERVATORY-V2": "global-markets-regimes-risk-command",
    "WS:OPERATION-ASSURANCE": "autonomous-ai-organization",
    "WS:PROPHET-CANDIDATE-ADDED-DATE": "legendary-alpha-discovery-timing",
    "WS:REACTIVE-PROJECTION": "personal-institutional-desk",
    "WS:REPRODUCIBLE-WORKER-ENVIRONMENTS": "trusted-production-customer-platform",
    "WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE": "legendary-alpha-discovery-timing",
    "WS:TEMPORAL-GRAIN-INTELLIGENCE": "legendary-alpha-discovery-timing",
    "WS:TERMINAL-GITHUB-CANONICALIZATION": "trusted-production-customer-platform",
}
PARKED_ALIAS = "WS:TERMINAL-GITHUB-CANONICAL-DEPLOYMENT"


def _strategy() -> dict:
    return json.loads(STRATEGY.read_text(encoding="utf-8"))


def _row(key: str, *, status: str = "active") -> dict:
    return {
        "workstream_key": key,
        "desired_project_name": f"{key} — projected",
        "desired_project_status_class": "completed" if status == "done" else "active",
        "canonical_status": status,
    }


def _project_plan(strategy: dict | None = None) -> dict:
    strategy = strategy or _strategy()
    rows = [_row(key) for key in sorted(strategy["memberships"])]
    rows.append(_row("WS:WATCHLIST-PORTFOLIO-CEO"))
    return {
        "schema": lpp.PLAN_SCHEMA,
        "semantic_hash": "linear-project-plan-current-epoch",
        "active_projects": rows,
        "review_candidates": [],
        "excluded_projects": [],
    }


def _codes(error: lip.InitiativePlanError) -> set[str]:
    return {row["code"] for row in error.failures}


def _failure(error: lip.InitiativePlanError, code: str) -> dict:
    return next(row for row in error.failures if row["code"] == code)


def test_linear_initiative_strategy_is_exact_workspace_level_7_63_2() -> None:
    strategy = _strategy()
    assert strategy["schema"] == lip.STRATEGY_SCHEMA
    assert strategy["source_design"] == EXPECTED_SOURCE
    assert len(strategy["initiatives"]) == 7
    assert len(strategy["memberships"]) == 63
    assert len(strategy["unassigned_exceptions"]) == 2
    assert dict(sorted(Counter(strategy["memberships"].values()).items())) == (
        EXPECTED_GROUP_COUNTS
    )
    assert {key: strategy["memberships"][key] for key in REQUIRED_CURRENT} == (
        REQUIRED_CURRENT
    )
    assert PARKED_ALIAS not in strategy["memberships"]
    for initiative in strategy["initiatives"].values():
        assert initiative["status"] == "Active"
        assert initiative["lead_team"] is None
        assert initiative["owner"] is None
        assert initiative["target_date"] is None
        assert initiative["health"] is None
        assert initiative["labels"] == []
        assert initiative["parent_initiatives"] == []
    lip.validate_strategy(strategy, _project_plan(strategy))


@pytest.mark.parametrize(
    "revision",
    [
        "d004f5bf7953e943281dff7efd8fe17a54b0cf6c",
        "043d0c52ccd82edc11521c90c85dfd8d1b678a3e",
        "84d74cf9c7b81ba70169ab7df1f71835da2d297b",
        "0000000000000000000000000000000000000000",
    ],
)
def test_superseded_source_epoch_is_rejected(revision: str) -> None:
    strategy = _strategy()
    strategy["source_design"]["protected_revision"] = revision
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan())
    assert "strategy_source_design_invalid" in _codes(caught.value)


def test_temporal_grain_membership_is_required() -> None:
    strategy = _strategy()
    strategy["memberships"].pop(TEMPORAL_GRAIN, None)
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan(strategy))
    assert {
        "strategy_membership_count_mismatch",
        "strategy_current_membership_mismatch",
        "strategy_group_counts_mismatch",
    } <= _codes(caught.value)
    mismatch = _failure(caught.value, "strategy_current_membership_mismatch")
    assert mismatch["missing"] == [TEMPORAL_GRAIN]
    assert mismatch["unexpected"] == []


def test_temporal_grain_alternate_mapping_fails_closed() -> None:
    strategy = _strategy()
    strategy["memberships"][TEMPORAL_GRAIN] = (
        "canonical-intelligence-substrate-learning"
    )
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan(strategy))
    assert {
        "strategy_current_membership_mismatch",
        "strategy_group_counts_mismatch",
    } <= _codes(caught.value)
    mismatch = _failure(caught.value, "strategy_current_membership_mismatch")
    assert mismatch["missing"] == [TEMPORAL_GRAIN]
    assert mismatch["unexpected"] == []


def test_duplicate_temporal_grain_membership_row_fails_closed() -> None:
    strategy = _strategy()
    rows = [
        {"workstream_key": key, "initiative_key": initiative}
        for key, initiative in strategy["memberships"].items()
    ]
    rows.append(
        {
            "workstream_key": TEMPORAL_GRAIN,
            "initiative_key": TEMPORAL_GRAIN_INITIATIVE,
        }
    )
    strategy["memberships"] = rows
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan())
    assert "strategy_duplicate_membership" in _codes(caught.value)


def test_missing_other_current_membership_and_group_drift_fail_closed() -> None:
    strategy = _strategy()
    strategy["memberships"].pop("WS:CODE-INTELLIGENCE-FABRIC")
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan())
    assert {
        "strategy_membership_count_mismatch",
        "strategy_current_membership_mismatch",
        "strategy_group_counts_mismatch",
    } <= _codes(caught.value)


def test_parked_terminal_alias_cannot_replace_canonical_identity() -> None:
    strategy = _strategy()
    initiative = strategy["memberships"].pop("WS:TERMINAL-GITHUB-CANONICALIZATION")
    strategy["memberships"][PARKED_ALIAS] = initiative
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, _project_plan(strategy))
    assert {
        "strategy_parked_workstream_mapped",
        "strategy_current_membership_mismatch",
    } <= _codes(caught.value)


def test_new_unclassified_active_workstream_fails_closed() -> None:
    strategy = _strategy()
    project_plan = _project_plan(strategy)
    project_plan["active_projects"].append(_row("WS:UNCLASSIFIED-FUTURE"))
    with pytest.raises(lip.InitiativePlanError) as caught:
        lip.validate_strategy(strategy, project_plan)
    assert "strategy_unmapped_active_workstream" in _codes(caught.value)


def test_current_plan_and_receipt_are_deterministic_and_hash_bound() -> None:
    strategy = _strategy()
    project_plan = _project_plan(strategy)
    first, first_receipt = lip.compile_initiative_plan(
        project_plan=project_plan,
        strategy_path=STRATEGY,
    )
    second, second_receipt = lip.compile_initiative_plan(
        project_plan=copy.deepcopy(project_plan),
        strategy_path=STRATEGY,
    )
    assert lpp.semantic_json(first) == lpp.semantic_json(second)
    assert first_receipt == second_receipt
    assert first["summary"]["desired_initiatives"] == 7
    assert first["summary"]["desired_memberships"] == 63
    assert first["summary"]["unassigned_exceptions"] == 2
    assert first["summary"]["group_counts"] == EXPECTED_GROUP_COUNTS
    assert first_receipt["strategy_content_sha256"]
    assert first_receipt["desired_memberships_sha256"]


# ---------------------------------------------------------------------------
# Immutable membership evidence
# ---------------------------------------------------------------------------
#
# The relation between a Linear Project and its Initiative is proved by the
# immutable ``initiative_ids`` on the Project row.  ``initiative_names`` is
# PRESENTATION evidence: it shows which Initiative a Project is labelled with,
# but it cannot prove the membership relation itself.  A Project row that
# OMITS ``initiative_ids`` therefore carries UNKNOWN evidence — it certifies
# neither an intended membership nor a deliberate emptiness — and the compiler
# must refuse it through the existing hard-blocking
# ``membership_identity_conflict`` mechanism instead of compiling clean.

_MEMBERSHIP_MODES = ("omitted", "explicit", "correct")
_EXCEPTION_WORKSTREAM = "WS:WATCHLIST-PORTFOLIO-CEO"
_EXCEPTION_PROJECT_ID = "9aef6461-306a-4a3c-911b-c6a4b6635a78"


def _membership_snapshot(strategy: dict, mode: str) -> dict:
    """Build a current snapshot whose Project rows carry the requested evidence.

    ``omitted``  — matching ``initiative_names`` and NO ``initiative_ids`` key.
    ``explicit`` — ``initiative_ids: []`` (known empty membership).
    ``correct``  — the exact immutable ``initiative_ids`` plus the matching name.
    """
    if mode not in _MEMBERSHIP_MODES:
        raise ValueError(mode)
    names = {
        key: strategy["initiatives"][initiative]["name"]
        for key, initiative in strategy["memberships"].items()
    }
    ids = {
        key: f"init-{strategy['memberships'][key]}"
        for key in strategy["memberships"]
    }
    projects: list[dict] = []
    for key in sorted(strategy["memberships"]):
        row = {
            "workstream_key": key,
            "project_id": f"proj-{key}",
            "name": f"{key} project",
        }
        if mode == "omitted":
            row["initiative_names"] = [names[key]]
        elif mode == "explicit":
            row["initiative_ids"] = []
        else:
            row["initiative_ids"] = [ids[key]]
            row["initiative_names"] = [names[key]]
        projects.append(row)
    # The two deliberate unassigned exceptions stay unassigned by construction.
    projects.extend([
        {
            "workstream_key": _EXCEPTION_WORKSTREAM,
            "project_id": "proj-watchlist-portfolio-ceo",
            "name": "Watchlist portfolio compatibility redirect",
            "initiative_ids": [],
        },
        {
            "workstream_key": "WS:CANONICAL-PARENT-UNRESOLVED",
            "project_id": _EXCEPTION_PROJECT_ID,
            "name": "Canonical parent unresolved",
            "initiative_ids": [],
        },
    ])
    initiatives: list[dict] = []
    for key in sorted(strategy["initiatives"]):
        row = strategy["initiatives"][key]
        initiatives.append({
            "initiative_id": f"init-{key}",
            "name": row["name"],
            "status": row["status"],
            "priority": row["priority"],
            "owner_id": row["owner"],
            "lead_team": row["lead_team"],
            "target_date": row["target_date"],
            "labels": list(row["labels"]),
            "parent_initiative_ids": [],
            "health": row["health"],
        })
    return {
        "schema": "linear_initiative_snapshot.v1",
        "source": {"authority": "witness_only_not_canonical"},
        "initiatives": initiatives,
        "projects": projects,
    }


def _compile_with_snapshot(tmp_path, strategy: dict, mode: str):
    path = tmp_path / f"initiative_snapshot_{mode}.json"
    path.write_text(
        json.dumps(
            _membership_snapshot(strategy, mode),
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return lip.compile_initiative_plan(
        project_plan=_project_plan(strategy),
        strategy_path=STRATEGY,
        snapshot_path=path,
    )


def _drift_codes(plan: dict) -> list[str]:
    return [row["code"] for row in plan["drift"]]


def test_initiative_membership_evidence_helper_is_shared_by_the_facade() -> None:
    """The facade must delegate the SAME helper the legacy compiler runs."""
    assert lip._current_membership_evidence is _lip_legacy._current_membership_evidence
    assert lip.initiative_drift is _lip_legacy.initiative_drift
    assert _lip_legacy.validate_strategy is lip.validate_strategy

    id_to_name = {"init-autonomous-ai-organization": "Autonomous AI Organization"}

    omitted = lip._current_membership_evidence(
        {"initiative_names": ["Autonomous AI Organization"]},
        id_to_name,
    )
    assert omitted["initiative_ids"] == []
    assert omitted["issues"] == [{
        "code": "membership_identity_conflict",
        "reason": "initiative_ids_missing",
    }]

    explicit = lip._current_membership_evidence({"initiative_ids": []}, id_to_name)
    assert explicit == {"initiative_ids": [], "names": [], "issues": []}

    correct = lip._current_membership_evidence(
        {
            "initiative_ids": ["init-autonomous-ai-organization"],
            "initiative_names": ["Autonomous AI Organization"],
        },
        id_to_name,
    )
    assert correct == {
        "initiative_ids": ["init-autonomous-ai-organization"],
        "names": ["Autonomous AI Organization"],
        "issues": [],
    }


def test_initiative_membership_omitted_ids_is_unverified_and_hard_blocking(tmp_path) -> None:
    """Matching names without the immutable IDs must not compile clean."""
    strategy = _strategy()
    plan, receipt = _compile_with_snapshot(tmp_path, strategy, "omitted")

    assert receipt["snapshot_supplied"] is True
    codes = _drift_codes(plan)
    assert set(codes) == {"membership_identity_conflict"}
    assert len(plan["hard_blockers"]) == len(strategy["memberships"])
    assert {row["code"] for row in plan["hard_blockers"]} == {
        "membership_identity_conflict"
    }
    assert {row["reason"] for row in plan["hard_blockers"]} == {
        "initiative_ids_missing"
    }
    # Unknown evidence certifies NEITHER an intended membership NOR a
    # deliberate emptiness.
    assert "membership_missing" not in codes
    assert "membership_wrong" not in codes
    assert "membership_multi_parent" not in codes
    # The refusal names every Project whose evidence could not be verified.
    assert {row["workstream_key"] for row in plan["hard_blockers"]} == set(
        strategy["memberships"]
    )


def test_initiative_membership_explicit_empty_ids_is_known_empty(tmp_path) -> None:
    """``initiative_ids: []`` is known empty membership, not unknown evidence."""
    strategy = _strategy()
    plan, receipt = _compile_with_snapshot(tmp_path, strategy, "explicit")

    assert receipt["snapshot_supplied"] is True
    codes = _drift_codes(plan)
    assert set(codes) == {"membership_missing"}
    assert len(plan["drift"]) == len(strategy["memberships"])
    # Known-empty membership is an ordinary drift row, not an identity refusal.
    assert plan["hard_blockers"] == []
    assert {row["workstream_key"] for row in plan["drift"]} == set(
        strategy["memberships"]
    )


def test_initiative_membership_exact_id_and_name_is_a_valid_control(tmp_path) -> None:
    """Matching exact immutable ID and name is the valid control."""
    strategy = _strategy()
    plan, receipt = _compile_with_snapshot(tmp_path, strategy, "correct")

    assert receipt["snapshot_supplied"] is True
    assert plan["drift"] == []
    assert plan["hard_blockers"] == []
    assert plan["summary"]["desired_initiatives"] == 7
    assert plan["summary"]["desired_memberships"] == 63
    assert plan["summary"]["unassigned_exceptions"] == 2


def test_initiative_deliberate_exceptions_remain_unassigned(tmp_path) -> None:
    """The two deliberate exceptions stay unassigned in every evidence mode."""
    strategy = _strategy()
    for mode in _MEMBERSHIP_MODES:
        plan, _receipt = _compile_with_snapshot(tmp_path, strategy, mode)
        codes = _drift_codes(plan)
        assert "exception_has_forbidden_membership" not in codes
        assert "unmapped_visible_project" not in codes
        assert not [
            row for row in plan["drift"]
            if row.get("workstream_key") == _EXCEPTION_WORKSTREAM
            or row.get("project_id") == _EXCEPTION_PROJECT_ID
        ]
        assert plan["summary"]["unassigned_exceptions"] == 2


def test_initiative_offline_planning_needs_no_snapshot() -> None:
    """Offline desired-state planning stays valid without a live witness."""
    strategy = _strategy()
    plan, receipt = lip.compile_initiative_plan(
        project_plan=_project_plan(strategy),
        strategy_path=STRATEGY,
    )

    assert receipt["snapshot_supplied"] is False
    assert plan["drift"] == []
    assert plan["hard_blockers"] == []
    assert plan["summary"]["desired_initiatives"] == 7
    assert plan["summary"]["desired_memberships"] == 63
    assert plan["summary"]["unassigned_exceptions"] == 2
    assert plan["summary"]["group_counts"] == EXPECTED_GROUP_COUNTS
