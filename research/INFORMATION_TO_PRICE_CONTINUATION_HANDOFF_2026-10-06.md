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
