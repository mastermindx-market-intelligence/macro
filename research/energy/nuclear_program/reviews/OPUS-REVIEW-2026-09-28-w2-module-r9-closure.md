# Opus closure check, round 9 — PR #8002 nuclear theme-research module (2026-09-28)

- **Artifact:** PR #8002 at `992cfa4bf09146cc454ec5cddd2aedcb7636f6a3`, with records PR #8148 at `bca32e73ba22` (merged as `b26775a7b739`) and the #7870 relay 5868018569 in scope.
  - This head is the round-9 lane's output: lane `ene_w2_nuclear_module_r9fix` on mb, a transcription by script, one commit "test(energy): pin the malformed-cutoff surface and the instant review clock (R-ENE-35, R-ENE-36)".
  - The commit transcribes seat rulings R-ENE-35 and R-ENE-36 (`../rulings/R-ENE-2026-09-28-w2-module-r9.md`).
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier.
- **Verdict: ACCEPT_WITH_NITS.** There is no BLOCKER, MAJOR or MINOR. Round 9 is correct as delivered: it touches one path, and the engine is byte-identical to round 8.
  - New findings:
    - NIT-1: the docstring's R-ENE-35 sentence overstates the engine. The guard reads the cutoff once a review time is readable, and the R-ENE-33 sentence holds only when either side is date-only.
    - NIT-2: four review-clock gap mutants survive, and each has a one-line kill.
    - NIT-3: the relay's table is right, but its prose overreaches in three places (the 400 bound, a second reader, the trace), and the records copy it.
    - NIT-4: the handoff's guard-escape sentence drops "against a well-formed cutoff".
    - NIT-5: R-ENE-35 stops observing the guard once the base validates cutoffs; with an ISO-parser validator that becomes a real hole.
    - Observations: O1, #8148 is already merged; O2, a citation to the parent's line numbers; O3, the relay's `source_history` row stands; O4, two more base-owned silent 200s; O5, the six persistent survivors are the recorded equivalents.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-28-w2-module-r10.md`.
  - NIT-1 becomes R-ENE-37 (the docstring rescoped), NIT-2 becomes R-ENE-38 (five review-clock cases), and nuclear's half of NIT-5 becomes R-ENE-39 (`20261231`).
  - NIT-3, NIT-4 and O2 are corrected at source. The relay correction (NIT-3) and the parser note (NIT-5) went to #7870 as comment 5869344590.
  - The seat's own finding refines O4: nuclear's review-expiry gate reads `recorded_cutoff` in every mode.

## Review text (verbatim)

STATUS: COMPLETE. This is the round-9 closure review by the same carrier, a14e0071943034a00. MODE: READ_ONLY. Every mutant, probe and test ran only in my scratch at /private/tmp/r9rev_8955bbc3/.

# RESULT

**Verdict: ACCEPT_WITH_NITS.** This covers #8002 at 992cfa4bf091 (parent 8bae70522f38), records PR #8148 at bca32e73ba22 (already merged as b26775a7b739), and relay 5868018569 on #7870.

- There is no BLOCKER, MAJOR or MINOR finding. There are five NITs and five observations.
- Round 9 is correct as delivered. It touches one path, and the engine is byte-identical to round 8.
- Nothing here blocks #8002's path. Every NIT can ride the next records PR or the post-#7870 rebase.

## Answers by vector

**(a) Right reason for the 8 newly killed seat mutants: PASS.** There were no errors in any run.

| Mutant | What it does | Failed, r8 → r9 | Where it fails in r9 |
|---|---|---|---|
| m34_broad | moves the try around `_le`, so the cutoff error is swallowed | 0 → 2 | :167 [not-a-date], [2026-13-45], "DID NOT RAISE ValueError" |
| my8_swallow_cutoff | parses the cutoff inside the guard's try | 0 → 2 | :167 ×2, same message |
| my8_inst_withheld | withholds any instant review time | 0 → 2 | :174; :184[11:00Z] |
| my8_dateonly_parse | checks readability with strptime %Y-%m-%d | 0 → 2 | :174; :184[11:00Z] |
| m36_inst_cutoff_withheld | withholds an instant review against an instant cutoff | 0 → 1 | :184[11:00Z] |
| my8_day_trunc | truncates the review to its day | 0 → 1 | :184[23:00Z] |
| my8_guard_all_modes | outside a replay, withholds a None or '' review | 0 → 4 | :196, latest and source_history × None and '' |
| m36_parse_all_modes | runs the readability guard in every mode | 0 → 6 | :196, all six cases |

