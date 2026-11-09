"""tests/test_build_active_build_map.py — Unit tests for build_active_build_map.py.

Tests
-----
1. collision_basic                 — two PRs sharing files produce a collision record.
2. collision_no_match              — PRs with disjoint files produce no collision.
3. collision_sort_order            — pairs sorted by shared_count descending.
4. collision_protected_flag        — any_protected set when a shared file matches a glob.
5. collision_empty_files           — PRs with no files list are skipped silently.
6. protected_path_workflow         — .github/workflows/daily.yml matches protected globs.
7. protected_path_check_star       — scripts/check_dag_conformance.py matches check_*.py glob.
8. protected_path_neuralweb        — engine/neuralweb/foo.py matches engine/neuralweb/** glob.
9. protected_path_no_match         — a plain scripts/build_foo.py does NOT match.
10. render_section_headers          — render_markdown output contains all required H2 sections.
11. render_conflicting_flag         — CONFLICTING shown for merge_state==DIRTY.
12. render_truncation               — shared_files list > 8 items is truncated with "+N more".
13. render_draft_flag               — DRAFT flag appears for is_draft=True PR.
14. render_protected_count          — protected:N shown when protected_paths_touched is non-empty.
15. render_no_gh_invocation         — none of the pure functions call subprocess (no gh access).
16. render_merged_truncated_note    — truncation annotation in merged section header when flag set.
17. render_files_error_flag         — files:error flag shown and footnote present for files_error PR.
18. render_files_truncated_distinct — files_truncated renders "files-truncated", NOT "files:error".
19. render_unknown_mergeability     — UNKNOWN annotation line rendered when PRs remain UNKNOWN.
20. render_no_unknown_annotation    — UNKNOWN line absent when all PRs resolved.
21. collect_null_files_typed_error  — explicit GitHub files:null degrades one PR without crashing.
22. open_pr_set_above_old_cap       — a >cap open-PR set enumerates fully, truncated False.
23. open_pr_fetch_at_the_ceiling    — exactly-at-limit is the honest truncated sentinel.
24. merged_window_above_old_cap     — a >cap merged window enumerates fully across pages.
25. merged_page_failure_partial     — a mid-sweep page failure keeps partial rows, flags truncated.
26. merged_runaway_guard            — exhausting the page guard flags truncated.
27. pre_filter_truncation_survives  — the exact-cutoff filter must not clear the flag.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_active_build_map import (
    _collect_open_prs,
    _collect_pr_files,
    _collect_recent_merged,
    build_map,
    compute_collisions,
    is_protected_path,
    protected_paths_for_pr,
    render_markdown,
    PROTECTED_GLOBS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pr(
    number: int,
    files: list[str],
    title: str = "Test PR",
    head_ref: str = "feat/test",
    is_draft: bool = False,
    merge_state: str = "CLEAN",
    merge_state_raw: str | None = "CLEAN",
    files_truncated: bool = False,
    files_error: bool = False,
    protected_paths_touched: list[str] | None = None,
    updated_at: str = "2026-07-01T00:00:00Z",
) -> dict:
    return {
        "number": number,
        "title": title,
        "head_ref": head_ref,
        "updated_at": updated_at,
        "is_draft": is_draft,
        "merge_state": merge_state,
        "merge_state_raw": merge_state_raw,
        "files_count": len(files),
        "files_truncated": files_truncated,
        "files_error": files_error,
        "files": files,
        "protected_paths_touched": protected_paths_touched if protected_paths_touched is not None else [],
    }


# ---------------------------------------------------------------------------
# 1-5: Collision computation
# ---------------------------------------------------------------------------

def test_collision_basic():
    pr1 = _make_pr(1, ["engine/foo.py", "site/bar.html"])
    pr2 = _make_pr(2, ["engine/foo.py", "site/other.html"])
    cols = compute_collisions([pr1, pr2])
    assert len(cols) == 1
    col = cols[0]
    assert col["pr_a"] == 1
    assert col["pr_b"] == 2
    assert "engine/foo.py" in col["shared_files"]
    assert col["shared_count"] == 1


def test_collision_no_match():
    pr1 = _make_pr(1, ["engine/foo.py"])
    pr2 = _make_pr(2, ["engine/bar.py"])
    cols = compute_collisions([pr1, pr2])
    assert cols == []


def test_collision_sort_order():
    pr1 = _make_pr(1, ["a.py", "b.py", "c.py"])
    pr2 = _make_pr(2, ["a.py", "b.py", "c.py"])  # 3 shared with pr1
    pr3 = _make_pr(3, ["a.py"])                    # 1 shared with pr1
    cols = compute_collisions([pr1, pr2, pr3])
    # pair (1,2) has 3 shared, pair (1,3) has 1 shared — sorted desc
    assert cols[0]["shared_count"] >= cols[-1]["shared_count"]
    assert cols[0]["pr_a"] == 1 and cols[0]["pr_b"] == 2


def test_collision_protected_flag():
    pr1 = _make_pr(1, [".github/workflows/daily.yml", "scripts/foo.py"])
    pr2 = _make_pr(2, [".github/workflows/daily.yml", "engine/bar.py"])
    cols = compute_collisions([pr1, pr2])
    assert len(cols) == 1
    assert cols[0]["any_protected"] is True


def test_collision_empty_files():
    pr1 = _make_pr(1, [])
    pr2 = _make_pr(2, ["engine/foo.py"])
    cols = compute_collisions([pr1, pr2])
    assert cols == []


# ---------------------------------------------------------------------------
# 6-9: Protected-path glob matching
# ---------------------------------------------------------------------------

def test_protected_path_workflow():
    assert is_protected_path(".github/workflows/daily.yml") is True
    assert is_protected_path(".github/workflows/render.yml") is True


def test_protected_path_check_star():
    assert is_protected_path("scripts/check_dag_conformance.py") is True
    assert is_protected_path("scripts/check_synapse_registry.py") is True
    assert is_protected_path("scripts/check_validated_claims.py") is True


def test_protected_path_neuralweb():
    assert is_protected_path("engine/neuralweb/factor_contradictions.py") is True
    assert is_protected_path("engine/neuralweb/kernel.py") is True


def test_protected_path_no_match():
    assert is_protected_path("scripts/build_sector_central.py") is False
    assert is_protected_path("site/macro.html") is False
    assert is_protected_path("engine/alert_triage.py") is False


# ---------------------------------------------------------------------------
# 10-14: Markdown rendering
# ---------------------------------------------------------------------------

def _fixture_payload(
    open_prs: list[dict] | None = None,
    recent_merged: list[dict] | None = None,
    collisions: list[dict] | None = None,
    merged_truncated: bool = False,
) -> dict:
    if open_prs is None:
        open_prs = []
    if recent_merged is None:
        recent_merged = []
    if collisions is None:
        collisions = []
    return {
        "schema": "active_builds.v1",
        "generated_at": "2026-07-06T12:00:00+00:00",
        "base": {"sha": "abc123def"},
        "merged_days": 14,
        "merged_truncated": merged_truncated,
        "open_prs": open_prs,
        "collisions": collisions,
        "recent_merged": recent_merged,
    }


def test_render_section_headers():
    md = render_markdown(_fixture_payload())
    assert "## Open PRs" in md
    assert "## File Collisions" in md
    assert "## Recently Merged" in md
    # Advisory header present
    assert "Advisory only" in md
    # Footer present
    assert "DO_NOT_REBUILD.md" in md


def test_render_conflicting_flag():
    pr = _make_pr(99, ["engine/foo.py"], merge_state="DIRTY", title="Conflicting PR")
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "CONFLICTING" in md
    assert "#99" in md


def test_render_truncation():
    # Build a collision record with 10 shared files
    files = [f"engine/mod_{i}.py" for i in range(10)]
    pr1 = _make_pr(1, files)
    pr2 = _make_pr(2, files)
    cols = compute_collisions([pr1, pr2])
    payload = _fixture_payload(open_prs=[pr1, pr2], collisions=cols)
    md = render_markdown(payload)
    # 10 files, max 8 shown → "+2 more" should appear
    assert "+2 more" in md


def test_render_draft_flag():
    pr = _make_pr(42, ["scripts/foo.py"], is_draft=True, title="Draft work")
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "DRAFT" in md
    assert "#42" in md


def test_render_protected_count():
    pr = _make_pr(
        7,
        ["config/dag.yml", "engine/validation.py"],
        protected_paths_touched=["config/dag.yml", "engine/validation.py"],
        title="Protected path PR",
    )
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "protected:2" in md


# ---------------------------------------------------------------------------
# 15: No subprocess calls in pure functions
# ---------------------------------------------------------------------------

def test_no_gh_invocation_in_pure_functions():
    """Pure functions must not call subprocess — no gh access in tests."""
    with mock.patch("subprocess.run") as mock_run:
        pr1 = _make_pr(1, ["engine/foo.py"])
        pr2 = _make_pr(2, ["engine/foo.py"])
        compute_collisions([pr1, pr2])
        is_protected_path("scripts/check_dag_conformance.py")
        protected_paths_for_pr(pr1)
        render_markdown(_fixture_payload(open_prs=[pr1, pr2]))
        # subprocess.run must never have been called
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# 16-20: New fix tests (FIX 1-3 coverage)
# ---------------------------------------------------------------------------

def test_render_merged_truncated_note():
    """FIX 1: section header carries truncation annotation when merged_truncated=True."""
    payload = _fixture_payload(
        recent_merged=[{"number": 1, "title": "PR one", "merged_at": "2026-07-01T00:00:00Z"}],
        merged_truncated=True,
    )
    md = render_markdown(payload)
    assert "window truncated" in md
    assert "most recent 500" not in md, "the note must not name a cap the sweep no longer uses"


def test_render_no_merged_truncated_note_when_false():
    """FIX 1: no truncation annotation when merged_truncated=False (default)."""
    payload = _fixture_payload(
        recent_merged=[{"number": 1, "title": "PR one", "merged_at": "2026-07-01T00:00:00Z"}],
        merged_truncated=False,
    )
    md = render_markdown(payload)
    assert "window truncated" not in md


def test_render_files_error_flag():
    """FIX 3: files_error PR renders 'files:error' flag and footnote."""
    pr = _make_pr(55, [], title="Error PR", files_error=True, files_truncated=False)
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "files:error" in md
    # Footnote about unknown collisions must also appear
    assert "collision data for those PRs is unknown" in md


def test_render_files_truncated_distinct():
    """FIX 3: files_truncated renders 'files-truncated' NOT 'files:error', no footnote."""
    pr = _make_pr(56, ["a.py"] * 100, title="Truncated PR", files_error=False, files_truncated=True)
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "files-truncated" in md
    assert "files:error" not in md
    assert "collision data for those PRs is unknown" not in md


def test_render_unknown_mergeability():
    """FIX 2: UNKNOWN annotation line appears when PRs remain UNKNOWN after per-PR view."""
    pr = _make_pr(
        77,
        ["engine/foo.py"],
        merge_state="UNKNOWN",
        merge_state_raw="UNKNOWN",
        title="Unknown merge state",
    )
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "mergeability not yet computed by GitHub (UNKNOWN)" in md
    assert "1 of 1 PRs" in md


def test_render_no_unknown_annotation():
    """FIX 2: UNKNOWN annotation line absent when all PRs resolved to non-UNKNOWN."""
    pr = _make_pr(
        78,
        ["engine/foo.py"],
        merge_state="CLEAN",
        merge_state_raw="CLEAN",
        title="Clean merge state",
    )
    payload = _fixture_payload(open_prs=[pr])
    md = render_markdown(payload)
    assert "mergeability not yet computed by GitHub" not in md


# ---------------------------------------------------------------------------
# 21: Nullable GitHub file-list boundary regression
# ---------------------------------------------------------------------------

def test_collect_pr_files_treats_null_files_as_typed_error():
    """An explicit files:null response degrades one PR instead of crashing the map."""
    response = {"files": None, "mergeStateStatus": "UNKNOWN"}

    with mock.patch("scripts.build_active_build_map._run_gh", return_value=response):
        result = _collect_pr_files(123)

    assert result == ([], False, True, "UNKNOWN")


# ---------------------------------------------------------------------------
# 22-27: fetch coverage — a cap must never silently shrink the join
# ---------------------------------------------------------------------------

def _stamp(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _gh_open_row(number: int, days_ago: float = 0.5) -> dict:
    """One row as ``gh pr list --state open --json …`` renders it."""
    return {
        "number": number,
        "title": f"PR {number}",
        "headRefName": f"lane/{number}",
        "updatedAt": _stamp(days_ago),
        "isDraft": False,
        "mergeStateStatus": "CLEAN",
    }


def _rest_row(
    number: int, merged_days_ago: float = 1.0, updated_days_ago: float | None = None
) -> dict:
    """One row as the REST pulls list renders it (snake_case, ISO-Z)."""
    updated = merged_days_ago if updated_days_ago is None else updated_days_ago
    return {
        "number": number,
        "title": f"merged {number}",
        "merged_at": _stamp(merged_days_ago),
        "updated_at": _stamp(updated),
    }


def _fake_gh(open_rows, merged_pages, repo: str = "owner/repo"):
    """Stand-in for ``_run_gh``: open list, repo view, REST pages, per-PR view.

    A ``None`` entry in *merged_pages* simulates a page whose fetch failed.
    """
    calls: list[list[str]] = []

    def runner(args, timeout=30):
        calls.append(list(args))
        if args[:2] == ["repo", "view"]:
            return {"nameWithOwner": repo}
        if args[:2] == ["pr", "list"]:
            return open_rows
        if args[0] == "api":
            page = int(re.search(r"[?&]page=(\d+)", args[1]).group(1))
            return merged_pages[page - 1] if page <= len(merged_pages) else []
        if args[:2] == ["pr", "view"]:
            return {"files": [], "mergeStateStatus": "CLEAN"}
        raise AssertionError(f"unexpected gh call: {args}")

    runner.calls = calls
    return runner


def test_open_pr_set_above_the_old_cap_enumerates_fully():
    """>100 open PRs is the live shape (560 measured): every one must reach the map."""
    open_rows = [_gh_open_row(n) for n in range(1, 251)]
    pages = [[_rest_row(n) for n in range(9000, 9010)]]

    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh(open_rows, pages)):
        payload = build_map(merged_days=14)

    assert len(payload["open_prs"]) == 250
    assert payload["open_prs_truncated"] is False
    assert payload["merged_truncated"] is False
    assert [pr["number"] for pr in payload["open_prs"]] == list(range(1, 251))


def test_open_pr_fetch_at_the_ceiling_is_flagged_truncated():
    """Exactly-at-the-limit cannot be proven complete, so the flag must be honest."""
    from scripts.build_active_build_map import _OPEN_PR_FETCH_LIMIT

    open_rows = [_gh_open_row(n) for n in range(1, _OPEN_PR_FETCH_LIMIT + 1)]
    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh(open_rows, [[]])):
        prs, truncated = _collect_open_prs()

    assert len(prs) == _OPEN_PR_FETCH_LIMIT
    assert truncated is True


def test_merged_window_above_the_old_cap_enumerates_fully():
    """>500 merged in the window: every page is walked, the short last page ends the sweep."""
    pages = [
        [_rest_row(n) for n in range(100, 200)],
        [_rest_row(n) for n in range(200, 300)],
        [_rest_row(n) for n in range(300, 350)],
    ]
    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh([_gh_open_row(1)], pages)):
        recent, truncated = _collect_recent_merged(14)

    assert truncated is False
    assert len(recent) == 250
    assert recent[0]["merged_at"].endswith("Z"), "artifact keeps gh's ISO-Z convention"
    assert set(recent[0]) == {"number", "title", "merged_at"}, "entry shape unchanged"


def test_merged_page_failure_keeps_partial_rows_and_flags_truncated():
    """A page we could not read ends the sweep: partial rows survive, the flag says so."""
    pages = [[_rest_row(n) for n in range(100, 200)], None]
    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh([_gh_open_row(1)], pages)):
        recent, truncated = _collect_recent_merged(14)

    assert truncated is True
    assert len(recent) == 100, "rows already fetched must survive a later page failure"


def test_merged_runaway_guard_flags_truncated(monkeypatch):
    """Exhausting the page guard is not proof of coverage, so it must set the flag."""
    monkeypatch.setattr("scripts.build_active_build_map._MERGED_MAX_PAGES", 2)
    pages = [
        [_rest_row(n) for n in range(100, 200)],
        [_rest_row(n) for n in range(200, 300)],
    ]
    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh([_gh_open_row(1)], pages)):
        recent, truncated = _collect_recent_merged(14)

    assert truncated is True
    assert len(recent) == 200


def test_pre_filter_truncation_survives_the_cutoff_filter(monkeypatch):
    """The flag is fetch arithmetic, never the filtered length.

    The live artifact carried 496 rows with the flag set while the cap was 500: a
    post-filter rewrite would have cleared a true truncation.
    """
    monkeypatch.setattr("scripts.build_active_build_map._MERGED_FETCH_LIMIT", 150)
    pages = [
        [_rest_row(n) for n in range(100, 200)],
        # Updated inside the window (so the stop condition cannot fire) but MERGED
        # outside it: the exact-cutoff filter drops these only after the ceiling was hit.
        [_rest_row(n, merged_days_ago=30, updated_days_ago=1) for n in range(300, 400)],
    ]
    with mock.patch("scripts.build_active_build_map._run_gh",
                    side_effect=_fake_gh([_gh_open_row(1)], pages)):
        recent, truncated = _collect_recent_merged(14)

    assert len(recent) == 100, "the cutoff filter still trims the out-of-window rows"
    assert truncated is True, "a shorter filtered list must not clear the truncation flag"
