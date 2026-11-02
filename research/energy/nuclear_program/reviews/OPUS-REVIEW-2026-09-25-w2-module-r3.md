# Opus re-review, round 3 — PR #8002 nuclear theme-research module (2026-09-25)

- **Artifact:** PR #8002 at `c857ec36311a0fb52ff61480f860c0f985e2a483`.
  - Branch `claude/energy-nuclear-vertical-module`, stacked on `claude/energy-stack-base-b-6cd958e9`, which is #7870 frozen at `6cd958e92b25`.
  - This head is the round-2 fix lane's output (lane `ene_w2_nuclear_module_r2fix`, m1, GLM, one commit `c857ec36311` "fix(energy): close nuclear review gates").
- **Reviewer:** an Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`.
  - It stopped once at its 24-turn limit, mid-review. The seat resumed it on the same carrier with a bounded finish directive. Nothing was re-dispatched.
- **Verdict: FIX_REQUIRED.**
  - CLOSED: NEW-1, NEW-2, NEW-3, NEW-4 (with NIT R3-5), NEW-5, NEW-6, NEW-7, NEW-10, the NEW-8 selector, and the S1 code.
  - Every mutant the round was required to kill is killed.
  - Open:
    - R3-1 is MAJOR: NEW-9 is incomplete, and truth law L1 has no test guard.
    - R3-2 is MINOR: the S1(b) round trip never exercises `corroboration_refs`.
    - R3-3 through R3-8 are NITs.
  - The X04 rewording the seat found (DEVIATION) changed 0 test outcomes across 19 mutants. It is NIT R3-4.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-25-w2-module-r3.md` (R-ENE-24..26).
  - The seat reproduced R3-1 and R3-2 at the artifact before ruling.
  - It found R3-3 to be an equivalent mutant.

## Review text (verbatim)

STATUS: FAIL

RESULT:
**FIX_REQUIRED.** I re-reviewed PR #8002 at exact head `c857ec36311a0fb52ff61480f860c0f985e2a483`.

The fix round's code is correct. NEW-1 through NEW-7, NEW-10 and the core of S1 are closed, and every mutant the round was required to kill is killed. The result is still not acceptable, for two reasons:
- **NEW-9 is only partly done, and it leaves truth law L1 unguarded.** Promoting Cameco (CCJ) into the `reactor_technology` witness cohort, or Centrus (LEU) into `nuclear_components`, passes all 55 tests. That is the literal L1 failure ("supplemental never promoted"). X04 was restored as a fixture, but no test uses it for its packet purpose.
- **S1(b)'s round-trip test never exercises `corroboration_refs`.** A mutant that refuses advertised corroboration refs survives.

R-ENE-22 made these items required this round, so the round does not close.

**Closure table (round 2)**

Line numbers are in `engine/market_ontology/nuclear_theme_research.py` unless a test file is named.

| Id | State | Where | Test that proves it (mutant killed) |
|---|---|---|---|
| NEW-1 | CLOSED | `tests/test_nuclear_research_temporal.py`: all 5 round-1 names are back; X03 is used at :144 and :151 | `test_correction_pair_supersedes_without_deleting` kills supersession-disabled and empty-lineage |
| NEW-2 | CLOSED | :226-231 read `self.current` | `test_reference_day_ignores_a_rejected_record`, `…_a_collapsed_syndicated_copy`, `test_no_target_disclosure_when_the_only_target_is_rejected` |
| NEW-3 | CLOSED | temporal test file | `test_source_history_window_only_target_boundary` kills latest-only |
| NEW-4 | CLOSED, with a NIT (R3-5) | :76-78 | `test_every_emitted_limitation_matches_exactly_one_declared_code` now covers system_replay and the P2 recipe |
| NEW-5 | CLOSED | :142 | `test_valid_to_equal_to_reference_day_is_retrospective` kills the `<` mutant |
| NEW-6 | CLOSED | `tests/test_nuclear_research_route.py:75-88`: 400 `invalid_request` with private/no-store and noindex/noarchive; the 200 response is checked at :64-67 | `test_error_responses_keep_paid_private_headers` |
| NEW-7 | CLOSED | :612-613 | `test_superseded_interpretations_leave_why_it_matters` |
| NEW-8 | Selector CLOSED; role order OPEN (NIT R3-3) | :93-100, :498-499 | `test_businessless_product_selector_and_application_subjects` kills the old product-only branch. The role-order revert SURVIVES. |
| NEW-9 | **PARTIAL / OPEN (MAJOR R3-1)** | X04 is back on `reactor_technology`. X04C was added and its refusal really comes from the cohort gate (facet `nuclear_components` matches the slice; company `co:us:CCJ` is outside `('co:us:BWXT',)`). | `test_facet_matches_but_witness_cohort_is_excluded`. Not done: X04 is never asserted in `reactor_technology`, and the cohort-count test was never extended with CCJ/LEU. |
| NEW-10 | CLOSED | composition file (`numeric_values`, exact `[100, 50]`); temporal file (prefix check) | m7 is killed by `test_equity_method_investee_never_consolidated` |
| S1 | Code CLOSED (:818 iterates `review_ok`); test (b) OPEN (MINOR R3-2) | composition file | Reverting to `selection.assertions` is killed by `test_review_gate_refuses_held_rejected_and_expired_evidence`. The `selection.current` mutant SURVIVES. |