- my8_guard_all_modes shows 'not-a-date', so its 'not-a-date' cases pass. That matches its definition. m36_parse_all_modes covers 'not-a-date' in both non-replay modes.

**(b) R-ENE-35: PASS, with a forward caveat (NIT-5).**

*Where the ValueError is raised.*
- It comes from `datetime.strptime` in semis `_parse_day` (semiconductor_theme_research.py:151 @a0d7b054ff23).
- `_parse_day` is called by `_le:159`, the branch where both sides are date-only.
- `_le` is called by nuclear `_reviewed_by_cutoff` at nuclear_theme_research.py:340 @992cfa4bf091. That line is outside the try at :334-339, so nothing swallows the error.
- The guard is reached from the absent count in `__init__` at :213-215.
- The full chain is `compose_nuclear_research:789 → _compose:720 → __init__:213 → <genexpr>:215 → _reviewed_by_cutoff:340 → _le:159 → _parse_day:151`.
- The error message names the cutoff value.
- `_validate_query` saw both cutoffs and passed them. It refuses only None (semis :179-181).
- In both bundles, the only `_le` call is the guard's. The time gate at semis :236 is never reached, which matches r9 ruling :46.

*Positive control.*
- The control uses the same bundle, the same block and the same call site, with REPLAY's '2026-12-31'.
- The call `_le('2026-09-20','2026-12-31')` returns True, and the block counts as `interpretation_inputs_absent:1`.
- The path is identical in all four sub-cases: 2 cutoffs × with and without the record.

*HTTP status.*
- No HTTP status is pinned.
- The round-9 diff touches one path. The route test is unchanged: sha256 dff63c3926ef02a6 at both heads.
- None of the added lines mention a status, 400/422/500/503, the client or the route.
- I simulated three base fixes independently: replay-only, all modes, and an ISO-parser variant. Under each, the nuclear suite gives 110 passed on both trees.

**(c) Docstring vs engine: PASS on "claims no coverage"; NIT-1 on two contract sentences.**
- The docstring (tests/test_nuclear_research_interpretation_scope.py:1-14 @992cfa4bf091) names rulings and claims no coverage. The r8 line "R-ENE-33 pins the rest of that review clock" is gone.
- The R-ENE-34 and R-ENE-36 sentences match the engine (:329-340) and `_le` (semis :154-164).

**(d) New mutants: 13, none of them in mutplug9.py.**
- The r8 suite kills 3 of them; the r9 suite kills 6.
- The three newly killed ones (n9_source_cutoff_instants, n9_skip_instant_pairs, n9_cutoff_trunc) are killed by the R-ENE-36 pins, which shows those pins do real work.
- Seven survive:
  - n9_lt_instants, n9_drop_offset, n9_eod_synthesis and n9_parse_clock_guard: **GAP** (NIT-2).
  - n9_utc_day: **GAP deferred to the base**. It is the relay's O1 contract question, and pinning either side now would pre-empt the owner.
  - n9_mode_whitelist: **EQUIVALENT under the route contract**. `time_mode` is a Literal, so 'bogus' answers 400 `invalid_request` `literal_error ['time_mode']` before the engine runs.
  - n9_cutoff_parse_outside_try: **EQUIVALENT under a `_parse_day` base fix**. Today it is evidence for NIT-1, not a pin request.

**(e) Records #8148: PASS, with NIT-3 (part), NIT-4, O1 and O2.**
- The citations resolve at the commits they name.
- Every false claim is corrected by quoting it, never by deleting it (E9).
- The r8-closure record is my round-8 message verbatim.
- `agentos validate` exits 0.

**(f) Relay 5868018569: PASS on the statuses, on O1, and on "Semis was not probed"; NIT-3 on the prose.**
- I reproduced the status table exactly, both at head and under a replay-only fix.
- Both O1 examples hold:
  - `_le('2026-12-31T23:00:00-05:00','2026-12-31')` is True; in UTC that instant is 2027-01-01T04:00Z.
  - `_le('2027-01-01T01:00:00+08:00','2026-12-31')` is False; in UTC that instant is 2026-12-31T17:00Z.
  - Both calls take semis :162-163.
