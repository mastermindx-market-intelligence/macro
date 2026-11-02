# Terminal Tactical R1-A: current state and continuation

Parent: Terminal #598. D0 dependency: Terminal #601 at `c0f36cb16fadd190ad747fc47a28405d9ec0fca4`. Organizational carrier: Macro #7262. R1-A carrier: Macro #7270. Executive remains unfinished and is not a prerequisite for this research lane.

## Current capability state

R1-A is **implemented and retrospectively measured, but not production-promoted**. The frozen prereg/config landed before outcomes at `5d950c85cd0c8e3a393e555433bf94fd3ee395a7`; all 84 cells were appended to the existing `entry_radar` TrialLedger at `0109877f57009973cbebe9f72e43bd23e35a5183`; causal primitives/runner were hardened through `30a72e85a25f188d1f654ec71b18872aa4fee3d8`. `TTI_R1A_REPORT.md` and `tti_r1/RESULT.json` carry the aggregate result. No rank, alert, size, order or options authority exists.

Registration receipt: 1,674 ledger lines before, 1,758 after, exactly 84 R1-A rows; prior ledger prefix SHA256 `7a82e5b7766a7f2bbeb9e8c46bb57ab0b9a1b32d262a853944d093645769f119`, preserved byte-for-byte. Full registered-grid SHA256 `86b9e84faec43882e4ccc0975b2193a2ee489e618cd13adcbe784ea7dab53b46`.

## Empirical result

Canonical run-003 used the unchanged captured five-minute inputs: 312 scheduled dates, 2,464 name-day candidates, 1,810 comparable rows and 58,308 arm/horizon/cost outcome rows. Aggregate result SHA256 is `5c75a38d3f5acc61ad5e79fcec2f26af37a6f62da0ed449c4b1533b5cc35ff0b`.

The exact strict AH→PM `PERSISTENT` arm fired 12 times / 10 dates and did not improve the primary 60-minute outcome versus either ALL_EARLY or GAP_UP. `WEAKNESS_PERSISTENT` had N=1 and is uninformative. `WEAKNESS_RECLAIM` fired 514 times / 213 dates but its primary 60-minute incremental delta was near zero and its later-horizon strength was partition-unstable. `PERSISTENT_OPEN_ACCEPT` produced only 3 rows / 2 development dates: interesting intraday observations, no validation.

Disposition: **no R1-A arm may be promoted to standalone live rank/alert/size authority.** Strict persistence is not supported as tested; weakness reclaim remains context-only; opening acceptance remains an underpowered prospective hypothesis. This closes only the exact registered construction, not the broader low-timeframe research space.

## Adversarial execution record

Run-001 was rejected after post-run adversarial review found causal robustness defects: missing scheduled sessions could bridge returns, zero-volume bars could extend evidence recency, future duplicate/corrupt observations could contaminate earlier windows, and malformed outcome rows could erase a fire instead of censoring that outcome. Each repair was driven by a failing test. After repair, run-002 and run-003 are byte-identical at feature-panel, outcome and aggregate-result levels on the unchanged inputs; the fixes changed robustness rather than opportunistically changing the observed result.

Latest focused tactical suite: 41 passes. Broader relevant suite excluding sparse-only species fixtures: 265 passed, 2 skipped. A wider run including `test_species_registry.py` had six failures/two errors solely because this sparse worktree intentionally omits `data/species/registry.json` and `data/experiments/registry_seed.json`; those are checkout-availability failures, not credited as green. Compileall and diff-check passed before report publication.

## Adjacent dependencies

Terminal #595 remains the current-history refresh owner. Exact-head review `5242058779` found failure masking in exhausted fetch/pagination paths; its owner must repair and prove those paths. This R1 lane did not fork the updater.

Terminal #601 remains the D0 release carrier; its semantic implementation is consumed by exact head only. Its Vercel status failures are rate-limit deployment failures, not source validation. Independent review/release proof remains separate from R1-A research.

The six-value historical projection still discards provider `vw`/transaction-count detail and historical availability receipts. Bar-VWAP proxies therefore remain proxies; corrected-history research is not faithful live-fill reconstruction.

## Next actions

1. Push the current #7270 head with report, machine aggregate, registration receipt and exact verification evidence; obtain current-head review/CI before any merge.
2. Preserve the R1-A negative/tiny-N dispositions; no post-hoc threshold rescue or options/regime/news additions inside this study.
3. After R1-A source acceptance, open a separate bounded R1-B carrier for the already-specified long-side exhaustion/reclaim-versus-continuation experiment. Measure local reversal, candidate LOD survival, confirmation delay and remaining opportunity separately.
4. Keep finer-grain/live work behind the existing data owner and D1 qualification. Do not treat static one-minute absence as vendor incapability.
5. Only after admitted price-side evidence exists may existing Radar shadow events and Terminal Forming/Confirmed UI be implemented; options remain a separately measured incremental witness.

## Must not be redone

Do not rebuild D0, repeat the unchanged R1-A grid, refetch the preserved inputs, ask for design approval/Executive reconnection, retry the held INTC operation through another carrier, or reinterpret tiny cells as validated signals. No duplicate scanner, event store, research registry, calendar, provider or capital plane is authorized.