**Mutants.** I ran every one myself: 55 tests per run, all 8 nuclear files.

| Mutant | Result | Failing tests |
|---|---|---|
| Supersession disabled | KILLED | `test_correction_pair_supersedes_without_deleting`, `test_superseded_interpretations_leave_why_it_matters` |
| `_correction_lineage` returns `[]` | KILLED | `test_correction_pair_supersedes_without_deleting` |
| Target windows judged in latest mode only | KILLED | `test_source_history_window_only_target_boundary` |
| `≤` changed to `<` | KILLED | `test_valid_to_equal_to_reference_day_is_retrospective` |
| Reference day and presence check over `self.assertions` (full revert) | KILLED | `test_no_target_disclosure_when_the_only_target_is_rejected`, `test_reference_day_ignores_a_collapsed_syndicated_copy`, `test_reference_day_ignores_a_rejected_record` |
| Reference day only reverted | KILLED | the two `test_reference_day_ignores_*` tests |
| Presence check only reverted | KILLED | `test_no_target_disclosure_when_the_only_target_is_rejected` |
| S1: selector iterates `selection.assertions` | KILLED | `test_review_gate_refuses_held_rejected_and_expired_evidence` |
| NEW-7: superseded interpretations kept in `why_it_matters` | KILLED | `test_superseded_interpretations_leave_why_it_matters` |
| Cohort gate removed | KILLED | `test_facet_matches_but_witness_cohort_is_excluded`, `test_fuel_cycle_supplemental_witnesses_appear_only_in_that_slice`, `test_out_of_cohort_assertions_are_dropped_counted_and_absent_everywhere` |
| NEW-4: three codes removed | KILLED | `test_every_emitted_limitation_matches_exactly_one_declared_code` |
| B1 (call kept, made a no-op) | KILLED | `test_syndicated_copy_collapses_into_its_single_original`, `test_reference_day_ignores_a_collapsed_syndicated_copy` |
| M1/M2 (passed-target branch deleted) | KILLED | `test_explicit_latest_cutoff_still_decides_target_windows`, `test_latest_without_cutoff_uses_the_evidence_frontier_for_targets`, `test_milestones_never_leave_limitations_for_summary_text`, `test_passed_forward_target_stays_a_retrospective_target`, `test_same_retention_and_publication_still_judges_only_the_target_window`, `test_source_history_window_only_target_boundary`, `test_valid_to_equal_to_reference_day_is_retrospective` |
| M3 (sort by negated value) | KILLED | `test_rows_order_is_deterministic_never_by_magnitude`, `test_contingent_backlog_rows_never_summed_or_funded`, `test_correction_pair_supersedes_without_deleting` |
| M5 (`:1` hard-coded) | KILLED | `test_out_of_cohort_assertions_are_dropped_counted_and_absent_everywhere`, `test_composer_defence_in_depth_excludes_unmapped_rights_source` |
| m3 (`establishes[0]` read restored) | KILLED | `test_attributed_interpretation_is_never_a_view_row`, `test_milestones_never_leave_limitations_for_summary_text` |
| m7 (investee figure summed into Cameco's row) | KILLED | `test_equity_method_investee_never_consolidated`, `test_contingent_backlog_rows_never_summed_or_funded`, `test_correction_pair_supersedes_without_deleting` |
| Route rights filter set to identity | KILLED | `test_route_filters_refused_rights_families_before_composition` |
| My extra: NEW-8 old product-only selector restored | KILLED | `test_businessless_product_selector_and_application_subjects` |
| **My extra: role sort key back to `predicate`** | **SURVIVED** | — |
| **My extra: selector iterates `selection.current`** | **SURVIVED** | — |
| **My extra: CCJ exempt from the cohort in `reactor_technology`** | **SURVIVED** | — |
| **My extra: `WITNESS_COHORT` gains CCJ in `reactor_technology`** | **SURVIVED** | — |
| **My extra: `WITNESS_COHORT` gains LEU in `nuclear_components`** | **SURVIVED** | — |
| My extra: `WITNESS_COHORT` gains LEU in `reactor_technology` | KILLED | `test_fuel_cycle_supplemental_witnesses_appear_only_in_that_slice` |
| My extra: `WITNESS_COHORT` gains CCJ in `nuclear_components` | KILLED | 2 composition tests |
| **My extra: `interpretation_stale` removed from `LIMITATION_CODES`** | **SURVIVED** | — |

**probe_r2.py re-run at the new head**

| Probe | Output | Required by the rulings | Verdict |
|---|---|---|---|
| P0 | refs match `gmi-curation://theme:nuclear_power/gmirca_<32 hex>` | ref shape unchanged | OK |
| P1 | N03 alone: False, `target_windows_judged_at:2026-09-20`, N03 in `next_evidence`. With a rejected 2028 record: identical, plus `rejected_present`. | day and code unmoved | OK |
| P1b | N03 False, code `…:2026-09-20` | same as P1 | OK |
| P1c | 0 commercial rows; limitations `['rejected_present']` | no `target_windows_judged_at:` code | OK |
| P2 | `unmatched []` | empty | OK |
| P3 | `{'gmirca_6d961b6': True}` | True | OK |
| P4 | `{'gmirca_08393ac': True, 'gmirca_bc45c1a': False}` | N03C True, N03D False | OK |
| P4b | same values, plus `target_windows_judged_at:2026-09-19` | — | OK |
| P5 | N03 row retrospective True AND N03 in `next_evidence` | — | NIT R3-6 |
| P6 | the shared contract rejects empty coverage (same as round 2) | — | n/a |
| P7 | `why_it_matters` refs `['gmirca_38a5518']` (X01B only); `superseded_present` True | superseded X01 absent | OK |
| P8 | L2 hits `[]` | none | OK |
| P9 | DEPLOYMENT_TARGET / FORWARD_TARGET, retrospective True, `next_evidence` `[]` | L5 | OK |
| P10 | values `[100, 50, 1, 3]`; total `totals_not_computed`; 150 absent | L3/L4 | OK |
| P11 | selector `[None]`, errs `[]` | matches Robotics | OK |

My own extra NEW-2 attacks: late records that are held, review-expired, in another facet, out of cohort, or on an nrc.gov source each leave the code at `target_windows_judged_at:2026-09-20` and N03 at retrospective False.

**R-ENE-19 test names and fixtures**

Test names, 9e3237ef → head, "missing" lists empty in every file. Counts: 4→4, 5→5, 2→2, 17→20, 2→2, 1→2, 6→7, 3→13. All five round-1 temporal names are present.

Also compared against 1071dd9 (pre-existing since 9e3237ef, not a round-3 change):
- Missing: `test_misfaceted_supplemental_assertion_is_dropped_and_counted`. The build packet names it for L1, and no ruling authorised its removal.
- Missing: `test_unmapped_rights_source_is_excluded_from_rows_and_evidence`. Its rename was authorised by R-ENE-10 / M4.
- Missing: `test_bundle_declares_exactly_three_absent_surfaces`. Its rename was authorised by the round-1 nit ruling.

Fixtures, compared with `ast`:
- N01–N12, X01–X03, N03B: same at all three heads.
- N13, N14, X05–X08, N03C, N03D, X04B, X02B, X09, X10: new at 9e3237ef, same since.
- X04C: new at head (allowed).
- `_assertion`: changed round 1, same since.
- X04: changed at both steps. Facet, company, predicate, mode, period and observation now equal 1071dd9. Only `product` and `establishes` differ; those are the seat's deviation, judged below.
- No packet fixture other than X04 changed after 9e3237ef, so there is no BLOCKER.

**X04 deviation probe (required by the seat)**
- I rebuilt X04 with its byte-exact 1071dd9 arguments through the head's `_assertion` (revision `gmirca_ef1fd417b780e…`, different from the head's).
- I injected it into `helpers.X04` and `FIXTURES["X04"]` inside `pytest_configure`, before the test modules import, and asserted after collection that `tests.test_nuclear_research_codes` and `tests.test_nuclear_research_composition` bound the substituted object.
- I ran the whole matrix twice (head X04 and original X04): baseline plus 19 mutants, including every mutant X04 takes part in (cohort, M5, codes).
- Result: **0 per-test outcome differences.** The rewording weakened no test, so it is a **NIT (R3-4): restore the text.**

