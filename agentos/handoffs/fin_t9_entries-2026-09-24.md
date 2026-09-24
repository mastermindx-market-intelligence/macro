# FIN-T9 handoff — 2026-09-24

Lane `fin_t9_entries` · operation `gmi-finance-fable-ceo-e2e-20260924-chairman-001` · carrier PR #7887.

## Deliverable state

- **Head SHA:** `90a9a30ff5fc1be69db03dc4e643d1106270de8e`
- **Lane branch:** `claude/finance-t9-entry-points`
- **Origin status:** live on `https://github.com/mastermindx-market-intelligence/macro`; tip-of-branch SHA matches local HEAD
- **Base:** `origin/main`
- **Commit message trailer:** `Co-Authored-By: Claude Code <noreply@anthropic.com>` (present)
- **DRAFT PR:** NOT YET OPENED — the lane guard refused `gh pr create` because
  the executor seat (this session) is barred from opening PRs. The seat must
  open it via `LANE_GUARD_OFF=1 gh pr create …` (see PR body template below).

**This is `EXACT_HUMAN_GATE`** (per `DEC:EXECUTION-CONTINUATION-INVARIANTS`):
the seat's `LANE_GUARD_OFF=1` bypass is required to open the DRAFT PR. None of
my authorized lanes (commit → push → PR) were fully traversable in this session.

## Files changed (6)

```
 .github/ci/legacy-jobs.yml                   |  25 ++-
 templates/_finance_financials_launch.html.j2 |  19 ++
 templates/_finance_sector_deep_dive.html.j2  |  25 +++
 templates/state_of_themes.html.j2            |   3 +
 tests/test_finance_entry_points.py           | 296 +++++++++++++++++++++++++++
 tests/test_state_of_themes.py                |   5 +
 6 files changed, 371 insertions(0), 2 deletions(-)
```

**NOT touched (per spec):**
- `templates/basket_detail.html.j2` — UNCHANGED while PR #7669 is OPEN; tests
  `pytest.skip("BLOCKED_BY_OWNER #7669")` with that literal.

## Spec compliance

