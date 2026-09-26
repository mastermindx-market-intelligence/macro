---
key: CRYPTO-VECTOR-R2-20260926
question: >
  After the Chairman rejected Crypto + Bitcoin R1, what design and production
  contract should govern the replacement experience without creating new
  decision, chart, snapshot or alert authority?
answer: >
  R2 is a chart-led research experience: preserve P0A BitcoinDecisionState as
  the final allocation authority, reuse the existing Lightweight Charts,
  snapshot and Alert Center owners, expose evidence and data-quality limits,
  distinguish valid zero from unavailable state, and progressively reshape the
  existing governed Vector shelves rather than building a parallel product.
rationale: >
  R1 simplified away too much analytical depth and remained card-heavy. The
  recovered Vector research and live audit support a quieter instrument with
  synchronized charts, explicit source semantics, point-in-time replay and
  progressive depth. Truth and authority boundaries must improve at the same
  time as visual quality so missing model state cannot become an apparent
  0% cash decision and design work cannot silently fork canonical engines.
alternatives:
  - option: >
      Implement the rejected R1 card layout directly.
    why_not: >
      Chairman explicitly rejected R1 and commissioned a deeper chart-led
      replacement.
  - option: >
      Create a new chart engine, decision model or alert system for R2.
    why_not: >
      Existing canonical owners already provide those capabilities; duplicating
      them would create competing control and truth planes.
evidence:
  - >
    Paper R2 page p-R-0 in file 01M2WGNCX9475G79JRKJTCM08P contains five
    native editable, screenshot-reviewed boards and the builder release contract.
  - >
    research/CRYPTO_VECTOR_R2_DESIGN_AND_RELEASE_CONTRACT_2026-09-26.md records
    the recovered research, live audit findings, prototype proof and release
    gates.
  - >
    Commit 52937b45eb61f1ebe360fca086fb6b324f6e51a4 adds the qualified replay
    contract, source inspector and fail-closed allocation-history gate.
  - >
    Commit a8c0c6a129f06ad79abb4555f14fb1fed9f9ac9f reshapes the governed
    Vector front door around R2 research navigation and plain-language hierarchy.
affects:
  - "WS:CRYPTO-INTELLIGENCE"
  - crypto-vector-r2-20260926-sol-001
  - templates/vector.html.j2
  - scripts/build_vector.py
  - site/vector_chart.js
  - tests/test_vector_r2_data_boundary.py
  - tests/test_vector_r2_frontdoor.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-26
---

# DEC-CRYPTO-VECTOR-R2-20260926

Recorded 2026-09-26 by Sol under the Chairman's current Crypto/Bitcoin redesign commission.
Existing owner/workstream: `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md`.
Operation: `crypto-vector-r2-20260926-sol-001`.
Projection/evidence: Macro Draft PR #8050, branch `sol/crypto-vector-r2-20260926`.

## Ruling

The Chairman rejected R1 for insufficient beauty, sophistication, understandability and production readiness. Do not implement R1 as an accepted reference. R2 is the new proposed visual direction; Chairman acceptance and production certification are not claimed.

The R2 design uses chart-led research rather than a card-wall: synchronized price/risk/exposure, relative price-ratio comparison, selected-date evidence, separate current versus historical model state, light/dark compositions and a purpose-designed mobile layout. Preserve useful existing analytical depth and the accepted P0A BitcoinDecisionState authority.

## Durable design/evidence anchors