**Route test**
- Command: `tests/test_nuclear_research_route.py` with `-v -rs` (httpx 0.28.1, fastapi 0.141.1).
- Output: `::test_route_filters_refused_rights_families_before_composition PASSED`, `::test_error_responses_keep_paid_private_headers PASSED`, `2 passed, 90 warnings`. No skip.
- Rights still go through `app/theme_research.py`: making `_filter_bundle_for_rights` return `(bundle, False)` fails `test_route_filters_refused_rights_families_before_composition` (`'rights_refused_families_hidden' in [...]` is false).

**New findings**
- **R3-1 — MAJOR (NEW-9 incomplete; L1 unguarded).**
  - Three plugins show it:
    - `WITNESS_COHORT["reactor_technology"] += ("co:us:CCJ",)` → `55 passed`;
    - `WITNESS_COHORT["nuclear_components"] += ("co:us:LEU",)` → `55 passed`;
    - a CCJ exemption from the cohort gate in `reactor_technology` → `55 passed`, and `compose(reactor_technology, capacity, [X04])` returns rows `['Cameco']` with no `witness_cohort_excluded`.
  - Causes:
    - X04 is used only by the codes matrix (`tests/test_nuclear_research_codes.py:15,17`) and as a facet-gated passenger at `tests/test_nuclear_research_composition.py:55`. No test composes it in `reactor_technology` and asserts the drop and count, which is what the packet-named L1 test did at 1071dd9 :37-41.
    - This round swapped X04 out of `test_fuel_cycle_supplemental_witnesses_appear_only_in_that_slice` (:58, now `N07, X04B`).
    - The cohort-count test (:41-51) still uses SMR variants only. The ruling's "extend … with CCJ/LEU variants" was not done.
    - `WITNESS_COHORT` is pinned by no test (grep finds no hit).
  - Fix: restore `test_misfaceted_supplemental_assertion_is_dropped_and_counted` over X04 in `reactor_technology` (drop, `witness_cohort_excluded:1`, evidence refusal). Add CCJ and LEU count variants for both primary slices, and an exact-tuple pin for `WITNESS_COHORT`.
