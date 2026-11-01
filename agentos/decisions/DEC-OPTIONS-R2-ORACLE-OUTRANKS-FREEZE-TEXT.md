---
key: OPTIONS-R2-ORACLE-OUTRANKS-FREEZE-TEXT
question: >
  When the Options R2 F1 contract freeze prose and the attached quant oracle
  (terrashade-quant-oracles/1.0.0, 499/499 self-checks) disagree about a formula,
  which one governs the Terminal implementation?
answer: >
  The oracle governs. The Terminal node reducer ports the oracle literally
  (distance_fit is 0 below 0.1 EM, ramps to 1 at 0.5 EM, stays 1 to 2.0 EM,
  decays to 0 at 4.0 EM, and returns null on a negative or non-finite distance;
  scanner_score = (0.55 * strength + 45 * fit) * penalty with the oracle's reason
  vocabulary collected without short-circuit). The freeze text is amended as an
  erratum where it said "capped at 1" and where it typed distanceFit as a plain
  number.
rationale: >
  The oracle is executable and self-checked against 499 golden cases; the freeze
  prose was a human paraphrase of it written for the lanes. A paraphrase cannot
  outrank the artifact it paraphrases, and shipping the paraphrase would have
  silently changed candidate ranking between 2.0 and 4.0 EM. The independent F1
  audit flagged the divergence and the repairs lane (R1 to R12) aligned the
  module to the oracle before PR 1109 was opened.
alternatives:
  - option: Follow the freeze text and amend the oracle to match
    why_not: The oracle is the commission's quantitative source of truth; editing it to match a paraphrase inverts the evidence chain.
  - option: Ship both behaviours behind a flag
    why_not: Two rankings for one scanner contradict the commission's single-engine law and leave the discrepancy unresolved.
evidence:
  - >
    Terminal PR 1109 (branch claude/r2-pr1-dex-reducer-1021, head 52aa270aa): lib/exposureNodeReducer.ts
    distanceFit and scannerScore, ported oracle suite in lib/__tests__/exposureNodeReducer.test.ts.
  - >
    Oracle file quant_oracles.py sha256 e23eb6a3 (prefix), version terrashade-quant-oracles/1.0.0,
    self-check 499/499; staged read-only on the fabric host at ~/lanes/ext/quant_oracles.py.
  - >
    Opus F1 audit (read-only) returned REPAIR_REQUIRED on the first lane output; repairs R1 to R12 recorded
    in the PR 1109 body under "Audit and repairs" and "Freeze errata".
affects:
  - "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
  - "terminal:terminal/lib/exposureNodeReducer.ts"
  - "terminal:terminal/lib/exposureMapProjection.ts"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-21
---

## Context

The R2 commission (acceptance schema `mastermind.options.parity-research.v1`, rows P01 to P76) shipped a
contract freeze for the F1 wave (`F1_CONTRACT_FREEZE.md`) alongside the oracle. Two lanes built the DEX
validator and the node reducer from the freeze; the audit compared the result to the oracle and found the
distance-fit tail and the refusal signature wrong. The repairs lane fixed both and the integration branch was
re-gated (vitest 7 files / 159 tests, tsc, eslint, plain-language guard) before PR 1109.

## What this does not decide

The oracle covers the scanner and distance fit only. The local-scenario engine contract
(`engine_contracts.json`, `local_scenario`) remains a separate owner and is composed through the existing
`scenarioGrid` reducer; nothing here changes exposure units or the matched-report semantics.
