# R-ENE-31..32 — Energy nuclear module, round 7 (interpretation inputs gated by served scope and replay cutoff; lineage pointer pinned)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-28. PR #8002 at `e31e2db3702a68105bd67183af7e14c8fce8dd58` (round 6).
- Triggers, in order:
  - The round-6 closure check (`../reviews/OPUS-REVIEW-2026-09-25-w2-module-r6-closure.md`, same independent Opus reviewer) returned **ACCEPT_WITH_NITS**.
    - It found R-ENE-29 correct and R-ENE-30 SOUND.
    - It raised one MINOR: `known_revisions` crosses the scope and time gate. This revised its own round-5 (6b) "relay-only" agreement.
    - It raised two NITs: the lineage pointer after a served hop is not pinned, and a relay line number was wrong.
  - Five #7870 comments posted after the round-6 relay were read. They are 5832358700 and 5832596394 (RULING 12 and its fix), 5835036878 and 5835079563 (the fleet-blocker retraction and its verification), and 5835307458 (the Robotics owner's class sweep).
  - #7870 moved from `6cd958e92b25` to `a0d7b054ff23`. The move was a merge of main plus six carrier commits. The seat re-proved the module against the new head.

## R-ENE-31 — interpretation inputs are known only through the served scope and the replay cutoff (the round-6 MINOR)

**Finding (reviewer, confirmed by the seat).** At `e31e2db3702a:engine/market_ontology/nuclear_theme_research.py:210-213`, `known_revisions` is built from the raw `bundle.assertions`. That sits upstream of every scope, cohort, rights and time gate. `_inputs_known` uses that set for two jobs:

- **Display.** `interpretation_blocks()` (:319-330) decides whether a block is SHOWN, as `interpretation_stale`, or dropped.
- **Count.** `__init__` decides whether the block counts toward `interpretation_inputs_absent:{n}`.

The result is that a block citing an input this query may not serve is shown as stale when it should be absent. Such inputs are:

- another slice;
- a rights-refused source;
- a company outside the witness cohort;
- a record retained after the replay cutoff.

The count also ignored the replay review cutoff. A `system_replay` answer as of its cutoff therefore changed when a later-recorded block or record existed, which is a look-ahead that breaks replay reproducibility.

**Why this is nuclear-local and not a relay (it supersedes the round-6 "(6b) relay-only" disposition).**

- In Robotics the same set is count-only. The owner's class sweep (5835307458) measured it: `known_revisions` (:400) is read only at :549, to decide a boolean that becomes the count. In the owner's words, "a number, never an identity."
- In nuclear the same set also gates whether a block's TEXT is shown.
- The (6b) reason, "withheld existence is already disclosed by design (`*_present`)", covers only records withheld at review. No `*_present` code announces a record from another slice, a record outside the cohort, or a record recorded after the cutoff.

**Ruling.**
1. `known_revisions` is the revision set of `self.assertions`. That set is taken after the scope, cohort, rights and time gates and BEFORE the review gate, so a block citing a review-withheld input is still shown stale. That behaviour is designed and matches the `*_present` announcements.
2. One helper, `_reviewed_by_cutoff(block)`, gates both the absent count and the served list. It returns True outside `system_replay`. Inside replay it returns True only when `reviewed_at` is at or before `recorded_cutoff`.

**Documented cost.** A block citing an input from another slice is now absent and counted in `interpretation_inputs_absent`, instead of being shown stale. Per-slice block scope belongs to the base once a block source is accepted (R-ENE-09). The base loader still sends `interpretation_blocks=()`, so no served payload changes today.

**Tests (append-only, R-ENE-19).** `tests/test_nuclear_research_interpretation_scope.py` is a new file with 5 tests and 8 cases:
- `test_a_block_citing_an_input_this_query_may_not_know_is_absent_not_stale`, with 4 parameters: `other_slice`, `rights_refused`, `outside_cohort`, `not_yet_recorded`;
- `test_a_replay_answers_the_same_with_or_without_a_later_record`;
- `test_a_replay_never_counts_a_block_reviewed_after_its_cutoff`;
- `test_a_replay_never_shows_a_block_reviewed_after_its_cutoff` (guard);
- `test_a_block_citing_a_review_withheld_input_is_still_shown_stale` (guard; pins the before-review point of item 1).

## R-ENE-32 — the lineage pointer after a served hop comes from the last served record (the round-6 test NIT)

- The reviewer's mutant `my_pointer_from_root` survived round 6 with 80 passed. It takes the pointer revision from the served root instead of from `current`.
- Every round-6 withheld case withheld the served record's immediate predecessor, so the pointer was never exercised after a real hop.
- The behaviour was already correct. The pin is added to `tests/test_nuclear_research_lineage.py` as one appended test, `test_after_a_served_hop_the_pointer_comes_from_the_last_served_record`, covering A → B (accepted) → C (rejected) ⇒ `[ref(B), prefix/C]`. No existing test changes.

## Erratum and corrections marked at source

