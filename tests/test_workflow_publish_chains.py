"""Workflow-shape pins for the lanes that commit rendered ``site/`` pages to main.

Home: ``public-render-fastlane`` (``.github/ci/legacy-jobs.yml``, ``gate: code``,
minimal deps ``pytest pyyaml jinja2``) — the job every PR pack actually runs.
These pins used to live next to their engines (``tests/test_sector_intelligence_page.py``
runs only inside ``express-render-guards``, ``tests/test_uk_policy_brain.py`` only inside
``outcome-spine``; both are ``gate: data`` jobs that never run in a PR pack), so a
regression on the workflow text passed contract-delta while gating nothing.
Seat ruling 2026-09-23 (Meta-CEO A, PR #7758): workflow-shape tests belong in a
``gate: code`` job, and this file is their home.

Pure text checks — no engine import, no network, no ``site/``/``data/`` bytes.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTOR_WORKFLOW = ROOT / ".github" / "workflows" / "sector-intelligence.yml"
WHITEHOUSE_WORKFLOW = ROOT / ".github" / "workflows" / "whitehouse-sentinel.yml"

CHAIN = (
    "python -m scripts.inject_data_base",
    "python -m scripts.externalize_css",
    "python -m scripts.optimize_assets",
)


def _step(src: str, *, name: str | None = None, containing: str | None = None) -> str:
    """Return the ``- name:`` chunk selected by exact step name or by a contained token."""
    assert (name is None) != (containing is None), "select by name OR by token"
    for chunk in src.split("- name:"):
        lines = chunk.splitlines()
        if not lines:
            continue
        if name is not None and lines[0].strip() == name:
            return chunk
        if containing is not None and containing in chunk:
            return chunk
    raise AssertionError(f"no step selected by name={name!r} containing={containing!r}")


def _assert_externalize_chain_precedes_staging(step: str, *, stage_marker: str) -> None:
    """shim -> externalize -> stamp strictly before the first ``git add`` of pages,
    every pass non-fatal (``||`` on the same line), and the content-hashed assets the
    pages now link staged AFTER the page ``git add`` with ``--ignore-removal``."""
    positions = [step.index(needle) for needle in CHAIN]
    pos_git_add = step.index(stage_marker)
    assert positions == sorted(positions) and positions[-1] < pos_git_add, (
        "shim/externalize/stamp chain must run in order and BEFORE the page git add; "
        f"got chain={positions} git_add={pos_git_add}"
    )
    for needle in CHAIN:
        line = next((ln for ln in step.splitlines() if needle in ln), None)
        assert line is not None, f"line containing {needle!r} missing"
        assert "||" in line, (
            f"{needle!r} must stay non-fatal under set -e (`|| echo ...` on the same line); "
            f"got: {line!r}"
        )
    for asset_dir in ("site/assets/css", "site/assets/js"):
        pos_asset = step.index(f"git add --ignore-removal {asset_dir}")
        assert pos_git_add < pos_asset, (
            f"content-hashed {asset_dir} must be staged AFTER the page git add"
        )


def test_sector_publish_step_runs_externalize_chain_before_staging_site_pages() -> None:
    """MO-A heal 2026-09-23 (#7758): sector-intelligence's ``publish scoped generation
    to main`` step MUST run the shim/externalize/stamp chain BEFORE staging ``site/``
    pages, otherwise the lane commits RAW pages (inline <style>, no
    ``assets/css/<hash>.css`` ref, stale ``?v=``) and every PR merge-ref reds
    ci-pack-11 (``test_basket_detail_glance_copy`` fingerprint guard) until the next
    render-public re-stamp. Whitehouse-sentinel's ``commit + push (only on change)``
    step (P0 2026-08-04, 9a997e9da3f) is the canonical cure this mirrors.
    """
    src = SECTOR_WORKFLOW.read_text(encoding="utf-8")
    step = _step(src, name="publish scoped generation to main")
    _assert_externalize_chain_precedes_staging(step, stage_marker="git add -- \\")
    # The staged site paths must still cover the published surface (basket + sectors).
    assert "site/basket" in step
    assert "site/sectors" in step
    assert "git add site/" not in step, "targeted lane must never stage the whole site"


def test_whitehouse_sentinel_keeps_the_canonical_externalize_chain() -> None:
    """The sector heal copies whitehouse-sentinel's chain; if the original ever loses
    it, the copy's rationale is gone too. Pin the source of truth in the same job."""
    src = WHITEHOUSE_WORKFLOW.read_text(encoding="utf-8")
    step = _step(src, name="commit + push (only on change)")
    _assert_externalize_chain_precedes_staging(step, stage_marker="git add data/ai_costs")


def test_whitehouse_sentinel_activates_the_uk_policy_desk_and_stages_its_artifacts() -> None:
    """MO-PAID-023 (#7351, merged 2026-09-23): the already-shipped UK policy desk is
    activated on the credentialed whitehouse sentinel via ``UK_POLICY_DESK_ENABLED``
    set in the desk step's env (before its ``run``), and the commit step stages the
    desk's artifacts with ``--ignore-removal`` on their own lines (``git add a b``
    exits 128 when either pathspec matches nothing). The engine-side suite
    (``tests/test_uk_policy_brain.py``) runs only in a ``gate: data`` job, so this is
    the PR-gating pin for the activation itself.
    """
    src = WHITEHOUSE_WORKFLOW.read_text(encoding="utf-8")
    desk = _step(src, containing="python -m scripts.build_whitehouse")
    pos_flag = desk.index('UK_POLICY_DESK_ENABLED: "1"')
    pos_run = desk.index("python -m scripts.build_whitehouse")
    assert pos_flag < pos_run, "the activation flag must sit in the desk step's env"

    commit = _step(src, name="commit + push (only on change)")
    pos_pages = commit.index("git add data/ai_costs")
    for pathspec in ("data/uk_policy", "site/uk_policy.json"):
        line = f"git add --ignore-removal {pathspec}"
        assert line in commit, f"{line!r} missing from the commit step"
        assert pos_pages < commit.index(line), f"{pathspec} must be staged with the page set"
