# Market fragility: research-to-consumer delivery

Operation: `web-market-fragility-20261113`.
Assignment: Chris's 2026-11-13 request in the VolSignals discussion to research, implement and verify the complete fragility capability. This is not an instruction to replace T3 or the risk control plane.
Source: Macro `f3a162741e2d6e57be19febf2e7e9799e39be6d8`; governing Mastermind `fc91f33ccce3e8f18c78546f03c955c2ced0c704`, Sol Skillpack 1.0.1.
Related owner: `WS:GREY-DEER-RISK-INTELLIGENCE`. This source plan transfers no live writer, release hold or unfinished program acceptance. Organizational link: the workstream's 2026-11-13 additive gamma-fragility section points to this plan. This is a knowledge link, not a new execution admission or program takeover.

## Outcome / DONE_WHEN

A real canonical source reaches an existing machine consumer as an honest, non-directional market-structure observation, with source lineage, clock/freshness limitations, same-series persistence/oscillation metrics, missingness and a reproducible validation path. Distinguish modeled amplification from predictive usefulness. Code/tests/PR alone are not live consumer acceptance. No trade, rank, sizing, auto-exit or risk-policy authority is added.

## Reuse and boundaries

Reuse `engine/market_gamma.py`, `cboe/gex_SPX`, `lib/nyse_calendar.py`, regime publication, existing risk-envelope ownership and Mastermind's `get_regime` consumer. Preserve `market_gamma.view()` and existing risk/scoring semantics: do not silently change its legacy missing-flip behavior. The additive observation can report a known direct engine gamma sign even when a flip is absent. Never infer inventory from volume, sign from distance to flip, or an SPX dollar percentile from reconstructed SPY history. Do not copy VolSignals' proprietary implementation.

Use pure functions and thin adapters, not a new service, store, scheduler, queue, fused risk score or trading controller. Existing snapshots remain the publication path.

## Phases

P1 - Research and contract (in progress): primary-source mechanics and counterevidence; freeze units, lineage, observation/availability/session clocks and strict missing/invalid semantics; determine actual PIT data coverage.

P2 - Canonical observation (after P1): direct same-source SPX regime; current sign/freshness separately from trailing short-share, adjacent-session sign changes, streak and maximum positive run. Invalid/non-session/future/duplicate/conflicting rows cannot become benign readings, zeros or contiguous streaks. Missing flip is independent of gamma sign. Optional volatility/liquidity retain their own clocks/units; unsupported sources remain absent.

P3 - Validation (after P2): invariants, serialization, ordering, gaps/duplicates, real consumer integration and unchanged legacy risk outputs. Audit/replay command with input digest, usable/missing records and availability-clock qualification. Research protocol: chronological holdout, volatility-only/gamma-only ablations, episode-honest N, overlap purge, uncertainty and prospective criteria. Never claim alpha from reconstructed vintages or synthetic tests.

P4 - Consumer/release (after P2/P3): publish through incumbent regime artifact, expose in Mastermind regime response without recomputing risk; self-review, affected checks, one owned qualified PR per changed repo, actual release controls, exact merged/deployed and returned-payload proof. Report remaining scientific/data/production gates independently.

## Delegation / custody

Principal retains scientific architecture and acceptance. Use bounded workers when admitted. This session exposes no native Web subagent or direct T3 tool. Fabric capability reports adapter unavailable. Executive read failure does not establish submit availability. Remote Desktop Commander reports M2 offline; Studio Direct source tools work but its shell surface is not an agent-handoff interface. No bypass or invented workers. Direct work reason: PRINCIPAL_JUDGMENT / NO_ELIGIBLE_PRE_EFFECT_WORKER until an eligible worker route is proven.

The original acquisition returned unqualified. Same-operation `mmx-workspace status` reconciled a clean acquired base, branch `sol/web-web-market-fragility-20261113`, path `/Volumes/Mastermind 2/agent-workspaces/macro/web/web-market-fragility-20261113`. No replay/replacement workspace. Preserve other sessions' shared edits and held PRs.

## DO_NOT_REDO / stop conditions

No replacement gamma engine/calendar/history/risk envelope/provider router. No legacy score changes, trading activation, held-research rewrite, fake independent review, secrets exposure or uncertain-effect replay. No provider/spend expansion. Missing historical availability clocks block predictive promotion, not honest observations or independent source/tests.

## Research anchors (scope, not current-market predictions)

- Cboe, Evaluating the Market Impact of SPX 0DTE Options (2023-09-08): https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options
- Cboe, 0DTEs Decoded (2025-05-02): https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact
- Cboe VVIX: https://www.cboe.com/us/indices/dashboard/vvix/
- VolSignals official documentation: https://vs3d.volsignals.com/home/getting-started

Add actual code revisions, evidence and remaining acceptance at material milestones.


## Material milestone: source, research and pre-release consumer

P1 source research is complete for the bounded observation: Cboe mechanics/counterevidence, VolSignals' own platform basis, the original 2025 inventory study and VVIX definition are reconciled in `RESEARCH_AND_VALIDATION_PROTOCOL.md`. P2 source implementation is complete locally: strict `engine.market_fragility`, additive canonical gamma/regime/market-structure adapters and separately dated existing VIX/VVIX/realized-vol/macro-liquidity context. Unsupported depth and spot-scenario sensitivity remain explicitly unavailable.

P3 has deterministic, adverse-input, real-parquet and existing-consumer regression coverage. Self-review found and repaired optional-observer errors leaking into legacy publication; unavailable optional context now preserves the core. The paired Mastermind source is isolated on operation/branch `web-market-fragility-consumer-20261113` / `sol/web-web-market-fragility-consumer-20261113`, based on the governing SHA above. It validates schema, source, units, authority and validation claims, re-ages data at read time, and preserves qualifiers over actual SDK MCP transport. This is author SELF_REVIEWED work, not a claim that an independent worker ran.

A read-only production-source capture is recorded in `PRODUCTION_SOURCE_AUDIT_2026-11-13.json`: 95 rows, source session 2026-11-12, SHA-256 `39a0ea3a33dabde22aefa65bcb5aa465e916bcdc95898773aea3410b46edda1c`. The trailing 20-session window has 15 known and five missing observations. The existing validator remains building-history, and no historical availability clocks exist in the summary. This blocks predictive promotion, not truthful current observation.

P4 remains open at this milestone: publish qualified owned PRs through each repository's existing release owner, reconcile merge/deployment, then verify the actual published artifact and actual Brain `get_regime` response. Never substitute a local test fixture, green CI or a merge for that live proof. Exact release results belong in the original PR receipts and the final delivery record. No provider configuration, trading policy, production data correction, collector or scheduler has been changed.
