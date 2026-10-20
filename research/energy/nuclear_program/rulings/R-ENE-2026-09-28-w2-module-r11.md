# R-ENE-40 — Energy nuclear module, round 11 (the replay review-expiry clock and the malformed-cutoff failure pinned)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-28. PR #8002 at `3a7e6582feb173f0dd88ff21291c8869907d3774` (round 10).
- Triggers, in order:
  - The round-10 closure check (`../reviews/OPUS-REVIEW-2026-09-28-w2-module-r10-closure.md`, the same independent Opus reviewer) returned three verdicts:
    - round 10: **ACCEPT**, no findings;
    - the seat's #7870 comment 5869344590: **FIX_REQUIRED**, with one MEDIUM, two NITs and three observations;
    - the R-ENE-40 candidate: **DELIVER_WITH_CHANGES**, with two MEDIUMs, two LOWs and the exact text to deliver.
  - #7870 stayed at `a0d7b054ff23`. The Robotics seat's comment 5869676610 (12:17:51Z) answered 5869344590 with no ask of Energy. #8153 (squash `fd072295de2e`) recorded that answer on main.

## Disposition of the round-10 closure findings

| Finding | Disposition |
|---|---|
| **Round 10 @3a7e6582: ACCEPT.** | Round 10 is closed. |
| **Post, MEDIUM.** "Missed two readers" and "a silent 200 otherwise" are false. Nuclear's target-window judgement is a third reader, and it reads `source_cutoff` in every mode. | Accepted and reproduced (below). Corrected on #7870 in addendum 5870740225, item 1. Annotated at source (list below). |
| **Post, NIT.** "`_parse_clock` accepts more than `_le` does" is wrong: neither set contains the other. | Accepted and reproduced. Addendum item 3. No record repeated the superset claim, so nothing is annotated for it. (The r10 ruling's post summary says only that `fromisoformat` accepts `20261231` and `2026-W53-4`, which is true.) |
| **Post, NIT.** The expiry gate reads only the selected assertions, and in a replay the base time gate reads a malformed `recorded_cutoff` first. | Accepted and reproduced (below). Addendum item 2. Annotated at source. |
| **OBS 1.** Nuclear's response schema `$defs/when` and `_parse_day`'s grammar do not match in either direction, and today's silent 200 already echoes schema-invalid cutoffs. | Accepted as Energy's own open item, with no ask of #7870 (the addendum's "No ask"). Aligning `$defs/when` to whatever grammar item 7 admits is a rebase step, added to the handoff's `unresolved` and `next_actions`. |
| **OBS 2.** A validator that skips `latest` leaves the third reader's 503 in `latest`. | Accepted. Addendum item 1, last sentence. |
| **OBS 3.** "Nuclear's pins pass under any choice" holds for validating, not for refusing. | Accepted. Addendum item 4 names the four tests that fail under refusal shapes. |
| **R-ENE-40, MEDIUM.** The candidate's docstring writes down an every-mode clock that R-ENE-18 left out of scope, and it claims more than the tests pin. | Accepted. The delivered docstring states the replay clock and, outside a replay, only the failure. |
| **R-ENE-40, MEDIUM.** The candidate's test (a) entrenches the unruled `latest`/`source_history` clock. | Accepted. Test (a) is dropped. |
| **R-ENE-40, LOW.** Six mutants survive the candidate. | Accepted. The new replay test kills all six. |
| **R-ENE-40, LOW.** Test (b) has no control of its own, and it builds its fixture inside `pytest.raises`. | Accepted. The delivered (b) asserts its own well-formed control (`selected == 1`) and builds the bundle and query outside `pytest.raises`. |

## R-ENE-40 — the replay review-expiry clock and the malformed-cutoff failure are pinned

**The finding (seat, round 10).** It is recorded in the r10 ruling, under "Seat finding — the review-expiry gate reads `recorded_cutoff` in every mode":
- `_now_of_query` returns a supplied `recorded_cutoff` as the expiry clock in every mode, and `_review_excluded` compares it with each selected assertion's `review_due_at`.
- The 117-test suite observed neither the clock nor its failure. Two swallow mutants and a replay-only clock mutant survived it.

**The candidate, and why it changed.** The candidate (seat scratch `r11gate/edits_r11_candidate.py`) had two parts:
- (a) a positive control: in `latest` and in `source_history`, a recorded cutoff of `2026-12-31` marks `review_expired_present` for a due time of `2026-12-31T00:00:00Z`, and not for `2027-01-01T00:00:00Z`;
- (b) a pin: a malformed recorded cutoff in both modes raises `ValueError`.

The reviewer raised four objections, and the seat adopted all four:
- **(a) pins a clock that no ruling chose.** R-ENE-18 left `_now_of_query` "out of scope and unchanged". The clock outside a replay is an accident of that function, not a contract.
  - (a) kills `e_now_replay_only` even under the every-mode `_parse_day` base fix. So the natural fix for the rewind hazard (below) would break the pin even when nothing is swallowed.
  - Under refusal-shaped item-7 fixes, (a) adds new failures: +4 under `refuse_unread`, +2 under `refuse_latest` and +4 under `refuse_rec_unread`.
- **The docstring overclaims.** The candidate's "In every mode, a supplied recorded cutoff is the now" writes that accident down. It also claims more than the tests pin: the replay clock itself was unpinned, since `e_now_not_replay` had 0 kills.
- **Six mutants survived the candidate:** `e_now_not_replay`, `e_now_source_cutoff`, `e_now_advance_only`, `e_now_date_only`, `e_due_trunc` and `e_now_trunc`.
- **(b) had no control of its own.** It leaned on (a) for its control and built its fixture inside `pytest.raises`. That is the shape of the round-10 trap.
  - With a date-only due time, the shared curation assertion refuses the fixture with a `ValueError`, so the raise "passes" for the wrong reason.
  - The reviewer measured this with `trap/test_trap.py`. The candidate's form passes vacuously under `e_swallow_serve`; the delivered form fails at its control.

**Ruling.**
- **A replay judges review expiry at its recorded cutoff.** This is in scope, and R-ENE-18 does not forbid it.
  - R-ENE-18 kept `_now_of_query` unchanged. Pinning what that function already does in a replay changes nothing.
  - A replay is the one mode whose contract names the recorded cutoff. It is the "as recorded by" clock of the base time gate and of the replay review guard (R-ENE-33, R-ENE-34).
  - The reviewer left this call to the seat ("If it does, drop R and keep B"). The seat keeps R.
- **Outside a replay, only the failure is pinned.** A malformed recorded cutoff supplied beside a record with a review due time raises, instead of serving or withholding that record. Which clock applies there stays unruled (R-ENE-18), and no test pins it.
- **The reviewer's exact text is delivered unchanged.** The reviewer's applier is `variant_r11d.py`; the seat's is `r11gate/edits_r11.py`. The seat checked that both produce the same bytes.
- **The docstring.** The module docstring's closing paragraph changes. Before:

  > A held, rejected or review-expired record never counts as coverage, never
  > changes a view's reason and never supports an interpretation block.

  After:

  > A held, rejected or review-expired record never counts as coverage, never
  > changes a view's reason and never supports an interpretation block. A replay
  > judges review expiry at its recorded cutoff, never at its source cutoff or
  > the newest review time. Outside a replay the gate also reads a supplied
  > recorded cutoff, because `_now_of_query` checks no mode; which clock applies
  > there is out of scope (R-ENE-18), so only the failure is pinned: a malformed
  > recorded cutoff supplied beside a record with a review due time raises
  > instead of serving or withholding that record (R-ENE-40).

- **The tests.** Appended to `tests/test_nuclear_research_review_gate.py`:

```python
EARLY = {"published_at": "2026-01-15", "observed_at": "2026-01-15T00:00:00Z",
         "retained_at": "2026-01-15T00:00:00Z"}


def replay_expired(recorded_cutoff, due):
    dated = variant("N04", "R11DUE", source=EARLY, review={
        **review("accepted", due), "reviewed_at": "2026-05-01T00:00:00Z"})
    later = variant("N04", "R11LATER", source=EARLY, review=review("accepted"))
    query = nuclear_query("nuclear_components", "economics", time_mode="system_replay",
                          source_cutoff="2026-06-30T00:00:00Z", recorded_cutoff=recorded_cutoff)
    payload = nuclear.compose_nuclear_research(query, nuclear_bundle(dated, later))
    return "review_expired_present" in payload["limitations"]


@pytest.mark.parametrize(("recorded_cutoff", "due", "expired"), [
    ("2026-12-31", "2026-12-31T23:00:00Z", True),
    ("2026-12-31", "2027-01-01T00:00:00Z", False),
    ("2026-12-31T12:00:00Z", "2026-12-31T12:00:00Z", True),
    ("2026-12-31T12:00:00Z", "2026-12-31T18:00:00Z", False),
    ("2026-07-31", "2026-08-01T00:00:00Z", False),
])
def test_a_replay_judges_review_expiry_at_the_recorded_cutoff(recorded_cutoff, due, expired):
    assert replay_expired(recorded_cutoff, due) is expired


@pytest.mark.parametrize("recorded_cutoff", ["not-a-date", "2026-13-45", "20261231"])
@pytest.mark.parametrize("time_mode", ["latest", "source_history"])
def test_the_expiry_gate_never_swallows_a_malformed_recorded_cutoff(time_mode, recorded_cutoff):
    bundle = nuclear_bundle(variant("N04", "R11DUE", review=review("accepted", "2027-01-01T00:00:00Z")))
    query = nuclear_query("nuclear_components", "economics", time_mode=time_mode)
    assert nuclear.compose_nuclear_research(query, bundle)["authorized_coverage"]["selected"] == 1
    malformed = dataclasses.replace(query, recorded_cutoff=recorded_cutoff)
    with pytest.raises(ValueError):
        nuclear.compose_nuclear_research(malformed, bundle)
```

- **Why the replay fixture looks like that.**
  - Its source is observed and retained on `2026-01-15`, inside the query's `source_cutoff` of `2026-06-30T00:00:00Z`. So the record passes the base time gate and reaches the expiry gate. A record observed after the source cutoff never does (see the reproduction below).
  - A second record, `R11LATER`, carries no due time and a review time of `2026-09-20`. That keeps the newest review time off every recorded cutoff in the table. A clock that falls back to the newest review time, or to the source cutoff, therefore answers differently in at least one case.

**What each test kills.** These are the reviewer's mutants, with no base fix; the full table is in the review record's EVIDENCE.
- **The replay test (R)** kills the six mutants that survived the candidate. It also kills `e_now_never_cutoff`, `e_now_rewind_only`, `e_expiry_strict` and `e_expiry_swapped`.
- **The failure test (B)** kills three groups, all on its `latest` and `source_history` cases:
  - the swallow mutants: `e_swallow_serve`, `e_swallow_withhold`, `e_swallow_latest_serve` and `e_swallow_sh_serve`;
  - the three malformed-fallback mutants;
  - `e_now_replay_only`, `e_now_not_latest` and `e_now_not_sh`.

  With R, it also kills `e_now_never_cutoff` and `e_expiry_swapped`.
- **Three survive, each classified:**
  - `e_swallow_replay_serve` is EQUIVALENT. Every assertion a replay admits has already passed the base time gate's `retained_at` comparison (semis `:236`), which raises on a malformed recorded cutoff first.
  - `e_now_eager_parse` fails closed and is left unpinned by design.
  - `e_now_min` changes the store clock, which is out of scope (R-ENE-18).

**Base shapes.** The reviewer modelled nine item-7 shapes: six validation shapes and three refusal shapes.
- Under all nine, the delivered text adds no failure. The head suite's existing failures under the refusal shapes (6, 2 and 4) are unchanged.
- R's kills persist under all nine. B's swallow kills become equivalent under the every-mode shape and the refusal shapes, where the base refuses the malformed cutoff before nuclear reads it.
- The seat reproduced three of the shapes on the delivered head: replay-only, every mode that carries cutoffs, and replay-only with an ISO parser.

**The remaining cost (INFO, accepted).** B also fails if the clock is later made replay-only, unless the base refuses or `_parse_day`-validates cutoffs in `latest` and `source_history`.
- The reviewer measured `e_now_replay_only` failing: 6 cases with no base fix, 3 under `all`, 4 under `sh_iso`, 2 under `every_iso`, and none under `every` or the refusal shapes.
- That is the intended tripwire. Without it, making the clock replay-only would turn a malformed cutoff into a silent 200.

## The rewind hazard (recorded, unruled)

The reviewer's probe P3 (round-10 closure, `probe_r10_py312.out`) measured the expiry clock outside a replay with *well-formed* cutoffs:
- In `latest` and `source_history`, a supplied recorded cutoff earlier than the store clock un-expires a review. Take a due time of `2026-09-19` with the newest review time at `2026-09-20`:
  - with no recorded cutoff, the record is withheld (`review_expired_present`);
  - with a recorded cutoff of `2026-09-18` or `1970-01-01`, it is served (`ready`, 1 selected).
- A later recorded cutoff does the reverse. A due time of `2027-01-01` is served with no recorded cutoff and withheld with `2099-12-31`.

So a caller outside a replay can move the expiry clock in either direction.
- R-ENE-18 keeps `_now_of_query` out of scope and unchanged. R-ENE-40 deliberately pins no clock there, so the natural fix, a replay-only clock, stays open.
- The hazard is recorded as an `unresolved` item in the handoff. It is decided at the rebase, together with item 7:
  - If the base refuses a recorded cutoff outside a replay (the `refuse_rec_unread` shape), the hazard closes at the base. The existing nuclear tests that fail under that shape (4, per the review record) change with it.
  - Otherwise, closing it changes the review clock. That needs a ruling that supersedes R-ENE-18's "unchanged" clause, and B then needs the base to validate cutoffs in `latest` and `source_history` (the remaining cost above).

## Seat reproductions

All run in `r11gate/newhead_a0d7` (the delivered head's #8002 files over #7870 `a0d7b054ff23`) under Python 3.12.13. Each output is saved beside its probe.

- **The third reader** (`probe_third_reader.py` → `.out`).
  - In `latest`, with target-bearing records in the slice, `source_cutoff` values `not-a-date` and `20261231` raise `ValueError`, at nuclear `:142` → semis `_parse_day` (`:151`). The well-formed `2026-12-31` selects 2.
  - In `source_history`, the same cutoffs raise earlier, at the base time gate (semis `:159`).
  - With no target in the slice, `latest` with `not-a-date` succeeds (1 selected).
- **The parsers** (the same probe). `20261231` and `2026-W53-4` parse under `_parse_clock` and raise under `_le`. `2026-1-5` and `２０２６-12-31` raise under `_parse_clock` and parse under `_le`.
- **The selection** (`probe_selection.py` → `.out`). This is `latest` and `source_history`, with a malformed recorded cutoff:
  - a due-carrying record outside the slice beside an undue record inside it succeeds (1 selected);
  - with the due-carrying record inside the slice, the query raises in `_parse_day`.
- **The replay raise site** (`probe_replay.py` → `.out`). The recorded cutoff is `not-a-date` in both cases:
  - With the plain N04 variant, observed `2026-09-20T00:00:00Z`, after the query's `source_cutoff` of `2026-06-30T00:00:00Z`, the replay returns a payload with 0 selected. The time gate drops the record on its availability before it reads the recorded cutoff.
  - With a record observed and retained on `2026-01-15`, inside the source cutoff, the same query raises at semis `:236`, the `retained_at` comparison, reached via nuclear `:199`. That is before the expiry gate.
  - The seat's first probe used the plain variant and did not reproduce the reviewer's claim. The in-window record did.

## The #7870 addendum (comment 5870740225)

Posted at 13:23:01Z, after the carrier fence. The fence read:
- the Slack root: no thread message since 08:00Z;
- #7870 at `a0d7b054ff23`: no comment created or edited since 12:17:52Z;
- #8002 at `3a7e6582feb1`: DRAFT, no labels, auto-merge null, no comments or reviews.

It is 4003 characters as served, and it carries:
1. the third reader: "missed three, all in nuclear", its line in the corrected sentence, and the fact that a validator that skips `latest` leaves its 503 there;
2. that the expiry gate reads only the selection, and a replay's 503 comes from the time gate;
3. that the parsers' accepted sets do not nest, and why `_parse_day` stays the recommendation;
4. validating versus refusing, naming the four tests a refusal can fail.

It also carries:
- "No ask": nuclear's `$defs/when`, which Energy aligns at the rebase;
- round 11's status: the replay clock and the failure, measured by the review across nine item-7 shapes, three of them reproduced by the seat;
- the standing line: items 1, 3, 5, 6 and 7 remain with #7870's owner, and item 1 is the only one nuclear needs.

## The Robotics relay (5869676610) and #8153 — no reply owed

- The Robotics seat adopted Energy's constraint: `object.subject_role` is OPTIONAL in v1.1, and its absence means "no direction".
- It measured two further facts:
  - the closed `object` block makes a direction unemittable today;
  - the curation-assertion schema exists only at `a0d7b054ff23`, so v1.1 is itself blocked on #7870.
- It accepted the item-7 correction, endorsed `_parse_day`, and ruled 14b to be robotics-only.
- #8153 (squash `fd072295de2e`) recorded this on main. Nothing asks Energy to act, so the seat did not reply.

## #7870, the critical path (measured 12:35Z)

- **Nuclear's dependency.** Nuclear needs 8 files that exist only on #7870:
  - `curation_assertion.py` and its v1 schema;
  - `theme_research_{registry,binding,mounts}.py`;
  - `semiconductor_{theme_research,owner_bundle}.py`;
  - `app/theme_research.py`.

  `rights.py` also differs between main and #7870.
- **#7870's state** at `a0d7b054ff23`: 21 checks pass, 4 skip and 1 is red, the chronic, non-binding `merge-queue-pilot`. It is 114 commits, 98 files and +33.8k lines past its merge-base. Its head has not moved since 2026-09-27 05:54Z.
- **The owner's checkpoint** says Semiconductor B is NOT_BUILT, with lanes in flight (T09-fix rights, T08c-2, T12, T11). It treats the Chairman and Astra's "Semiconductors builds the base out" direction as coordination relayed by peers, not as a scope grant.
- **The lever.** The seat surfaced it to the Chairman: a direct instruction to the Semiconductors seat to land the shared base as a slice, with the choice of slice left to that seat. Until then Energy stays parked behind #7870 (R-ENE-09).

## At-source corrections (2026-09-28, round-10 closure)

Each correction quotes the superseded text and points to addendum 5870740225:
- **The handoff:**
  - the `verified` relay claim;
  - the `unresolved` malformed-cutoff item;
  - the `unresolved` expiry-gate item, now resolved by round 11;
  - the danger item on malformed-cutoff probes;
  - section 17's summary of 5869344590.
- **The r8 ruling:** its correction "misses two nuclear readers".
- **The r8 closure record:** the seat's note on NIT-D.
- **The r10 ruling:**
  - the O4 row;
  - the seat finding's "every assertion";
  - the post summary's "two more readers".

## Tests (append-only, R-ENE-19)

- One file changes: `tests/test_nuclear_research_review_gate.py`, `+43 −1`.
  - The module docstring's closing paragraph is extended, as quoted above. That is the only edit that is not an append.
  - Two tests are appended, with a fixture dict and a helper: 5 replay cases and 6 failure cases.
- That makes 11 new cases. The file's node ids go from 9 to 20, and none is removed.
- No test is deleted or renamed, and no fixture is reshaped. The engine, the scope test and the route test are unchanged.
- The nuclear suite goes from `117 passed` to `128 passed`.

## Seat verification (sim `r11gate/`)

- **Byte reference.** `r11gate/edits_r11.py`, applied to the round-10 review-gate test (`abf611716b1fd390…`), gives `8993ae8eaa823a12…`. The reviewer's `variant_r11d.py` gives the same bytes.
- **Suites.** The round-11 tree gives `128 passed`, and the route file `4 passed`, in each of these runs:
  - on the frozen snapshot base;
  - on the `a0d7b054ff23` compat tree;
  - under Python 3.12.13 as well as 3.14.7;
  - under three simulated base fixes: replay-only, every mode that carries cutoffs, and replay-only with an ISO parser.

  pyflakes is clean.
- **Matrix.** 84 mutants: round 10's 81 plus the seat's three expiry mutants from round 10 (`x11_expiry_swallow_serve`, `x11_expiry_swallow_withhold`, `x11_now_replay_only`).
  - 75 are killed, all three expiry mutants among them, 6 failures each.
  - The 9 survivors are unchanged from round 10: round 7's six equivalents, plus `n9_utc_day`, `n9_mode_whitelist` and `n9_cutoff_parse_outside_try` in the reviewer's classes.
- **The reviewer's table.** It has 26 rows: 23 expiry-clock mutants, `m34_broad`, `my8_swallow_cutoff` and the unmutated control.
  - Each row's failure count is identical between the seat's verified tree and the lane's delivered tree, and matches the review record's table. For example, `e_expiry_swapped` fails 12: the head's 3, plus R×3 and B×6.
  - The three survivors are the classified three above.
- **The older mutants.** Under the ISO-parser fix, `20261231` still kills `m34_broad` and `my8_swallow_cutoff`. Under the `_parse_day` fixes both are EQUIVALENT by construction, as recorded in R-ENE-39.

## Lane

- `ene_w2_nuclear_module_r11fix` is a transcription BY SCRIPT on mb.
  - The seat-authored `apply_r11.py` (sha256 `4de85cc691605d7d…`) refuses unless its inputs are the `3a7e6582feb1` bytes: engine `3a795c54c70e3a08…`, scope test `fa529ab81e730136…`, route test `dff63c3926ef02a6…` and review-gate test `abf611716b1fd390…`.
  - It also refuses to leave anything behind unless its output review-gate test matches the seat tree (`8993ae8eaa823a12…`) and the engine, the scope test and the route test are unchanged.
- **Lane result (2026-09-28 13:28Z).** The lane delivered `3a7e6582feb1..508d8c206357287a5f8ff9d1596efc32b3749459` (committed 13:24:06Z, 310 s wall, verdict `REVIEW_DEFERRED`). The seat's post-lane gate (`r11gate/postlane11.sh`, run as `postlane11_run.sh` with the dispatch time `2026-09-28T13:22:53Z` filled in; exit 0) confirmed all of the following:
  - one commit, carrying the packet's exact subject;
  - exactly 1 path, the review-gate test;
  - all four files byte-identical to the seat tree;
  - no test name or node id removed (R-ENE-19);
  - `128 passed` over the frozen snapshot base and on the `a0d7b054ff23` compat tree, under each simulated base fix, and under Python 3.12.13;
  - route `4 passed` on each base;
  - pyflakes clean;
  - on the compat tree, a matrix survivor set equal to the documented 9 (84 mutants);
  - the reviewer's 26 rows, with failure counts identical to the seat's verified run;
  - #8002 still DRAFT, with no labels and a null auto-merge;
  - no nuclear commit on main.
- **The #8002 body** was refreshed at 13:37:28Z, after the carrier fence (Slack: no thread message; #7870: no comment since 13:23:02Z). It carries row 10's closure, row 11, the corrected base report and Energy's two open items. It is still DRAFT, with no labels and a null auto-merge.

## Round-11 closure

No separate closure review is owed.
- Round 11 delivers the reviewer's own measured text, byte for byte. The post-lane gate shows the delivered review-gate test is byte-identical to the seat tree that reproduces it.
- The reviewer already measured this text: `128 passed` under Python 3.12.13 and 3.14.7, 26 mutant rows and nine item-7 shapes. Its mutation-tested tree differed from the final only in docstring lines.
- The seat reproduced the suites, three of the base shapes and every row's failure count.
- The next review of nuclear's module comes at the rebase onto #7870's merged base.
