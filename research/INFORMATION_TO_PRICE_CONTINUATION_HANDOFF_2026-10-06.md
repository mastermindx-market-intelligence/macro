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
