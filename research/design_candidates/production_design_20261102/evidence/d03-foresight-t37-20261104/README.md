# D03 T37 — pending 90-day outcomes remain visible

**Source, Paper component and browser proof complete. Draft / HOLD.**
This is the T37 / F08 presenter slice of the existing D03 Phase 2A mission, not completion of the six-route programme or release authority.

## Observable result

The Foresight Track Record previously displayed `n_pending` only when there were no graded results. Once grading began, the remaining pending population disappeared. The template now renders a separate pending chip after the graded/accruing/empty branch, using the producer-declared count.

| Source input | Presentation |
| --- | --- |
| Graded results and positive pending count | Existing graded results plus the pending count, once |
| No graded results, positive logged population | Existing accruing/logged-flags chip plus the pending count, once |
| Declared integer zero | `0 pending 90d` / `0 待90天` |
| Missing, null or invalid count | No numeric pending chip; available results remain |
| Control-only graded cohort | Existing forward-excess/control-arm result plus pending count |

A nonnegative integer is required. Booleans, fractions, strings, arrays, objects and negative values do not become counts. No total-minus-graded arithmetic or substitution is performed. The adversarial fixture explicitly reports 7 pending alongside 351 total / 122 graded; the page must show 7.

The existing source artifact at `macro@24bb49beebccc5ddf19e77082ea5bc0e8138bf13` reports 351 total, 122 graded, 229 pending and 51 directional observations. Those are producer-reported values, not an independent validation of grading science.

## Exact source and custody

- Tested base: `201e94dd75f385d118cc0f692768c26e0f02b355`.
- Prepublication main observation: `52abe2e183833a216267942a99513e6c9cbe062f`.
- The comparison endpoint reached its 300-file cap. It was not used to infer absence of changes. Exact Git blob reads verified all ten relevant source, dependency, CI and local-instruction paths unchanged between those revisions; see [DEPENDENCY_BLOBS.json](DEPENDENCY_BLOBS.json).
- Protected Mastermind pin: `124df8d533dd01400a7dc514ac98b92b2d63186e`, schema `mastermind.sol_skillpack.v1`, skillpack 1.0.1, bootstrap major 1 compatible. Refreshed after a material session-local review-policy change; applicable unchanged companions were fetched at that same pin.
- [Canonical T37 pickup and active-T36 custody boundary](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6626197521).
- Host-policy-admitted branch: `claude/ssd-d03-foresight-pending-t37-20261104-c2-b181e904c380228d`.
- Fresh admitted workspace: `/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/d03-foresight-pending-t37-20261104-c2-b181e904c380228d`.
- Direct principal integration reason: **UNIQUE_APPROVED_ACCESS** to the qualified original Studio/Paper carrier. A native child supplied bounded read-only reasoning; no implementation worker, reviewer gate, Fabric effect or watcher was started.

Only two product/test paths change:

1. `templates/foresight.html.j2`: independent pending chip and record-chip text increased from 11px to 12px.
2. Existing `tests/test_foresight_page_flag_ledger.py`: 27 new actual-template cases, within the already declared CI page-reader command.

Remaining files are owned D03 evidence. No CI manifest, producer, grader, score, ranking, threshold, data, builder, shared navigation/theme, authentication, generated site or publication-control code changes. The historical table markup renders byte-for-byte identically in the retention test.

T35 and active T36 are separate held candidates. Their template changes are not present in this fresh-main proof. Integration must qualify the combined candidate later.

## Focused regression evidence

[RED result](red-test-result.txt): **11 failed / 20 passed** on the unmodified fresh-main template. The failures establish disappearing pending counts, missing zero, invalid values in the all-pending branch and the separate pending presentation.

[Final focused result](focused-test-result.txt): **48 passed**. This is the existing CI page-reader command, including 31 flag-ledger tests (4 prior cases plus 27 T37 cases):

```bash
python3 -m pytest \
  tests/test_foresight_page_analyst_zh.py \
  tests/test_foresight_page_fingerprint_depth.py \
  tests/test_foresight_page_flag_ledger.py \
  tests/test_foresight_page_score_base.py \
  tests/test_foresight_page_trend_state.py -q --tb=short
```

The existing `healthcare-fda-supply` job already declares the edited test and runs these five files. No new CI lane or registry was added. Final `git diff --check` passed.

Retention assertions cover the 51-member directional denominator, separate control-arm forward excess and the unchanged dated membership table. They do not revalidate or alter the grading algorithm.

## Actual-template browser proof

[Final report](browser-final/browser-proof.json) · [run log](browser-final.log) · [reproduction script](verify_browser.py)

**60 cases:** 320 / 390 / 1440 × light / dark × EN / ZH × mixed / all-pending / zero-pending / unavailable-pending / control-only.

