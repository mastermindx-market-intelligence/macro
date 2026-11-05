---
key: COMMERCIAL-ACTIVATION-OWNS-JOURNEY-NOT-TRUTH-PLANES
question: 'Should one new workstream own the visitor-to-retention commercial journey, and does owning
  the journey permit it to own authentication, billing, entitlements, Watchlists, Portfolio, analytics
  storage, email, or Market OS?

  '
answer: 'Create WS:COMMERCIAL-ACTIVATION as an integration and acceptance owner only. It owns journey
  transitions, transition contracts, instrumentation completeness, activation computation, contextual
  upgrade orchestration, cohort/retention learning, and end-to-end proof. Every underlying truth plane
  keeps its existing owner: Supabase auth, Stripe customer/payment authority, user_entitlements, Account
  Identity, canonical watchlists/watchlist_symbols and portfolio_positions, Market OS product truth, the
  existing /api/collect + analytics_events plane, app.mailer, and the commercial-path sentinel transport.

  '
rationale: 'Historical policy rationale recorded on 2026-09-04, retained as dated reasoning. Its then-current
  wizard, owner census, product and dependency observations are not freshly re-attested in November. The
  2026-09-03 PROJECT_SOL census proved no current workstream spans visitor-to-retention: WS:ACCOUNT-IDENTITY-HARDENING
  owns identity, WS:MARKET-OS owns the product surface, WS:COMMERCIAL-PATH-ALERTING owns operational alarms,
  and the analytics sink has storage but no vocabulary owner. Forcing the journey into any of them stretches
  their charters; creating a new owner WITH truth-plane authority would duplicate systems that already
  exist and reopen settled ownership. A bounded integration owner closes the product gap without minting
  a second auth, billing, event, state, mail, or product plane.'
alternatives:
- option: Extend WS:MARKET-OS to own the commercial journey
  why_not: 'Market OS owns user-facing product truth, not cross-company growth instrumentation, billing
    interpretation, or funnel acceptance; the stretch would make one workstream both truth plane and its
    own auditor.

    '
- option: Create a full-stack growth workstream that also owns analytics storage and signup
  why_not: 'That mints a second analytics plane and a second identity/billing interpreter — exactly the
    duplication the no-rebuild census rejected; the existing planes are PROVEN_LIVE or BUILT_NOT_PROVEN,
    not absent.

    '
- option: Leave the journey ownerless and fix surfaces ad hoc
  why_not: 'The owner gap is the proven root cause of the current incoherence (Plan/Billing in free signup,
    unjoinable event vocabularies, no activation definition); ad hoc fixes cannot produce one measured
    journey.

    '
evidence:
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md
  §2.2-§2.3 (owner census and absence proof)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: agentos/workstreams/WS-ACCOUNT-IDENTITY-HARDENING.md,
  WS-MARKET-OS.md, WS-COMMERCIAL-PATH-ALERTING.md (adjacent owners, none spanning the journey)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: gh
  api repos/mastermindx-market-intelligence/macro/contents/agentos/workstreams — no commercial-activation
  record existed before this carrier (2026-09-04)'
- 'November source qualification: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324;
  original bundle custody and limits: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609.
  This records repair has not retrieved its payload.'
- 'Current source outcomes: Macro#6838/#6858 merged; Terminal#444/#446/#435/#507 merged; Terminal#445
  closed/unmerged. Source release does not prove the original production journey.'
affects:
- WS:COMMERCIAL-ACTIVATION
- WS:MARKET-OS
- WS:ACCOUNT-IDENTITY-HARDENING
- WS:COMMERCIAL-PATH-ALERTING
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

The complete original below is 3,608 UTF-8 bytes, Git blob `b23b6dea59841ce04e0dce4057c4af9e07f2c924`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: COMMERCIAL-ACTIVATION-OWNS-JOURNEY-NOT-TRUTH-PLANES
question: >
  Should one new workstream own the visitor-to-retention commercial journey, and does
  owning the journey permit it to own authentication, billing, entitlements, Watchlists,
  Portfolio, analytics storage, email, or Market OS?
answer: >
  Create WS:COMMERCIAL-ACTIVATION as an integration and acceptance owner only. It owns
  journey transitions, transition contracts, instrumentation completeness, activation
  computation, contextual upgrade orchestration, cohort/retention learning, and
  end-to-end proof. Every underlying truth plane keeps its existing owner: Supabase auth,
  Stripe customer/payment authority, user_entitlements, Account Identity, canonical
  watchlists/watchlist_symbols and portfolio_positions, Market OS product truth, the
  existing /api/collect + analytics_events plane, app.mailer, and the commercial-path
  sentinel transport.
rationale: >
  The 2026-09-03 PROJECT_SOL census proved no current workstream spans
  visitor-to-retention: WS:ACCOUNT-IDENTITY-HARDENING owns identity, WS:MARKET-OS owns
  the product surface, WS:COMMERCIAL-PATH-ALERTING owns operational alarms, and the
  analytics sink has storage but no vocabulary owner. Forcing the journey into any of
  them stretches their charters; creating a new owner WITH truth-plane authority would
  duplicate systems that already exist and reopen settled ownership. A bounded
  integration owner closes the product gap without minting a second auth, billing,
  event, state, mail, or product plane.
alternatives:
  - option: Extend WS:MARKET-OS to own the commercial journey
    why_not: >
      Market OS owns user-facing product truth, not cross-company growth
      instrumentation, billing interpretation, or funnel acceptance; the stretch would
      make one workstream both truth plane and its own auditor.
  - option: Create a full-stack growth workstream that also owns analytics storage and signup
    why_not: >
      That mints a second analytics plane and a second identity/billing interpreter —
      exactly the duplication the no-rebuild census rejected; the existing planes are
      PROVEN_LIVE or BUILT_NOT_PROVEN, not absent.
  - option: Leave the journey ownerless and fix surfaces ad hoc
    why_not: >
      The owner gap is the proven root cause of the current incoherence (Plan/Billing in
      free signup, unjoinable event vocabularies, no activation definition); ad hoc
      fixes cannot produce one measured journey.
evidence:
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md §2.2-§2.3 (owner census and absence proof)
  - agentos/workstreams/WS-ACCOUNT-IDENTITY-HARDENING.md, WS-MARKET-OS.md, WS-COMMERCIAL-PATH-ALERTING.md (adjacent owners, none spanning the journey)
  - "gh api repos/mastermindx-market-intelligence/macro/contents/agentos/workstreams — no commercial-activation record existed before this carrier (2026-09-04)"
affects:
  - "WS:COMMERCIAL-ACTIVATION"
  - "WS:MARKET-OS"
  - "WS:ACCOUNT-IDENTITY-HARDENING"
  - "WS:COMMERCIAL-PATH-ALERTING"
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

Ratified by direct Chairman grant of end-to-end authority to session
claude/mmx-commercial-activation-03fe73 on 2026-09-04, acting on PROJECT_SOL packet
MMX-SOL-COMMERCIAL-ACTIVATION-20260903-001. The workstream may compose and accept across
planes; it may never write around an authority. If a journey requirement seems to need a
truth-plane change, the change is commissioned to that plane's owner, not absorbed here.
``````