- **Relay line number.** Energy's relay 5832062081 and `R-ENE-2026-09-25-w2-module-r6.md` §Relays cite the Robotics `by_revision` build "over `bundle.assertions` (:1300)". It is at **:1298-1299** (read at `a1c8968f8e2f`). Every other Robotics citation the reviewer checked is exact. The r6 file is corrected at source in the same commit as this record.
- **(6b).** The r6 relay line "(6b) `known_revisions` … relay-only" is marked at source as superseded by R-ENE-31 for nuclear. For Robotics it stays a relay (count-only, per the owner's sweep). Its corrected reason is carried below.

## Relays adjudicated (no Energy change)

- **RULING 12** (5832358700, 5832596394): Energy's lineage finding was confirmed for Robotics.
  - Robotics fixed it in `652e2e4fee`, a staged, unpushed lane commit (`lane/rob-r12-lineage-scope` on mb) for the Robotics re-land. It is not on #7870 and not on main (`git cat-file` reports the object absent here). The seat records it as the owner's claim.
  - Robotics indexes lineage over `selection.assertions`. For Robotics that set is right, because RBV-18 retains held records as authorized evidence, and the owner states that keying off `review_ok` would be wrong for Robotics.
  - Nuclear indexes over `selection.review_ok`, and for nuclear that is right because R-ENE-20 pins held, rejected and expired records as `not_available`. The two choices are the same principle applied to two opposite pinned contracts; they do not conflict. R-ENE-29 and R-ENE-30 stand.
- **Class sweep** (5835307458): the owner found RULING 12 a singleton in the Robotics composer and carved out `known_revisions` as count-only. The seat accepts that for disclosure.
  - Corrected reason, for the owner's measurement and not a finding about their code: a count built over the raw bundle is still a replay look-ahead. A `system_replay` count as of its cutoff changes when a record retained after the cutoff exists. The round-6 reviewer measured exactly this on nuclear before R-ENE-31.
  - Energy's next #7870 post carries this as one relay line.
- **Fleet-blocker retraction** (5835036878, 5835079563): #7870 is not the fleet blocker; the Robotics revert (#8013) healed ci-pack-4.
  - The kept ordering constraint binds Energy as it binds Robotics. A vertical that imports #7870's modules must not merge ahead of it. #8002 imports `semiconductor_theme_research`, `theme_research_binding`, `semiconductor_owner_bundle` and `theme_graph.curation_assertion`, none of which is on main. So #8002 stays DRAFT/HOLD until #7870 lands; this is a technical constraint, not a preference.

## Re-proof against #7870 at `a0d7b054ff23` (seat, 2026-09-28)

- Of the base modules nuclear imports, only `engine/theme_graph/curation_assertion.py` changed between `6cd958e92b25` and `a0d7b054ff23`: +21/−6, the jsonschema deferral `52b741c5082b`.
- The seat built a tree from `a0d7b054ff23` (engine, tests, contracts, config, app, lib) plus #8002's 14 files at `e31e2db3702a`:
  - `80 passed` over the 10 nuclear test files;
  - route test `2 passed`.
  - These are identical to the counts on the frozen snapshot base.
- The same tree with round 7:
  - `89 passed` over 11 files;
  - route `2 passed`;
  - pyflakes clean.

## Seat verification (sim `r7gate/`)

- **Red check** at `e31e2db3702a` with the new tests and the unfixed engine: `6 failed, 12 passed`.
  - The six failures are the 4 parameters plus the two replay tests.
  - The 12 passes are the two interpretation guards and the 10 lineage cases. The pin passes before and after the fix because the behaviour was already correct; it exists to kill the mutant.
- **Mutant matrix** (`r7gate/mutplug7.py`, `matrix7.sh`), run on the `a0d7b054ff23` + round-7 tree: 50 mutants, 44 killed, 6 EQUIVALENT.
  - The 6 equivalents are the 3 round-6 equivalents (`role_pred`, `r9_reason_review_ok`, `r9_status_review_ok`) plus the reviewer's 3 classified equivalents (`my_continue_past_pointer`, `my_no_seen`, `my_prefix_from_served`).
  - New kills, with failure counts:
    - `r31_raw` (known_revisions back to the raw bundle): 5;
    - `r31_count_ungated`: 1;
    - `r31_select_ungated`: 1;
    - `r31_helper_true`: 2;
    - `r31_accepted_only` (known_revisions over review-passing records only): 4;
    - `my_pointer_from_root`: 1 (it was the round-6 survivor).
- **Lane.** `ene_w2_nuclear_module_r7fix` is a transcription BY SCRIPT on mb. m1's lane volume was still wedged on 2026-09-28.
  - The seat-authored `apply_r7.py` (sha256 `58c7a467fbc60a9b…`) refuses unless its inputs are the `e31e2db3702a` bytes (engine `cd2b4d2d594970e3…`, lineage `5f3a9ec9a24046b8…`).
  - It also refuses to leave anything behind unless all three outputs match the seat tree: engine `95aa6b2a68923ffe…`, lineage `0571bc248a6b56c0…`, new test `17985e086d3e39f2…`.
- **Lane result (2026-09-28 ~07:37Z).** The lane delivered `e31e2db3702a..3c775ea592a683d9265e5c67ce438f4322f72cd6`. The seat's post-lane gate (`r7gate/postlane7.sh`) confirmed all of the following:
  - one commit, carrying the packet's exact subject;
  - exactly the 3 paths, each byte-identical to the seat tree;
  - `89 passed`, both on the frozen snapshot base and on the `a0d7b054ff23` compat tree;
  - route `2 passed`;
  - pyflakes clean;
  - on the compat tree, the matrix survivor set equals the 6 equivalents above exactly;
  - #8002 is still DRAFT, with no labels and a null auto-merge;
  - no nuclear commit reached main.
- Closure goes to the same independent reviewer carrier.
