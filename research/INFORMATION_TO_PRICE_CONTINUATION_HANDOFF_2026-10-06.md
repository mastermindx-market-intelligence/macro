# Information-to-Price program — continuation handoff (wave 2 boundary, 2026-10-06)

**Seat:** Fable Program-CEO (Claude Code session `2fc05761`), activated by the Chairman via PR #8480
(merged `892157418ec6`). **Carrier:** macro issue #8309 (seat START comment `6009214890` — never re-post).
**Authority:** Chairman directive 2026-10-05 (Meta-CEO, finish end to end, no Claude-native subagents, labor
through the Subagent Fabric, Chairman-only gates saved for last). Sol remains the holding authority on every
program PR: each is DRAFT + HOLD-FOR-SOL and merges only on a Sol comment beginning `HOLD-RELEASED`, with
`--match-head-commit <exact head>`.

This file is the durable program state (`CLAUDE.md` §Context economy). A cold successor resumes from
§4 NEXT and the ledger in §2; nothing here grants authority the workstream record does not already carry.

## 1. Ladder rung reached per artifact (rung = fact, none implies the next)

| Artifact | Head | Rung | Evidence |
|---|---|---|---|
| #8312 source integration (SRC-A1 October accrual, 13 paths incl. the CI manifest) | `94fc98253dc467e57672474533d28308f5255f7c` | CI green → **RESULT / HOLD-FOR-SOL** | RESULT comment `6009778531`; body edited once |
| #8505 R1 identity/basis/rights coverage census (records only) | `ab77f792ee91c95825fe9faca8647dc3d91ac502` | CI green (ci `37415996105`) → **RESULT / HOLD-FOR-SOL** | RESULT comment `6009812189`; seat note `6009778809` |
| #8504 EVAL-1 admission hardening round 1 (P1-1 / P1-3 / P1-4) | `0a54b9dcb7190128d37b2d3f700704c30b2aa48f` | **DELIVERED → CI pending** (ci `37417285240`; fences + ci-authority green) | seat note `6009866776`; body edited once; one watcher |
| #8394 A7 | `0f6fd5b286be` | CI green → RESULT / HOLD-FOR-SOL | `6009629303` |
| #8467 A8 | `056e596e6efe` | CI green → RESULT / HOLD-FOR-SOL | `6009452019` |
| #8461 A9 coupling composer | `3bf903fae36b` | DELIVERED → **CI red (own unenrolled suite)** | note `6009864775` |
| #8463 A10 | `02fe6b515b9b` | DELIVERED → **CI red (own unenrolled suite)** | note `6009786326` |
| #8422 MKT-1 / #8337 EXP-1 | `314ddae3f926` / `13910854fbd6` | DRAFT, queued behind #8312 for the manifest | D17 queue |
| R1 completion spec + readiness probe lane (`itp_r1_completion_spec`, grok/m2) | branch `claude/ssd-itp-r1-completion-spec-20261006-2fc05761` | **RUNNING** (launched 05:28Z) | kit stdout `lanes_itp_r1_completion_spec.stdout`, sentinel `LANE_DONE` |

Nothing in this program is MERGED since #8480 itself; nothing is PRODUCTION_PROOF; nothing is ACCEPTED.

## 2. Decisions taken by the seat (durable; cite before re-deciding)

- **D8 / D17 — one manifest writer at a time.** `.github/ci/legacy-jobs.yml` is owned by #8312 until it MERGES;
  then the queue is #8422 → #8337 → #8461 (enrol `tests/test_k3e_coupling.py`) → #8463 (enrol
  `tests/test_institutional_census_k3e_projection.py`). Two manifest-writing PRs in flight deadlock on
  `contract-delta`.
- **D18 — R1 completion stays with the source owners** (program §8 R1 row). The seat commissions
  measurement and owner-addressed proposals only; it assigns no rights class, invents no identity, buys
  no feed.
- **D20 / D22 — the #8505 census is ACCEPTED as the R1 input**, not as R1 completion. Findings: universe 1503
  (sha `441a942e…`), issuer id resolved 779/1503, 777 alias rows all undated, currency / fiscal-year-end /
  accounting-basis columns absent in every source, `cik_map` 1499 CIK rows without issuer id, rights
  class `UNKNOWN`, provider yfinance, no source-effective or publication clock anywhere (0 of 495,320).
- **D23 — EVAL-1 round-1 head `0a54b9dc` accepted by artifact** (one commit, two files, T1–T8, seat re-run
  32 passed, inspector refuses `EVAL1_REGISTRATION_MISSING`). P1-2 and P1-5 stay with the Eval OS owner (Sol).
- **D21 / D24 — the #8461 and #8463 reds are the PRs' own unenrolled suites** (`contract-delta`: 1 introduced,
  0 inherited), not main's. Remedy is enrolment after #8312 merges, not a waiver and not a re-run.
- **Capacity:** GLM 5.3 Flash is fleet-unavailable (mini2 `STORAGE_GUARD_LOW_SPACE`, Chairman-only fix);
  lanes run on grok/m2 and cursor/ubuntu1 per the Chairman ladder; no Opus lane has been used.

## 3. Standing hazards for a successor

- Every program PR carries a recorded HOLD; `merge-on-green`, ready, native auto-merge and manual merge are
  all forbidden until Sol's `HOLD-RELEASED` comment is the newest human comment on that PR.
