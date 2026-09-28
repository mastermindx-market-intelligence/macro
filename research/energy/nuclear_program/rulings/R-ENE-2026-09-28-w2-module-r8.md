# R-ENE-33..34 — Energy nuclear module, round 8 (the review clock pinned; an unreadable review time is withheld, not failed)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-28. PR #8002 at `3c775ea592a683d9265e5c67ce438f4322f72cd6` (round 7).
- Triggers, in order:
  - The round-7 closure check (`../reviews/OPUS-REVIEW-2026-09-28-w2-module-r7-closure.md`, the same independent Opus reviewer) returned **ACCEPT_WITH_NITS**.
    - R-ENE-31 and R-ENE-32 are closed. There is no BLOCKER or MAJOR in the three changed files.
    - It raised one MINOR on the seat's records and relay, and four NITs.
  - #7870 stayed at `a0d7b054ff23`. Energy posted its relay as comment 5866433049, and nothing was posted after it before this ruling.

## Disposition of the round-7 closure findings

| Finding | Disposition |
|---|---|
| **MINOR-1.** Robotics' `known_revisions` is not count-only, so the r7 reversal of "(6b) relay-only" rested on a false premise. | Accepted. The r6 and r7 records are corrected at source in the same commit as this ruling. The relay went to #7870 as comment 5866433049 item 4: effects (a) and (b), with R-ENE-31's construction as the reference fix. Whether (c) is a Robotics defect is the owner's call. Nuclear's code is unaffected. |
| **NIT-1.** The reviewer retracts its own round-6 line-number NIT: `:1300` was correct. | Accepted. The `:1298-1299` erratum is withdrawn at source in the r6 ruling, the r7 ruling, the r6 closure record and the handoff. It was dropped from the #7870 post, which says relay 5832062081 stands as posted. |
| **NIT-2.** The `_reviewed_by_cutoff` contract is unpinned on four axes, and the absent count has no positive control of its own. | Accepted. This is **R-ENE-33**. |
| **NIT-3.** Two wording points at r7 :36 and :39. | Accepted. Both are corrected at source in the r7 ruling. |
| **NIT-4.** A replay block with `reviewed_at=''` fails the whole request with HTTP 503. This is pre-existing and shared with the base. | Accepted. **R-ENE-34** is the nuclear-local guard. The base defect was relayed as 5866433049 item 5. |

## R-ENE-33 — the review clock is pinned (round-7 closure NIT-2)

**Finding (reviewer, confirmed by the seat).** R-ENE-31 item 2 states the contract of `_reviewed_by_cutoff`. Four of the reviewer's mutants survived it with `89 passed`, and each one answers differently from the head on a concrete input:

| Axis | Mutant | Input where the head and the mutant differ |
|---|---|---|
| A block reviewed ON the cutoff day is shown (`<=`, not `<`) | `my_helper_lt` | `reviewed_at="2026-12-31"`, recorded cutoff `2026-12-31` |
| A non-string `reviewed_at` is withheld | `my_nonstr_reviewed` | `reviewed_at=None` |
| The review time is read against `recorded_cutoff`, not `source_cutoff` | `my_helper_source_cutoff` | source cutoff `2026-06-30T00:00:00Z`, recorded cutoff `2026-12-31`, review `2026-09-20` |
| Only `system_replay` reads the review time | `my_helper_cutoff_any_mode` | `source_history` with recorded cutoff `2026-12-31` and review `2027-01-15` |

The absent count (`test_a_replay_never_counts_a_block_reviewed_after_its_cutoff`) had no positive control of its own.

**Ruling.** There is no engine change for R-ENE-33, because the behaviour was already correct. Five pins are appended to `tests/test_nuclear_research_interpretation_scope.py`:

- `test_a_replay_counts_an_unknown_input_block_reviewed_by_its_cutoff`: the count's positive control;
- `test_a_replay_shows_a_block_reviewed_on_its_cutoff_day`;
- `test_a_replay_reads_review_time_against_the_recorded_cutoff`;
- `test_only_a_system_replay_reads_review_time`;
- the non-string axis is the `None` case of R-ENE-34's parametrized test.

## R-ENE-34 — an unreadable review time is withheld, not failed (round-7 closure NIT-4)

**Finding (reviewer, confirmed by the seat).** In a `system_replay`, a block whose `reviewed_at` is a string that does not parse (`''`, `'not-a-date'`, `'2026-13-45'`) reaches `_le` (`semiconductor_theme_research.py:154`), which raises `ValueError`. The route's catch-all turns that into HTTP 503 for the WHOLE request, while `latest` returns 200 for the same bundle.
- The defect is pre-existing: it was the same at `e31e2db3702a`.
- Semis (`:323-325`) and Robotics (`:538-541`) share the path.
- It contradicts the route's own comment at `app/theme_research.py:384-388`, which says to withhold a malformed row and never answer 503.

**Why nuclear-local AND a relay.** `_le` and the route belong to the base owner (R-ENE-09), so the base fix is theirs: 5866433049 item 5. Nuclear's own helper is what calls `_le` on the block's clock, so nuclear guards its own call.

**Ruling.** `_reviewed_by_cutoff` parses the block's review time with `_parse_day` before comparing. On `ValueError` it returns False, so the block is withheld exactly like one with no review time: not shown, and not counted. Only the block's clock is parsed. A malformed QUERY cutoff is not swallowed here and still surfaces through the base (see the queued relay below). The engine change is these lines, at `8bae70522f38:engine/market_ontology/nuclear_theme_research.py:334-340` (the helper starts at :328):

