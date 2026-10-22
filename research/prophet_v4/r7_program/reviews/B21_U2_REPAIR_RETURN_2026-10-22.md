STATUS: PARTIAL — every F28 ruling R1–R10 is implemented and tested; M1–M10 are all CAUGHT; P1 and P3–P7 pass; the merged-tree acceptance passes on the merge with origin/main 1f536032. One item is not satisfied: `git merge-tree --write-tree origin/main refs/pro/b21u2-fix` exits 1 (CONFLICT in tests/test_ci_pack.py only). That conflict is structurally forced: a sole-parent-6e6798aa commit cannot both carry the 5_844/5_817 ceilings and merge cleanly, because main already rewrote the same two lines (see §8). The resolved merge commit 93158bfc (parents: fix + origin/main 1f536032) merges with rc=0 against current origin/main b8e7bbb7. It is dangling and is the recommended push head.

# B21 U2 repair return — 2026-10-22

- Fix commit (refs/pro/b21u2-fix): **0024c326da5228dac6ecff3ea5bbf45c63b03c05**. Sole parent: 6e6798aa0c72baf1c427f3593fc14eafc41aebb9. Tree: f93693757c77f60cf615363d46211c253ef3e83e.
- Resolved merge tree against origin/main 1f536032d446e2b51bda47f0575e371f0c4a0aae: **9ded0d9e33a529012ea9579501ce5f1875a983c1** (the acceptance tree).
- Optional merge commit (not referenced by any ref, so it is dangling; seat must anchor it or rebuild it): **93158bfc6d07a03817885006936eefa51245a90f**. Parents: 0024c326 and 1f536032. Tree: 9ded0d9e.
- origin/main then moved to b8e7bbb70c9965f56e326c2c830014816969986a, which adds only two agentos/ markdown files. `git merge-tree --write-tree origin/main 93158bfc` gives 783e4b95 with rc=0; 783e4b95 differs from the acceptance tree 9ded0d9e only in those two agentos/ files.
- Superseded (do not use): fix 4425ba19 / merge 4f2a185d / tree 44bd61f3, built against main a46365b2 (ceilings 5_840/5_813). refs/pro/b21u2-fix was moved 4425ba19 -> 0024c326 with an old-value-checked update-ref.
- The engine, the U2 suite and the contract blobs in 0024c326 are byte-identical to 4425ba19 (05df5a57 / 8ec3799d / f9ae22cd). Only tests/test_ci_pack.py changed.
- Nothing was pushed, no PR was edited, nothing was posted. No git command ran on the seat worktree beyond those the commission allows. Git dirs for test HEADs were scratch-only.

## 1. Fabric outcome (verbatim)
- host_pick `--mode build` was invalid.
- `--mode glm` admitted ubuntu2 (rc 0).
- Direct execution was chosen; lane pro-source-b21u2-fix-20261022-r1 is unused.

## 2. Per-ruling changes (engine = engine/prophet_journey_notifications.py, tests = tests/test_prophet_journey_notifications.py; line numbers at 0024c326, identical to 4425ba19)

**R1 — from_state is the B1 replay state before the causing event.**
- Engine:
  - `_replay_order` (L667) replays the ledger in canonical (known_at, source_system, source_event_id) order with B1's deferral.
  - `derive_events` (L794; comment at L877) tracks the replayed lifecycle per episode.
  - retracted and superseded set `from_state = before` (L958, L979).
  - The projection_prev lookup is gone.
- Tests:
  - `test_r1_from_state_is_the_b1_replay_state_and_stable_across_runs` (L1219)
  - `test_r1_replay_uses_canonical_known_at_order` (L1260)
  - `test_derive_events_is_input_order_invariant` (L1280)

**R2 — not_after anchors on the transition's session; stale or unresolvable never mints.**
- Engine:
  - `_session_end` (L1068) reads the transition's market_session from `_session_of` (L759).
  - Unresolvable gives `not_after_unresolvable` (L1219).
  - The recency gate is `now_key is None or not_after <= now_key`, giving `stale_transition_at_mint` (L1164, L1221–L1224).
  - SUPPRESSION_KEYS gains both keys (L181–L182).
