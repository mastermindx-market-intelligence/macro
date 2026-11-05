---
key: BILLING-UNKNOWN-AND-MALFORMED-SUCCESS-FAIL-CLOSED
question: 'What may the product claim when payment or entitlement authority is unavailable, stale, or
  returns an incomplete/malformed success body?

  '
answer: 'Nothing beyond what the authority proves. Unknown entitlement renders as Unavailable, never as
  Free and never as paid. A same-owner last-good paid state may be displayed explicitly labeled stale
  but cannot newly unlock capability. A trial may be declared only with exact trialing status, non-empty
  subscription identity, and a valid authority-sourced trial end — no locally fabricated dates. A 2xx
  billing response whose body cannot be verified stays on the Billing surface with "completion could not
  be verified"; checkout.completed and trial.started events are prohibited in that state. All billing
  state and dates come only from payment authority; entitlement unlocks come only from verified entitlement
  authority.

  '
rationale: 'Historical policy rationale recorded on 2026-09-04, retained as dated reasoning. Its then-current
  wizard, owner census, product and dependency observations are not freshly re-attested in November. Money
  and access claims are user-trust boundaries: a fabricated trial date or an unlock from a stale cache
  is a lie the user can act on. HTTP success alone does not prove a subscription exists. Fail-closed keeps
  every failure recoverable (retry, portal) while fail-open manufactures unowed access or phantom purchases
  that no later reconciliation can honestly unwind. This is the cross-app law that Terminal D7 (PR #435)
  and E-3/E-4 (PRs #444/#445) implement client-side.'
alternatives:
- option: Treat unknown entitlement as Free (fail-open to the cheapest tier)
  why_not: 'Unverified != free: a paid user on a flaky connection would see their product degrade to Free
    and paid surfaces lock/flicker — punishing exactly the users who paid; unknown must render as unknown.

    '
- option: Trust client-observed checkout success and reconcile later via webhooks
  why_not: 'Client-authoritative checkout events were explicitly rejected in the no-rebuild census; webhook
    reconciliation cannot un-tell a user they had a trial.

    '
- option: Cache entitlement indefinitely and unlock from cache
  why_not: 'Stale display must never be gate authority; cancellation/past-due would keep unlocking until
    cache expiry.

    '
evidence:
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md
  §6.10 (authority matrix), §5.3 (malformed-2xx state law)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: Terminal
  PR #435 (claude/d5-billing-fail-closed, head d6eb13f24084cbf70f72580de04837f082f07182) — D7 fail-closed
  trial receipt'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: Terminal
  PRs #444/#445 — E-3 canonical entitlement store (unverified != free), E-4 freshness/invalidation'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/MASTERMIND_SECURITY_AUTH_BILLING_AUDIT.md
  (webhook/portal spine this composes with)'
- 'November source qualification: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324;
  original bundle custody and limits: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609.
  This records repair has not retrieved its payload.'
- 'Current source outcomes: Macro#6838/#6858 merged; Terminal#444/#446/#435/#507 merged; Terminal#445
  closed/unmerged. Source release does not prove the original production journey.'
affects:
- WS:COMMERCIAL-ACTIVATION
- WS:ACCOUNT-IDENTITY-HARDENING
- terminal/components/onboarding/**
- terminal/lib/useEntitlement.ts
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

# Retained commercial policy

The original Chairman policy, decision date, alternatives and authority boundaries remain. November annotations qualify its supporting historical observations; they do not redesign signup, Watchlist, billing or measurement. The third-symbol prompt, where applicable, remains a preregistered product hypothesis rather than a measured success.

## Source qualification — November 5, 2026

Assigned Sol root `macro-backlog-oldest-first-20261105-c3` qualifies this record under protected
Mastermind `5fbcbffe77a06e41bc590fa09d12a7e2baefb4f7`. The source boundary is the ten existing AgentOS records
on original PR #6835; [the current claim](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324) transfers no application,
runtime, account, report or Watchlist writer.

The original PR's claim that frozen artifacts were committed under
`research/commercial_activation/` is retracted. The actual dated recovery source is
[receipt 5601315609](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609): archive
`MMX_COMMERCIAL_ACTIVATION_SOL_BUNDLE_20260903.zip`, 32,868 bytes,
SHA-256 `642a1f27a33d30a7dc9cb076f7e1f8ec0880a5be3b349307fa4500f76628d27e`,
in authenticated Linear MAS-6 attachment `fcdbe167-85d4-4331-9857-b405ca2b0f49`.
That receipt records original-member hashes and authenticated custody, discloses the
unauthenticated 401, and does not claim a complete stored-object hash recomputation.
This qualification reads that published receipt, not the archive or attachment; it
publishes no replacement research payload and claims no fresh attachment availability.

Original policy references to that bundle are historical locators, not claims that this
carrier published those paths. Original source/history/caller/collision, archive-content,
Flow Velocity and production-script refusals remain fenced. No alternate carrier, retained
copy or reconstruction is used to repeat them. Current source merges and dated synthetic
proof remain distinct from the original production canary and full commercial journey.

## Complete original September record — dated evidence

The complete original below is 3,217 UTF-8 bytes, Git blob `bd84a8681976ef224946f269a8342e6baa57e39a`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: BILLING-UNKNOWN-AND-MALFORMED-SUCCESS-FAIL-CLOSED
question: >
  What may the product claim when payment or entitlement authority is unavailable,
  stale, or returns an incomplete/malformed success body?
answer: >
  Nothing beyond what the authority proves. Unknown entitlement renders as Unavailable,
  never as Free and never as paid. A same-owner last-good paid state may be displayed
  explicitly labeled stale but cannot newly unlock capability. A trial may be declared
  only with exact trialing status, non-empty subscription identity, and a valid
  authority-sourced trial end — no locally fabricated dates. A 2xx billing response
  whose body cannot be verified stays on the Billing surface with "completion could not
  be verified"; checkout.completed and trial.started events are prohibited in that
  state. All billing state and dates come only from payment authority; entitlement
  unlocks come only from verified entitlement authority.
rationale: >
  Money and access claims are user-trust boundaries: a fabricated trial date or an
  unlock from a stale cache is a lie the user can act on. HTTP success alone does not
  prove a subscription exists. Fail-closed keeps every failure recoverable (retry,
  portal) while fail-open manufactures unowed access or phantom purchases that no later
  reconciliation can honestly unwind. This is the cross-app law that Terminal D7
  (PR #435) and E-3/E-4 (PRs #444/#445) implement client-side.
alternatives:
  - option: Treat unknown entitlement as Free (fail-open to the cheapest tier)
    why_not: >
      Unverified != free: a paid user on a flaky connection would see their product
      degrade to Free and paid surfaces lock/flicker — punishing exactly the users who
      paid; unknown must render as unknown.
  - option: Trust client-observed checkout success and reconcile later via webhooks
    why_not: >
      Client-authoritative checkout events were explicitly rejected in the no-rebuild
      census; webhook reconciliation cannot un-tell a user they had a trial.
  - option: Cache entitlement indefinitely and unlock from cache
    why_not: >
      Stale display must never be gate authority; cancellation/past-due would keep
      unlocking until cache expiry.
evidence:
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md §6.10 (authority matrix), §5.3 (malformed-2xx state law)
  - "Terminal PR #435 (claude/d5-billing-fail-closed, head d6eb13f24084cbf70f72580de04837f082f07182) — D7 fail-closed trial receipt"
  - "Terminal PRs #444/#445 — E-3 canonical entitlement store (unverified != free), E-4 freshness/invalidation"
  - research/MASTERMIND_SECURITY_AUTH_BILLING_AUDIT.md (webhook/portal spine this composes with)
affects:
  - "WS:COMMERCIAL-ACTIVATION"
  - "WS:ACCOUNT-IDENTITY-HARDENING"
  - terminal/components/onboarding/**
  - terminal/lib/useEntitlement.ts
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

Ratified by direct Chairman grant to session claude/mmx-commercial-activation-03fe73 on
2026-09-04. Analytics may describe billing outcomes only from server authority events;
no client emitter may originate a billing success fact.
``````
