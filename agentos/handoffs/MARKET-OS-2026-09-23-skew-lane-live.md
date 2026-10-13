---
workstream: "WS:MARKET-OS"
session: claude/mo-a-3-a-f03-skew-lane-live-docs
model: fable
ended_because: complete
prs:
  - 6923
  - 7737
  - 7743
mission: >
  Close MO-PAID-013 (options skew source migration polygon_gex -> ThetaData) under the
  three-PR sequencing law and record what is now installed on the M1 store host, the
  first-run receipts, the real-overlap audit, and what the next session must not redo.
state_before: >
  Production skew was live and fresh from the polygon chain path; a no-fallback migration
  would have blanked it. W2-1b (#6923) shipped the ledger upsert + accrue/emit split with
  every live caller pinned to the legacy source; W2-2 (#7737) shipped the store-host lane
  but its runbook cloned from a local root and its first run could not hydrate an empty
  R2 prefix; W2-3 (#7743) was built by a Grok lane and held DRAFT until the producer was live.
changed:
  - path: research/MARKET_ONTOLOGY_F03_SKEW_OVERLAP_RECEIPT_2026-09-22.md
    what: Real-overlap audit receipt produced on the M1 store host by scripts/audit_options_skew_overlap.py against the committed legacy ledger.
  - path: agentos/discoveries/DSC-SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER.md
    what: Discovery — the two skew constructions agree on sign for only 60% of the 3,965 keys both can price; display-tier only until a parity packet.
  - path: agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md
    what: The two W2-1b "unresolved" lines now point here; W2-2 and W2-3 are merged.
verified:
  - claim: W2-1b merged with zero live change (all six callers pinned), W2-2 merged, W2-3 merged; no legacy pin remains on main and every workflow hydrates options_skew from R2 before its builder step.
    command: gh pr view 6923 7737 7743 --json state,mergeCommit; grep -rn OPTIONS_SKEW_LEGACY_CHAIN .github scripts; grep -rn "fetch_r2 --dirs options_skew" .github/workflows scripts/ci
    result: MERGED dd973910 (2026-09-22T21:05Z), MERGED ac731aec (23:35Z), MERGED b2d43b3a (2026-09-23T00:54Z); pin grep empty; one hydrate step per workflow plus the desk script.
  - claim: The store-host lane is installed and produced its first R2 publish.
    command: bash /Users/chriswong/install_skewaccrual_m1.sh seed|dryrun|full|bootstrap on m1 (wrapper run_with_env.sh; no secret ever printed)
    result: seed 2 uploaded / hydrate rc=0; dry-run rc=0 (accrue 23:36:01->23:47:31Z, ledger verified OK, publish skipped); full run rc=0 (accrue 23:48:10->23:59:51Z, publish completed 23:59:54Z); launchctl print gui/501/com.macro.skewaccrual state=not running, program=run_with_env.sh, logs under /Users/chriswong/skew-ops-state/logs/.
  - claim: The accrued ledger is durable on R2, not only in the disposable checkout.
    command: after the bootstrap refresh reset the checkout to the committed 238,595-byte ledger — run_with_env.sh .env python -m scripts.fetch_r2 --dirs options_skew; pandas read of data/options_skew/snapshots.parquet
    result: 1 restored, 1 already current; 246,371 bytes, 12,747 rows, source = polygon_gex 12,375 + thetadata 372 (all on 2026-09-21).
  - claim: The real-overlap audit ran on the store host against the legacy ledger.
    command: python -m scripts.audit_options_skew_overlap (defaults) in /Users/chriswong/skew-ops-wt
    result: keys_compared 3965; abs_delta_skew p50 0.0379 / p90 0.167 / max 3.9529; n_sign_match 2392, n_sign_flip 1563; 8,410 skipped no_chain (2,875 weekend-dated legacy rows + 5,535 weekday keys without a store chain).
unverified:
  - claim: The first render after the cutover emits site/options_skew/latest.json with ledger_asof >= 2026-09-21 and non-null n.
    what_would_verify: the seat's render sentinel on the first green render.yml run created after 2026-09-23T00:54Z; read the artifact's ledger_asof, accrual_state, n from origin/main.
  - claim: The launchd job fires on schedule.
    what_would_verify: launchctl print gui/501/com.macro.skewaccrual "last exit code" after 05:30 local on 2026-09-23, plus /Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log.
unresolved:
  - Cutover liveness on the render hosts (first post-merge render) is not yet observed.
  - Methodology parity between the ThetaData recompute and the retired polygon path (tenor/strike selection, chain snapshot timing) is not reconciled; skew stays display-tier.
  - 5,535 weekday legacy keys had no ThetaData chain in the store; the coverage reason is not characterized.
next_actions:
  - Read the 2026-09-23 launchd receipt on m1 and the first post-cutover render artifact; record both in the seat ledger.
  - Commission a methodology-parity packet (A-F03-W2-4 candidate) before any promotion of skew beyond display tier; it owns DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER.
  - Characterize the 5,535 weekday no_chain keys (store coverage vs underlying set) on the store host.
do_not_redo:
  - Do not re-run W2-1b, W2-2 or W2-3; all three are merged. Do not re-pin OPTIONS_SKEW_LEGACY_CHAIN on any caller.
  - Do not re-clone the lane checkout from a local repo root; /Users/chriswong/skew-ops-wt exists with origin = GitHub (runbook §3.1 as corrected in #7743).
  - Do not stage a second secret file on m1; the lane .env is a symlink to the producers' flow-ops-wt/.env (runbook §3.2).
  - Do not seed R2 again; options_skew/ on the bucket is populated (runbook §3.3b) and the runner hydrates it on every run.
  - Do not compare polygon_gex and thetadata rows as one series (DSC above).
danger_areas:
  - The lane checkout is disposable — every run does fetch + detach + reset --hard + clean -fd; anything written into it (including audit receipts under research/) is deleted on the next run. Receipts live under /Users/chriswong/skew-ops-state/receipts/.
  - fetch_r2 exits 1 on ZERO objects and the runner refuses to accrue on a failed hydrate; an emptied bucket prefix would silently stop accrual (the runner logs "refusing to accrue and publish").
  - launchd opens StandardOutPath/StandardErrorPath before the runner starts and does not create parent dirs; the logs dir must exist before any re-bootstrap.
  - The plist and tests pin /opt/homebrew/Caskroom/miniconda/base/bin/python; the m1 system python3 has no pandas.
  - The polygon ledger carries weekend-dated rows (as_of artifacts); ThetaData never will. Consumers that join on date must expect that.
---

# Handoff — MARKET-OS / MO-PAID-013 skew lane live (2026-09-23)

The three-PR sequencing law is complete and the producer is live on the M1 store host.
Everything a cold stranger needs is in the frontmatter; the seat's minute-level ledger lives in
the Meta-CEO A handoff scratch (`estate_plain_language_packet_ledger.md`, 2026-09-22/23 entries).

| step | PR | merge | live effect |
| --- | --- | --- | --- |
| W2-1b ledger upsert + accrue/emit + legacy pins | #6923 | dd973910 2026-09-22 21:05Z | none (pins) |
| W2-2 store-host accrual lane (launchd + R2) | #7737 | ac731aec 2026-09-22 23:35Z | m1 produces; render hosts unchanged |
| W2-3 cutover (hydrate from R2, `--emit`) | #7743 | b2d43b3a 2026-09-23 00:54Z | render hosts emit from the ThetaData ledger |

Install surface on m1: `/Users/chriswong/skew-ops-wt` (blobless sparse clone, origin GitHub),
`/Users/chriswong/skew-ops-state/{logs,receipts}`, `~/Library/LaunchAgents/com.macro.skewaccrual.plist`
(weekdays 05:30 local), `.env` -> `/Users/chriswong/flow-ops-wt/.env`.
