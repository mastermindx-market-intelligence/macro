# A02 — update and SYNTHETIC correction acceptance (lane A02-1, programme DATA-OS-COMPLETION)

## Scope

- Start commit: `15bc4a7b392f152518c9fb8b822bd336ddc108b5`; lane branch `lane/dataos-a02-1`.
- Evidence class: **SYNTHETIC hermetic fixtures through the real read seams**
  (`read_contract.current/reconstruct/replay`, `price_views.reconstruct_price_view/retain_view/reopen_view`).
  This is acceptance of the update/correction read semantics, **not** of a natural production update —
  every generation, action row and correction in the suite is a controlled SYNTHETIC case; the
  correction `SYN-S1C` is a controlled SYNTHETIC correction, NOT a natural vendor event.
- Suite: `tests/verification/test_a02_corrections.py` (25 collected items, 0 skipped, all PASS on main;
  no FINDING was raised). In-memory rows plus fixed UTC literals only; nothing under any stored tree is read.
- Blob pins at the start commit (all six verified before any test was written):

  | path | blob |
  |---|---|
  | `lib/dataos/price_views.py` | `9ceb782f6426bc8d701341f433d0d0eb7e8dedb8` |
  | `lib/dataos/read_contract.py` | `460fc9403c28eefc771710cbd5b2ecd43bedfdd5` |
  | `research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md` | `784b6c259815ccdc1324bd7345499699d3c6122c` |
  | `tests/test_dataos_price_revisions.py` | `d38ab1036c685b4f5c5e652a8b0f4bd694006a59` |
  | `lib/dataos/registry.py` | `65b0d69036da97760f20241468f2549b21d9c686` |
  | `lib/dataos/temporal.py` | `094b149a8b9158f19cb99c4005568c12db96ed41` |

## Timeline

One SYNTHETIC listing `SYN-LST.A02` (security `SYN-SEC-A02`, venue `XNYS`, dataset `SYN-DS-A02-SPLITS`).
Five trading days D1..D5 = 2026-06-01..06-05, new day D6 = 2026-06-08; split ex-date D3 = 2026-06-03.
Every row of this table is SYNTHETIC.

