---
key: MARKET-TIME-MACHINE
title: Market Memory daily historical experience
objective: 'Let a user or machine inspect any sufficiently covered historical date
  before Mastermind existed, with source-bound market observations, first-print macro
  chronology, explicit unavailable evidence and separately revealed outcomes.

  '
status: active
program: market-memory
p0: US_PROPHET_ENTRY_TIMING
repos:
- macro
owner: sol
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
- engine/neuralweb/market_memory_history.py
- engine/neuralweb/market_memory_history_archive.py
- engine/neuralweb/market_memory_history_macro.py
- engine/neuralweb/market_memory_history_view.py
- scripts/market_memory_history.py
- templates/market_memory_history.*
- engine/neuralweb/market_memory_history_extend.py
waves:
- id: H0
  title: Qualified retrospective archive and independent numerical proof
  status: done
  pr: 9445
  next_action: Merged PR9445, installed c223bd38 private Data & Lab, source/browser/installed-reader
    proofs retained; no public/PIT claim.
- id: H1
  title: Exact-date machine and browser consumers with first-print chronology
  status: done
  pr: 9445
  depends_on:
  - H0
  next_action: Merged PR9445, installed c223bd38 private Data & Lab, source/browser/installed-reader
    proofs retained; no public/PIT claim.
- id: H2
  title: Broader historical information and independently evaluated consumer value
  status: in_progress
  depends_on:
  - H1
  next_action: Qualify immutable accrual and richer historical evidence; preserve
    source-specific scheduling and publication holds.
next_action: Complete immutable-extension source qualification, consume original bounded
  review, and publish through normal CI. Existing private installed history lookup
  is live; daily scheduling remains held.
---

# Cumulative frontier — 2026-10-15

Mission: source-bound daily market history before and after Mastermind, with honest coverage, isolated later outcomes and proven user/machine consumption. Active Chairman commission continues. `owner: sol` is this assigned responsibility, not an addressable historic chat.

## Source, custody and installation

Original root/parent `market-time-machine-20261015`. Original source PR9445 head cf3332019f89c5d6417515b8102638d8f77efd70 merged c223bd38c3750e5f4a4707d9ab3083b5089764f7 at10:29:30Z. All binding CI checks concluded clean; inactive pilot negative-control failure was verified from its machine inactive_base_context receipt, not waived. Prior reviews and rebuttals remain in the existing HISTORY_* adjudications.

The fixed M2 `/Users/chriswong/.local/bin/mmx-data-workspace` now selects accepted immutable c223bd38. Seven installed-path canaries pass: capabilities, market/stock day, absent date, legacy read/Lab plan and wrong-hash refusal. Launcher SHA532f34f2ee0cb5574cd758e43282553a6010e2d71e609b5f2111ec61edc2f10c; source/root guards unchanged, old0b204cde release preserved. Installation receipt b6417a96d9b0d554258cbc9b2100a98d1cede765d7f9905a8c77bda8b8ecd228 is retained under `/Volumes/Mastermind/evidence/market-time-machine-20261015-install/INSTALLATION.json` and `web_test_runs:market-time-machine-20261015-receipts/installation.json`. GitHub comment6190044327 confirms the installed result on PR9445.

Existing personal Studio Direct plugin plugin_asdk_app_6ab650d46de88191ac2ca930acf5a77b was updated, not recreated: version1.0.1/release pluginrel_6ad0ad1a5c488191b03c1b619af634e4. It now carries the exact accepted Data & Lab workflow/reference. App ID, connection, name, audience, presentation and prompts preserved. Saved source readback proven; all-account adoption/current-session skill-index refresh are NOT proven.

Next source operation `market-time-machine-accrual-20261015`, original root retained. Managed workspace `/Volumes/Mastermind 2/agent-workspaces/macro/web/market-time-machine-accrual-20261015`, branch sol/web-market-time-machine-accrual-20261015, base c223bd38. Original source workspace remains preserved; no other writer displaced.

## Verified archival data

Initial v2:25market proxies,152980state rows,8482observed dates Jan29,1993–Oct9,2026,22.6MBParquet; manifest31f61ea6dc152265d3e9ed2d955068e8d914b1f82b990804ad5efb0b68b5ecd0. Stock cohort:50stocks+SPY,345032states,50.9MBParquet; manifest43da330274bb1728e627d59781afea0a158139bccfa782d08e92a9b97d81bcec. Macro:16518first-print records/54series; chronology21d432846cf6d7d2c41d39cf4df75b8faa39e0afe7bb6c629b14066819b5f5f1. No full macro vintages, intraday clocks, consensus, strict PIT or complete historical stock universe. COHR/CRCL/SIVB/FRC were found in the older Massive store, but RAW basis is not silently spliced into Tiingo adjusted history.

