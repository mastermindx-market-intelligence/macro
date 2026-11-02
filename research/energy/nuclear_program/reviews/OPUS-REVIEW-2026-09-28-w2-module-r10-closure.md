# Opus closure check, round 10 — PR #8002 nuclear theme-research module (2026-09-28)

- **Artifacts:** three, each with its own verdict.
  - PR #8002 at `3a7e6582feb173f0dd88ff21291c8869907d3774`, round 10's output. Lane `ene_w2_nuclear_module_r10fix` on mb, a transcription by script, one commit "test(energy): rescope the review-guard docstring and pin the review-clock boundaries (R-ENE-37, R-ENE-38, R-ENE-39)" transcribing the seat rulings in `../rulings/R-ENE-2026-09-28-w2-module-r10.md`.
  - The seat's #7870 comment 5869344590 (the corrected relay, the parser note and the `object.subject_role` constraint).
  - The seat's R-ENE-40 candidate (seat scratch `r11gate/edits_r11.py` at review time): a positive control and a raise pin on nuclear's review-expiry clock.
    - After the review the seat saved the candidate as `r11gate/edits_r11_candidate.py` and rewrote `r11gate/edits_r11.py` to the delivered text. Where the verbatim text below names `edits_r11.py`, it means the candidate.
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier.
- **Verdicts:**
  1. **Round 10 @3a7e6582: ACCEPT, no findings.** R-ENE-37's docstring is true, each R-ENE-38 gap mutant dies on its intended case, and R-ENE-39's `20261231` is the only case that keeps `m34_broad` and `my8_swallow_cutoff` observable under the `fromisoformat` bases.
  2. **Post 5869344590: FIX_REQUIRED.**
     - One MEDIUM: a third nuclear reader, the target-window judgement, reads `source_cutoff` in every mode.
     - Two NITs: the two parsers' accepted sets do not nest; the expiry gate reads only the selection, and in a replay the base time gate reads first.
     - Three observations: nuclear's response schema `$defs/when` is itself out of step with `_parse_day`; the third reader also leaves a 503 in `latest`; "nuclear's pins pass under any choice" fails for refusal shapes.
  3. **R-ENE-40: DELIVER_WITH_CHANGES.** The candidate's every-mode docstring and its latest/source_history clock test pin a clock R-ENE-18 left unruled, and they add failures under refusal-shaped item-7 fixes. The reviewer's final text pins the replay clock at the recorded cutoff. Outside a replay it pins only the malformed-cutoff failure, with a control of its own.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-28-w2-module-r11.md`.
  - The final text is adopted in full as round 11.
  - The post is corrected on #7870 in addendum 5870740225.
  - Every records copy of the corrected claims is annotated at source.
  - OBS 1 becomes an Energy-side open item for the rebase.
- **Seat verification of this review:**
  - The seat reproduced the final text: 128 passed on both trees under Python 3.12.13 and 3.14.7, pyflakes clean, and the documented 9 seat-matrix survivors.
  - The reviewer's 26 mutants give the same counts under three of its nine base shapes: none, refuse_unread and every.
  - The seat re-measured the replay raise site (`r11gate/probe_replay.py`).
  - The seat's first probe had used a record observed after the source cutoff, which the time gate drops before it reads the recorded cutoff. That is why it showed no raise.

## Review text (verbatim)

## STATUS
DONE. All three artifacts have a verdict and R-ENE-40 has a delivery ruling. Everything was measured in scratch copies under /private/tmp/r10rev_8955bbc3/. I wrote nothing outside that directory.

## RESULT

**1. #8002 round 10 @3a7e6582 (tests/test_nuclear_research_interpretation_scope.py, +22/-8): ACCEPT, no findings.**
- **R-ENE-37 docstring:** true. It limits itself to readable review times, which matches the recorded survivor n9_cutoff_parse_outside_try.
- **R-ENE-38 (NIT-2):** each of the four intended mutants dies on its intended case, all in tests/test_nuclear_research_interpretation_scope.py:
  - n9_lt_instants dies on `a_replay_compares_an_instant_review_time_with_an_instant_cutoff[2026-12-31T12:00:00Z-expected2]`.
  - n9_skip_instant_pairs dies on the same test's `[2026-12-31T23:00:00Z-expected1]` and `[…08:00:00-05:00…]` cases.
  - n9_eod_synthesis dies on `a_replay_reads_a_date_review_time_against_an_instant_cutoff_by_day[2026-12-31-expected0]`.
  - n9_parse_clock_guard dies on `a_replay_withholds_a_block_without_a_readable_review_time[20260920]`.
- **R-ENE-39 (NIT-5(1)):** `[20261231]` is the only case that still kills m34_broad and my8_swallow_cutoff under the fromisoformat-based bases (iso, sh_iso, every_iso). Under the `_parse_day` bases both mutants are equivalent.
- **Recorded equivalents:** n9_utc_day, n9_mode_whitelist and n9_cutoff_parse_outside_try still have 0 kills, so no equivalent mutant is being killed.
- **Suite:** 117 passed with no base fix and under all 6 validation shapes, on both trees (tA10 and tB10).

**2. Post 5869344590: FIX_REQUIRED.** I checked each sentence against the saved body; the post is unedited.
- **MEDIUM, L26 and L34-37.** "Missed two readers" and "a silent 200 otherwise" are false because there is a third nuclear reader.
  - `_reference_day` (nuclear :118) feeds `_is_passed_target` (:133, compare at :142), which is called from `_row` :409 and from :602. It reads `source_cutoff` in every mode.
  - Probe Q3, on 3.12.13: `latest`, `reactor_technology`/`commercial`, N03 in the slice, `source_cutoff="not-a-date"`. The engine raises ValueError (frames :409 → :142 → semis `_parse_day`) and the route returns 503. With `2026-12-31` it returns 200.
  - This reader is deliberate. It is pinned by `test_explicit_latest_cutoff_still_decides_target_windows` (tests/test_nuclear_research_temporal.py:45).
- **NIT, L16.** "`_parse_clock` accepts more than `_le` does" is wrong: neither set contains the other.
  - `_parse_clock` accepts `20261231` and `2026-W53-4`, which `_le` refuses.
  - `_le` and `_parse_day` accept `2026-1-5` and full-width digits, which `_parse_clock` refuses.
- **NIT, L28/L36.** The expiry gate only looks at the selected assertions, not "every assertion". In a replay, the base time gate (semis a0d7b054ff23:236, the `retained_at` comparison) reads a malformed `recorded_cutoff` first (probe Q4 frames), so the 503 in a replay comes from the time gate.
- **OBS 1 (response schema).** Passing `_parse_day` does not guarantee the echoed value is schema-valid. Nuclear's `$defs/when` refuses `2026-1-5`, `…T12:00Z`, `+0800` and full-width digits, and admits `2026-13-45` and `2026-02-29` (probe Q5). The silent 200 already echoes schema-invalid values: probe P4 shows errors at `request.recorded_cutoff` for `not-a-date` and `20261231`.
- **OBS 2.** The L40 consequence also applies to the third reader: a validator that skips `latest` leaves its 503 in `latest`.
- **OBS 3.** "Nuclear's pins pass under any choice" holds for all 6 validation shapes. It fails for refusal shapes: 6, 2 and 4 existing tests go red under refuse_unread, refuse_latest and refuse_rec_unread (list in EVIDENCE).

**Suggested addendum (for the seat to post; I posted nothing):**
> Addendum to `5869344590`. The table rows stand; four sentences go further than the probes.
> - **A third nuclear reader.** Nuclear's target-window judgement reads `source_cutoff` in every mode (`_reference_day` → `_is_passed_target`, via `_row`). In `latest`, a malformed `source_cutoff` with a target-bearing record in the slice raises the same bare `ValueError`, and the route answers 503. `test_explicit_latest_cutoff_still_decides_target_windows` pins this reader. "Missed two readers" should read "missed three, all in nuclear". The corrected sentence gains a line: 503 when the target-window judgement reads a malformed `source_cutoff`, in any mode. A validator that skips `latest` leaves this 503 in `latest` as well.
> - **The expiry gate reads the selection.** It compares the recorded cutoff with the `review_due_at` of selected assertions only. In a replay, the base time gate reads a malformed `recorded_cutoff` first, so a replay's 503 comes from the time gate.
> - **Parsers.** `_parse_clock` and `_le` accept different sets, not a superset. `20261231` and `2026-W53-4` pass only `_parse_clock`; `2026-1-5` and full-width digits pass only `_le`.
> - **No ask.** Nuclear's response schema `$defs/when` both refuses some cutoffs `_parse_day` admits and admits some it refuses, and today's silent 200 already echoes schema-invalid values. "Nuclear's pins pass under any choice" holds for validating; if item 7 instead refuses cutoffs the base never reads, 2–6 existing nuclear tests fail, depending on which cutoffs it refuses.

**3. R-ENE-40: DELIVER_WITH_CHANGES.**

Findings against the candidate (/private/tmp/claude-501/-Users-chriswong-Documents-Cluade-macro-main/8955bbc3-eb16-43cb-b087-bf5cacf2ffcf/scratchpad/r11gate/edits_r11.py):
- **MEDIUM:** the docstring says "In every mode, a supplied recorded cutoff is the now". That writes down a clock R-ENE-18 put out of scope, and it claims more than the tests pin. Replay is unpinned (e_now_not_replay: 0 kills), and so are e_now_advance_only and e_now_source_cutoff.
- **MEDIUM (yes, (a) entrenches the accident):** test (a) pins the unruled latest/source_history clock.
  - It kills e_now_replay_only (clock read only in replay) even under BASEFIX=every: A[2026-12-31T00:00:00Z-True-latest] and A[…-source_history]. So the natural fix for the P3 rewind hazard would break the pin even when nothing is swallowed.
  - It adds new failures under refusal-shaped item-7 fixes: +4 (refuse_unread), +2 (refuse_latest), +4 (refuse_rec_unread). The head suite already fails 6, 2 and 4 there, so (a) is not the first pin to break.
- **LOW, missed mutants (0 candidate kills):** e_now_not_replay, e_now_source_cutoff, e_now_advance_only, e_now_date_only, e_due_trunc, e_now_trunc.
- **LOW:** (b) has no control of its own; it relies on (a)'s cases. It builds its fixture inside `pytest.raises`. The trap is measured at /private/tmp/r10rev_8955bbc3/trap/test_trap.py: with a date-only due, the seat form passes vacuously under e_swallow_serve (2 passed), because CurationAssertionError is a ValueError; the variant form fails at its control.

Your specific questions:
- **One-mode swallows:** latest and source_history are killed 3 each by B in both versions. The replay one is EQUIVALENT: every admitted replay assertion passes semis :236 before the gate.
- **`_now_of_query` falling back to max(reviewed_at) on a malformed cutoff** (e_now_fallback_malformed): B kills all 6 cases in both versions.
- **Every plausible item-7 shape:** final text has 0 new failures across all 9 shapes.

**Exact text to deliver** (applier /private/tmp/r10rev_8955bbc3/variant_r11d.py; same anchor as edits_r11.py):
```
@@ -1,7 +1,13 @@ tests/test_nuclear_research_review_gate.py
 A held, rejected or review-expired record never counts as coverage, never