```python
        try:
            _parse_day(reviewed)
        except ValueError:
            # An unreadable review time is withheld like a missing one. Only the
            # block's clock is read here, so a bad query cutoff still surfaces.
            return False
        return _le(reviewed, self.query.recorded_cutoff)
```

- Every string that `_parse_day` accepts is one that `_le` also parses (`semiconductor_theme_research.py:141-163` at `a0d7b054ff23`). `_le` reads the value through `_parse_day` when it is date-only and through `_parse_clock` when it is an instant, and for an instant `_parse_day` is `_parse_clock(...).date()`. So, with a well-formed cutoff, the guard cannot let through a value that `_le` then rejects.
- **Latent today.** The owner loader sends `interpretation_blocks=()` (`nuclear_owner_bundle.py:41`), so no served payload changes.

**Tests (append-only, R-ENE-19).**
- `tests/test_nuclear_research_interpretation_scope.py`: `test_a_replay_withholds_a_block_without_a_readable_review_time`, parametrized over `None`, `''`, `'not-a-date'` and `'2026-13-45'`. Each case asserts that the block is neither shown nor counted.
- `tests/test_nuclear_research_route.py`: `test_a_replay_withholds_an_unreadable_review_time_instead_of_failing`, with cases `("2026-09-20", True)` and `("", False)`. Each case asserts HTTP 200, `no-store`, `noarchive`, and that the block's text is served exactly when its review time is readable.
- **R-ENE-19 compliance.** No test is deleted or renamed, and no data fixture is reshaped. The route file's `client` helper gains an optional `registration` argument whose default reproduces its current behaviour exactly, and the file gains `import dataclasses`.

**Documented residual: `m34_broad`.** This mutant moves the `try` around `_le` itself, so a malformed query cutoff is swallowed too. It survives, and it is left unpinned on purpose:
- It is observable only with a malformed query `recorded_cutoff` AND no assertion reaching nuclear's time gate. Any assertion that reaches `_passes_time_mode` (nuclear :199) raises first, at `semiconductor_theme_research.py:236`.
- The only test that could kill it would pin today's 503 for a malformed user cutoff. That 503 is the base defect relayed below, and the pin would fight the base's fix (a 400).

## Queued base relay (next #7870 post): a malformed replay cutoff answers 503, not 400

- `_QueryBody.source_cutoff` and `recorded_cutoff` are bounded only by length (`app/theme_research.py:197-198`), and `_validate_query` never parses them.
- Seat probe (`r8gate/probe_cutoff400.py`, nuclear on the `a0d7b054ff23` compat tree):
  - `'2026-12-31'` gives 200;
  - `'not-a-date'` and `'2026-13-45'` give 503 `{"error":{"code":"service_unavailable","action":"retry_later"}}`.
- The client is told to retry a request that can never succeed.
- Suggested fix, which is the owner's call: parse both cutoffs in `_validate_query` and refuse with 400.
- Semis was not probed. The instrument's positive control did not fire there, so that result is void, not clean.

## Seat verification (sim `r8gate/`)

- **Suites.** The round-8 tree gives `99 passed` both on the `a0d7b054ff23` compat tree and on the frozen snapshot base. The route file gives `4 passed`.
- **Red check.** The round-7 engine (`95aa6b2a68923ffe…`) with the round-8 tests gives `4 failed, 95 passed`. The four are `withholds['']`, `withholds['not-a-date']`, `withholds['2026-13-45']` and the route's `[-False]`.
  - The `None` case and the four R-ENE-33 pins pass before and after, because the behaviour was already correct. They exist to kill mutants.
- **Mutant matrix** (`r8gate/mutplug8.py`, `matrix8.sh`): 59 mutants (round 7's 50 plus 9 new), 52 killed. The 7 survivors are round 7's 6 equivalents plus `m34_broad` (above).

  | New mutant | Failing tests |
  |---|---|
  | `m33_lt` | 1: `on_cutoff_day` |
  | `m33_nonstr` | 1: `withholds[None]` |
  | `m33_source_cutoff` | 1: `reads_review_time_against_the_recorded_cutoff` |
  | `m33_any_mode` | 1: `only_a_system_replay_reads_review_time` |
  | `m33_no_mode` | 12 |
  | `m34_no_guard` | 4: the three unreadable strings and the route's `[-False]` |
  | `m34_show` | 4: the same four |
  | `m34_parse_cutoff` | 4: the same four |
  | `m34_broad` | 0: the documented residual |

- **Lane.** `ene_w2_nuclear_module_r8fix` is a transcription BY SCRIPT on mb.
  - The seat-authored `apply_r8.py` (sha256 `e7e4f15b9bf91f53…`) refuses unless its inputs are the `3c775ea592a6` bytes: engine `95aa6b2a68923ffe…`, scope test `17985e086d3e39f2…`, route test `13c06dd126f43125…`.
  - It also refuses to leave anything behind unless all three outputs match the seat tree: engine `3a795c54c70e3a08…`, scope test `55f5580590aeea2d…`, route test `dff63c3926ef02a6…`.
- **Lane result (2026-09-28 08:57Z).** The lane delivered `3c775ea592a6..8bae70522f38f251e224cdf81a0a975710be9be0`. The seat's post-lane gate (`r8gate/postlane8.sh`) confirmed all of the following:
  - one commit, carrying the packet's exact subject;
  - exactly the 3 paths, each byte-identical to the seat tree;
  - `99 passed` both over the frozen snapshot base and on the `a0d7b054ff23` compat tree, and route `4 passed` on each;
  - pyflakes clean;
  - on the compat tree, the matrix survivor set equals the 6 equivalents plus `m34_broad` exactly;
  - #8002 is still DRAFT, with no labels and a null auto-merge;
  - no nuclear commit reached main.
- Closure goes to the same independent reviewer carrier.