- "Semis was not probed" is honest. The probe registers only nuclear, and the relay makes no claim about semis statuses. app/theme_research.py:156-162 @a0d7b054ff23 records that semis refuses system_replay in its loader (404).

## Findings

**NIT-1 (c): the docstring's R-ENE-35 sentence overstates the engine.**
- **Severity:** NIT.
- **Where:**
  - The docstring text is at tests/test_nuclear_research_interpretation_scope.py:12-14 @992cfa4bf091: "The guard reads only the block's clock, so a malformed query cutoff still fails the query instead of withholding the block (R-ENE-35)."
  - At bca32e73ba22, the same wording appears in research/energy/nuclear_program/rulings/R-ENE-2026-09-28-w2-module-r9.md at :41 and :104-106, and in its title at :1.
  - It also appears at agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md:55.
- **What is wrong:**
  1. The guard does read the cutoff: engine/market_ontology/nuclear_theme_research.py:340 is `return _le(reviewed, self.query.recorded_cutoff)`. Only the try at :334-339 reads the block's clock alone. The engine comment at :337-338 says "Only the block's clock is read here", and the docstring drops "here".
  2. "Still fails the query" holds only when the guard reaches :340, that is, for a block whose own review time is a readable string. A block with no review time, an empty one or an unreadable one is withheld at :333 or :339 before the cutoff is read. If nothing else reads the cutoff, the query succeeds.
  3. At :10-11, "a review on the cutoff day is by the cutoff (R-ENE-33)" holds only when either side is date-only (semis `_le` docstring :155-157). Against an instant cutoff, an instant review later that day is not by the cutoff. The file itself pins this at :184 [23:00Z].
- **Probe:**
  - `probe_f9.py head` gives `replay recorded='not-a-date' [out-of-slice + block reviewed=''] -> 200`, beside `[... reviewed='2026-09-20'] -> 503`.
  - `probe_d9.py` gives `n9_cutoff_parse_outside_try ... recorded='not-a-date' reviewed_at='' assertions=0: head=withheld mutant=RAISES ValueError`.
  - The surviving mutant is the one that would make the sentence true.
- **Fix:** No engine change. Change the docstring wording only:
  - Scope the sentence the way the test name does, for example: "wherever the guard compares a readable review time with the recorded cutoff, a malformed cutoff raises; the guard never swallows it (R-ENE-35)".
  - Qualify the R-ENE-33 sentence: "a review on the cutoff day is by the cutoff when either side is date-only".
  - Carry the same wording to r9 ruling :41 and :104-106 and handoff :55 as quoted annotations.
- **Owner:** Energy seat.

**NIT-2 (d): four gap mutants on the review clock survive, and each has a one-line kill.**
- **Severity:** NIT.
- **Where:**
  - tests/test_nuclear_research_interpretation_scope.py:177-184 @992cfa4bf091 pins the instant clock with only two Z-suffixed reviews, both off the boundary: 11:00Z and 23:00Z against a 12:00Z cutoff.
  - Handoff :656 @bca32e73ba22 says "The instant review clock is pinned".
- **The four survivors, each 0 failed out of 110 (head vs mutant from probe_d9):**

| Mutant | Input (cutoff, review time) | Head | Mutant |
|---|---|---|---|
| n9_lt_instants | noon, 12:00Z | shown | withheld |
| n9_drop_offset | noon, '2026-12-31T08:00:00-05:00' (13:00Z) | withheld | shown (a leak) |
| n9_drop_offset | noon, '2026-12-31T19:00:00+08:00' (11:00Z) | shown | withheld |
| n9_eod_synthesis | noon, '2026-12-31' | shown | withheld |
| n9_parse_clock_guard | '2026-12-31', '20260920' or '2026-W38-7' | withheld | raises ValueError (route 503) |

- **Probe:** I wrote the candidate pins in a scratch file, /private/tmp/r9rev_8955bbc3/tB/tests/test_zz_r9rev_suggested_pins.py.
  - At head, all 5 cases pass.
  - They kill n9_lt_instants (1 case), n9_drop_offset (2), n9_eod_synthesis (1) and n9_parse_clock_guard (1, "ValueError: time data '20260920' does not match format '%Y-%m-%d'").
  - n9_utc_day, n9_mode_whitelist and n9_cutoff_parse_outside_try survive, as expected (0 failed).
