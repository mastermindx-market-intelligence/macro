# EW-P5 acceptance receipts (seat 00dea969, started 2026-11-01)

Schema: ACCEPTANCE_AND_RELEASE.md §7 (identity, provenance, real checks, independent review, effect claim, held unknowns, rollback).

Rule: a row says only what its primary artifact shows. A pack is PASS only when every row in it is COVERED_ISOLATED under the independent mapping and every mapped test passed in a named run. Run `ew-p5-packs-20261101T071404Z-518ae7cd` at `d3fb043b0f2f` is the first census; no pack is PASS.

## Merged waves

Every row below reached the MERGED rung. None is PRODUCTION_PROOF or ACCEPTANCE.

| Wave | PR | Reviewed head | Independent review | Merged squash (UTC) | Effect claim | Held unknowns |
|---|---|---|---|---|---|---|
| EW-P0 records and takeover | #10249 | 5db46730 (after the R2 repair) | GD-EW-P0-R2, Fabric, non-author | 1d937d7e2b36 at 2026-10-31T16:09:14Z | Adoption record and handoff on main | None material |
| Records r2 | #10328 | b5b402ff | GD-EW-REC-R3 PASS-WITH-GAPS; the SHA typo was fixed before merge | a46192f7f4dd at 2026-10-31T16:54:21Z | Workstream wave states | None material |
| EW-P2 rotation continuity | #10325 | 697b90ab; review gd-ew-p2-r1 APPROVE on f2532edb, later delta is a main merge plus rig-emitted P0B receipts | Fabric r1 APPROVE | b38935afc1a5 at 2026-10-31T18:29:16Z | Recorder lands default-off; #10104 left open with a pointer | Activation (T2+) has no gate yet; O01-O08 not run |
| CI budget (not a wave) | #10341 | none | Seat-direct CI repair | dbaf1e07bccc at 2026-10-31T20:08:33Z | International job budget 8 to 15 minutes | None |
| EW-P3 forecast prereg (product B) | #10340 | c5f00584 r3 ACCEPT_WITH_FINDINGS, plus the seat sys.path pin 3c986e24 | Fabric r1-r3 | 11e6c98eb8c3 at 2026-10-31T20:37:56Z | Contract v1 blob 5270e309 frozen; prereg registered | Reader NOT_EXECUTABLE until L0 2027-12-31; R01-R08 not run |
| Records r3 (prereg dating) | #10346 | 9e7e9ce490fd | GD-EW-REC3-R1 APPROVE (R1-R9 PASS, ubuntu0, glm-5.3) | f9b070d84100 at 2026-10-31T21:14:36Z | Prereg dated: merge 2026-10-31, start 2026-11-02; two declared_budget rows appended | None |
| EW-P4 descriptive surface (product A) | #10350 | a49a16d52ac2 | gd-ew-p4-r1 REQUEST_CHANGES (F1-F5 repaired), r2 and r3 APPROVE_WITH_NOTES; r3 is on the exact head | 886ab694c947 at 2026-11-01T04:36:16Z | Radar inset and Sector Central observation language, EN/ZH, dark/light, 1280/390/320; 46 shots, receipt source_revision 5bb16bdb | No producer writes latest_observation, so production renders the unavailable state; review notes F-1 to F-3; vision review lane refused |
| EW-P4-FU validator parity | #10364 | 19accf478bb9 | Native Opus read-only reviewer: round 1 found parity counterexamples (pair_id whitespace and length, withdrawal source_as_of, stamps); round 2 PASS with notes on the exact head, no blocking findings | d3fb043b0f2f at 2026-11-01T07:11:16Z | The UI (Jinja and JS) rejects every observation the library validator rejects; F-1 to F-3 closed; 46 shots re-rendered and the receipt re-bound at 30998ca1 | The UI is stricter than the library on stamp forms the producer never emits; still no producer of latest_observation |
| EW-P4-ACT gated producer, point-in-time lift, O06 receipt | #10394 | 8de2ac3e8eed (PASS_WITH_NOTES); later delta is the CI split (0bd14feb), the curated-exclusive declaration (fb2b01da), the manifest comment-line move (eff1a462) and two main merges | Native Opus read-only reviewer | 983c6b0798e2 at 2026-11-02T12:59:13Z | Producer publishes latest_observation only under the recording flag, which stays off; receipts on every view; consumers refuse unreceipted views | Flag off: no real observation rendered; vision lane still refused |
| EW-P5 FU2 glance design-review repairs and CI split | #10401 | 675290c1 APPROVE-WITH-FIXES, delta re-review APPROVE on 6dae735a4ae1; 145d844d took that re-review's minor and nits (build_rotation_events fsync placement, band css content fallback) without a further round; later deltas are evidence recaptures, CI repairs, comment rewording and main merges | Native Opus read-only reviewer | 20a05db07376 at 2026-11-02T14:30:59Z | Governed glance stylesheet, copy and band reduction, F1-F4 clock gates, O01/C05 tests, ew-p4-descriptive-ui job | FU3 carve-outs open; U pack still fixture-only |