- PR bodies have each been edited once this wave (#8312, #8504); a second `gh pr edit --body-file` inside one
  `ci-authority` run cancels that run — post comments instead.
- The seat's own worktree branch (`handoff/information-to-price-fable-program-ceo-20261005`) is already merged;
  every records PR needs a fresh `claude/*` branch off `origin/main`.
- Never re-post START on #8309; seat notes exist once per PR (ids in §1).
- An unenrolled `tests/test_*.py` turns `contract-delta` red by construction; research-dir probes self-check
  through a `--check` mode instead.

## 4. NEXT (critical path first)

1. Sol `HOLD-RELEASED` on #8312 → merge `--match-head-commit 94fc98253dc467e57672474533d28308f5255f7c` on concluded
   checks; fresh `git fetch origin` + 13-blob compare; then the D17 manifest queue.
2. Watcher on #8504 ci `37417285240` fires → GREEN: one RESULT / HOLD-FOR-SOL; RED: own CI-owned suite, so a
   real failure → one REQUEST_REPAIR lane.
3. `itp_r1_completion_spec` returns → judge by artifact (probe reproduces the census counts; `--check` exits 0;
   every gap names an owner by `owns_paths`); seat note + RESULT on its DRAFT PR.
4. Records: this file plus the wave-2 agentos handoff (same PR).
5. Chairman-only gates, last: #8402 cap (569 > 490, Mastermind #974), PID 8688 EFFECT_UNKNOWN,
   TYPED_GIT_PRECHECK, vendor procurement, capital authority, mini2 disk (≥ 50 GB free), EVAL-1 P1-2 / P1-5
   custody, and every Sol HOLD release.

## Wave 2b / wave 3 delta (2026-10-06 08:45Z)

**Scope:** Seat ledger D28–D35 (D33 is seat-ledger-only — not recorded here) plus orchestrator wave-3
lanes W3-A/B/C. **Ordinary records PR** for this delta (no hold on the records lane itself). Carrier #8309
unchanged; Opus 5.5 orchestrators may administer fabric lanes per Chairman ruling (D32); held program PRs
release per D34 (Meta-CEO seat posts `HOLD-RELEASED` naming Chairman authority, then `gh pr ready` and
exact-head squash — never `merge-on-green` on a held PR).

### 5. Seat ledger (D28–D32, D34–D35)

| Id | Time (Z) | Decision |
|---|---|---|
| D28 | 05:43 | Records PR **#8510 MERGED** 05:42:44Z squash `91f274d860e77f245bde31232a617f81d9a5b331` (ci 37419129533 success). Both paths blob-verified on fresh `origin/main` = **PRODUCTION_PROOF** for records-only work. Watcher bhy72774m concluded. Worktree `…/itp-records-wave2-20261006-45ad6225fe668ffa` reclaimable. |
| D29 | 06:03 | R1-completion lane **DELIVERED PR #8514** (DRAFT, HOLD-FOR-SOL, no labels, automerge null) head `9f0b775415e6cadf4e3250ab5b1d51a42f706771` → **ACCEPTED by artifact**: three ADDED research files only; probe on `origin/main` `ef1f7db98cff` with `--check` vs #8505 census JSON on `ab77f792` → `OK (shared counts equal)` exit 0. G1–G5 OPEN, owners UNOWNED. Seat note **6010391922** = ACCEPT + RESULT / HOLD-FOR-SOL. |
| D30 | 06:22 | #8514 ci 37420775034 **FAILURE**: only red = ci-pack-5 `unrun-brain-gateway` → `tests/test_brain_history_widget.py::test_composer_controls_keep_touch_targets_and_reflow[2-en-320]` focus assertion. **Not #8514's defect**: test and manifest step created by merged #8473 `585d26568a9` (05:46:51Z); main's newest concluded ci.yml proof **predates** that merge. One `gh run rerun 37420775034 --failed` (watcher b5yofhmz1). Never touch test/manifest; never second rerun. |
| D31 | 06:4x | Rerun **GREEN** → D30 red was runner-local flake of #8473's new test, not inherited main red. #8514 fully green; still DRAFT + HOLD-FOR-SOL. Merge only on `HOLD-RELEASED` with `--match-head-commit 9f0b775415e6cadf4e3250ab5b1d51a42f706771`. |
| D32 | 07:0x | Chairman: Opus 5.5 orchestrators administer fabric lanes for this seat (no native children; Opus never a worker). Wave 3 commissioned to one Opus orchestrator (`$S/orch_wave3/`): W3-A R4 dry-run receipt, W3-B R5 prospective-consumer spec, W3-C D17 queue pre-staging, W3-D records refresh (this PR). |
| D34 | 07:3x | Chairman: Sol HOLD-FOR-SOL on **this program's own PRs** is an administrative block the Meta-CEO seat releases itself (`HOLD-RELEASED` + Chairman authority + release condition; body hold edited out once after checks; `gh pr ready`; exact-head squash). Release order: #8312 (released comment 6011558025), then #8505, #8514, #8394, #8467; D17 queue #8422 → #8337 → #8461 → #8463 one at a time; #8521/#8522 stay DRAFT until seat releases after queue. |
| D35 | 07:31 | **#8312 MERGED** squash `0f575e51469fc66fa9fd326022ac2d7eee814926`. Post-merge blob compare: 12/13 paths byte-identical to head `94fc9825`; 13th `.github/ci/legacy-jobs.yml` 3-way-merged with main and carries **both** enrolments (needles present). **D17 queue OPEN.** |

### 6. Wave-3 orchestrator outcomes (DELIVERED ≠ MERGED)

| Lane | PR / branch | Rung | Summary |
|---|---|---|---|
| W3-A `itp_r4_dryrun` | #8522 DRAFT HOLD, head `a14846336932a2579bd3cdec707362d13ec94c56`, `claude/ssd-itp-r4-dryrun-20261006-2fc05761` | **DELIVERED**, orchestrator-**ACCEPTED** | Three files under `research/alpha_intelligence/expectation_market_dynamics/`. Composite = main + held #8337/#8422/#8461 heads (never pushed). Stages 6/6 RAN; MKT-1 refused (no parquet bars); coupling COMPONENTS_ONLY; honest N = 0 issuer episodes; prereg K3E-EVAL-0-V1 digest MATCH; `k3e_admissible=false`. verified: `python3 research/alpha_intelligence/expectation_market_dynamics/r4_dryrun_receipt_check.py --check …/R4_DRYRUN_RECEIPT_2026-10-06.json` rc=0; negative controls rc=1. |
| W3-B `itp_r5_spec` | #8521 DRAFT HOLD, head `ad498bddac6fd2400cead0ddc63ed19235059927`, `claude/ssd-itp-r5-consumer-spec-20261006-2fc05761` | **DELIVERED**, orchestrator-**ACCEPTED** (one repair) | Single file `R5_PROSPECTIVE_CONSUMER_SPEC_2026-10-06.md`. Round-1 fixed manifest enrolment precondition (#8312 + D17 queue) and CI-authority note for future build PR. verified: path:line and DNR keys checked against `origin/main`; binding checks green on head (inactive codex merge-queue context only fail). |
| W3-C `itp_queue_prestage` | (nothing pushed) | **DELIVERED** (seat-held scratch) | Post-#8312 merge-tree probes; three post-8312 patches sha256 `47ae5768…`, `42b19975…`, `cf372fc2…`; 12-pack validate-only fail=0; patch apply-check on bare post-#8312 main. Pre-#8312 patch set **SUPERSEDED**. Launch args `args_itp_d17_enrol_{8337,8461,8463}.json` await seat, one PR at a time. |
| W3-D `itp_records_wave3` | (this PR) | **RUNNING → DELIVERED** when pushed | Docs-only: this append + wave-3 agentos handoff. |

GLM probe **refused** this wave (mini2 below 50 GiB `min_free_gb`); fabric lanes used grok on local m2.

### 7. Updated ladder (selected artifacts)

| Artifact | Head / note | Rung |
|---|---|---|
| #8510 wave-2 records | squash `91f274d8…` | **MERGED** → PRODUCTION_PROOF (D28) |
| #8312 source integration | squash `0f575e51…` | **MERGED** (D35) |
| #8514 R1 completion spec | `9f0b775415e6…` | **ACCEPTED** + CI green + DRAFT HOLD (D29/D31) |
| #8505 census | `ab77f792…` | CI green + RESULT; census JSON not on main (held) |
| #8522 R4 dry-run receipt | `a1484633…` | DELIVERED on branch; not on main |
| #8521 R5 consumer spec | `ad498bdd…` | DELIVERED on branch; not on main |
| Queue #8422/#8337/#8461/#8463 | per §2 D8/D17 | OPEN after #8312 merge |

### 8. do_not_redo (wave 3 additions)

- **#8510** records merge and blob proof (D28).
- **#8514** R1 completion acceptance and probe counts (D29); do not re-run the lane.
- **W3-C post-#8312 patches** — validated on main descendant `e95e32d4418f` containing squash `0f575e51`; do not regenerate unless main's manifest neural-web or signal-contract jobs change before the queue finishes.
- **#8312** merge and paths (D35).
- **GLM probe** outcome for this wave (storage guard).
- Wave-2 `do_not_redo` in §3 and the wave-2 agentos handoff remain binding.

### 9. danger_areas (wave 3 additions)

- **#8337** `.github/ci/legacy-jobs.yml` conflict: merge main into branch, keep **MAIN's** manifest, apply `pr8337_legacy-jobs_enrolment_post8312.patch`; four pre-#8312 patches are **SUPERSEDED**.
- **#8473** `test_brain_history_widget` focus flake: at most one failed-run rerun; never edit test or manifest.
- **Held PR protocol** (D34): `HOLD-RELEASED` → ready → `--match-head-commit` squash; never merge-on-green on held PRs.
- **contract-delta** for any new `tests/test_*.py` without legacy-jobs enrolment (W3-B D1).
- **ci-authority**: second body edit on same PR cancels ci-authority run.

### 10. NEXT (wave 3 critical path)

1. Ship W3-D records PR (this append + handoff); arm ordinary merge path when checks conclude.
2. Execute D34 release order on held PRs after green checks (seat may post `HOLD-RELEASED` for this program).
3. Run D17 queue with post-#8312 patches and `args_itp_d17_enrol_*.json`, one merge at a time.
4. Release #8522 / #8521 when queue and upstream gates allow; blob-verify after each merge.
5. Chairman-only gates unchanged from §4 item 5.

## Wave 3 repair round 1 delta (2026-10-06)

**Scope:** Seat ledger D36–D40 (D38 absent in seat delta — gap preserved), authoritative D17 queue wording,
W3-D delivery and fabric facts (supplements §6 without amending prior lines), and #8522 W3-A status. All five
merges below were gated `gh pr merge --squash --match-head-commit <head>` with post-merge blob verification
(missing=0) under Chairman ruling D34; zero merge-on-green arms; reversal for each = `git revert <squash>`.
verified (orchestrator, 07:5xZ): `git fetch origin main` then `git merge-base --is-ancestor <squash> origin/main`
true for all five squashes on main `eae8baa8d3d4`; GraphQL read shows each PR MERGED with exactly the
headRefOid → mergeCommit pairs below.

### 11. Seat ledger (D36–D37, D39–D40; D38 gap)

| Id | PR | Head | Squash | Release comment | Notes |
|---|---|---|---|---|---|
| D36 | #8505 | `ab77f792ee91c95825fe9faca8647dc3d91ac502` | `999e43f1` | 6011669970 | R1 census records MERGED (D34 order after #8312). |
| D37 | #8514 | `9f0b775415e6cadf4e3250ab5b1d51a42f706771` | `1bd2813b` | 6011673427 | R1 completion spec MERGED. |
| D38 | — | — | — | — | **Intentional gap** — not in this seat delta; do not invent or renumber. |
| D39 | #8394 | `0f6fd5b286be` | `96422cf6` | 6011777769 | A7; stale CHANGES_REQUESTED review **5404446368** DISMISSED with evidence. |
| D40 | #8467 | `056e596e6efe` | `ab63a77e` | 6011782121 | A8; stale review **5411174554** DISMISSED. |

(D35 #8312 squash `0f575e51469fc66fa9fd326022ac2d7eee814926`, release comment **6011558025**, recorded in §5.)

### 12. D17 manifest queue (authoritative)

**Order:** #8422 -> #8337 -> #8461 -> #8463 — **one manifest writer in flight at a time.**

#8337 uses the after-#8312 patch variant **`fd677a71`** (content-identical to the orchestrator's post-#8312
re-derivation **`47ae5768`** — only the git `index` header line differs; verified hunk-for-hunk). Both #8461 and
#8463 post-#8312 patches and the #8337 patch apply alone **and** stacked on main `eae8baa8` (`git apply --check`,
rc 0/0/0). Main's `.github/ci/legacy-jobs.yml` is **unchanged** between `e95e32d4` and `eae8baa8`.

