# Opus closure check, round 5 — PR #8002 nuclear theme-research module (2026-09-25)

- **Artifact:** PR #8002 at `b3ea8a19ea05f72ea610ca627c68ef1a5452dc3e`.
  - This head is the round-5 lane's output: lane `ene_w2_nuclear_module_r5fix` on m1, GLM, one commit "fix(energy): gate nuclear coverage, view reasons and interpretation support on review (RULING 9)".
  - The commit transcribes seat ruling R-ENE-27 (`../rulings/R-ENE-2026-09-25-w2-module-r5.md`).
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier. The brief also asked it to red-team R-ENE-29 before the seat built it.
- **Verdict: FIX_REQUIRED.**
  - E1–E4 are correct and each is pinned. The E2/E3 equivalence is proven.
  - New findings:
    - MAJOR: the correction lineage walks the raw bundle and discloses refs read out of withheld records;
    - MINOR: a malformed predecessor row turns evidence selection into a 503;
    - NIT: identity-vintage availability (relay only).
  - Design verdicts: (6a) R-ENE-29 is accepted with amendments; (6b) is relay-only, agreed.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-25-w2-module-r6.md`.
  - R-ENE-29 fixes the MAJOR and MINOR findings.
  - R-ENE-30 checks #7870 RULING 11, which arrived after this review, against nuclear's own pins.

## Review text (verbatim)

STATUS: FAIL
RESULT:
FIX_REQUIRED for b3ea8a19ea05. The RULING 9 edits (E1–E4) are correct and each is pinned by a test, and R-ENE-27's table holds. The head still can't be accepted because `_correction_lineage` (engine/market_ontology/nuclear_theme_research.py:782-800) walks the raw `bundle.assertions`. That causes two new findings, one MAJOR and one MINOR (below). This is Energy's own code: the base composer takes lineage only from each record's own `lineage_refs` (semiconductor_theme_research.py at 6cd958e9, :1068). So R-ENE-09 (don't patch the base) doesn't cover it, and it isn't only a relay to #7870. R-ENE-29, amended as described in (6a), fixes both.

New findings:
- **MAJOR, lineage multi-hop disclosure (:782-800, called at :835).** The walk goes through records the query may not serve and emits refs it could only have read from a withheld record's body. This is the same existence-leak class that RULING 9 fixes at E1 and E4.
  - Concrete input: chain A (accepted) corrects B, B corrects C, and B and C are both rejected. `select_authorized_evidence(A)` returns lineage `[B, C]`. C's revision is disclosed only inside rejected B.
  - The same happens when B is outside the cohort (`co:us:SMR`), in another slice (`fuel_cycle`), or not yet recorded at the cutoff in `system_replay`. In that last case the query learns "B corrects C" from a record in its future.
  - Probe output, current code vs simulated R-ENE-29:

    | Case | Current | R-ENE-29 |
    |---|---|---|
    | B, C rejected | `['c27f09','c29fdf']` | `['c27f09']` |
    | B in another slice | `['51b262','9c7662']` | `['51b262']` |
    | B refused on rights | `['672137','fe7eae']` | `['672137']` |
    | B outside the cohort | `['1faf2f','8256c3']` | `['1faf2f']` |
    | B not yet recorded (replay) | `['b05fa4','9a9daf']` | `['b05fa4']` |

  - The rights case can't reach production, because the route drops refused families first (app/theme_research.py:391-405). The other four can.
- **MINOR, a malformed predecessor turns the request into a 503 (:797-798).** `source_ref_for(predecessor)` re-validates the record without catching the error. `_Selection` does catch it (:180) and counts the row as invalid.
  - Concrete input: A, C, plus a mapping that carries B's `curation_revision` and a valid source but `observation: None`.
  - The route only removes non-mapping rows and rows with an unattributable source (app/theme_research.py:382-395), so this row reaches the selector. `select_authorized_evidence(A)` then raises `CurationAssertionError: schema_violation: None is not of type 'object'`, and the catch-all at app/theme_research.py:683-685 returns a 503.
  - That breaks the route's own rule at :384-389: one malformed row is withheld, never a 503. It is also a request-wide failure for a record that is itself served.
- **NIT, relay only: identity-vintage refusal (:693).** A rejected record whose label has no `mapping_learned_at` makes a `system_replay` query refuse with `identity_vintage_unsupported`. N04 alone composes. RULING 9 rates this SAFE ("refuses more; conservative"), and I agree there is no content leak. It is an availability effect caused by a withheld record. Relay to #7870; no Energy change.

No findings on the E1–E4 edits themselves.

EVIDENCE:
**Scope and state**
- HEAD is b3ea8a19ea05f72ea610ca627c68ef1a5452dc3e, one commit on fa4ebadbb9fe; the base is still 6cd958e92b25.
- `git diff --stat fa4ebadbb9fe b3ea8a19ea05`: 2 files, +107/-4. The files are engine/market_ontology/nuclear_theme_research.py and tests/test_nuclear_research_review_gate.py.
- A grep of the added lines for clock, network, `open(`, `data/`, env and credential reads found nothing (rc=1). The fixtures are synthetic (`variant` / `nuclear_bundle`).
- pyflakes is clean on both files.
- Suite: `71 passed, 89 warnings`.
- Route test, no skip:
  - `tests/test_nuclear_research_route.py::test_route_filters_refused_rights_families_before_composition PASSED`
  - `tests/test_nuclear_research_route.py::test_error_responses_keep_paid_private_headers PASSED`
  - `2 passed, 89 warnings in 2.81s`

**(1) R-ENE-27 table: confirmed at head.**
- The edits:
  - E1 at :565 reads `selection.review_ok`.
  - E2 at :669 reads `not selection.current`.
  - E3 at :721 reads `not selection.current`.
  - E4 at :768 reads `len(selection.current)`.
- :818 (selector over `review_ok`) and :759/:767 (`evidence_refs` / `input_refs` over `current`) were already closed.
- :693 and :276-280 are SAFE, as tabled.

**(2) Every read of the pre-gate or raw set, with a verdict**

| Line | Read | Verdict |
|---|---|---|
| :171-207 | builds `self.assertions` from `bundle.assertions` | SAFE (this is the filter itself) |
| :211 | `known_revisions` over all `bundle.assertions` | SAFE, relay only (see 6b) |
| :278 | `_now_of_query` over review stamps | SAFE (see note 1) |
| :298-299 | builds `review_ok` | SAFE (this is the gate) |
| :565 E1, :669 E2, :721 E3, :768 E4 | post-gate reads | SAFE |
| :693 | identity-vintage labels | SAFE on content; availability NIT above |
| :785 | `_correction_lineage` over `bundle.assertions` | LEAK (MAJOR) and WRONG (MINOR, 503), both above |

1. `_now_of_query` (:278), probed: a rejected record reviewed 2026-12-01 expires an accepted record due 2026-10-01 (rows go 1 → 0, reasons `rejected_present` and `review_expired_present`). A real reviewer timestamp is valid evidence of the store clock, so this is SAFE by definition and agrees with RULING 9.
2. The rest of the grep hits (:226-271, :304-314, :568, :611, :644, :759, :767, :818) read `current`, `review_ok` or supersession state, and are SAFE.
3. Missed by the seat: only :785. R-ENE-27 didn't table it, and R-ENE-28 treats it as the single-hop R3-7 relay. The multi-hop and 503 behaviour are new.

**(3) Mutants (run5.sh, 71 tests; failing names in $TMPDIR/nucr3/r5.out)**
- `none`: 71 passed.

| Mutant | Result | Failing tests |
|---|---|---|
| E1 reverted | KILLED, 3 | `test_interpretation_citing_a_withheld_record_is_stale` ×3 |
| E1 → current | KILLED, 1 | `test_interpretation_citing_a_served_record_stays_supported[collapsed_copy]` |
| E2 reverted | KILLED, 3 | `test_withheld_records_are_not_counted_as_coverage` ×3 |
| E2 → review_ok | SURVIVED, 71 passed (EQUIVALENT) | none |
| E3 reverted | KILLED, 3 | `test_withheld_records_are_not_counted_as_coverage` ×3 |
| E3 → review_ok | SURVIVED, 71 passed (EQUIVALENT) | none |
| E4 reverted | KILLED, 4 | `withheld` ×3 and `test_selected_counts_exactly_the_served_input_refs` |
| E4 → review_ok | KILLED, 1 | `test_selected_counts_exactly_the_served_input_refs` |
| evidence_refs → assertions | KILLED, 3 | not captured by name |
| coverage refs → pre-gate | KILLED, 5 | not captured by name |
| coverage refs → review_ok | KILLED, 2 | `test_syndicated_copy_collapses_into_its_single_original`, `test_selected_counts…` |

- **E2/E3 equivalence, proved.** `current` is empty exactly when `review_ok` is empty:
  - Supersession sets `current = list(review_ok)` and removes nothing (:303-314).
  - Syndication (:241-271) removes a copy only if a non-copy original with the same publisher and predicate is present in `current`. Non-copies are never removed.
  - So if `review_ok` is non-empty, at least one record survives: either a non-copy, or copies with no original to collapse into.
- **Round-4 mutants, all still killed:**

  | Mutant | Failing tests |
  |---|---|
  | B1_noop | 4 |
  | M1M2 | 7 |
  | M3 | 3 |
  | M5 | 4 |
  | m3 | 2 |
  | m7 | 3 |
  | cohort_off | 6 |
  | codes_off | 1 |
  | latest_only | 1 |
  | lineage_empty | 1 |
  | lt | 1 |
  | refday_pre | 3 |
  | refday_only | 2 |
  | presence_only | 1 |
  | sel_pre | 1 |
  | sel_current | 1 |
  | sel_corr_refuse | 1 |
  | sup_off | 3 |
  | why_sup | 1 |
  | prd_only | 1 |
  | ccj_rt_exempt | 2 |
  | ccj_rt_cohort | 3 |
  | leu_nc_cohort | 2 |
  | ccj_any_exempt | 5 |
  | leu_any_exempt | 3 |
  | nostale_src | 1 |
  | next_query | 1 |

- `role_pred`: 71 passed, still EQUIVALENT.

**(4) The E4 choice is correct.**
- `current` keeps `selected == len(input_refs)`, which is the base's own invariant (semiconductor_theme_research.py ~:1007-1010, where both use one set).
- It is also consistent with R-ENE-11: a collapsed copy is never counted in `input_refs`.
- The `review_ok` alternative is killed by `test_selected_counts_exactly_the_served_input_refs`: N04, collapsed X05 and rejected N05 must give `selected == 1` and `input_refs == [N04]`.

**(5) Every fix is pinned, and each rejected alternative is killed except the two proven equivalences.**
- The "stays supported" cases pass both before and after the fix by design. They exist to kill the E1 → current alternative, and they do (see the table).
- No assertion is vacuous: each withheld case asserts status, `selected`, `input_refs`, per-view reasons and no `evidence_refs`, and each of those is killed by at least one mutant.

**(6a) Design verdict: R-ENE-29 is ACCEPTABLE, with amendments.**
- Emitting B is right. A's served body already carries `correction.predecessor_revision == B` (probe: "A body carries B revision: True"), so the pointer adds nothing new.
- Walking `review_ok` closes every leak case in the table above (each collapses to `[B]`), and it closes the 503, because `review_ok` holds only validated records.
- An all-accepted chain A→B→C still gives `[B, C]`: superseded records stay in `review_ok` (probe row 1: `['a4da21','920d08']` under both).
- Cycles: keep the `seen` guard (:788, :790) and the stop after emitting a pointer. A self-loop terminates on `seen`.
- Cost: an accepted predecessor in another slice is cut short to a pointer. Accept that and document it as slice-local lineage.
- A better alternative was considered and not recommended: walk records that are servable under their own facet. It would keep cross-slice chains, but it duplicates the whole filter pipeline for a completeness gain only.
- Required tests:
  - A→B(rejected)→C gives `[B]`;
  - A→B→C all accepted gives `[B, C]`;
  - a B outside the cohort, in another slice, or not yet recorded in replay each gives `[B]`;
  - a malformed row carrying B's revision gives `[B]` with no raise;
  - `test_correction_pair_supersedes_without_deleting` still gives `[N04]`.

**(6b) Design verdict: I agree with RELAY-ONLY.**
- Probe: a block citing rejected N05 is shown stale. Its `input_refs` keeps `…791fac` (the owner's published provenance), and the reasons are `interpretation_stale` and `rejected_present`. A block citing a nonexistent `gmirca_a…a` is hidden and counted in `interpretation_inputs_absent:1`.
- The difference reveals only that the cited revision exists in the store. The block's author supplied that id, and `rejected_present` already shows that withheld records exist.
- Fixing it needs a family-wide definition of "known", so it belongs with the #7870 owner.

**Status:** `git -C <review worktree> status --short` printed nothing (empty, 0 lines).

GAPS:
- I didn't build a real cycle A↔B. Revisions follow the pattern `^gmirca_[0-9a-f]{32}$` (content-stamped per the correction contract), so a fixed point isn't realistic. I checked termination by reading the code (:788-791) and the self-loop by reasoning, not by running a probe.
- The R-ENE-29 results come from a `$TMPDIR` simulation (`$TMPDIR/nucr3/probe_r5.py`, function `lin29`), not from a seat patch. The real patch still needs the required tests above and an independent closure.
- I didn't run the 503 case end to end through the HTTP route. I inferred the 503 from the route's catch-all at app/theme_research.py:683-685 and its pre-filter at :382-395.

DEVIATIONS:
- None. The only state change was the commissioned fetch and detached checkout of b3ea8a19ea05. Probes and harnesses ran only under `$TMPDIR/nucr3/`. I made no edits, commits, pushes, comments or labels.
