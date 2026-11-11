# Lane 9 — integrated evidence join (phase A)

Written 2026-11-10T03:50Z by lane 9 (read-only). Scope: the v1.1 amendment §12 (SI01–SI20) and
§13 (SP01–SP24), joined against eight lane returns, the PR heads re-read at 10:2x–10:3xZ, and
spot checks of the named artifacts at those heads. Nothing here was executed as a test; no suite
was run; no host was contacted. A lane's own "done" is recorded as a claim unless the named
artifact was seen at the named head.

## Class counts (44 rows total)

| class | count | ids |
|---|---|---|
| `SERVED` | **0** | — |
| `REAL-BYTES-LOCAL` | **7** | SI01, SI02, SI18, SP01, SP02, SP14, SP15 |
| `REAL-ENGINE` | **6** | SI08, SI10, SI12, SP11, SP21, SP22 |
| `FIXTURE` | **7** | SI13, SI17, SP07, SP10, SP13, SP20, SP23 |
| `CONTRACT-ONLY` | **10** | SI04, SI05, SI06, SI07, SI09, SI11, SI15, SI19, SP17, SP19 |
| `NOT-EXECUTED` | **13** | SI03, SI14, SI20, SP03, SP04, SP05, SP06, SP08, SP09, SP12, SP16, SP18, SP24 |
| `UNPRODUCED` | **1** | SI16 |

No row is `SERVED`. The single live check ever run (Step A, lane 3, ~09:28Z) returned a real
refusal, not a product: a genuine member sign-in succeeded, and the deployed Terminal route
answered `400 {"error":"invalid_source"}` because #1414 is not merged. That observation is
evidence of absence, and is cited where relevant; it closes no row.

## PR heads used (re-read this session, one read each)

| carrier | repo | head | state as read |
|---|---|---|---|
| #10929 lane 1 generation + population route | macro | `9c5db069856d1cd71def5e5ce575e79953a7a301` | OPEN, draft, labels `hold`/`do-not-merge`/`merge-blocked` |
| #10924 lane 8 analytics | macro | `f1337bdd8738995aa01bde14374dfc5a4ef99acf` (artifacts checked at `3e6b51ef09fc`) | OPEN, `merge-on-green` + `merge-blocked`, UNSTABLE |
| #10923 lane 2 Paper design | macro | `8abe28febaf08b48da95745b2cec7ac5d9cfab8d` | OPEN, `merge-on-green` |
| #10931 lane 5 research | macro | `3290bfe75f965469945471cb96db0cf2a768a0b4` | OPEN, no labels |
| #10945 lead status record | macro | `0f62091bf7c24c60c0210ee1439c19e054065f4a` | OPEN, `merge-on-green` |
| #1414 lane 3 workspace/BFF | terminal | `3004b74f48bc375af7488e645accc5052700d40e` | OPEN, `merge-on-green`, CLEAN |
| #1413 lane 4 Cycles | terminal | `a8cf1f5d7250b2e7e00340f9ef7638bdde9076c0` | OPEN, `merge-on-green` + `merge-blocked`, BLOCKED |
| #1410 lane 6 investigations | terminal | `dc02f1c28879178f309f16ab381ac1cf17216cae` | OPEN, `merge-on-green`, CLEAN |
| #1425 lane 6 v3 readers + 0053 | terminal | `57d63a5e6d8f467bcf8845d2a48bc9d9cf4cc572` | OPEN, unarmed, BEHIND (stacked on #1410) |
| #1419 lane 7 retained depth | terminal | `f6f2bfac4ef8dbdfd7df32ad0e7c404419ff393c` | OPEN, unarmed, BEHIND |

Lane 3's v1.1 delta branch `claude/ssd-si-lane3-v11-consumer-20261110` has **no pull request**
(`gh pr list --head … --state all` → `[]`). Everything the lane 3 return says it built after
`3004b74f48bc` is therefore not visible in GitHub and cannot be verified or joined.

## A. The join

### SI rows (cross-contracts)