- **R3-2 — MINOR (S1(b) test is vacuous for corroboration).**
  - `test_advertised_and_corroborating_evidence_round_trips` (composition :98-114) bundles N04, a correction of N04 and a copy of "Synthetic Energy Filings". Two originals match, so the copy never collapses: probe `syndicated_collapsed? False corroboration_refs [[], [], []]`.
  - The selector mutant `for assertion in selection.current:` survives 55/55. On a bundle that does collapse (N04 plus copy), that mutant refuses the advertised `corroboration_refs` entry: `REFUSED not_available`.
  - The head code is correct (probe: both refs SERVED, and no selector-vs-advertised mismatch anywhere in the corpus). Fix the fixture so the copy collapses, and assert `syndicated_collapsed`.
- **R3-3 — NIT (NEW-8 role order untested).** The `role_pred` revert (:499) survives. The lane also added `roles.sort(...)` in `tests/test_nuclear_research_sections.py:81`, which would mask any ordering check. Assert the composer's order on a two-role subject.
- **R3-4 — NIT (seat deviation, X04 text).** `tests/nuclear_research_helpers.py:301,303` reword `product` and `establishes`. This has no effect on any test (probe above). Restore the 1071dd9 strings. The lane's "Restored frozen X04" left the rewording undisclosed.
- **R3-5 — NIT (NEW-4 matrix).** The ruling asked for "the stale-interpretation fixture". `stale_payload()` (`tests/test_nuclear_research_codes.py:32-41`) is really the P2 same-day recipe under a misleading name. Removing `interpretation_stale` from `LIMITATION_CODES` gives `9 passed`.
- **R3-6 — NIT (pre-existing; seat to clarify).**
  - P5: in source_history with cutoff 2026-12-31, N03 (valid_to 2027-12-31, retained after published) shows row `retrospective: True` (archival rule), yet it stays in `next_evidence`.
  - The rows call `_is_passed_target` with `query` at :399-400; the summary calls it without `query` at :592. Read literally, that conflicts with R-ENE-11 ("excludes every assertion `_is_passed_target` judges passed").
  - The behaviour is truthful, because the window is still open.
