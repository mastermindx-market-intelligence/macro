# R-ENE seat rulings — wave 2, module review round 1 (2026-09-25)

Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`; seat session `8955bbc3-eb16-43cb-b087-bf5cacf2ffcf` (claude8). Authority: Chairman live delegation (DIRECT_TARGETED, 2026-09-24), inside the scope R-ENE-09 leaves Energy — its own vertical module on Semiconductor B's shell, never a rebuild of the base.

This file is the citable index. The section "Binding text" is exactly what the fix round received (lane `ene_w2_nuclear_module_r1fix`). The review it adjudicates is `research/energy/nuclear_program/reviews/OPUS-REVIEW-2026-09-25-w2-module-r1.md`.

| Ruling | Decision | Evidence | Reversibility |
|---|---|---|---|
| R-ENE-10 | Round-1 adjudication of #8002. FIX_REQUIRED is accepted in full, except where R-ENE-13/14 override. One fabric fix round runs on the same branch (lane `ene_w2_nuclear_module_r1fix`, m1, glm-codex glm-5.3, existing-PR mode, seat review). An Opus READ_ONLY re-review at the new exact head decides whether the module is done. Nothing leaves the snapshot branch before #7870 merges. | The review record, at `1071dd9de3e9`; m1 `lane.log`: `[09:06:13Z] start PR #8002 … head=1071dd9d rounds=1` | Standing for this round |
| R-ENE-11 | L2 is a truth law, so the milestone leak is MAJOR (m3 promoted). The summary's `_text_of` returns `limitations.coverage` only and never reads `establishes` or `does_not_establish`. `next_evidence` excludes every passed target. Rows keep echoing both lists verbatim. | Review m3 / probe P5: a `next_evidence` item labelled "target" carried a first-criticality milestone. R-ENE-07 fallback (b) makes the limitations the only milestone channel. | Revisit only if the shell admits a truthful milestone predicate |
| R-ENE-12 | Judging a passed target reads no clock and never depends on the caller. The reference day is `query.source_cutoff`, else the evidence frontier (the latest `retained_at`, falling back to `published_at`, over the final selected assertions). A `DEPLOYMENT_TARGET` / `FORWARD_TARGET` has passed when its `business_valid_to` day is on or before the reference day. When the frontier decides, the response discloses `target_windows_judged_at:<YYYY-MM-DD>`. The shared archival rule stays OR-ed in, and `_is_passed_target` is the single source for rows and summary. | Review M1: `nuclear_theme_research.py:97-105` judged a target only when the caller sent a cutoff. Review M2. | Superseded if the shell adds a shared as-of parameter |
| R-ENE-13 | Seat override of m6. The contract's limitations field stays pattern-only (Robotics parity; the shared client validates by pattern). The emitted codes are pinned instead by a module tuple `LIMITATION_CODES` and two pin tests: every emitted code matches exactly one entry, and every entry fits the wire pattern. | Review m6; shared wire grammar `^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$` | Reversible if the shell adopts per-vertical code enums |
| R-ENE-14 | The loader-import nit is accepted as-is. The owner-bundle loader imports `OwnerBundle` / `ResearchQuery` through its own composer, as Robotics does. | `engine/market_ontology/robotics_owner_bundle.py:156` on main | Reversible any time |
| R-ENE-15 | Evidence refs keep the `theme:`-scoped `canonical_theme_id` segment — the form Robotics mints on main through `theme_node_id` — until the shell owner rules. There is no evidence-route test until then; it is a recorded GAP. Energy edits no shell file. | Review GAP 1: `POST /api/themes/v1/research/evidence` returns 400 `string_pattern_mismatch` against `app/theme_research.py:207` at #7870 @ `6cd958e92b25`. Reported on #7870, comment 5829675838. | Flips to whichever form the shell owner rules |
| R-ENE-16 | Power-Demand (plan Task 11) stays preparation-only until the first vertical is accepted. The read-only scope census (PR #8016) is that preparation. There is no Power-Demand design or build before nuclear ACCEPTANCE. | Plan blob `f7dc93621532b06e2478f90ef3876d6c31236242` §19, lines 491-504: "Task 11 starts only after first vertical accepted." | Lifts on nuclear ACCEPTANCE |

## Binding text as issued to the fix round

In the lane packet, "below" pointed at the reviewer's findings; those now live in the review record named above.

The same ids are used as in the reviewer's findings. Every behavioural fix needs a RED-first test: say which test fails on `1071dd9de3e9` and why.

**B1 — Syndication collapse (BLOCKER).**
- **Port.** Add `_Selection._apply_syndication()` to `nuclear_theme_research.py`, a faithful port of Robotics `_apply_syndication` (origin/main `robotics_theme_research.py` :480-515).
  - Call it at the same point Robotics does: `:428`. Read `:415-435` for its order relative to `_apply_review_gate()`, `_apply_supersession()`, `row_assertions` and `live`.
- **Rules**, identical to Robotics:
  - A copy is an assertion whose `limitations.source_dependence` starts with `syndicated_copy_of:`.
  - A copy collapses into its original only when exactly ONE selected assertion matches. That original must:
    - have `source.publisher` equal to the named upstream;
    - not be a copy itself;
    - have the same predicate.
  - With 0 or 2+ matching originals, the copy stays as its own row. Never guess.
  - A collapsed copy is removed from `current`. It is never a row in any view and never appears in any view's `input_refs`.
- **Row fields.**
  - The row builder reads `selection.corroboration.get(revision, [])`, as Robotics does at `:620`/`:664`.
  - The original's row carries `corroboration_refs` = sorted `source_ref_for(copy)` for each collapsed copy.
  - `independent_source_count` stays 1 on every surviving row (Robotics parity).
  - Emit limitation `syndicated_collapsed` once when any collapse happened.
- **Docstring.** "Ported from robotics_theme_research.py @ origin/main 6c9465c7ed7d; moves to a shared import when the shell hosts one."
- **Contract.** The contract text at `:483` and `:1293` becomes true. Leave it unchanged.
- **Tests:**
  - (i) N04 plus a copy: publisher "Synthetic Wire", `source_dependence="syndicated_copy_of:Synthetic Energy Filings"`, same predicate. Expect:
    - exactly one economics row, N04's revision;
    - `corroboration_refs == [source_ref_for(copy)]` and `independent_source_count == 1`;
    - `syndicated_collapsed` present;
    - the copy's revision in no row and no `input_refs` of any view.
  - (ii) Ambiguous: two originals from "Synthetic Energy Filings" with the same predicate, plus one copy. Expect no collapse, all three rows present, and no `syndicated_collapsed`.
  - (iii) A copy that names a publisher absent from the selection stays as its own row.
- **Mutant:** delete the `_apply_syndication()` call. Test (i) must fail.

**M1 — L5: judging whether a target has passed must not depend on the caller sending a cutoff (MAJOR).**
- **Reference instant.**
  - Use `query.source_cutoff` when it is a string.
  - Otherwise use the EVIDENCE FRONTIER. Compute it over the assertions that survive every selection gate (the final `self.assertions`): take each assertion's `source.retained_at`, or `source.published_at` where `retained_at` is absent, and use the latest day among them.
  - The computation is pure: it reads no clock.
  - If no assertion is selected, there is nothing to judge and no code is emitted.
- **When a target counts as passed.** A `DEPLOYMENT_TARGET` with statement_mode `FORWARD_TARGET` has passed when the day of `temporal.business_valid_to` is on or before (≤) the reference day. Its row gets `retrospective: true`.
  - Keep the shared archival rule (`_is_retrospective`) exactly as it is, OR-ed in as today (Robotics parity). Do not change shared semantics.
  - Keep ONE function (`_is_passed_target`) as the single source of truth. The row flag and the summary (m3) both use it.
- **Disclosure code.** When the frontier, not a caller cutoff, decided the question and at least one `DEPLOYMENT_TARGET` assertion is selected, emit ONE limitation `target_windows_judged_at:<YYYY-MM-DD>` (the frontier's day). It matches the shared wire grammar `^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$`.

**M2 — The temporal test must key rows by revision, never by value (MAJOR).**
- Rewrite the assertions in `tests/test_nuclear_research_temporal.py` to key rows by `curation_revision`. Required cases:
  - (a) LATEST mode with NO `source_cutoff`, which is the route default. N03B → `retrospective` True. N03 → False. `target_windows_judged_at:<frontier day>` is present.
  - (b) Latest mode WITH a `source_cutoff`: the existing behaviour holds.
  - (c) `source_history`: add a fixture variant whose `retained_at == published_at`, so the archival rule is off and only the window decides. N03B-variant → True. N03-variant → False.
- **Mutant:** `_is_passed_target = _is_retrospective`, which deletes the passed-target branch. It must fail case (a) or case (c). Quote the test name.

**M3 — The row-order test must be able to see a sort by size (MAJOR).**
- Delete the unused `_ROW_ORDER` (`:64`). The shared `_row_sort_key` is the order; L8 says "the shared row sort key".
- Add a fixture pair where the shared-key order is the REVERSE of largest-first (the smaller value sorts first by key). Assert the exact revision order.
- Also assert that reversing the bundle's assertion order leaves the output order unchanged.
- **Mutant:** make the sort key the negated observation value. It must fail the named test.

**M4 — Prove L7 on the production path, and check evidence (MAJOR).**
- **Route-level test.** Use the FastAPI TestClient over `app/theme_research.py`'s router. Build the client the way the shell's own route tests do (`git grep -l TestClient -- tests`).
  - Replace ONLY `registration_for`, via monkeypatch. It returns a nuclear `VerticalRegistration` whose `load_bundle` supplies the synthetic bundle N04 + X02. Build that registration the way the existing registration-reconcile test builds it.
  - Assert:
    - status 200;
    - `Cache-Control` contains `private` and `no-store`;
    - `X-Robots-Tag` contains `noindex` and `noarchive`;
    - limitations include `rights_refused_families_hidden`;
    - X02's revision string appears NOWHERE in the serialized JSON;
    - N04's revision is present.
- **Composer defence-in-depth.** Rename `test_unmapped_rights_source_is_excluded_from_rows_and_evidence` to name what it proves: the composer's defence-in-depth branch. Make it ALSO assert that `select_authorized_evidence` (nuclear `:632`) never returns X02 for an unfiltered bundle that contains it.
- **Not an evidence-route test.** Do not add one while the owner's pattern gap stands. Record it under GAPS.

**M5 — Real drop counts (MAJOR).**
- Count cohort exclusions and unmapped-rights exclusions in the selection loop. After the loop, emit `witness_cohort_excluded:<n>` and `unmapped_rights_source_excluded:<n>` once each, with the true n, and only when n > 0.
- Tests:
  - two CCJ assertions faceted `reactor_technology` → `witness_cohort_excluded:2`;
  - two nrc.gov assertions → `unmapped_rights_source_excluded:2`.
- **Mutant:** restore the hard-coded `:1`. It must fail.

**m1 — Rewording.** At schema lines 378, 943, 966, 1094 and 1098, reword "Robotics" to Nuclear. Change descriptions only; nothing structural. The structural-parity test must stay green.

**m2 — L1 tests.**
- (a) The cohort-gate test must actually reach the cohort gate. Use CCJ/LEU assertions faceted `reactor_technology` and `nuclear_components`, which pass the facet gate. Assert that they are:
  - excluded and counted;
  - absent from rows, `select_authorized_evidence`, companies and native_subjects.
- (b) `fuel_cycle`: `supplemental_basket_witnesses` is present, and CCJ/LEU rows appear only there. Check both rows AND evidence.
- (c) Delete the vacuous check `"nuclear_power membership" not in str(payload)`. Do not replace it. The shared company row cannot carry the cohort relation, so L1 rests on the limitation code, the slice label and (a)/(b). Say so under GAPS.

**m3 — PROMOTED TO MAJOR (L2 is a truth law).**
- In nuclear v1, `limitations.establishes` and `limitations.does_not_establish` ARE the milestone channel (seat ruling R-ENE-07, fallback (b)). A summary item that quotes them moves the milestone outside the limitations of the assertion it qualifies. The reviewer's P5 shows next_evidence reading "a separate test reactor reached first criticality (technical milestone)", labelled "target".
- **Ruling:**
  - Nuclear `_text_of` returns `limitations.coverage` verbatim when it is a non-empty string, otherwise "". It never reads `establishes` or `does_not_establish`.
  - `next_evidence` EXCLUDES every assertion that `_is_passed_target` judges passed.
  - Rows keep echoing both lists verbatim, as `:348` does today.
  - Update the contract's summary-text description to match. Change the description only.
- **Tests:**
  - No summary item text equals any string from any selected assertion's `establishes` or `does_not_establish`.
  - In latest mode with no cutoff, N03B is absent from `next_evidence` and N03 is present.
  - The N03 row still echoes both lists verbatim.
- **Mutant:** restore the `establishes[0]` read. It must fail.

**m4 — Native subjects.**
- `source_label` never carries a kind prefix: `biz:BWX Technologies` → `BWX Technologies`; for a product, the product label.
- Port the selector kinds from Robotics `_native_subjects` (`:860-893`), including `app:` (application) selectors. Do this only for kinds the nuclear contract's native_subjects enum admits.
- Test both behaviours.

**m5 — Port the Robotics section behaviour the packet asked you to mirror.**
- From `_summary` (`:902-998`): items built from `selection.interpretation_blocks()` (port `interpretation_blocks()` and `_inputs_known` from `:527-552`), `stale` marking, `status: degraded` with `reason: interpretation_stale`, and a `reason` when nothing is current. Where Robotics calls `_text_of`, nuclear uses its coverage-only `_text_of` (the m3 ruling wins).
- From `_companies` (`:809-858`): `degraded` / `identity_incomplete`.
- `_ownership_role` (`:791-807`), byte-faithful. It reads neither `establishes` nor labels.
- One test per ported behaviour:
  - a stale block → the item carries `stale: true` and the summary reads `degraded` / `interpretation_stale`;
  - no current assertion → a `reason` is present;
  - an unresolved company identity → companies are `degraded` / `identity_incomplete`;
  - OWNERSHIP_EVENT with REPORTED_FACT and a valid_from → `owner_from:<date>`;
  - ANNOUNCED_ARRANGEMENT → `announced_party`.

**m6 — SEAT OVERRIDE of its own packet.**
- Keep the contract's limitations field pattern-only (Robotics parity; the shared client validates by pattern). Do not add an enum.
- Instead, add a module-level tuple `LIMITATION_CODES` to `nuclear_theme_research.py`. It lists every code the composer can emit: bare names, plus `name:` prefixes for parameterised codes. That includes:
  - `slice_scope_unowned`, `milestone_predicate_unavailable`, `supplemental_basket_witnesses`, `syndicated_collapsed`;
  - `target_windows_judged_at:`, `witness_cohort_excluded:`, `unmapped_rights_source_excluded:`, `assertion_invalid:`, `scope_slug_keyed:`, `interpretation_inputs_absent:`, `omitted:`;
  - any other code the composer can actually emit.
- Test 1: run the fixture matrix (every slice × every time mode, plus the syndication, drop and stale fixtures) and assert that every emitted limitation matches exactly one declared entry.
- Test 2: assert that every declared entry fits the contract's limitations pattern.
- List the nuclear-specific codes in the limitations description. Change the description only.

**m7 — L4 test with real figures.**
- Add two synthetic `fuel_cycle` fixtures, subject co:us:CCJ:
  - a Cameco consolidated `REPORTED_FINANCIAL_MEASURE`, 100 USD million;
  - Cameco's equity-method share of Westinghouse, 50 USD million, with establishes/does_not_establish that say equity-accounted and not consolidated.
- Assert:
  - both rows are echoed separately with 100 and 50 exactly;
  - no row, total or summary value equals 150, or 100 minus 50;
  - totals stay `{"value": None, "reason": "totals_not_computed"}`;
  - both limitations lists are echoed verbatim.
- Point `test_equity_method_investee_never_consolidated` at these fixtures.
- **Mutant:** add the investee figure into Cameco's row. It must fail.

**nit — Owner-bundle test name.** Rename `test_bundle_declares_exactly_three_absent_surfaces` to `test_bundle_declares_exactly_two_omissions`. Assert the exact tuple `(PRIVATE_ASSERTIONS_UNBOUND, "public_assertions_uncurated")`; the packet specifies two.

**nit — Loader imports: ACCEPTED AS-IS. Change nothing.** Robotics' loader imports `OwnerBundle`/`ResearchQuery` through its own composer (`robotics_owner_bundle.py:156-159` on main), so this is parity. The seat withdraws the packet's "imported by the other" clause for the cohort: the loader has no use for it, and an unused import fails pyflakes. The cohort stays declared once, in the composer.

**nit — Subject selector with no business label.** Port Robotics `_subject_selector` and its `_biz_selector` / `_prd_selector` (`:275-305`) semantics. A missing or empty business label must never produce `prd:None/…`. Test: a product label with no business label → the string `prd:None` appears nowhere in the payload.