- **Fix:**
  - Extend the parametrize at :177-178 with ("2026-12-31T12:00:00Z", SUPPORTED), ("2026-12-31T19:00:00+08:00", SUPPORTED), ("2026-12-31T08:00:00-05:00", []) and ("2026-12-31", SUPPORTED).
  - Add one test: a review time of "20260920" is withheld (shown == []) and not counted (counted_absent == [] for an unknown input).
  - Two caveats:
    - The '20260920' kill needs Python 3.11 or later, because older fromisoformat rejects the basic format. On older versions the test passes on both head and mutant.
    - The ("2026-12-31", SUPPORTED) case pins the base's date-vs-instant branch (semis :160-161), not the O1 branch.
  - Until the pins land, scope the handoff wording to "pinned for Z instants off the boundary".
- **Owner:** Energy seat. This can ride the post-#7870 rebase.

**NIT-3 (f, e): the relay's table is right, but its prose overreaches in three places, and the records copy it.**
- **Severity:** NIT.
- **Where:**
  - Relay 5868018569 body, lines 5, 16 and 20.
  - At bca32e73ba22:
    - handoff :119 (a verified claim), :135, :639 and :672;
    - r8 ruling :77;
    - r9 ruling :57.
- **What is wrong:**
  1. **"A malformed cutoff never gets a 400."**
     - A cutoff longer than 32 characters, or a non-string, gets 400 `invalid_request` from pydantic (`string_too_long`, `string_type`; app/theme_research.py:197-198 and :541-543).
     - The verified claim at handoff :119 says "never", but its result at :121 covers only 'not-a-date' and '2026-13-45'. The claim is upgraded beyond its evidence.
  2. **"When a time gate reads the cutoff ... 503" and "So the first parse happens inside a time gate."**
     - Nuclear's own review guard is a second reader.
     - With an out-of-slice record no time gate runs, yet a block reviewed '2026-09-20' answers 503. The same bundle with a block reviewed '' answers 200.
     - The recommended fix shape is unaffected and still right.
  3. **"The malformed cutoff leaves no trace."**
     - The limitations match the control.
     - But the 200 payload differs at `.generation`, and it echoes the bad value at `.request.recorded_cutoff`.
- **Probe (probe_f9 head rows):**
  - `replay recorded=<33-char non-date> -> 400 ... string_too_long`
  - `replay recorded=20261231 (JSON int) -> 400 ... string_type`
  - `[out-of-slice + block reviewed='2026-09-20'] -> 503` and `[... reviewed=''] -> 200`
  - `empty-bundle payload diff control vs 'not-a-date': 2 path(s): [('.generation', ...), ('.request.recorded_cutoff', '2026-12-31', 'not-a-date')]`
- **Root cause is partly mine.** My round-8 NIT-D proposed "503 when a time gate reaches the cutoff, a silent 200 otherwise" (research/energy/nuclear_program/reviews/OPUS-REVIEW-2026-09-28-w2-module-r8-closure.md:123 @bca32e73ba22). I amend it to: "For a malformed cutoff string within the 32-character bound, the answer is 503 when a time gate reads it, or when nuclear's review guard reads it for a block with a readable review time, and a silent 200 otherwise. A longer or non-string cutoff gets 400."
- **Fix:**
  - Annotate at source in the next records PR, quoting the old text rather than deleting it.
  - Correct the relay only on the next #7870 post that has substance, for example together with NIT-5's parser note. Do not post a correction on its own.
- **Owner:** Energy seat.

**NIT-4 (e): the handoff drops the "well-formed" qualifier.**
- **Severity:** NIT.
- **Where:** agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md:654 @bca32e73ba22: "No string passes the guard and then makes `_le` raise: 68 named strings × 10 cutoffs and a 300,000-string fuzz gave 0 escapes."
- **What is wrong:**
  - Without "against a well-formed cutoff", the sentence contradicts R-ENE-35. R-ENE-35 pins exactly that event: a readable review string passes the guard, and `_le` raises on the malformed cutoff (the probe_b chain in (b)).
  - r9 ruling :8 carries the qualifier.
  - Handoff :53 uses the defined term "guard escape", which is acceptable, but it would read better with the qualifier too.