| id | requirement | owner | best evidence today | class | PR @ head | test / artifact | missing → owner |
|---|---|---|---|---|---|---|---|
| SI01 | One exact Sector capture travels into the Prophet read bundle | 1/3 | Capture compatibility tuple `sector_population.capture/v1` produced from the real committed `site/` artifacts through the real publisher/reader/route; SHA-pinned sample | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `lib/sector_population.py`; `tests/test_sector_population.py::test_real_population_is_full_ordered_joined_and_bounded`; sample sha256 `10b4b955…e9c` | No Prophet consumer binds the tuple; BFF still forwards the **legacy** `?audience=preview` path → lane 1 wire + lane 3 (unpublished branch) |
| SI02 | Full point-in-time identity, membership and population | 1/8 | Real full population: configured-current 1020, served 1015, accounted-unserved 5, unaccounted 0, 26 removed; both industry fields on separate current basis (617/698 GICS, 424/698 S&P sub-industry) | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `tests/test_sector_population.py::test_industry_is_current_basis_not_point_in_time_and_never_relabelled`; `tests/test_sector_central_carry.py::test_industry_and_sub_industry_are_separate_current_basis_taxonomies` | PIT membership, first-known time, original affiliation, taxonomy revision are `unavailable/not_produced` — **no producer exists**; owner unassigned (lane 1 and the panel roster owner both named, neither ships it) |
| SI03 | Connected journey Sector → Prophet → evidence → precise return | 3 | Step A: real member sign-in succeeded; deployed route refused `400 invalid_source`; consumer path exists only on an unpublished branch | `NOT-EXECUTED` | #1414 @3004b74f (route only) | `terminal/app/api/sector-intelligence/route.ts` adds `generation: SECTOR_GENERATION_PATH` (legacy preview path) | Whole journey unproven; return-state codec tests are fixture-level → lane 3 (no PR for the delta) |
| SI04 | Absolute / relative / wealth / beta / residual kept separate | 8/3 | B04 metric definitions enumerate the separation; Cycles UI shows rebased series on fixtures | `CONTRACT-ONLY` | #10924 @f1337bdd (doc), #1413 @a8cf1f5d | `research/sector_completion_20261021/B04_METRIC_DEFINITIONS.md`; `terminal/lib/__tests__/sectorCycle*.test.ts` | No served surface separates all five; no wealth/residual series produced → lane 8 (definitions) / lane 3 (render) |
| SI05 | All-alias issuer exclusion for independent support | 5/8 | Lane 5 contract doc exists; alias exclusion **not stated** in any return | `CONTRACT-ONLY` | #10931 @3290bfe7 | `research/sector_completion_20261021/LANE5_RESEARCH_V2_CONTRACT_2026-11-09.md`; `engine/market_ontology/theme_research_registry.py` | No return file at all; SP04 unrun → lane 5 (no written return) |
| SI06 | Source-root dedupe, overlap and concentration | 5/8 | Contract text only; no dedupe artifact or test was named | `CONTRACT-ONLY` | #10931 @3290bfe7 | same contract doc | Dedupe/concentration not demonstrated → lane 5 |
| SI07 | Original dated company economics returned upstream | 5 | Theme-research registration code in the PR; no dated original-economics artifact named | `CONTRACT-ONLY` | #10931 @3290bfe7 | `engine/sector_intelligence/finance_research_registration.py` | Nothing states an original-economics path; no return → lane 5 |
| SI08 | Native phase/turn and per-head forecast semantics | 4/8 | Every head emitted withheld with its own reason code on the live sector build; engine contract + tests | `REAL-ENGINE` | #10924 @f1337bdd | `engine/sector_heads.py`; `tests/test_sector_forecast_heads.py::test_live_sector_build_emits_forecast_heads_all_withheld` | No live record carries the v2 epoch, so all heads stay withheld; no UI reason lines (lane 4 lex has **0** of the 5 codes at `a8cf1f5d`) → lane 4/lane 3 |
| SI09 | Original/current retained context | 6 | Contract + admitted identity fields only; lane 6 says so explicitly | `CONTRACT-ONLY` | #1410 @dc02f1c2, #1425 @57d63a5e | `supabase/migrations/0052_…sql`, `0053_…sql`; `docs/sector-intelligence/LANE6_INVESTIGATION_CONTRACT_2026-11-09.md` | No retention, rights, reopen or entitled-route proof; no migration applied → lane 6 + lane 1 + lane 3 |
| SI10 | One compatible investigation version sequence | 6 | Full `0021→…→0052→0053` chain executed on disposable PostgreSQL 17, 33 passed; ACL, rerun idempotence, down refusal, exact restore | `REAL-ENGINE` | #1410 @dc02f1c2 + #1425 @57d63a5e | `tests/test_investigation_postgres.py`; `supabase/migrations/0052_sector_intelligence_investigation_admission.sql`, `0053_investigation_v3_prophet_decision_admission.sql` | Nothing applied in production; #1312 (0051) body-pin ordering unresolved → operator + lane 6 |
| SI11 | Strategy-specific qualified policy consumption | Strategy with 3/8 | Typed Evaluation/Portfolio contracts defined; no Strategy consumer | `CONTRACT-ONLY` | #10924 @f1337bdd | `engine/sector_heads.py` (`StrategyEvaluationResult`, `validate_evaluation_result`) | No Strategy integration → Strategy owner (not in this programme) |
| SI12 | Benchmark-first economic programme | 8/Evaluation | Comparators C1–C3, C7 on real SPDR/SPY/BIL tapes with costs; C3 did not beat passive SPY | `REAL-ENGINE` | #10924 @f1337bdd | `research/sector_completion_20261021/b12/v11_heads.py`, `…/v11_heads_result.json`, `…/B12_V11_HEADS_RESULTS.md` | C4/C5 need PIT constituents (none); C6 needs the incumbent Prophet record → lane 8 + unassigned PIT producer |
| SI13 | Separate qualified Strategy evaluation adapter | Evaluation with 8 | Adapter contract + validator executed on synthetic result objects | `FIXTURE` | #10924 @f1337bdd | `tests/test_sector_forecast_heads.py::test_valid_evaluation_result_passes` | Evaluation owner has not adopted it; no registered trial → Evaluation |
| SI14 | Actual authorized exposure and correlated risk | Portfolio/Risk with 7/8 | Only ETF ΔShares×NAV flow views on a dev fixture harness | `NOT-EXECUTED` | #1419 @f6f2bfac | `terminal/components/sector-intelligence/depth/SectorFlowMatrix.tsx` | No exposure/correlation producer; no portfolio inputs → Portfolio/Risk (no lane) |
| SI15 | Material Follow through the existing producer/outbox | 6 | Not advanced in v1.1; v1.0 evidence unchanged; no producer exists | `CONTRACT-ONLY` | #1410 @dc02f1c2 | lane 6 return §SI/SP | Follow is a saved preference only; no producer/outbox → lane 6 + producer owner (unnamed) |
| SI16 | Market-native source, benchmark and execution | 1/8 | `native_sector_ref` and `prophet_eligibility` are `unavailable/not_produced` on every row; HK/CN NOT_EVALUATED | `UNPRODUCED` | #10929 @9c5db069 | lane 1 wire §1 row shape; lane 8 GAPS | No native sector crosswalk, no non-US tapes/calendars → unassigned producer |
| SI17 | Responsive, accessibility and localization | 2/3/9 | 47 R5 frames + 20 R6 roots as images; lane 4 e2e 10 passed at 390/768/1440 EN/ZH light/dark; lane 7 9 proof PNGs incl. 390 ZH | `FIXTURE` | #10923 @8abe28fe, #1413 @a8cf1f5d, #1419 @f6f2bfac | `terminal/e2e/sector-cycle-lens.spec.ts`; `terminal/e2e/sector-retained-depth.spec.ts`; `mockups/refs/sector-intelligence-r5/*.png` | No served consumer; 320 width untested; delivered against fixture data → lane 3 (mount) |
| SI18 | Degradation, corrections and private observability | 1/3/6/9 | Every refusal class carries `private, no-store`/`Vary`/`nosniff`; reset/unavailable classes tested on real bytes | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `tests/test_sector_population.py::test_duplicate_parameters_and_refusal_headers`, `…::test_retained_capture_loss_resets_and_never_substitutes_latest` | Correction lineage is `unavailable/not_produced`; no private observability emitter; UI states fixture-only → lane 1 (correction producer), lane 3 (states) |
| SI19 | Live-writer / version compatibility | Fable with 1/3/6 | `basis_version` bound into every cursor; v2→v3 compose plan written; no live-writer reconciliation | `CONTRACT-ONLY` | #10929 @9c5db069, #1425 @57d63a5e | lane 1 wire §1; lane 6 return "(c)" | No test that an old reader survives a writer change in place → lane 1/lane 6 |
| SI20 | Actual served path and compatible rollback | 9 | Deployed route returns `400 invalid_source`; no programme migration applied | `NOT-EXECUTED` | — | Step A observation (lane 3) | Nothing served; no rollback exercised → lane 9 phase B after #1414 + #10929 |

