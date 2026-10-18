---
key: CCW-LOCAL-DERIVED-HISTORY-LAGS-HOLDINGS
claim: The inspected Macro primary checkout held corporate-bond snapshots through 2026-10-07 while its derived issuer series and latest bond panel stopped at 2026-09-08; the existing SSGA parser independently accepted live holdings dated 2026-10-15.
falsifier: Read the same checkout's data/corp_bonds/holdings dates and issuer_daily.parquet and bond_panel_latest.parquet as_of maxima, or repeat the permitted official holdings-source check; a newer derived generation supersedes this dated observation.
so_what: Diagnose the existing collection-to-calculation path and preserve source dates; do not call a freshly rendered view current or infer a global market-data outage from this local binding.
kind: data
verified_at: 2026-10-18
verified_by: "Macro PR #9590; research/credit_dislocation/IMPLEMENTATION_STATUS.md; scoped pandas date/count inspection and existing CorpBondHoldingsAdapter parser with five successful source snapshots."
scope:
  - macro
  - ccw
  - data/corp_bonds
confidence: verified
expires: 2026-10-25
---

## Observed scope

This is a read-only inspection of the configured primary checkout's data, not a production-fleet diagnosis. The admitted isolated CDI worktree was initially sparse and did not contain those historical files. Its source acquisition subsequently copied a narrowly declared input set into its own data directory without altering the primary checkout.

At inspection, each of five holdings directories contained 53 dates ending 2026-10-07. The derived issuer series contained 525 rows ending 2026-09-08; the latest bond panel had 10,305 rows on that date. A CDI projection from that binding correctly reports historical-only rather than a fresh signal.

The existing official SSGA source and parser returned 2026-10-15 snapshots: SPIB 5,358 rows, SPSB 1,669, SPLB 2,973, JNK 1,144 and SPHY 1,936. These are per-fund rows, not unique bonds or issuer liabilities. New snapshots do not fill the intervening history gap.

## Preserve the distinction

Source transport, raw ingestion, derived calculation, user projection and live production acceptance are separate observations. The rebuild over 54 captured dates processes more than half a million historical bond rows; memory and timing are being measured, but no root cause of the earlier local lag has been established. Do not silently convert a timing suspicion into a proven outage cause.

The implementation source, tests and latest proof boundary live in the existing CCW research directory and PR, not in a new operational registry. No external worker, new monitor or prediction authority is created by this record.

## Recovered implementation boundary

The isolated #9590 workspace subsequently completed a bounded YTM rebuild through October 15 (810 issuer rows on 54 dates; 10,376 latest bond rows). Pricing validation remains PENDING. This does not change the earlier observation about the primary checkout or prove its repair.

The implementation and recovery evidence are preserved under `research/credit_dislocation/IMPLEMENTATION_STATUS.md`, `evidence/recovery_receipt.json`, and `CONTINUATION.md` on PR #9590. The exact branch is `claude/ssd-ccw-dislocation-v1-cc87720e59421398`; the source workspace is `/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/ccw-dislocation-v1-cc87720e59421398`. Current assignment continues in a fresh Pro chat after the observed heavy-chat generation failure. No duplicate workstream, worker or generic state store is created.

Next action: resolve the preserved pricing-validation PENDING result and recompile CDI against that refreshed generation, then qualify the real Bonds consumer before release. Raw source captures stay local and unstaged. The interrupted Paper bond-row edit was reconciled as applied on its original carrier and must not be replayed. Parent mission remains incomplete.
