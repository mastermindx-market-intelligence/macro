# R-ENE-29..30 — Energy nuclear module, round 6 (lineage closure; #7870 RULING 11 checked against nuclear's own pins)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-25 ~12:10Z. PR #8002 at `b3ea8a19ea05f72ea610ca627c68ef1a5452dc3e` (round 5).
- Triggers, in order:
  - The round-5 closure check (independent Opus reviewer, same carrier as rounds 3–4) returned **FIX_REQUIRED** on `b3ea8a19ea05`. E1–E4 were confirmed correct and E2/E3 proven equivalent. The findings were: MAJOR, a multi-hop lineage disclosure; MINOR, a malformed predecessor row that turns evidence selection into a 503; NIT, identity-vintage availability (relay only). Its design verdicts: (6a) R-ENE-29 accepted with amendments; (6b) relay-only, agreed.
  - #7870 comment 5831714261 (RULING 11, Robotics owner, 11:34:53Z) reversed RULING 9 for Robotics. The "review-gate leak" there is RBV-18, a designed retention contract. The owner asked Energy to check its own composer "against its own pins rather than against my reversal".

## R-ENE-30 — RULING 11 against nuclear's own pins

**The two composers pin opposite contracts, and each is coherent with its own selector.**

| Composer | Pin | Asserts |
|---|---|---|
| Robotics | `test_robotics_research_composition.py:408` `test_held_assertion_is_still_selectable_evidence` | the selector RETURNS a held row, disposition attached (RBV-18) |
| Robotics | `test_market_ontology_robotics_theme_research.py:534` | "the held assertion remains authorized evidence" |
| Nuclear | `test_nuclear_research_composition.py:79` `test_review_gate_refuses_held_rejected_and_expired_evidence` | a held, a rejected and a review-expired ref each raise `ResearchRefusal("not_available")` |

- The nuclear pin is R-ENE-20 (round 2, seat finding S1, accepted by the round-2 and round-4 closure checks). Nuclear's authorized evidence is `selection.review_ok`, by pinned design.
- No nuclear pin claims retention.
  - Grep for `RBV|retained evidence|remains? authorized|still selectable|retention` over the nine nuclear test files plus the helpers: 3 hits, all unrelated. Two are the synthetic `retention_ref` source field and one is `test_same_retention_and_publication_still_judges_only_the_target_window`.
  - Positive control: the same grep over the Robotics tests gives 113 hits, including all three pins RULING 11 names.

**R-ENE-27 stands, on nuclear's own grounds.** RULING 9 prompted the look; nuclear's pins justify the edits, independently of RULING 9.
- **E3 and E4** (`authorized_coverage.status` and `selected` over `selection.current`).
  - Before round 5, `selected` counted records the pinned selector refuses, while `input_refs` (already over `current`, R-ENE-11) omitted them.
  - So `selected != len(input_refs)` whenever a withheld record was present. That breaks the base invariant (`semiconductor_theme_research.py:1007-1013`), in nuclear's own terms, with or without RULING 9.
  - Robotics keeps the invariant the other way: both sides are over its pre-gate set.
- **E2** (view reason from `selection.current`). When every record is withheld, nuclear's selector serves nothing, so `no_selected_assertions` is the true reason.
- **E1** (summary block support over `selection.review_ok`). This matches even the Robotics principle RULING 11 quotes from `:974-978`: "summary makes no retention claim, so its status must describe the content beside it."
- Records keep the history. R-ENE-27's trigger line (RULING 9) stays as written. This ruling supplies its standing basis.

**Family divergence, relayed and not acted on.**
- Nuclear `authorized_coverage` counts only records its selector serves. Robotics' counts retained evidence (RBV-18).
- The two now mean different things under one field name. One definition is owed when the shell hosts a shared evidence gate, which is the "until" condition R-ENE-20 already recorded.
- Energy changes neither the base nor Robotics (R-ENE-09).

## R-ENE-29 — the correction lineage walks only records this query may serve

**Defect at `b3ea8a19ea05`.** `select_authorized_evidence` calls `_correction_lineage(assertion, bundle)`, which indexes `bundle.assertions`. That is the RAW owner bundle, upstream of every gate that builds `selection.assertions`. So the walk can:
- name a record the query may not serve;
- read that record's own `correction.predecessor_revision` to name the next one.

It has three strata. Only one depends on nuclear's review contract.