- **R3-7 — NIT (family observation).**
  - The `select_authorized_evidence` lineage (:782-800) walks `bundle.assertions`, so it names a rejected predecessor's ref that the selector refuses (probe: `lineage ['…570607b4b2a1'] selector on it: refused:not_available`). The row also echoes `correction.predecessor_revision`.
  - These are pointers, not content. Relay to the shell owner; not an Energy fix this round.
- **R3-8 — NIT.** `_subject_selector` leaves out Robotics' `source_platform_label` branch (Robotics :296-298), although R-ENE-21 says "exactly". It is unreachable with the nuclear fixtures, and `industrial_row.kind` admits only business/product. Record it as a deliberate difference.

**Energy laws L1–L9**
- **L1: code HOLDS; test guard BROKEN (R3-1).** The cohort gate is at :193. `supplemental_basket_witnesses` is added at :169-170. A CCJ promotion into `reactor_technology` or an LEU promotion into `nuclear_components` passes every test.
- **L2 HOLDS.** P8 finds no hits; the m3 mutant is killed.
- **L3 HOLDS.** P10 total is `totals_not_computed`; M3 and m7 are killed by `test_contingent_backlog_rows_never_summed_or_funded`.
- **L4 HOLDS.** P10 values `[100, 50, 1, 3]`; m7 is killed by `test_equity_method_investee_never_consolidated`.
- **L5 HOLDS.** NEW-2 is fixed (:226-231). P1, P1b and P1c pass, and so do my five extra late-record attacks. P9: a passed target stays DEPLOYMENT_TARGET / FORWARD_TARGET with retrospective True.
- **L6 HOLDS.** :742-755 are unchanged, and `test_nulls_stay_null_never_zero` passes.
- **L7 HOLDS.** The shared `family_for_source_ref` is used at :196. The route mutant and M5 are killed, and the composer defence-in-depth test passes.
- **L8 HOLDS.** The shared `_row_sort_key` is used at :659; M3 is killed; `AUTHORITY` comes from the shared module.
- **L9 HOLDS.**
  - The purity grep hits only the docstring at :244.
  - All 30 fixture refs match the `theme:nuclear_power/gmirca_<32 hex>` pattern.
  - Fixtures are under `sec.gov/Archives/edgar/data/synthetic/`.
  - There is no data/, network, clock or credential read.

**Scope**
- The name-only diff against `6cd958e9…` lists exactly the 12 owned files. No shared or shell file is touched.
- `c857ec36311` is one commit on top of `9e3237efdef`.

EVIDENCE:
- **Head and refs.**
  - `git -C $W rev-parse HEAD` → `c857ec36311a0fb52ff61480f860c0f985e2a483`. The checkout was at 9e3237ef, so I ran the permitted fetch and detached checkout.
  - `ls-remote`: module branch `c857ec36…`; base `6cd958e92b259f7221690547e7076f4a0de4ed33`.
  - `merge-base --is-ancestor c857ec36311a origin/main` → `NOT_ANCESTOR`.
  - `git log 9e3237efdef6..c857ec36311a` → `c857ec36311 fix(energy): close nuclear review gates`, 8 files, +260/−45.
