# MO-PAID-013 — Single-name skew: ThetaData chain closure record (2026-09-23)

This note closes the MO-PAID-013 chain (options skew source migration `polygon_gex` →
`thetadata`) for a cold reader. Every claim cites a PR number, a commit, a file path,
or a receipt path on the M1 store host. Where the seat's facts are silent, the answer
is "not measured" — nothing is estimated.

## 0. Verdict in plain words

The store-host accrual lane is live on the M1 store host (`com.macro.skewaccrual`,
weekdays 12:30Z in PDT / 13:30Z in PST — `ops/launchd/com.macro.skewaccrual.plist`
fires at 05:30 America/Los_Angeles) and is accruing thetadata rows against an
R2-published ledger. The first scheduled day (2026-09-23) fired two incidents,
both fixed the same day (`#7819` runner hardening, `#7827` stdout-only gate
verdict). The committed `data/options_skew/snapshots.parquet` on `origin/main`
carries 12,747 rows (polygon_gex 12,375 + thetadata 372); the store-host/R2
ledger after the 2026-09-23 backfill + first scheduled accrual carries 13,971
rows across 48 dates. The render path is cut over (`#7743`) — render hosts
hydrate `options_skew` from R2 and `--emit`, no longer pinned to the legacy
chain. Six things remain open: PR `#7783` (W2-4c source-window fields +
plain-language Directional sentence) awaits a base-side HK-state re-bake;
PR `#7832` (A-F03-W2-6 complete-session resolver / thin-session emit guard)
is lane PASS and seat RATIFIED, armed `merge-on-green`, merge pending its CI
run; the 2026-08-14 → 2026-09-18 ledger hole is backfillable from the store
and the seat's `--backfill` is in progress at the time of writing; the
methodology-parity packet (`scripts/audit_options_skew_parity.py`) and the F00C
ledger row 013 reconciliation are owed by separate lanes; the `render-linux`
self-hosted runner is offline, so engine-render push-triggered runs pend and
page-side proofs come from the `closing-bell`, `render`, and `daily` lanes on
`macstudio`.

## 1. What shipped

| wave | PR | merged (UTC) | what it proves | proof path |
| --- | --- | --- | --- | --- |
| W2-1b | #6923 | 2026-09-22 21:05:39Z | ledger `source` column; thetadata canonical-wins upsert; legacy polygon chain behind `OPTIONS_SKEW_LEGACY_CHAIN=1` | merge commit `dd973910e95ea3ad99118fbbc2c83473fe8f1c80` |
| W2-2 | #7737 | 2026-09-22 23:35:22Z | store-host launchd lane (`ops/launchd/run_skew_accrual.sh`, plist `com.macro.skewaccrual`, weekdays 12:30Z); runbook published | merge commit `ac731aec23bde1b8e628259f82937b2013340623`; runbook `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` |
| W2-3 | #7743 | 2026-09-23 00:53:59Z | cutover: render hosts hydrate `python -m scripts.fetch_r2 --dirs options_skew` then `scripts.build_options_skew --emit`; `publish_r2` registry entry `options_skew`; six legacy callers unpinned | merge commit `b2d43b3a4078b7b539b6081cc30d02e1112d7754` |
| W2-4b | #7770 | 2026-09-23 07:42:47Z | backfill leg (canonical-wins) + DEC `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`; weekend rows excluded from emit | merge commit `d857f4568a7e0f4eb7c30d4ca6aabd69003f5d40`; `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` |
| W2-5a | #7759 | 2026-09-23 05:17:48Z | options payoff lab producer (`com.macro.payofflab`, weekdays 15:00Z) — index-ETF structures from `engine/options_payoff` over the thetadata chain; R2 publish; no UI | merge commit `148d1bfec8bbf1c080253b46a15d3e08184e8cfe` |
| W2-5b | #7763 | 2026-09-23 08:46:03Z | payoff lab consumer — "What a structure pays" fold on `options.html`; R2 → emit wiring on the render path | merge commit `668237947e016f679782e41e61c91c9133a5ea99` |
| runner hardening | #7819 | 2026-09-23 13:34:10Z | `git reset --hard && git clean -fd` BEFORE the detach in both runners; runbook §3.8 "restore the shared checkout after ANY manual session" | merge commit `646eb0611710bfecc395601a29ddd94c52349c03` |
| gate-stdout fix | #7827 | 2026-09-23 14:14:19Z | freshness gate verdict is read from stdout only; stderr `.err` sidecar; FRESH store no longer reads STALE | merge commit `2e476c04bb817022a352a8ae0c6a959390a58274` |
| W2-4c | #7783 | OPEN | source-window fields on `site/options_skew/latest.json`; one plain-language Directional-read sentence (per `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`); pinned awaiting a base-side HK-state re-bake | head ref `84428a84`; merge-candidate `f2e9a685b4d276db5c13dfce25492f8e7c214208`; state `open` per `gh api repos/mastermindx-market-intelligence/macro/pulls/7783` |
| W2-6 | #7832 | OPEN | complete-session resolver + bounded catch-up + thin-session emit guard; lane PASS, seat RATIFIED at `ba2729b7` 16:05Z, armed `merge-on-green`, merge pending its CI run | head ref `ba2729b7`; merge-candidate `3ffffb1900238bbf41db4a7a12e9ff2dacae0172`; state `open` per `gh api repos/mastermindx-market-intelligence/macro/pulls/7832` |

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
**13,971** rows across **48 dates**: 46 dates ≤ 2026-08-13 with thetadata at
~48/date alongside polygon 330–332/date, plus 2026-09-21 (372) and 2026-09-22
(12 — partial, see §3 incident).

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
yet", retried 3 × 20 min while the store was actually fresh. Cause: the gate
(`scripts/skew_accrual_gate.py`) prints ONE verdict word on stdout (`FRESH` /
`STALE` / `RESOLVE_ERROR` / `USAGE_ERROR`) and ONE `::gate-info::` info line
on stderr; the old runner capture was `>"$GATE_STATUS_FILE" 2>&1` and matched
the WHOLE merged file with `case "$status" in FRESH|RESOLVE_ERROR)`, so the
two-line content never matched the case pattern and every attempt fell through
to the not-fresh branch (the info line carries `latest/required/reason`, no
`STALE` token). Fix: PR `#7827` redirects stderr to `$GATE_STATUS_FILE.err`,
tails the info line into the lane log as the receipt's evidence, and parses
the verdict as the last line that IS a verdict word.

