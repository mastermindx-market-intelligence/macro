# Opus closure check, round 4 — PR #8002 nuclear theme-research module (2026-09-25)

- **Artifact:** PR #8002 at `fa4ebadbb9fe7dcdacf4513fa67f454a41f895fc`.
  - This head is the round-3 fix lane's output: lane `ene_w2_nuclear_module_r3fix` on m1, GLM, one commit `fa4ebadbb9f` "test(energy): pin nuclear cohort, round-trip, stale-code and archival next-evidence (round 3 fixes)".
  - The commit transcribes seat rulings R-ENE-23..26 (`../rulings/R-ENE-2026-09-25-w2-module-r3.md`).
- **Reviewer:** the same Opus `reviewer` as rounds 2–3, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier.
- **Verdict: ACCEPT.** Every round-3 finding that needed a fix is closed, nothing new was found, and `role_pred` stays EQUIVALENT (R-ENE-26).
- **Later history.**
  - #7870 RULING 9 (comment 5830798482) reopened four sites; that became round 5 (`../rulings/R-ENE-2026-09-25-w2-module-r5.md`).
  - RULING 11 (comment 5831714261) then reversed RULING 9 for Robotics. The seat found that nuclear's round-5 edits stand on nuclear's own pins (R-ENE-30, `../rulings/R-ENE-2026-09-25-w2-module-r6.md`).

## Review text (verbatim)

STATUS: PASS

RESULT:
**ACCEPT.** PR #8002 at `fa4ebadbb9fe7dcdacf4513fa67f454a41f895fc` closes every round-3 finding that needed a fix, and I found nothing new.
- The commit adds tests only, and its text is byte-identical to the seat's binding packet (sections B–D; section A is the two X04 literals). There is no engine change.
- Every non-equivalent mutant in my own harness is killed, including the five that survived round 3.
- The role-key revert still survives, and I confirmed it is genuinely equivalent, so R-ENE-26 stands.

**Items 1–9**
1. **Scope: holds.**
   - One commit on top of `c857ec36311a`: `fa4ebadbb9f test(energy): pin nuclear cohort, round-trip, stale-code and archival next-evidence (round 3 fixes)`.
   - The name-only diff is exactly the four permitted files, +98/−2.
   - The only removed lines are the two X04 literals. Composition, codes and temporal equal the c857ec3 file plus the packet block byte for byte; codes also gains `import dataclasses` above `import re`.
2. **R3-1: closed.**

   | Mutant | Result | Failing tests |
   |---|---|---|
   | CCJ promoted into the `reactor_technology` cohort | KILLED (3) | `test_misfaceted_supplemental_assertion_is_dropped_and_counted`, `test_fuel_cycle_companies_are_out_of_cohort_in_both_primary_slices[reactor_technology-intruders0]`, `test_witness_cohort_is_the_packet_cohort` |
   | LEU promoted into `nuclear_components` | KILLED (2) | `…[nuclear_components-intruders1]`, `test_witness_cohort_is_the_packet_cohort` |
   | CCJ exempted from the gate in `reactor_technology` only | KILLED (2) | `test_misfaceted_…`, `…[reactor_technology-intruders0]` |
   | My extra: CCJ exempted everywhere | KILLED (5) | — |
   | My extra: LEU exempted everywhere | KILLED (3) | — |

   I also tried inputs that might sneak a company past the gate: node id `None`, `CO:US:CCJ`, `"co:us:CCJ "` (trailing space), and a slug-keyed theme. All four are excluded and counted.
3. **R3-2: closed.**
   - The new bundle really collapses: `syndicated_collapsed True`, `superseded_present True`, and corroboration equals `[source_ref_for(copy)]`.
   - The mutant that survived round 3 (the selector iterating `selection.current`) is KILLED by `test_collapsed_copy_and_correction_pair_round_trip`.
   - My extra mutant that refuses corroboration refs explicitly is also KILLED by that test.
4. **R3-4: closed.** Compared with `ast`: X04 at the new head equals its 1071dd9 definition (True) and no longer equals c857ec3's (False). X04B and X04C are unchanged from c857ec3.
5. **R3-5: closed.**
   - Deleting `"interpretation_stale"` from `LIMITATION_CODES` in the source is KILLED by `test_stale_interpretation_code_is_declared`.
   - The probe shows the code is emitted, and with it undeclared `unmatched` is `['interpretation_stale']`. So the `unmatched == []` check cannot pass in that state.
6. **R-ENE-25: holds.**
   - Passing `selection.query` into `_is_passed_target` inside `next_evidence` is KILLED by `test_archival_record_of_an_open_target_stays_next_evidence`.
   - I agree with the reading. The shared `_is_retrospective` (`semiconductor_theme_research.py:253-262`) is a provenance label ("recorded later than its publication"), not a window judgment. N03's window runs to `2027-12-31`, after the 2026-12-31 cutoff, so it is still open and belongs in `next_evidence`.
