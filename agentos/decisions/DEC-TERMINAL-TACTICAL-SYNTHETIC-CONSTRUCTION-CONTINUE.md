---
key: TERMINAL-TACTICAL-SYNTHETIC-CONSTRUCTION-CONTINUE
question: Must R1-B synthetic candidate construction wait for R1-A shared-source release?
answer: >
  No. Permit the existing #7274 owner to construct and test frozen v4 candidate/confirmation mechanics on
  path-disjoint pure code with synthetic-only inputs. Retain the #7270 shared-source/review gate for empirical
  registration, market-data/outcome execution and every release or promotion. No scientific rule is changed.
rationale: >
  The earlier blanket implementation wait conflated a source-release dependency with independent synthetic
  construction. The pure constructor imports no unaccepted R1-A code and modifies no TrialLedger, provider,
  production event registry, live evaluator or CI authority. Continuing it advances the Chairman-approved product
  while preserving reproducibility and all empirical/independent-review gates.
alternatives:
- option: Wait on every implementation step until all R1-A checks and review conclude
  why_not: It unnecessarily stalls path-disjoint synthetic work and repeats a no-capability-delta cycle.
- option: Run empirical R1-B outcomes immediately
  why_not: Full-grid registration and the existing shared-source/review gate have not cleared.
evidence:
- 'Chairman continuing TTI delivery instruction, 2026-09-19; no new approval required.'
- 'Same-carrier Sol ruling: Macro #7274 comment 5745472291.'
- 'Construction head f6738dffff1516216b552d426f956f8f6551248d: 40 new tests, 192 detector-suite passes, full Radar 1520 passed/3 skipped; no market inputs or TrialLedger change.'
- 'Frozen v4 config SHA256 24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19 and prereg SHA256 a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3 remain unchanged.'
affects:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: '2026-09-19'
---

Supersedes only the earlier STATUS/workstream scheduling instruction holding all implementation. The frozen v4 preregistration, TrialLedger accounting, scientific ownership, independent review, data qualification and release gates remain controlling. This is not a waiver of a failed test or permission to promote an unvalidated strategy.
