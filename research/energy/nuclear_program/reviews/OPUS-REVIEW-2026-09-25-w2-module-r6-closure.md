# Opus closure check, round 6 — PR #8002 nuclear theme-research module (2026-09-25)

- **Artifact:** PR #8002 at `e31e2db3702a68105bd67183af7e14c8fce8dd58`.
  - This head is the round-6 lane's output: lane `ene_w2_nuclear_module_r6fix` on m1, GLM, one commit "fix(energy): walk nuclear correction lineage only through servable records (R-ENE-29)".
  - The commit transcribes seat ruling R-ENE-29 (`../rulings/R-ENE-2026-09-25-w2-module-r6.md`).
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier. The brief also asked it to attack R-ENE-30, the seat's answer to #7870 RULING 11.
- **Verdict: ACCEPT_WITH_NITS.** R-ENE-29 closes the round-5 MAJOR and MINOR. **R-ENE-30 is SOUND.**
  - New findings:
    - MINOR: `known_revisions` crosses the scope and time gate. This revises the reviewer's own round-5 (6b) "relay-only" agreement.
    - NIT: the lineage pointer after a served hop is not pinned (mutant `my_pointer_from_root` survived).
    - **[Withdrawn 2026-09-28 by the same reviewer (round-7 closure NIT-1): :1300 was correct; the `def` is at :1295, the docstring at :1297-1299, and `by_revision = {… bundle.assertions` at :1300-1301 (read at `a1c8968f8e2f`). See `OPUS-REVIEW-2026-09-28-w2-module-r7-closure.md`.]** NIT: a relay line number was wrong (:1300 should be :1298-1299).
  - GAP 3 ("`r9_evrefs_pre` was not re-run at this head") is answered by the seat's post-lane output, which the reviewer did not open: `r9_evrefs_pre  3 failed, 77 passed` at `e31e2db3702a` (`r6gate/postlane6.out`).
- **Seat adjudication:** `../rulings/R-ENE-2026-09-28-w2-module-r7.md`.
  - R-ENE-31 fixes the MINOR inside Energy's own module, the reviewer's first option.
  - R-ENE-32 adds the pin.
  - **[Seat annotation 2026-09-28 (round-8 closure NIT-C): that correction was itself withdrawn. The same reviewer retracted the line-number NIT in round-7 closure NIT-1, because :1300 was correct.]** The line number is corrected at source.

## Review text (verbatim)

STATUS: PARTIAL
RESULT:
ACCEPT_WITH_NITS for e31e2db3702a. R-ENE-30 is SOUND.

**Head e31e2db3702a.**
- E5 fixes both round-5 findings:
  - MAJOR closed: the lineage walk no longer reads the raw bundle.
  - MINOR closed: a malformed predecessor row no longer raises.
- My probe now gives the same answer as the simulated R-ENE-29 in every row.
- All five required seat mutants are killed.
- One test gap (NIT): the tests never check the lineage pointer after a served middle hop.

**R-ENE-30** is correct on its three main claims:
- Nuclear pins refusal of held, rejected and review-expired records, which is the opposite of Robotics' RBV-18.
- R-ENE-27 stands on nuclear's own invariants, independently of RULING 9.
- The three strata of R-ENE-29 are correct.

**New findings:**
- **MINOR, known_revisions crosses the scope and time gate** (engine/market_ontology/nuclear_theme_research.py:210-213, used at :319-330). This revises my round-5 (6b) agreement that it was relay-only.
  - `known_revisions` is built from the raw `bundle.assertions`, upstream of every scope and time gate. Under RULING 11, that is exactly the seam where authorization lives.
  - The relay's reason for leaving it alone is "withheld existence is already disclosed by design (`*_present`)". That covers only records withheld at review. No `*_present` code announces a record from another slice or one recorded after the cutoff.
  - Concrete input, measured with a `system_replay` query (recorded_cutoff 2026-12-31) and a block reviewed 2026-09-20:
    - The block cites a record retained on 2027-06-01. It is shown as stale (`[('00d899', True)]`, reason `interpretation_stale`).
    - The same block citing a revision that does not exist is hidden and counted as `interpretation_inputs_absent:1`.
    - So the replay output as of the cutoff depends on data recorded after the cutoff: a look-ahead bit that breaks replay reproducibility.
  - In the default (latest) mode, a block citing a record from another slice is also shown as stale. It is not counted as absent.
  - Robotics has the identical construct (robotics_theme_research.py:400-402 at a1c8968f8e2f). The base composer has none (0 hits at 6cd958e92b25).
  - Before #8002 leaves DRAFT, the seat should either:
    - fix it within Energy's own module, by building `known_revisions` from `self.assertions` (after the scope and time gates, before review, so review-withheld inputs still show as stale); or
    - re-relay it with the corrected reason, next to the Robotics lineage relay.
  - It is outside the round-6 diff and is not a regression.
