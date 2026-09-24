## Finance T9 — entry points only

Lane `fin_t9_entries` · operation `gmi-finance-fable-ceo-e2e-20260924-chairman-001` · carrier PR #7887.

Two entry points into the Finance Intelligence dossier. Both are **link only** — no theme semantics, no stage, no rank, no score. Both reuse the host page's existing card idiom so a reader sees each entry point as a peer of the modules above it. No new stylesheet, no inline `<style>` block.

**Head SHA:** `90a9a30ff5fc1be69db03dc4e643d1106270de8e`

---

### Files changed (6)

```
 .github/ci/legacy-jobs.yml                   |  25 ++-
 templates/_finance_financials_launch.html.j2 |  19 ++
 templates/_finance_sector_deep_dive.html.j2  |  25 +++
 templates/state_of_themes.html.j2            |   3 +
 tests/test_finance_entry_points.py           | 296 +++++++++++++++++++++++++++
 tests/test_state_of_themes.py                |   5 +
 6 files changed, 371 insertions(+), 2 deletions(-)
```

- **NEW** `templates/_finance_sector_deep_dive.html.j2` — sector deep-dive card on the Theme Tracker (outside the canonical lanes, in a NEW region "Sector deep dives / 行业深度")
- **NEW** `templates/_finance_financials_launch.html.j2` — launch module for the Financials basket detail page (skip-mode safe; guarded include lands AFTER PR #7669 merges)
- **MOD** `templates/state_of_themes.html.j2` — single additive `{% include "_finance_sector_deep_dive.html.j2" %}` between the lanes-loop close anchor and the STUDY SHELF section header (3-line hunk)
- **MOD** `tests/test_state_of_themes.py` — adds `_finance_sector_deep_dive.html.j2` to `_SUPPORT_PARTIALS` so synthetic-root renders can satisfy the include (5-line hunk)
- **NEW** `tests/test_finance_entry_points.py` — 12 explicit assertions + 1 skip-mode for the basket-detail integration
- **MOD** `.github/ci/legacy-jobs.yml` — `finance-intelligence` job paths/run command extended for FIN-T9 + import closure widening per `test_curated_exclusive_scopes_cover_their_own_import_closure`

**NOT touched (per spec):**
- `templates/basket_detail.html.j2` — UNCHANGED while PR #7669 is OPEN; the basket-detail integration tests `pytest.skip("BLOCKED_BY_OWNER #7669")`.

---

### Test commands and validator results

Running locally from the lane worktree:

```
$ python -m pytest tests/test_finance_entry_points.py -q
..........s..                                                              [100%]
12 passed, 1 skipped in 2.69s

$ python -m pytest tests/test_state_of_themes.py -q
1 failed, 52 passed, 11 skipped in 44.13s
  ↳ The 1 failure is test_check_validated_claims — 75 UNEARNED 'validated'
    claims in templates I did NOT touch (_debt_maturity.html.j2,
    _macro_suite_shell.html.j2, macro_*.html.j2, hk.html.j2, ...).
    Grep of 'validated' against my two partials returns zero matches —
    pre-existing on origin/main; not a FIN-T9 regression.

$ python -m pytest tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure -q
.                                                                        [100%]
1 passed in 192.98s   ← GREEN after import-closure widening

$ python3 scripts/check_design_system.py --mode enforce-added --diff-file -
::notice title=design-system::R0 enforce-added: 0 blocking finding(s)
design-system ratchet — mode=enforce-added blocking=0

$ python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only
Validated 230 legacy jobs; 230 in scope (full suite: changed-file set unavailable); pack weights=[860, 672, 672, 671, 671, 671, 673, 671, 671, 672, 672, 672]; selected pack 0 (1 jobs).
Selected jobs: engine-render-guards
```

Run command in the `finance-intelligence` CI job:
```
python -m pytest tests/test_finance_intelligence_contract.py tests/test_finance_overlap.py tests/test_finance_intelligence_projection.py tests/test_finance_entry_points.py -q
```

---

### CI status

Not run from this lane (lane does not own the merge or CI levers). The CI pipeline will pick up the head SHA and run the configured gates after this PR is marked ready. Reviewers: do not block on green for the basket-detail test — that lands in the follow-up once PR #7669 merges.

---

### FROZEN-SPEC compliance

| Spec field              | Result |
|-------------------------|--------|
| C0 gate (PR #7669 OPEN, files exist on main) | ✅ satisfied |
| Sector deep-dive partial (link-only, no banned words, l-en/l-zh pair, single `<a>`) | ✅ all 4 assertions |
| Financials launch partial (skipped while #7669 OPEN) | ✅ 4 standalone + 1 skip |
| Tracker live render: canonical theme count unchanged, "Finance Intelligence" only in new region | ✅ both assertions |
| Include position is between lanes-loop close and study-shelf anchor | ✅ by string index |
| CI extension: paths + run command + closure widening | ✅ |
| NOT DONE UNLESS met | ✅ |
| Commit, push to lane branch | ✅ |
| DRAFT PR open | ❌ EXACT_HUMAN_GATE: `gh pr create` refused by executor lane guard |

The lane guard at `/Volumes/STORAGE/Offloaded/m1-20260917/lanes/ext/lane_bin/gh`
prevents executor sessions from opening PRs (seat-only `LANE_GUARD_OFF=1`
bypass). This PR body is committed to the lane worktree as `PR_BODY.md`;
the seat (Meta-CEO Fable B per Chairman override 2026-09-06) opens the PR
with the bypass.

Co-Authored-By: Claude Code <noreply@anthropic.com>
