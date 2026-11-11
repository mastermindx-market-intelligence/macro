"""The docs fast lane through build_plan: one narrow YES, every doubt a NO.

WHY THIS SUITE EXISTS.  A `docs fast lane` verdict selects ZERO legacy jobs, so
`has_work` goes false, `ci-pack` skips entirely and `ci-gate` publishes the
affirmative proven-no-work success that merges the PR (#4779: absence of red is
not a pass — the gate is the pass).  That makes the tier the same class of
decision as `select_jobs`' widening rules, and test_ci_pack.py's law applies
verbatim: a plan that wrongly proves no-work merges a completely unrun PR
green.  These tests therefore pin

  1. the ONE shape that admits the tier — a fully bound affirmative verdict on
     an active `pr_head` plan whose planner-resolved diff the verdict names by
     digest — and what that plan then looks like (zero legacy jobs, twelve
     empty packs, `has_work: false`, scope inference never paid for);
  2. EVERY other shape refusing back to the incumbent scoped selection, pinned
     by `plan_sha256` equality so "almost the same plan" cannot pass;
  3. the verdict FILE transport (`load_docs_tier_verdict` / `plan_from_workflow`)
     failing closed on absent, malformed, oversize, non-object and wrong-schema
     inputs exactly as the classifier's own error token does.

The verdict is produced by the DEFAULT-BRANCH copy of scripts/ci_docs_tier.py
(the ci-authority.yml shape); tests/test_ci_docs_tier.py pins that classifier,
and tests/test_ci_plan_workflow.py pins the workflow wiring that keeps the
planner reading it from trusted base code.

Run: python3 -m pytest tests/test_ci_pack_docs_tier.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"

# Own module object (not the package import) so monkeypatching never leaks into
# test_ci_pack.py's PACK; the name differs for the same reason.
SPEC = importlib.util.spec_from_file_location(
    "run_ci_pack_docs_tier", ROOT / "scripts" / "run_ci_pack.py"
)
assert SPEC and SPEC.loader
PACK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACK
SPEC.loader.exec_module(PACK)

from scripts.ci_docs_tier import SCHEMA as CLASSIFIER_SCHEMA  # noqa: E402

BASE = "b" * 40
MERGE = "a" * 40
SUBJECT = "c" * 40
DOCS_CHANGED = ["docs/NOTE.md", "research/PLAN_2026/ROOM.md"]


def _plan_job(job_id: str, ordinal: int, *, paths: tuple[str, ...] = ()) -> object:
    return PACK.LegacyJob(
        job_id=job_id,
        definition={"if": PACK.DISABLED_IF, "runs-on": "ubuntu-latest", "steps": []},
        ordinal=ordinal,
        weight=1,
        paths=paths,
    )


def _jobs() -> list[object]:
    """Unscoped always-on + a narrative over-claimer + an out-of-scope owner.

    This is the measured #10997 shape in miniature: one unscoped job and one
    job whose hand-written scope smears over `research/**/*.md` even though its
    suite reads no markdown.
    """
    return [
        _plan_job("always-on", 0),
        _plan_job("narrative-owner", 1, paths=("research/**/*.md",)),
        _plan_job("engine-owner", 2, paths=("engine/**",)),
    ]


def _verdict(**overrides: Any) -> dict[str, Any]:
    """A fully bound affirmative verdict for DOCS_CHANGED / (BASE, MERGE)."""
    verdict: dict[str, Any] = {
        "schema": PACK.DOCS_TIER_SCHEMA,
        "docs_tier": True,
        "reason": f"{len(DOCS_CHANGED)} inert narrative path(s)",
        "base_sha": BASE,
        "merge_sha": MERGE,
        "paths_sha256": PACK.changed_files_digest(DOCS_CHANGED),
        "paths_count": len(DOCS_CHANGED),
        "example_path": DOCS_CHANGED[0],
    }
    verdict.update(overrides)
    return verdict


def _identity() -> dict[str, Any]:
    return dict(
        changed_from=BASE,
        scope_mode="active",
        pack_count=12,
        event="pull_request",
        role="pr_head",
        tested_tree_sha=MERGE,
        subject_head_sha=SUBJECT,
        base_sha=BASE,
        workflow_run_id="42",
        workflow="ci",
    )


def _freeze_scope_inference(monkeypatch: pytest.MonkeyPatch) -> list[list[object]]:
    """Keep fixture scopes; record every call so skipped inference is provable."""
    calls: list[list[object]] = []

    def infer(jobs: list[object]) -> tuple[list[object], str]:
        calls.append(list(jobs))
        return list(jobs), "fixture scopes"

    monkeypatch.setattr(PACK, "infer_job_scopes", infer)
    return calls


def _plan(monkeypatch: pytest.MonkeyPatch, verdict: Any, **overrides: Any) -> Any:
    identity = _identity()
    identity.update(overrides)
    return PACK.build_plan(_jobs(), DOCS_CHANGED, docs_tier_verdict=verdict, **identity)


def _incumbent(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Any:
    return _plan(monkeypatch, None, **overrides)


@pytest.fixture(autouse=True)
def _isolate_planner_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CI_CHANGED_FILES_FILE",
        "CI_CHANGED_FILES_JSON",
        "CI_SCOPE_MODE",
        "CI_DYNAMIC_MATRIX_MODE",
        "GITHUB_EVENT_NAME",
        "CI_SEMANTIC_ROLE",
        "CI_TESTED_TREE_SHA",
        "CI_SUBJECT_HEAD_SHA",
        "CI_BASE_SHA",
    ):
        monkeypatch.delenv(name, raising=False)


# ─── the tier ──────────────────────────────────────────────────────────────────


def test_a_fully_bound_verdict_selects_zero_legacy_jobs_and_no_packs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _freeze_scope_inference(monkeypatch)
    plan = _plan(monkeypatch, _verdict())
    assert plan.eligible_job_ids == ()
    assert plan.skipped_job_ids == ("always-on", "narrative-owner", "engine-owner")
    assert plan.pack_jobs == ((),) * 12
    assert plan.nonempty_pack_indices == ()
    assert plan.has_work is False
    assert plan.matrix() == {"include": []}
    assert plan.semantic_jobs == ()
    assert plan.legacy_job_count == 3
    assert "docs fast lane" in plan.reason
    assert "2 inert narrative path(s)" in plan.reason
    assert plan.scope_summary == "scope inference skipped: docs fast lane"
    assert calls == [], "the tier must not pay for scope inference it cannot use"
    assert plan.authority_changed is False
    # The changed-file pin and plan hash stay first-class: packs still verify
    # the plan, and ci-gate still sees the exact diff the tier attested.
    assert plan.changed_files_sha256 == PACK.changed_files_digest(DOCS_CHANGED)
    assert plan.plan_sha256 != _incumbent(monkeypatch).plan_sha256
    assert plan.plan_sha256 == _plan(monkeypatch, _verdict()).plan_sha256


def test_the_tier_lands_in_plan_from_workflow_through_the_verdict_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The workflow transports the verdict as a FILE; this is that path end to end."""
    _freeze_scope_inference(monkeypatch)
    monkeypatch.setattr(PACK, "load_legacy_jobs", lambda path, gate=None: _jobs())
    monkeypatch.setattr(
        PACK, "resolve_changed_files", lambda changed_from, explicit_json=None, explicit_file=None: list(DOCS_CHANGED)
    )
    verdict_file = tmp_path / "verdict.json"
    verdict_file.write_text(json.dumps(_verdict()), encoding="utf-8")
    plan = PACK.plan_from_workflow(
        MANIFEST,
        changed_from=BASE,
        scope_mode="active",
        pack_count=12,
        event="pull_request",
        role="pr_head",
        tested_tree_sha=MERGE,
        subject_head_sha=SUBJECT,
        base_sha=BASE,
        docs_tier_file=verdict_file,
    )
    assert plan.eligible_job_ids == ()
    assert plan.has_work is False