- **Baseline.** 8 nuclear files, `55 passed` (the `none` run of the matrix, both X04 modes).
- **Mutants.**
  - Plugin `$TMPDIR/nucr3/mutplug3.py` applies exact source replacements, each asserting `count == 1`. The runner is `$TMPDIR/nucr3/runall.sh` (xargs -P6, `MUTANT`/`X04ORIG` env), with per-test JSON in `$TMPDIR/nucr3/out/`.
  - One-off plugins: `cohortpromote.py`, `cohortpromote2.py`, `nostale.py`, `routemut.py`.
  - Summary lines:
    - B1 `2 failed, 53 passed`; M1M2 `7 failed`; M3 `3 failed`; M5 `2 failed`; m3 `2 failed`; m7 `3 failed`;
    - `codes_off` `1 failed`; `cohort_off` `3 failed`; `latest_only` `1 failed`; `lineage_empty` `1 failed`; `lt` `1 failed`;
    - `refday_pre` `3 failed`; `refday_only` `2 failed`; `presence_only` `1 failed`; `sel_pre` `1 failed`; `sup_off` `2 failed`; `why_sup` `1 failed`; `prd_only` `1 failed`;
    - `role_pred`, `sel_current`, `ccj_rt_exempt`, CCJ→`reactor_technology`, LEU→`nuclear_components`: each `55 passed`;
    - `nostale`: `9 passed`.
- **X04 probe.** The comparison script printed `x04 diffs: 0` and `x04 substituted rev gmirca_ef1fd417b780e checked modules ['tests.test_nuclear_research_codes', 'tests.test_nuclear_research_composition']`. The M3/m3 pair was re-run separately because of a filename clash (next section): identical failing sets in both X04 modes.
- **Probes.**
  - `PYTHONPATH=. python3 $TMPDIR/nucr3/probe_r2_p6guard.py`: the verbatim appendix, with only the P6 `variant()` call moved inside its `try`, because it raises on this contract. The same happened in round 2.
  - `$TMPDIR/nucr3/probe_r3.py` holds the S1, NEW-2, lineage, codes and ref-shape attacks. Key lines:
    - `S1b-lane-test: syndicated_collapsed? False corroboration_refs [[], [], []] rows 3`
    - `selector==advertised mismatches over corpus: []`
    - `unmatched over corpus x modes: set()`
    - `ref shape all ok: True 30`
    - `P5 … row retro True in next_evidence True`
- **Test-name diff and fixtures.** A bash loop of `git show <c>:<file> | grep -E '^def test_'` with `comm -23`; `$TMPDIR/nucr3/fixcmp.py` does the `ast` comparison.
- **Static.** `pyflakes_rc=0` over the 11 owned `.py` files. The purity grep's only hit is `:244` (docstring). The name-only diff is quoted above.
- **Final state.** `git -C $W status --short | wc -l` → `0`, shown after the last run.

GAPS:
- I did not open the lane's own report on m1 (the ssh read). Nothing here relies on it, and its "Restored frozen X04" wording is taken from the seat's brief only.
- I did not re-run the adjacent shared suites. The module touches no shared file, per the name-only diff.
- Round-2 GAPS still stand: no evidence-route test (R-ENE-15, the shell's pattern), and L1 rests on the limitation code and slice label because the shared row cannot carry the cohort relation.
- `_now_of_query` (the review-expiry clock) still reads the pre-gate list. R-ENE-18 puts it out of scope, so it is not a finding.

DEVIATIONS:
- STATUS is FAIL because the verdict is FIX_REQUIRED.
- Mutants were applied by exec'ing replaced source into the live module from a `$TMPDIR` pytest plugin, not by editing files. `$W` stayed clean throughout.
- My first matrix wrote `M3.*.json` and `m3.*.json` into the same files, because macOS paths are case-insensitive. I re-ran both separately and quote those results.
- The round-1 m3 mutant and the m7 mutant are semantic equivalents of the ruled edits: the `establishes[0]` read put back into `_text_of`, and the second same-company economics value added into the first row.
- The round-2 probe needed its P6 guard moved (above). Nothing else in it was changed.
