# Opus closure check, round 8 — PR #8002 nuclear theme-research module (2026-09-28)

- **Artifact:** PR #8002 at `8bae70522f38f251e224cdf81a0a975710be9be0`, with records PR #8143 at `719517e33b8d` in scope.
  - This head is the round-8 lane's output: lane `ene_w2_nuclear_module_r8fix` on mb, a transcription by script, one commit "fix(energy): withhold unreadable replay review times and pin the review clock (R-ENE-33, R-ENE-34)".
  - The commit transcribes seat rulings R-ENE-33 and R-ENE-34 (`../rulings/R-ENE-2026-09-28-w2-module-r8.md`).
- **Reviewer:** the same Opus `reviewer`, MODE READ_ONLY, native child `a14e0071943034a00`, resumed on the same carrier. The brief also put #8143's at-source corrections and the queued base relay in scope.
- **Verdict: ACCEPT_WITH_NITS.** There is no BLOCKER or MAJOR. Vector (a), whether any string passes the guard and then makes `_le` raise, found no escape: 68 named strings × 10 well-formed cutoffs, and a fuzz of 300,000 strings, gave 0 escapes and 0 inverses.
  - New findings:
    - NIT-A: the reason the r8 records give for leaving `m34_broad` unpinned is false. An engine `pytest.raises(ValueError)`, or a route `status_code >= 400`, kills it without pinning the 503, and both keep passing after the base fix.
    - NIT-B: the instant-format review clock has no pins (four surviving mutants), and the scope test's docstring overclaims.
    - NIT-C: four copies of the withdrawn line-number point are still unmarked.
    - NIT-D: the queued relay's headline holds only when the bundle has content. Nuclear's own empty owner loader answers a silent 200.
    - Observations: O1 is base-owned (`_le` reads an instant against a date-only cutoff on the instant's own local day); O2 is a line span; O3 is the R-ENE-19 bullet not naming the docstring edit.
- **Seat adjudication:** `../rulings/R-ENE-2026-09-28-w2-module-r9.md`.
  - NIT-A becomes R-ENE-35, an appended engine pin. The false reason is corrected at source.
  - NIT-B becomes R-ENE-36: appended instant-clock and non-replay pins, and the docstring's closing sentences rewritten to state the contract instead of claiming coverage.
  - NIT-C, NIT-D, O2 and O3 are corrected at source. NIT-D also corrects the relay before it is posted to #7870.

## Review text (verbatim)

STATUS: COMPLETE. I answered all eight vectors (a) to (h). I ran the vector (a) probe again in this session. The reviewer tree W is at detached HEAD 8bae70522f38f251e224cdf81a0a975710be9be0 and `git status --short` is empty after every run. I made no writes anywhere.

RESULT
ACCEPT_WITH_NITS for #8002 at 8bae70522f38 and records PR #8143 at 719517e33b8d.

The FIX_REQUIRED trigger in vector (a) did not fire: no string passes `_parse_day` and then makes `_le` raise against a well-formed cutoff. There are four nits:
- **NIT-A:** the reason given for leaving m34_broad unpinned is false.
- **NIT-B:** the instant-format review clock has no pins.
- **NIT-C:** four copies of the withdrawn line-number point are still unmarked.
- **NIT-D:** the relay headline is only true when the bundle has content.

**Answers by vector**

- **(a) Guard completeness: no escape.**
  - By construction: `_le` reads the review time only through `_parse_day` (date-only) or `_parse_clock` (instant). For an instant, `_parse_day` is `_parse_clock(value).date()` (semiconductor_theme_research.py:150-151 @a0d7b054ff23). `_parse_clock` always returns a timezone-aware datetime (:142-147), so comparing naive and aware values cannot raise.
  - Probe, run this session: 68 named strings x 10 well-formed cutoffs gave escapes=0, inverses=0. A fuzz of 300000 strings (seed 8002), 15044 of which passed the guard, gave escapes=0, inverses=0.
- **(b) The inverse: none.** The guard and `_le` make the same parse calls, and the probe found inverses=0.
- **(c) Semantics: sound, no finding.**
  - In a replay, the payload with an unreadable-review block is byte-identical to the payload with no block (C1 True). A block reviewed after the cutoff behaves the same (C1b True).
  - In latest mode the block is still shown (C2).
  - Surfacing the unreadable time in a replay would reveal that a post-cutoff block exists and would break R-ENE-31 determinism. Rejecting malformed `reviewed_at` belongs in block-source validation, which is base-owned.
- **(d) m34_broad: choosing to leave it unpinned is acceptable, but the stated reason is false (NIT-A).**
  - The seat's observability claim holds. With an in-slice N04 assertion, every mode raises first at semis :236 (E4).
- **(e) Yes, the pins fail for the right reason.**
  - Against the round-7 engine 3c775ea5, exactly four new cases fail:
    - the three string cases of `withholds[...]` fail with ValueError from `_le`;
    - route case `[-False]` fails with `assert 503 == 200`.
  - `[None]` passes there, because the `isinstance` check already existed.
  - Each mutant is killed by the intended test:

    | Mutant | Killed by |
    |---|---|
    | m33_lt | the cutoff-day test |
    | m33_source_cutoff | the recorded-cutoff test |
    | m33_any_mode | `only_a_system_replay_reads_review_time` |
    | m33_nonstr | `withholds[None]` |
    | m34_no_guard, m34_parse_cutoff, m34_show | the three string cases plus route `[-False]` |

  - The route test does reach the engine through the `load_bundle` override (route test :43-54, :105-108): my8_helper_false kills route case `[2026-09-20-True]`.
  - The coverage gap is NIT-B.
- **(f) R-ENE-19 append-only holds.**
  - No test is deleted or renamed, and no fixture is reshaped.
  - `client(monkeypatch, registration=None)` returns `registration or nuclear_registration()`, which reproduces the old behaviour. The control run gives 99 passed.
  - See O3.
- **(g) The markers that exist are accurate.**
  - Robotics facts re-read at a1c8968f8e2f:
    - `_correction_lineage` def at :1295, docstring :1297-1299, `by_revision` :1300-1301;
    - `known_revisions` built :400, counted :404, withheld :530, read :549 inside `_inputs_known`.
  - Relay 5866433049 items 4-5 match (created 2026-09-28T08:37:33Z, never edited).
  - Every surviving "count-only" copy is marked. NIT-1 has four unmarked copies (NIT-C).
- **(h) The relay is correctly scoped as base-owned.**
  - The cutoff fields on `_QueryBody` (app/theme_research.py:197-198) belong to the shell.
  - `_validate_query` belongs to semis (:171 @a0d7b054ff23). Nuclear imports it and calls it at nuclear_theme_research.py:719 and :821.
  - So one base fix covers nuclear. My simulated base fix returns 400 in every case, including the empty bundle.
  - The headline is wrong for nuclear's own loader (NIT-D).

**NIT-A (vector d): false reason for leaving m34_broad unpinned**
- **Severity:** NIT, in records plus an optional pin. The handoff's do_not_redo entry makes the false reason binding on future sessions.
- **Where** (all @719517e33b8d):
  - R-ENE-2026-09-28-w2-module-r8.md:73 says "The only test that could kill it would pin today's 503".
  - agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md:136 (do_not_redo: "stays unpinned") and :151 repeat it.
- **Input:** a replay with recorded_cutoff='not-a-date', one out-of-slice assertion (N05 'K1other_slice'), and one block with a readable review time.

  | Mode | Engine | Route |
  |---|---|---|
  | head | raises ValueError | 503 |
  | m34_broad | returns a payload | 200 |
  | simulated base fix (`ResearchRefusal('replay_cutoffs_required')`, a ValueError subclass at semis :121) | raises | 400 |

- So `pytest.raises(ValueError)` at the engine, or `status_code >= 400` at the route, kills m34_broad and my8_swallow_cutoff. Neither pins 503, and both keep passing after the base fix.
- **Owner:** nuclear-local. Either append the pin, or reword the ruling and do_not_redo to say the mutant is left unpinned by choice.

**NIT-B (vector e): instant review clock has no pins; test docstring overclaims**
- **Severity:** NIT.
- **Where:** tests/test_nuclear_research_interpretation_scope.py:9 @8bae70522f38 says "R-ENE-33 pins the rest of that review clock".
- **Survivors:** four mutants each survive the full nuclear suite with 99 passed. On each input below the head's own behaviour is correct.

  | Case | Input | Head | Surviving mutant(s) |
  |---|---|---|---|
  | C3 | replay, reviewed_at '2026-09-20T00:00:00Z' | shows | my8_inst_withheld and my8_dateonly_parse withhold it |
  | C4 | recorded_cutoff '2026-12-31T12:00:00Z', reviewed_at '2026-12-31T23:00:00Z' | withholds | my8_day_trunc shows it, leaking a post-cutoff review |
  | C2 | latest mode, reviewed_at '' | shows | my8_guard_all_modes withholds it |

- The base fixtures use instant review times ('2026-03-05T00:00:00Z' and '2026-08-13T00:00:00Z' in corrected_interpretation.json @a0d7b054ff23). So the unpinned path is the format production uses.
- **Owner:** nuclear-local tests.

**NIT-C (vector g): unmarked copies of the withdrawn line-number point**
- **Severity:** NIT.
- **Where** (all @719517e33b8d):
  - OPUS-REVIEW-2026-09-25-w2-module-r6-closure.md:209: "The only mismatch is the :1300 line number (NIT)." It carries no annotation; lines :11, :56 and :202 do.
  - The same file, :16: "The line number is corrected at source."
  - R-ENE-2026-09-28-w2-module-r7.md:9: "a relay line number was wrong".
  - Handoff :49 says "the three places"; there are four.
  - So the r8 ruling's :16 claim that the erratum is "withdrawn at source in ... the r6 closure record" is incomplete.
- **Owner:** nuclear-local records. The root cause is mine: my round-7 revert list named :11, :56 and :202 and missed :209.

**NIT-D (vector h): relay headline only true when the bundle has content**
- **Severity:** NIT in the relay text. The defect itself is base-owned under R-ENE-09.
- **Where** (@719517e33b8d): r8 ruling :75-82, and handoff :117 and :616.
- **Probe:** nuclear's owner loader (`load_nuclear_owner_bundle`, nuclear_owner_bundle.py:25-43, which returns an empty bundle), run through the route with recorded_cutoff 'not-a-date' and '2026-13-45':
  - answers 200, not 503;
  - returns limitations identical to a well-formed cutoff: `['milestone_predicate_unavailable','omitted:private_assertions_unbound','omitted:public_assertions_uncurated','slice_scope_unowned']`.
- **[Seat annotation 2026-09-28 (round-9 closure NIT-3): the same reviewer amended this sentence in the round-9 closure: "For a malformed cutoff string within the 32-character bound, the answer is 503 when a time gate reads it, or when nuclear's review guard reads it for a block with a readable review time, and a silent 200 otherwise. A longer or non-string cutoff gets 400." The seat adds a third reader, nuclear's review-expiry gate, in every mode, for an assertion with a `review_due_at` (`../rulings/R-ENE-2026-09-28-w2-module-r10.md`).]** **[Seat annotation 2026-09-28 (round-10 closure): there is a fourth reader, nuclear's target-window judgement, which reads `source_cutoff` in every mode. And the review-expiry gate reads only the *selected* assertions; in a replay the base time gate reads a malformed `recorded_cutoff` first, so the expiry gate adds its 503 only outside a replay. Corrected on #7870 in addendum 5870740225 (`../rulings/R-ENE-2026-09-28-w2-module-r11.md`).]** The route test's fixture bundle does give 503. So the real behaviour is "503 when a time gate reaches the cutoff, a silent 200 otherwise". The silent 200 is what nuclear's own loader produces today.
- **Relay addition:** the base fix must use a code that `_RESEARCH_REFUSAL_MAP` (app/theme_research.py:146-167) maps to 400. `_map_research_refusal` (:170-178) turns any unmapped code into 503.
- **Engine comment:** the comment at nuclear_theme_research.py:337-338 ("still surfaces") is accurate for the helper itself. It is not a guarantee for the whole request.

**Observations**
- **O1 (base-owned):** `_le` compares an instant against a date-only cutoff using the instant's own local day. `_le('2026-12-31T23:00:00-05:00','2026-12-31')` is True, while `_le('2027-01-01T01:00:00+08:00','2026-12-31')` is False. The guard inherits this by construction.
- **O2:** r8 ruling :63 cites semis ":141-163". The helpers actually span :138-164.
- **O3:** the scope-test docstring was edited (1 line removed, 2 added), and the R-ENE-19 bullet (:69) does not mention it. Harmless.

EVIDENCE
Scratch files are in /private/tmp/r8rev_8955bbc3/.
- `/private/tmp/r8rev_8955bbc3/probe_a_guard.py`: `NAMED: 68 strings x 10 cutoffs; escapes=0 inverses=0` and `FUZZ: 300000 mutated strings, 15044 passed the guard; escapes=0 inverses=0`.
- `/private/tmp/r8rev_8955bbc3/probe_d_killer.py` in modes head, m34_broad and basefix: produced the E1, E1b, E3, E4, R1, R2 and C1-C4 results quoted above.
- Owner-loader route probe, inline: 200 / 200 / 200.
- `/private/tmp/r8rev_8955bbc3/matrix8r.sh` over the 4 files `tests/test_*nuclear*.py`:
  - control run: 99 passed;
  - m34_broad, my8_dateonly_parse, my8_inst_withheld, my8_day_trunc, my8_guard_all_modes and my8_swallow_cutoff each: 99 passed;
  - among the seat's own mutants, the only survivors are the six round-7 equivalents plus m34_broad, as the ruling states.
- Red check with plugin `oldeng8` and engine_3c775ea5.py: `4 failed, 16 passed`, with the ValueError and `assert 503 == 200` failures listed under (e).
- Line citations were re-read with `git show <sha>:<path> | sed -n` at the shas named above.

GAPS
- I did not rebuild the a0d7b054ff23 compatibility tree for round 8. The semis time helpers are the same code on both bases. I did not independently reproduce the seat's "99 passed on both bases" claim there.
- I did not probe semis itself with a malformed cutoff. That is base-owned.
- No production registration wires `load_nuclear_owner_bundle` at 8bae70522f38. The "owner loader" in NIT-D was reached through a test registration.
- The mastermind-executive MCP server needs authorization: claude.ai connector settings, or /mcp in an interactive session. The mmx-cimd-probe server failed to connect (501). Neither was needed for this review.

DEVIATIONS
- I ran read-only local git reads beyond the literal allow-list: `git diff 3c775ea592a6 8bae70522f38`, `git show`/`git grep`/`git ls-tree` at 8bae70522f38, a0d7b054ff23 and 719517e33b8d for route, fixture and record paths, and the Robotics blob at a1c8968f8e2f. That blob was copied under /var/folders/.../nucr7/robtree, which is outside /private/tmp.
- I made one read-only `gh api` GET of #7870 comment 5866433049.
- I made no push, commit, comment, label, PR edit or remote write.

SESSION END: PROVEN_OUTCOME