### SP rows (falsifiers)

| id | discriminating case | owner | best evidence today | class | PR @ head | test / artifact | missing → owner |
|---|---|---|---|---|---|---|---|
| SP01 | Publication advances mid-read; one capture retained | 1/3 | Real store; reader that started on capture X finishes on X, never the current pointer | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `test_sector_population.py::test_sp01_reader_that_started_on_capture_x_finishes_on_x` | Not exercised across a real publication → phase B |
| SP02 | Valid member beyond the first page is found and compared | 1/3 | Real store, 1015 members, offset signed and joined | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `…::test_sp02_member_beyond_page_one_is_reachable_and_correctly_joined` | No served continuation; lane 3 consumer unpublished → phase B |
| SP03 | Sector −2% / market −4%: absolute decline stays visible | 3/8 | No case named by any return | `NOT-EXECUTED` | — | — | No producer of the joint absolute/relative pair → lane 8 + lane 3 |
| SP04 | Issuer/alias perturbation leaves raw LOO invariant | 5/8 | No return from lane 5; LOO mentioned only for sectors in lane 8 | `NOT-EXECUTED` | — | — | Alias exclusion unbuilt → lane 5 |
| SP05 | Repeat price root does not raise independent count | 5/8 | Dedupe described in contract only | `NOT-EXECUTED` | #10931 @3290bfe7 | lane 5 contract doc | No executed case → lane 5 |
| SP06 | Concentration rises as breadth narrows; counter-case visible | 3/8 | Not named by any return | `NOT-EXECUTED` | — | — | No concentration metric/consumer → lane 8 + lane 5 |
| SP07 | Strong independently-evidenced company reachable inside a weak group | 3/7 | Calls board renders named rows with trace disclosure on the dev harness | `FIXTURE` | #1419 @f6f2bfac | `terminal/components/sector-intelligence/depth/SectorCallsBoard.tsx`; `terminal/lib/__tests__/sectorDepthCalls.test.ts` | Not mounted in the workspace; no real payload → lane 3 |
| SP08 | Membership change after decision: original stays original or unavailable | 1/6 | PIT membership unproduced; `removed_members` carries dates only | `NOT-EXECUTED` | — | — | Needs PIT membership (none) → unassigned |
| SP09 | Later US availability cannot enter an earlier Asia cutoff | 1/8 | Only `us` market profile exists | `NOT-EXECUTED` | — | — | No Asia native source → unassigned |
| SP10 | Withdraw one head; only that head disappears | 4/8 | `withdraw()` unit-tested on synthetic records; no UI reads reason codes | `FIXTURE` | #10924 @f1337bdd | `test_sector_forecast_heads.py::test_withdrawing_one_head_leaves_its_siblings_untouched` | Reason lines missing in `sectorCycleLex.ts` (0/5 codes at `a8cf1f5d`) → lane 4 |
| SP11 | Pivot known only after confirmation; history uses availability | 4/8 | H4 scored on `confirmed_at`; PIT check over 3,130 dates on real US tape | `REAL-ENGINE` | #10924 @f1337bdd | `research/…/b12/v11_heads_result.json`; `B12_V11_HEADS_RESULTS.md` | Not served; no live protocol epoch → lane 8 + lane 1 |
| SP12 | Unreported issuers keep correct eligible/reported/unknown denominators | 5 | Not named by any return | `NOT-EXECUTED` | — | — | Denominator contract exists, no executed case → lane 5 |
| SP13 | Sector → Prophet → evidence → Sector preserves account/view/filters/focus | 3/9 | e2e capture→navigate→apply return passes on the fixture harness | `FIXTURE` | #1413 @a8cf1f5d | `terminal/e2e/sector-cycle-lens.spec.ts` (10 passed, 6 by-design cross-skips) | Whole-journey case never run against a served route → lane 3/phase B |
| SP14 | Saved digest without bytes → original-unavailable, never latest-as-original | 6 | Route-level: a lost retained capture answers `404 ORIGINAL_UNAVAILABLE`, never the latest | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `…::test_original_ref_reopens_the_retained_capture_not_the_latest` | No saved-investigation reopen exists (lane 6 contract only) → lane 6 |
| SP15 | Account change during deep link/save; late private results cannot commit | 3/6 | Cross-actor cursor/context use answers reset/unavailable; unverified actor refused | `REAL-BYTES-LOCAL` | #10929 @9c5db069 | `…::test_cursor_binding_change_is_an_explicit_reset_not_a_mixed_page`, `…::test_unverified_actor_is_refused_not_bound_to_a_shared_anonymous` | Save-time account switch untested (lane 6 not executed) |
| SP16 | Fresh quote with stale sector does not refresh dependent evidence | 1/3 | Qualification is re-evaluated per page (documented, not tested) | `NOT-EXECUTED` | — | lane 1 return N3 | No clock-mix case → lane 1 |
| SP17 | Saved Follow preference without producer claims no notification | 6 | Contract wording only; no producer | `CONTRACT-ONLY` | #1410 @dc02f1c2 | lane 6 return | Producer absent → unassigned |
| SP18 | Same-context refresh emits no duplicate; correction links to original | 1/6 | Correction lineage is `unavailable/not_produced` | `NOT-EXECUTED` | — | lane 1 wire §2 | No correction producer → lane 1 |
| SP19 | Positive selection and benchmark shortfall both remain visible | Evaluation/9 | Validator forbids establishing selection value; C3 underperformance recorded | `CONTRACT-ONLY` | #10924 @f1337bdd | `test_sector_forecast_heads.py::test_selection_value_can_never_be_established_here` | No Evaluation consumer → Evaluation |
| SP20 | All-cash / near-zero benchmark / missing weights cannot fake capture | Evaluation/Portfolio/9 | Three synthetic boundary tests pass | `FIXTURE` | #10924 @f1337bdd | `…::test_near_zero_benchmark_cannot_fake_capture`, `…::test_unknown_positions_or_weights_are_unavailable_never_zero`, `…::test_all_cash_attribution_is_explicit_not_missing` | Not exercised with real portfolio inputs → Portfolio/Risk |
| SP21 | Improvement disappears after cost/exposure match; no skill claim | 8 | C3 − exposure-matched = −0.5% [−1.7%, +0.6%] on real tapes | `REAL-ENGINE` | #10924 @f1337bdd | `research/…/b12/v11_heads_result.json` (comparator table) | Research only; nothing served → lane 8 |
| SP22 | Rebound, failed old leaders, no-fill and limits stay in evaluation | 8 | Real result: 6 drawdown episodes, 326 failed leaders, 1 no-entry / 0 no-fill; validator rejects omission | `REAL-ENGINE` | #10924 @f1337bdd | `…::test_failed_leaders_rebounds_and_no_fill_cannot_be_dropped` | Not served → lane 8 |
| SP23 | 320/390, long ZH, keyboard, reduced motion keep useful action | 2/3/9 | 390/768/1440 e2e + PNGs; reduced motion not named; 320 not tested | `FIXTURE` | #1413 @a8cf1f5d, #1419 @f6f2bfac, #10923 @8abe28fe | `terminal/e2e/sector-cycle-lens.spec.ts`; `…/r5-*.png` | No 320 case, no reduced-motion run, no served surface → lane 2/3 |
| SP24 | Ordinary served release / refresh / correction / rollback preserve source and originals | 9 | Never run | `NOT-EXECUTED` | — | — | Nothing served; no rollback → phase B |