7. **Full matrix: holds.** Baseline is `62 passed`. Every mutant below is KILLED; failure counts are in brackets.
   - Round 2: supersession disabled (3), empty lineage (1), latest-only windows (1), `<` boundary (1), reference day and presence check reverted together (3), reference day only (2), presence check only (1), selector on `selection.assertions` (1), superseded interpretations in `why_it_matters` (1), cohort gate removed (6), three codes removed (1).
   - Round 1: B1 no-op (3), M1/M2 (7), M3 (3), M5 (4), m3 (2), m7 (3).
   - My extras: old product-only selector (1), selector on `selection.current` (1).
   - The role-key revert gives `62 passed`. I could not kill it:
     - Tampering a record so a second one shares its revision is rejected by the shared contract (`curation_revision_mismatch`).
     - A duplicated assertion gives two identical role entries, `('7cf874','subject','REPORTED_FINANCIAL_MEASURE')` twice, so both keys order them the same.
     - R-ENE-26 is right.
8. **R-ENE-19: holds.** In every file, nothing is missing against either 9e3237ef or c857ec3. Counts: composition 17→20→24, codes 2→2→3, temporal 3→13→14; every other file is unchanged.
9. **Suite: holds.**
   - `python3 -m pytest tests/test_*nuclear*.py -q -p no:cacheprovider` → `62 passed, 90 warnings in 6.23s`.
   - Route test with `-v -rs`: both tests `PASSED`, `2 passed, 90 warnings in 2.18s`, no skip.
   - `pyflakes` on the four files: rc 0.

**Round-3 findings**

| Finding | State | Why |
|---|---|---|
| R3-1 (MAJOR, L1 unguarded) | CLOSED | item 2 |
| R3-2 (MINOR, round trip never collapsed) | CLOSED | item 3 |
| R3-3 (NIT, role order untested) | ACCEPTED-AS-RULED (R-ENE-26) | equivalence confirmed in item 7 |
| R3-4 (NIT, X04 text) | CLOSED | item 4 |
| R3-5 (NIT, stale code not pinned) | CLOSED | item 5 |
| R3-6 (NIT, archival target in `next_evidence`) | ACCEPTED-AS-RULED (R-ENE-25) | now pinned by a test (item 6) |
| R3-7 (NIT, lineage names a rejected predecessor) | ACCEPTED-AS-RULED (R-ENE-26) | a family pattern, relayed to the shell owner |
| R3-8 (NIT, platform selector branch omitted) | ACCEPTED-AS-RULED (R-ENE-26) | recorded as a deliberate difference |

EVIDENCE:
- **Checkout.** `git -C $W status --short | wc -l` → `0` before the checkout. After the permitted fetch and detached checkout, `rev-parse HEAD` → `fa4ebadbb9fe7dcdacf4513fa67f454a41f895fc`.
- **Refs.** `ls-remote`: module branch `fa4ebadb…`; base `6cd958e92b259f7221690547e7076f4a0de4ed33`, unchanged.
- **Scope.**
  - `git diff --name-only c857ec36311a fa4ebadbb9fe` → `tests/nuclear_research_helpers.py`, `tests/test_nuclear_research_codes.py`, `tests/test_nuclear_research_composition.py`, `tests/test_nuclear_research_temporal.py`.
  - `--stat`: `4 files changed, 98 insertions(+), 2 deletions(-)`.
  - `diff -U0 | grep '^-[^-]'` shows only the two X04 lines.
- **Packet byte check.** An inline Python script pulled the three python blocks out of the rulings file and compared each head file with (c857ec3 file + two newlines + block): `exact==packet True` for all three.
- **X04.** An inline `ast` compare printed `X04 head==1071dd9: True head==c857ec3: False`, `X04B … head==c857ec3: True`, `X04C … head==c857ec3: True`.
- **Mutants.**
  - My own plugin `$TMPDIR/nucr3/mutplug4r.py`: my round-3 `mutplug3.py` plus source-level mutants `ccj_rt_cohort`, `leu_nc_cohort`, `ccj_any_exempt`, `leu_any_exempt`, `nostale_src`, `next_query` and `sel_corr_refuse`. Each replacement asserts `count == 1`.
  - Runner `$TMPDIR/nucr3/run4.sh` (all 8 nuclear files, `--rootdir $W`). Its FAILED names and summary lines are quoted above.
  - I did not use the seat's `mutplug4.py`.
- **Probes.** `$TMPDIR/nucr3/probe_r4.py`. Outputs quoted: `R3-2 collapsed True superseded True corroboration True`; `R3-5 emitted True unmatched-if-undeclared ['interpretation_stale']`; `tampered same-revision rejected: curation_revision_mismatch…`; and the promotion-input lines.
- **Final state.** `git -C $W status --short | wc -l` → `0`.

GAPS:
- One input shows Cameco's name in `reactor_technology`: an assertion labelled "Cameco" that carries `company_node_id` `co:us:SMR` surfaces there (`rows ['Cameco']`). The cohort gate keys on the node id, as the packet defines, and the shared curation contract does not bind label to node id. This is input integrity for the curation/identity owner, not a promotion of CCJ's node, so I did not raise a finding; the seat may want to relay it.
- I did not re-run the adjacent shared suites, because no engine or shared file changed.
- I did not read the lane's report; nothing here relies on it.

DEVIATIONS:
- `M3.json`/`m3.json` in `$TMPDIR/nucr3/out4` overwrite each other again (macOS paths are case-insensitive). The results above come from the per-run stdout, which is separate for each mutant, not from those JSON files.
- The matrix's first stdout capture was too broad (it caught `Error` lines from pytest temp-dir cleanup). I re-extracted only the FAILED and summary lines from the saved output.
