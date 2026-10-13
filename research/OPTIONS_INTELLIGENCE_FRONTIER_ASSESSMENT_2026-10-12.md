# Options Intelligence — frontier assessment and upgrade plan (2026-10-13T02:3xZ)

Status: seat assessment, owed by ledger D52(c). Programme `options-intelligence` (Terminal #599); packet
`Mastermind_Options_Fable_End_to_End_2026-10-11` (masterplan §8 stages A–F, 36 work packages, 169 acceptance
assertions). Companion to `OPTIONS_INTELLIGENCE_CONTINUATION_HANDOFF_2026-10-11.md` (the ledger); where they
disagree, the ledger's latest D-entry wins. Rungs follow the nine-fact ladder (ACK → QUEUED → START → RUNNING
→ DELIVERED → CI → MERGED → PRODUCTION_PROOF → ACCEPTANCE); no status below claims a higher rung than its
evidence.

## 1. Headline

- **Landed (MERGED):** F01 chain heat (#8922), M01 gamma-regime consumer (#8921), MT test pins (#8918),
  V01 (#8851), D16a resolver (#8856), #7861 retention writer (its own owner). OC package closed Q01.
- **In flight:** M02P #8920 (blocked by a semantic proof refusal, cause unknown), D04A #8923 (held for the
  Tuesday 2026-10-13 observation window, runner armed), N01-T1 #948 (CI re-running at `a976f73ade59`), U01
  step 1B / #723 (REQUEST_REPAIR r1).
- **Untouched packages:** F02, F03, F04, M03, M04, V02, V04, Q03, Q04, N02, N03, U03, U04, R01–R04, C00.
- **Gated by someone other than this seat:** D01 root fix (m1 TCC), Q05 (#8555/#7328 holders), R05 (Sol),
  U02 (SQL approver; D12 scoped-only), D17(ii)/O-9(ii) synthetic `history/` write (source owner), m1 grok
  login, MCP OAuth.
- **Binding throughput constraint has moved** from m2 fabric admission (O-14) to seat judgment turns: the
  grok CLI carrier (D52) gives four Linux hosts with ~30 free cores each. The upgrade below is therefore
  primarily a *parallelism* upgrade: census every untouched package at once, then build only from frozen,
  falsifier-first commissions.

## 2. Package frontier (G00–C00)

| Pkg | Rung / state | Evidence | What is left |
|---|---|---|---|
| G00 | ACCEPTANCE | D20 custody | — |
| G01 | CLOSED PARTIAL | O-1 | A02 deferred until fabric admission (optional) |
| D01 | Measured: CURRENT NOT SERVICEABLE (D15); O-2 falsifier ACCEPTED by the Codex root (D54) | D15, D54; macro #8884 issuecomment-6135018681 / #9029 | Matrix data acceptance is the root's (second natural run Tue 23:00Z, follow-up 00:00Z — never duplicated or forced); root fix m1 TCC (user) |
| D02 | Crosswalk ACCEPTED (D32) | D32 | A02–A05 producer fixes (D18) — READY since #7861 merged |
| D03 | Plan R1–R7 | D03 plan | D03-Q red tests on the one retention writer (#7861), then implementation |
| D04 | D04A DELIVERED → #8923 HELD | D52/D53 | Tuesday window → label swap → `status()` projection + macro-api restart → strict; full Intraday proof |
| D16a | MERGED #8856 | D42 | Natural resolver proof on m1 (`resolved store=…`) — observe, never manufacture |
| D16b | READY | D16 | `ops/launchd/run_options_matrix.sh` bounded gate read with stderr |
| D16c | Defined | D16 | F3 backfill reclassify race, F4 `publish_r2` default-path fallback, F5 `--theta-store` message, F9 identity vs presence, 14 unassessed call sites |
| F01 | MERGED #8922 | D52 | `side_basis` (F01 Q3) handed to F02 |
| F02 | Not started | — | F02-A01..A04 on carrier #7417; owns `_detect_sweeps` region of `engine/live_flow.py` + `engine/flow_enrich.py` |
| F03 | Untouched | — | Carriers #7398/#8350/#8205/#7265/#7263/#7193; gate = unknown effects + publication-writer binding |
| F04 | Untouched | — | #7290/#8345/#8358(inactive)/#599; inert fixtures until an activation receipt |
| M01 | MERGED #8921 | D52 | Deferrals: MINOR-5 `options_hub.py:636-639`/`:746-750`, `_bs_g` `:507-519`, NaN flip `market_gamma.py:189-197`, `GexSummaryBar.tsx:145` (after #723), MINOR-6 replay measurement |
| M02 | #8920 blocked | D53 | Diagnose `test_main_cli_pre_rows_blocks_no_op_accrue` head-vs-base; CLI `TypeError` at `scripts/build_options_scenario_surface.py:39`; then close #8684 |
| M03 | Waits for #8920 | D52 overlap | Shares `engine/options_scenario_surface.py` |
| M04 | Untouched | — | Depends on M02/V01; #7328 held |
| V01 | MERGED #8851 | — | Natural proof pending |
| V02 | Untouched | — | #780; Terminal `lib/__tests__/expiryTermStructure.test.ts`, `volatilityConflictContinuity.test.tsx`, `components/vol/*` |
| V03 | Untouched | — | READ-ONLY reconciliation of Sol #781 (`85d9f4eae172`) |
| V04 | Untouched | — | #7405/#8318 |
| Q01 | CLOSED | D13 + OC | DR-6 bookkeeping owed by #8385 author |
| Q02 | Adapter NOT ADOPTED (D45) | MT merged | Adoption only after Q03 data qualification |
| Q03/Q04 | Untouched | — | Data-qualification gate |
| Q05 | GATED | D33 | #8555/#7328 holders |
| N01 | #948 at CI | D53 | Merge → deploy `--target-sha` → live chunk grep; natural windows 10-15/16, 11-02, 11-27 |
| N02 | Design lane | — | Return-only design |
| N03 | Untouched | — | — |
| U01 | 1B DELIVERED (pushed `14a331f8`); 1C RUNNING | D53, D54 | oi-1c (mmx-ubuntu0) → judge → Paper parity PP1/PP2 (below) → independent exact-head review → ship #723 with #599; step 2 = #846 refresh |
| U02 | SCOPED ONLY (D12) | — | Save OFF until D03 + source-use rights interface; SQL approver (O-5) |
| U03/U04 | Untouched | — | Depend on #846 |
| R01–R04 | Per vertical release | — | After each vertical's MERGED + PRODUCTION_PROOF |
| R05 | GATED (Sol) | charter #7711 | — |
| C00 | Final | — | Capability ledger after R01–R04 |

## 3. What would make the programme materially better (upgrades)

Each upgrade names the consumer capability it unlocks (no infrastructure without a consumer) and stays
inside the masterplan's no-new-plane rule (no new collector, store, pricer, replay clock, candidate
lifecycle, queue, auth or evaluation plane).

1. **Census-before-build for every untouched package (U-1).** One READ-ONLY grok lane per package turns the
   packet's planned falsifiers into a vector table (PROVEN / OWED / CONTRADICTED with `file:line`), red-test
   specs, and one frozen build commission with owned files. Unlocks: build waves that cannot collide (O.1) and
   cannot silently narrow (each assertion ID is carried to a test). Packages: F03, F04, V04, M03, M04, N03,
   U03, U04, R04, Q03 (10 lanes).
2. **Falsifier-first build lanes on the READY frontier (U-2).** F02-Q, D18-A, D03-Q, D16b, M01-D, V02-Q each
   start with red tests on the exact acceptance IDs, then the fix. Unlocks: sweep/side basis in live flow (F02),
   producer contract truth for the matrix (D18), one retention writer under test (D03), observable launchd
   gate failure (D16b), regime consumer edge cases (M01-D), expiry term-structure continuity (V02).
3. **Unblock the stalled delivery chain (U-3).** 8920-R1 (diagnose the semantic refusal by bisecting the
   stacked #8684 commits and the main merges), oi-1c (finish #723), TFLAKE (the two unowned Terminal flakes
   that red unrelated PRs). Unlocks: M03, U01 step 2, every Terminal PR's CI signal.
4. **Independent exact-head review by a different host (U-4).** Every build return gets a READ-ONLY grok review
   on another host before the seat opens or arms anything (replaces the forbidden native Opus auditor).
5. **Natural-cycle proof harvesting (U-5).** D16a, V01, D01 falsifier, D04 window: read-only observations of
   runs that happen anyway, written into the ledger as PRODUCTION_PROOF — never manufactured runs.
6. **Copy and contract follow-ups after #723 (U-6).** New string key for the partial-total note; O-13
   one-decoder adoption (`GexDeskView`, `StrikeExpiryMatrix`, `aggTrend`, `HeatSeekerCard`); M01 Terminal
   deferral `GexSummaryBar.tsx:145`.

7. **#723 Paper parity (U-7, P1 — material acceptance for #723, Codex continuation D54).** Bind Paper file
   `01M3NSZGE8JWN2EZCSF0DT05RM` (Options p-2-0, build ref p-P-1). Scope frozen in #723 issuecomment-6136994735:
   P-A reading hierarchy (map, scope and selected node together near the top; production matrix starts at
   y=816.6 / 1083.0 / 1804.5), P-B receipt clocks only where supplied, P-C exact strike/DTE, P-D newer snapshot
   announced not swapped under a selection, P-E missing-vs-zero key/hatch, P-F chart → map → node → return with
   scroll restoration, P-G doc pointer. Unlocks: an Options map whose first screen answers "where is the
   exposure, for which scope, at which node" on every viewport. Lanes PP1 (P-B/P-C/P-D/P-E) and PP2
   (P-A/P-F/P-G) start only after the Codex root returns accepted criteria from its own GLM contract task
   `fable-paper-parity-build-contract-20261013` (not this seat's: never duplicated, partial stdout never read)
   and after the oi-1c return is judged; they are serialized on the #723 lane branch and placed through a
   fresh read of the installed Fabric skill and current normal admission. A quality gap goes back to the root
   as viewport / node / measured delta.

## 4. Wave 3 (launched with ledger D54)

| Lane | Host | Kind | Owned files / scope |
|---|---|---|---|
| CEN-F03, CEN-F04, CEN-V04, CEN-M03, CEN-M04, CEN-N03, CEN-U03, CEN-U04, CEN-R04, CEN-Q03 | ubuntu0 / ubuntu3 / mastermind-pc | READ-ONLY census | return dir only |
| oi-1c | mmx-ubuntu0 (`~/lanes/wt/oi-1c`) | build (continuation) — LAUNCHED 02:51:36Z | #723 lane branch |
| 8920-R1 | ubuntu0 | diagnose + bounded fix | #8920 own files / tests |
| TFLAKE | ubuntu3 | build | `lib/__tests__/aiContext.test.ts`, `guideExperience.test.ts` |
| F02-Q | ubuntu0 | build | `engine/live_flow.py` sweep region, `engine/flow_enrich.py`, appended tests |
| D03-Q | ubuntu3 | build | `tests/test_options_matrix_retention.py` (+ minimal retention module) |
| D16b | mastermind-pc | build | `ops/launchd/run_options_matrix.sh` (+ appended test) |
| V03 | ubuntu3 | READ-ONLY review | Sol #781 |
| N02 | mastermind-pc | design | return dir only |

D18-A, M01-D and V02-Q are frozen next: D18-A after the 8920-R1 return (shared `engine/thetadata_store.py`),
M01-D after F02-Q (no shared files but one Macro gate budget), V02-Q after #723 merges (it changes
`terminal/lib/expiryTermStructure.ts`). There is no seat O-2 lane: the natural matrix proof is the Codex root's (D54). Every build lane appends to CI-wired test files (contract-delta), runs `tests/test_ci_pack.py`
when it adds an import edge between top-level packages, never opens a PR, and returns by artifact. The seat
judges, opens PRs, labels (Macro: `merge-on-green` only; Terminal: label + `--auto`), deploys and verifies.

## 5. Pre-mortem (wave 3)

1. A census lane edits files → tripwire: census worktrees are detached at a pinned SHA and the return dir is
   the only write target; the seat diffs `git status` of each census worktree on return.
2. Two build lanes touch `engine/thetadata_store.py` → D18-A is serialized behind 8920-R1.
3. A lane ends at its turn budget on a status note → every commission puts the return first ("write the return
   file before any optional step") and caps items at ten.
4. Foreign sessions saturate a host → launch only where load1 < 16; a refused host is recorded, not routed
   around by killing anything.
5. An early Macro merge → the seat never runs `--auto` on Macro (D52 law).
6. A lane reads credentials → FORBIDDEN clause plus the prompt wrapper's hard limits; the seat greps each
   stdout for key-shaped strings before rsyncing anything into the repo.

## 6. User-only controls (unchanged by this plan)

- m1: Full Disk Access for the matrix launchd job (D15 root fix); grok login on m1.
- MCP OAuth for `linear-server`, `mastermind-executive`, `figma` (via `/mcp`); `mmx-cimd-probe` unreachable.
- Sol: R05 acceptance; #781 custody.
- #8555 / #7328 holders: Q05.
- U02 SQL approver (O-5); D17(ii) synthetic `history/` write (source owner); #6867 HOLD-FOR-SOL.
- m2 host load and pipe memory (O-14); the Vercel daily deployment limit on preview comments.