## B. Spot verification (`EXISTS` / `NOT-FOUND`)

Every row classed `REAL-BYTES-LOCAL` or `REAL-ENGINE` is listed. Checked with
`gh api repos/<repo>/contents/<path>?ref=<sha>` (or a raw read + `grep` for a named test function).
No suite was run.

| row | named evidence | head checked | mark |
|---|---|---|---|
| SI01 | `tests/test_sector_population.py::test_real_population_is_full_ordered_joined_and_bounded`; `lib/sector_population.py`; `lib/sector_generation_wire.py`; `app/sector_generation_reader.py`; sample sha256 `10b4b955…` | macro `9c5db069` | **EXISTS** (blobs `852a6e21`, `1f24b682`, `a49f299c`, `29259896`; sample re-hashed on disk → `10b4b955…e9c` matches) |
| SI02 | `…::test_industry_is_current_basis_not_point_in_time_and_never_relabelled`; `tests/test_sector_central_carry.py::test_industry_and_sub_industry_are_separate_current_basis_taxonomies` | macro `9c5db069` | **EXISTS** (functions present at file lines 190 and 84) |
| SI08 | `engine/sector_heads.py`; `tests/test_sector_forecast_heads.py::test_live_sector_build_emits_forecast_heads_all_withheld` | macro `3e6b51ef` (pre-addendum; file unchanged by addendum) | **EXISTS** (`a4079b06`; function at line 121) |
| SI10 | `tests/test_investigation_postgres.py`; `0052_…sql` on #1410; `0053_…sql` on #1425 | terminal `dc02f1c2`, `57d63a5e` | **EXISTS** (`aa1cf569`; migration listings show `0052_sector_intelligence_investigation_admission.sql` at #1410 and both 0052 + `0053_investigation_v3_prophet_decision_admission.sql` at #1425) |
| SI12 | `b12/v11_heads.py`; `b12/v11_heads_result.json`; `B12_V11_HEADS_RESULTS.md` | macro `3e6b51ef` | **EXISTS**, at a different path than the return states: `research/sector_completion_20261021/b12/v11_heads.py` and `…/v11_heads_result.json` (blob `bab975c3`); the return's `b12/v11_heads.py` is NOT-FOUND at repo root |
| SI18 | `…::test_duplicate_parameters_and_refusal_headers`; `…::test_retained_capture_loss_resets_and_never_substitutes_latest` | macro `9c5db069` | **EXISTS** (lines 384, 468) |
| SP01 | `…::test_sp01_reader_that_started_on_capture_x_finishes_on_x` | macro `9c5db069` | **EXISTS** (line 264) |
| SP02 | `…::test_sp02_member_beyond_page_one_is_reachable_and_correctly_joined` | macro `9c5db069` | **EXISTS** (line 222) |
| SP11 | `research/…/b12/v11_heads_result.json` + protocol-epoch test | macro `3e6b51ef` | **EXISTS** (`test_protocol_epoch_is_the_v2_close_price_14pct_epoch`, line 38) |
| SP14 | `…::test_original_ref_reopens_the_retained_capture_not_the_latest`; `…::test_retained_capture_loss_resets_and_never_substitutes_latest` | macro `9c5db069` | **EXISTS** (line 484, 468) |
| SP15 | `…::test_cursor_binding_change_is_an_explicit_reset_not_a_mixed_page`; `…::test_unverified_actor_is_refused_not_bound_to_a_shared_anonymous` | macro `9c5db069` | **EXISTS** (line 290, 403) |
| SP21 | comparator table in `v11_heads_result.json` | macro `3e6b51ef` | **EXISTS** (blob `bab975c3`) |
| SP22 | `…::test_failed_leaders_rebounds_and_no_fill_cannot_be_dropped` | macro `3e6b51ef` | **EXISTS** (line 159) |

