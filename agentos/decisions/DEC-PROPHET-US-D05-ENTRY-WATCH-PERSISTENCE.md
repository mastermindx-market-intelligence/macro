---
key: PROPHET-US-D05-ENTRY-WATCH-PERSISTENCE
question: >
  Which durable owners may honestly back watchlist, portfolio, Pass, thesis, milestone and
  alerts persistence for Prophet US, and which user-facing actions must remain disabled when
  no durable owner exists? (R6 decision D05)
answer: >
  The census ruling accepts the observed owner map: watchlists and portfolio scopes have real
  cloud owners (`watchlist_symbols` and `portfolio_*`), while Pass, thesis and milestone
  actions have no durable owner today. Those controls therefore stay honestly DISABLED with
  plain-word “not saved yet” wording and may never be advertised as saved. The ruling also
  accepts three watchlist cases as forbidden: a read must not paint `saved`; a failed push
  needs a per-list pending marker and retry; and a failed unwatch needs a list-scoped
  tombstone so union merge cannot resurrect the deleted row. For `holdings_material_change`,
  the alert kind is either disabled at the surface or given a producer by the alerts owner as
  open item D05-b. A `public.trade_episodes` extension with a new `source` enum value is the
  accepted candidate owner for durable thesis capture, but production DDL remains an
  operator-ratified step.
rationale: >
  The D05 owner census verified the actual persistence result rather than inferring it from
  UI state. Its defects showed that read success was being rendered as a write, failed pushes
  were dropped without retry, and failed unwatch operations could later reappear through union
  merge. R6 §16, the plain-word doctrine, and the prohibition on production DDL without
  operator ratification therefore require truthful absence until a durable owner exists.
alternatives:
  - option: Treat a signed-in read or local UI state as cloud persistence.
    why_not: Local-only behaviour cannot be advertised as cloud persistence; `saved` may follow only a landed write.
  - option: Keep a failed push or failed DELETE silently absorbed by the existing union merge.
    why_not: A dropped retry loses user intent, and a failed DELETE can resurrect a cloud row and falsely paint `saved`.
  - option: Enable Pass, thesis or milestone surfaces on local storage before durable owners exist.
    why_not: The surfaces would make persistence promises they cannot satisfy; they remain honestly DISABLED until an owner lands.
  - option: Run the `trade_episodes` DDL now to create the thesis owner.
    why_not: Production DDL is an operator-ratified EXACT_HUMAN_GATE and has not been authorized.
evidence:
  - research/prophet_v4/r6_program/wave0/D05_USER_ACTION_OWNER_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D05-01_2026-09-23.md
  - Macro PR 7811 (merged 5d8c71c5), carrying the census and ruling after lane PR 7816 was closed as superseded
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision D05 for Prophet US durable user-action ownership. Build unit
`pu_w1_watch_honesty` implements the three forbidden-case corrections with RED→GREEN tests
and two mutants under the ruling’s frozen three-defect spec.

Unresolved: D05-b, whether `holdings_material_change` gains a producer or is disabled, is
owned by the alerts surface. D05-c, the owner mapping for Pass, thesis and milestone, remains
blocked by the operator-ratified DDL gate.

## What this decision does not do

It does not promote a Prophet signal, change rank/gate/size, or touch the D5/B1 science
surfaces. It does not authorize DDL, redesign the store, or imply local-only persistence when
no durable owner exists.
