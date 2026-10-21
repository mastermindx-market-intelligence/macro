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
| pro-regional-cnscout-20261021-r1 | census | mmx-ubuntu0 | DONE rc=0 03:33Z, lane STATUS DONE | lane commit f18ef8a8ea7: `research/prophet_v4/r7_program/regional/CN_CORRECTNESS_CENSUS_2026-10-21.md` (12 questions: PRESENT 2 / PARTIAL 7 / ABSENT 3) |
| pro-regional-hkscout-20261021-r1 | census | mmx-ubuntu3 | RUNNING (poll 27 @03:45Z) | — |
| pro-regional-cascout-20261021-r1 | census | mmx-ubuntu3 | RUNNING (poll 24 @03:45Z) | — |
- 03:27Z: CNA-CIE04-06 row corrected to BLOCKED-DATA (CIE package pin 1b0f2ee2 absent from macro + local Mastermind) → Decision F4. Both round-1 lanes on mmx-ubuntu0, pending.
- 03:32Z: hkscout round-2 lane launched (`pro-regional-hkscout-20261021-r1`, census). cnscout still pending.
- 03:35Z: cazb consumed. Diff read on ubuntu0 and matches the frozen spec: `setups` None/non-dict keeps SKIP; a dict with empty buy no longer returns early; `append_board` is withheld with an info log; scorecard/grade/track/shadow still run; health starts with the identical SKIP row; the non-empty path is unchanged. T6 showed T1 fails at BASE ("write_shadow must run exactly once; got 0"). Suites: board_shadow 69 passed, canada_build 13, board_ledger 69, canada_canonical_board 35. prophet_board_since: 2 failed, which the lane reproduced at a pristine BASE extraction, so they are pre-existing.
- 03:38Z: CI consequence verified at BASE. `scripts/build_canada.py` is a path trigger of job `unrun-picks-boards` (`.github/ci/legacy-jobs.yml:28132`), and that job runs `tests/test_prophet_board_since.py` (`:28523`). The two pre-existing failures are deterministic text asserts:
  - `:626` expects one `include "_us_board_cards.html.j2"` in `templates/dashboard.html.j2`, but BASE has two (lines 17097 and 17341, last touched by #9517/#9550 on 10-17);
  - `:377` checks the Canada laggards strip tokens.
  A CA-ZB PR therefore inherits a red `unrun-picks-boards` until those are repaired. This is a seat routing item and outside this lane's owned files.

- 03:40Z: cascout round-2 lane launched (`pro-regional-cascout-20261021-r1`, census: Canada + shared). Both live slots are now the two scouts on mmx-ubuntu3.
- 03:40Z: cnscout consumed. The report was read from the lane tree and copied to seat scratchpad `cn_census.md`. It drives the CN-P0..P4 rows.
- 03:42Z: China collision census from the PR file sets of the named incumbents (#6871 4 files, #8444 71, #7669 all 471, #8184 3, #7018 27, #7286 4, #7385 4, #7288 4, #7303 3, #7248 3, #6996 2, #7499 52). Results:
  - Nothing touches `scripts/build_cn_live_pack.py`, `scripts/build_china_library.py`, `collectors/china_margin_detail.py`, `templates/cn_prophet_live.js` or the China test files.
  - `templates/_prophet_card.html.j2` is in #8444, and `templates/china.html.j2` is in #8184 (sol/).
- 03:44Z: round-3 build packets written. Both passed the launcher pre-checks (no `HOLD-` token, no stray `validated`, only `__BASE__`, `{COMMON}` present):
  - `$S/pk/pro-regional-cnp1trad-20261021.md`: China P1 full-universe tradability wired into the live pack, strict on a missing key or empty map. CI job `express-render-guards`.
  - `$S/pk/pro-regional-cnp4margin-20261021.md`: China P4 margin prior-window repair at `collectors/china_margin_detail.py:156`. CI job `unrun-intl-collectors`.
  - Both wait for a free slot once the scouts end.
- 03:46Z: disposition §1 rows CN-P0..P4 written: P0 BLOCKED-CUSTODY (#6871 R0 carrier), P1 READY, P2 BLOCKED-ORDER + F3b, P3 F2 + SSR half behind #8444, P4 margin READY. F3 rewritten and F6 added (inherited reds on `unrun-picks-boards`).
- 03:50Z: found a P1 defect the census missed. `load_frozen` (`scripts/build_cn_live_pack.py:45-79`) never reads the real board, `site/factordata/china_standouts.json`, so the production frozen score/rank is empty. Wrote packet `$S/pk/pro-regional-cnp1proj-20261021.md` from #8714 `REPAIR_DECISIONS.md:59,70` (157 lines; pre-checks pass). Launch order when the scouts free the slots: cnp1proj + cnp1trad (handoff step 2), then cnp4margin (step 4).
- 03:54Z: wrote packet `$S/pk/pro-regional-cnp1arch-20261021.md` (117 lines; pre-checks pass) and added F7 to the disposition. The packet covers China P1 (iii): a content-addressed archive written before the current-key replace, with intended session and source-board identity. It is gated by sequence: it launches on the main revision containing cnp1proj+cnp1trad, after F7 is ratified, and is not launchable at BASE. CI-line collision check: only cnp1proj adds a line at BASE (cnp1trad extends an existing `express-render-guards` test), so the two BASE lanes merge on disjoint hunks.