Supporting claims checked while joining (not `REAL-*` rows, recorded because they change the join):

| claim | head checked | mark |
|---|---|---|
| lane 7 components exist (`SectorCallsBoard.tsx` at `terminal/components/sector-intelligence/SectorCallsBoard.tsx`) | terminal `f6f2bfac` | **NOT-FOUND** at that path; **EXISTS** under `terminal/components/sector-intelligence/depth/` (with `SectorBottomingWatch`, `SectorFlowMatrix`, `SectorThemeCompare`, `SectorConfluenceUniverses`, `DepthUnavailable`); `terminal/lib/sectorLegacyMap.ts` **EXISTS** (`c7e2c814`) |
| lane 4 e2e claim (10 passed) | terminal `a8cf1f5d` | spec **EXISTS** (`4fa0e2f5`); 8 `sectorCycle*.test.ts` files **EXIST**; pass counts are author-claimed, not re-run |
| lane 4 lexicon carries lane 8's reason codes | terminal `a8cf1f5d` | **NOT-FOUND** — `terminal/lib/sectorCycleLex.ts` contains **0** of the five reason-code strings |
| lane 3 population consumer (decoder with `population`, `typed_blocks`, `CURSOR_RESET`, `ORIGINAL_UNAVAILABLE`, `unserved_members`) | terminal `3004b74f` | **NOT-FOUND** in `terminal/lib/sectorIntelligence.ts` (only a comment uses the word "population"). BFF `SECTOR_GENERATION_PATH` = `"/api/sector-generation?audience=preview"`, i.e. the legacy path |
| lane 3 v1.1 consumer branch has a PR | terminal | **NOT-FOUND** (`gh pr list --head claude/ssd-si-lane3-v11-consumer-20261110 --state all` → `[]`) |
| lane 8 named new head `f1337bdd8738` | macro | **EXISTS** and is now the PR head (moved after the first read at `3e6b51ef09fc`) |
| lane 1 route file at repo root `app/sector_generation.py` | macro `main` | **NOT-FOUND** on `main` (the population route and the file are new on the branch) |

