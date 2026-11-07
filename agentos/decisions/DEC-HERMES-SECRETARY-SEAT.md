---
key: HERMES-SECRETARY-SEAT
question: >
  Should Mastermind establish a Hermes-native Secretary seat for company
  operations, distinct from the existing Grok Secretary, and what authority
  envelope should it hold?
answer: >
  Yes. Chairman directive of 2026-11-06 establishes the Hermes Secretary seat
  (Hermes agent, profile `secretary`) to run company operations for the Chairman:
  channel and repo monitoring, records, drafts, and cadence. Its authority
  envelope is A0-A2 of the Mastermind authority ladder (telemetry, advisory,
  display-only); governance records and docs ship by PR and are never
  self-merged. The seat definition lives in
  Mastermind/docs/HERMES_SECRETARY_ROLE.md.
rationale: >
  The Chairman asked for a standing, Hermes-native operations seat with its own
  Slack account, Linear access, and GitHub PR rights. Writing the envelope down
  now fixes the one-source rule (Charter P7) before habits diverge: the seat is
  operations-only, never touches portfolio effects above A2, and never merges
  its own PRs, so no new control path is created.
alternatives:
  - option: Extend the existing Grok Secretary seat instead
    why_not: >
      The Grok Secretary serves the ChatGPT-account side with its own runtime
      and channel norms. Folding a Hermes host agent into it would blur
      identities and tooling without Chairman instruction to do so.
  - option: Keep the seat informal (chat directive only, no record)
    why_not: >
      Authority inferred from conversation drifts. Without a written envelope
      the seat's limits would be re-litigated every session.
evidence:
  - "Chairman chat directive, 2026-11-06, Hermes secretary profile session: 'You're the future Secretary of Mastermind'"
  - "Mastermind/docs/evidence/2026-11-06-unified-project-instructions.txt — existing Grok Secretary seat and #dotsandgroksecretary norms"
  - "Mastermind/AGENTS.md — hierarchy and executive contract"
  - "Mastermind/config/authority_map.yml — A0-A7 effect ladder definitions"
affects: ["Mastermind/docs/HERMES_SECRETARY_ROLE.md", "Hermes profile `secretary` cron cadence", "Slack account alias `secretary`"]
confidence: high
reversibility: easy
decided_by: chairman-chris
decided_at: 2026-11-06
---

## Grounds

The Chairman directed the seat's creation and its tooling during the 2026-11-06
bootstrap session, and authorized autonomous setup. The envelope mirrors the
existing authority ladder rather than inventing a new privilege class, and the
record cites the role document as the single source of truth for seat details.

## What would reopen this

A Chairman directive changing the seat's mandate, authority envelope, or its
relationship to the Grok Secretary; or a charter amendment affecting operations
seats.
