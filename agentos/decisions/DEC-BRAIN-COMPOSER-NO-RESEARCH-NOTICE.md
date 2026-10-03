---
key: BRAIN-COMPOSER-NO-RESEARCH-NOTICE
question: Should the Brain composer show the full research disclosure in a purple row?
answer: >
  No. Remove the complete notice, its cost subline, and its row in both languages
  and themes. Do not replace it with a banner, tooltip, or smaller disclosure pill.
  Keep Fast/Pro, quota display, explicit /research entry, and backend research
  authority and billing constraints unchanged.
rationale: >
  The Chairman explicitly requested complete removal on 2026-09-21 after reviewing
  the active-chart composer. The large notice obstructs the primary interaction.
  This is a placement reversal, not permission to change research or trade authority.
alternatives:
  - option: Hide the existing row with CSS
    why_not: Leaves dead UI and permits the notice or empty spacing to return.
  - option: Replace the notice with a smaller warning
    why_not: Contrary to the explicit request for complete removal.
evidence:
  - 'Chairman screenshot and direct instruction, 2026-09-21: remove this purple message completely.'
  - 'Source: templates/mm_brain.js at 14335094062d3f73fd169778a447727640ded139; composer mmb-rrow and mmb-rpill.'
  - 'Regression coverage: tests/test_mm_brain_asset.py.'
affects: [templates/mm_brain.js, site/mm_brain.js, site/theme.js, tests/test_mm_brain_asset.py]
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-21
---

## Scope and supersession

This supersedes the W9B F11-8 composer sentence-row treatment only. The F11
MO-PAID-031 answer-level authority ceiling and server-side research routing,
entitlement, billing, and signal/ranking restrictions are not modified.
No engine or gateway file is part of this change.

## Delivery identity

Operation: remove-brain-purple-notice-20260921.
Carrier: macro, claude/remove-brain-purple-notice-20260921.
Skillpack: Mastermind protected master 412deca03631f9768158205bc2802b032aa0a1cc.
Direct execution: LOWER_TOTAL_OVERHEAD; no worker was dispatched.
This record is the placement decision, not a claim of deployment or acceptance.
PR checks and live browser evidence establish delivery separately.

Do not reintroduce the composer notice to satisfy the superseded snapshot tests.