- **Fix:** Add "against a well-formed cutoff" at :654 as an annotation.
- **Owner:** Energy seat.

**NIT-5 (b, forward): R-ENE-35 stops observing the guard once the base validates cutoffs, and with an ISO-parser validator that becomes a real hole.**
- **Severity:** NIT.
- **Where:**
  - tests/test_nuclear_research_interpretation_scope.py:160 @992cfa4bf091 parametrizes over 'not-a-date' and '2026-13-45' only.
  - The relay's fix shape (line 21) does not name a parser.
- **What happens after a base fix:**
  - Once the base validates, both current values are refused before they reach the guard. The pin then observes the base's refusal, because ResearchRefusal subclasses ValueError, and the swallow mutants survive.
  - **With a `_parse_day` validator, that is harmless.** A cutoff `_parse_day` accepts is one `_le` parses (the r8 ruling :63 argument, applied to the cutoff), so the mutants become equivalent by construction.
  - **With a `fromisoformat` validator, it is a real hole.**
    - '20261231' and '2026-W53-4' pass `datetime.fromisoformat` but fail `_parse_day`, so they reach the guard.
    - At head the query raises, which the route turns into 503 via app :683-687.
    - Under m34_broad or my8_swallow_cutoff the block is silently withheld and the route answers 200.
- **Probe:** `probe_o2.py`:
  - `validator=parse_day cutoff='20261231'`: head, m34_broad and my8_swallow_cutoff all raise `ResearchRefusal(replay_cutoffs_required)`.
  - `validator=iso cutoff='20261231'`: `head: bare ValueError | m34_broad: absent=[] | my8_swallow_cutoff: absent=[]`.
- **Pytest runs, with `-p mp9r -p bf9r`:**

| BASEFIX | MUTANT | Result |
|---|---|---|
| iso | m34_broad | R-ENE-35 [not-a-date] and [2026-13-45] pass, so the mutant survives; the variant's [20261231] case FAILED, so it is killed. my8_swallow_cutoff behaves the same. |
| none, replay, iso | none | 5 passed |
| iso, replay, all | none (full nuclear suite) | 110 passed on tA and on tB |

- **Fix:**
  1. Nuclear: add "20261231" to the parametrize at :160. It is one token. It passes at head and under every simulated fix, and it keeps m34_broad observable unless the owner validates with `_parse_day`. In that case m34_broad becomes EQUIVALENT: record that at the rebase, and do not reopen it as a regression.
  2. Base owner, as an addendum on the next #7870 post with substance: validate cutoffs with `_parse_day`, the parser `_le` uses.
- **Owner:** Energy seat for (1); the #7870 owner for (2).

## Observations

- **O1.** #8148 is already MERGED (merge commit b26775a7b7399504ca3708e5d6d04d2adb43fb5d). Every records fix above therefore needs a follow-up records PR of quoted annotations.
- **O2.** r9 ruling :22 @bca32e73ba22 cites "the handoff (:117, :616)". Those are the parent's line numbers (fbd78d1242a3).
  - At bca32e73ba22, :117 is a postlane command line, and :616 reads "5. a report: the base's unreadable-`reviewed_at` 503;".
  - The annotated lines are :135 and :639. Name the commit, or re-point the citation.
- **O3.** The seat's relay probe had no well-formed source_history control. Mine answers 200 both in-slice and with an empty bundle, so the relay's source_history 503 row stands.
- **O4.** Two more silent 200s are not in the relay's table. They are base-owned, and no ask is needed now.
  - source_history with a malformed recorded_cutoff answers 200, even with an in-slice record.
  - latest with a malformed recorded_cutoff answers 200.
  - Whether an unread cutoff should be refused or ignored is the owner's call. My all-modes fix variant turns the source_history row into 400 and leaves latest at 200.
- **O5.** The six persistent seat survivors are the recorded EQUIVALENTs: role_pred, r9_reason_review_ok, r9_status_review_ok, my_continue_past_pointer, my_no_seen and my_prefix_from_served (rulings/R-ENE-2026-09-28-w2-module-r7.md:89 @bca32e73ba22).
  - The engine is byte-identical at both heads (sha256 3a795c54c70e3a08), so nothing needs reclassifying.