Real checks for EW-P4 at the exact head: local 539 passed and 2 skipped, node 19/19, contract-delta 0/0, hosted ci-gate, ci-plan and fence-pack SUCCESS. The seat's contact-sheet check passed; it is the seat's own check, not an independent review.

Real checks for EW-P4-FU at the exact head: ci-plan, fence-pack, all twelve ci-pack shards, self-mod-fence and ci-gate succeeded on head 19accf478bb9 (21 success, 4 skipped); the one red context is the advisory ci-authority/codex/merge-queue-pilot, which does not gate the merge.

## Pack census (run ew-p5-packs-20261101T071404Z-518ae7cd)

This is the first EW-P5 execution. It runs every test the independent mapping cites, plus the seat's candidates below, at one exact head. The mapping itself was made at an earlier head; see the mapping-head note. It is a census of what the tests prove, not an acceptance grant.

| Field | Value |
|---|---|
| Run ID | `ew-p5-packs-20261101T071404Z-518ae7cd` |
| Head (origin/main) | `d3fb043b0f2f521f3d37971f19622019b5b041f1` |
| Started / finished (UTC) | 2026-11-01T07:14:04Z / 2026-11-01T07:18:40Z |
| Runner | Grey Deer early-warning CEO seat, local M2 Studio, pytest + node --test |
| pytest | 1069 passed, 0 failed, 0 error, 17 skipped; exit 0 |
| node --test | 20 passed, 0 failed; exit 0 |

Skipped cases and their recorded reason:

- 15 cases: "explicit paired Terminal source required; no ambient private host".
- 2 cases: "settled market-state artifact not present in this checkout".

Mapping source: an independent native Opus read-only reviewer mapped all 63 catalogue rows to tests. Its dispositions are copied unchanged. The seat did not upgrade any row.

Mapping-head note (added after the records r5 review): the mapping was made at `2796abf7`, the head of the EW-P4-FU pull request branch, whose main base is `c3f5994b`. `2796abf7` is not an ancestor of the census head `d3fb043b`. #10255 merged between them as `c2772cc44ef5` at 2026-11-01T06:29:41Z and is on the census head. So every reason below that says #10255 is not on this tree is false at the census head. Rows S01, S03, S05, S06 and Q01 to Q05 are stale: their dispositions were not rechecked at the census head. #10255 added `tests/test_qledger_carve.py` (17 test functions; three are parametrized, so 21 collected cases). It was neither mapped nor run here and joins the next named run, which re-maps these rows.

A pack is PASS only when every row in it is COVERED_ISOLATED and every mapped test passed in this run. No pack meets that bar.

| Pack | Rows | Isolated | Partial | Not covered | Not executable | Held external | Mapped cases run | Result |
|---|---|---|---|---|---|---|---|---|
| S Publication and source clocks | 12 | 0 | 2 | 5 | 0 | 5 | 27 passed | NOT PASS (12 of 12 rows lack isolated coverage) |
| Q QLedger custody | 8 | 0 | 0 | 0 | 0 | 8 | none | NOT PASS (8 of 8 rows lack isolated coverage) |
| O Recorder | 8 | 3 | 3 | 1 | 1 | 0 | 13 passed | NOT PASS (5 of 8 rows lack isolated coverage) |
| C Consent and outbox | 16 | 1 | 4 | 2 | 7 | 2 | 8 passed | NOT PASS (15 of 16 rows lack isolated coverage) |
| U Descriptive UI | 11 | 0 | 8 | 1 | 1 | 1 | 36 passed | NOT PASS (11 of 11 rows lack isolated coverage) |
| R Science negatives | 8 | 0 | 3 | 1 | 4 | 0 | 4 passed | NOT PASS (8 of 8 rows lack isolated coverage) |
| All | 63 | 4 | 20 | 10 | 13 | 16 | 88 passed (sum of row cells; a test shared by rows counts once per row) | NOT PASS |