**Defect found on the 14:24Z accrual receipt (14:40Z).** The accrued
2026-09-22 session is PARTIAL — 12 names: AAPL, AMZN, AVGO, DIA, GOOGL, IWM,
META, MSFT, NVDA, QQQ, SPY, TSLA. Store contract: the T1 daily maintainer
(`com.macro.thetadata-daily`, `scripts/topup_thetadata_day.py --daily`; manifest
`daily_refresh` `D=2026-09-22 S=2026-09-21 greeks_S_roots=372`) writes the full
panel for `S` = the session before the last completed one, while an early-morning
writer (~04:30 local) lands the newest session for a 12-root priority set.
`load_chain(asof=None)` resolved the newest raw date. Measured store greeks
roots/date: **48** through 2026-08-20, **372–378** from 2026-08-21 to 2026-09-21,
**12** on 2026-09-22. Seat stopgap (committed 2026-09-23): the 12 rows were
dropped from the store-host ledger and R2 re-published (backup
`~/skew-ops-state/receipts/snapshots.parquet.before-drop-partial-2026-09-22.bak`)
so emits stay at 2026-09-21 / 372 rows. Durable fix = A-F03-W2-6 (PR `#7832`,
complete-session resolver + bounded catch-up + thin-session emit guard; OPEN,
armed).

## 4. Still open

- **W2-4c merge** (PR `#7783`). Owner: seat. Head ref `84428a84`; merge-candidate
  `f2e9a685b4d276db5c13dfce25492f8e7c214208`. Proof that will close it:
  `gh pr view 7783 --json state,mergedAt` reporting `state=merged`,
  `mergedAt` populated, and a post-merge render sentinel on `options.html` whose
  Directional read carries the plain-language source sentence per
  `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`.

- **W2-6 merge** (PR `#7832`). Owner: seat, armed `merge-on-green`. Head ref
  `ba2729b7`; merge-candidate `3ffffb1900238bbf41db4a7a12e9ff2dacae0172`. Proof
  that will close it: `gh pr view 7832 --json state,mergedAt` reporting
  `state=merged`; the next scheduled accrual receipt in
  `~/skew-ops-state/logs/skewaccrual.stdout.log` will then show the thin newest
  session dropped before emit instead of via the seat's manual stopgap.

- **Hole backfill 2026-08-14 → 2026-09-18** (operator: seat; in progress).
  Receipt (when complete):
  `~/skew-ops-state/receipts/skew-backfill-2026-08-14_2026-09-18.json` and the
  backup `snapshots.parquet.before-hole-backfill-2026-09-23.bak`. Coverage from
  the store: 2026-08-21 → 2026-09-18 at 372 roots, 2026-08-14 → 2026-08-20 at
  48 roots. Final numbers from the run are not measured at the time of writing;
  they will land in the receipt above.