Real foreground extension:25new EOD requests all succeeded (100rows,22723raw bytes), with Oct9overlap anchor and Oct12–14tail. Original collector and materializer used without credential exposure, retry or scheduler. New archive `web_test_runs:market-time-machine-20261015-through-1014/manifest.json` SHAa87654c54470d604640aa3ee3ed66b43fb4df18132c6f01a64d64a6e3c9984b7 holds153055states:all152980prior states preserved,75new observations. All original68files and manifest hashes unchanged. Actual installed c223reader serves allthree newdates(25rows each), preserves historical Sept13values, and returns zero for unobservedOct15. Stock prices are now also extended as described below; macro chronology has not been refreshed. Exact extension/inputs/proof receipts are in the existing receipt directory and HISTORY_REAL_EXTENSION_PROOF_20261015.json.

## Current code and proof

New `market_memory_history_extend.py` composes existing archive/data owners. Same study/universe/price basis and original refs required; no retroactive state replacement, dropped row or false no-data success. No-new-observation request creates nothing. Parent state hash recomputed streaming from exact retained Parquet; parent outcomes never opened by extension. New outcome maturity stays in a new immutable generation. CLI `extend` and tests enrolled in existing research-price-panel; no new scheduler, queue, registry, latest pointer or access plane.

18module +2CLI negative tests failed before implementation, now pass; five further adversarial tests and a failing-before/passing-after no-nested-parent-write test were added.455combined checks pass24.98s on the final guarded source;78focusedchecks also pass; all3affected owner scopes have no missing inferred dependency. Whole historical reconstruction is still a bounded snapshot rebuild, not a proven low-cost perpetual schedule.

Independent review run market-time-machine-accrual-20261015-review-01: submitted once afterNOT_FOUND, originalroot/parent, sourcehash49c1e5bde4fd6a61b757ded927134bf2395bae537ed55001b45ac76206d4b8fa. Canonical route Qwen/Bailian onUbuntu0. Returned PASS with no findings; retained4217bytes SHAa5987566ea1a0c92eb9619369f29b923a9ccb6bfa20256e7980b4ff65be2d26c, accepted once after actual review. A subsequent no-nested-parent destination guard has its own final-source review market-time-machine-accrual-20261015-review-02, source1dfe3df537de0b5ae615c1644b773fd5080652988c35f26c37ce004b1549360d, same root/parent. Result/acceptance still owed on that exact second run; no repeat of the first.

## Stock extension and real revision refusal

47additional foreground EOD requests succeeded(188rows,43226rawbytes); SPY reused its existing same-day capture rather than redownloaded. Three ended vendor series were not requested. Total mission newrequests72, all successful,65949rawbytes. Exact vendor-symbol labeling remains retrospective, not canonical identity.

The first whole-stock append refused before output because MU's Oct9adjustedOHLC changed in the new source. No field was overwritten and no provider call retried. The eligible request retained the same51selectedsources and oldMUreferences, withheld only MU's conflictingnewcapture, and added141newstates for47eligible sources onOct12–14. Archive `web_test_runs:market-time-machine-20261015-stocks-through-1014/manifest.json`, SHAccaff1599545c58d2f9e1bfcba81bd1088c65267b400f773fcd6f7d2f553e709. All345032oldstates and68parentfiles unchanged;345173newgenerationstates. Fiveactual installeddatechecks passed. MUremains present onhistoricaldates and explicitlyabsent onnewdates, alongside the threeendedseries. Exactholdmetadata is in stocks-through-1014-holds.json; no rawvendorpricepublishedinGit. See HISTORY_STOCK_EXTENSION_PROOF_20261015.json.

## Held boundaries / next action

Persistent Tiingo scheduling/publisher change was previously explicitly refused and remains held. No new launchd/timer, BOATS relay, auth or public redistribution action was performed here. Current finite EOD acquisition is a distinct bounded existing-owner operation, not a workaround for that scheduling refusal. No source/PIT/trading authority added.

Next: consume original review, finish adversarial/CLI/CI qualification, publish source and verify landing. Extend the selected stock archive through the same preserved-state mechanism where eligible new receipts exist. Broader news/earnings/filing context, full macro revisions, true intraday history, historical universe and measured predictive value remain separate program obligations. Keep one frontier; no repeated original corpus acquisition or legacy numeric/browser tests absent relevant change.
