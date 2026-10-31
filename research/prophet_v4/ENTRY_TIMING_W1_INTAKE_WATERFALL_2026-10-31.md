# Entry Timing W1 — candidate-episode intake waterfall and identity replay (2026-10-31)

**Status:** measurement only, authority none, outcome-blind. Produced by the Fable CEO seat under the
October 31 commission (completion brief packet 2: "Inventory how many rows had authentic clocks,
quote/basis and membership by session. Produce a waterfall with explicit denominators and refusal
classes before inspecting any formally gated outcome"). No outcome, price, grade, paired-race or
timing surface was read. Nothing in this note changes W0 (DONE), the B4 preregistration (#7751,
amendment A1), the W3 measurement ledger or any registered look.

**Revision r2 (after independent review round 1, verdict REVISE).** Round 1 found that mapped
turn_watch rows were binned by their trigger date, not by the session the intake read them on,
which invented sessions (for example a "2026-05-07" session of 19 turn_watch rows recorded on
2026-08-28) and inflated the session count to 60. This revision bins every turn_watch row, mapped
and refused, by the `data_session` of the turn_watch source document it was read from, recovered
through the row's `source_receipt`; the clock section below quantifies the correction. Totals and
the identity replay are unchanged by the correction.

**Reproduce (read-only):** `python3 scripts/report_us_candidate_episode_waterfall.py --git-history origin/main [--json]`
(tests: `tests/test_report_us_candidate_episode_waterfall.py`, 7 tests). The script reads the
SELECTED B1 generation named by `data/us_prophet_rank/episodes/HEAD.json`, the turn_watch source
documents under `data/us_prophet_rank/episode_inputs/turn_watch/` (tracked files, plus every
historical version reachable from the ref with `--git-history`, because the nightly rewrites
`<session>.json` in place), and the committed Data OS identity reference through the intake's own
reader (`load_identity_spine`); it writes nothing. Without `--git-history` the same table is
produced for the rows whose document is still tracked, and the rest are reported as
`unrecovered_turn_watch`, never binned by the trigger clock.

## Inputs

| Fact | Value |
|---|---|
| Selected B1 generation (HEAD.json at this checkout) | `peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9` |
| Events in the generation (mapped observations, `OPENED` + `OBSERVED`) | 15,511 (OPENED 1,087 = one per episode, all from turn_watch, the only source with a structural anchor; OBSERVED 14,424) |
| Suppression ledger rows (typed refusals, all sessions) | 72,814 |
| turn_watch source documents recovered by receipt | 77 distinct documents (54 commits of `episode_inputs/turn_watch/` on `origin/main`); every one of the 1,694 turn_watch events and 13,649 turn_watch suppressions resolved to a document (0 unrecovered) |
| Identity reference replayed against | `data/reference/vendor_aliases.parquet` `sha256:ff8a32df8e47d88149d8ac8d8ae54b9b117a3c44cd34cfcd57eebcf0de816306` (membership vendor: 1,941 rows; 3 carry a validity bound; principal `ingested_at` ingests 2026-08-13: 702, 08-21: 508, 09-04: 3, 10-11: 721, plus a 2026-10-07 ingest visible in history) |
| Reference the generation's Oct 25 nightly receipt was built against | `sha256:eeb880747bee9d23ff0c5714b608dda399997d567a61936b78b4e43231c9da31` (main at `e1e1b5d35`, 2026-10-24); that receipt is incremental (`mode: nightly`, 70 appended events, 2,072 inputs) and pins only the 10-25 run |

The denominator is `inputs = mapped + refused` per observation session, where the observation
session is the session on which the intake READ the row. A mapped row is one event in the episode
store; a refused row is one suppression-ledger row with its native typed reason. Rows are
observations, not distinct securities: a ticker refused on twenty sessions is twenty rows.

**Clock.** `candidate` and `doors` rows carry their session directly (`opened_session` for an
`OPENED` event, else the `occurred_at` date; `observation_session` for a suppression). `turn_watch`
rows do not: the intake stamps `occurred_at = known_at = min(trigger.last_date)`
(`engine/us_candidate_episode_intake.py`, turn_watch branch), the trigger clock, which can precede
the session the row was first read by months, and the ledger's `observation_session` for turn_watch
suppressions is not uniformly the document session either. Measured on this generation:

| Clock fact (turn_watch) | Count |
|---|---:|
| Mapped events recovered to their source document | 1,694 of 1,694 |
| … whose trigger date precedes the document session | 1,376 |
| Suppressions recovered to their source document | 13,649 of 13,649 |
| … whose ledger `observation_session` differs from the document session | 3,302 |

The first turn_watch document is 2026-08-26, so no session before 2026-08-26 exists in the
corrected table. **Consequence for W2:** a turn_watch event's `known_at` is the trigger date, not
an as-known clock; the earliest defensible decision instant for an episode is the session of the
document that first carried it (recoverable by receipt as above), never `known_at`. The intake's
clock stamping is a Data OS / intake contract question routed to its owner; this note does not
change it.

## Waterfall by session (all 27 sessions with any row, 2026-08-26 → 2026-10-23)

| Session | Inputs | Mapped | mapped: candidate / turn_watch / doors | IDENTITY_UNRESOLVED | ISSUER_UNRESOLVED | MISSING_STRUCTURAL_ANCHOR | ACTIVE_EPISODE_DIFFERENT_ANCHOR | Distinct refused tickers | Refused but resolvable today (reference widened later) |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 2026-08-26 | 1,903 | 467 | 0 / 467 / 0 | 1,436 | 0 | 0 | 0 | 1,436 | 221 |
| 2026-08-27 | 4,447 | 448 | 448 / 0 / 0 | 3,310 | 0 | 689 | 0 | 3,997 | 696 |
| 2026-08-28 | 4,441 | 450 | 448 / 0 / 2 | 3,300 | 0 | 691 | 0 | 3,988 | 694 |
| 2026-08-31 | 2,937 | 415 | 415 / 0 / 0 | 1,894 | 0 | 628 | 0 | 2,519 | 694 |
| 2026-09-04 | 6,666 | 990 | 588 / 400 / 2 | 4,972 | 0 | 548 | 156 | 4,887 | 952 |
| 2026-09-11 | 6,954 | 1,070 | 781 / 284 / 5 | 5,267 | 0 | 350 | 267 | 4,936 | 1,037 |
| 2026-09-17 | 5,980 | 1,137 | 892 / 244 / 1 | 4,178 | 0 | 149 | 516 | 4,001 | 1,092 |
| 2026-09-21 | 4,900 | 1,031 | 981 / 46 / 4 | 3,486 | 0 | 146 | 237 | 3,784 | 710 |
| 2026-09-23 | 3,370 | 962 | 921 / 39 / 2 | 2,031 | 0 | 117 | 260 | 2,320 | 710 |
| 2026-09-24 | 4,895 | 1,025 | 995 / 30 / 0 | 3,500 | 0 | 131 | 239 | 3,786 | 713 |
| 2026-09-25 | 350 | 33 | 0 / 25 / 8 | 100 | 0 | 0 | 217 | 317 | 26 |
| 2026-09-29 | 1,950 | 93 | 69 / 24 / 0 | 1,610 | 0 | 21 | 226 | 1,857 | 27 |
| 2026-10-01 | 3,258 | 943 | 935 / 8 / 0 | 2,005 | 0 | 104 | 206 | 2,233 | 717 |
| 2026-10-02 | 4,924 | 1,021 | 1005 / 9 / 7 | 3,540 | 0 | 124 | 239 | 3,814 | 720 |
| 2026-10-05 | 3,341 | 952 | 937 / 10 / 5 | 2,020 | 0 | 103 | 266 | 2,305 | 718 |
| 2026-10-06 | 3,340 | 950 | 936 / 11 / 3 | 2,020 | 0 | 103 | 267 | 2,308 | 713 |
| 2026-10-08 | 4,967 | 1,021 | 1005 / 6 / 10 | 3,576 | 0 | 123 | 247 | 3,866 | 710 |
| 2026-10-09 | 1,661 | 70 | 70 / 0 / 0 | 1,570 | 0 | 21 | 0 | 1,591 | 0 |
| 2026-10-13 | 307 | 16 | 0 / 16 / 0 | 88 | 0 | 0 | 203 | 291 | 1 |
| 2026-10-14 | 4,869 | 1,041 | 1002 / 21 / 18 | 2,796 | 2 | 795 | 235 | 3,768 | 2 |
| 2026-10-15 | 2,047 | 91 | 71 / 20 / 0 | 1,673 | 0 | 19 | 264 | 1,955 | 0 |
| 2026-10-16 | 378 | 18 | 0 / 18 / 0 | 95 | 0 | 0 | 265 | 360 | 0 |
| 2026-10-19 | 3,402 | 957 | 923 / 0 / 34 | 1,686 | 0 | 759 | 0 | 2,442 | 0 |
| 2026-10-20 | 2,075 | 86 | 70 / 16 / 0 | 1,664 | 0 | 18 | 307 | 1,988 | 0 |
| 2026-10-21 | 1,664 | 83 | 69 / 0 / 14 | 1,562 | 0 | 19 | 0 | 1,581 | 0 |
| 2026-10-22 | 1,647 | 69 | 69 / 0 / 0 | 1,560 | 0 | 18 | 0 | 1,578 | 0 |
| 2026-10-23 | 1,652 | 72 | 69 / 0 / 3 | 1,561 | 0 | 19 | 0 | 1,580 | 0 |
| **Total (27 sessions)** | **88,325** | **15,511** | | **62,500** | **2** | **5,695** | **4,617** | | **11,153** |

Source split of the refusals, all sessions: candidate 59,144, turn_watch 13,649,
doors 21. Mapped events by source: candidate 13,699, turn_watch 1,694,
doors 118. `ACTIVE_EPISODE_DIFFERENT_ANCHOR` (4,617) is turn_watch-only;
`MISSING_STRUCTURAL_ANCHOR` is candidate-only but for 12 doors rows. There is no double count:
1,087 OPENED events equal 1,087 episodes, no OPENED event shares a `source_event_id` with an
OBSERVED event, and the suppression ledger has no duplicate `source_event_id`.

## Identity replay — is any legitimate opportunity lost at the join?

Every refused (ticker, session) pair carrying `IDENTITY_UNRESOLVED` (62,500 rows;
59,185 distinct pairs; 5,433 distinct tickers; sessions on the clock above) was
re-resolved through the ONE Data OS alias reader exactly as the intake resolves
(`VendorAliasTable.resolve("membership", ticker, on=session)`) against the CURRENT committed
reference, then split by the alias row's `ingested_at` relative to the session:

| Class | Rows | Distinct (ticker, session) | Meaning |
|---|---:|---:|---|
| `no_current_reference` | 51,347 | 49,199 | no membership alias covers the ticker on that session today either — a reference-coverage gap, owner `scripts/build_security_master.py` (Data OS); not an intake defect |
| `reference_widened_after_session` | 11,153 | 9,986 | the alias resolves today but was ingested after the session (the 2026-10-11 membership ingest added 721 symbols; the 08-21 and 09-04 ingests the rest); the refusal stood on the reference the nightly had at the time |
| `resolvable_at_session` | **0** | **0** | the only class that could indicate an intake or snapshot defect |

**On "lawful as-known".** The refusals in the second class stand because the suppression ledger is
append-only and each nightly decided against the reference it had, not because the intake applies
an as-known gate: `covers()` ignores `ingested_at`/`known_at` for the `membership` vendor and the
intake passes no decision instant, so a from-scratch rebuild of the generation against today's
reference would map these 11,153 rows. The independent round-1 reviewer replayed every
pair against all 41 committed versions of `vendor_aliases.parquet`: 0 pairs resolve in any
historical version but not today, and the only 2 pairs resolving in a version committed within two
days after their session (CBOE on 10-05 and 10-06) match the single 2026-10-07 ingest and are
correctly classed as widened. A reference row with no ingest stamp would be counted as
`resolvable_at_session` (conservative); none exists in the membership vendor.

**Finding.** No `IDENTITY_UNRESOLVED` row was resolvable by a reference that was already ingested on
its session. The join is correct and fail-closed; the loss is entirely reference coverage. From
2026-10-09 onward the per-session `IDENTITY_UNRESOLVED` count (1,560–2,796 of ~1,650–4,900 inputs)
is `no_current_reference` for all but 3 rows (10-13: 1, 10-14: 2): the candidate universe is
several times wider than the 1,941-symbol membership reference. Widening the reference is Data OS
work with its own identity evidence rules; it must not be done by forcing ticker matches or by
accepting a later snapshot for historical sessions (the brief's first disconfirming test), and
nothing here reopens the as-known refusals.

The 26 pairs where the `membership` vendor is silent but a `store`/`yahoo` alias exists (from the
seat's exploratory run) are inside `no_current_reference` here: the intake resolves through
`membership` by design, and this note does not propose changing the vendor.

## Denominator facts the W2 design must carry

1. **Two candidate stamp sizes alternate.** Sessions with a curated stamp (09-21/23/24, 10-01/02/05/
   06/08/14/19) map ~920–1,005 candidate rows; the others (09-29, 10-09/15/20/21/22/23) map ~70. The
   alternation starts no later than 2026-09-21. The last curated stamp on main is 2026-10-19. Every
   wholesale nightly commit since 2026-10-21 was rejected by GitHub GH001 (`data/qledger/claims.jsonl`
   over 100 MB) — repair PR #10255; until it lands and the next SCHEDULED nightly proves it, no curated
   stamp after 10-19 exists on main.
2. **The W3 measurement ledger has no 10-21/22/23 pairing either.** `data/us_prophet_rank/w3/status.json`
   (board_as_of 2026-10-23) records 2026-10-21/22/23 as `session_missing` ("candidate session missing
   from the durable store; not pulled from Pages" — terminal under the ledger's own rule) and
   2026-10-29 as `degraded_or_unpaired`; 30 paired sessions accrued, **1** matured H10 session against
   an honest-N floor of 20. The episode store does carry 69 scan-tier candidate rows on each of those
   three sessions; what is missing is the curated stamp the W3 pairing needs. There is still no lawful
   comparison read and no defensible timing-uplift claim.
3. **`ACTIVE_EPISODE_DIFFERENT_ANCHOR` is a turn_watch-only class** (4,617 rows) and
   `MISSING_STRUCTURAL_ANCHOR` is candidate-only but for 12 doors rows (5,695 rows): the W2
   pre-policy population must state which anchor rule it inherits before counting either class as a
   false start or a miss.
4. **The decision instant is the document session, not `known_at`** (clock section above): a W2
   first-decision instant taken from a turn_watch event's `known_at` would look ahead by up to months
   for 1,376 of 1,694 turn_watch events.
5. **The falsifier holds trivially here**: no primary score was computed, so removing a refused row
   cannot improve one. It becomes binding the moment W2 is registered: the cohort is the pre-policy
   population including every refused class above, with the refusals reported, never dropped.

## What this does not establish

Nothing about entry lead, false-positive cost, fill or the H10 MAE endpoint. No prospective
B4 capture has run durably (its alias seam is bound in PR #10267; its durable home is an open
design decision because `NATIVE_LIVE_ROOT` is VPS-only and the live-host ledger law forbids `data/`
writes there). The B-17 historical population (7,918 C0 episodes, none with a complete 34-session
window) is unchanged and no favorable subset is substituted. The "no outcome surface" test checks the
script's own text; the modules it imports (`load_identity_spine`) read only the identity reference.