- **NIT, the pointer after a served hop is not pinned** (tests/test_nuclear_research_lineage.py, all cases).
  - Every withheld case withholds the served record's immediate predecessor. So the pointer is always taken from the served record itself, and "the last served record" is never exercised after a real hop.
  - Mutant `my_pointer_from_root` (pointer revision taken from the served root instead of from `current`) SURVIVES: 80 passed.
  - The correct behaviour holds today. For A → B (accepted) → C (rejected), the lineage is `['bb9f7c','da8f69']`, i.e. [B, pointer to C]. The mutant would emit [B, B-pointer].
  - Suggested test: A → B(accepted) → C(rejected) gives `[ref(B), prefix/C.revision]`.
- **[Seat annotation 2026-09-28: retracted by the same reviewer in round-7 closure NIT-1; :1300 was correct.]** **NIT, relay line number**: 5832062081 says `by_revision` is at :1300; it is at :1298-1299. Every other Robotics citation checked is exact.

EVIDENCE:
All paths are absolute. W=/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/energy-w2-review-28c2741ee34f22a6.

**State and diff**
- Command: `git -C $W fetch … && git -C $W checkout -q --detach e31e2db3…; git rev-parse HEAD origin/claude/energy-nuclear-vertical-module HEAD^`
  - HEAD and remote are both e31e2db3702a68105bd67183af7e14c8fce8dd58.
  - Parent is b3ea8a19ea05f72ea610ca627c68ef1a5452dc3e.
- Commit message: "fix(energy): walk nuclear correction lineage only through servable records (R-ENE-29)".
- `git diff --stat b3ea8a19ea05 HEAD`: `nuclear_theme_research.py | 6 +-`, `tests/test_nuclear_research_lineage.py | 89 +++`, `2 files, 92 insertions(+), 3 deletions(-)`.
- The engine diff changes exactly three lines:
  - the signature becomes `visible: list[dict[str, Any]]`;
  - `by_revision` is built `for item in visible`;
  - the call site becomes `_correction_lineage(assertion, selection.review_ok)`.
- sha256: engine `cd2b4d2d594970e3…`, test `5f3a9ec9a24046b8…`. Both match the seat's figures.

**(1) Closing the MAJOR and the MINOR**
- `PYTHONPATH=. python3 $TMPDIR/nucr3/probe_r5.py` at the new head:

  | Case | now | r29 |
  |---|---|---|
  | all accepted A>B>C | `['a4da21','920d08']` | `['a4da21','920d08']` |
  | B, C rejected | `['c27f09']` | `['c27f09']` |
  | B cross-slice | `['51b262']` | `['51b262']` |
  | B rights-refused | `['672137']` | `['672137']` |
  | B cohort-excluded | `['1faf2f']` | `['1faf2f']` |
  | B not yet recorded (replay) | `['b05fa4']` | `['b05fa4']` |

- Malformed impostor of B: `lineage now: ['3d3e82'] limits ['assertion_invalid:2']`, with no raise. `:2` is the row index, not a count; I checked with `probe_inv.py`, which gives `['assertion_invalid:1']` for the second row.
- The required tests exist and pass under `none` (80 passed):
  - `test_a_predecessor_this_query_cannot_serve_ends_the_walk` covers `[rejected]` (A→B(rejected)→C gives [B]), `[rejected_chain]`, `[other_slice]`, `[outside_cohort]`, `[not_yet_recorded]` and `[rights_refused]`;
  - `test_an_all_accepted_chain_is_walked_to_its_root` gives [B, C];
  - `test_a_malformed_row_is_never_read_as_a_predecessor` gives [B];
  - `test_correction_pair_supersedes_without_deleting` is unchanged and green.
- The collapsed-copy case is correct.
  - The selector iterates `review_ok` (:818), so it serves a collapsed copy.
  - Walking through the copy therefore names only refs the selector will answer.
  - `r29_current` is killed, by `test_a_collapsed_copy_is_walked_because_the_selector_serves_it` only.
  - This is consistent with R-ENE-11, which constrains `input_refs`, not lineage.