# EVIDENCE

All runs used my scratch at /private/tmp/r9rev_8955bbc3/, with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=<scratch>:<tree>.

**E1. Trees and hashes.**
- tA is the frozen snapshot base plus the #8002 files @992cfa4bf091.
- tB is the a0d7b054ff23 compat tree plus the #8002 files @992cfa4bf091.
- tB8 is the same compat tree with the r8 suite @8bae70522f38.
- sha256 prefixes:
  - scope test: f0c4042b3f65d4bd in tA and tB; 55f5580590aeea2d in tB8;
  - engine: 3a795c54c70e3a08 in all three;
  - route test: dff63c3926ef02a6 in all three.

**E2. Baselines** (`pytest tests/test_*nuclear*.py`).
- tA: 110 passed. tB: 110 passed. tB8: 99 passed.
- The route test: 4 passed.
- `pyflakes` on the r9 scope test: rc 0.

**E3. Mutation matrix.**
- Command: `bash run9r.sh <tree> <outdir>`, covering the seat's 68 mutants (loaded from my copy of mutplug9.py) plus my 13 n9 mutants.
- Output files: matrix_tB.out and matrix_tB8.out. There were no errors in any of the 164 runs.
- Seat mutants: 54 of 68 killed in r8, 62 of 68 in r9. The r9 survivors are exactly the 6 equivalents in O5.
- n9 mutants: 3 of 13 killed in r8, 6 of 13 in r9.

**E4. probe_b.py (tB).** The first sub-case is shown; the other three are identical, with only the cutoff value changing.

```
== cutoff='not-a-date' assertions=(elsewhere,)
   control: counted_absent=['interpretation_inputs_absent:1']; _le calls=[('nuclear', '_reviewed_by_cutoff', '2026-09-20', '2026-12-31', True)]
   malformed: ValueError(time data 'not-a-date' does not match format '%Y-%m-%d'); validate saw ['2026-12-31', 'not-a-date']
   malformed _le calls=[('nuclear', '_reviewed_by_cutoff', '2026-09-20', 'not-a-date', 'RAISES ValueError')]
   raising chain=['compose_nuclear_research:789', '_compose:720', '__init__:213', '<genexpr>:215', '_reviewed_by_cutoff:340', '_le:159', '_parse_day:151']
```

**E5. probe_d9.py (tB).** The head-vs-mutant lines are quoted in NIT-2 and in (d). The two cases that do not distinguish are `n9_cutoff_parse_outside_try` with reviewed=None and `n9_mode_whitelist` in latest mode.

**E6. Suggested pins.** Results are in sugg_*.json (passed/failed):

| Run | Passed | Failed |
|---|---|---|
| none | 5 | 0 |
| n9_lt_instants | 4 | 1 |
| n9_drop_offset | 3 | 2 |
| n9_eod_synthesis | 4 | 1 |
| n9_parse_clock_guard | 4 | 1 |
| n9_utc_day | 5 | 0 |
| n9_mode_whitelist | 5 | 0 |
| n9_cutoff_parse_outside_try | 5 | 0 |

- The file now has 8 tests, including the R-ENE-35 variant. At head: 8 passed.

**E7. probe_f9.py in modes head, replayfix and allfix.** The output is in probe_f9_tB.out.

| Request | Head (in-slice / empty) | Replay-only fix | All-modes fix |
|---|---|---|---|
| replay, recorded 2026-12-31 (control) | 200 / 200 | 200 / 200 | 200 / 200 |
| replay, recorded not-a-date or 2026-13-45 | 503 / 200 | 400 / 400 | 400 / 400 |
| replay, source not-a-date | 503 / 200 | 400 / 400 | 400 / 400 |
| source_history, well-formed source (control) | 200 / 200 | 200 / 200 | 200 / 200 |
| source_history, source not-a-date | 503 / 200 | 503 / 200 | 400 / 400 |
| source_history, recorded not-a-date | 200 / 200 | 200 / 200 | 400 / 400 |
| latest, recorded not-a-date | 200 / 200 | 200 / 200 | 200 / 200 |

