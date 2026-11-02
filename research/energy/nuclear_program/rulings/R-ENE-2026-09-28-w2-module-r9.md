# R-ENE-35..36 — Energy nuclear module, round 9 (a malformed query cutoff still fails the query; the instant review clock pinned)

**[Corrected 2026-09-28 (round-9 closure NIT-1): the title's "a malformed query cutoff still fails the query" holds only where the guard compares a readable review time with the cutoff. A block with no readable review time is withheld before the cutoff is read. See R-ENE-37 in `R-ENE-2026-09-28-w2-module-r10.md`.]**

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-28. PR #8002 at `8bae70522f38f251e224cdf81a0a975710be9be0` (round 8).
- Triggers, in order:
  - The round-8 closure check (`../reviews/OPUS-REVIEW-2026-09-28-w2-module-r8-closure.md`, the same independent Opus reviewer) returned **ACCEPT_WITH_NITS**.
    - R-ENE-33 and R-ENE-34 are closed, and there is no BLOCKER or MAJOR.
    - Vector (a) found no string that passes the guard and then makes `_le` raise against a well-formed cutoff.
    - It raised four NITs (A to D) and three observations (O1 to O3).
  - #7870 stayed at `a0d7b054ff23`. The Robotics seat answered Energy's 5866433049 as comment 5866989985:
    - RULING 13: a lazily loaded module enrols in both restart surfaces;
    - RULING 14: Robotics adopts R-ENE-31's shape as a re-land obligation;
    - item 2 agreed: Energy lands the nuclear registration itself.

## Disposition of the round-8 closure findings

| Finding | Disposition |
|---|---|
| **NIT-A.** The reason the r8 records give for leaving `m34_broad` unpinned is false. | Accepted. This is **R-ENE-35**, which pins it. The false reason is corrected at source in the r8 ruling and in the handoff's `do_not_redo` and `danger_areas`. |
| **NIT-B.** The instant review clock has no pins, and the scope test's docstring overclaims. | Accepted. This is **R-ENE-36**, which pins it and rewrites the docstring's closing sentences. |
| **NIT-C.** Four copies of the withdrawn line-number point are unmarked. | Accepted. They are annotated at source: the r6 closure record :16 and :209, the r7 ruling :9, and the handoff's count at :49. The r8 ruling's :16 claim that the withdrawal was complete is annotated too. |
| **NIT-D.** The queued relay's headline holds only when the bundle has content. | Accepted. The seat re-probed before posting, and the corrected relay went to #7870 as comment 5868018569, item 7 (below). The r8 ruling's queued-relay section and the handoff (:117, :616) are annotated at source. **[Corrected 2026-09-28 (round-9 closure O2): :117 and :616 are the handoff's lines at the parent `fbd78d1242a3`. The annotated places are the `unresolved` item that begins "A malformed cutoff in a user query" and the paragraph that begins "Queued for the next #7870 post"; locate them by those strings.]** |
| **O1.** `_le` reads an instant against a date-only cutoff on the instant's own local day. | Base-owned. The seat reproduced it and relayed it in 5868018569 as an observation with no ask. Nuclear inherits the owner's answer by construction. |
| **O2.** The r8 ruling cites semis `:141-163`, but the helpers span `:138-164`. | Corrected at source. |
| **O3.** The r8 ruling's R-ENE-19 bullet does not name the docstring edit. | Corrected at source. |

## R-ENE-35 — the review guard never swallows a malformed query cutoff (round-8 closure NIT-A)

**Finding (reviewer, confirmed by the seat).** The r8 ruling left the mutant `m34_broad` (the `try` moved around `_le` itself) unpinned. Its reason was that the only test able to kill it would pin today's 503, a status the base's fix turns into 400. That reason is false.

Take a replay whose `recorded_cutoff` is `'not-a-date'`, with one block that has a readable review time and cites a revision the query does not know:

| | Engine | Route |
|---|---|---|
| Head | raises `ValueError` | 503 |
| `m34_broad` | returns a payload | 200 |
| Simulated base fix (`ResearchRefusal('replay_cutoffs_required')`) | raises | 400 |

`ResearchRefusal` subclasses `ValueError` (`semiconductor_theme_research.py:121` at `a0d7b054ff23`). So an engine `pytest.raises(ValueError)` kills `m34_broad` and the reviewer's `my8_swallow_cutoff`, pins no HTTP status, and keeps passing after the base fix.

**Ruling.** There is no engine change. The contract is the one R-ENE-34 stated: the guard reads only the block's clock, so a malformed query cutoff still fails the query instead of withholding the block. **[Corrected 2026-09-28 (round-9 closure NIT-1): the guard reads only the block's clock to judge readability, then compares a readable review time with the cutoff (`return _le(reviewed, self.query.recorded_cutoff)`). A malformed cutoff fails the query wherever that comparison runs; a block with no readable review time is withheld before the cutoff is read. R-ENE-37 rescopes the docstring.]** One test is appended: `test_the_review_guard_never_swallows_a_malformed_replay_cutoff`, parametrized over `'not-a-date'` and `'2026-13-45'`.
- It builds one block with a readable review time, citing an input from another slice (`K1other_slice`) that the query does not know.
- For each of two bundles, one holding that out-of-slice assertion and one holding no assertion:
  - **positive control:** the well-formed replay counts the block absent, so the block does reach the review guard;
  - **pin:** the malformed replay raises `ValueError`.
- Neither bundle reaches nuclear's time gate. An in-slice assertion raises first, at `semiconductor_theme_research.py:236`, where `m34_broad` cannot be observed (reviewer E4).

**The base relay (NIT-D), corrected before it was posted.** The seat re-probed nuclear's route at `992cfa4bf091` over `a0d7b054ff23` (`r9gate/probe_r9_relay.py`). Every response carries `Cache-Control: private, no-store`.

| Request | Bundle with an in-slice record | Empty bundle |
|---|---|---|
| `system_replay`, `recorded_cutoff` `2026-12-31` (control) | 200 | 200 |
| `system_replay`, `recorded_cutoff` `not-a-date` or `2026-13-45` | 503 `service_unavailable`/`retry_later` | 200 |
| `system_replay`, `source_cutoff` `not-a-date` | 503 | 200 |
| `source_history`, `source_cutoff` `not-a-date` | 503 | 200 |

- The empty-bundle 200s carry exactly the limitations of the well-formed control, so the malformed cutoff leaves no trace. An empty bundle is what nuclear's own owner loader returns today. **[Corrected 2026-09-28 (round-9 closure NIT-3): "no trace" is false. Against the control, the 200 differs at `.generation` and echoes the malformed value at `.request.recorded_cutoff`; only the limitations match.]**
- A bare `ValueError` from `_le` reaches the route's catch-all (`app/theme_research.py:683-687` at `a0d7b054ff23`), which answers 503.
- A simulated fix that parses only the two replay cutoffs (`r9gate/basefix9.py`) turns every replay row into 400 `invalid_request`/`fix_request`. It leaves the `source_history` row at 503 and 200.
- **Posted** to #7870 as comment 5868018569, item 7, after the carrier fence (2026-09-28 10:20:50Z). It names the fix shape as the owner's call:
  - parse the cutoffs in `_validate_query`;
  - refuse with a code that `_RESEARCH_REFUSAL_MAP` (`:146-167`) maps to 400, because `_map_research_refusal` (`:170-179`) sends an unmapped code to 503;
  - cover `source_history`.
- The same comment carries O1 as an observation with no ask. It also answers the Robotics seat's 5866989985:
  - item 2 is agreed;
  - RULING 13 is already in REG-PACKET §3b.1, on both surfaces: the `update.sh:1261` regex and the `MUST_RESTART` row;
  - RULING 14 is noted.

## R-ENE-36 — the instant review clock is pinned (round-8 closure NIT-B)

**Finding (reviewer, confirmed by the seat).** R-ENE-33 pinned the review clock with date-only review times. Every review time in the base's own fixture is an instant: `tests/fixtures/semiconductor_theme_research/corrected_interpretation.json` at `a0d7b054ff23` carries `2026-03-05T00:00:00Z`, `2026-08-01T09:00:00Z` and `2026-08-13T00:00:00Z`. So the unpinned path is the format production uses. Four reviewer mutants survived with `99 passed`:

| Case | Input | Head | Surviving mutant |
|---|---|---|---|
| C3 | replay, `reviewed_at` `2026-09-20T00:00:00Z` | shows | `my8_inst_withheld` and `my8_dateonly_parse` withhold it |
| C4 | recorded cutoff `2026-12-31T12:00:00Z`, `reviewed_at` `2026-12-31T23:00:00Z` | withholds | `my8_day_trunc` shows it, leaking a post-cutoff review |
| C2 | `latest`, `reviewed_at` `''` | shows | `my8_guard_all_modes` withholds it |

The seat added two mutants of its own, and both survived the r8 tests:
- `m36_inst_cutoff_withheld` withholds every instant review time when the cutoff is an instant;
- `m36_parse_all_modes` runs the readability guard before the mode check.

The scope test's docstring said "R-ENE-33 pins the rest of that review clock", which claimed coverage the tests did not have.

**Ruling.** There is no engine change, because the head is correct on every input above. Three tests are appended:
- `test_a_replay_reads_an_instant_review_time`: a replay shows a block reviewed `2026-09-20T00:00:00Z`.
- `test_a_replay_compares_an_instant_review_time_with_an_instant_cutoff`: against recorded cutoff `2026-12-31T12:00:00Z`, a review at `2026-12-31T11:00:00Z` is shown and one at `2026-12-31T23:00:00Z` is withheld.
- `test_outside_a_replay_the_review_time_is_never_read`: `latest` and `source_history`, each with `reviewed_at` `None`, `''` and `'not-a-date'`, show the block.

The module docstring's closing sentences now state the contract instead of claiming coverage.

Before, at `8bae70522f38`:

```
time the same way (R-ENE-34). R-ENE-33 pins the rest of that review clock.
```

After, at `992cfa4bf091`:

```
time the same way (R-ENE-34). Only a replay reads the review time, and only
against the recorded cutoff; a review on the cutoff day is by the cutoff
(R-ENE-33). An instant review time is readable, and against an instant cutoff
it compares as an instant (R-ENE-36). The guard reads only the block's clock,
so a malformed query cutoff still fails the query instead of withholding the
block (R-ENE-35).
```

**[Corrected 2026-09-28 (round-9 closure NIT-1): the last two sentences above overstate the engine, and the R-ENE-33 sentence holds only when either side is date-only. The round-10 wording is quoted under R-ENE-37 in `R-ENE-2026-09-28-w2-module-r10.md`.]**

## Tests (append-only, R-ENE-19)

- One file changes: `tests/test_nuclear_research_interpretation_scope.py`.
  - Four test functions are appended, with 11 cases: 2 for R-ENE-35 and 9 for R-ENE-36.
  - The module docstring's closing sentences are rewritten, as quoted above. That is the only edit that is not an append.
- No test is deleted or renamed, and no fixture is reshaped. The engine and the route test are unchanged.
- The nuclear suite goes from `99 passed` to `110 passed`.

## Seat verification (sim `r9gate/`)

- **Suites.** The round-9 tree gives `110 passed` on the `a0d7b054ff23` compat tree and on the frozen snapshot base. The route file gives `4 passed`, and pyflakes is clean.
- **No red check.** The head was already correct, so the new pins pass before and after. They exist to kill mutants. The matrix is the evidence, read from the per-mutant outcomes at the lane head:

| Mutant | Source | r8 tests (`99`) | r9 tests (`110`): failing cases |
|---|---|---|---|
| `m34_broad` | seat, round 8 | survives | `never_swallows[not-a-date]` and `[2026-13-45]` |
| `my8_swallow_cutoff` | reviewer | survives | the same two |
| `my8_inst_withheld` | reviewer | survives | `reads_an_instant_review_time` and `instant_cutoff[…T11:00:00Z…]` |
| `my8_dateonly_parse` | reviewer | survives | the same two |
| `my8_day_trunc` | reviewer | survives | `instant_cutoff[…T23:00:00Z…]` |
| `my8_guard_all_modes` | reviewer | survives | four `never_read` cases: `latest` and `source_history`, each with `None` and `''` |
| `m36_inst_cutoff_withheld` | seat | survives | `instant_cutoff[…T11:00:00Z…]` |
| `m36_parse_all_modes` | seat | survives | all six `never_read` cases |

- **Matrix totals** (`r9gate/mutplug9.py`, `matrix9.sh`): 68 mutants.
  - They are round 8's 59, the reviewer's 7 and the seat's 2. Two of the reviewer's seven, `my8_count_never` and `my8_helper_false`, were already killed by the r8 tests.
  - With the r8 tests, 14 survive. With the r9 tests, 62 are killed.
  - The 6 survivors are round 7's six equivalents.
- **Base-fix compatibility.** Under the simulated base fix (`r9gate/basefix9.py`) the suite gives `110 passed`, so the new pins do not fight the owner's fix.

## Lane

- `ene_w2_nuclear_module_r9fix` is a transcription BY SCRIPT on mb.
  - The seat-authored `apply_r9.py` (sha256 `6ad420c0a20bd5e2…`) refuses unless its inputs are the `8bae70522f38` bytes: engine `3a795c54c70e3a08…`, scope test `55f5580590aeea2d…`, route test `dff63c3926ef02a6…`.
  - It also refuses to leave anything behind unless its output scope test matches the seat tree (`f0c4042b3f65d4bd…`) and the engine and route test are unchanged.
- **Lane result (2026-09-28 10:11Z).** The lane delivered `8bae70522f38..992cfa4bf09146cc454ec5cddd2aedcb7636f6a3`. The seat's post-lane gate (`r9gate/postlane9.sh`) confirmed all of the following:
  - one commit, carrying the packet's exact subject;
  - exactly 1 path, the scope test;
  - the scope test and the unchanged engine and route test are byte-identical to the seat tree;
  - no test name was removed (R-ENE-19);
  - `110 passed` in three runs: over the frozen snapshot base, on the `a0d7b054ff23` compat tree, and under the simulated base fix;
  - route `4 passed` on each base;
  - pyflakes clean;
  - on the compat tree, the matrix survivor set equals the 6 equivalents exactly (68 mutants);
  - #8002 is still DRAFT, with no labels and a null auto-merge;
  - no nuclear commit reached main.
- The lane reported one deviation: it left the PR body stale, because its ruling forbade `gh pr edit`. That is by design; the seat refreshes the body.
- Closure goes to the same independent reviewer carrier.
