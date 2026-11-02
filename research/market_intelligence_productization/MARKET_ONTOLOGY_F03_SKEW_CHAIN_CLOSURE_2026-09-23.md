# MO-PAID-013 — Single-name skew: ThetaData chain closure record (2026-09-23)

This note closes the MO-PAID-013 chain (options skew source migration `polygon_gex` →
`thetadata`) for a cold reader. Every claim cites a PR number, a commit, a file path,
or a receipt path on the M1 store host. Where the seat's facts are silent, the answer
is "not measured" — nothing is estimated.

## 0. Verdict in plain words

The store-host accrual lane is live on the M1 store host (`~/skew-ops-wt`, plist
`com.macro.skewaccrual`, weekdays 12:30Z in PDT / 13:30Z in PST — `ops/launchd/com.macro.skewaccrual.plist`
fires at 05:30 America/Los_Angeles) and is accruing thetadata rows against an
R2-published ledger. The first scheduled day (2026-09-23) fired two incidents,
both fixed the same day (`#7819` runner hardening, `#7827` stdout-only gate
verdict). The committed `data/options_skew/snapshots.parquet` on `origin/main`
carries 12,747 rows (polygon_gex 12,375 + thetadata 372); the store-host/R2
ledger after the 2026-09-23 backfill + first scheduled accrual carries 13,971
rows across 48 dates. The render path is cut over (`#7743`) — render hosts
hydrate `options_skew` from R2 and `--emit`, no longer pinned to the legacy
chain. Five things remain open: PR `#7783` (W2-4c source-window fields + plain-language Directional sentence; seat; ratification WITHDRAWN 17:25Z at head `84428a84` — on the live ledger the per-date majority-run windows fragment into 15 alternating runs, so round 5 replaces them with per-source coverage spans and one `source_break_date`, lane in flight); PR `#7832` (A-F03-W2-6 complete-session
resolver / thin-session emit guard; seat, RATIFIED at `ba2729b7`, armed
`merge-on-green`, CI pending); the F00C ledger row 013 reconciliation (seat); the
`render-linux` self-hosted runner offline (operator); and a holiday no-op
accrual ruling (seat: when the complete store session is already on the
ledger, `--accrue` writes 0 rows and the runner verifier's `--pre-rows`
rule reports a failure — runner-side ruling owed). The render-host lanes
that produce page-side proofs are the closing-bell.yml and render.yml lanes
on `[self-hosted, macstudio]`, plus daily.yml's regional desk builders
script which runs the same hydrate→emit pair.

## 1. What shipped

| wave | PR | merged (UTC) | what it proves | proof path |
| --- | --- | --- | --- | --- |
| W2-1b | #6923 | 2026-09-22 21:05:39Z | ledger `source` column; thetadata canonical-wins upsert; legacy polygon chain behind `OPTIONS_SKEW_LEGACY_CHAIN=1` | merge commit `dd973910e95ea3ad99118fbbc2c83473fe8f1c80` |
| W2-2 | #7737 | 2026-09-22 23:35:22Z | store-host launchd lane (`ops/launchd/run_skew_accrual.sh`, plist `com.macro.skewaccrual`, weekdays 12:30Z); runbook published | merge commit `ac731aec23bde1b8e628259f82937b2013340623`; runbook `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` |
| W2-3 | #7743 | 2026-09-23 00:53:59Z | cutover: render hosts hydrate `python -m scripts.fetch_r2 --dirs options_skew` then `scripts.build_options_skew --emit`; `publish_r2` registry entry `options_skew`; six legacy callers unpinned | merge commit `b2d43b3a4078b7b539b6081cc30d02e1112d7754` |
| W2-4 | #7756 | 2026-09-23 03:43:02Z | methodology-parity audit (compared 3965; match 2392 / flip 1563 / zero 10; sign agreement 0.603279); parity packet published; no engine change | merge commit `6298d58ea497`; `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md`; `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md` |
| W2-4b | #7770 | 2026-09-23 07:42:47Z | backfill leg (canonical-wins) + DEC `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`; weekend rows excluded from emit | merge commit `d857f4568a7e0f4eb7c30d4ca6aabd69003f5d40`; `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` |
| W2-5a | #7759 | 2026-09-23 05:17:48Z | options payoff lab producer (`com.macro.payofflab`, weekdays 15:00Z) — index-ETF structures from `engine/options_payoff` over the thetadata chain; R2 publish; no UI | merge commit `148d1bfec8bbf1c080253b46a15d3e08184e8cfe` |
| W2-5b | #7763 | 2026-09-23 08:46:03Z | payoff lab consumer — "What a structure pays" fold on `options.html`; R2 → emit wiring on the render path | merge commit `668237947e016f679782e41e61c91c9133a5ea99` |
| runner hardening | #7819 | 2026-09-23 13:34:10Z | `git reset --hard && git clean -fd` BEFORE the detach in both runners; runbook §3.8 "restore the shared checkout after ANY manual session" | merge commit `646eb0611710bfecc395601a29ddd94c52349c03` |
| gate-stdout fix | #7827 | 2026-09-23 14:14:19Z | freshness gate verdict is read from stdout only; stderr `.err` sidecar; FRESH store no longer reads STALE | merge commit `2e476c04bb817022a352a8ae0c6a959390a58274` |
| W2-4c | #7783 | OPEN | source-window fields on `site/options_skew/latest.json`; one plain-language Directional-read sentence (per `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`); head `84428a84` after a merge-of-main on 2026-09-23 15:33Z; ratification withdrawn 17:25Z (majority-run windows fragment: 15 runs measured on the live ledger); round 5 = per-source coverage spans + `source_break_date`, lane in flight | head ref `84428a84`; state `open` per `gh api repos/mastermindx-market-intelligence/macro/pulls/7783` |
| W2-6 | #7832 | OPEN | complete-session resolver + bounded catch-up + thin-session emit guard; lane PASS, seat RATIFIED at `ba2729b7` 16:05Z, armed `merge-on-green`, merge pending its CI run | head ref `807365f4`; state `open` per `gh api repos/mastermindx-market-intelligence/macro/pulls/7832` |