## C. Contradictions

1. **Where the typed blocks live.** Lane 1 emits the seven blocks at
   `projection.data.typed_blocks.<name> = {status, reason, value}` of the **legacy** projection.
   Lane 7 asks for parsed `action_board` / `bottoming_watch` / `etf_flows` / `confluence` /
   `theme_table` from `lib/sectorNativeGeneration.ts`, i.e. top-level native-generation keys, and
   its components read that shape. Neither side has been adapted to the other. Lane 1's wire even
   asks lane 7 to "confirm `theme_context.themes` is the `theme_table` you need"; no confirmation
   appears in lane 7's return.
2. **`etf_flows` shape.** Lane 7's matrix is 11 SPDRs × 1/3/5/10/21-day windows of ΔShares × NAV
   with `as_of` + depth. Lane 1 carries `flow_desk.json#etf_tile` verbatim as a "sector-SPDR
   creation/redemption proxy" whose committed artifact is dated **2026-08-13**. Both lanes call it
   `etf_flows`; neither has shown the carried value satisfies lane 7's window/depth contract.
3. **Two lanes claim the population consumer.** Lane 3's return says the population fetch and
   field mapping exist in one decoder module; that module at the only published head
   (`3004b74f48bc`) contains none of it, and the branch that supposedly carries it has no PR.
   Lane 3 also says lane 7's parser exposure is "not yet mounted", which the code confirms.