-changes a view's reason and never supports an interpretation block.
+changes a view's reason and never supports an interpretation block. A replay
+judges review expiry at its recorded cutoff, never at its source cutoff or
+the newest review time. Outside a replay the gate also reads a supplied
+recorded cutoff, because `_now_of_query` checks no mode; which clock applies
+there is out of scope (R-ENE-18), so only the failure is pinned: a malformed
+recorded cutoff supplied beside a record with a review due time raises
+instead of serving or withholding that record (R-ENE-40).
 """
@@ append at end of file @@
+EARLY = {"published_at": "2026-01-15", "observed_at": "2026-01-15T00:00:00Z",
+         "retained_at": "2026-01-15T00:00:00Z"}
+
+
+def replay_expired(recorded_cutoff, due):
+    dated = variant("N04", "R11DUE", source=EARLY, review={
+        **review("accepted", due), "reviewed_at": "2026-05-01T00:00:00Z"})
+    later = variant("N04", "R11LATER", source=EARLY, review=review("accepted"))
+    query = nuclear_query("nuclear_components", "economics", time_mode="system_replay",
+                          source_cutoff="2026-06-30T00:00:00Z", recorded_cutoff=recorded_cutoff)
+    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(dated, later))
+    return "review_expired_present" in payload["limitations"]
+
+
+@pytest.mark.parametrize(("recorded_cutoff", "due", "expired"), [
+    ("2026-12-31", "2026-12-31T23:00:00Z", True),
+    ("2026-12-31", "2027-01-01T00:00:00Z", False),
+    ("2026-12-31T12:00:00Z", "2026-12-31T12:00:00Z", True),
+    ("2026-12-31T12:00:00Z", "2026-12-31T18:00:00Z", False),
+    ("2026-07-31", "2026-08-01T00:00:00Z", False),
+])
+def test_a_replay_judges_review_expiry_at_the_recorded_cutoff(recorded_cutoff, due, expired):
+    assert replay_expired(recorded_cutoff, due) is expired
+
+
+@pytest.mark.parametrize("recorded_cutoff", ["not-a-date", "2026-13-45", "20261231"])
+@pytest.mark.parametrize("time_mode", ["latest", "source_history"])
+def test_the_expiry_gate_never_swallows_a_malformed_recorded_cutoff(time_mode, recorded_cutoff):
+    bundle = nuclear_bundle(variant("N04", "R11DUE", review=review("accepted", "2027-01-01T00:00:00Z")))
+    query = nuclear_query("nuclear_components", "economics", time_mode=time_mode)
+    assert nuclear.compose_nuclear_research(query, bundle)["authorized_coverage"]["selected"] == 1
+    malformed = dataclasses.replace(query, recorded_cutoff=recorded_cutoff)
+    with pytest.raises(ValueError):
+        nuclear.compose_nuclear_research(malformed, bundle)
```

- **Remaining cost (INFO):** B also trips if the clock is later made replay-only, unless the base refuses or `_parse_day`-validates cutoffs in latest and source_history. Measured e_now_replay_only kills: none 6, all 3, sh_iso 4, every_iso 2 (`[20261231]`), every 0, refusal shapes 0. That is the intended tripwire: without it, a malformed cutoff would become a silent 200.
- **Why the wording changed from the mutation-tested version:** an earlier version said "wherever the gate compares…". B fails under e_now_replay_only even though the gate no longer compares outside a replay, so that wording promised less than B enforces. The final sentence matches B exactly.

## EVIDENCE
- **Suites:** final text (fresh copies tB10y and tA10y, `python -m pytest tests/test_*nuclear*.py -q`) gives 128 passed on Python 3.12.13 (CI's pin) and on 3.14.7. `diff` against the mutation-tested tB10w shows the docstring lines only; tA and tB copies are identical. The candidate gives 127 passed.
- **Unmutated engine, per base shape** (via /private/tmp/r10rev_8955bbc3/bf10s.py, which wraps `_validate_query`):

  | Version | none + 6 validation shapes | refuse_unread | refuse_latest | refuse_rec_unread |
  |---|---|---|---|---|
  | Candidate | 127/0 | 10 fails (4 new) | 4 (2 new) | 8 (4 new) |
  | Final | 128/0 | 6 (0 new) | 2 (0 new) | 4 (0 new) |

  - The head tests that fail under refusal shapes are `test_only_a_system_replay_reads_review_time`, `test_outside_a_replay_the_review_time_is_never_read[source_history-None|''|not-a-date]`, `test_explicit_latest_cutoff_still_decides_target_windows` and `test_passed_forward_target_stays_a_retrospective_target`.
- **Per mutant, no base fix** (`python3 /private/tmp/r10rev_8955bbc3/table.py`). A = the candidate's clock test, B = the no-swallow test, R = the new replay test. Head kills are 0 for all of these except e_expiry_swapped (3).

  | Mutant | Candidate | Final |
  |---|---|---|
  | e_swallow_serve / e_swallow_withhold | B×6 / B×6 | B×6 / B×6 |
  | e_swallow_latest_serve / e_swallow_sh_serve | 3 / 3 | 3 / 3 |
  | e_swallow_replay_serve | 0, EQUIVALENT | 0, EQUIVALENT |
  | e_now_fallback_malformed / _nonreplay / e_now_none_malformed | B×6 each | B×6 each |
  | e_now_replay_only | A×2 + B×6 | B×6 |
  | e_now_not_latest / e_now_not_sh | 4 / 4 | 3 / 3 |
  | e_now_never_cutoff | 8 | R×3 + B×6 |
  | e_now_not_replay | 0 | R[2026-12-31…T23-True], R[…T12-…T12-True], R[2026-07-31…-False] |
  | e_now_source_cutoff | 0 | R cases 1 and 3 |
  | e_now_advance_only | 0 | R[2026-07-31-2026-08-01T00:00:00Z-False] |
  | e_now_rewind_only | A×2 | R cases 1 and 3 |
  | e_now_date_only | 0 | R[…T12-…T12-True] |
  | e_expiry_strict | A×2 | R cases 1 and 3 |
  | e_expiry_swapped | A×2 | R×3 + B×6 |
  | e_due_trunc / e_now_trunc | 0 / 0 | R[…T12-…T18-False] each |
  | e_now_eager_parse | 0 | 0 (fail-closed, unpinned by design) |
  | e_now_min | 0 | 0 (store clock, out of scope) |

- **Kills under base fixes** (`python3 anbf.py tB10w <shape>`): the R kills persist under all 9 shapes. B's swallow kills become equivalent under every and the refusal shapes.
- **Parity:** Python 3.12 and 3.14 results match for all 26 mutants on the candidate and final trees. tA and tB results match for all 26 mutants on all three variant trees.
- **Probes:** /private/tmp/r10rev_8955bbc3/probe_r10_py312.out and probe2_r10_py312.out.
- **Citations at the exact commits:** nuclear 3a7e6582 at :109, :118, :133, :142, :179, :199-200, :272, :274, :282, :291, :328, :385, :409, :602. Semis a0d7b054ff23 at `_validate_query` :171-181, `_passes_time_mode` :204, and the comparisons at :234 and :236.
- **Current state:** #8002 head is still 3a7e6582 (OPEN, DRAFT). Post 5869344590 is unedited (created and updated both 11:56:10Z; body matches my saved copy).

## GAPS
- The MCP server `mastermind-executive` needs authorization, via `claude mcp` or /mcp in an interactive session. `mmx-cimd-probe` failed to connect (HTTP 501). Neither was needed for this review.
- I ran the R-ENE-40 tests at the engine only, not through the route.
- The seat's own matrix covered only the `all` and `iso` base shapes (its m11_all and m11_iso directories). The refusal-shape results above are new.
- Whether R-ENE-18 also puts the replay clock out of scope is the seat's call. If it does, drop R and keep B. The six mutants R alone kills (e_now_not_replay, e_now_source_cutoff, e_now_advance_only, e_now_date_only, e_due_trunc, e_now_trunc) would then survive again.
- I did not record the protected trees' HEADs at the start of the session. Now both have no tracked changes, at 9cd369985e5c (energy-records-r9-closure-r10) and 719517e33b8d (energy-records-r8), and macro-main has no tracked changes on main.

## DEVIATIONS
None. I only read the seat's scratch. GitHub access was four read-only GETs: rate_limit, pr view 8002, and the comment twice. I made no comments, labels, pushes or Slack actions.

SESSION END: PROVEN_OUTCOME