A passing mapped test does not make its row pass. For S02 and S12 the mapped test passes because it pins the behaviour the oracle forbids. The repair merged later as #10371 (`a7628775`, 2026-11-01T07:29:24Z) and is not on this head.

### Row census

Short names: ROS, ROB and ROI are the rotation observation state, builder and integration tests; UI is `tests/test_ew_p4_descriptive_ui.py`; CJS is `tests/ew_p4_glance_ui.test.cjs`; LRE is `tests/test_live_risk_envelope.py`; DRN, EFB and AP are the alert drain, effect-boundary and account-prefs tests; RDR is the EW forecast reader test.

| Row | Independent disposition | Mapped tests | Run result | Reviewer reason |
|---|---|---|---|---|
| S01 | HELD_EXTERNAL | None | No mapped test | Needs a natural eligible session and a paired public/durable commit identity, which depend on #10255 (another owner). Stale at the census head: see the mapping-head note. |
| S02 | NOT_COVERED | `LRE::TestPrecedence::test_l_equal_s_clears_the_transition_on_settle_catch_up` | 1 passed | This test asserts the opposite of the row: matching session dates alone make the settled side win. Nothing tests that a label alone cannot grant settlement. |
| S03 | HELD_EXTERNAL | None | No mapped test | Detecting the express/closing-bell split is the publisher path of #10255/#10221, which is not on this tree. Stale at the census head: see the mapping-head note. |
| S04 | NOT_COVERED | None | No mapped test | No test for a partial write to one envelope target was found. `tests/test_risk_envelope.py` was not searched exhaustively. |
| S05 | HELD_EXTERNAL | None | No mapped test | The final 40-hex pushed-commit check is the #10255 commit/publish path. Stale at the census head: see the mapping-head note. |
| S06 | HELD_EXTERNAL | None | No mapped test | The typed worktree/index/commit mismatch is the same #10255 path. Stale at the census head: see the mapping-head note. |
| S07 | NOT_COVERED | None | No mapped test | No test checks that a same-session envelope revision is monotonic and keeps the original first-known time. |
| S08 | PARTIAL | `ROS::test_future_source_and_older_observation_clock_never_roll_history_back`; `ROS::test_malformed_numeric_evidence_withdraws_without_coercion`; `ROS::test_half_day_settlement_and_holiday_follow_existing_calendar` | 23 passed | Future, malformed and holiday inputs are withheld at the observation layer. Missing: a wrong-market case, and an envelope-level "no calm replacement of the prior severity" check. |
| S09 | PARTIAL | `UI::test_journey_c_exact_stale_strings`; `UI::test_fragile_headline_does_not_create_an_observation` | 2 passed | Stale rotation is scoped correctly ("latest is Oct 20"). The envelope's PARTIAL state is never asserted. |
| S10 | HELD_EXTERNAL | None | No mapped test | Needs two natural nightly `engine: regime update` landings. |
| S11 | NOT_COVERED | None | No mapped test | `lineage_roots` appears only in fixtures. No test checks that clues sharing the Yahoo root count as dependent. |
| S12 | NOT_COVERED | `LRE::TestPrecedence::test_l_equal_s_clears_the_transition_on_settle_catch_up` | 1 passed | Precedence compares session dates only, and the test pins the suppression this oracle forbids. |
| Q01 | HELD_EXTERNAL | None | No mapped test | Complete-generation certification belongs to #10079 (draft) and #10255; neither is on this tree. Stale at the census head: see the mapping-head note. |
| Q02 | HELD_EXTERNAL | None | No mapped test | Refusing a forged COMPLETE scope belongs to the same owners. Stale at the census head: see the mapping-head note. |
| Q03 | HELD_EXTERNAL | None | No mapped test | The historic-reader label belongs to the same owners. Stale at the census head: see the mapping-head note. |
| Q04 | HELD_EXTERNAL | None | No mapped test | Append versus atomic replace with an old open file descriptor belongs to the same owners. Stale at the census head: see the mapping-head note. |
| Q05 | HELD_EXTERNAL | None | No mapped test | Oversized-ledger custody is in the #10255 carve, which is not merged here. Stale at the census head: see the mapping-head note. |
| Q06 | HELD_EXTERNAL | None | No mapped test | This is an agent-conduct rule (no replay of a refused native operation), which no test can exercise. |
| Q07 | HELD_EXTERNAL | None | No mapped test | The native validator ceilings belong to the #10079 owner. |
| Q08 | HELD_EXTERNAL | None | No mapped test | #10079 is a draft and no complete original cut exists. |
| O01 | PARTIAL | `ROS::test_receipts_use_existing_ledger_state_and_keep_legacy_data`; `ROS::test_append_then_checkpoint_crash_reuses_original_receipt_clock`; `ROS::test_weekend_is_contiguous_using_existing_calendar` | 3 passed | The state id equals the first record's id and the first clock is kept. The receipt has no definition/version or rights field, and no test shows two fresh runs produce the same id. |
| O02 | COVERED_ISOLATED | `ROS::test_receipts_use_existing_ledger_state_and_keep_legacy_data`; `ROS::test_same_measurement_is_idempotent_and_does_not_mutate_input` | 2 passed | A replay returns `records==[]` and the ledger stays at 1 row. This holds at the receipt layer only. |
| O03 | COVERED_ISOLATED | `ROS::test_append_then_checkpoint_crash_reuses_original_receipt_clock`; `ROS::test_recovery_with_changed_input_keeps_original_ledger_parent` | 2 passed | After an injected `os.replace` failure: 1 ledger line, original `observed_at`, no temp files left. |
| O04 | COVERED_ISOLATED | `ROS::test_revision_of_notifiable_observation_is_linked_correction`; `ROS::test_recovery_with_changed_input_keeps_original_ledger_parent`; `ROS::test_conflicting_or_truncated_canonical_receipt_never_gets_overwritten` | 3 passed | A correction links to its predecessor, and a tampered or truncated ledger raises and is never overwritten. |
| O05 | PARTIAL | `ROS::test_data_withdrawal_uses_null_values_not_old_positive_returns` | 1 passed | Withdrawal produces null values. There is no rights-unqualified path, and the predecessor link is not asserted. |
| O06 | NOT_COVERED | `ROB::test_actual_builder_calls_observer_only_after_json_publication` | 1 passed | This test pins publish-before-record. The consumer only checks the id's format and never refuses an id that lacks a source-owned published reference. |
| O07 | NOT_EXECUTABLE | None | No mapped test | The cross-system same-bundle join is EW-P4.T2, which is not built. |
| O08 | PARTIAL | `RDR::test_t6_gate4_no_receipted_issue` | 1 passed | The reader returns NOT_EXECUTABLE with `no_receipted_issue`. No consumer test covers availability `UNKNOWN`. |
| C01 | PARTIAL | `AP::test_the_new_category_is_a_legal_member_and_is_not_opted_in_by_default`; `DRN::test_optin_absent_yields_suppressed_and_unknown_metadata_leaves_pending` | 2 passed | Default-off and absent-opt-in suppression are covered. "No historical backfill" cannot be tested because there is no bridge from observations to the outbox. |
| C02 | NOT_EXECUTABLE | None | No mapped test | The server-owned effective revision and activation clock is EW-P2.T2. |
| C03 | NOT_EXECUTABLE | None | No mapped test | A serialized permission order is EW-P2.T2. |
| C04 | NOT_EXECUTABLE | None | No mapped test | Family-level revocation is EW-P2.T2. |
| C05 | NOT_COVERED | `AP::test_stale_cached_snapshot_never_reaches_the_put` | 1 passed | This only shows a fresh GET wins over the cache. It does not cover an opt-out landing between the GET and the PUT. |
| C06 | NOT_EXECUTABLE | None | No mapped test | Needs an activation clock (EW-P2.T2). |
| C07 | NOT_EXECUTABLE | None | No mapped test | Needs an activation revision and superseding of old-generation rows (EW-P2.T2). |
| C08 | PARTIAL | `DRN::test_lapsed_entitlement_yields_suppressed_row_never_deleted_never_sent` | 1 passed | A lapsed entitlement is suppressed and the row kept. Source-rights failure at final admission is missing, and the quiet-hours assertions were not read. |
| C09 | NOT_EXECUTABLE | None | No mapped test | The per-user dimension of one `fire_event_id` for observations needs the EW-P2.T2 bridge. |
| C10 | PARTIAL | `ROS::test_revision_of_notifiable_observation_is_linked_correction`; `DRN::test_same_fire_event_id_drained_twice_sends_once_and_reports_duplicate` | 2 passed | Each side is covered alone. The logical key mapping from observation to outbox is not built. |
| C11 | PARTIAL | `EFB::test_p2_death_during_smtp_is_effect_unknown_and_is_never_auto_resent` | 1 passed | The in-flight crash case holds. The `test_p1_*` assertions were not read, and the "outbox transaction succeeds" half needs the bridge. |
| C12 | COVERED_ISOLATED | `EFB::test_p2_death_during_smtp_is_effect_unknown_and_is_never_auto_resent` | 1 passed | The mailbox does not grow over 5 more ticks and the status never becomes `sent`. |
| C13 | HELD_EXTERNAL | None | No mapped test | Needs a real provider and a witnessed inbox. |
| C14 | NOT_EXECUTABLE | None | No mapped test | There is no risk-family store RLS or server-only mutation (EW-P2.T2 DDL). A live database proof would also be external. |
| C15 | NOT_COVERED | None | No mapped test | No test separates acknowledge from unsubscribe. `ROI::test_real_category_click_preserves_topics_owned_by_other_surfaces` tests a different invariant. |
| C16 | HELD_EXTERNAL | None | No mapped test | Needs a natural event, an opted-in real user, the provider, the inbox and the signed-in link. |
| U01 | PARTIAL | `UI::test_quiet_headline_does_not_suppress_qualified_observation` | 1 passed | `RISK_ON`/NONE still shows `observed`. No test checks that the broad gate is unchanged, and there is no Caution case. |
| U02 | PARTIAL | `UI::test_side_by_side_ratio_legs_table`; `ROI::test_less_negative_is_only_relative_shelter_not_an_absolute_gain`; `CJS` "state parity against expected.json, EN and ZH" | 5 passed | The "fell less" copy is checked in EN and ZH. No negative scan for gain, flow or safety words exists. |
| U03 | PARTIAL | `UI::test_two_session_vs_twenty_session_horizons`; `CJS` "conflicting horizons carry the conflict sentence as text" | 2 passed | The conflict sentence appears, but the sign of each horizon (+2.06 vs −2.97) is never asserted. |
| U04 | PARTIAL | `UI::test_journey_c_exact_stale_strings`; `UI::test_policy_footer_keeps_w9_fact_and_adds_not_an_all_clear` | 2 passed | "This is not an all-clear." is present. There is no "no confirmed repair" negative and no Mixed/Partial assertion. |
| U05 | NOT_COVERED | None | No mapped test | No test covers a known severe warning followed by a malformed calm snapshot. `LRE::test_empty_live_block_is_not_present_never_fresh_calm` was seen by name only. |
| U06 | PARTIAL | `UI::test_correction_history_original_and_corrected`; `UI::test_withdrawal_keeps_original_and_hides_current_values` | 2 passed | Correction and withdrawal are covered. The reconstructed-past-source case is missing. |
| U07 | PARTIAL | `CJS` "fetch/parse failure renders the scoped unavailable state" | 1 passed | This greps the source text rather than running it. Anonymous/401/403 states and protected-payload leakage are not tested. |
| U08 | NOT_EXECUTABLE | None | No mapped test | The Macro/Terminal/Mastermind same-event consumer is EW-P4.T2. |
| U09 | PARTIAL | `UI::test_receipt_shots_depict_the_source_under_test`; `UI::test_bilingual_spans_paired_and_no_title_attributes` | 16 passed | The 46 screenshots are only hash-bound to the source. There is no separate dark or light design judgement, and the input is fixtures only. |
| U10 | PARTIAL | `UI::test_css_no_edge_stripe_no_color_literal_focus_visible`; `UI::test_state_matrix_words_and_attribute` | 7 passed | Focus outlines and text state words are covered. Reduced motion, screen-reader status and keyboard traversal are missing. |
| U11 | HELD_EXTERNAL | None | No mapped test | Needs a comparison study with real users. |
| R01 | NOT_COVERED | None | No mapped test | No test was found that preserves the failed 39-trigger out-of-sample gate. The search was not exhaustive. |
| R02 | NOT_EXECUTABLE | `RDR::test_t7_gate5_scorer_not_implemented` | 1 passed | `SCORER_IMPLEMENTED` is False, so EW-P3.T2 is required. |
| R03 | NOT_EXECUTABLE | None | No mapped test | There is no scorer (EW-P3.T2). |
| R04 | PARTIAL | `ROS::test_half_day_settlement_and_holiday_follow_existing_calendar` | 1 passed | Nothing is issued before settlement. Issuing only after the k-th eligible session needs EW-P3.T2. |
| R05 | PARTIAL | `RDR::test_t6_gate4_no_receipted_issue` | 1 passed | The reader refuses when there is no receipted issue. Silently reconstructed point-in-time membership is not tested explicitly. |
| R06 | NOT_EXECUTABLE | None | No mapped test | Cluster/embargo scoring is EW-P3.T2. |
| R07 | PARTIAL | `ROS::test_positive_divergence_is_observed_not_sized_or_predicted` | 1 passed | The output is `notification_only` with no confidence or allocation field. With no model, the "promising model, no policy grant" case cannot run. |
| R08 | NOT_EXECUTABLE | None | No mapped test | Disposition logic is EW-P3.T3. The reader only refuses. |