- Out-of-slice record plus a block reviewed '2026-09-20', recorded not-a-date: 503 at head; 400 under both fixes.
- The same with a block reviewed '': 200 at head; 400 under both fixes.
- A 33-character cutoff and a JSON integer cutoff answer 400 in every mode.
- Every response carries `Cache-Control: private, no-store`.
- The payload diff and the echoed value are quoted in NIT-3.
- time_mode 'bogus' answers `400 invalid_request literal_error ['time_mode']`.

**E8. The NIT-5 forward check.** probe_o2.py (output in probe_o2_tB.out) and the BASEFIX pytest runs are quoted in NIT-5. I added an `iso` option to my bf9r.py for this.

**E9. Records.**
- I ran `git diff -U0 fbd78d1242a3 bca32e73ba22` read-only (output in records_diff_U0.txt). It removes 16 lines:
  - **9 lines are kept verbatim** with a dated bracket annotation: handoff :49, :604→:627 and :616→:639; r6-closure :16 and :209; r7 ruling :9; r8 ruling :16, :69 and :71.
  - **4 corrections quote the superseded wording** inside the annotation: handoff old :117→:135, :136→:156 and :151→:173, and r8 ruling :63 (the old `:141-163` is quoted).
  - **2 are superseded next-actions** (old :120-121).
  - **1 is the `prs` list.** It gains 8018, 8023 and 8143. All three are MERGED Energy records PRs (checked with a GraphQL read).
  - Old :117 also rewords "_validate_query never parses" to "refuses only a missing replay cutoff". Both statements are true.
- The r8-closure record is my round-8 message verbatim. The only difference is the EOF newline, and the seat header (lines 1-20) is accurate.
- **Citations resolved at a0d7b054ff23:**
  - semis :121, :138-164, :162-163, :179-181 and :236;
  - app/theme_research.py :146-167, :170-179, :197-198 and :683-687;
  - update.sh:1261. It is present at a0d7b054ff23 and absent on main, which is correctly scoped.
- **Fixture values present:** 2026-03-05T00:00:00Z, 2026-08-01T09:00:00Z and 2026-08-13T00:00:00Z.
- **Hashes match:** apply_r9 6ad420c0a20bd5e2; engine, scope test and route test as in E1.
- **The #8002 change itself:**
  - It is one commit, 992cfa4bf091, "test(energy): pin the malformed-cutoff surface and the instant review clock (R-ENE-35, R-ENE-36)".
  - Its hunks are -6,7 +6,12 and -150,3 +155,42.
  - The seat's sim files are identical.
- **State of main:**
  - None of the four #7870 modules is on main: semiconductor_theme_research, curation_assertion, theme_research_binding and semiconductor_owner_bundle.
  - No nuclear commit is on main.

**E10. agentos validate.** `python3 scripts/agentos.py validate` in partial archives of bca32e73ba22 and fbd78d1242a3 exits 0 for both, with "1340 records ... 0 error(s), 637 warning(s)". The warning sets are identical.

**E11. GitHub reads** (all read-only).
- #8148 is MERGED as b26775a7b7399504ca3708e5d6d04d2adb43fb5d. The compare shows six files with 81, 4, 155, 2, 10 and 156 changes, which equals the PR diffstat.
- #8002 is DRAFT at head 992cfa4bf091, with labels [], auto_merge null, and base `claude/energy-stack-base-b-6cd958e9`.
- Comment 5868018569 was created 2026-09-28T10:20:50Z and has never been edited.

**Per-mutant list.** Figures are failed tests, r8 suite / r9 suite; 0 means the mutant survived.