| Stratum | Cases (new test `WITHHELD_PREDECESSOR`) | Why it is a defect |
|---|---|---|
| (a) authorization scope | `other_slice`, `rights_refused`, `outside_cohort`, `not_yet_recorded` (system_replay) | The record is outside `selection.assertions` — outside the authorized set even by RULING 11's own definition ("`self.assertions` *is* the authorized set"). The walk reads it anyway. This is the scope/rights-seam class RULING 11 invited. |
| (b) review | `rejected`, `rejected_chain` | Nuclear's selector refuses these (R-ENE-20), so lineage must not walk through them. (In Robotics, RBV-18 would make them retained evidence. That is not a claim this ruling makes about Robotics.) |
| (c) robustness | malformed row carrying the predecessor's revision | The walk reads a row the selection already rejected as `assertion_invalid`; round-5 probe: the evidence call raises instead of answering (a 503 at the route) |

**The fix (E5; three lines in `engine/market_ontology/nuclear_theme_research.py`).**
- `_correction_lineage` takes `visible: list[dict]` instead of `bundle`.
- It indexes only `visible`.
- The call site passes `selection.review_ok`, the same set the selector serves.
- When a predecessor is not visible, the walk emits the pointer the LAST SERVED record carries. That is the existing `prefix/prior` branch, and the field is already published in that record's own served body (round-5 probe: `A body carries B revision: True`). Then the walk stops. Nothing is ever read out of a withheld record.
- Why `review_ok` and not `current`: a collapsed syndicated copy is served by the selector (R-ENE-11, the `corroboration_refs` round trip), so the walk must be able to pass through it. The new test `test_a_collapsed_copy_is_walked_because_the_selector_serves_it` pins this, and mutant `r29_current` dies on it.
- Unchanged: the cycle guard, an all-accepted chain walked to its root (RBV-17 shape), and the correction pair's `[N04]` lineage.
- **Documented cost: lineage is slice-local.** This was the round-5 reviewer's amendment. An accepted predecessor in another slice is cut to a pointer, because this query may not serve it.
- The alternative was rejected: walking records that are servable under their own facet would keep cross-slice chains, but it duplicates the whole filter pipeline for a completeness gain only.

**Tests (append-only, R-ENE-19).** `tests/test_nuclear_research_lineage.py` is a new file with 4 tests and 9 cases. No existing test or fixture changes.

**Seat verification (sim `r6gate/sim`, 11:5xZ).**
- Red check at `b3ea8a19ea05`, with the new file and the unfixed engine: `7 failed, 2 passed`. The 2 passing tests are the all-accepted and collapsed-copy guards, which are meant to pass both before and after the fix.
- Sim with E5: `80 passed` over the 10 nuclear files (route test executed). Without httpx: `78 passed, 1 skipped`, and the only skip is the route test.
- Mutant matrix (`r6gate/mutplug6.py`, `matrix6.sh`): 39 mutants, 36 killed, 3 EQUIVALENT (`role_pred` per R-ENE-26; `r9_reason_review_ok` and `r9_status_review_ok` per R-ENE-27). The new ones:
  - `r29_raw` (back to `bundle.assertions`): 7 failed;
  - `r29_pre` (`selection.assertions`): 2;
  - `r29_current`: 1;
  - `r29_no_pointer`: 7;
  - `r29_one_hop`: 2.
- pyflakes is clean.
- The round-5 reviewer's own probe equals R-ENE-29 in every row.
- Mechanical application of packet `ene_w2_nuclear_module_r6fix` to a fresh export of `b3ea8a19ea05` gives files byte-identical to the sim: engine sha256 `cd2b4d2d594970e3…`, test `5f3a9ec9a24046b8…` (3838 bytes).

## Relays (no Energy change)
- **The lineage walk in Robotics.** `robotics_theme_research.py:1295-1320` (read at `a1c8968f8e2f`, the pre-revert main copy) has the same mechanism: `by_revision` is built over `bundle.assertions` (:1300).
  - The gate that builds `self.assertions` is at :372-396: validation, canonical theme, facet, the slug-keyed drop, and the time mode. There is no in-composer rights gate.
  - So the reachable Robotics cases are: another slice, a slug-keyed or other-theme record, a record not yet available, and a malformed row.
  - The Robotics lineage pins read were RBV-17: `test_robotics_research_composition.py:358`, `test_market_ontology_robotics_theme_research.py:502` and `test_robotics_research_temporal.py:156`. They cover in-scope chains only. None asserts or forbids a cross-scope walk.
  - This is mechanism only, not probed against Robotics fixtures, and it is for the owner's measurement. It is the scope/rights-seam class RULING 11 said it would take seriously.
- (6b) `known_revisions` and the identity-vintage NIT: relay-only, as the round-5 closure agreed.
- R-ENE-28 (label-to-node binding) is unchanged.