4. **Reason-code ownership is unassigned.** Lane 8 asks lane 3 (UI copy) *and* lane 4 (Cycles) for
   the five EN/ZH reason lines; lane 3 returns it to lane 4 as a shared-file request; lane 4 has not
   returned a v1.1 delta and its lexicon at `a8cf1f5d` has zero of the codes. Nobody owns it.
5. **`hazard_qualification` has no owner.** Lane 1 emits it as `unavailable/not_produced` until
   #10924 merges; lane 8 asks "owners of `scripts/build_cycle.py` and
   `engine/commodity_cycle_state.py`" to route through `qualify_current_model` without naming a
   lane, and neither file is in any lane's returned scope.
6. **Cursor durability contradictions compose into a dead path.** Lane 1 tells lane 6 to persist
   `context_ref` only when `retained_resolver_ref_durability == "durable"`; lane 6 says
   `context_ref` is "a persisted hint only". The secret that makes it durable
   (`SECTOR_GENERATION_CURSOR_SECRET`) is provisioned nowhere, and no lane owns provisioning, so the
   only lawful state today is "do not persist".
7. **Lane 7's return is stale against its own PR.** The return has `<!-- PR_URL -->` /
   `<!-- HEAD_SHA -->` placeholders and says the commit "is not on the remote and there is no PR";
   PR #1419 exists at exactly `f6f2bfac4ef8`. The return's evidence section is still empty.
8. **Lane 4's return is v1.0.** Head there is `df1824c57a59`; the PR is `a8cf1f5d7250` and blocked.
   Nothing in the return covers the v1.1 delta (withdrawal state, confirmed vs first-known, R3
   wording).
9. **Lane 5 and lane 2 have no return at all.** `returns/lane5.md` and `returns/lane2.md` do not
   exist. Lane 5 has real source on #10931 and a moved head; nothing it claims can be joined.
   Lane 2's #10923 is PNGs plus a guide — a design artifact, which cannot close SI17 on its own.
10. **Unowned by any lane:** point-in-time constituent membership (blocks SI02, SP08, C4/C5);
    `prophet_eligibility`; the native-sector crosswalk (`xlf` ⇄ `sector:financials` deliberately not
    invented); the correction-lineage producer (SP18, SI18); a Follow producer/outbox (SI15, SP17);
    `SECTOR_GENERATION_CURSOR_SECRET` provisioning; and the migration APPLY itself.
11. **Terminal #1413 is BLOCKED while armed** (`merge-on-green` + `merge-blocked`), and #1425/#1419
    are BEHIND and unarmed. #1414 is the only clean armed Terminal carrier. Macro #10929 carries
    `hold` + `do-not-merge` + `merge-blocked` and is a draft.

## D. Served today

- **Default branches carry none of this programme's changes.** Every carrier above is an open PR;
  no programme PR is merged. `lib/sector_population.py` does not exist on macro `main`; the
  Terminal `master` route table has no `generation` source (`grep` of
  `terminal/app/api/sector-intelligence/route.ts` at `master` shows `sector, confluence, themes,
  heatmap, finviz, risk, history, events, relative_trend, holdings, intraday` only, and
  `invalid_source` at line 166).
