# R03 — Second normal source cycle and existing ongoing owner (P23-1)

PLAN ONLY — NOT EXECUTED. Every step below is a seat act or a read-back; this document performs none of them.

## 1. Owner

The pinned commit has no `.github/workflows/` directory: `daily.yml` does not exist, so there is no job `name:` and no cron
line to cite (census A3 in R02_INSTALL_PLAN.md). The recurring units that do exist are systemd timer units for the live
dashboard lanes under `app/deploy/` (e.g. `macro-live-bars.timer`, OnCalendar Mon..Fri 13..21:37 UTC at
app/deploy/macro-live-bars.timer:5); none of their `ExecStart` commands runs the Data OS source cycle — the only
`dataos` hits under `app/deploy/` are the `update.sh` restart-fence regexes (app/deploy/update.sh:1304, 1504, 2388).
`scripts/vps_live_orchestrator.py:4-5` states the VPS owns short-lived `site/live` products while the Mac/PC nightly
runners own canonical history; those runners are host-side and are not committed in this repository, so no committed
recurring owner can be cited.

| owner the plan relies on | real return path | state |
| --- | --- | --- |
| the D00 ordinary source cycle, "one nightly collector run producing one coherent generation" (D00_SEMANTIC_DECISIONS.md:123-125) | none committed | UNFINISHED: no existing recurring owner for the nightly Data OS source cycle |

This plan creates no new daemon, watcher, cron entry, schedule, queue or publisher — not even as a recommendation. The gap
is recorded, never papered over.

## 2. Cycle definition

- Cycle 1 = the generation recorded by R02's receipts (the envelopes and digests of R02_INSTALL_PLAN.md §2).
- Cycle 2 = the next normal run of that same owner, once an owner exists (§1: currently `UNFINISHED`).
- D00 frames second-cycle acceptance as two consecutive nightly cycles producing coherent generations with the pointer
  transition and no refusal regression (D00_SEMANTIC_DECISIONS.md:124-125).
- The wait is one bounded read of that owner's next run id after it CONCLUDES — no polling loop, no dispatch, no re-run, no
  new watcher service. The read is a seat act: after the owner's next run concludes, the seat reads the owner's retained
  run record once and records its run id. No concrete read command is written here because the owner does not exist to
  name a return path; the row stays `UNFINISHED: no existing recurring owner` until one lands. An interrupted publish is
  `EFFECT_UNKNOWN` until the pointer target is checked against its own receipt, and reconciliation reads — it never re-runs
  the write (D00_SEMANTIC_DECISIONS.md:104-105).

## 3. Invariants for R03.01

| invariant | how the receipts must show it | state |
| --- | --- | --- |
| population preserved per enrolled market | member count per enrolled market identical between cycle 1 and cycle 2 accounts: US (XNAS, XNYS, ARCX) for consumer A, US for consumer B, US suites for consumer C (D00_SEMANTIC_DECISIONS.md:113-115); HK/CN remain identity-normalization-only with the gap reported as coverage (D00_SEMANTIC_DECISIONS.md:117-119) | B: PLANNED (envelope digests, request-local; no population account exists in web_api today — the per-market population account is carried by the C02 coverage contract, so the population invariant for composition is BLOCKED-ON-C03/C04). A: PLANNED. C: BLOCKED-ON-C03 |
| generation id moved forward exactly once | cycle-2's generation `supersedes` names the cycle-1 generation id and no third generation exists between them (`GenerationRef.generation_id`/`supersedes`, read_contract.py:220-225; superseded generations stay readable by id and leave CURRENT selection, D00_SEMANTIC_DECISIONS.md:100). A receipt-only change is itself a new generation (D00_SEMANTIC_DECISIONS.md:102-103) | UNFINISHED: no existing recurring owner produces `GenerationRef` records (no constructor exists, R02 appendix A4) |
| historical views byte-identical for dates < cycle-2 as_at | B: re-run the identical `read` request over a window ending before the cycle-2 as_at and compare sha256(stdout) with cycle 1's digest; `expected_version` (web_api.py:216-217) must be unchanged for that window. A: anonymous re-read of the OHLC JSON for the same pre-as_at window. C: same check over the composition output | B: PLANNED. A: PLANNED. C: BLOCKED-ON-C04 |
| dispositions per member are new / unchanged / revised, with counts | the cycle account classifies each member against cycle 1 (new = asked for the first time; unchanged = same disposition class and receipt; revised = disposition class or generation changed) and each member carries one of the eight `Disposition` values with its receipt in `detail` (read_contract.py:904-917) | the per-member disposition account is the C02 `account_coverage` output; zero production callers exist (R02 appendix A2): BLOCKED-ON-C03/C04 |
| zero duplicate publications | a duplicate is detectable from receipts alone: two retained returns claiming the same `generation_id`, or two generations whose `supersedes` both name the same predecessor (a forked pointer), or one run id appearing twice in the retained return path. An effect-unknown publish is reconciled by reading, never re-run (D00_SEMANTIC_DECISIONS.md:104-105) | UNFINISHED: no existing recurring owner and no retained return path to check |