### Seat-found candidates (not verified by the mapping reviewer)

The mapping reviewer did not read three envelope test files in full. The seat found the tests below in them. They change no disposition above until an independent reviewer confirms them.

| Row | Candidate tests | Run result | Seat note |
|---|---|---|---|
| S08 | `tests/test_risk_envelope.py::TestNullLaw::test_stale_source_never_casts_a_calm_vote_over_a_fresh_damaged_one`; `tests/test_risk_envelope.py::TestGD1PermanentRegressionFixture::test_calm_radar_is_carried_but_does_not_cancel_the_broken_cohort` | 2 passed | A stale source never casts a calm vote over a fresh damaged one. This is close to the oracle's "no calm replacement" half. |
| S11 | `tests/test_rotation_risk_envelope.py::test_disjoint_recorded_roots_do_not_claim_statistical_independence`; `tests/test_rotation_risk_envelope.py::test_incomplete_lineage_total_is_null`; `tests/test_rotation_risk_envelope.py::test_declared_ancestry_is_shared_even_when_roots_differ` | 5 passed | These cover shared lineage in general. None names the Yahoo root. |
| U05 | `tests/test_risk_envelope_radar_integration.py::test_malformed_live_transition_is_not_a_healthy_read`; `tests/test_risk_envelope_radar_integration.py::test_missing_inputs_never_render_calm_or_risk_on` | 6 passed | These cover a malformed transition and missing inputs. Neither starts from a known severe warning. |