- Seat (68):
  - B1_noop 5/5, M1M2 7/7, M3 3/3, M5 4/4, ccj_rt_cohort 3/3, ccj_rt_exempt 2/2, codes_off 1/1, cohort_off 8/8, latest_only 1/1, leu_nc_cohort 2/2, lineage_empty 11/11, lt 1/1, m3 2/2, m7 3/3
  - m33_any_mode 1/4, m33_lt 1/1, m33_no_mode 12/18, m33_nonstr 1/1, m33_source_cutoff 1/4
  - m34_broad 0/2, m34_no_guard 4/4, m34_parse_cutoff 4/6, m34_show 4/4, m36_inst_cutoff_withheld 0/1, m36_parse_all_modes 0/6
  - my8_count_never 5/7, my8_dateonly_parse 0/2, my8_day_trunc 0/1, my8_guard_all_modes 0/4, my8_helper_false 6/10, my8_inst_withheld 0/2, my8_swallow_cutoff 0/2
  - my_continue_past_pointer 0/0, my_no_seen 0/0, my_pointer_from_root 1/1, my_prefix_from_served 0/0, my_raw_fallback 7/7, my_reverse 3/3
  - next_query 1/1, nostale 1/1, prd_only 1/1, presence_only 1/1
  - r29_current 1/1, r29_no_pointer 8/8, r29_one_hop 3/3, r29_pre 2/2, r29_raw 7/7
  - r31_accepted_only 4/4, r31_count_ungated 5/7, r31_helper_true 7/10, r31_raw 5/7, r31_select_ungated 6/7
  - r9_evrefs_pre 3/3, r9_reason_pre 3/3, r9_reason_review_ok 0/0, r9_selected_pre 4/4, r9_selected_review_ok 1/1, r9_stale_current 1/1, r9_stale_pre 4/4, r9_status_pre 3/3, r9_status_review_ok 0/0
  - refday_only 2/2, refday_pre 3/3, role_pred 0/0, sel_current 1/1, sel_pre 1/1, sup_off 3/3, why_sup 1/1
- Reviewer n9 (13): n9_cutoff_parse_outside_try 0/0, n9_cutoff_trunc 0/1, n9_drop_offset 0/0, n9_empty_readable 2/2, n9_enforce_only_instants 2/4, n9_eod_synthesis 0/0, n9_le_swapped 6/11, n9_lt_instants 0/0, n9_mode_whitelist 0/0, n9_parse_clock_guard 0/0, n9_skip_instant_pairs 0/1, n9_source_cutoff_instants 0/1, n9_utc_day 0/0.
- Baseline "none": 99 passed in r8, 110 passed in r9.

# GAPS

- Two MCP servers were unavailable; neither was needed for this review.
  - `mastermind-executive` needs authorization. It must be authorized via `claude mcp` or `/mcp` in an interactive session.
  - `mmx-cimd-probe` failed to connect with HTTP 501.
- The GraphQL blob lookups returned null for all six records paths. Byte identity with the PR therefore rests on the compare change counts and on local git objects.
- `agentos validate` ran on partial archives (agentos, config, scripts, research/energy, docs), not a full checkout. The warning sets are identical at head and parent.
- Route probes ran on tB only. Semis was not probed.
- The '20260920' kill depends on Python 3.11 or later. I ran on 3.14.7 and did not check CI's Python version.
- I did not re-run the seat's postlane9.sh or probe_r9_relay.py. I reproduced their results with my own instruments.
- NIT-5's ISO validator simulates one plausible owner fix; it is not the owner's code.

# DEVIATIONS

- **Pytest temp directory.** Pytest put its own basetemp under the system temp directory (/private/var/folders/.../pytest-of-chriswong), because the autouse `tmp_path_factory` fixtures in tests/conftest.py require it. The PytestWarnings in the runs are `rm_rf` failures on other runs' leftover directories there.
- **Protected trees are untouched.** W (8bae70522f38), R9 (bca32e73ba22) and macro-main (c492e673fbda) each show 0 lines from `git status --porcelain`, run with GIT_OPTIONAL_LOCKS=0, and their HEADs are unchanged.
- **Possible object-cache fill.** Before the context compaction I did not set GIT_NO_LAZY_FETCH for read-only `git show` and archive reads. A missing blob could therefore have been fetched into the shared object store. That fills a cache; it changes no ref, index or worktree file.
- **GitHub reads.** All were read-only GETs:
  - rate_limit;
  - comment 5868018569;
  - PRs 8002 and 8148;
  - one compare;
  - two GraphQL queries (the null blob lookup, and the titles of #8018, #8023 and #8143).
- **Denied loop.** The quota hook denied one `gh` loop before any call ran. I did not retry it.
- **Own transcript.** I read my own subagent transcript (agent-a14e0071943034a00.jsonl, line 1315) to extract my round-8 message for the verbatim check.
- **Scratch-only additions.**
  - tB/tests/test_zz_r9rev_suggested_pins.py. It is never proposed as bytes, and it falls outside the tests/test_*nuclear*.py glob, so the matrix is unaffected.
  - The `iso` option in bf9r.py.

SESSION END: PROVEN_OUTCOME
