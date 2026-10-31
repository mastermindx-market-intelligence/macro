# Entry Timing W1 — candidate-episode intake waterfall and identity replay (2026-10-31)

**Status:** measurement only, authority none, outcome-blind. Produced by the Fable CEO seat under the
October 31 commission (completion brief packet 2: "Inventory how many rows had authentic clocks,
quote/basis and membership by session. Produce a waterfall with explicit denominators and refusal
classes before inspecting any formally gated outcome"). No outcome, price, grade, paired-race or
timing surface was read. Nothing in this note changes W0 (DONE), the B4 preregistration (#7751,
amendment A1), the W3 measurement ledger or any registered look.

**Reproduce (read-only):** `python3 scripts/report_us_candidate_episode_waterfall.py [--json]`
(tests: `tests/test_report_us_candidate_episode_waterfall.py`). The script reads the SELECTED B1
generation named by `data/us_prophet_rank/episodes/HEAD.json` and the committed Data OS identity
reference through the intake's own reader (`load_identity_spine`); it writes nothing.

## Inputs

| Fact | Value |
|---|---|
| Selected B1 generation (HEAD.json at this checkout, main `91b936c46424`) | `peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9` |
| Events in the generation (mapped observations, `OPENED` + `OBSERVED`) | 15,511 |
| Suppression ledger rows (typed refusals, all sessions) | 72,814 |
| Identity reference replayed against | `data/reference/vendor_aliases.parquet` `sha256:ff8a32df8e47d88149d8ac8d8ae54b9b117a3c44cd34cfcd57eebcf0de816306` (membership vendor: 1,941 rows) |
| Reference the generation's Oct 25 receipt was built against | `sha256:eeb880747bee9d23ff0c5714b608dda399997d567a61936b78b4e43231c9da31` (main at `e1e1b5d35`, 2026-10-24) |

The denominator is `inputs = mapped + refused` per observation session. A mapped row is one event in
the episode store (its session is the payload's `opened_session` for `OPENED`, else `occurred_at`'s
date); a refused row is one suppression-ledger row with its native typed reason. Rows are observations,
not distinct securities: a ticker refused on twenty sessions is twenty rows.

## Waterfall by session (all 43 sessions with any row)

| Session | Inputs | Mapped | mapped: candidate / turn_watch / doors | IDENTITY_UNRESOLVED | ISSUER_UNRESOLVED | MISSING_STRUCTURAL_ANCHOR | ACTIVE_EPISODE_DIFFERENT_ANCHOR | Distinct refused tickers | Refused but resolvable today (reference widened later) |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 2026-05-07 | 19 | 19 | 0 / 19 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-03 | 6 | 6 | 0 / 6 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-04 | 7 | 7 | 0 / 7 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-05 | 6 | 6 | 0 / 6 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-06 | 17 | 17 | 0 / 17 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-07 | 25 | 25 | 0 / 25 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-10 | 27 | 27 | 0 / 27 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-11 | 38 | 38 | 0 / 38 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-12 | 54 | 54 | 0 / 54 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-13 | 31 | 31 | 0 / 31 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-14 | 28 | 28 | 0 / 28 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-17 | 5 | 5 | 0 / 5 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-18 | 30 | 30 | 0 / 30 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-19 | 78 | 78 | 0 / 78 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-20 | 49 | 49 | 0 / 49 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-21 | 49 | 49 | 0 / 49 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-24 | 66 | 66 | 0 / 66 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-25 | 64 | 64 | 0 / 64 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-26 | 1,534 | 98 | 0 / 98 / 0 | 1,436 | 0 | 0 | 0 | 1,436 | 221 |
| 2026-08-27 | 4,452 | 453 | 448 / 5 / 0 | 3,310 | 0 | 689 | 0 | 3,997 | 696 |
| 2026-08-28 | 4,441 | 450 | 448 / 0 / 2 | 3,300 | 0 | 691 | 0 | 3,988 | 694 |
| 2026-08-31 | 2,949 | 424 | 415 / 9 / 0 | 1,894 | 0 | 628 | 3 | 2,522 | 694 |
| 2026-09-01 | 48 | 24 | 0 / 24 / 0 | 0 | 0 | 0 | 24 | 24 | 0 |
| 2026-09-02 | 138 | 68 | 0 / 68 / 0 | 0 | 0 | 0 | 70 | 70 | 0 |
| 2026-09-03 | 197 | 116 | 0 / 116 / 0 | 0 | 0 | 0 | 81 | 80 | 0 |
| 2026-09-04 | 6,294 | 680 | 588 / 90 / 2 | 4,972 | 0 | 548 | 94 | 4,797 | 952 |
| 2026-09-08 | 43 | 27 | 0 / 27 / 0 | 0 | 0 | 0 | 16 | 16 | 0 |
| 2026-09-09 | 29 | 22 | 0 / 22 / 0 | 0 | 0 | 0 | 7 | 7 | 0 |
| 2026-09-10 | 83 | 46 | 0 / 46 / 0 | 0 | 0 | 0 | 37 | 36 | 0 |
| 2026-09-11 | 6,776 | 907 | 781 / 121 / 5 | 5,267 | 0 | 350 | 252 | 4,837 | 1,037 |
| 2026-09-14 | 231 | 75 | 0 / 75 / 0 | 0 | 0 | 0 | 156 | 156 | 0 |
| 2026-09-15 | 90 | 35 | 0 / 35 / 0 | 0 | 0 | 0 | 55 | 40 | 0 |
| 2026-09-16 | 131 | 35 | 0 / 35 / 0 | 0 | 0 | 0 | 96 | 50 | 0 |
| 2026-09-17 | 5,618 | 968 | 892 / 75 / 1 | 4,178 | 0 | 149 | 323 | 3,598 | 1,092 |
| 2026-09-18 | 149 | 11 | 0 / 11 / 0 | 0 | 0 | 0 | 138 | 51 | 0 |
| 2026-09-21 | 4,870 | 1,032 | 981 / 47 / 4 | 3,486 | 0 | 146 | 206 | 3,620 | 710 |
| 2026-09-22 | 35 | 3 | 0 / 3 / 0 | 0 | 0 | 0 | 32 | 28 | 0 |
| 2026-09-23 | 3,278 | 956 | 921 / 33 / 2 | 2,031 | 0 | 117 | 174 | 2,147 | 710 |
| 2026-09-24 | 4,735 | 998 | 995 / 3 / 0 | 3,500 | 0 | 131 | 106 | 3,607 | 713 |
| 2026-09-25 | 327 | 23 | 0 / 15 / 8 | 100 | 0 | 0 | 204 | 193 | 26 |
| 2026-09-28 | 114 | 4 | 0 / 4 / 0 | 0 | 0 | 0 | 110 | 41 | 0 |
| 2026-09-29 | 1,902 | 77 | 69 / 8 / 0 | 1,610 | 0 | 21 | 194 | 1,695 | 27 |
| 2026-09-30 | 130 | 11 | 0 / 11 / 0 | 0 | 0 | 0 | 119 | 33 | 0 |
| 2026-10-01 | 3,220 | 945 | 935 / 10 / 0 | 2,005 | 0 | 104 | 166 | 2,077 | 717 |
| 2026-10-02 | 4,957 | 1,018 | 1005 / 6 / 7 | 3,540 | 0 | 124 | 275 | 3,663 | 720 |
| 2026-10-05 | 3,289 | 949 | 937 / 7 / 5 | 2,020 | 0 | 103 | 217 | 2,129 | 718 |
| 2026-10-06 | 3,165 | 942 | 936 / 3 / 3 | 2,020 | 0 | 103 | 100 | 2,106 | 713 |
| 2026-10-07 | 23 | 1 | 0 / 1 / 0 | 0 | 0 | 0 | 22 | 16 | 0 |
| 2026-10-08 | 4,911 | 1,023 | 1005 / 8 / 10 | 3,576 | 0 | 123 | 189 | 3,702 | 710 |
| 2026-10-09 | 1,794 | 79 | 70 / 9 / 0 | 1,570 | 0 | 21 | 124 | 1,635 | 0 |
| 2026-10-12 | 134 | 11 | 0 / 11 / 0 | 0 | 0 | 0 | 123 | 39 | 0 |
| 2026-10-13 | 239 | 12 | 0 / 12 / 0 | 88 | 0 | 0 | 139 | 162 | 1 |
| 2026-10-14 | 4,805 | 1,036 | 1002 / 16 / 18 | 2,796 | 2 | 795 | 176 | 3,615 | 2 |
| 2026-10-15 | 2,085 | 86 | 71 / 15 / 0 | 1,673 | 0 | 19 | 307 | 1,839 | 0 |
| 2026-10-16 | 215 | 6 | 0 / 6 / 0 | 95 | 0 | 0 | 114 | 185 | 0 |
| 2026-10-19 | 3,494 | 961 | 923 / 4 / 34 | 1,686 | 0 | 759 | 88 | 2,530 | 0 |
| 2026-10-20 | 1,838 | 76 | 70 / 6 / 0 | 1,664 | 0 | 18 | 80 | 1,761 | 0 |
| 2026-10-21 | 1,664 | 83 | 69 / 0 / 14 | 1,562 | 0 | 19 | 0 | 1,581 | 0 |
| 2026-10-22 | 1,647 | 69 | 69 / 0 / 0 | 1,560 | 0 | 18 | 0 | 1,578 | 0 |
| 2026-10-23 | 1,652 | 72 | 69 / 0 / 3 | 1,561 | 0 | 19 | 0 | 1,580 | 0 |
| **Total (60 sessions)** | **88,325** | **15,511** | | **62,500** | **2** | **5,695** | **4,617** | | **11,153** |

Source split of the refusals, all sessions: candidate 59,144 (`IDENTITY_UNRESOLVED` 53,459,
`MISSING_STRUCTURAL_ANCHOR` 5,683, `ISSUER_UNRESOLVED` 2), turn_watch 13,649 (`IDENTITY_UNRESOLVED`
9,032, `ACTIVE_EPISODE_DIFFERENT_ANCHOR` 4,617), doors 21. Mapped events by source: candidate 13,699,
turn_watch 1,694, doors 118.

## Identity replay — is any legitimate opportunity lost at the join?

Every refused (ticker, session) pair carrying `IDENTITY_UNRESOLVED` (62,500 rows; 59,185 distinct
pairs; 5,433 distinct tickers) was re-resolved through the ONE Data OS alias reader exactly as the
intake resolves (`VendorAliasTable.resolve("membership", ticker, on=session)`) against the CURRENT
committed reference, then split by the alias row's `ingested_at` relative to the session:

| Class | Rows | Distinct (ticker, session) | Meaning |
|---|---:|---:|---|
| `no_current_reference` | 51,347 | 49,199 | no membership alias knows the ticker today either — a reference-coverage gap, owner `scripts/build_security_master.py` (Data OS); not an intake defect |
| `reference_widened_after_session` | 11,153 | 9,986 | the alias exists today but was ingested after the session (the 2026-10-11 membership ingest added 721 symbols; smaller ingests 08-21 / 09-04); the refusal was lawful as-known, pinned by the generation receipt's reference sha |
| `resolvable_at_session` | **0** | **0** | the only class that could indicate an intake or snapshot defect |

**Finding.** No `IDENTITY_UNRESOLVED` row was resolvable by a reference that was already ingested on
its session. The join is correct and fail-closed; the loss is entirely reference coverage. From
2026-10-09 onward the per-session `IDENTITY_UNRESOLVED` count (1,560–1,686 of ~1,650–3,500 inputs) is
100% `no_current_reference`: the candidate universe is several times wider than the 1,941-symbol
membership reference. Widening the reference is Data OS work with its own identity evidence rules; it
must not be done by forcing ticker matches or by accepting a later snapshot for historical sessions
(the brief's first disconfirming test), and nothing here reopens the as-known refusals.

The 26 pairs where the `membership` vendor is silent but a `store`/`yahoo` alias exists (from the
seat's exploratory run) are inside `no_current_reference` here: the intake resolves through
`membership` by design, and this note does not propose changing the vendor.

## Denominator facts the W2 design must carry

1. **Two candidate stamp sizes alternate.** Sessions with a curated stamp (2026-10-02/05/06/08/14/19)
   map ~940–1,040 candidate rows; the others map ~70. The last curated stamp on main is 2026-10-19
   (1,706 rows). Every wholesale nightly commit since 2026-10-21 was rejected by GitHub GH001
   (`data/qledger/claims.jsonl` over 100 MB) — repair PR #10255; until it lands and the next
   SCHEDULED nightly proves it, no curated stamp after 10-19 exists on main.
2. **The W3 measurement ledger lost the same sessions.** `data/us_prophet_rank/w3/status.json`
   (board_as_of 2026-10-23) records 2026-10-21/22/23 as `session_missing` (terminal; reconstruction
   refused by ledger law) and 2026-10-29 as `degraded_or_unpaired`; 30 paired sessions accrued,
   **1** matured H10 session against an honest-N floor of 20. There is still no lawful comparison
   read and no defensible timing-uplift claim.
3. **`ACTIVE_EPISODE_DIFFERENT_ANCHOR` is a turn_watch-only class** (4,617 rows) and
   `MISSING_STRUCTURAL_ANCHOR` is candidate-only (5,683 of 5,695): the W2 pre-policy population must
   state which anchor rule it inherits before counting either class as a false start or a miss.
4. **The falsifier holds trivially here**: no primary score was computed, so removing a refused row
   cannot improve one. It becomes binding the moment W2 is registered: the cohort is the pre-policy
   population including every refused class above, with the refusals reported, never dropped.

## What this does not establish

Nothing about entry lead, false-positive cost, fill or the H10 MAE endpoint. No prospective
B4 capture has run durably (its alias seam is bound in PR #10267; its durable home is an open
design decision because `NATIVE_LIVE_ROOT` is VPS-only and the live-host ledger law forbids `data/`
writes there). The B-17 historical population (7,918 C0 episodes, none with a complete 34-session
window) is unchanged and no favorable subset is substituted.