Full source, feature and release contract: `research/CRYPTO_VECTOR_R2_DESIGN_AND_RELEASE_CONTRACT_2026-09-26.md`.
Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-R-0`:
https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-R-0

Nodes: Bitcoin light `1EQ1-0`; Crypto light `1FL0-0`; Cycle Lab dark `1FRD-0`; Bitcoin mobile `1G0I-0`; builder blueprint `1GKA-0`. Five boards screenshot-inspected. Shared tokens `bba69475` unchanged.

Mastermind law pin `a31f49f4056943124cc0e7e42349e46feee444c7`; Macro audit pin `7150f29a765387f1c14fbae086314af6e0d6bddc`.

Offline preview artifact SHA-256 `80f95a5f241eb3f07f9e454168197059e16409848517e6888043e553dece5044`. Twelve core tests and 44 offline authored-DOM/browser checks passed. Local URL navigation was policy-blocked; no browser policy changed. Offline DOM proof is not real-route acceptance. Separate M2 audit successfully loaded both current public routes at desktop width; actual audit exceptions are documented in the research contract.

## DO_NOT_REDO / effect frontier

Do not rebuild accepted P0A authority, revive failed macro-allocation gating, recreate R1, rescan recovered research without a changed question, or duplicate existing chart/snapshot/alert owners. Resume verified R2 effects. At the original R2 design checkpoint, no production application files, model output, live alert, deployment, trade or durable worker had been changed/started; the later Extra High continuation below records the subsequent Bitcoin production commits. No modifying effect is known EFFECT_UNKNOWN. Denied action/target paths remain fenced as documented in the contract; one working action is not blanket capability evidence.

## Remaining release work

Bitcoin Slice 0 plus the narrow Slice 1 candidate is now published and awaiting exact-head CI/browser proof: qualified chart contract -> existing chart adapter -> exact source inspector -> invalid-state suppression, plus the R2 front-door hierarchy. The Crypto template lane remains held behind active #7645; shared theme changes remain held behind #7849. After Bitcoin proof, investigate and quarantine implausible ranked returns, distinguish altseason definitions, label source clocks, add Crypto budget/return-window consistency tests on a reconciled carrier, and close the recorded H5 budget bypass without replacing the canonical total-budget authority.

Full acceptance still requires real data integration, production-path screenshots/results, EN/ZH and both themes, accessibility/task completion, failure fixtures and cost/performance evaluation where relevant. No return series is fabricated to fill a performance card. No synthetic fixture is production strategy authority.

Classification: CHECKPOINTED_CONTINUATION at R2 design review / production integration boundary. This is not completion or custody transfer. Sol retains ownership. Next phase recommendation: Extra High for iterative implementation and real-route browser tests, after required capability/ownership verification. No mode self-switch, daemon or watcher is claimed.

## Extra High continuation — 2026-09-26

The Chairman enabled Extra High and continued the commission. Source collision review found the Bitcoin Vector production paths unchanged since the R2 audit pin; active PR #7645 still owns Crypto table/template work and #7849 still owns shared theme tokens, so this continuation deliberately advances Bitcoin only without touching those paths.

Two production commits now exist on PR #8050:

- 52937b45eb61f1ebe360fca086fb6b324f6e51a4 — creates mastermind.vector_risk_strategy.v2, preserves genuine 0% allocation separately from unavailable state, refuses to infer trade markers across missing decisions, exposes exact source/unit metadata without inventing availability timestamps, suppresses replay when required history is incomplete, and places the source contract in the real Vector study surface.
- a8c0c6a129f06ad79abb4555f14fb1fed9f9ac9f — keeps the exact governed S1–S6 roots but removes their decorative rail/card-wall treatment, adds Overview/Cycle/Strategy/On-chain/Derivatives research navigation, leads with a plain-language market read plus the canonical final model allocation, and keeps deeper evidence progressively available.

Local pytest execution for the new contract tests was explicitly refused before dispatch and was not rerouted or disguised. Earlier static Python/JavaScript/Jinja syntax verification succeeded on the first slice; a later combined front-door static verification call was separately refused before dispatch and was not retried. Canonical PR CI is therefore the test owner for these published candidates.

The first published slice exposed one fence failure unrelated to implementation logic: this decision record lacked the required YAML frontmatter. All other fence components in that run passed. This record has now been repaired in-place rather than creating a second decision owner. Production acceptance remains false until exact-head CI, generated-page/browser proof, and the remaining truth/data gates pass.