### Defects and gaps the census found

Major:

- **S02 and S12, live-overlay precedence.** `scripts/build_live_risk_envelope.py` lets the settled side win whenever the session dates match, and `LRE::TestPrecedence::test_l_equal_s_clears_the_transition_on_settle_catch_up` pins that. The oracle says a label or matching date alone must not suppress the live overlay. This is a candidate defect against the catalogue at this head. The EW-P5-FU repair merged later as #10371 (`a7628775`, 07:29:24Z) and is not on this head: a same-session settled copy must carry a settled or corrected revision, a produced_at at or after 16:00 New York time on the session, and a matching public copy before it suppresses the live overlay.
- **O06, published identity.** `ROB::test_actual_builder_calls_observer_only_after_json_publication` pins publish-before-record. The consumer checks only the id's format, so nothing refuses an id that lacks a source-owned published reference.
- **U pack is fixture-only.** No producer writes `latest_observation`, so every U test runs against `tests/fixtures/ew_p4_observation/`. Production shows the unavailable state until an activation gate exists.

Minor:

- **O01.** The observation receipt carries no definition, version or rights field.
- **C05.** No test covers an opt-out landing between the preference GET and the PUT.
- **U02.** No negative scan bans gain, flow or shelter wording, and an integration test asserts "relative shelter".
- **U09.** The 46 screenshots are hash-bound to the source, but there is no separate dark or light design judgement. The vision review lane was refused.
- **Sparse trees.** `ROI::test_real_category_click_preserves_topics_owned_by_other_surfaces` reads `site/account.js` with no skip guard, so it errors on a sparse checkout.

