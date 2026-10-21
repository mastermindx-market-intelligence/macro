---
key: OPTIONS-R1-ONE-JOURNEY-ON-EXISTING-OWNERS
question: >
  How does the Terminal surpass GammaPulse's rotation → positioning → research loop:
  as a new options workspace with its own stores and evaluators, or as one continuous
  journey composed on the owners the Terminal already has?
answer: >
  One journey on existing owners. Sector Central → holding → expiry/strike → chart →
  matched change → save → watch → review runs across the sector rotation map, the
  options exposure workspace, the ChartPanel options-levels overlay, Market Memory
  changes, the investigation workspace, the alerts engine and the Supabase
  investigation revision store. No new store, evaluator, watcher, queue or cron is
  added; what an owner cannot supply is rendered as its honest absence
  ("not supplied by the flow owner", "method not stated by source", "no evaluator in
  the alerts owner"), never inferred and never shown as zero.
rationale: >
  Every owner already carries the data, the entitlement boundary and the failure
  states the journey needs; a second implementation would fork truth (two evaluators,
  two evidence registries, two clocks) and could not be proven against production.
  Composing on the owners keeps one responsive Terminal, one alerts transport, one
  revision store with its validator, and lets each wave ship through the ordinary
  commit → PR → CI → merge-on-green → git-gated deploy chain with live verification.
  Surpassing GammaPulse comes from continuity and provenance (origin strip, closed-bar
  snapshot references, observed book changes with their clocks, revision history,
  condition watches that say what they evaluate), not from a wider feature list.
alternatives:
  - option: A standalone options research app with its own positioning store and evaluators
    why_not: >
      Duplicates entitlement, revision and alert semantics; cannot reuse the installed
      validator or the alerts engine; violates the one-responsive-Terminal contract.
  - option: Infer what owners do not publish (squeeze probability, package confidence, band method)
    why_not: >
      Unknown rendered as a number is a false claim; the frozen rules forbid inferred
      causal headlines and confidence levels on expected moves.
evidence:
  - "terminal/docs/OPTIONS_R1_PROGRAM.md (mission, exit gate, wave plan, rulings)"
  - "terminal/docs/OPTIONS_R1_W1_FREEZE.md, OPTIONS_R1_W2_FREEZE.md, OPTIONS_R1_W3_FREEZE.md § 0 owner maps with file:line evidence from read-only census lanes"
  - "Terminal PR #1096 (W1, merged, live-verified on app.mastermind-x.com 2026-10-21), PR #1103 (W2), the W3 PR"
  - "Macro PRs #9991 / #9992 (W2 producers: holdings coverage, relative-trend rotation)"
affects: ["WS:OPTIONS-R1", "terminal/components/sector/**", "terminal/components/options/**", "terminal/components/flowdesk/**", "terminal/components/vol/**", "terminal/components/investigation/**", "terminal/components/eodcontext/**", "terminal/lib/alerts*", "terminal/supabase/migrations/0039_*", "terminal/supabase/migrations/0040_*"]
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-10-21
---

## Grounds

The commission (FABLE_HANDOFF, MASTERPLAN §4–§7, FEATURE_MATRIX) asked for a journey,
not a page. The W1–W3 census lanes mapped every owner with file:line evidence before a
line was written, and each freeze names what the owner can and cannot supply. Where an
owner is missing a field (per-print receipt clock, earnings time of day, an
`exposure_change` evaluator), the lane is HELD or a follow-on, and the UI says so.
