# Opus closure check, round 7 — PR #8002 nuclear theme-research module (2026-09-28)

- **Artifact:** PR #8002 at `3c775ea592a683d9265e5c67ce438f4322f72cd6`.
  - This head is the round-7 lane's output: lane `ene_w2_nuclear_module_r7fix` on mb, a transcription by script, one commit "fix(energy): gate nuclear interpretation inputs by served scope and replay cutoff (R-ENE-31, R-ENE-32)".
  - The commit transcribes seat rulings R-ENE-31 and R-ENE-32 (`../rulings/R-ENE-2026-09-28-w2-module-r7.md`).
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier. The brief also asked it to attack the seat's reading of the five #7870 comments posted after the round-6 relay.
- **Verdict: ACCEPT_WITH_NITS.** R-ENE-31 closes the round-6 MINOR and R-ENE-32 pins the lineage pointer. There is no BLOCKER or MAJOR in the three changed files.
  - New findings:
    - MINOR-1 (records and relay, not #8002's code): Robotics' `known_revisions` is not count-only. The r7 reversal of "(6b) relay-only" rested on that false premise.
    - NIT-1: the reviewer retracts its own round-6 line-number NIT. The original `:1300` was correct, so the `:1298-1299` erratum is wrong.
    - NIT-2: the `_reviewed_by_cutoff` contract is unpinned on four axes (four surviving mutants).
    - NIT-3: two wording points in the r7 ruling (:36 and :39).
    - NIT-4: a pre-existing defect shared with the base. A replay block with `reviewed_at=''` fails the whole request with HTTP 503.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-28-w2-module-r8.md`.
  - MINOR-1 was relayed to #7870 as comment 5866433049 item 4, effects (a) and (b) with R-ENE-31's construction as the reference fix; (c) is left to the owner. The r6 and r7 records are corrected at source.
  - NIT-1: the erratum is withdrawn at source. Relay 5832062081 stands as posted, `:1300` included (5866433049 item 4).
  - NIT-2: R-ENE-33 pins the four axes.
  - NIT-3: corrected at source in the r7 ruling.
  - NIT-4: R-ENE-34 withholds an unreadable review time inside nuclear, and the base defect was relayed as 5866433049 item 5.

## Review text (verbatim)

STATUS: PARTIAL

RESULT:
ACCEPT_WITH_NITS for 3c775ea592a683d9265e5c67ce438f4322f72cd6.
- The code closes R-ENE-31, my round-6 MINOR, and pins R-ENE-32. There is no BLOCKER or MAJOR in the 3 changed files.
- One MINOR is in the seat's records, not in #8002's code. The reversal of "(6b) relay-only" rests on a false premise: Robotics' `known_revisions` is not count-only. It must be corrected before the next #7870 post.
- There are 4 NITs. One of them retracts my own round-6 line-number NIT, which was wrong.

Paths used below:
- W = /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/energy-w2-review-28c2741ee34f22a6 (the review tree)
- R = /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/energy-records-r7-26e7e1f603935c28 (the seat's records tree; its rulings are under research/energy/nuclear_program/rulings/)
- T = /var/folders/sb/h3rq5rvj1b3_r18p6w9swyp80000gn/T/nucr7 (my probes and harness)

**MINOR-1 (records and relay; #8002's code is unaffected)**
- **Where.** R/…/R-ENE-2026-09-28-w2-module-r7.md:
  - :29 says the fix is "nuclear-local and not a relay".
  - :31 says "In Robotics the same set is count-only".
  - :57 says (6b) "stays a relay (count-only…)".
  - :65-66: the seat accepts the carve-out "for disclosure". The corrected reason covers only "a record retained after the cutoff".
  - R-ENE-2026-09-25-w2-module-r6.md:83 carries the same claim.
  - These records are committed as 7f9e69097d0e and pushed on claude/energy-records-w2-r6-r7.
- **Proof, read at a1c8968f8e2f:**
  - `known_revisions` is read once, at :549, inside `_inputs_known`.
  - `_inputs_known` is called at :404, which is the count, and at :530. At :530, `interpretation_blocks()` does `continue`, so the block's text is withheld.
  - The comment at :531-537 and tests/test_robotics_research_temporal.py:302 (`…input_absent_from_the_bundle_is_withheld`) pin that display effect.
  - The owner's line in 5835307458 ("used at exactly one place (:549) to decide a boolean, which becomes the count") is right about the read and wrong about the effect.
- **Concrete inputs.** `python3 $T/robtree/probe_rob.py $T/robtree`, run on a composer whose sha256 7dcdbee913af67d7 equals the git blob. There are three effects:
  - **(a) Replay text depends on a later record.** With a later-recorded record in the bundle, a replay prints `shown=[(True, '[stale interpretation] …')] limits=['interpretation_stale']`. Without that record, the same block prints `shown=[] limits=['interpretation_inputs_absent:1']`.
  - **(b) A replay counts a block reviewed after the cutoff.** Such a block (with an unknown input) gives `limits=['interpretation_inputs_absent:1']`, against `limits=[]` when there is no block at all.
  - **(c) A latest query marks another slice's record stale.** The output is `shown=[(True, '[stale interpretation] …')]`.
  - Controls: an own input prints `(False, …)` with `limits=[]`; a nonexistent input prints `['interpretation_inputs_absent:1']`.
- **Fix.** Add an amendment commit to the records, since they are already pushed. The #7870 relay should carry (a) and (b), with R-ENE-31's construction as the reference fix. Whether (c) is a defect for Robotics is the owner's call.

**NIT-1 (retraction of my round-6 NIT)**
- `git show a1c8968f8e2f:engine/market_ontology/robotics_theme_research.py | sed -n '1293,1302p'` shows:
  - the `def` at :1295;
  - the docstring at :1297-1299;
  - `by_revision = {… bundle.assertions` at :1300, continuing at :1301.
- So the original ":1300" was correct, and the ":1298-1299" erratum that grew from my NIT is wrong. It needs reverting in:
  - the r6 ruling :78 and the r7 ruling :56;
  - R/agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md:39, :103, :512;
  - R/research/energy/nuclear_program/reviews/OPUS-REVIEW-2026-09-25-w2-module-r6-closure.md:11, :56, :202. Line 202's ":1293-1318" is also 2 lines early.
- Handoff :103 plans to post this erratum to #7870. Drop it from that post.

**NIT-2 (tests)**
- The helper contract at r7 :37 is not pinned on 4 axes. Four of my mutants survive with "89 passed", and each one behaves differently from the head on a concrete input (listed under (4)).
- Fix: append cases to W/tests/test_nuclear_research_interpretation_scope.py.
- Also, `never_counts` has no positive control of its own. The suite covers this through the `absent_not_stale` parameters and the `r31_count_ungated` kill.

**NIT-3 (records wording)**
- r7 :36 says the design "matches the `*_present` announcements". That overstates it. A stale block ties its cited input to "withheld": for a held input the probe prints `shown=[('78e5f8', True)]`. `*_present` only counts, and `not_available` answers the same for withheld and unknown refs. The behaviour itself is acceptable and matches semis and Robotics.
- r7 :39 should add that a block whose inputs span slices is now served by no slice. `probe_xslice` shows it absent in both slices, where e31 showed it stale in both.

**NIT-4 (pre-existing; a relay candidate for the base)**
- A replay block with `reviewed_at=''` makes `_le` (semiconductor_theme_research.py:154) raise ValueError. The whole request then fails with HTTP 503, while latest returns 200.
- It is the same at e31, and semis :323-325 and Robotics :538-541 share it.
- It contradicts the route's own comment at app/theme_research.py:384-388, which says to withhold rather than fail with 503.

EVIDENCE:
All runs used `cd $W; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$T:$W`, with pytest flags `-p no:cacheprovider --rootdir`.

**State**
- `git -C $W rev-parse HEAD` gives 3c775ea592a683d9265e5c67ce438f4322f72cd6.
- `gh pr view 8002` gives `{"auto":null,"isDraft":true,"labels":[],"state":"OPEN"}`.
- #7870 is DRAFT at head a0d7b054ff23.

**(1) Closure: confirmed**
- `grep -n` on the engine shows:
  - :177 `enumerate(bundle.assertions)` is the gate loop and the only raw read.
  - :210 builds `known_revisions` over `self.assertions`.
  - :215 is `if self._reviewed_by_cutoff(block) and not self._inputs_known(block)`.
  - :323 is `if not self._reviewed_by_cutoff(block)`.
  - :821 is `for assertion in selection.review_ok`.
  - :838 is `_correction_lineage(assertion, selection.review_ok)`.
- `probe_r7.py`: every unknowable case gives `shown=[]`, and each has `interpretation_inputs_absent:1` in its limits. Extra codes:

  | Case | Extra code |
  |---|---|
  | other_slice | – |
  | rights_refused | `unmapped_rights_source_excluded:1` |
  | outside_cohort | `witness_cohort_excluded:1` |
  | slug_keyed | `scope_slug_keyed:1` |
  | other_theme | – |
  | recorded_after_cutoff (replay) | – |
  | available_after_cutoff (replay) | – |
  | invalid_impostor | `assertion_invalid:1` |
  | nonexistent (latest) | – |
  | nonexistent (replay) | – |

- Positive control: known N04 gives `shown=[('7cf874', False)]` in both latest and replay.
- `reviewed_at` boundary on a known input:
  - '2026-12-31' and '2026-12-31T23:59:59Z' are shown.
  - '2027-01-01', None and 20261231 give `shown=[] limits=[]`, so they are neither shown nor counted.
- `probe_replay.py`:
  - With vs without a later record, the only difference is `/generation`, and the same difference appears with no block at all.
  - A block reviewed after the cutoff, citing 7cf874, cccccc or 9f7618, prints "vs no block: IDENTICAL".

**(2) Before review**
- `probe_review.py`, in both latest and replay:
  - held gives `['held_present','interpretation_stale']`;
  - rejected gives `['interpretation_stale','rejected_present']`;
  - expired gives `['interpretation_stale','review_expired_present']`;
  - all three give `evidence_refs_contains_withheld=False`.
- This is consistent with R-ENE-20 (the selector at :821).
- `reviewed_at` is the block's only review clock, and the helper matches semis :320-328 and Robotics :538-541.

**(3) Documented cost**
- `probe_xslice.py`: both slices give `shown=[] limits=['interpretation_inputs_absent:1']`.
- The owner loader returns `interpretation_blocks=()` (nuclear_owner_bundle.py:34-45), and theme_research_registry.py:172 registers only semis. So "no served payload changes today" is correct.

**(4) Mutants**
- Run with `run7.sh` over 59 mutants: the seat's 50 plus my 9. Output is in `$T/matrix7r_W.out`.
- The seat's 50 reproduce: 44 killed, and the 6 survivors are exactly the equivalents listed at r7 :89.
- The required kills, with failing tests:
  - `r31_raw` (5): `absent_not_stale[not_yet_recorded, other_slice, outside_cohort, rights_refused]` and `test_a_replay_answers_the_same_with_or_without_a_later_record`.
  - `r31_count_ungated` (1): `test_a_replay_never_counts_a_block_reviewed_after_its_cutoff`.
  - `r31_select_ungated` (1): `test_a_replay_never_shows_a_block_reviewed_after_its_cutoff`.
  - `r31_helper_true` (2): the two tests above.
  - `r31_accepted_only` (4): `test_a_block_citing_a_review_withheld_input_is_still_shown_stale` and `test_interpretation_citing_a_withheld_record_is_stale[expired, held, rejected]`.
  - `my_pointer_from_root` (1): `test_after_a_served_hop_the_pointer_comes_from_the_last_served_record`.
- My other mutants were killed: `my_helper_no_mode_crash` 11, `my_kr_after_review` 4, `my_kr_current` 5, `my_count_raw` 5, `my_display_raw` 5, `r4_ccj_any_exempt` 5, `r4_leu_any_exempt` 3, `r4_sel_corr_refuse` 1.
- My 4 survivors, from `probe_survivors.py`. Each one DIFFERS from the head:
  - `my_helper_lt`: a block reviewed on the cutoff day is shown by the head and hidden by the mutant.
  - `my_nonstr_reviewed`: `reviewed_at=None` is hidden by the head and shown by the mutant.
  - `my_helper_source_cutoff`: with source cutoff 06-30, recorded cutoff 12-31 and review 09-20, the head shows and the mutant hides.
  - `my_helper_cutoff_any_mode`: with source_history plus a recorded cutoff and review 2027-01-15, the head shows and the mutant hides.

**(5) Tests**
- Red check at e31 (the `oldeng` plugin, which reports "has _reviewed_by_cutoff: False") gives "6 failed, 12 passed". The failures are the 4 `absent_not_stale` parameters, `replay_answers_the_same` and `never_counts`.
- The plain suite gives "89 passed, 43 warnings in 8.69s".
- The route test, with httpx 0.28.1 and `-rs` (no skips), gives "2 passed, 50 warnings in 6.01s".
- pyflakes returns rc=0.
- `probe_refs.py` prints "lineage: ['2b9806', '28a717'] == [mid, root]: True". That is the pin's chain: the served record, then the accepted middle, then the rejected root. It also prints "6 refs; all match pattern: True".

**(6) Relays** (all five #7870 comments read with GET)
- **RULING 12** (5832358700, 5832596394) is sound. The owner states that Robotics keys lineage off `selection.assertions` because RBV-18 keeps held records as evidence. Robotics' selector does iterate that set (:1271), and nuclear's iterates `review_ok` (:821, :838).
- **Class sweep** (5835307458) is MINOR-1.
- **Fleet-blocker retraction** (5835036878, 5835079563) is consistent with the facts: `gh pr view 8013` shows it MERGED at 2026-09-25T11:01:34Z as e5512ef66a74.
- **Ordering constraint** is verified: the 4 imported modules were absent on main at 1690e69040d2 when I checked.

**(7) Compat**
- `git diff --numstat 6cd958e92b25 a0d7b054ff23` over every module nuclear imports gives only `21 6 engine/theme_graph/curation_assertion.py`. The directory-scoped stat also lists a mining schema file, which nuclear never reads; the only "mining" hit is a registry docstring at :12.
- My own compat tree (a0d7 plus the 15 PR files, in `$T/compat_own`) gives "89 passed, 76 warnings in 22.76s", and the route test gives "2 passed".

**(8) Scope and privacy**
- The diff is 3 files changed, 125 insertions and 8 deletions.
- I swept the added lines for network, clock, environment, `data/`, `site/` and credential patterns. The only hit is the synthetic fixture URL `https://www.nrc.gov/synthetic/interpretation`.

**NIT-4 probe**
- `probe_route503.py`, with `reviewed_at=''`, at both head and e31: system_replay returns HTTP 503 and latest returns HTTP 200.

**Final state**
- `git -C $W status --short | wc -l` gives 0. The output is empty at HEAD 3c775ea592a683d9265e5c67ce438f4322f72cd6.

GAPS:
- I could not get the Robotics fix commits 532c7fb866 and 652e2e4fee: they are not local, and GitHub returned 422 for 532c7fb866. MINOR-1 is proven on a1c8968f8e2f, the version the owner cited.
- Not assessed, because they belong to the base and R-ENE-20: the record-level review gate is not time-scoped in replay, and block `freshness` is read as-is in replay.
- I ran only the nuclear suite and the route test.
- PR states are point-in-time reads.
- Separately, the mastermind-executive MCP server needs authorization, and mmx-cimd-probe failed to connect. Neither affected this review.

DEVIATIONS:
- Every gh call was a read: rate_limit, the 5 comment GETs, `pr view` on 8013, 8002 and 7870, the earlier GraphQL tree read, and the commit GET that returned 422.
- All probes ran under T with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.
- Nothing was written to W, R or SP. The only state change was the commissioned detached checkout.

SESSION END: PROVEN_OUTCOME