## 2. Data receipts

**Backfill receipt (2026-09-23, M1 store host).** Command
`python -m scripts.build_options_skew --backfill 2026-06-21 2026-08-13` over the
ThetaData store: **38** sessions requested, **3,965** rows replaced
(polygon_gex → thetadata), **1,212** rows added, **2026-07-03** not in store.
Receipt files
`~/skew-ops-state/receipts/skew-backfill-2026-06-21_2026-08-13.json` and the
matching `.stdout` on the M1 host. Local parquet backup
`~/skew-ops-state/receipts/snapshots.parquet.local-after-backfill-2026-09-23.bak`
(262,795 B).

**Cutover proof (committed artifact on origin/main).**
`site/options_skew/latest.json` generated **2026-09-23T08:37Z** by a render host:
`ledger_asof 2026-09-21`, `n 372`, `source "thetadata"`, `source_state "ok"`,
`accrual_state "ledger_only"`,
`gate_status "insufficient_history (have 44/120 dates, 417/15 names)"` (the gate
message stays context-only under DEC display-tier).

**Committed ledger on origin/main.** `data/options_skew/snapshots.parquet` —
**12,747** rows across **35 dates**: polygon_gex 2026-06-21 → 2026-08-13 (34 dates,
12,375 rows) + thetadata 2026-09-21 (372 rows).