- **Parity packet** (`scripts/audit_options_skew_parity.py`). Owner: lane (not
  the F03 seat). The W2-4 overlap audit
  (`research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md`) is the
  receipt that opened this: **3,965** keys compared, **sign agreement 0.603279**
  (match=2,392 / flip=1,563 / zero=0), |delta skew| p50/p90/max =
  **0.0379 / 0.167 / 3.9529**. The parity packet owes the methodology
  reconciliation (tenor/strike selection, chain snapshot timing) per
  `DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER`. Skew stays
  display-tier until it closes.

- **F00C ledger row 013 reconciliation**. Owner: separate seat packet (outside
  the F03 chain).

- **`render-linux` self-hosted runner offline**. Owner: operator. Effect:
  `engine-render.yml` push-triggered runs pend forever; page-side proofs come
  from the `closing-bell`, `render`, and `daily` lanes on `macstudio`. Until the
  runner returns, a successful render proof is read off a `macstudio` artifact,
  not an `engine-render` conclusion.

## 5. Operating the lane

Full text lives in `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md`
(W2-2 install + runbook). Cited by section, not re-explained.

- **Install + logs** (§3.3): M1 store host, plist `~/Library/LaunchAgents/com.macro.skewaccrual.plist`,
  lane checkout `/Users/chriswong/skew-ops-wt` (origin = GitHub, runbook §3.1),
  state dir `/Users/chriswong/skew-ops-state/{logs,receipts}`.
- **Receipt logs**: `~/skew-ops-state/logs/skewaccrual.stdout.log` and the
  long-lived stderr sibling `skewaccrual.stderr.log` (the launchd-plist
  `StandardOutPath` / `StandardErrorPath` — both predate `#7827`); per-run gate
  sidecar `$STATE_DIR/.skew_gate_status.$RUN_TAG.err` (post-`#7827`).
- **Freshness verdict**: stdout only, last line that IS `FRESH|STALE|RESOLVE_ERROR|USAGE_ERROR`
  (post-`#7827`); FRESH means `latest` ≥ `required`. Schedule: weekdays 12:30Z
  PDT / 13:30Z PST (plist fires 05:30 America/Los_Angeles).
- **§3.8 restore after ANY manual session**: sequence + `git status --short | wc -l`
  must print `0`. Durable state lives on R2; the checkout is disposable.
- **Recovery kickstart** (after an aborted run):
  `launchctl kickstart gui/$(id -u)/com.macro.skewaccrual` (runbook §3.8).
  Accrual is idempotent for the session it targets.
- **"Which session is accrued" rule**: `load_chain(asof=None)` resolves the
  newest raw date; the store contract (T1 daily maintainer vs early-morning
  12-root writer) means that date may be a thin session and must be filtered
  — until W2-6 (`#7832`) merges, the seat's stopgap is to drop rows from the
  store-host ledger before publish (see §3 defect).

## 6. Do-not-redo

- Never re-run the `2026-06-21 → 2026-08-13` backfill. The receipt files at
  `~/skew-ops-state/receipts/skew-backfill-2026-06-21_2026-08-13.{json,stdout}`
  and the parquet backup at
  `~/skew-ops-state/receipts/snapshots.parquet.local-after-backfill-2026-09-23.bak`
  are the audit; re-running is harmless (the ledger upsert is keyed by
  `(date, underlying)` and the parquet is "not rewritten when nothing changed"
  — `engine/options_skew.py:374–379`,`:520–521` — a second call reports no
  replacements and no additions) but wastes store I/O and adds nothing.
- Never pin `OPTIONS_SKEW_LEGACY_CHAIN=1` in CI, in a workflow file, or in
  `scripts/ci/`. The W2-3 cutover (`#7743`) removed every legacy pin;
  re-pinning would re-introduce the polygon path the chain is closing.
- Never accrue from a render host. Accrual runs on the M1 store host only; the
  render path is hydrate + `--emit`, never accrue.
- Never edit `scripts/build_options_command.py::load_stores`. That function
  loads render-side JSON stores only (flow_desk / screener / leaders /
  market_structure / vol / gex / gex_index — `scripts/build_options_command.py:143–160`,
  pinned by `tests/test_render_options_workspace_scope.py`). It has no
  ThetaData/polygon resolution-order code; the resolution order
  (ThetaData canonical, polygon_gex for unpriceable) lives in
  `engine/options_skew.py` (`snapshot`, `load_chain`, `backfill_from_store`)
  and is the contract `DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY` rests
  on. Editing `load_stores` is excluded by scope; editing `engine/options_skew.py`
  re-breaks the backfill canonical-wins invariant.
- Never write `site/options_skew/latest.json` by hand. The artifact is produced
  by `scripts/build_options_skew --emit` on render hosts after `scripts/fetch_r2
  --dirs options_skew` hydrates R2; hand-writing it would diverge from the
  source-of-truth parquet.