- Tests:
  - `test_r2_not_after_anchors_on_the_transition_session_and_stale_never_mints` (L1305)
  - `test_not_after_from_session_calendar_and_fail_closed` (L841, rewritten)

**R3 — the machine-id guard matches the id form, so HPE mints.**
- Engine: `_MACHINE_ID_RE = \b(?:pee?:[0-9a-f]|peg:[0-9a-f]|pe:SEC:)` (L213), used by `_glance_is_clean` (L528–L541).
- Tests:
  - `test_r3_machine_id_guard_matches_the_id_form` (L1369)
  - `test_banned_terms_suppress_at_persist` (L1074)

**R4 — a non-terminal STATE_TRANSITIONED mints nothing; emergence needs the current lifecycle ACTIVE.**
- Engine:
  - `if target not in _TERMINAL_SOURCE_STATES:` gives `ineligible_event` (L902–L904).
  - Emergence with a non-ACTIVE current lifecycle gives `ineligible_event` (L1033–L1036).
- Test: `test_r4_non_terminal_state_transitioned_mints_nothing` (L1393)

**R5 — contract §4 branch table.**
- Engine:
  - An unsent original (pending, or minted in this run) gets a PATCH to suppressed with last_error `superseded_by_prophet_correction` (PRODUCER_SUPPRESSED_REASON, L192; patch at L1281). The correction is minted in the same run with the non-presuming copy (`presumes_receipt=False`, L470–L515).
  - An original minted in this run is born suppressed (`original_superseded_in_run`, L1246).
  - A readback whose last_error is the producer reason gives `original_producer_suppressed`, and nothing is minted (L1256–L1258).
  - Effect-unknown gives `original_quarantined` (L1266–L1268).
- Tests:
  - `test_r5_producer_suppressed_original_is_never_reread_as_opt_out` (L1441)
  - `test_correction_rows_follow_the_original_status_table` (L962, extended)

**R6 — the original comes from the outbox readback.**
- Engine:
  - Notices per (episode, user) are parsed from existing fire ids and ranked by B1 replay rank (L1136–L1160).
  - The original is the latest prior notice of any kind, `max(prior)` (L1230–L1238).
  - None gives `no_original` (L1237).
  - The payload's `corrects_fire_event_id` is that original (L1301).
- Test: `test_r6_original_resolved_from_readback_any_kind_including_emergence` (L1519)

**R7 — relation-level retraction copy.**
- Engine:
  - `_SHOWN_RELATION_TYPES = {OPENED, OBSERVED}` (L269–L273).
  - A retraction of an OBSERVED relation uses relation_level copy: "…an earlier observation was withdrawn; the name remains tracked." (L476–L506).
- Test: `test_r7_relation_level_retraction_copy` (L1564)

**R8 — an absent or UNESTIMABLE prior emergence counts as not triggered.**
- Engine: `_PRIOR_EMERGENCE_UNKNOWN = _UNKNOWN_STATES - {"UNESTIMABLE"}` (L262–L265, applied at L1007–L1014).
- Contract: one sentence citing "seat ruling F28 R8", added at B21_ALERT_STATE_MACHINE_CONTRACT_2026-10-21.md L116–L119.
- Test: `test_r8_absent_or_unestimable_prior_emergence_counts_as_not_triggered` (L1580)

**R9 — prev READ_UNAVAILABLE gives `prev_projection_unavailable` and nothing is derived.**
- Engine: L804–L806, key at L175.
- Test: `test_r9_prev_projection_unavailable_derives_nothing` (L1607)

**R10 — `_episode_identity` applies CORRECTED ticker/company patches in replay order.**
- Engine: L724–L757 (CORRECTED branch at L744).
- Test: `test_r10_corrected_ticker_routes_to_the_new_ticker` (L1622)