# ─── every fail-closed arm, pinned by plan-hash equality ──────────────────────


@pytest.mark.parametrize(
    "tamper",
    [
        pytest.param(lambda v: None, id="no-verdict"),
        pytest.param(lambda v: {**v, "docs_tier": False}, id="negative-verdict"),
        pytest.param(
            lambda v: {**v, "docs_tier": False, "reason": "classifier-error: x"},
            id="classifier-error-token",
        ),
        pytest.param(
            lambda v: {k: value for k, value in v.items() if k != "docs_tier"},
            id="docs_tier-missing",
        ),
        pytest.param(lambda v: {**v, "schema": "ci.docs_tier.v0"}, id="wrong-schema"),
        pytest.param(lambda v: {**v, "base_sha": "f" * 40}, id="base-sha-mismatch"),
        pytest.param(lambda v: {**v, "merge_sha": "e" * 40}, id="merge-sha-mismatch"),
        pytest.param(
            lambda v: {**v, "paths_sha256": PACK.changed_files_digest(["docs/OTHER.md"])},
            id="paths-digest-mismatch",
        ),
        pytest.param(lambda v: {**v, "paths_count": 1}, id="paths-count-mismatch"),
        pytest.param(
            lambda v: {**v, "paths_sha256": PACK.changed_files_digest(["docs/ONE.md"])},
            id="digest-and-count-agree-on-a-different-list",
        ),
        pytest.param(lambda v: {**v, "paths_count": True}, id="paths-count-is-bool"),
        pytest.param(
            lambda v: {**v, "base_sha": ""}, id="empty-base-sha",
        ),
    ],
)
def test_any_binding_doubt_keeps_the_incumbent_scoped_plan(
    monkeypatch: pytest.MonkeyPatch, tamper
) -> None:
    _freeze_scope_inference(monkeypatch)
    incumbent = _incumbent(monkeypatch)
    assert incumbent.eligible_job_ids == ("always-on", "narrative-owner"), (
        "fixture sanity: the incumbent selection is the measured #10997 shape"
    )
    plan = _plan(monkeypatch, tamper(_verdict()))
    assert plan.plan_sha256 == incumbent.plan_sha256
    assert plan.eligible_job_ids == incumbent.eligible_job_ids
    assert plan.skipped_job_ids == incumbent.skipped_job_ids
    assert plan.pack_jobs == incumbent.pack_jobs
    assert plan.has_work is True
    assert "docs fast lane" not in plan.reason
    assert plan.scope_summary == "fixture scopes"