**Store-host / R2 ledger after the 2026-09-23 backfill + first scheduled accrual.**
**13,971** rows across **48 dates** (max 2026-09-22). The per-date source
composition is not restated here; `source_windows` on the emitted artifact
(after #7783) is the authoritative view.

**Store-host / R2 ledger after the seat stopgap** (12 partial rows dropped):
**13,959** rows across **47 dates** (max 2026-09-21, sha256 d7b4aeeb…98fb35).

**Hole backfill receipt (2026-09-23 15:22Z → 17:21Z, M1 store host).** Command
`python -m scripts.build_options_skew --backfill 2026-08-14 2026-09-18` over the
ThetaData store (dry run 15:22Z → 16:21Z, real run 16:21Z → 17:21Z, ~60 min each,
single core): **36** dates requested, **10** weekend skipped, **1** not in store
(2026-09-07), **25** sessions backfilled, **7,686** rows added, **0** replaced.
Ledger **13,959 → 21,645** rows across **72 dates** (max 2026-09-21); verifier OK
(`--pre-rows 13959`); `publish_r2 --dirs options_skew` 1 uploaded; hydrate-back
sha256 `10d80182…98e66`. Receipt files
`~/skew-ops-state/receipts/skew-backfill-2026-08-14_2026-09-18.{json,stdout,stderr}`;
backup `~/skew-ops-state/receipts/snapshots.parquet.before-hole-backfill-2026-09-23.bak`.
Per-source coverage on session dates after this run: thetadata 2026-06-22 → 2026-09-21
(64 dates), polygon_gex 2026-06-22 → 2026-08-13 (33 dates; the 2026-06-21 Sunday
as-of row is excluded); first ThetaData-only session 2026-08-14.

**First scheduled accrual receipt (2026-09-23 14:15Z).** `kickstart 14:15:12Z`,
log start `14:15:16Z` (`~/skew-ops-state/logs/skewaccrual.stdout.log`): gate
FRESH on attempt 1 (latest 2026-09-22 / required 2026-09-21); pre-accrue
**13,959** rows → post **13,971**; `accrue rc=0` at **14:24:30Z**; ledger
verified OK; `publish_r2 --dirs options_skew` completed **14:24:33Z**.

## 3. Incidents on the first scheduled day and their fixes

**(a) 12:30Z accrual aborted at `step_refresh`.** Symptom:
`git checkout --detach origin/main failed`. Cause: the seat's manual backfill had
left `data/options_skew/snapshots.parquet` modified in the shared checkout
`~/skew-ops-wt`; the runner's detach preceded its own reset/clean and git refused
to overwrite the dirty tracked file. Fix: PR `#7819` moved `git reset --hard &&
git clean -fd` to run BEFORE the detach in both runners, and the runbook §3.8
("Restore the shared checkout after ANY manual session") codifies the manual
discipline that prevents the dirty state in the first place.

**(b) 12:50Z re-fire stuck in the freshness gate.** Symptom: "store not fresh
yet", retried 3 × 20 min while the store was actually fresh; the run sat
through 3 of the runner's 6 attempts (`MAX_ATTEMPTS=6`, `SLEEP_SECS=1200`)
before the seat stopped it by exact pid. Cause: the gate
(`scripts/skew_accrual_gate.py`) prints ONE verdict word on stdout (`FRESH` /
`STALE` / `RESOLVE_ERROR` / `USAGE_ERROR`) and ONE `::gate-info::` info line
on stderr; the runner captured the gate's stdout AND stderr into ONE status
file (`>file 2>&1`), read the whole file into `$status`, and matched it with
`case "$status" in FRESH|RESOLVE_ERROR)` — the two-line value never matched,
so every attempt fell through to the not-fresh branch (the info line carries
`latest/required/reason`, no `STALE` token). Fix: PR `#7827` writes stdout to
the status file and stderr to a sidecar
`$STATE_DIR/.skew_gate_status.<run_tag>.err` and parses the last verdict-word
line.

**Defect found on the 14:24Z accrual receipt (14:40Z).** The accrued
2026-09-22 session is PARTIAL — 12 names: AAPL, AMZN, AVGO, DIA, GOOGL, IWM,
META, MSFT, NVDA, QQQ, SPY, TSLA. Store contract: the T1 daily maintainer
(`com.macro.thetadata-daily`, `scripts/topup_thetadata_day.py --daily`; manifest
`daily_refresh` `D=2026-09-22 S=2026-09-21 greeks_S_roots=372`) writes the full
panel for `S` = the session before the last completed one, while an early-morning
writer (~04:30 local) lands the newest session for a 12-root priority set.
`load_chain(asof=None)` resolved the newest raw date. Measured store greeks
roots/date: **48** through 2026-08-20, **372–378** from 2026-08-21 to 2026-09-21,
**12** on 2026-09-22. Seat stopgap (applied by the seat on the store host
2026-09-23, NOT a git commit): the 12 rows were dropped from the store-host
ledger and R2 re-published (backup
`~/skew-ops-state/receipts/snapshots.parquet.before-drop-partial-2026-09-22.bak`)
so emits stay at 2026-09-21 / 372 rows. Durable fix = A-F03-W2-6 (PR `#7832`,
complete-session resolver + bounded catch-up + thin-session emit guard; OPEN,
armed).

## 4. Still open

- **W2-4c merge** (PR `#7783`). Owner: seat. Head ref `84428a84`; ratification
  withdrawn 2026-09-23 17:25Z (round 5 in flight: per-source coverage spans +
  `source_break_date` replace the majority-run windows). Proof that will close it:
  `gh pr view 7783 --json state,mergedAt` reporting `state=merged`,
  `mergedAt` populated, and a post-merge render sentinel on `options.html` whose
  Directional read carries the plain-language source sentence per
  `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`.

- **W2-6 merge** (PR `#7832`). Owner: seat, armed `merge-on-green`. Head ref
  `807365f4`; merge-candidate `0a5ea3326006d1abe8de1a40a3d7cc0b1d61fbda`. Proof
  that will close it: `gh pr view 7832 --json state,mergedAt` reporting
  `state=merged`; the next scheduled accrual receipt in
  `~/skew-ops-state/logs/skewaccrual.stdout.log` will then show the thin newest
  session dropped before emit instead of via the seat's manual stopgap.

- **F00C ledger row 013 reconciliation**. Owner: separate seat packet (outside
  the F03 chain). Proof that closes it: a merged PR updating
  `tests/test_mo_b_ledger_reconciliation_2026_09_18.py` EXPECTED /
  OUTSIDE_UNION_SHA256 and the F00C manifest per the MO-B single-writer
  precedent (seat packet, after `#7783` merges).

- **`render-linux` self-hosted runner offline**. Owner: operator. Effect:
  `engine-render.yml` push-triggered runs pend forever; page-side proofs come
  from the render-host lanes (closing-bell.yml and render.yml run on
  `[self-hosted, macstudio]`; daily.yml's regional desk builders script runs
  the same hydrate→emit pair). Until the runner returns, a successful render
  proof is read off one of those artifacts, not an `engine-render` conclusion.

- **Holiday no-op accrual ruling**. Owner: seat. Mechanism: when the complete
  store session is already on the ledger, `--accrue` writes 0 rows and the
  runner verifier's `--pre-rows` rule reports a failure. A runner-side ruling
  is owed (seat).

## 5. Operating the lane

Runbook `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` by section
number (§3.1, §3.2, §3.3, §3.3b, §3.7, §3.8); lane host is the M1 store.

- Recovery kickstart: `launchctl kickstart gui/$(id -u)/com.macro.skewaccrual` (§3.8).
- "Which session is accrued" rule: `S` = manifest's `daily_refresh.S`, one session
  behind the store's early 12-root set (per `#7832`); until W2-6 merges, the seat's
  stopgap is to drop partial rows before publish (see §3 defect).
- Gate sidecar `$STATE_DIR/.skew_gate_status.<run_tag>.err` (post-`#7827`); the
  receipt log's stderr sibling `~/skew-ops-state/logs/skewaccrual.stderr.log`
  predates `#7827` and is NOT the gate sidecar.

## 6. Do-not-redo

- Never re-run the `2026-06-21 → 2026-08-13` backfill. The receipt files at
  `~/skew-ops-state/receipts/skew-backfill-2026-06-21_2026-08-13.{json,stdout}`
  and the parquet backup at
  `~/skew-ops-state/receipts/snapshots.parquet.local-after-backfill-2026-09-23.bak`
  are the audit; re-running the backfill is idempotent — UPSERT keyed by
  `(date, underlying)`; a second call replaces and adds nothing
  (`backfill_from_store` docstring) — and only burns store-host CPU (the seat
  measured 59 minutes for a 25-session dry run on 2026-09-23).
- Never pin `OPTIONS_SKEW_LEGACY_CHAIN=1` in CI, in a workflow file, or in
  `scripts/ci/`. The W2-3 cutover (`#7743`) removed every legacy pin;
  re-pinning would re-introduce the polygon path the chain is closing.
- Never accrue from a render host. Accrual runs on the M1 store host only; the
  render path is hydrate + `--emit`, never accrue.
- Never edit `scripts/build_options_command.py::load_stores`. It reads only
  flow_desk / screener / leaders / market_structure / vol / gex / gex_index
  (`scripts/build_options_command.py:143`). Skew and payoff are separate
  loaders (`load_skew_source` added by `#7783`, `load_payoff_lab` at
  `scripts/build_options_command.py:187`) threaded through `build_context`
  (`scripts/build_options_command.py:2020`).
- Never write `site/options_skew/latest.json` by hand. The artifact is produced
  by `scripts/build_options_skew --emit` on render hosts after `scripts/fetch_r2
  --dirs options_skew` hydrates R2; hand-writing it would diverge from the
  source-of-truth parquet.