**Invariants kept:**
- `REQUIRES_TIER = "essential"` (L137).
- The 17-key payload is unchanged (`test_payload_key_set_and_glance_text_are_clean`).
- The fire_event_id literal `prophet|kind|episode|from->to|b1_event_id|user_id` is unchanged (L381–L395).
- Stdlib only (re, uuid, dataclasses, datetime, typing; enforced by `test_module_is_pure_and_imports_no_repo_modules`).
- The module stays a pure producer: no sending, persistence or scheduling.
- No trade, sizing or recommendation language.

**CI ceiling (amendment step 4):**
- tests/test_ci_pack.py = main's file at 1f536032 (blob f0ea0eb3), with exactly two edits:
  - the ceiling lines are now `("templates/index.html", 136, 5_844)` and `("scripts/build_free_content.py", 135, 5_817)`; and
  - the U2 prophet-lab paragraph is inserted next to main's fixed-redirect, HK-lookup, Research-API and Shared-Shell paragraphs.
- All of main's docstring paragraphs are kept. The plan_book line `("engine/prophet/plan_book.py", 130, 5_600)` is untouched.
- Resulting blob: fe3dbb0d15b6d1b48c31833d8a3e8631777507f2.

## 3. Measured ceilings (packing_probe_measurements(MANIFEST, PACKING_PROBES, max_packs=…) on the exported trees, scratch git index populated)
```
before (main 1f536032 tree d997332b, exported in place by read-tree -m -u and measured):
  templates/index.html          135 jobs / 5841 weight / 10 packs
  scripts/build_free_content.py 135 jobs / 5814 weight / 10 packs
  engine/prophet/plan_book.py   128 jobs / 5590 weight / 10 packs
after (merge tree 9ded0d9e):
  templates/index.html          135 jobs / 5844 weight / 10 packs   ceiling 136 / 5_844
  scripts/build_free_content.py 135 jobs / 5817 weight / 10 packs   ceiling 135 / 5_817
  engine/prophet/plan_book.py   128 jobs / 5593 weight / 10 packs   ceiling 130 / 5_600 (unchanged)
breaches []
```
- U2 adds exactly +3 per probe, and no job joins or leaves any probe.
- Main's 5_841/5_814 + 3 = 5_844/5_817 is confirmed by measurement on both trees, not by arithmetic. (The coordinator's 5_840/5_813 was correct for main 80854549 through a46365b2; main's #9997 (7bb2f72e, HK lookup + fixed redirect stubs) then raised main's own ceilings to 5_841/5_814. #10002 (a6cb1a7b) also touched test_ci_pack.py/legacy-jobs.yml but not the ceilings.)
- Main changed `packing_probe_measurements` to take the manifest path; the measuring script was adapted (scratchpad/probe_measure2.py).

## 4. Pytest
**Acceptance environment for the merged tree (`scratchpad/u2fix_merged`):**
- The export of merge tree 9ded0d9e is bound to a scratch git store, `scratchpad/u2fix_fastgit`, through a `.git` gitfile. (The a46365b2-era export was moved to 9ded0d9e in place with `read-tree -m -u` under a scratch alternates gitdir, then re-bound.)
  - The store holds commit 93158bfc, every tree, and every blob except data/, mockups/, site/, verify_shots/, ux-evidence/ and blobs over 5 MB (two packs: the original one plus the 90 objects new in 9ded0d9e; 0 of the 26,539 listed objects missing).
  - It is marked shallow, HEAD is 93158bfc, and its index is the stat-refreshed index of 9ded0d9e (`git write-tree` = 9ded0d9e).
- `git update-index --refresh` reported 0 mismatches over all 131,959 paths, so the export is byte-identical to 9ded0d9e. `git status --porcelain` was empty before and after the runs.
- No GIT_DIR or GIT_WORK_TREE environment variables were set, so tests that build their own temp repos resolve them exactly as in CI.