| instant (UTC) | object | meaning |
|---|---|---|
| 2026-05-20 | `SYN-S1` (2/1 forward split, ex D3) + actions generation `SYN-AG1` | SYNTHETIC original event, published before T1 |
| 2026-06-06 T1 | bars generation `SYN-G1` (D1..D5) | SYNTHETIC day-5 source generation |
| 2026-06-07 | cutoff CUT_A (in [T1, T2)) | view A's as-of instant |
| 2026-06-09 T2 | bars generation `SYN-G2`, supersedes `SYN-G1` (D1..D5 identical + D6) | SYNTHETIC ordinary NEW-DAY update |
| 2026-06-09 12:00 | cutoff CUT_B (in [T2, T3)) | view B's as-of instant |
| 2026-06-10 T3 | `SYN-S1C` (3/1, supersedes `SYN-S1`) + actions generation `SYN-AG2` | a controlled SYNTHETIC correction, NOT a natural vendor event |
| 2026-06-10 12:00 | cutoff CUT_C (in [T3, T4)) | the corrected view's as-of instant |
| 2026-06-11 T4 | bars generation `SYN-G3`, supersedes `SYN-G2` (row values identical to `SYN-G2`'s; only `generation_id`/`published_at`/`ingested_at` differ) | SYNTHETIC receipt-only generation (D5.3) |

Retained outputs: `SYN-OUT-A` (view A: `SYN-G1` × `SYN-S1` at CUT_A), `SYN-OUT-B` (view B: `SYN-G2` ×
`SYN-S1` at CUT_B). The corrected view (CUT_C) is never retained — its retention under `SYN-OUT-B` is
the A02.02 refusal case.

## Acceptance map

| id | requirement | test node id | verdict |
|---|---|---|---|
| A02.01 | new eligible current view B visible while exact retained A reopens unchanged, correct mode/source labels | `test_a02_01_step1_retain_view_a_under_its_receipt`, `test_a02_01_step2_new_day_generation_is_current`, `test_a02_01_step2_current_takes_no_mode_parameters[cutoff/clock/output_id]`, `test_a02_01_step2_view_b_composes_from_the_new_generation`, `test_a02_01_retained_a_reopens_byte_exact_after_b`, `test_a02_01_old_cutoff_reconstruction_binds_g1_and_is_labelled_reconstruction`, `test_a02_01_superseded_generation_is_never_current_even_if_stamped_later`, `test_a02_mode_matrix_after_the_full_sequence[...]` | PASS |
| A02.02 | synthetic or manually injected correction never called natural | `test_a02_02_synthetic_correction_is_a_new_revision_set_vintage_and_receipt`, `test_a02_02_old_receipt_cannot_publish_the_corrected_view`, `test_a02_02_every_correction_fixture_is_labelled_synthetic`, `test_a02_02_returns_before_and_after_the_correction_differ_only_where_the_factor_moved` | PASS |
| A02.03 | unchanged data body with a new refusal/rights generation cannot keep an invalid current view active | `test_a02_03_evidence_naming_a_superseded_generation_is_stale[SYN-G1]`, `[SYN-G2]`, `test_a02_03_receipt_only_generation_is_current_although_the_rows_did_not_move`, `test_a02_03_pinned_superseded_generation_is_stale_for_current`, `test_a02_dependent_current_evidence_naming_the_pre_correction_actions_generation_is_stale` | PASS (as modelled) + GAP (no refusal/rights field on `GenerationRef`/`ViewVintage`; A02.03 is tested as a receipt-only superseding generation, D5.3) |
| A02.04 | no wait for a future corporate action to postpone otherwise ready tests | `test_a02_04_no_wall_clock_and_no_future_event` (and the whole suite: every fixture instant is a fixed UTC literal before 2026-10-13, no wall clock anywhere) | PASS |
| WP step 1 | consume an existing naturally produced update through the original owner after checking active operations | not exercisable from a hermetic lane | UNFINISHED: natural new-day update through the original owner — hermetic lane; routed to the R03 cycle plan |
| WP step 2 | use actual recorded revisions when available and controlled isolated revision cases for missing event classes | every revision case here is a controlled isolated SYNTHETIC case (new-day update, split correction, receipt-only generation) | UNFINISHED for recorded revisions (see Pending legs) / PASS for the controlled SYNTHETIC cases |
| WP step 3 | verify current selection, exact old read, dependent invalidation and truthful evidence-class labels | `test_a02_01_step2_new_day_generation_is_current` (current selection), `test_a02_01_retained_a_reopens_byte_exact_after_b` + `test_a02_retained_a_still_refuses_tampered_or_missing_material[...]` (exact old read), `test_a02_03_*` + `test_a02_dependent_*` (dependent invalidation), `test_a02_01_old_cutoff_reconstruction...` (truthful labels) | PASS |

## Mode matrix

World = the ledgers supplied at that step of the sequence. "observed ad-hoc" marks a cell observed
through the same seams in a one-off run (not an asserting test); every other cell is asserted by the
named test. gen = the bars generation the mode binds.

| step (world) | CURRENT | RECONSTRUCT at A's cutoff (CUT_A) | REPLAY of A (`SYN-OUT-A`) |
|---|---|---|---|
| A retained (bars: G1) | gen `SYN-G1`, label `current` (observed ad-hoc) | gen `SYN-G1`, label `reconstruction` (step-1 test) | label `replay`, A's exact bytes (reopen test) |
| B update (bars: G1,G2) | gen `SYN-G2`, label `current`, rows incl. D6, evidence carries no `cutoff`/`clock` keys (step-2 current test) | gen `SYN-G1`, label `reconstruction` (observed ad-hoc at this step; asserted with the full ledger below) | label `replay`, A's exact bytes (reopen-after-B test) |
| correction (bars: G1,G2; actions: S1+S1C, ledger AG1,AG2) | bars gen `SYN-G2`, actions gen `SYN-AG2`, label `current` (observed ad-hoc); evidence naming `SYN-AG1` → refusal `STALE_GENERATION` (dependent-invalidation test) | gen `SYN-G1`, the 2/1 ratio, label `reconstruction`, values equal A's (old-cutoff test) | label `replay`, A's exact bytes; tampered → `RETAINED_DIGEST_MISMATCH`, missing/wrong id → `NO_RETAINED_OUTPUT` (negatives test) |
| receipt-only (bars: G1,G2,G3) | gen `SYN-G3`, label `current`, bound row values equal G2's (receipt-only test); evidence naming `SYN-G1`/`SYN-G2` → `STALE_GENERATION`; pinned `SYN-G2` → `STALE_GENERATION` | gen `SYN-G1`, label `reconstruction` (old-cutoff test, full ledger) | label `replay`, A's exact bytes (mode-matrix test) |

## D5 conformance

| rule | observed behaviour | verdict |
|---|---|---|
| D5.1 a generation is immutable and complete; the pointer moves atomically to a complete generation only | only the selected generation's rows ever serve (`SYN-G2`'s five shared days serve identically before and after; `SYN-G3` serves exactly `SYN-G2`'s values); each dependency binds exactly one generation id per read. The producer-side atomic capture (alias table + master + receipt together) is not reachable from the read seams and is never contradicted here | CONFORMS (read side) |
| D5.2 a correction publishes a new generation carrying `supersedes`; the superseded generation stays readable by id for RECONSTRUCT/REPLAY and is never selected by CURRENT | `SYN-G2`/`SYN-G3` supersede and CURRENT binds the live generation even when the superseded one carries the later stamp; A's cutoff still binds `SYN-G1` with the old ratio; retained A replays byte-exact | CONFORMS |
| D5.3 a receipt-only change (identical bytes, different receipt) is a new generation; a prior refusal cannot disappear because the bytes did not move | `SYN-G3` (identical row values) becomes the CURRENT generation; evidence naming `SYN-G1`/`SYN-G2` is `STALE_GENERATION`, a pinned `SYN-G2` is `STALE_GENERATION` | CONFORMS |
| D5.5 exact replay only when the original output and its material are retained; otherwise the read is a reconstruction and says so | `reopen_view(A)` serves A's exact bytes with label `replay`; the same values recomputed at A's old cutoff are labelled `reconstruction`, never `replay`; tampered/missing material refuses `RETAINED_DIGEST_MISMATCH`/`NO_RETAINED_OUTPUT` | CONFORMS |

## Relation to the P05/P06 unit tests

The existing units (`tests/test_dataos_price_revisions.py`, `test_P05_01_*`..`test_P06_*`) pin
single-step facts of RECONSTRUCT and REPLAY; none calls `read_contract.current`. A02 is sequence-level:
one fixture world through update → correction → receipt-only, all three modes at each step.

| A02 test | nearest existing test | what A02 adds |
|---|---|---|
| `test_a02_01_step1_retain_view_a_under_its_receipt` | `test_P05_01_retained_view_reopens_byte_exactly` | the receipt equals `view_receipt_sha256("SYN-OUT-A", vintage, digest)` at retain time, and step 1 of a multi-step sequence |
| `test_a02_01_step2_new_day_generation_is_current` | none (no existing test calls `current`) | the first CURRENT-mode binding over a superseding ledger: gen `SYN-G2`, D6 present, and the no-`cutoff`/no-`clock` evidence law |
| `test_a02_01_step2_current_takes_no_mode_parameters` | none (request-shape law untested in P05/P06) | CURRENT with `cutoff`/`clock`/`output_id` refuses `ReadContractError` |
| `test_a02_01_step2_view_b_composes_from_the_new_generation` | `test_P05_01_corrected_old_bar_is_a_new_vintage_not_a_rewrite` | the NEW-DAY shape (D6 appended, prior days identical) rather than a corrected bar; six-row view; label naming `source_generation=SYN-G2` |
| `test_a02_01_retained_a_reopens_byte_exact_after_b` | `test_P05_02_the_retained_older_view_still_returns_the_old_rows` | byte-equality of the payload (not just rows) and the vintage, reopened after a LATER generation exists |
| `test_a02_01_old_cutoff_reconstruction_binds_g1_and_is_labelled_reconstruction` | `test_P05_02_correction_known_after_the_cutoff_is_invisible` | the truthful label: equal values to A's but `reconstruction`, never `replay` (D5.5) |
| `test_a02_01_superseded_generation_is_never_current_even_if_stamped_later` | none | the D5.2 stamp-vs-edge law: the `supersedes` edge, not `published_at`, decides CURRENT |
| `test_a02_mode_matrix_after_the_full_sequence` | none | the cross-mode answer for the same question after the full sequence |
| `test_a02_02_synthetic_correction_is_a_new_revision_set_vintage_and_receipt` | `test_P05_02_correction_known_before_the_cutoff_moves_view_and_vintage` | the correction composes over the NEW-DAY generation (not a corrected bar); same output id, receipt and digest inequality |
| `test_a02_02_old_receipt_cannot_publish_the_corrected_view` | `test_P05_03_an_old_receipt_cannot_publish_a_new_generation` | the receipt move is a REVISION-SET move (view digest + vintage) under one unchanged output id |
| `test_a02_02_every_correction_fixture_is_labelled_synthetic` | none | the SYNTHETIC-labelling law over every fixture id and pending leg (and over this record when present) |
| `test_a02_02_returns_before_and_after_the_correction_differ_only_where_the_factor_moved` | `test_P05_04_a_constant_rescale_cancels_in_simple_returns_a_correction_does_not` | the factor move localized exactly to the ex-date-spanning return, exact Fractions |
| `test_a02_03_evidence_naming_a_superseded_generation_is_stale` | none | `STALE_GENERATION` for CURRENT evidence naming a superseded ledger id |
| `test_a02_03_receipt_only_generation_is_current_although_the_rows_did_not_move` | `test_P05_01_corrected_old_bar_is_a_new_vintage_not_a_rewrite` (bytes moved there) | the receipt-only generation (D5.3): current moves while the row values do not |
| `test_a02_03_pinned_superseded_generation_is_stale_for_current` | none | a pinned superseded id is stale for CURRENT |
| `test_a02_dependent_current_evidence_naming_the_pre_correction_actions_generation_is_stale` | none | dependent invalidation: the ACTIONS ledger's generation move staleness |
| `test_a02_retained_a_still_refuses_tampered_or_missing_material` | `test_P05_01b_tampered_payload_refuses_RETAINED_DIGEST_MISMATCH`, `test_P05_01b_missing_material_or_wrong_output_id_refuses_NO_RETAINED_OUTPUT` | the same refusals asserted AFTER the full update+correction+receipt-only sequence |
| `test_a02_04_no_wall_clock_and_no_future_event` | none | the no-wall-clock / fixed-literal-instant law asserted on the module itself |

## Pending legs

`PENDING_LEGS` (asserted non-empty by `test_a02_02_every_correction_fixture_is_labelled_synthetic`),
verbatim:

- `UNFINISHED: natural new-day update through the original owner — hermetic lane; routed to the R03 cycle plan`
- `UNFINISHED: actual recorded revisions — hermetic lane, no data/ reads; every revision case here is a controlled SYNTHETIC case`
- `GAP: no refusal/rights generation field on GenerationRef or ViewVintage; A02.03 is tested as a receipt-only superseding generation (D5.3)`
- `GAP: no CURRENT-mode price-view composition; CURRENT is exercised at read_contract.current, the price view B is a RECONSTRUCT composition`

What closes each:

- Leg 1 → the R03 second-cycle acceptance: one real producer run consumed through the original owner
  (a real generation transition observed end to end), out of this hermetic lane's reach.
- Leg 2 → a lane permitted to read recorded revisions (a non-hermetic read lane or the R03 cycle),
  replaying the same assertions over recorded rows instead of controlled SYNTHETIC ones.
- Leg 3 → a refusal/rights field on `GenerationRef`/`ViewVintage` (a production change owned elsewhere),
  after which A02.03 can be restated against a true refusal/rights generation rather than the
  receipt-only model.
- Leg 4 → a CURRENT-mode composition in `price_views` (production change owned elsewhere); until then
  CURRENT is exercised at `read_contract.current` and the price view B stays a RECONSTRUCT composition.

The §1 grep, quoted (run at the start commit in the lane worktree):

```
$ grep -n "ReadMode.CURRENT\|read_contract.current" lib/dataos/price_views.py
(no output; exit status 1)
```

## Mutation sensitivity

Procedure: a detached mutation worktree added at HEAD (lane-local, never pushed); each mutation is a
≤ 6-line edit in that tree only; the suite runs there; `git checkout -- lib/` restores before the next
mutation. **Killed 6/6. No survivor.**

| id | mutation | failing tests in the mutation tree |
|---|---|---|
| AM1 | `read_contract._current_generation` ignores `supersedes` (`superseded = set()`) | `test_a02_01_superseded_generation_is_never_current_even_if_stamped_later` |
| AM2 | `read_contract.current` skips the identity-coherence loop | `test_a02_03_evidence_naming_a_superseded_generation_is_stale[SYN-G1]`, `[SYN-G2]`, `test_a02_dependent_current_evidence_naming_the_pre_correction_actions_generation_is_stale` |
| AM3 | `price_views.retain_view` skips the supplied-receipt comparison | `test_a02_02_old_receipt_cannot_publish_the_corrected_view` |
| AM4 | `price_views.reconstruct_price_view` uses a constant revision set id (`"actions:fixed"`) | `test_a02_02_synthetic_correction_is_a_new_revision_set_vintage_and_receipt` |
| AM5 | `read_contract.current` labels its result `"reconstruction"` | `test_a02_01_step2_new_day_generation_is_current`, `test_a02_mode_matrix_after_the_full_sequence[current]` |
| AM6 | `read_contract.select_generation` ignores the cutoff | `test_a02_01_step1_retain_view_a_under_its_receipt`, `test_a02_01_step2_view_b_composes_from_the_new_generation`, `test_a02_01_retained_a_reopens_byte_exact_after_b`, `test_a02_01_old_cutoff_reconstruction_binds_g1_and_is_labelled_reconstruction`, `test_a02_mode_matrix_after_the_full_sequence[reconstruct_at_a_cutoff]`, `test_a02_02_synthetic_correction_is_a_new_revision_set_vintage_and_receipt`, `test_a02_02_returns_before_and_after_the_correction_differ_only_where_the_factor_moved` |

## Findings

None. Every asserted behaviour held on main at the start commit; no strict-xfail was needed.

## Commands

All run from the lane worktree; `PY` names the lane's pinned venv interpreter.

- P1 (twice): `PYTHONDONTWRITEBYTECODE=1 PY -m pytest tests/verification/test_a02_corrections.py -rs -q -p no:cacheprovider`
  - run 1 last line: `25 passed in 0.59s`
  - run 2 last line: `25 passed in 0.58s`
  (0 skipped; both runs identical apart from the duration.)
- P2a: `git diff --name-only 15bc4a7b392f152518c9fb8b822bd336ddc108b5 HEAD` → the three owned paths only
  (`tests/verification/__init__.py`, `tests/verification/test_a02_corrections.py`,
  `research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md`).
- P2b: `git diff --diff-filter=M --name-only 15bc4a7b392f152518c9fb8b822bd336ddc108b5 HEAD` → empty.
- P3: `PYTHONDONTWRITEBYTECODE=1 PY -m py_compile tests/verification/test_a02_corrections.py && echo compile-ok`
  → `compile-ok`
- P4: `grep -n "datetime.now\|time\.time\|date.today\|requests\|urllib\|socket\|subprocess\|data/" tests/verification/test_a02_corrections.py`
  → exactly one hit, line 62: the verbatim frozen `UNFINISHED: actual recorded revisions — hermetic
  lane, no data/ reads; …` string inside `PENDING_LEGS` (the lane's own required text naming what this
  suite never does; not a filesystem read). No other pattern occurs.
- P5: `PYTHONDONTWRITEBYTECODE=1 PY scripts/check_contract_delta.py --base 15bc4a7b392f152518c9fb8b822bd336ddc108b5 2>&1 | tail -8`
  → `::error title=contract-delta::finding computation refused on this PR's head: cannot load workflow
  …/.github/ci/legacy-jobs.yml: [Errno 2] No such file or directory` — an infrastructure error of the
  sparse lane worktree (`.github/` is outside this worktree's sparse cone), quoted, never fixed here;
  the suite is not yet wired into CI (the orchestrator applies the `.github/ci/legacy-jobs.yml` patch).
- P6: the six mutations of the table above; kill tally 6/6; the mutation worktree was removed
  afterwards with `git worktree remove --force`.
