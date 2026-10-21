# Prophet Stage 5 regional orchestration — worklog (2026-10-21)

Orchestrator: Opus 5.5 under seat 69eb9a1c (ROUTE: orchestration). BASE e5dd30c6344e4b62a0beba054ac4da97e00bab36.
Writes only under `research/prophet_v4/r7_program/regional/`; nothing committed, pushed, posted or dispatched.

## Timeline (UTC)
- 03:05 commission received; fable-mode loaded; masterplan Stage 5, §10, §7.3–7.4, A3, A4 read by range.
- 03:10 PR census (one batched read): states of #6871 #6872 #6996 #7018 #7163 #7248 #7277 #7286 #7288 #7303 #7385 #7499 #8184 #8270 #8444 #8714 recorded in seat scratchpad `regional_prs.tsv`. Older-PR file census returned HTTP 502 twice -> tactic changed to named incumbents + 100 most-recent open PRs (residual risk recorded).
- 03:15 custody check for the Canada zero-buy hole: `_canada_board_ledger` (scripts/build_canada.py:678, early return 685-687) is touched by no open PR in the census (#7018 hunks are import ~37 and main() ~1471; #7286 and #8444 do not touch build_canada.py). Workstream owner WS-PROPHET-HK-CA-REVAMP = fable (the seat).
- 03:20 lanes launched (round 1, 2 live max):
  - `pro-regional-cazb-20261021-r1` — build, Canada zero-buy liveness repair (packet `$S/pk/pro-regional-cazb-20261021.md`).
  - `pro-regional-cnscout-20261021-r1` — census, China P0–P4 correctness at BASE (packet `$S/pk/pro-regional-cnscout-20261021.md`).

## Lanes
| run id | class | host | status | report / commit |
|---|---|---|---|---|
| pro-regional-cazb-20261021-r1 | build | mmx-ubuntu0 | DONE rc=0 03:31Z, lane STATUS PARTIAL (see 03:35 note) | lane commit c9a6553bbab on `lane/pro-regional-cazb-20261021-r1`: `scripts/build_canada.py` +18/-6, `tests/test_board_shadow.py` +186 |
| pro-regional-cnscout-20261021-r1 | census | mmx-ubuntu0 | RUNNING (poll 17 @03:27Z) | — |
- 03:27Z: CNA-CIE04-06 row corrected to BLOCKED-DATA (CIE package pin 1b0f2ee2 absent from macro + local Mastermind) → Decision F4. Both round-1 lanes on mmx-ubuntu0, pending.
- 03:32Z: hkscout round-2 lane launched (`pro-regional-hkscout-20261021-r1`, census). cnscout still pending.
- 03:35Z: cazb consumed. Diff read on ubuntu0 and matches the frozen spec: `setups` None/non-dict keeps SKIP; a dict with empty buy no longer returns early; `append_board` is withheld with an info log; scorecard/grade/track/shadow still run; health starts with the identical SKIP row; the non-empty path is unchanged. T6 showed T1 fails at BASE ("write_shadow must run exactly once; got 0"). Suites: board_shadow 69 passed, canada_build 13, board_ledger 69, canada_canonical_board 35. prophet_board_since: 2 failed, which the lane reproduced at a pristine BASE extraction, so they are pre-existing.
- 03:38Z: CI consequence verified at BASE. `scripts/build_canada.py` is a path trigger of job `unrun-picks-boards` (`.github/ci/legacy-jobs.yml:28132`), and that job runs `tests/test_prophet_board_since.py` (`:28523`). The two pre-existing failures are deterministic text asserts:
  - `:626` expects one `include "_us_board_cards.html.j2"` in `templates/dashboard.html.j2`, but BASE has two (lines 17097 and 17341, last touched by #9517/#9550 on 10-17);
  - `:377` checks the Canada laggards strip tokens.
  A CA-ZB PR therefore inherits a red `unrun-picks-boards` until those are repaired. This is a seat routing item and outside this lane's owned files.