**Merged tree 9ded0d9e: test_ci_pack plus the U2 suite (the acceptance run):**
```
$ cd u2fix_merged && python3 -m pytest tests/test_ci_pack.py tests/test_prophet_journey_notifications.py -q --durations=8
........................................................................ [ 92%]
..................                                                       [100%]
============================= slowest 8 durations ==============================
206.96s call     tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
159.62s setup    tests/test_ci_pack.py::test_selection_fails_safe_toward_running_everything
46.33s call     tests/test_ci_pack.py::test_curated_exclusivity_drops_only_the_opaque_fallback_tier
36.16s call     tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs
21.79s call     tests/test_ci_pack.py::test_plan_and_execution_select_the_exact_same_jobs
6.43s call     tests/test_ci_pack.py::test_selection_fails_safe_toward_running_everything
4.12s call     tests/test_ci_pack.py::test_a_main_role_plan_from_a_data_health_trigger_carries_every_data_job
3.77s call     tests/test_ci_pack.py::test_ancestor_init_census_does_not_grow
234 passed in 616.61s (0:10:16)
rc=0
```

**Merged tree 9ded0d9e: the probe subset:**
```
$ python3 -m pytest tests/test_ci_pack.py -k "probe or packing or weight" -q
........                                                                 [100%]
8 passed, 196 deselected in 22.28s
rc=0
```
- `git status --porcelain` in u2fix_merged after the runs: empty (rc=0); `git write-tree` still 9ded0d9e.

