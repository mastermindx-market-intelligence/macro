# R-ENE-37..39 — Energy nuclear module, round 10 (the guard docstring rescoped; the review-clock boundaries and an ISO-only cutoff pinned)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-28. PR #8002 at `992cfa4bf09146cc454ec5cddd2aedcb7636f6a3` (round 9).
- Triggers, in order:
  - The round-9 closure check (`../reviews/OPUS-REVIEW-2026-09-28-w2-module-r9-closure.md`, the same independent Opus reviewer) returned **ACCEPT_WITH_NITS**.
    - Round 9 is correct as delivered, and there is no BLOCKER, MAJOR or MINOR.
    - It raised five NITs (1 to 5) and five observations (O1 to O5).
  - #7870 stayed at `a0d7b054ff23`. The Robotics seat's comment 5868610048:
    - confirmed Energy's REG-PACKET §3b.1 reading (its ruling 13);
    - supported item 7's fix shape;
    - asked #7870's owner again, after its 5866368947, for a joint answer on `object.subject_role`.

## Disposition of the round-9 closure findings

| Finding | Disposition |
|---|---|
| **NIT-1.** The docstring's R-ENE-35 sentence overstates the engine. | Accepted. This is **R-ENE-37**, which rescopes the docstring. The same wording is annotated at source: in the r9 ruling (its title, the R-ENE-35 ruling paragraph, the quoted docstring) and in the handoff's `changed` entry for that ruling. |
| **NIT-2.** Four review-clock gap mutants survive. | Accepted. This is **R-ENE-38**, which carries the reviewer's five cases. The handoff's "The instant review clock is pinned" is annotated with its round-9 scope. |
| **NIT-3.** The relay's prose overreaches in three places, and the records copy it. | Accepted. The relay is corrected on the next #7870 post with substance, comment 5869344590 (below). The copies are annotated at source, quoting the old text: in the handoff, the verified relay claim, the malformed-cutoff `unresolved` item, the queued-relay paragraph and section 16's item 7; the r8 ruling's queued-relay correction; the r9 ruling's trace bullet; and the r8 closure record's NIT-D sentence, which carries the reviewer's own amendment. |
| **NIT-4.** The handoff's guard-escape sentence drops "against a well-formed cutoff". | Accepted. Annotated at source, in section 16 and in the `changed` entry for the r8 closure record. |
| **NIT-5.** R-ENE-35 stops observing the guard once the base validates, and an ISO-parser validator makes that a real hole. | Accepted. Nuclear's half is **R-ENE-39**. The base half, validate with `_parse_day`, went to #7870 in comment 5869344590. |
| **O1.** #8148 is already merged. | Noted. The corrections ride this records PR. |
| **O2.** The r9 ruling cites the handoff at its parent's line numbers. | Corrected at source: the citation now names both places by string. |
| **O3.** The relay's `source_history` 503 row stands. | Noted. No change. |
| **O4.** Two more silent 200s: `source_history` and `latest` with a malformed `recorded_cutoff`. | Base-owned, and refined by the seat's own finding (below): both answer 503 once an assertion carries a `review_due_at`. The corrected relay names it. |
| **O5.** The six persistent survivors are the recorded equivalents. | Noted. Nothing needs reclassifying. |

## R-ENE-37 — the guard's docstring says what the engine does (round-9 closure NIT-1)

**Finding (reviewer, confirmed by the seat).**
- The guard reads only the block's clock to judge readability, then compares a readable review time with the cutoff: `return _le(reviewed, self.query.recorded_cutoff)` in `nuclear_theme_research.py`.
- A block with no review time, an empty one or an unreadable one is withheld before the cutoff is read. If nothing else reads the cutoff, such a query succeeds.
- "A review on the cutoff day is by the cutoff" holds only when either side is date-only. Against an instant cutoff, a later instant on the same day is not by the cutoff, which the file already pins at `…T23:00:00Z`.

**Ruling.** There is no engine change. The docstring's closing sentences are rescoped the way the test name is.

Before, at `992cfa4bf091`:

```
time the same way (R-ENE-34). Only a replay reads the review time, and only
against the recorded cutoff; a review on the cutoff day is by the cutoff
(R-ENE-33). An instant review time is readable, and against an instant cutoff
it compares as an instant (R-ENE-36). The guard reads only the block's clock,
so a malformed query cutoff still fails the query instead of withholding the
block (R-ENE-35).
```

After, at `3a7e6582feb1`:

```
time the same way (R-ENE-34). Only a replay reads the review time, and only
against the recorded cutoff; when either side is date-only, a review on the
cutoff day is by the cutoff (R-ENE-33). An instant review time is readable,
and against an instant cutoff it compares as an instant (R-ENE-36). The guard
judges readability from the block's clock alone; wherever it then compares a
readable review time with the recorded cutoff, a malformed cutoff raises
instead of withholding the block (R-ENE-35).
```

- The surviving `n9_cutoff_parse_outside_try` parses the cutoff before the readability check, which is the behaviour the old sentence described.
- The reviewer classes it EQUIVALENT under a `_parse_day` base fix, and today as evidence for NIT-1 rather than a pin request. It stays a documented survivor.

## R-ENE-38 — the review clock's boundaries are pinned (round-9 closure NIT-2)

**Finding (reviewer, confirmed by the seat).** Round 9 pinned the instant clock only with two Z-suffixed reviews off the boundary, 11:00Z and 23:00Z against a 12:00Z cutoff. Four mutants survived the 110-test suite. The inputs and outcomes below are the reviewer's (`probe_d9`); the last column is the seat's round-10 matrix.

| Mutant | Input (cutoff, review time) | Head | Mutant | Killed at `3a7e6582feb1` by |
|---|---|---|---|---|
| `n9_lt_instants` | 12:00Z, `2026-12-31T12:00:00Z` | shown | withheld | `instant_cutoff[2026-12-31T12:00:00Z]` |
| `n9_drop_offset` | 12:00Z, `2026-12-31T19:00:00+08:00` (11:00Z) | shown | withheld | `instant_cutoff[2026-12-31T19:00:00+08:00]` |
| `n9_drop_offset` | 12:00Z, `2026-12-31T08:00:00-05:00` (13:00Z) | withheld | shown (a leak) | `instant_cutoff[2026-12-31T08:00:00-05:00]` |
| `n9_eod_synthesis` | 12:00Z, `2026-12-31` | shown | withheld | `date_review_time_against_an_instant_cutoff_by_day[2026-12-31]` |
| `n9_parse_clock_guard` | `2026-12-31`, `20260920` or `2026-W38-7` | withheld | raises `ValueError` (route 503) | `withholds_a_block_without_a_readable_review_time[20260920]` |

**Ruling.** There is no engine change. The five cases:
- The instant parametrize gains `("2026-12-31T12:00:00Z", SUPPORTED)`, `("2026-12-31T19:00:00+08:00", SUPPORTED)` and `("2026-12-31T08:00:00-05:00", [])`.
- One test is appended, `test_a_replay_reads_a_date_review_time_against_an_instant_cutoff_by_day`. Against recorded cutoff `2026-12-31T12:00:00Z`, a block reviewed `2026-12-31` is shown and one reviewed `2027-01-01` is withheld.
- `test_a_replay_withholds_a_block_without_a_readable_review_time` gains `"20260920"`.

Two deviations from the reviewer's letter, both deliberate:
- The date-only case sits in its own test with a negative twin, not in the instant parametrize, because that test's name says "instant review time". It pins the base's date-against-instant branch, as the reviewer noted.
- `20260920` extends the existing withhold test instead of adding a new one. That test already asserts both properties the reviewer named: the block is not shown, and it is not counted absent.

The `20260920` kill needs Python 3.11 or later, because older `fromisoformat` rejects the basic format. CI runs 3.12.13, and the seat re-ran the suite under 3.12.13.

## R-ENE-39 — the malformed-cutoff pin survives an ISO-parser base fix (round-9 closure NIT-5)

**Finding (reviewer, confirmed by the seat).**
- Once the base validates cutoffs, both of R-ENE-35's values are refused before they reach the guard. The pin then observes the base's refusal (`ResearchRefusal` subclasses `ValueError`), and the swallow mutants survive.
- With a `_parse_day` validator that is harmless: a cutoff `_parse_day` accepts is one `_le` parses, so the mutants become equivalent by construction.
- With a `fromisoformat` validator it is a hole. `20261231` and `2026-W53-4` pass `datetime.fromisoformat` but not `_parse_day`, so they reach the guard.

**Ruling.** `"20261231"` joins the parametrize of `test_the_review_guard_never_swallows_a_malformed_replay_cutoff`. The seat measured it with `matrix10.sh` (`-p mp9r -p bf9r`) on the seat tree, which is byte-identical to the delivered files over `a0d7b054ff23`:

| Simulated base fix | `m34_broad` | `my8_swallow_cutoff` |
|---|---|---|
| none | killed by all three values | killed by all three values |
| replay-only, `_parse_day` | survives: EQUIVALENT by construction | survives: EQUIVALENT |
| every mode but `latest`, `_parse_day` | survives: EQUIVALENT | survives: EQUIVALENT |
| replay-only, `fromisoformat` | killed by `[20261231]` | killed by `[20261231]` |

- If the owner validates with `_parse_day`, record both mutants as EQUIVALENT at the rebase. Do not reopen them as a regression.
- The base half of NIT-5 went to #7870 (below).

## Seat finding — the review-expiry gate reads `recorded_cutoff` in every mode (refines O4)

**Finding (seat, 2026-09-28).** While drafting the relay correction, the seat read nuclear's other reader of `recorded_cutoff`.
- `_now_of_query` returns a supplied `recorded_cutoff` as the query's "now" in every mode. Only when none is supplied does it fall back to the latest `reviewed_at`.
- `_review_excluded` compares that now with the `review_due_at` of every assertion that is not held or rejected: `_le(due, now)`.
- Probe (`r10gate/probe_now_of_query.py`, at the engine): in `latest` and in `source_history`, a malformed `recorded_cutoff` with an assertion that carries a `review_due_at` raises a bare `ValueError`. The route's catch-all answers that as 503. Without a `review_due_at`, the same query succeeds.
- So O4's two silent 200s hold only for bundles whose assertions carry no `review_due_at`. The corrected relay names this reader.

**The 117-test suite does not observe it.** The seat built three mutants (`r10x/mk.py`, `r10x/mk_now.py`), and all three pass all 117 tests on the seat tree, under Python 3.12.13:

| Mutant | What changes |
|---|---|
| `expiry_swallow_serve` | a `ValueError` from `_le(due, now)` counts as not expired, so the assertion is served |
| `expiry_swallow_withhold` | a `ValueError` counts as expired, so the assertion is withheld |
| `now_replay_only` | a supplied `recorded_cutoff` is the expiry clock only in `system_replay` |

**A candidate pin, not yet delivered** (`r10x/cand_r11.py`, meant to be appended to `tests/test_nuclear_research_review_gate.py`):
- a positive control: with recorded cutoff `2026-12-31` in `latest` and in `source_history`, a due time of `2026-12-31T00:00:00Z` marks `review_expired_present`, and `2027-01-01T00:00:00Z` does not;
- the pin: a malformed recorded cutoff (`not-a-date`, `2026-13-45`, `20261231`) in both modes, with a due time of `2027-01-01T00:00:00Z`, raises `ValueError`.

| Run (candidate only, 10 cases) | head | `expiry_swallow_serve` | `expiry_swallow_withhold` | `now_replay_only` |
|---|---|---|---|---|
| no base fix | 10 passed | 6 failed | 6 failed | 8 failed |
| replay-only `_parse_day`, and replay-only `fromisoformat` | 10 passed | 6 failed | 6 failed | 8 failed |
| every mode but `latest`, `_parse_day` | 10 passed | 3 failed | 3 failed | 5 failed |

- Under every simulated fix the `latest` cases still kill, and head stays green, because the pin asserts only `pytest.raises(ValueError)`.
- **A trap met on the way.** The seat's first draft used date-only due times. The shared curation assertion refuses those (`CurationAssertionError`, a `ValueError`), so the raise cases "passed" on every mutant for the wrong reason. The positive control is what exposed it, and it stays in the candidate for that reason.

**Disposition.** The candidate is with the same reviewer for a pre-review. It is ruled as R-ENE-40 and delivered as round 11, together with any test-only finding from the round-10 closure. Until then the gap is open and recorded here.

## The #7870 post (NIT-3 relay correction, NIT-5 parser note)

Posted as comment 5869344590 at 11:56:10Z, after the carrier fence. The fence read:
- the Slack root, with no thread message since 08:00Z;
- #7870, with no comment created or edited since 5868610048;
- #8002 at `3a7e6582feb1`: DRAFT, no labels, auto-merge null, no comments or reviews.