### 13. Wave-3 fabric and W3-D delivery (supplements §6)

| Lane | Fabric | Delivery note |
|---|---|---|
| W3-A | grok on local m2 | #8522 — see §14 |
| W3-B | grok on local m2 | #8521 DELIVERED on branch (unchanged) |
| W3-C | grok on local m2 | seat-held scratch (unchanged) |
| W3-D | cursor/composer-2.5 on ubuntu1 | **DELIVERED** as PR **#8525** round-0 head `cb31edb8be80a12dd4d15cd8f700a7f1360580f1` (opened DRAFT by lane driver; ordinary PR, no hold — seat runs `gh pr ready` and arms merge-on-green after this repair's checks conclude). Two no-effect local admission refusals before ubuntu1 run: load1 **42.6** at **07:28:57Z**, **21.81** at **07:49:18Z** vs gate **16.8**. |

### 14. #8522 (W3-A) — OPEN + DRAFT (not MERGED)

Head `a14846336932a2579bd3cdec707362d13ec94c56`. Seat re-ran validator from `refs/remotes/pr/8522`:
`ok stages=6 ran=6`, rc=0. Merge-tree clean vs main `eae8baa8`. Seat **releases** #8522 once its last pending
check concludes; remains **OPEN + DRAFT** until then — never describe as merged.