@pytest.mark.parametrize("mode", ["shadow", "off"])
def test_shadow_and_off_scope_modes_never_enter_the_tier(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Shadow/off exist to RUN the full suite while observing selection; a tier
    that emptied them would hide the very divergence those lanes measure."""
    _freeze_scope_inference(monkeypatch)
    incumbent = _incumbent(monkeypatch, scope_mode=mode)
    assert incumbent.eligible_job_ids == ("always-on", "narrative-owner", "engine-owner")
    plan = _plan(monkeypatch, _verdict(), scope_mode=mode)
    assert plan.plan_sha256 == incumbent.plan_sha256
    assert plan.has_work is True


def test_a_global_invalidator_next_to_the_markdown_refuses_the_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A workflow/script change in the SAME diff means job meanings changed; the
    tier may not silence the jobs it would redden."""
    _freeze_scope_inference(monkeypatch)
    changed = ["docs/NOTE.md", "scripts/run_ci_pack.py"]
    identity = _identity()
    incumbent = PACK.build_plan(_jobs(), changed, docs_tier_verdict=None, **identity)
    assert incumbent.eligible_job_ids == ("always-on", "narrative-owner", "engine-owner")
    verdict = _verdict(
        paths_sha256=PACK.changed_files_digest(changed), paths_count=len(changed)
    )
    plan = PACK.build_plan(_jobs(), changed, docs_tier_verdict=verdict, **identity)
    assert plan.plan_sha256 == incumbent.plan_sha256


def test_a_manifest_delta_refuses_the_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editing .github/ci/legacy-jobs.yml changes what selection MEANS; the
    manifest's own job set must run, not a zero-job tier."""
    _freeze_scope_inference(monkeypatch)
    identity = _identity()
    incumbent = PACK.build_plan(
        _jobs(), DOCS_CHANGED, docs_tier_verdict=None, manifest_changed_job_ids=("demo",), **identity
    )
    plan = PACK.build_plan(
        _jobs(), DOCS_CHANGED, docs_tier_verdict=_verdict(), manifest_changed_job_ids=("demo",), **identity
    )
    assert plan.plan_sha256 == incumbent.plan_sha256
    assert "docs fast lane" not in plan.reason


def test_role_and_inventory_arms_refuse_the_gate_purely() -> None:
    """Arms that cannot coexist with a valid plan are pinned at the gate itself."""
    verdict = _verdict()
    common = dict(
        changed=DOCS_CHANGED,
        changed_from=BASE,
        tested_tree_sha=MERGE,
        base_sha=BASE,
        scope_mode="active",
        role="pr_head",
        invalidated=False,
        manifest_changed_job_ids=None,
    )
    assert PACK.docs_tier_eligible(verdict, **common) is True
    for overrides in (
        dict(role="main"),
        dict(scope_mode="shadow"),
        dict(scope_mode="off"),
        dict(changed=None),
        dict(changed=[]),
        dict(changed_from=None),
        dict(changed_from="f" * 40),
        dict(invalidated=True),
        dict(manifest_changed_job_ids=("demo",)),
    ):
        assert PACK.docs_tier_eligible(verdict, **{**common, **overrides}) is False, overrides
    assert PACK.docs_tier_eligible(None, **common) is False


def test_a_single_path_verdict_with_a_bool_count_is_refused() -> None:
    """``True == 1`` in Python; the gate must not mistake it for ``paths_count: 1``."""
    changed = ["docs/ONLY.md"]
    verdict = _verdict(
        paths_sha256=PACK.changed_files_digest(changed), paths_count=True
    )
    assert PACK.docs_tier_eligible(
        verdict,
        changed=changed,
        changed_from=BASE,
        tested_tree_sha=MERGE,
        base_sha=BASE,
        scope_mode="active",
        role="pr_head",
        invalidated=False,
        manifest_changed_job_ids=None,
    ) is False


# ─── the verdict-file transport ────────────────────────────────────────────────


def _valid_verdict_file(tmp_path: Path, name: str = "verdict.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(_verdict()), encoding="utf-8")
    return path


def test_load_docs_tier_verdict_parses_a_bound_verdict(tmp_path: Path) -> None:
    loaded = PACK.load_docs_tier_verdict(_valid_verdict_file(tmp_path))
    assert loaded == _verdict()
    assert PACK.DOCS_TIER_SCHEMA == CLASSIFIER_SCHEMA


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="absent-file"),
        pytest.param("not json {", id="malformed-json"),
        pytest.param("[1, 2]", id="json-array"),
        pytest.param('"a string"', id="json-string"),
        pytest.param("null", id="json-null"),
        pytest.param(json.dumps({"schema": "ci.docs_tier.v0"}), id="wrong-schema"),
        pytest.param(json.dumps({"docs_tier": True}), id="schema-missing"),
    ],
)
def test_load_docs_tier_verdict_fails_closed_on_transport_defects(
    tmp_path: Path, payload: str | None
) -> None:
    if payload is None:
        path = tmp_path / "absent.json"
    else:
        path = tmp_path / "verdict.json"
        path.write_text(payload, encoding="utf-8")
    assert PACK.load_docs_tier_verdict(path) is None