Mapping gaps: the reviewer did not read the `test_qledger_*` files, three envelope test files in full, or the quiet-hours, `test_p1_*` and expiry tests it saw by name. It mapped at `2796abf7`, before #10255 merged, so `tests/test_qledger_carve.py` is unmapped.

Records r5 review of the seat-found candidates (independent, read-only): S08 stays PARTIAL; no wrong-market case and no test against calm replacement of an earlier qualified severity. S11 rates PARTIAL on `test_duplicate_alias_and_source_permutation_never_add_corroboration`, which shows two price sources sharing a root collapse to one component; no test uses a real price-derived Yahoo root. U05 rates PARTIAL; no test starts from a known severe warning and then feeds a later calm snapshot. These ratings are recorded here and adopted by the next named run's mapping; the table above keeps this run's mapping.

## Open waves

- **EW-P1.** T1 diagnosis is done. T2 is superseded by #10255 (merged `c2772cc44ef5` at 2026-11-01T06:29:41Z). Acceptance is two natural engine sessions after that commit (scheduled daily.yml runs on main, never a seat dispatch) in which `engine: regime update <date>` lands on main and `data/risk_envelope/latest.json` advances. The first landed on 2026-11-02 (`b0a37dfbaff4` 10:20:35Z and `9d7925b30a01` 10:40:00Z; latest.json advanced from its 2026-10-21 landing). A session lands one to five engine commits (per-day census since 2026-10-01), so commit count does not count sessions and that pair is one session (the delayed 22:30Z `daily.yml` scheduled run 41378879186 (created 02:39:14Z; engine job 06:46:36Z-10:42:38Z; the run ended cancelled after the engine job, but both commits landed and latest.json advanced, which is what acceptance counts)); the seat's earlier watcher counted commits and has been replaced by an hourly git-only read that counts distinct landing dates. Rung today: one of two sessions observed; PRODUCTION_PROOF is not recorded.
- **EW-P4 follow-ups.** F-1 to F-3 are closed by #10364. The gated `latest_observation` producer landed as EW-P4-ACT #10394 (`983c6b0798e2`); the recording flag stays off, so no real observation is rendered. The vision review lane stays refused.
- **EW-P5 follow-ups.** The census defects above are tracked as EW-P5-FU in the workstream. FU2 #10401 (`20a05db07376`) landed the glance design-review repairs, the O01 and C05 tests, the sparse-tree guard and the `ew-p4-descriptive-ui` CI job. The FU3 carve-outs (runtime-injected early-context stylesheet, ZH state words, footer punctuation, the fixture page's combined measure, O06 publish-before-record, U09 dark/light judgement) each need their own PR and review.
- **EW-P5 packs.** First census run `ew-p5-packs-20261101T071404Z-518ae7cd`; every pack is NOT PASS. The next run follows the EW-P5-FU repairs, adds `tests/test_qledger_carve.py`, and re-maps the stale rows at its own head. Remaining scope by pack:
  - S01-S12 publication and source clocks. These depend on the EW-P1 landings.
  - Q01-Q08 QLedger custody, in the #10079 and #10255 context.
  - O01-O08 recorder behaviour. EW-P2 recording is default-off.
  - C01-C16 consent and outbox. No live send is authorized.
  - U01-U11 EW-P4 UI, EN/ZH by dark/light by desktop/mobile, plus accessibility. A real observation needs an activated producer first.
  - R01-R08 science negatives and prereg reader refusals.

## Rollback (owned mechanisms, per §7.7)

- EW-P2 recorder: the default-off flag; no history rewrite.
- EW-P3: the prereg is immutable and the reader refuses before its window.
- EW-P4: UI only; revert by PR.
- No consent or alert path is live, so no send rollback is needed.

## Release posture (per §8)

This file grants no informational Tier A release, no predictive or trading authority, and no live send. The parent mission stays incomplete until the EW-P1 landings exist, the EW-P5-FU repairs land, and a later named run shows every executable row COVERED_ISOLATED and green. Rows marked HELD_EXTERNAL or NOT_EXECUTABLE stay open until their owners' work exists.