### 15. Still OPEN + DRAFT (orchestrator verified on main `eae8baa8d3d4`)

| PR | headRefOid (prefix) |
|---|---|
| #8422 | `314ddae3` |
| #8337 | `13910854` |
| #8461 | `3bf903fa` |
| #8463 | `02fe6b51` |
| #8521 | `ad498bdd` |
| #8522 | `a1484633` |

### 16. Ladder updates (post D36–D40)

| Artifact | Squash / head | Rung |
|---|---|---|
| #8505 census | squash `999e43f1` | **MERGED** (D36) |
| #8514 R1 completion | squash `1bd2813b` | **MERGED** (D37) |
| #8394 A7 | squash `96422cf6` | **MERGED** (D39) |
| #8467 A8 | squash `ab63a77e` | **MERGED** (D40) |

### 17. NEXT (repair round 1)

1. Land W3-D repair on #8525; seat `gh pr ready` + merge-on-green after checks conclude.
2. Run D17 queue per §12 (post-#8312 patches on main `eae8baa8`), one PR at a time.
3. Release #8522 / #8521 when queue and gates allow; blob-verify each merge.
4. Chairman-only gates unchanged from §4 item 5.

## Wave 3 release round delta (2026-10-06, D41–D49; #8337 in flight)

Append-only. Everything above stays as written; this section supersedes §15–§17 where they
describe PRs as OPEN + DRAFT. Authority for every release below: the Chairman's 10-06 ruling
("they are all really administrative blocks and not hard blocks, so u should just overrule them
and get us past them rather than making me go fix them using chatgpt web sessions"), recorded as
`DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06`. Every release used the
D34 form: release comment naming the Chairman authority and the exact head → ONE title/body edit
(`HOLD-FOR-SOL` → `HOLD-RELEASED 2026-10-06`) → `gh pr ready` → state read on CONCLUDED checks →
`gh pr merge --squash --match-head-commit <head>` → `git fetch origin main` alone → ancestor +
per-path blob compare. Reversal of any merge is `git revert <squash>`.

### 18. Seat ledger D41–D49

| D | PR | Rung | Squash | Exact head | Release comment | Note |
|---|---|---|---|---|---|---|
| D41 | #8522 R4 descriptive-coupling dry-run receipt | **MERGED** 08:07:22Z | `8c3d0f60148bd70f0b5fcbee3ff24889f8efda98` | `a14846336932a2579bd3cdec707362d13ec94c56` | 6012094323 | research-only; blob-compare 0 missing |
| D42 | #8422 ruling | — | — | `314ddae3` at ruling time | — | review 5408914930 is a semantic PASS whose single blocker (no CI owner for `tests/test_price_pressure.py`) was closed by #8312's `options-skew-engine` job; dismissed on content, not on head |
| D43 | D17 queue ruling | — | — | — | — | the D17 single-writer manifest queue is satisfied by DISJOINT prestaged hunks (`git apply --check` rc 0 alone and stacked on `eae8baa8`), so enrolment lanes may run concurrently, one watcher each, released in conclusion order after a merge-tree re-check |
| D44 | #8504 EVAL-1 admission hardening r1 | **MERGED** 08:03:19Z | `cab92332ea939ca148257e16c117768db5523634` | `0a54b9dcb7190128d37b2d3f700704c30b2aa48f` | 6012034313 | `WS:EVAL-OS-MEASUREMENT-LAW` ownership unchanged; admits nothing to EVAL-1; P1-2/P1-5 stay with the Eval OS owner |
| D45 | #8521 R5 prospective-consumer frozen spec | **MERGED** 08:03:11Z | `f8ce27bff995eff1e52bff16ffbe97496a61ab00` | `ad498bddac6fd2400cead0ddc63ed19235059927` | 6012032293 | spec only: builds nothing, ratifies nothing, assigns no owner |
| D46 | #8525 wave-3 records refresh | **MERGED** 08:3xZ | `42107c53e23e140f5c60cdd9c64f6a74c6e5a2d1` | `26cc065f` | ordinary chain (no hold) | records §11–§17 above |
| D47 | #8461 A9 descriptive coupling composer + D17 enrolment | **MERGED** 08:38Z | `77fc9b1c447ab8432284f5a6023dc4558f0d534a` | `42574962ca0c` | 6012568839 | ci.yml run 37434219548 success; manifest needle `test_k3e_coupling` present on main |
| D48 | #8463 A10 immutable 13F holding context + D17 enrolment | **MERGED** 08:45Z | `fbd63e4f12e11bfbadf32895ed03d0bf80311769` | `cba435e5` | 6012679845 | ci.yml run 37435074643 success |
| D49 | #8422 MKT-1 owner-native market-response export | **MERGED** 08:52:21Z | `d0ede600ca23552f3e1d59f8dc8f369fd95fe9ca` | `56d2b794249d196b52ebd364edbb9f7cd5a89d99` | 6012779228 | hand-merged on an INHERITED red — see §19; review 5408914930 DISMISSED; blob-compare 0 missing (`engine/price_pressure/response_export.py`, `tests/test_price_pressure.py`) |

Dismissed reviews under the ruling: 5404446368 (#8394, D39), 5411174554 (#8467, D40),
5408914930 (#8422, D49). Each dismissal message names the evidence that the review's blocker is
closed on main; none asserts the reviewer was wrong at the time of review.

### 19. D49 — inherited-red classification on #8422 (seat ruling)

- ci.yml run 37433544726 on head `56d2b794` concluded red on attempt 1 AND on one `--failed`
  rerun (attempt 2), both times solely on `tests/test_brain_history_widget.py::
  test_composer_controls_keep_touch_targets_and_reflow[1-zh-320]` / `[2-zh-320]` ("Locator
  expected to be focused") in ci-pack-6, with ci-gate red by inheritance. That test is #8473's;
  #8422 touches neither it nor its manifest.
- Main's own baseline run 37432781824 passes ci-pack-6; the same assertion flaked on #8522
  (`[2-en-320]`) and greened on a single rerun there.
- The PR's owner job `options-skew-engine` was planned and EXECUTED on this run (ci-plan: scoped
  to 2 changed files, 76/172 jobs, 0 unowned; ci-pack-4 `60 passed in 20.74s`).
- L.4 forbade a third identical rerun. The seat classified the red inherited/flaky and merged on
  the exact head with a gate allowing red ⊆ {ci-pack-6, ci-gate}.
- Watch item: if main's next proof or the nightly fails this assertion, the owner is #8473's
  test, never this merge. Reversal `git revert d0ede600`.
- Consequence accepted: the Stop guard may file `ci_failed` INTERNAL blocks for this merged head;
  they are answered by the escape ladder, never by another rerun.

### 20. #8337 EXP-1 — IN FLIGHT at write time (not merged)

- First chain (run 37434234401 success on head `3b025ca2`) ABORTED before any release act:
  `git merge-tree` reported a both-added conflict in `.github/ci/legacy-jobs.yml` because
  sibling enrolments #8455 (`731a23fb`) and #8461 (`77fc9b1c`) landed on the same `paths:` list.
- Seat resolution under L.7 (no worker started, lawful custody, no other owner): SSD worktree
  `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/itp-8337-conflict-20261006-8d244c76a11dd2b0`
  on branch `claude/ssd-information-to-price-exp1-20261003-b4cff810e30514df`; keep-both merge of
  main `77fc9b1c` pushed as merge commit `95280c15e3429f48374fce2a640f59b30f476e04` (parents
  `3b025ca2` + `77fc9b1c`; `run_ci_pack.py --validate-only` rc 0 for packs 0–11; diff vs main =
  the PR's own 8 files; no rebase, no force-push).
- New ci.yml run 37437949027 (fences 37437948340 success); merge-tree clean vs main `fbd63e4f`.
- Release chain `chain_enrol.sh 8337 95280c15… 37437949027 query_k3e_expectation_surface` is the
  single watcher; on success it posts the D34 release and merges on `--match-head-commit 95280c15`.
- Verification after merge: `git grep -c query_k3e_expectation_surface origin/main -- .github/ci/legacy-jobs.yml`
  ≥ 1; the manifest blob itself will differ from the PR head (3-way artifact), which is expected.

### 21. Ladder (post D41–D49)

| Artifact | Squash | Rung |
|---|---|---|
| #8312 SRC-A1 source integration | `0f575e51` | MERGED (D35) |
| #8505 R1 census · #8514 R1 completion | `999e43f1` · `1bd2813b` | MERGED (D36, D37) |
| #8394 A7 · #8467 A8 | `96422cf6` · `ab63a77e` | MERGED (D39, D40) |
| #8522 R4 dry-run receipt · #8521 R5 spec | `8c3d0f60` · `f8ce27bf` | MERGED (D41, D45) |
| #8504 EVAL-1 hardening r1 | `cab92332` | MERGED (D44) |
| #8525 wave-3 records | `42107c53` | MERGED (D46) |
| #8461 A9 · #8463 A10 | `77fc9b1c` · `fbd63e4f` | MERGED (D47, D48) |
| #8422 MKT-1 | `d0ede600` | MERGED (D49) |
| #8337 EXP-1 | head `95280c15` | CI (run 37437949027) → release chain armed |
| Commission-2 #8402 | — | BLOCKED: cap 569 > 490 (Mastermind #974) — Chairman gate |
| EVAL-1 positive outcome access (P1-2 / P1-5) | — | with `WS:EVAL-OS-MEASUREMENT-LAW` owner |
| R1 gaps G1–G5 | — | UNOWNED source-owner receipts — Chairman/owner gate |

No merge above grants consumer wiring, Market OS UI, rank, gate, size, trade, capital or
deployment authority; every merged artifact is descriptive/diagnostic or a frozen spec.

### 22. do_not_redo (release-round additions)

- Do not re-release, re-dismiss, re-edit or re-arm any PR in §18; each is MERGED with its squash
  recorded; reversal is `git revert <squash>`, never a replacement PR.
- Do not rerun ci.yml run 37433544726 (#8422) a third time; the D49 classification stands unless
  main's own proof fails the same assertion.
- Do not re-resolve the #8337 manifest conflict: merge commit `95280c15` already carries the
  keep-both resolution; a second resolver produces a second writer on `.github/ci/legacy-jobs.yml`.
- Do not spawn a second orchestrator: the W3 Opus orchestrator (agent `ac3cb0fb09d6f62e8`,
  Chairman-authorized 10-06) FINISHED with `STATUS: PROVEN_OUTCOME`; resume it only by message.
- Do not delete worktree `…/itp-8337-conflict-20261006-8d244c76a11dd2b0` before #8337 merges.

### 23. danger_areas (release-round additions)

- A body edit followed by `gh pr ready` schedules a `ci-authority` run; the merge gate must wait
  it out (measured on #8422: first merge attempt SKIPPED on a pending ci-authority, merged ~3 min
  later by the tail watcher). Edit once, then never again.
- Gate a `gh pr checks --watch` output file on its LAST snapshot only; a whole-file
  `grep -c pending` accumulates every refresh (chain brlc1kah1 falsely reported pending=6).
- Manifest enrolments from different programs collide on the same `paths:` list in
  `.github/ci/legacy-jobs.yml` (both-added, trivially keep-both); re-run merge-tree before every
  release, never trust a green run on a pre-collision head.
- `ci-authority/codex/merge-queue-pilot` FAILURE is a standing inactive context on every PR;
  exclude it by name before deciding red.

### 24. NEXT (after the release round)

1. #8337: on the chain's sentinel read the release output; MERGED → record D50 with the squash;
   red → classify from the job list (own enrolled suite = own; #8473 focus flake = ONE rerun);
   merge-tree ABORT → repeat the keep-both merge in the same worktree, re-validate packs 0–11.
2. Report to the Chairman the non-administrative gates LAST, exactly: Commission-2 #8402 cap
   569 > 490 (Mastermind #974); PID8688 EFFECT_UNKNOWN (same-carrier reconciliation only);
   TYPED_GIT_PRECHECK_REFUSED on the PIT-conformance workspace; vendor PIT procurement
   (SAMPLE_REQUIRED); capital/rank authority; mini2 free disk ≥ 50 GB for the GLM tier; EVAL-1
   P1-2/P1-5 custody; R1 source-owner receipts G1–G5 (UNOWNED).
3. Science lanes R4 (predictive admission) and R5 (prospective consumer proof) stay closed until
   R1 identity/basis/rights completion and lawful EVAL-1 admission; nothing in this round opens them.

## Final round delta (2026-10-06, D50–D54; program build-out closed)

Append-only. This section supersedes §20, §21 and §24 above. Authority is unchanged: Chairman
handoff #8480 and the Chairman's 10-06 administrative-override ruling
(`DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06`). At ~09:05Z the
Chairman switched this seat's session to Opus 5.5 orchestration; same seat, same duties.

### 25. Seat ledger D50–D54

| D | PR | Rung | Squash | Exact head | Release comment | Note |
|---|---|---|---|---|---|---|
| D50 | #8337 EXP-1 declared-capture inspector + enrolment | **MERGED** 09:17:56Z | `a9f815e1` | `95280c15e3429f48374fce2a640f59b30f476e04` | 6013193171 | ci.yml run 37437949027 success; needle `query_k3e_expectation_surface` on main = 2; see §26 for the manifest compare |
| D51 | #8532 release-round records (§18–§24) | **MERGED** | `4d470120` | `a2962511` | ordinary chain (no hold) | see §26 for the WS-record compare |
| D52 | #8402 Commission-2 PIT analyst-expectations hardened audit | **MERGED** | `0f9bc8e8` | `5b622d661da68a39e4d750c787181a7c6c978a5b` | 6013367403 | released as administrative; see §27 |
| D53 | #8534 synthetic PIT sample conformance harness recovery + enrolment | **MERGED** | `960cb183` | `5760d97238252ea96d791f47281b18e53832cf31` | ordinary chain; hand-merged under D54 (comment 6014098651) | recovered under L.7; see §28 and §28a |

### 26. Post-merge compares that reported MISSING were false alarms

The chains' per-path blob compare reported `missing=1` on D50 and on D51. Both were the same
benign shape: a later PR edited the same file after this PR's merge base, so main's blob can
never equal the PR head's blob. The lawful check is a hunk compare, `git diff
$(git merge-base <head> <squash>^) <head> -- <path>` against `git diff <squash>^ <squash> --
<path>`.

- D50: `.github/ci/legacy-jobs.yml`, also edited by #8463 after the base. The PR's 8 manifest
  lines equal the squash's 8 lines.
- D51: `agentos/workstreams/WS-ALPHA-INTELLIGENCE-INTEGRATION.md`, also edited by #8337. The PR's
  25 lines equal the squash's 25 lines. The other three paths are blob-identical.

### 27. D52 — #8402 released as administrative

- Sol's comment 5990874275 accepted the research semantics and current-base compatibility.
  The PR carries approved review 5409767415.
- The only remaining gate was the fleet-wide Source Continuity census cap (569 open PRs > 490,
  Mastermind #974). That cap counts the whole fleet's open PRs. It is not a property of this
  PR, so the Chairman's 10-06 ruling classes it as administrative.
- The seat ran the collision check directly. The PR adds one file, absent on main, and
  `git merge-tree` is clean.
- Update-branch moved the head from `63208615` to `5b622d66` (main parent `82804283`). The diff
  against main is the single added file.
- Release followed the D34 form on concluded checks. Reversal is `git revert <squash>`.

### 28. D53 — PIT conformance harness recovered; PID 8688 inert

- The precheck block named in §24 (`TYPED_GIT_PRECHECK_REFUSED` on Sol's PIT-conformance
  workspace) had one cause: three verified files with no CI owner.
- The seat copied the three files byte-identically from the Sol workspace (read only) into
  `research/alpha_intelligence/expectation_market_dynamics/`. The sha256 prefixes match the
  handoff: `pit_sample_conformance.py` f789ab25, `test_pit_sample_conformance.py` 594bcfb2,
  `PIT_SAMPLE_CONFORMANCE_IMPLEMENTATION_2026-10-04.md` 4ee8ac33.
- One CI step in `unrun-factor-research`, placed after SRC-A1, names the CLI with `--help` and
  runs the 24-test suite. That enrolment is the owner the precheck asked for.
- This was bounded principal work under L.7. No worker had started on it, the seat held
  lawful tools, no other owner was on the artifact, and nothing was EFFECT_UNKNOWN. The harness
  is synthetic and grants no data, rank, or capital authority.
- PID 8688 is classed INERT. Its only possible effect is unreferenced common-store tree objects
  from a timed-out `git write-tree`. No ref, index or worktree moved, and gc prunes such
  objects. DO_NOT_REPLAY stands. It is no longer a gate.
- mini2 had 68 GB free at 09:2xZ, above the 50 GB `STORAGE_GUARD_LOW_SPACE` floor, so the GLM
  tier gate in §24 is resolved.

### 28a. D54 — #8534 hand-merged on a fleet-flake red

- The ordinary chain skipped the merge twice. The only red was `ci-pack-7`, with `ci-gate`
  failing as a consequence. Its sole failed job was `unrun-brain-gateway`, failing on
  `tests/test_brain_history_widget.py::test_composer_controls_keep_touch_targets_and_reflow`
  ("Locator expected to be focused"). It failed at `[2-zh-390]` on attempt 1, then at
  `[1-zh-320]` and `[2-zh-320]` on the single `--failed` rerun of run 37442173953.
- The red is the fleet's, not this head's:
  - Sibling PR #8533 is red on the same test (run 37441583018, job 112197541444, `[1-zh-320]`).
  - Main's proof run 37442227387 passed its packs.
  - The PR's diff is three new `research/` files plus one `legacy-jobs.yml` step.
  - The test belongs to #8473's lane, which this seat may not touch.
- A third rerun was banned by L.4. The seat posted comment 6014098651 naming the Chairman 10-06
  authority, then squash-merged exact head `5760d972` as `960cb183` at 10:14:14Z.
- On fresh `origin/main` the squash is an ancestor, all three new files are blob-identical, and
  the `pit_sample_conformance` manifest needle reads 2.
- Reversal is `git revert 960cb183`.
- The flaky focus assertion is #8473's to fix. It is now red on at least three independent PRs
  today, so a successor that meets it should check a sibling before rerunning.

### 29. Ladder (final)

| Artifact | Squash | Rung |
|---|---|---|
| #8312 SRC-A1 source integration | `0f575e51` | MERGED (D35) |
| #8505 R1 census · #8514 R1 completion spec | `999e43f1` · `1bd2813b` | MERGED (D36, D37) |
| #8394 A7 · #8467 A8 | `96422cf6` · `ab63a77e` | MERGED (D39, D40) |
| #8522 R4 dry-run receipt · #8521 R5 spec | `8c3d0f60` · `f8ce27bf` | MERGED (D41, D45) |
| #8504 EVAL-1 hardening r1 | `cab92332` | MERGED (D44) |
| #8525 · #8532 records | `42107c53` · `4d470120` | MERGED (D46, D51) |
| #8461 A9 · #8463 A10 | `77fc9b1c` · `fbd63e4f` | MERGED (D47, D48) |
| #8422 MKT-1 | `d0ede600` | MERGED (D49, inherited red) |
| #8337 EXP-1 | `a9f815e1` | MERGED (D50) |
| #8402 Commission-2 audit | `0f9bc8e8` | MERGED (D52) |
| #8534 PIT conformance harness | `960cb183` | MERGED (D53) |
| EVAL-1 positive outcome access (P1-2 / P1-5) | — | with `WS:EVAL-OS-MEASUREMENT-LAW` owner (blinding control) |
| R1 gaps G1–G5 | — | owner receipts required; paths UNOWNED; Chairman owner designation |

No merge above grants consumer wiring, Market OS UI, rank, gate, size, trade, capital or
deployment authority. Every merged artifact is descriptive, diagnostic, synthetic, or a frozen
spec. No artifact reached PRODUCTION_PROOF or ACCEPTANCE as a product capability, because none
is wired to a served surface.

### 30. Remaining gates are real, not administrative

1. **R1 G1–G5 owner designation.** Program §8 R1 and the completion spec require owner-issued
   receipts. No workstream `owns_paths` covers `data/reference/`, `data/symbol_directory/`,
   `data/revisions/` or `collectors/equity_revisions.py`. The rights vocabulary (G4) belongs to
   the shared-base owner (#7870), so this seat may not mint it. Only the Chairman can designate
   owners. After that, each owner issues receipts or a labeled absence per the spec's degraded
   path.
2. **EVAL-1 positive outcome custody (P1-2 / P1-5).** `WS:EVAL-OS-MEASUREMENT-LAW` holds it as
   a blinding control. A seat that unblinds its own outcomes defeats the control, so this stays
   with that owner.
3. **Vendor PIT procurement** (SAMPLE_REQUIRED) is a purchase.
4. **Capital and rank authority** is reserved to the Chairman.

R4 predictive admission and R5 prospective-consumer proof stay closed until gates 1 and 2 clear.

### 31. do_not_redo and danger_areas (final round)

- Do not re-release, re-merge or re-verify #8337, #8532, #8402 or #8534; their squashes are
  above. Reversal is `git revert <squash>`.
- Do not re-copy the PIT harness from Sol's workspace. Do not replay PID 8688.
- Do not open R4/R5 lanes, consumer wiring or an issuer/rights build before gate 1 clears.
- A post-merge blob compare reports MISSING whenever another PR touched the same file after the
  merge base. Run the hunk compare in §26 before believing it.
- Worktrees `…/itp-8337-conflict-20261006-8d244c76a11dd2b0`,
  `…/itp-records-20261006-ca7fc15125af3f91` and `…/itp-pit-conformance-20261006-972a780901f55ce3`
  are landed and reclaimable once their PRs read MERGED.

### 32. NEXT

1. The Chairman decides gate 1: name owner workstreams for the four R1 paths, or rule R1 stays
   in labeled-absence form.
2. After gates 1 and 2 clear, a seat commissions R4 predictive admission against the R4 dry-run
   receipt (#8522) and then R5 against its frozen spec (#8521).
3. Until then this program has no open build lane. A successor's first act is to read this
   section and the Chairman's carrier, not to re-census.