def test_oversize_verdict_file_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "verdict.json"
    verdict = _verdict()
    verdict["reason"] = "x" * 70_000  # over the 65,536-byte transport bound
    path.write_text(json.dumps(verdict), encoding="utf-8")
    assert PACK.load_docs_tier_verdict(path) is None


def test_an_unreadable_verdict_file_never_reaches_the_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A verdict path whose file is absent is the `set +e` fallback shape: the
    classifier step writes a token, but if even that failed the planner must
    still plan — on the incumbent selection."""
    _freeze_scope_inference(monkeypatch)
    monkeypatch.setattr(PACK, "load_legacy_jobs", lambda path, gate=None: _jobs())
    monkeypatch.setattr(
        PACK, "resolve_changed_files", lambda changed_from, explicit_json=None, explicit_file=None: list(DOCS_CHANGED)
    )
    plan = PACK.plan_from_workflow(
        MANIFEST,
        changed_from=BASE,
        scope_mode="active",
        pack_count=12,
        event="pull_request",
        role="pr_head",
        tested_tree_sha=MERGE,
        subject_head_sha=SUBJECT,
        base_sha=BASE,
        docs_tier_file=tmp_path / "never-written.json",
    )
    assert plan.eligible_job_ids == ("always-on", "narrative-owner")
    assert plan.has_work is True