- **Deployed.** The live Terminal BFF answered `400 {"error":"invalid_source"}` for
  `?source=generation` (Step A, ~09:28Z). The source confirms why: the deployed route table is the
  `master` table above.
- **No migration of this programme is applied.** The installed manifest validator is still the
  0040 body (`md5 16f7838c…`); the 0049 guard in 0052/0053 would refuse today. Operator order when
  applied: **0042 → 0047 → 0052 → 0053**.
- **What a signed-in member actually sees today:** the existing Sector product on the deployed
  build (its pre-programme surfaces), and — for this programme — nothing. No full population, no
  depth components in the workspace, no Cycles lens in the dossier, no saved investigation, no
  forecast-head reason text. The R5/R6 designs, the dev harnesses (`/dev/sector-cycles`,
  `/dev/sector-depth`) and every component exist only on PR heads.
- **Only on a PR head:** lanes 1, 3 (workspace/BFF/legacy generation transport), 4, 6, 7, 8 and the
  paper designs. **Only in a local, unpublished branch:** lane 3's v1.1 consumer path.

## E. Rollback (one combined ordered list)

Each step names whether its down path has been tested.

1. **Stop v3 creation at the app seam** (keep the v3 admission closed in
   `parseInvestigationCommand`; readers for v1/v2/v3 created records stay). — **not tested**
   (writes are already closed; no execution exists).
2. **v3 carrier V (0053) down** — restores the sector body 0052 exactly and strands no created v3
   record; ships in `0053_investigation_v3_prophet_decision_admission.sql`. — **down path written,
   not tested against the pinned 0053 body** (lane 6's real-engine run covered the chain to 0052
   and the exact 0052 restore; 0053 down is authored, and #1312/0051 ordering is unresolved).
3. **Sector carrier S (0052) down** — restores the 0047 body exactly. — **tested** on disposable
   PostgreSQL 17 (`tests/test_investigation_postgres.py`: exact 0052 restore, down refusal with a
   stored v3 row, re-apply).
4. **Lane 1 route** (`GET /api/sector-generation/population`, and the legacy route's additive
   `typed_blocks`): rollback = revert/close #10929. No schema, no stored state, no migration; the
   legacy projection hash is unchanged when no block is produced, so reverting the route leaves
   serving byte-identical. Outstanding cursors and `context_ref` become unrecognised (answer
   `409 CURSOR_RESET` / `404 ORIGINAL_UNAVAILABLE`) — that behaviour is **tested**; the deployment
   revert itself is **not tested**.
5. **Lane 3 consumer** (BFF `generation` source + workspace): rollback = revert #1414. The deployed
   route table returns to `master`'s (no `generation`), which is the already-observed state
   (`400 invalid_source`), so the down path is effectively proven by today's deployment; the
   v1.1 delta branch has no PR and therefore nothing to roll back.
6. **Order matters:** 1 → 2 → 3 keeps readers alive and stops creation first. Lane 1's route and
   lane 3's consumer are independent of migrations and can be reverted in either order; neither
   destroys stored state.

## F. Phase B run-sheet

Written to `/tmp/si_plan/v11/LANE9_PHASE_B_RUNSHEET.md`. Seven ordered checks, each with the exact
command or script, the expected answer, and the SI/SP rows it closes. Not run.

## Deviations / limits

- Read-only on both repositories; no branch, commit, push, comment, label or migration. To run
  `gh` at all I had to satisfy the session-root quarantine guard, so I minted its prescribed SSD
  worktree (`/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/t3-7e7aa529-0e25b303e00e0ee6`)
  and entered it; nothing was edited there.
- One staging copy of the lead's status record at #10945's head was written to
  `/tmp/si_plan/v11/lead_status_at_10945_head.md` so it could be read by line range. It is not a
  deliverable.
- Lane 1's round-2 review has **not** landed (`/tmp/si_plan/reviews/lane1_population_review_r2.md`
  absent; `reviews/r2probes/` exists, so it is in progress). Lane 1's F1/S1/S2/S3 fixes are
  therefore **author-claimed, review pending**; the artifacts they name do exist and their test
  functions are present at `9c5db069`.
- The `/tmp/si_plan/reviews/pr_tree.tar` is a 14.8 GB sparse-file artifact of the earlier review; it
  was not read.