- Chromium 151.0.7922.34.
- Zero whole-page horizontal overflow and zero JavaScript errors.
- All measured record-chip text at least 12px; minimum measured contrast **5.3297:1**.
- Native Enter opens Track Record, Space closes it, and focus remains on its summary. Minimum observed summary height: **52.39px**.
- Native Tab reaches the existing mobile table scroller, ArrowRight moves it, and the final member is within the viewport at full horizontal scroll. The shared existing `.tbl-scroll` behavior is retained; horizontal scrolling within that table is intentional.
- Pending text, directional denominator and control labels are checked in the active language in every case.
- Pending chips remain static with reduced motion.
- 26 retained final screenshots cover default component states, full-page context and mobile membership depth.

Representative captures:

- [320 light EN — graded and pending](browser-final/mixed-320-light-en.png)
- [320 light EN — all pending](browser-final/all-pending-320-light-en.png)
- [320 light EN — declared zero](browser-final/zero-pending-320-light-en.png)
- [390 dark ZH — unavailable count](browser-final/unavailable-pending-390-dark-zh.png)
- [320 dark ZH — final historical members](browser-final/members-mixed-320-dark-zh.png)
- [1440 dark ZH — component](browser-final/mixed-1440-dark-zh.png)

This is a network-isolated fixture using the actual template, owned CSS/JS and explicitly synthetic summaries. The only unrelated stubbed request is `/case/live_config.js`. No live-market request, builder run, server, backend/auth path, deployment or production acceptance is claimed. The inherited shared chat launcher remains visible in captures; this slice does not qualify the entire shared shell.

### Visual QA and fixture correction

Self-review caught an inaccurate synthetic stage key: `LATE` rendered as No read because the actual source vocabulary is `RE-RATING`. The fixture was corrected, bilingual Late assertions added, and all 48 focused tests plus the 60 browser cases passed against the corrected inputs. The earlier screenshot is retained as a diagnostic, not final proof.

A later capture-only check found that resetting the table immediately after native keyboard scrolling could leave an intermediate scroll position. Default screenshots now occur before the keyboard journey. The keyboard and final-member assertions remain; no production code was changed for this harness issue. The failed capture attempt is preserved under diagnostics.

## Native Paper component

[PROPHET / p-D-0](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-D-0), owned board **`11JL-0` — D03 T37 · Pending outcomes · EN ZH · DRAFT**.

- Exact isolated target at x=9640; no existing board changed.
- Existing domain tokens, Inter/PingFang, 14px body and 12px meaningful receipts.
- Mixed light EN / dark ZH, all-pending, declared-zero and unavailable-count states.
- Actual screenshot inspected for clipping, hierarchy, readability and density; JSX extracted after visual acceptance.
- [Native screenshot](pending-outcomes.paper.jpg) · [editable JSX export](pending-outcomes.paper.jsx).
- Guard: `989079ab7271f971a2886d4d7cbe3968ce15a3050d6385cba3fa00dd8510100b`; token hash `640746f9`.
- Live catalog: `03cb81e960dab705b21b0695f3886d39c4792df629a6419163efef52338182e4`, Paper 0.5.18, accepted TOOL_SCOPED_CONTRACT_V1.
- Three operations returned **APPLIED_RESPONSE_OBSERVED**:
  - `d03-t37-pending-component-create-20261104-c2-01`
  - `d03-t37-pending-component-content-20261104-c2-02`
  - `d03-t37-pending-component-finish-20261104-c2-03`

The guard is not a document revision or exclusive file lease. Board custody is target-scoped; the foreground p-C-0 and every other board were preserved. The component study is provisional domain design, not final F01/F02 shell conformance or a wired Paper UI.

## Source-bound hashes

| Artifact | SHA-256 |
| --- | --- |
| Template | `98a28a58b242675e6d0bb39cae724a4f9c52fa34d2ce4b6775a49c23447f3817` |
| Flag-ledger test | `471b320a5c4412ab59b5cbdf11cdf8f39e2ada05b5f87d0cb42d398247eb1471` |
| Paper screenshot | `8b041361895da88f8a8b12d4dfd55aa539a44d6b438dce5fe8f020a8ce1d7866` |
| Paper JSX | `10527d924501419cbfffacf60d4b1b6271a1f7d9468b806da4c188cdd0d25e0c` |

Final browser source hashes were checked against the current worktree. The [file inventory](EVIDENCE_MANIFEST.json) binds the retained evidence.

## Release boundary

**Draft / HOLD. No Ready, un-draft, labels, enqueue, auto-merge, merge or deploy.** This is the explicit programme release boundary, not a claim that pending CI alone prevents readiness.

The production consumer remains the existing Foresight builder and served route. After separately authorized integration/release, qualify the combined template and actual served route. A screenshot, green CI or PR does not substitute for that acceptance. [Continuation](CONTINUATION.md) preserves exact custody and the next authorized source action.