## 4. R03.02 — No duplicate capture

If a capture is already running, the seat waits for it to conclude and reads its retained return; the seat never dispatches
another capture of the same cycle to obtain a faster receipt. Nothing in this plan starts, triggers or re-runs any capture.

## 5. R03.03 — Owners and real return paths

Every owner this plan relies on, with its real return path:

- The nightly Data OS source cycle owner: no committed owner exists — `UNFINISHED: no existing recurring owner` (§1).
- The live-dashboard systemd timers (`app/deploy/*.timer`) exist but are NOT relied on: they own `site/live` products,
  not Data OS generations (scripts/vps_live_orchestrator.py:4-5), and this plan creates none and attaches to none.
- Consumer receipts that exist today are request-local (web_workspace.py:99-100); a request-local envelope is not a cycle
  return, so nothing here claims a background run produced it.

Any owner without a real return path is `UNFINISHED`, as recorded above; no scheduling or background reasoning is claimed
without an actual existing owner and return.

## 6. R03.04 — Source failure surfaces as data failure

- B: a source or configuration failure surfaces as a typed data error — the CLI prints one JSON object with a bounded
  `error` code and exits 2 (scripts/data_workspace.py:81-89; codes such as `PATH_REFUSED`, web_workspace.py:79-91), and the
  envelope keeps `production_qualification: NOT_ESTABLISHED_BY_THIS_ADAPTER` (web_workspace.py:126). The adapter has no
  fallback path at all: reads are request-local over declared roots, so it cannot silently serve a fresher substitute —
  the refusal, not a substitute, is the output.
- C: the carrier is `RefusalCode.FALLBACK_NOT_DECLARED` (read_contract.py:99, raised at read_contract.py:1155 and :1281);
  a member that cannot be served from the declared primary source is `Disposition.STALE`, `MISSING`, `NEVER_INSPECTED` or
  `REFUSED` (read_contract.py:910-916), never silently re-sourced. These paths are contract-only until a caller lands:
  BLOCKED-ON-C04.
- The read-back that proves no silently fresh fallback: the R03.01 historical-window byte-identity check (§3) plus D00's
  no-refusal-regression criterion across the two cycles (D00_SEMANTIC_DECISIONS.md:125). UNFINISHED: no existing recurring
  owner means there is no retained cross-cycle return yet to run this read-back against; the check is defined, not
  executed, in this plan.

## 7. Dependencies

- R03 starts only after R02 has been executed by the seat; cycle 1 is defined by R02's recorded receipts.
- Every wave-3 dependency stays BLOCKED-ON-<lane>: C03 (composition onto the C02 contract), C04 (coverage-bearing result
  production), M01, U03, U04. None of them has landed at the pinned commit, and this plan does not write any of them as if
  it had.
- The owner gap (§1) blocks the cycle itself; no owner is invented, recommended or created by this plan.
