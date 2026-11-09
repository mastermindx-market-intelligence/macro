---
key: FREE-SIGNUP-EXCLUDES-PLAN-AND-BILLING
question: 'Should Plan and Billing remain steps of the default account-creation wizard?

  '
answer: 'No. Signup mode contains Account and Preferences only. Plan and Billing exist solely in an explicit
  upgrade mode entered by deliberate user intent (opening Pricing) or by a contextual post-activation
  capability limit. Billing remains fully available at all times; it is never a step of free account creation.

  '
rationale: 'Historical policy rationale recorded on 2026-09-04, retained as dated reasoning. Its then-current
  wizard, owner census, product and dependency observations are not freshly re-attested in November. The
  current five-step Terminal wizard (Account, Preferences, Plan, Billing, Done) conflates registration
  with purchase: it makes the free account appear to require a billing decision, contradicts the value-first
  architecture (frozen law 3 and 4), and poisons the paid-intent signal — a paywall.encountered or plans.viewed
  emitted from a forced wizard step measures wizard completion, not upgrade intent. The capability ledger
  grades "current signup aligned with value-before-paid-ask" as BROKEN for exactly this reason.'
alternatives:
- option: Keep Plan/Billing steps but add a prominent skip
  why_not: 'A skippable paid ask is still a paid ask during registration; it keeps the intent signal contaminated
    and keeps free signup measurably longer than two screens.

    '
- option: Remove billing surfaces from the product entirely until activation
  why_not: 'Voluntary purchase intent is legitimate at any time (law 4 allows a user to open Pricing whenever
    they want); hiding Pricing would suppress real revenue and make deliberate upgrade intent unmeasurable.

    '
evidence:
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md
  §3 (capability ledger rows "Minimal two-screen free signup" NOT_BUILT / "signup aligned" BROKEN)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: terminal/components/onboarding/OnboardingSheet.tsx
  (current five-step wizard implementation)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/MASTERMIND_COMMERCIAL_V1_IMPLEMENTATION_PLAN.md
  (upgrade-mode specification)'
- 'November source qualification: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324;
  original bundle custody and limits: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609.
  This records repair has not retrieved its payload.'
- 'Current source outcomes: Macro#6838/#6858 merged; Terminal#444/#446/#435/#507 merged; Terminal#445
  closed/unmerged. Source release does not prove the original production journey.'
affects:
- WS:COMMERCIAL-ACTIVATION
- WS:ACCOUNT-IDENTITY-HARDENING
- terminal/components/onboarding/**
confidence: high
reversibility: easy
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

The complete original below is 2,437 UTF-8 bytes, Git blob `ee5aaf57694b4c1748fa507eb9f9fd7f0e65e378`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: FREE-SIGNUP-EXCLUDES-PLAN-AND-BILLING
question: >
  Should Plan and Billing remain steps of the default account-creation wizard?
answer: >
  No. Signup mode contains Account and Preferences only. Plan and Billing exist solely in
  an explicit upgrade mode entered by deliberate user intent (opening Pricing) or by a
  contextual post-activation capability limit. Billing remains fully available at all
  times; it is never a step of free account creation.
rationale: >
  The current five-step Terminal wizard (Account, Preferences, Plan, Billing, Done)
  conflates registration with purchase: it makes the free account appear to require a
  billing decision, contradicts the value-first architecture (frozen law 3 and 4), and
  poisons the paid-intent signal — a paywall.encountered or plans.viewed emitted from a
  forced wizard step measures wizard completion, not upgrade intent. The capability
  ledger grades "current signup aligned with value-before-paid-ask" as BROKEN for
  exactly this reason.
alternatives:
  - option: Keep Plan/Billing steps but add a prominent skip
    why_not: >
      A skippable paid ask is still a paid ask during registration; it keeps the intent
      signal contaminated and keeps free signup measurably longer than two screens.
  - option: Remove billing surfaces from the product entirely until activation
    why_not: >
      Voluntary purchase intent is legitimate at any time (law 4 allows a user to open
      Pricing whenever they want); hiding Pricing would suppress real revenue and make
      deliberate upgrade intent unmeasurable.
evidence:
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md §3 (capability ledger rows "Minimal two-screen free signup" NOT_BUILT / "signup aligned" BROKEN)
  - terminal/components/onboarding/OnboardingSheet.tsx (current five-step wizard implementation)
  - research/MASTERMIND_COMMERCIAL_V1_IMPLEMENTATION_PLAN.md (upgrade-mode specification)
affects:
  - "WS:COMMERCIAL-ACTIVATION"
  - "WS:ACCOUNT-IDENTITY-HARDENING"
  - terminal/components/onboarding/**
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-04
---

Ratified by direct Chairman grant to session claude/mmx-commercial-activation-03fe73 on
2026-09-04. Implementation is CA2 (Terminal journey parity) scope and must compose with
the settled Terminal carriers #444/#445/#435 — it does not start from this record.
``````
