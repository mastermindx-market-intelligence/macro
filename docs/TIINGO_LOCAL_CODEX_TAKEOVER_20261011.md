# MastermindX Tiingo / BOATS — local Codex takeover contract
**Issued:** 2026-10-11 UTC
**Current Chairman instruction:** Hand off the existing Tiingo integration mission to local Codex to complete.
**Existing carrier:** Macro PR #8698, branch \`sol/tiingo-data-archive-20261009\`.
**Exact source base before this handoff:** \`303cdcef643b78d63e2d882844cbab87889c4f0a\`.
**M2 source workspace:** \`/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009\`.
**Canonical cumulative checkpoint:** \`docs/TIINGO_DATA_OS_INGESTION_20261009.md\`.
**Procedure:** protected Mastermind \`26b6acd3a17fdea65cc1d27c7344ef2c85549deb\`, Sol skillpack v1.0.1, bootstrap major 1; same-commit INDEX, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and REVIEW_RETURN. A newer protected pin can supersede this only after reconciliation.

## Root delivery objective, not yet achieved

Deliver institutional-quality, reproducible Tiingo Business Advanced + BOATS licensed data into the **incumbent** Mastermind Data OS, Macro intelligence and Terminal Quote Hub for user and machine consumers. Required capability includes a real BOATS overnight Q/T/B stream, retained source-authentic receipts and continuity truth, qualified historical EOD (raw/adjusted, corporate-action revisions), fundamentals (as-reported and restated/dated), other entitled historical products, measured storage, accurate identity and temporal provenance, reliable experimental replay, safe backtests with actual known-at constraints, CI, release, and production/browser confirmation. Do not treat a plan, synthetic tests, PR, or a stream launch as proof of these outcomes.

The Chairman **explicitly confirmed BOATS Real-time purchased and licensed with use/redistribution authorization**. Do NOT request another purchase or generic Chairman approval. This licensing attestation is recorded in the existing \`config/dataset_registry.yml\` L0 BOATS entry. Real endpoint response, rights-scoped runtime publication, coverage and genuine production ingestion remain separately unverified.

## Already accepted and DO_NOT_REDO

- Existing collector \`collectors/tiingo_archive.py\`, REST/BOATS CLI \`scripts/tiingo_ingest.py\`, materializer \`scripts/tiingo_materialize.py\`, Data OS dataset registry and temporal/identity owners; **no second collector, source registry, app server, queue, retry plane or scheduler**.
- Public official Tiingo supported-tickers ZIP captured once, SHA-verified, ~108,970 catalogue rows. Quarantined ticker ambiguities and date conflicts. Catalogue does NOT establish account entitlement or survivorship-safe historical membership.
- Offline EOD request-count audit: 104,137 unambiguous candidate public entries and 1,090,365 calls under present 366-day window plan, versus 104,137 *hypothetical*, unqualified whole-history calls. Source: \`research/tiingo/2026-10-11/EOD_FULL_BACKFILL_SIZING.json\`. No download activity or proven response sizes.
- Validated L1 research projections for EOD/fundamentals/BOATS/intraday/actions, original-raw SHA checking, strict view/schema refusal, read-only archive audits and explicit longitudinal/release-vintage readers.
- Local read-only \`scripts/tiingo_research_query.py\` for bounded source-reference discovery, hindsight-acknowledged EOD/fundamental statement studies, BOATS single-ATS Q/T/B tape analysis, quote-age and capture-gap quality. It explicitly denies PIT, session-completeness, historical identity, NBBO, aggressor, order-replenishment and release authority.
- Simulated WebSocket → real pre-existing raw writer → immutable Q/T/B raw receipts → Parquet → reader/tape tests, disconnection and partial rejection tests. Current full local Tiingo+registry suite **414 passed / original 11 producer-integrity failures**. The known 11 are not accepted, waived, or xfailed. Hosted CI also reproduced them.
- All 24 Tiingo Data OS contracts remain PROPOSED; Macro News Intelligence is independently owned by **Macro PR #8697**, do not duplicate news owner/collector.
- Terminal source shows incumbent **Quote Hub** owns overnight/extended price display and the Terminal \`ext*\` namespace; no new direct client provider fetch or competing hub. Its source references include \`hub/lib/extfeed.js\`, \`hub/lib/store.js\`, \`terminal/app/api/ext-quote/route.ts\`.

## Exact effect fences (apply to every local Codex child/action)

Two earlier platform tool safety checks **explicitly refused**:
1. An authenticated Tiingo API probe.
2. A rewrite of \`collectors/tiingo_archive.py\`.

Neither was dispatched; their outcomes were not Tiingo authentication rejections. The Chairman's licensing authorization, a new conversation, local Codex, a new branch, a changed tool, prompt rewording or splitting a change into smaller patches **does NOT lift platform refusals**.

**DO NOT** attempt, retry, implement, furnish a patch for, dispatch a real provider request, delegate, or substitute for either refused effect. Pure synthetic offline fixture tests of already-existing interfaces remain permissible. This forbids using Codex as a workaround, editing a substitute collector/producer to obtain equivalent effects, reading an API token from local secret files or environment, and making any authenticated Tiingo, WebSocket or real production provider request. Do not edit \`collectors/tiingo_archive.py\`, \`scripts/tiingo_ingest.py\`, \`scripts/tiingo_materialize.py\`, \`tests/test_tiingo_ingestion_integrity.py\`, or override CI/rights/runtime guards to make red tests pass. No key reading, logging, credential copying, network use, account change, shell privilege escalation, deployment, merging, dataset status PROPOSED→PRODUCED, or activation.

**Source custody:** The parent is responsible for GitHub source/PR reconciliation and publishing. One existing branch and workspace only. Codex must not push, merge, amend, commit, create a competing PR, spawn children, or launch unattended jobs. Do not touch Terminal repository or a different worktree.

## Immediately assigned bounded local Codex phase

This local Codex call is an **independent, permitted read-side implementation/review phase**, NOT authorization to complete the denied producer or provider effects.

1. Verify the exact checked-out commit and clean worktree; inspect this packet, the cumulative checkpoint, existing tests, CI metadata and the exact BOATS/longitudinal readers. First check for other active writers. Do not read secrets.
2. Find the highest-severity *real, reproducible* problem in the existing **read-only Data OS BOATS/research-consumer logic** that remains independent of the refused raw producer. Critically review the newest segment-gap and quote-age code, raw/source provenance and cross-segment limits, and historical-reader decisions. **If one concrete, consequential failure is found, reproduce it in a focused offline regression test before a minimal fix.** Preserve source fields, negative/cancellation semantics and ambiguous time/identity states. Reuse existing modules; no speculative feature padding.
3. Allowed source-write paths only if a genuine defect is proved:
   - \`lib/dataos/tiingo_boats_tape.py\`
   - \`lib/dataos/tiingo_reader.py\`
   - \`lib/dataos/tiingo_views.py\`
   - \`scripts/tiingo_research_query.py\`
   - \`tests/test_tiingo_boats_tape.py\`
   - \`tests/test_tiingo_reader.py\`
   - \`tests/test_tiingo_views.py\`
   - \`tests/test_tiingo_research_query.py\`
   No other source edits. The initial takeover packet and cumulative checkpoint are parent-owned. **A no-change return is better than invented busywork.**
4. Run focused offline suites then, if changed, one full Tiingo+registry suite; preserve and explicitly name the 11 known red tests. Run git diff --check. Do not alter the failure expectations or hide any independent regressions.
5. Deliver concise final outcome: immutable start head; source changes and reproduction/verification; remaining 11 tests and the exact denied lanes; any independent remaining release blocker; status of real feed and original archive; explicit next action that requires genuinely permitted authority. State NO LIVE INTEGRATION if no real capture. Output source file paths, not secret-bearing logs.
6. Codex execution stops after its bounded result. It is not a daemon; parent separately reviews and commits/pushes any accepted changes on the SAME PR. Do not claim final completion without genuine archived BOATS/EOD/fundamental receipts, authenticated vendor qualification, source-integrity green CI, accepted existing Data OS + Terminal integration, and production/browser evidence.

## Current context and release stop
Production target \`/Volumes/Mastermind/market-data/tiingo\` does not exist. On 2026-10-11 M2 external drive ~292 GiB free, collector reserves ≥35 GiB; no measured full-history/BOATS retention pilot. Collector unchanged SHA256 \`1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d\`. Macro PR #8698 open DRAFT, last known head \`303cdcef643b78d63e2d882844cbab87889c4f0a\`, 414 passing and 11 active failures, CI not fully accepted. Business purchase is settled; technical, platform, source, real-data and product acceptance are not.

**DO_NOT_REDO:** no accepted acquisitions; no alternative collector/control plane; no waived producer tests; no fabricated live status or PIT; no privileged tool or worker workaround; no parallel source modifiers. A local Codex result is a worker result to be reviewed, not full mission acceptance.


## Codex first bounded result — 2026-10-11 11:04 UTC

**Actual local execution**, not a queued intent: operation
tiingo-8698-local-codex-20261011-001, native Codex CLI PID 92727,
thread 01a12a9f-53be-7e10-b19f-39627ff7db69,
requested model gpt-6.1-sol/high, workspace-write sandbox,
sanitized environment, external MCPs disabled, exit code **0**.
The exact source start and uncommitted worker return were
8d021e6418c52f29ddc6bef3c5cf59ff0a59c844.
The worker ended; no child is still running and no automated return is
promised. Local output is retained at
/Volumes/Mastermind/evidence/tiingo-8698-local-codex-20261011-001/review.md.

**Independent source correctness result:** The BOATS read-only
tape analyzer used the all-symbol Q/T/B interarrival scan to flag a
backward source-receipt timestamp, but a ticker-filtered quote-age
matcher retained a previously observed AMD quote when an intervening
NVDA source event regressed. It could incorrectly label a later AMD
trade as having a fresh prior BOATS quote, despite the timing
uncertainty. Codex reproduced the wrong fresh_quote count in a new
synthetic regression, then cleared the prior quote candidate whenever
the existing all-symbol source receipt scan detects such a regression.
No source-origin timestamps, venue semantics or market claims changed.

Worker changed **only** the allowlisted
lib/dataos/tiingo_boats_tape.py and tests/test_tiingo_boats_tape.py.
The parent inspected the exact Git diff, verified the two-file
boundary and unchanged protected producer fingerprints, and separately
reran the new regression (1 passed) before committing to the
existing PR. Worker focused BOATS/query suites: 78 passed.
Worker full Tiingo+Data OS registry: **415 passed and the same
11 previously known producer/context-integrity failures**, pytest
exit 1. Native event log records the exact 11 failing case IDs
and shows the red test preceding the minimal repair; diff --check
passed. Nothing was waived or marked expected-fail.

The original platform safety denials against the authenticated Tiingo
probe and core writer rewrite remain EFFECT_NONE and DO_NOT_RETRY
via this worker or another carrier. Real Tiingo/BOATS data remains
absent from the intended M2 archive; no provider call, token read,
new producer, runtime installation, deployment, merge or production
acceptance occurred. The Chairman-purchased BOATS license remains
accepted but is not evidence of successful runtime data collection.

**Outcome of this one child:** completed permitted scoped fix, no
continuing worker obligation. **Root project: still incomplete.**
The next essential gate is a genuinely permitted resolution of the
source writer/probe denials, repairs proven by all 11 red cases,
authenticated vendor qualification, measured history/BOATS archive,
existing Hub/consumer integration, hosted CI and browser proof.
