# ROR-1 — Cross-pipeline price vintage gap explains Oct15 Leadership Crack unavailability

**October 16, 2026; read-only original Git object/Actions forensic return.** Main source pin `4ae7f2ac4c58e6e93945a6f09313bcaadba5709e`. No code, original data, publisher, risk policy, QLedger issuer or live customer surface changed.

## Exact source and computed-date evidence

`engine/leadership_crack.py`, blob `cb0a3f468ac1bf2267fb6d0ee57d378b293d3c0b`, reads **active cohort** membership from `data/baskets/membership.json`, then each `data/baskets/ohlcv/<ticker>.parquet` (not Yahoo/SPY) to assemble the 42-name price panel. `_build()` chooses `asof` from the last jointly valid cohort statistic row (`z_series`, median drawdown and carnage EMA). A current SPY close **does not create a new cohort constituent row**.

At the exact Git tree above, the read-only researcher extracted original Git blob bytes (no working-tree checkout, no data vendor calls, no model/forward-log writes) for the **42 unique active names** in `ai_semiconductors`, `ai_infra`, `memory_storage`, `semicap_equipment`. All 42 original parquet objects decoded successfully and all 42 had last valid `close` on **October 14, 2026**. None has a valid October 15 close in that Git tree. In contrast, the same exact Git revision's `data/yahoo/SPY.parquet` has last valid close **October 15**.

Directly observed dependent artifacts in that revision:

- `data/market_state/latest.json`, blob `e5b10a5354bb5b9e78e838865e73683926c73b2d`: Oct15 `46/MIXED`, constituent freshness recorded not stale.
- `data/regime/latest.json`, blob `60d4c8dc5ababcd78fc6170c39e1352b7ae5deff`: Oct15 Market State/Radar, and its embedded `leadership_crack` is still Oct14 CRACKING.
- `data/leadership_crack/latest.json`, blob `420a1679e17f2e69cbfc1fa7d74acef84568b01e`: Oct14 `CRACKING`, `dislocation=true`, `n_fresh=42`, `n_total=42` **relative to the old October 14 cohort panel**, not proof of October 15 cohort-date coverage.
- `site/riskdata/risk_envelope.json`, blob `4e5dc3bf106761017282c01cd319042d3de3b0e0`: source session Oct15, `data_state=DEGRADED`, `hazard.stage=null`, `stage_reason=required_coverage_unavailable`, Leadership Crack unreadable as required source.

**Bounded inference:** this source-vintage split directly explains why the source-native Leadership Crack can report only Oct14 while U.S. Market State advances to Oct15 and the strict Risk Envelope rightly refuses a qualified Oct15 hazard. Replacing the date with Oct15, guessing the price move, or mapping a stale Oct14 `CRACKING` into a fresh `FRAGILE` would fabricate evidence. A legitimate Oct15 **cohort** observation must originate upstream first.

The immutable per-ticker blob/date/row-count inventory, with no vendor prices or unlicensed story content, is in `evidence/leader_cohort_source_date_census_20261016.json` (Git blob `e54a3214f85da14dbae98ba03d380d92cc0a11ca`, SHA256 `ac54222f33d59a2a64ad94591d7d457a8ff7d9bb5aa76c127eae445f89f491b5`).

## The original nightly data publication **failed** at the same boundary

Git commit history for `data/baskets/ohlcv/NVDA.parquet`, `AMD.parquet` and `MU.parquet` shows last accepted change at `data: daily collection 2026-10-15` commit `9fd048df0ebf4399e9c12926809c5ca66931a373` (**October 15 04:00:30Z**, after the October 14 U.S. close); none of those original files was accepted into main during the next U.S. close window. In contrast, SPY was advanced at `engine: regime update 2026-10-16` commit `3bbe42a324e9926f20ed583469ca242f3cc12116` (**October 16 06:37:21Z**).

Actual original GitHub Actions nightly [run 38830626430](https://github.com/mastermindx-market-intelligence/macro/actions/runs/38830626430): `collect` job **116748357565** failed step `push market data` at October 16 **03:37:58Z** with:

> File data/qledger/claims.jsonl is 100.29 MB; this exceeds GitHub's file size limit of 100.00 MB. GH001: Large files detected; main -> main (pre-receive hook declined).

The rejection stopped the **entire market-data Git push**, not merely the unrelated QLedger claims file. The same run also reports `collect_tail` and engine commit failures, while separate engine/closing-bell paths can advance market-state/SPY pointers. This is a named cross-workflow producer publication bottleneck, not evidence that the Git-backed leader input itself became current. The collect log reports broader collector activity (current-returned 4748 of 5120 attempted), but **does not prove each of the 42 specific leadership members was current on the rejected runner**. Do not assume unpublished local rows are accepted authoritative prices.

Other QLedger workstreams already own this GH001/issuer/old-writer problem: #8042 / #9426 prior merges, Draft/HOLD #8756 native cutover, original [Defensive Rotation #8669](https://github.com/mastermindx-market-intelligence/macro/pull/8669) recovery checkpoints. **No manual cherry-pick of a rejected claims/market-data commit, size-limit bypass, force push, issuer replay or secondary publisher** is authorized by this research.

## Two independent repairs required

1. **Original market-data/QLedger publisher custody:** on the original authorized writer, first fix accepted-main-only QLedger claims publication with size/ancestry/direct-parent/single-append and legacy-writer exclusion proof; then recover lawful accepted Git or existing authorized data publication of actual Oct15 basket constituent rows (strict adjustment basis, prices, timestamp and identity). A green unrelated build step/CI or manual local quote refresh does not prove saved/servable source.
2. **Original Leadership/Envelope/attention owner:** after the source advances, verify `_load_closes` and computed native `asof` truly advance to Oct15; then ensure the existing Risk Envelope becomes eligible or visibly degraded if another required source is absent. Preserve the data-state warning at glance tier and the last-known earlier CRACKING timestamp without claiming fresh systemic risk, recovery, cross-market contagion or capital authority. Demand user-facing authenticated origin/edge/render and notification receipts separately.

**Minimal acceptance evidence:** exact accepted Git blob for a representative high-liquidity basket constituent and **all 42 cohort-members' valid last-close sessions** (or explicitly qualified exclusions), SPY session, Leadership source session/coverage, Risk Envelope hazard + reason, public/entitled served revision, mounted warning, and actual user notification/ack clocks. The source-owner tests must include a rejected publish and mixed-date split as a negative control.

**Research effect state:** Git readback and one targeted 42-name in-memory parquet-date census only. No production repo writes, ticker/market forecast, alert firing, cohort selection, original worker source edit, or protected release effect.