It carries:
- the status line: #8002 at `3a7e6582feb1`, with `117 passed` and route `4 passed` on `a0d7b054ff23`, including under 3.12.13;
- item 7's fix shape: validate with `_parse_day`, the parser `_le` uses, not `fromisoformat`, which accepts `20261231` and `2026-W53-4`;
- the correction to 5868018569:
  - the 400 claim holds within the 32-character bound only;
  - nuclear's replay review guard and its review-expiry gate are two more readers;
  - the 200 differs from the control at `.generation` and echoes the value at `.request.recorded_cutoff`;
  - the corrected sentence, and the consequence that a replay-only validator leaves the expiry gate's 503 in `latest` and `source_history`;
- Energy's constraint on the v1.1 `object.subject_role` request:
  - nuclear already defers a direction to it;
  - keep it optional, with absence meaning "no direction", because nuclear validates every bundle assertion against an `object` block that is `additionalProperties: false`;
  - Energy has no sequencing preference.

The same body refresh gives #8002 row 9's closure, row 10, and the corrected base report.

## Tests (append-only, R-ENE-19)

- One file changes: `tests/test_nuclear_research_interpretation_scope.py`.
  - The docstring's closing sentences are rewritten (R-ENE-37), as quoted above. That is the only edit that is not an append.
  - Three parametrizes gain cases (R-ENE-38 twice, R-ENE-39 once), and one test is appended (R-ENE-38).
- That is 7 new cases: the scope file's node ids go from 27 to 34, and none is removed.
- No test is deleted or renamed, and no fixture is reshaped. The engine and the route test are unchanged.
- The nuclear suite goes from `110 passed` to `117 passed`.

## Seat verification (sim `r10gate/`)

- **Suites.** The round-10 tree gives `117 passed`, and the route file `4 passed`, in each of these runs:
  - on the frozen snapshot base;
  - on the `a0d7b054ff23` compat tree;
  - under Python 3.12.13 as well as 3.14.7.
  - Under three simulated base fixes, it gives `117 passed` each. The fixes are replay-only, every mode but `latest`, and replay-only with `fromisoformat`.
  - pyflakes is clean.
- **No red check.** The head was already correct, so the new pins pass before and after. The matrix is the evidence.
- **Matrix totals.** 81 mutants: round 9's 68, plus the reviewer's 13 `n9_` mutants.
  - 72 are killed, including all four NIT-2 gap mutants, by the cases in the R-ENE-38 table.
  - The 9 survivors are round 7's six equivalents: `role_pred`, `r9_reason_review_ok`, `r9_status_review_ok`, `my_continue_past_pointer`, `my_no_seen` and `my_prefix_from_served`.
  - The other three carry the reviewer's classes:
    - `n9_utc_day` is a GAP deferred to the base, because it is the base's local-day question (O1 in the r9 ruling);
    - `n9_mode_whitelist` is EQUIVALENT under the route contract;
    - `n9_cutoff_parse_outside_try` is EQUIVALENT under a `_parse_day` base fix.

## Lane

- `ene_w2_nuclear_module_r10fix` is a transcription BY SCRIPT on mb.
  - The seat-authored `apply_r10.py` (sha256 `86510d5893391b5c…`) refuses unless its inputs are the `992cfa4bf091` bytes: engine `3a795c54c70e3a08…`, scope test `f0c4042b3f65d4bd…`, route test `dff63c3926ef02a6…`.
  - It also refuses to leave anything behind unless its output scope test matches the seat tree (`fa529ab81e730136…`) and the engine and route test are unchanged.
- **Lane result (2026-09-28 11:45Z).** The lane delivered `992cfa4bf091..3a7e6582feb173f0dd88ff21291c8869907d3774` (committed 11:42:24Z, 311 s wall, verdict `REVIEW_DEFERRED`). The seat's post-lane gate (`r10gate/postlane10.sh`) confirmed all of the following:
  - one commit, carrying the packet's exact subject;
  - exactly 1 path, the scope test;
  - the scope test and the unchanged engine and route test are byte-identical to the seat tree;
  - no test name or node id was removed (R-ENE-19);
  - `117 passed` over the frozen snapshot base and on the `a0d7b054ff23` compat tree, and under each simulated base fix;
  - route `4 passed` on each base;
  - pyflakes clean;
  - on the compat tree, the matrix survivor set equals the documented 9 exactly (81 mutants);
  - #8002 is still DRAFT, with no labels and a null auto-merge;
  - no nuclear commit reached main.
- The lane left the PR body stale, because its ruling forbade `gh pr edit`. That is by design; the seat refreshed the body after the carrier fence.
- Closure goes to the same independent reviewer carrier, with the R-ENE-40 candidate in scope.