**(2) My amendments**
- The seen guard (:790) and the stop after emitting a pointer (:793-796) are unchanged. Command: `sed -n 780,802p`.
- `review_ok` holds only records validated by `validate_assertion` (:179-182). That validator binds the revision to the content (probe_r6: `tampered-content revision: rejected -> curation_revision_mismatch`). So a cycle among visible records cannot be built, and the guard is defence in depth.
- The slice-local cost is documented in R-ENE-29 ("Documented cost: lineage is slice-local").

**(3) Mutants**
- Command: `$TMPDIR/nucr6/run.sh`, which runs the seat's `mutplug6.py` plus my additions over the 10 nuclear test files with `--rootdir $W`. Output is in `$TMPDIR/nucr6/matrix.out`.
- Baseline `none`: 80 passed.
- The five required mutants are all KILLED:

  | Mutant | Failed | Failing tests |
  |---|---|---|
  | `r29_raw` | 7 | malformed; withheld `[not_yet_recorded, other_slice, outside_cohort, rejected, rejected_chain, rights_refused]` |
  | `r29_pre` | 2 | withheld `[rejected]`, `[rejected_chain]` |
  | `r29_current` | 1 | `test_a_collapsed_copy_is_walked_because_the_selector_serves_it` |
  | `r29_no_pointer` | 7 | same 7 as `r29_raw` |
  | `r29_one_hop` | 2 | `test_a_collapsed_copy_is_walked…`, `test_an_all_accepted_chain_is_walked_to_its_root` |

- My own mutants:

  | Mutant | Result | Detail |
  |---|---|---|
  | `my_raw_fallback` (review_ok, then raw rows) | KILLED, 7 | same names as `r29_raw` |
  | `my_reverse` | KILLED, 2 | all-accepted and collapsed-copy tests |
  | `my_continue_past_pointer` | 0 failed, EQUIVALENT | prior is added to `seen` and `current` is unchanged, so the next pass breaks. Nothing can be read past a pointer without the body. |
  | `my_no_seen` | 0 failed, EQUIVALENT under the contract | revisions are content-bound (see (2)) |
  | `my_prefix_from_served` | 0 failed, EQUIVALENT | every ref in a query shares `gmi-curation://theme:nuclear_power` |
  | `my_pointer_from_root` | 0 failed, SURVIVED | the NIT above |

- Earlier-round mutants, all still killed:

  | Mutant | Failed |
  |---|---|
  | `B1_noop` | 5 |
  | `M1M2` | 7 |
  | `M3` | 3 |
  | `M5` | 4 |
  | `m3` | 2 |
  | `m7` | 3 |
  | `cohort_off` | 7 |
  | `codes_off` | 1 |
  | `latest_only` | 1 |
  | `lineage_empty` | 10 |
  | `lt` | 1 |
  | `refday_pre` | 3 |
  | `refday_only` | 2 |
  | `presence_only` | 1 |
  | `sel_pre` | 1 |
  | `sel_current` | 1 |
  | `sup_off` | 3 |
  | `why_sup` | 1 |
  | `prd_only` | 1 |
  | `ccj_rt_exempt` | 2 |
  | `ccj_rt_cohort` | 3 |
  | `leu_nc_cohort` | 2 |
  | `nostale` | 1 |
  | `next_query` | 1 |
  | `r9_stale_pre` | 3 |
  | `r9_stale_current` | 1 |
  | `r9_reason_pre` | 3 |
  | `r9_status_pre` | 3 |
  | `r9_selected_pre` | 4 |
  | `r9_selected_review_ok` | 1 |

- Round-4 mutants that are not in the seat harness, run with `$TMPDIR/nucr3/mutplug5r.py`:

  | Mutant | Result |
  |---|---|
  | `ccj_any_exempt` | 5 failed, 75 passed |
  | `leu_any_exempt` | 3 failed, 77 passed |
  | `sel_corr_refuse` | 1 failed, 79 passed |
  | `nostale_src` | 1 failed, 79 passed |

- Still EQUIVALENT: `role_pred`, `r9_reason_review_ok`, `r9_status_review_ok` (0 failed each).
- r9_evrefs_pre, which the seat lists as killed (3 failed in round 5), is missing from both the seat's matrix6.sh and my run list. I did not re-run it at this head.

**(4) Tests**
- Red check equivalence: `r29_raw` restores the b3ea8a19 walk exactly (same body over `bundle.assertions`). It fails 7 and passes the other 2 new tests (all-accepted and collapsed-copy), matching the seat's 7 failed / 2 passed.
- No assertion is vacuous:
  - each withheld case compares full ref lists;
  - the collapsed-copy test also asserts `syndicated_collapsed`, so the copy really collapsed.
