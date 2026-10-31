---
key: CATALYST-EARLY-DISCOVERY-NEEDS-A-SEPARATE-ATTENTION-PATH
claim: >
  At Macro source 1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9, constructive theme
  confirmation uses N_STREAK=2 and advances at most once per session date;
  same-day rebuilds do not satisfy that confirmation.
falsifier: >
  Inspect engine/theme_alerts.py lines 55-105 and its confirmation consumer at
  that exact source, or a later materially changed accepted implementation,
  showing constructive confirmation advancing twice within one session date.
so_what: >
  Implement an explicitly provisional early-attention path through the existing
  alert owner rather than removing the confirmed channel's session-date rule.
  Use the Catalyst-to-Opportunity research package for the event-or-market
  discovery, Radar, evaluation and Fable implementation contract.
kind: constraint
verified_at: 2026-10-17
verified_by: >
  Connected GitHub fetch_file for engine/theme_alerts.py:55-105 at
  1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9; source contains N_STREAK=2
  and the session-date advancement constraint. No live runtime test asserted.
scope:
  - engine/theme_alerts.py
  - engine/entry_radar/
  - research/catalyst_opportunity/2026-10-17/
confidence: verified
---

# Early attention is a separate channel, not a weaker confirmation rule

The source finding is verified at the stated commit. The architectural response is the
CEO research specification, not proof that an early detector is already implemented or
that the existing confirmation method is empirically optimal.

Read [the research package](../../research/catalyst_opportunity/2026-10-17/README.md)
and [final review](../../research/catalyst_opportunity/2026-10-17/07_FINAL_REVIEW.md).
The parent remains Mastermind #1181. No new workstream or execution registry was created.

The package covers fourteen logical capabilities, thirty-six work packages, all seven
specialist domains and sixty-four adversarial acceptance requirements. Static plan checks
are not product tests. The October rally remains a development case, not a proven
historical executable trade. Current source, identity, data rights and live consumer
availability still require their actual acceptance evidence.

Fable was not dispatched by this research. After deliberate commissioning, the receiver
executes WP01 and advances the independent market-first path while event/economic inputs
and prospective observation are connected. Preserve real writers and original refused or
uncertain effects; historical author labels are not additional approval gates.