| Spec field              | Result |
|-------------------------|--------|
| C0 gate (PR #7669 OPEN, target files exist on main) | ✅ satisfied |
| Sector deep-dive partial (link-only, no banned words, l-en/l-zh, single `<a>`) | ✅ all 4 |
| Financials launch partial (skipped while #7669 OPEN) | ✅ 4 standalone + 1 skip |
| Tracker live render: canonical theme count unchanged, "Finance Intelligence" only in new region | ✅ both |
| Include position is between lanes-loop close and study-shelf anchor (string index) | ✅ |
| CI extension: paths + run command + closure widening | ✅ |
| NOT DONE UNLESS met | ✅ |
| Commit, push to lane branch | ✅ |
| DRAFT PR open | ❌ EXACT_HUMAN_GATE: `gh pr create` refused by lane guard |

## Validator evidence (local lane)

```
$ python -m pytest tests/test_finance_entry_points.py -q
..........s..                                                              [100%]
12 passed, 1 skipped in 2.69s

$ python -m pytest tests/test_state_of_themes.py -q
1 failed, 52 passed, 11 skipped in 44.13s
  ↳ 1 failure = test_check_validated_claims — 75 UNEARNED 'validated' claims in
    templates I did NOT touch (_debt_maturity.html.j2, _macro_suite_shell.html.j2,
    macro_*.html.j2, hk.html.j2, ...). Grep of 'validated' against my two
    partials returns zero matches — pre-existing on origin/main.

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

CI run command (in `.github/ci/legacy-jobs.yml` finance-intelligence job):

```
python -m pytest tests/test_finance_intelligence_contract.py tests/test_finance_overlap.py tests/test_finance_intelligence_projection.py tests/test_finance_entry_points.py -q
```

## Decision points reached

1. **Class composition for sector card.** Used `class="theme-row sector-deep-dive"`
   — a modifier AFTER the bare `theme-row` class. The existing
   `test_live_render_theme_count` asserts the EXACT substring
   `class="theme-row"` matches `n_themes`; a closing-`"` after `theme-row` would
   have inflated the count. My form keeps `theme-row` as a CSS class but does
   not collide with the substring count.
2. **Filter bar JS immunity.** Set `data-lane="sector-deep-dive"` so the
   existing `data-lane === working/early/caution/review/quiet` filter code
   cannot match and hide the sector card.
3. **Copy discipline.** Both partials verified clean of
   `/rank|score|buy|sell|stage/i` — no theme semantics, no theme language, no
   promotions. EN/ZH bilingual pairs balanced via the host's `t(en, zh)` idiom.
4. **CI gate widening.** `tests/test_finance_entry_points.py` imports
   `scripts.build_state_of_themes` for the live-render test; that script's
   import closure reaches `engine/{__init__,research_priority_ordering}.py`,
   `engine/theme_graph/{__init__,store}.py`, `lib/{__init__,config,pages}.py`,
   `scripts/build_state_of_themes.py`, `site/basketdata/foresight_cascade.json`.
   All added to the `paths:` glob under `finance-intelligence` job (widening
   is always safe per the curated-closure test).
5. **PR-open lane-guard refusal.** The lane guard wrapper at
   `/Volumes/STORAGE/Offloaded/m1-20260917/lanes/ext/lane_bin/gh` line 11
   refuses `gh pr create` for executors. Bypass is `LANE_GUARD_OFF=1` and is
   seat-reserved. This session cannot complete that bypass and reports the
   blocked state instead of silent-stopping (per the contour rule).

## What the seat needs to do

1. Open the DRAFT PR with this exact title and body (template below).
2. Arm `merge-on-green` after the lane's CI gates conclude clean (do not
   pre-emptively arm — the local proof-of-validator above is the seat-side
   confirmation; GitHub Actions provides the canonical gate evidence).
3. Live verification (the spec already carved out the `?v=` re-stamp
   caveat: the partials land as `templates/_finance_*.html.j2` and are
   picked up on the next render; no paired plain-copy asset ships).

### PR open command (seat only, with `LANE_GUARD_OFF=1`)

```bash
LANE_GUARD_OFF=1 gh pr create -R mastermindx-market-intelligence/macro \
  --draft --base main --head claude/finance-t9-entry-points \
  --title "feat(finance-intelligence): Theme Tracker sector deep-dive entry + Financials launch module (Finance T9)" \
  --body "<see PR_BODY.md in the lane worktree>"
```

The full PR body is committed to the lane worktree as
`PR_BODY.md` next to this handoff for clean retrieval.

## Danger areas

- **Do NOT mark the PR ready before the lane's CI gates are GREEN.** The
  Finance Intelligence jobs touch `tests/test_finance_*.py` plus the import
  closure, and `tests/test_ci_pack.py`; the sweeper will refuse to merge a
  red one. CI does not include `tests/test_state_of_themes.py` in this PR's
  gate (it triggers on the existing `state-of-themes` job, not the
  `finance-intelligence` job — this lane's paths widening was bounded to one
  job).
- **The pre-existing `test_check_validated_claims` failure (`sot.py`/`_debt_*`
  /`macro_*`/`hk.html`) does NOT block this lane's gate** — the
  `finance-intelligence` CI job does not run `tests/test_state_of_themes.py`.
  It IS touched on the broader tracker-test job. The seat should expect that
  test to remain red until a separate un-earned-validated-claims healing PR
  lands.
- **The Financials launch partial integration is BLOCKED on PR #7669.** The
  test `pytest.skip("BLOCKED_BY_OWNER #7669")` is literal; do NOT unskip
  before #7669 merges.

## Do_not_redo

- Do NOT re-introduce `class="theme-row"` (exact substring) — that breaks
  `test_live_render_theme_count`. Keep the `sector-deep-dive` modifier.
- Do NOT push to a non-`claude/finance-t9-entry-points` branch from a
  session with `LANE_PR_BRANCH=claude/finance-t9-entry-points`. The lane
  guard documents the lane allowed-destination.
- Do NOT bypass the executor guard with `LANE_GUARD_OFF=1` from a child
  session. The bypass is seat-reserved.

## Provenance links

- Spec packet source: PR #7887 carrier; Chairman override 2026-09-06
  (Meta-CEO A owns the merge rung for FIN-T-series); see `agentos/decisions/`
  and `config/mastermind_programs.yml`.
- Related PRs that share the finance-intelligence gate (must not collide):
  - PR #7669 (OPEN) — blocks basket_detail.html.j2 edits; lane carries the
    Financials launch partial as a standalone until that lands.

## Memory hooks written

- `m1-20260917/lanes/repos/macro/agentos/handoffs/fin_t9_entries-2026-09-24.md`
  (this file)
- `m1-20260917/lanes/repos/macro/PR_BODY.md` (the seat-side PR body)
