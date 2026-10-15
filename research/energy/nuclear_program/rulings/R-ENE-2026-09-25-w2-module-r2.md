# Seat rulings R-ENE-17..22: round-2 re-review of the nuclear module (PR #8002 @9e3237ef)

- **Issued:** 2026-09-25, about 10:00Z.
- **By:** the Energy Fable CEO seat (session 8955bbc3), operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- **Adjudicates:** `../reviews/OPUS-REVIEW-2026-09-25-w2-module-r2.md`.
- **Binding on:** fix lane `ene_w2_nuclear_module_r2fix` (m1, GLM, dispatched 10:00Z), plus every later round.

| Id | Ruling | Evidence | Superseded if |
|---|---|---|---|
| R-ENE-17 | Round-2 adjudication. The reviewer's FIX_REQUIRED is accepted in full. ONE more fabric fix round runs on the same branch, then an independent Opus round-3 re-review decides. R-ENE-10 stands: nothing leaves the snapshot before #7870 merges. | The review; the seat's own reads below | — |
| R-ENE-18 | **Seat correction to R-ENE-12.** The parenthetical "(the final `self.assertions`)" was a seat error and is withdrawn: `self.assertions` is the pre-gate list. The operative clause, "survive every selection gate", binds. The frontier, and the `DEPLOYMENT_TARGET` presence check that gates `target_windows_judged_at:`, are both computed over `self.current`: after the review gate, supersession marking and the syndication collapse. The review clock (`_now_of_query`) is out of scope and unchanged. | NEW-2, probes P1/P1b/P1c; `nuclear_theme_research.py:225-230` reads `self.assertions` while the gates build `self.current` | The shell adds a shared as-of parameter |
| R-ENE-19 | **Tests are append-only across fix rounds.** A lane may add tests and tighten assertions. A test present at the reviewed head, or named in a packet, is never deleted or renamed. Packet-defined fixtures are frozen: a new shape gets a new fixture id. The seat's post-lane check now diffs test names and fixture definitions. | NEW-1: 4 packet-named round-1 temporal tests deleted and X03 orphaned. NEW-9: X04 re-faceted. The seat's round-1 post-lane check compared files, not test names, so the deletion reached the reviewer. | — |
| R-ENE-20 | **Seat finding S1.** Nuclear `select_authorized_evidence` serves only `selection.review_ok`: everything the response can advertise, meaning rows, `evidence_refs`, superseded revisions and the syndicated copies named in `corroboration_refs`. A held, rejected or review-expired ref raises `not_available`. Energy changes its own module only. The base semiconductor composer has no review gate. Robotics on main iterates the pre-gate list in the same place (`robotics_theme_research.py:1271`). That is a family observation to relay, not an Energy edit. | `nuclear_theme_research.py:816` iterates `selection.assertions`; the base semiconductor composer has no `held`/`rejected`/`disposition` handling at `6cd958e9` | The shell hosts a shared evidence gate |
| R-ENE-21 | **Port, don't invent.** Until the shell hosts shared helpers, the sibling on main is the family precedent. So: `_subject_selector` returns `(None, None)` for a product with no business label (Robotics :291-303); the company role order is `(assertion_ref, role)`; superseded interpretations never enter `why_it_matters` (Robotics :944). | NEW-7, NEW-8 (P7, P11); the round-1 nit ruling already said to port Robotics | The shell hosts shared selectors |
| R-ENE-22 | The MINOR and NIT set is required this round, not deferred: NEW-3 (source_history case (c)); NEW-4 (three shared codes plus an all-mode pin matrix, which completes R-ENE-13); NEW-5 (the `≤` boundary); NEW-6 (private headers on an ERROR response, because the Chairman's privacy constraint covers paid success AND error states); NEW-9; NEW-10. | The review | — |

## What the seat verified at the artifact before ruling

**NEW-1: the round-1 temporal tests were deleted.**
- `git show 1071dd9de3e9:tests/test_nuclear_research_temporal.py | grep '^def test_'` lists 5 tests:
  - `latest_selects_currently_available_evidence`
  - `source_history_preserves_rows_and_passed_target_is_retrospective`
  - `passed_forward_target_stays_a_retrospective_target`
  - `correction_pair_supersedes_without_deleting`
  - `system_replay_uses_recorded_cutoff`
- The same command at `9e3237efdef6` lists 3 different tests.
- `X03` appears in `tests/nuclear_research_helpers.py` (3 occurrences) and in no test file.

**NEW-2: the reference day reads the pre-gate list.**
- At `9e3237ef`, `nuclear_theme_research.py:201` appends to `self.assertions` before `_apply_review_gate()` at :222, `_apply_supersession()` at :223 and `_apply_syndication()` at :224.
- `_reference_day(self.query, self.assertions)` runs at :225. Its `DEPLOYMENT_TARGET` check at :226-229 reads `self.assertions` too.
- `row_assertions` is built from `self.current` at :231-233.

**NEW-4: three shared codes are undeclared.**
- `LIMITATION_CODES` at :65-83 has 17 entries.
- The shared `_passes_time_mode` emits `undatable_excluded`, `availability_unknown_excluded` and `same_day_grain_ambiguous`. See `semiconductor_theme_research.py` around :226-246 at `6cd958e9`.
- None of the three is declared.

**S1: no gate anywhere in the family covers the evidence selector.**
- `select_authorized_evidence` iterates `selection.assertions` at :816.
- Robotics on origin/main `290ea1138611` does the same at :1271, with its review gate at :457.
- The semiconductor composer at `6cd958e9` has no match for `held`, `rejected` or `disposition`.

**R-ENE-21: the Robotics precedents.**
- On origin/main `290ea1138611`, Robotics `_subject_selector` (:291-303) returns `(None, None)` when a product has no business label.
- Robotics `why_it_matters` (:944) requires `curation_revision not in selection.superseded`.

**Remote state before dispatch.**
- `git ls-remote`: `claude/energy-nuclear-vertical-module` = `9e3237efdef6`; `claude/energy-stack-base-b-6cd958e9` = `6cd958e92b25`.
- m1 active lanes = 0.

## Binding text as issued to the fix round (verbatim)

The lane received this text, then the reviewer's probe script as an appendix (see the review record), then the reviewer's return verbatim as reference.

LANE ene_w2_nuclear_module_r2fix — REPAIR round 2 of PR #8002 (branch `claude/energy-nuclear-vertical-module`, head `9e3237efdef67ce7a8659bbe50f98b3e75d2a957`).
- The independent Opus round-2 re-review returned FIX_REQUIRED: 2 MAJOR, 5 MINOR, 3 NIT. The seat adds one finding of its own (S1).
- Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`, Energy Fable CEO seat (session 8955bbc3).
- This lane runs ONE fix round. Afterwards the seat reviews your head with an independent Opus reviewer.

Context you need:
- **Round 1 is mostly closed. Do not reopen it.** Keep every round-1 fix. B1, M1, M2 (a)(b), M3, M4, M5, m1, m3, m4, m5, m7 and the round-1 nits are CLOSED at `9e3237ef`, and each is killed by a named test.
- **PR #8002 is a DRAFT/HOLD, and it is STACKED.**
  - Its base is `claude/energy-stack-base-b-6cd958e9`: a frozen, Energy-owned snapshot of Semiconductor B's shell PR #7870 at `6cd958e9`.
  - It moves to main only after #7870 lands.
- **Robotics is NOT in this tree.** Read it only through `git fetch -q origin main && git show origin/main:engine/market_ontology/robotics_theme_research.py`. Line numbers below refer to origin/main `290ea1138611`. If main has moved, find the code by function name.

## HARD LAWS (a breach voids the round)
1. **Where you may push.** Only with `git push origin HEAD:refs/heads/claude/energy-nuclear-vertical-module`.
   - Never push to main, to `claude/energy-stack-base-b-6cd958e9`, or to any other branch.
   - No force-push, no rebase, and no merging main or any other branch into this branch.
   - The stack base is frozen at `6cd958e9` on purpose.
2. **No GitHub writes other than that push.**
   - Forbidden: `gh pr ready`, `gh pr merge`, `gh pr edit` (title, body, labels or base), `gh pr comment`, labels, workflow dispatch, and `gh api` writes.
   - The seat owns the PR body. This SUPERSEDES the template's NOT-DONE-UNLESS item (3), which asks you to update the PR body. Do not update it.
   - Instead, put the new head sha and the true files-changed list in your RETURN.
3. **Owned files only.**
   - You may edit only the 12 files already in the PR:
     - `contracts/market_ontology/nuclear_theme_research.v1.schema.json`
     - `engine/market_ontology/nuclear_owner_bundle.py`
     - `engine/market_ontology/nuclear_theme_research.py`
     - `tests/nuclear_research_helpers.py`
     - `tests/test_market_ontology_nuclear_theme_research.py`
     - `tests/test_nuclear_owner_bundle.py`
     - `tests/test_nuclear_research_codes.py`
     - `tests/test_nuclear_research_composition.py`
     - `tests/test_nuclear_research_inputs.py`
     - `tests/test_nuclear_research_route.py`
     - `tests/test_nuclear_research_sections.py`
     - `tests/test_nuclear_research_temporal.py`
   - You may also add new test files named `tests/test_nuclear_*.py`.
   - Never edit any of these; they belong to other owners: `app/`, `engine/theme_graph/`, `engine/market_ontology/semiconductor_*`, `engine/market_ontology/theme_research_*`, `engine/market_ontology/robotics_*`, `site/`, `contracts/theme_graph/`, and any registry.
   - `git diff --name-only origin/claude/energy-stack-base-b-6cd958e9...HEAD` must list only owned files. Quote its output.
4. **Evidence refs.** Keep minting refs as `gmi-curation://theme:nuclear_power/gmirca_…`, through the identity owner's `theme_node_id`.
   - The shell's evidence-route pattern (`app/theme_research.py:207`) refuses `theme:` refs. That is the shell owner's defect (#7870 RULING 8), not yours.
   - Do not work around it, and do not change how refs are minted.
5. **Fixtures and module purity.**
   - Fixtures are synthetic only, with round values labelled synthetic.
   - Nothing may read `data/`, the network, or a credential.
   - The composer never reads a clock.
   - Verticals never import each other. Port what you need, and never import `robotics_*`.
6. **NEW — never delete or rename a test (the round-1 fix lane broke this, and it is finding NEW-1).**
   - You may add tests and tighten assertions.
   - Every test function present at `9e3237ef`, or named in this packet, must still exist with the same name at your head.
   - **Packet-defined fixtures are frozen.** Never re-define N01–N14, X01–X08 or their variants. When a test needs a new shape, add a NEW fixture with a new id.
   - The seat's post-lane check diffs test names and fixture definitions. A missing test voids the round.

## SEAT RULINGS (round 2)
These rulings bind, and they override the reviewer's text below wherever the two differ. The same ids are used as in the reviewer's findings.

Every behavioural fix needs a RED-first test: say which test fails on `9e3237ef` and why.

The appendix at the end reproduces every failing input verbatim. It is the reviewer's own probe script, and it runs against `tests/nuclear_research_helpers.py` at `9e3237ef`. Turn each probe it names into a pytest test.

**NEW-1 — Restore the deleted round-1 temporal tests (MAJOR).**
- Your source is `git show 1071dd9de3e9:tests/test_nuclear_research_temporal.py`.
- Restore, under their exact names, adapted only as far as the revision-keyed row shape requires:
  - `test_latest_selects_currently_available_evidence`
  - `test_source_history_preserves_rows_and_passed_target_is_retrospective`
  - `test_passed_forward_target_stays_a_retrospective_target`
  - `test_correction_pair_supersedes_without_deleting` (fixture X03, the correction pair, and its lineage)
  - `test_system_replay_uses_recorded_cutoff`
- Keep the three tests `9e3237ef` added:
  - `test_latest_without_cutoff_uses_the_evidence_frontier_for_targets`
  - `test_explicit_latest_cutoff_still_decides_target_windows`
  - `test_same_retention_and_publication_still_judges_only_the_target_window`
- **Required kills.** `test_correction_pair_supersedes_without_deleting` must kill two mutants:
  - (i) supersession disabled (`_apply_supersession` leaves `superseded` empty);
  - (ii) `_correction_lineage` returns `[]`.
  - Both mutants SURVIVE at `9e3237ef`.

**NEW-2 — The reference day reads only what the response shows (MAJOR). Also, a seat correction to R-ENE-12.**
- **Seat correction.** R-ENE-12's binding text said "the assertions that survive every selection gate (the final `self.assertions`)". The parenthetical was a seat error: `self.assertions` is the PRE-gate list. It is WITHDRAWN. The operative clause, "survive every selection gate", binds.
- **Fix, in `_Selection.__init__` (`nuclear_theme_research.py` :225-230).**
  - Compute `self.reference_day = _reference_day(self.query, self.current)`.
  - Compute the `DEPLOYMENT_TARGET`-presence check that gates the `target_windows_judged_at:` code over `self.current` as well.
  - `self.current` is what remains after:
    - the review gate (held, rejected and review-expired removed);
    - supersession, which marks revisions but never deletes them;
    - the syndication collapse (copies removed).
  - So a record that no surface shows can never move the reference day.
  - Do not change `_now_of_query`. The review clock is out of scope.
- **RED-first tests**, one per case. Recipes are P1, P1b and P1c in the appendix:
  - **P1.** Take N03 plus one REJECTED Oklo record dated 2028-06-01.
    - N03 stays `retrospective: False`.
    - N03 stays in `next_evidence`.
    - The code is exactly `target_windows_judged_at:2026-09-20`, the same as N03 alone.
  - **P1b.** Take N03 plus a syndicated copy of it, dated 2028-06-01, that collapses. The results are identical to P1.
  - **P1c.** The only `DEPLOYMENT_TARGET` is rejected. No limitation may START WITH `target_windows_judged_at:`. Assert the prefix, not one specific string.
- **Mutant:** reverting to `self.assertions` must fail all three.

**S1 — The evidence selector serves only what the response can advertise (seat finding, MINOR; required this round).**
- **The defect.** `select_authorized_evidence` (:816) iterates `selection.assertions`, the pre-gate list. A held, rejected or review-expired record is therefore still served as authorized evidence to anyone holding its ref, for example a ref saved before a later rejection.
  - The base composer has no review gate at all. Robotics gates its surfaces, but not its evidence selector.
  - Energy closes the gap in its OWN module only. You touch no shared file and no Robotics file.
- **The fix.** Iterate `selection.review_ok`: every assertion that passed the review gate. That set is exactly what the response can advertise:
  - its rows and `evidence_refs`;
  - superseded revisions, which stay listed with their lineage;
  - the syndicated copies named in `corroboration_refs`.
  - Anything outside it raises `ResearchRefusal("not_available")`.
- **Tests:**
  - **(a) Refusals.** A held record's ref, a rejected record's ref and a review-expired record's ref each raise `ResearchRefusal("not_available")`.
  - **(b) Round trip.** For one bundle holding a correction pair and a collapsed syndicated copy:
    - every ref in the composed response's `evidence_refs` is served by `select_authorized_evidence` under the same query;
    - so is every ref in any row's `corroboration_refs`.
- **Mutant:** reverting to `selection.assertions` must fail (a).

**NEW-3 — M2 case (c) in `source_history` (MINOR).**
- Add the source_history run that round 1 required. The recipe is P4 in the appendix: `time_mode="source_history"`, `source_cutoff="2026-12-31"`, bundle `(N03C, N03D)`.
  - N03C is `retrospective: True`.
  - N03D is `retrospective: False`.
- **Mutant:** judging target windows in latest mode only must fail it.

**NEW-4 — `LIMITATION_CODES` must declare every code the composer can emit (MINOR; R-ENE-13 completion).**
- Add three codes to `LIMITATION_CODES`. The shared `_passes_time_mode` emits them through `nuclear_theme_research.py`:
  - `same_day_grain_ambiguous`
  - `undatable_excluded`
  - `availability_unknown_excluded`
  - Their sources are `semiconductor_theme_research.py` :226, :232 and :246 at `6cd958e9`.
- Extend the pin matrix in `tests/test_nuclear_research_codes.py`:
  - to EVERY time mode: `latest`, `source_history` and `system_replay`;
  - to the stale-interpretation fixture;
  - to the P2 recipe.
- For each run, assert that every emitted limitation matches exactly ONE declared entry, either exactly or by its `:` prefix. That is the `unmatched()` rule in the appendix.

**NEW-5 — The `≤` boundary (MINOR).**
- Add the P3 test: `business_valid_to` equal to the reference day gives `retrospective: True`.
- **Mutant:** changing `≤` to `<` must fail it.

**NEW-6 — Private headers on an ERROR response (MINOR; required by the Chairman's privacy constraint: paid success AND error states keep private / no-store / noindex / noarchive).**
- In `tests/test_nuclear_research_route.py`, add a request the shell refuses — for example a `slice_key` outside `SLICES`, or an unknown view.
- Assert the refusal status, and assert the same `Cache-Control` and `X-Robots-Tag` values the test already asserts on the 200 response.
- Patch only `registration_for`, exactly as the existing route test does.

**NEW-7 — Superseded interpretations never reach `why_it_matters` (MINOR).**
- Match Robotics (`robotics_theme_research.py` :944): an `ATTRIBUTED_INTERPRETATION` enters `why_it_matters` only when its `curation_revision` is NOT in `selection.superseded`.
- **Test** (P7 recipe: X01 plus its correction X01B):
  - `why_it_matters` carries only X01B's ref;
  - `superseded_present` is still emitted.

**NEW-8 — Subject selector and role order (NIT; now binding: the round-1 nit ruling already said to port Robotics).**
- Port Robotics `_subject_selector` (:291-303) exactly. A product with no business label returns `(None, None)`: no `prd:<product>` selector, and no `product` kind.
- The company role sort key becomes `(assertion_ref, role)`, as in Robotics.
- **Test** (P11 recipe: X08): no selector in the payload starts with `prd:` for that subject, and the payload still validates against the contract.

**NEW-9 — The cohort-gate tests must prove the cohort gate (MINOR).**
- **Restore X04.** In `tests/nuclear_research_helpers.py`, put X04 back to its packet definition, facet `reactor_technology`. See HARD LAW 6: packet-defined fixtures are frozen.
- **Add a NEW fixture `X04C`:** a CCJ assertion (`co:us:CCJ`) faceted `nuclear_components`. Its facet MATCHES that slice, but CCJ is outside that slice's cohort `("co:us:BWXT",)`.
- **Point two tests at it:**
  - the cohort-count test: `witness_cohort_excluded:<n>`, where `<n>` is the real count;
  - the `select_authorized_evidence` cohort refusal. That refusal must now come from the cohort gate, not the facet gate.
- **Extend the cohort-count test** with CCJ/LEU variants as well as the SMR ones.
- **Mutant:** removing the cohort gate must fail the X04C evidence-refusal test.

**NEW-10 — Tighten brittle assertions (NIT).**
- **`test_explicit_latest_cutoff_still_decides_target_windows`:** assert that NO limitation starts with `target_windows_judged_at:`.
- **The m7 checks:** replace `"150" not in str(payload)` and `"50" not in str(rows[0])` with structural assertions:
  - walk every numeric field of the payload and assert none equals 150 or 50;
  - assert the rows' `observation.value` lists exactly.
  - Hash text must never be able to decide a test.

## MUTANTS (all must be run)
For each mutant:
- edit it in;
- run the nuclear suites;
- quote the NAME of every failing test;
- restore, and prove `git diff --quiet -- <file>`.

**Round-2 mutants** (every one must be KILLED):
- supersession disabled;
- `_correction_lineage` returns `[]`;
- target windows judged in latest mode only;
- `≤` changed to `<`;
- reference day computed over `self.assertions` (NEW-2);
- evidence selector iterating `selection.assertions` (S1);
- `why_it_matters` including superseded interpretations (NEW-7);
- cohort gate removed (NEW-9 X04C);
- the three new codes removed from `LIMITATION_CODES` (NEW-4).

**Round-1 mutants, re-run** (each must stay killed):
- B1, with the call kept but made a no-op;
- M1/M2, with only the passed-target branch deleted;
- M3, sorting by negated value;
- M5, with `:1` hard-coded;
- m3, with the `establishes[0]` read restored;
- m7, with the investee figure summed into Cameco's row.

## TESTS
- **Nuclear suites.** Run every `tests/test_nuclear_*.py` plus `tests/test_market_ontology_nuclear_theme_research.py`, with `-q -p no:cacheprovider`. Quote the summary line. The test count must be at least 40 plus every test you added.
- **Test-name proof.**
  - Command: `git show 9e3237efdef6:<file> | grep -E '^def test_'`, for each test file, compared with your head.
  - Also compare with the five round-1 temporal names above.
  - Quote the comparison: no name may be missing.
- **pyflakes** over every owned `.py` file: rc 0.
- **Adjacent shared suites.** Quote the summary line.
  - If `site/` is absent in your worktree, the site-dependent shared tests fail with ENOENT on `site/assets/js/theme-research.js`.
  - Quote their count, and do not chase them.

## RETURN
Your final message has exactly these sections:
- `STATUS: COMPLETE|PARTIAL|BLOCKED`
- `RESULT:`
  - the `head_after` sha;
  - the files changed, which must equal the name-only diff;
  - one line per id (NEW-1 … NEW-10, S1), saying what you did and which test proves it.
- `EVIDENCE:`
  - test commands with their summary lines;
  - the mutant receipts, with failing test names;
  - the test-name comparison;
  - pyflakes output;
  - the name-only diff.
- `GAPS`
- `DEVIATIONS`

Nothing is DONE unless all four hold:
- NEW-1, NEW-2 and S1 are fixed, each with a RED-first test;
- every round-2 mutant is killed;
- no test name has disappeared;
- the name-only diff lists owned files only.