- Route test (httpx 0.28.1), command `python3 -m pytest tests/test_nuclear_research_route.py -v -rs`:
  - `test_route_filters_refused_rights_families_before_composition PASSED`
  - `test_error_responses_keep_paid_private_headers PASSED`
  - `======================== 2 passed, 81 warnings in 4.88s ========================` (no skip)
- `/opt/homebrew/bin/pyflakes` on both files: rc=0.

**(5) R-ENE-30**
- The nuclear pin `tests/test_nuclear_research_composition.py:79` (`test_review_gate_refuses_held_rejected_and_expired_evidence`) raises `not_available` for held, rejected and expired records. Confirmed by `sed -n 75,100p`.
- The retention grep over the nuclear tests and helpers gives exactly 3 unrelated hits: `temporal.py:66`, and the `retention_ref` field at `helpers.py:65` and `:425`.
- Nothing in nuclear treats a withheld record as authorized evidence:
  - the selector reads `review_ok` (:818);
  - `evidence_refs` and coverage read `current`;
  - lineage now reads `review_ok`.
- R-ENE-27 rests on nuclear's own invariants. `selected == len(input_refs)` holds on nuclear's own set, and the view reason is true. Neither needs RULING 9.
- The strata are correct:
  - (a) scope/time/rights is the class RULING 11 itself accepts;
  - (b) review follows from R-ENE-20;
  - (c) robustness is the malformed row.
- One point of RULING 11 that does apply here: it locates the authorization seam at the scope gate, and nuclear's `known_revisions` crosses that gate (the MINOR above).
  - Command: `PYTHONPATH=. python3 $TMPDIR/nucr6/probe_kr.py`
  - `other-slice (latest) shown=[('1d5ca9', True)] limits=['interpretation_stale', 'slice_scope_unowned']`
  - `recorded after cutoff (replay) shown=[('00d899', True)] limits=['interpretation_stale', 'slice_scope_unowned']`
  - `nonexistent (replay) shown=[] limits=['interpretation_inputs_absent:1', 'slice_scope_unowned']`
- The relay (comment 5832062081) is accurate about Robotics at a1c8968f8e2f (`git show a1c8968f8e2f:engine/market_ontology/robotics_theme_research.py`):
  - **[Seat annotation 2026-09-28 (round-7 closure NIT-1): the correct ranges are :1295-1320 for the function and :1300-1301 for the build.]** `_correction_lineage` is at :1293-1318, with `by_revision` over `bundle.assertions` at :1298-1299;
  - the gate at :372-396 covers validation, theme, facet, the slug-keyed drop and the time mode;
  - there is no in-composer rights gate: the only grep hits are the `rights_partial` omissions;
  - the pin at composition.py:408 `test_held_assertion_is_still_selectable_evidence` is correct;
  - robotics_theme_research.py:534 `test_rbv18_held_review_is_excluded_but_retained` is correct, with the "remains authorized evidence" assert at :545;
  - the RBV-17 lineage pins are at :358, :502 and temporal.py:156;
  - the :974-978 quote from RULING 11 matches.
  - **[Seat annotation 2026-09-28 (round-8 closure NIT-C): retracted by the same reviewer in round-7 closure NIT-1; :1300 was correct.]** The only mismatch is the :1300 line number (NIT).

**(6) Scope and privacy**
- `git diff --name-only b3ea8a19ea05 HEAD` lists exactly the two files.
- A grep of the added lines for clock, network, `open(`, `data/`, environment and credential reads found nothing (`grep-rc=1`).
- The new test builds only synthetic `variant(...)` records.
- probe_r6 prints `ref pattern ok: True` for `^gmi-curation://theme:nuclear_power/gmirca_[0-9a-f]{32}$`.

**Final state**
- `git -C $W status --short` printed nothing; `status-lines= 0`.

GAPS:
- I did not run the known_revisions MINOR on Robotics fixtures. The Robotics parity claim comes from reading the code at :400-402 only.
- The seat's own post-lane output file (postlane6.out) was not opened; every check above was re-run independently instead.
- r9_evrefs_pre was not re-run at this head (see (3)).

DEVIATIONS:
- None. The only state change was the commissioned fetch and detached checkout of e31e2db3702a. Probes and harnesses stayed under `$TMPDIR/nucr6/` and `$TMPDIR/nucr3/`, and ran with `--rootdir`. The Robotics file was read only through `git show`. The two `gh api` calls were read-only GETs. I made no edits, commits, pushes, comments or labels.