**Fix tree (`scratchpad/u2fix_tree`, the export of df761a4c, whose engine/U2-suite/contract blobs are identical to 0024c326's): the U2 suite:**
```
$ python3 -m pytest tests/test_prophet_journey_notifications.py -q
..............................                                           [100%]
30 passed in 2.74s
rc=0
```
- I did not run test_ci_pack on the fix tree alone, and it is not part of the acceptance (amendment: "that merged-tree run is the acceptance, not the fix tree alone").
- The fix side's tests/test_ci_pack.py is the resolved merge file, so it carries main's exclusive-curation entries. That makes it compatible with main's manifest, which is in the merged tree, and not with the older 6e6798aa manifest.

## 5. Mutations (private engine copy at the u2fix_tree export; restored after the run, sha1 dd79a8223ab3ae2c843188975ac4253ec096fb39 re-verified)

| id | mutation | U2 suite | verdict | tests that caught it |
|---|---|---|---|---|
| M1 | identity: drop `\|{user_id}` from fire_event_id | 5 failed, 25 passed in 1.27s | CAUGHT | test_fire_event_id_literal_and_round_trip, test_plan_enqueue_dedupes_per_user_and_never_leaks_across_users, test_correction_rows_follow_the_original_status_table, test_r5_producer_suppressed_original_is_never_reread_as_opt_out, test_r6_original_resolved_from_readback_any_kind_including_emergence |
| M2a | identity (review literal): from_state at both sites -> "ACTIVE" | 2 failed, 28 passed in 1.35s | CAUGHT | test_r1_from_state_is_the_b1_replay_state_and_stable_across_runs, test_r1_replay_uses_canonical_known_at_order |
| M2b | identity (bug re-introduced): from_state at both sites -> projection_prev lifecycle | 3 failed, 27 passed in 5.48s | CAUGHT | test_unestimable_or_unavailable_side_is_not_a_change, test_r1_from_state_is_the_b1_replay_state_and_stable_across_runs, test_r1_replay_uses_canonical_known_at_order |
| M3 | eligibility: `if target not in _TERMINAL_SOURCE_STATES:` -> `if not target:` | 1 failed, 29 passed in 1.02s | CAUGHT | test_r4_non_terminal_state_transitioned_mints_nothing |
| M4a | correction: drop the PATCH of an unsent original (insert-only) | 2 failed, 28 passed in 1.08s | CAUGHT | test_correction_rows_follow_the_original_status_table, test_r5_producer_suppressed_original_is_never_reread_as_opt_out |
| M4b | correction: remove `continue` after original_producer_suppressed (re-read as opt-out) | 2 failed, 28 passed in 1.07s | CAUGHT | test_correction_rows_follow_the_original_status_table, test_r5_producer_suppressed_original_is_never_reread_as_opt_out |
| M5 | correction: remove `continue` after original_quarantined | 1 failed, 29 passed in 1.08s | CAUGHT | test_correction_rows_follow_the_original_status_table |
| M6 | glance: _glance_is_clean -> return True | 2 failed, 28 passed in 1.06s | CAUGHT | test_banned_terms_suppress_at_persist, test_r3_machine_id_guard_matches_the_id_form |
| M7 | R2 recency gate disabled | 1 failed, 29 passed in 1.05s | CAUGHT | test_r2_not_after_anchors_on_the_transition_session_and_stale_never_mints |
| M8 | R3 machine-id regex reverted to a bare pee?:/peg: substring | 1 failed, 29 passed in 1.07s | CAUGHT | test_r3_machine_id_guard_matches_the_id_form |
| M9 | R9 prev READ_UNAVAILABLE gate removed | 1 failed, 29 passed in 1.01s | CAUGHT | test_r9_prev_projection_unavailable_derives_nothing |
| M10 | R10 CORRECTED identity patches ignored | 1 failed, 29 passed in 1.05s | CAUGHT | test_r10_corrected_ticker_routes_to_the_new_ticker |

- After restore: `30 passed in 0.99s`.
- M2 and M3, which survived on the 6e6798aa suite, are now CAUGHT.
  - M2a is the review's literal form (`from_state = "ACTIVE"`).
  - M2b re-introduces the original projection_prev lookup. Both are caught.
- M7–M10 are supplementary mutants for R2, R3, R9 and R10.

## 6. Probes (adapted copy at scratchpad/u2fix_probe.py; reviewer's rv_u2mut/tests/rv_probe.py untouched)

Adaptations:
- P4 prints rows plus the typed counts, because `rows[0]` no longer exists. It also adds a realistic variant: both sessions are in the calendar and now is 2027-03-01T22:00Z.
- P5 compares the payload's `corrects_fire_event_id` with the emergence fid, because `JourneyEvent.corrects` no longer exists.
- P1 prints every run-2 row of every kind.

```
P1 run1 fid: CLOSED->SUPERSEDED  run2 fid: CLOSED->SUPERSEDED  equal: True
P1 superseded rows run1: ['CLOSED->SUPERSEDED']  run2 rows (all kinds, after run1 rows sent): []  run2 duplicate_n: 2
P3 HPE rows: 1 banned_term: 0 text: HPE: the Prophet research journey you follow has closed — the setup no longer holds.
P4 (reviewer verbatim: calendar lacks the transition session) rows: 0 not_after_unresolvable: 1 stale_transition_at_mint: 0
P4 (realistic: calendar has both sessions, now 2027-03-01T22:00Z) rows: 0 not_after_unresolvable: 0 stale_transition_at_mint: 1
P5 run1 kinds: ['emergence_triggered']  run2 rows: ['superseded'] no_original: 0 superseded corrects == emergence fid: True
P6 run1 patches: [('ACTIVE->CLOSED', 'suppressed', 'superseded_by_prophet_correction')] rows: [('retracted', 'XYZ: this name is no longer tracked.')]
P6 run2 rows: [] original_producer_suppressed: 1 opted_out: None
P7 OBSERVED-retraction kinds: [('retracted', 'XYZ: an earlier observation was withdrawn; the name remains tracked.')]
```
- P1: `equal: True`, and run 2 mints nothing.
- P3: HPE mints 1 row.
- P4: the six-month-old event mints nothing, with a typed count:
  - `stale_transition_at_mint: 1` when the calendar resolves;
  - `not_after_unresolvable: 1` in the reviewer's verbatim calendar.
- P5: the supersession `corrects_fire_event_id` equals the emergence fid.
- P6: run 1 PATCHes the pending original and mints a non-presuming retraction; run 2 mints nothing on the producer-suppressed original (`original_producer_suppressed: 1`).
- P7: the relation-level copy ends "the name remains tracked."

## 7. diff --stat 6e6798aa refs/pro/b21u2-fix
```
 engine/prophet_journey_notifications.py            | 836 ++++++++++++++-------
 .../B21_ALERT_STATE_MACHINE_CONTRACT_2026-10-21.md |   4 +
 tests/test_ci_pack.py                              | 119 ++-
 tests/test_prophet_journey_notifications.py        | 692 +++++++++++++++--
 4 files changed, 1294 insertions(+), 357 deletions(-)
```
- The 119 lines in tests/test_ci_pack.py are mostly main's own content, carried so the fix side IS the resolved file: main's exclusive-curation entries and its fixed-redirect, HK-lookup, Research-API and Shared-Shell paragraphs.
- Against origin/main 1f536032, merge tree 9ded0d9e changes exactly these five paths (5 files, 3014 insertions, 2 deletions):
  - .github/ci/legacy-jobs.yml (M, +14, auto-merged from #9999)
  - engine/prophet_journey_notifications.py (A, 1329 lines)
  - the contract (M, +4)
  - tests/test_ci_pack.py (M, 25 lines: the two ceilings and the U2 paragraph)
  - tests/test_prophet_journey_notifications.py (A, 1644 lines)

## 8. merge-tree
```
$ git merge-tree --write-tree origin/main refs/pro/b21u2-fix      # origin/main = b8e7bbb7 (current), merge-base 562fc7dd
a8477006465b2397413f03cc5be98fe47be6f42e
100644 8a2fdf6d272eaf6a3beb2c055170a33cb0b7285e 1	tests/test_ci_pack.py
100644 f0ea0eb333c51187fa0755c8d77385da83de1cb8 2	tests/test_ci_pack.py
100644 fe3dbb0d15b6d1b48c31833d8a3e8631777507f2 3	tests/test_ci_pack.py

Auto-merging .github/ci/legacy-jobs.yml
Auto-merging tests/test_ci_pack.py
CONFLICT (content): Merge conflict in tests/test_ci_pack.py
rc=1
```
The same command against 1f536032 gives the identical stages (tree 9b638604, rc=1). Stage 3 (fix side) of the only conflicted path is fe3dbb0d, which is byte-identical to the resolved file. The resolution is "take the fix side wholesale":
```
$ git merge-tree --write-tree 1f536032 93158bfc6d07a03817885006936eefa51245a90f
9ded0d9e33a529012ea9579501ce5f1875a983c1
rc=0
$ git merge-tree --write-tree origin/main 93158bfc6d07a03817885006936eefa51245a90f      # origin/main = b8e7bbb7
783e4b95020daffab32523067d1e81b01749c661
rc=0
```
(Raw outputs: scratchpad/u2fix2_mt_final.txt, u2fix2_mt_M.txt, u2fix2_mt_ref.txt.)

**Why rc=1 cannot be removed under the commission's other constraints:**
- At merge-base 562fc7dd the ceiling lines read 5_825/5_798. Main rewrote those same lines (5_837/5_810 at a46365b2, now 5_841/5_814).
- A sole-parent-6e6798aa commit has three options for those lines, and none works:
  - Change them to anything else (5_844/5_817). Both sides then changed the same line, which is a CONFLICT.
  - Leave them at the base value. Main's value wins, and the merged tree gets 5_841 < 5_844.
  - Set them to main's value. The merged tree again gets 5_841 < 5_844.
- In both of the last two cases, test_packing_probe_* fails by 3.
- The only clean alternative is to fund the +3 somewhere other than the literal ceiling lines. That needs either:
  - a change to the assertion code, which the coordinator ruled out ("selector code … unchanged"); or
  - moving the U2 step out of a job that the probes select (legacy-jobs.yml), which is out of scope.

**Recommended (seat decision):** push 93158bfc (fix + main 1f536032 merge, rc=0 against current main) as the #9999 head.
- Its PR diff against main is exactly the five U2 paths above.
- A squash merge collapses it into one commit.
- 93158bfc is unreferenced (loose object in the shared store) and therefore eligible for gc after gc.pruneExpire. Anchor it with a ref, or rebuild it the same way: `git commit-tree 9ded0d9e -p 0024c326 -p 1f536032 -F <msg>` (message: scratchpad/u2merge2_msg.txt).
- Redo recipe if main moves again and touches tests/test_ci_pack.py or the CI manifest: take main's tests/test_ci_pack.py; set the index and free-content ceilings to main's values +3; insert the U2 paragraph after the "The measured before/after this wave exists to produce." line of test_exclusive_curation_narrows_ordinary_code_prs; rebuild the fix commit on 6e6798aa and the merge commit; measure with scratchpad/probe_measure2.py on the exported merge tree. A main move that touches neither file (like b8e7bbb7) needs nothing.

## 9. Interpretation notes and deviations

**Contract and key-name notes:**
- §2 `from_state` for corrected_material stays the pair `NONE->…` per the frozen fid. Retracted and superseded use the replayed lifecycle pair.
- §4 key name: the code uses `original_quarantined`; the contract text says `correction_original_effect_unknown`. The semantics are identical (mint nothing). This is a rename candidate, not changed here (fid-adjacent keys are frozen).

**Born-suppressed rows:**
- An original minted earlier in the same run is emitted with status suppressed and last_error `superseded_by_prophet_correction`.
- Rows can therefore carry 8 keys instead of 7 (last_error).
- U3 must perform the insert and the patch atomically, and must hand the producer the full B1 ledger slice (rank and replay need it).

**R2 details:**
- A missing or unparsable now_utc counts as stale. This fails closed.
- The payload's market_session is the transition's session.
- The weekend-only calendar fallback in `_session_end` (Saturday/Sunday uses the latest earlier session's next-session end) is a narrow convenience. The seat may strike it, which would make a weekend date unresolvable.

**R3:** the regex was widened beyond the review's `pe:`: it also guards `peg:` generation ids and `pe:SEC:` episode ids.

**R6:**
- "Latest prior" is ranked by B1 replay rank of the notice's cause, not by outbox insert time.
- An emergence notice whose relation is absent from the supplied ledger has no rank, so a later correction gets `no_original`. This fails closed.

**R10 residuals:**
- Watchers of the OLD ticker are not re-notified.
- The final corrected identity applies to every event of the episode in that run.

**Test-environment notes:**
- test_ci_pack needs a real git context: HEAD plus a populated, stat-refreshed index.
  - In a bare `git archive` export, `test_invalid_inventory_enters_the_existing_full_suite_planner_fallback` and `test_ancestor_init_census_does_not_grow` fail with exit 128.
  - With an index lacking stat data, every `git status`/`diff` call re-hashes the 12 GB tree, and a run takes hours.
  - Exporting GIT_DIR/GIT_WORK_TREE also redirects tests' own fixture repos.
- The gitfile plus refreshed-index setup above avoids all three problems. The acceptance run took 617 s (418 s on the superseded a46365b2 tree).
- I discarded two earlier attempts:
  - an env-var GIT_DIR with alternates to the shared 14,081-pack store, which was too slow;
  - an earlier run without any git context: 232 passed, 2 failed with exit 128.

**Other deviations:**
- origin/main moved during the work: 80854549, then bf9036b2, then a46365b2, then 1f536032, then b8e7bbb7.
  - Through a46365b2, main's ceilings stayed at 5_837/5_810; #9997 (in 1f536032) raised them to 5_841/5_814, so the fix was rebuilt (4425ba19 -> 0024c326, merge 4f2a185d -> 93158bfc).
  - b8e7bbb7 touches only two agentos/ files, so nothing was rebuilt for it.
  - Acceptance used the 1f536032 merge tree 9ded0d9e. The earlier a46365b2 acceptance outputs are kept in scratchpad/accept_prev_a46365b2/ and are superseded.
- The mutation table (§5) and the probes (§6) ran on scratchpad/u2fix_tree before the rebuild. They are reused, not rerun: the engine, the U2 suite and the contract blobs they exercise are byte-identical in 0024c326.
- DEVIATION (attribution): the trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` instead of the commission's `Claude Fable 5.1`, because this child ran on Opus 5.5 (fable-mode). This keeps attribution accurate.
